"""
Cliente de Firestore para ResumidorAI.

Usa el SDK Admin de Firebase (firebase-admin) con todas las operaciones
síncronas del SDK envueltas en asyncio.get_event_loop().run_in_executor()
para no bloquear el event loop de FastAPI/uvicorn.

Credenciales: la cuenta de servicio se carga desde FIREBASE_SERVICE_ACCOUNT_JSON.
"""
import asyncio
import os
import json
import logging
import functools
from typing import Any

import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger(__name__)

_db = None
_executor = None  # ThreadPoolExecutor for Firestore sync calls


def _get_executor():
    """Lazy ThreadPoolExecutor — reuses the same pool across calls."""
    global _executor
    if _executor is None:
        from concurrent.futures import ThreadPoolExecutor
        _executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="firestore")
    return _executor


async def _run_sync(fn, *args, **kwargs):
    """Run a blocking Firestore call in a thread pool, freeing the event loop."""
    loop = asyncio.get_event_loop()
    if kwargs:
        fn = functools.partial(fn, *args, **kwargs)
        return await loop.run_in_executor(_get_executor(), fn)
    return await loop.run_in_executor(_get_executor(), fn, *args)


def _escape_newlines_inside_json_strings(text: str) -> str:
    """Fix raw newlines inside JSON string values (common in Firebase service account JSON)."""
    result = []
    in_string = False
    escaped = False
    for ch in text:
        if escaped:
            result.append(ch)
            escaped = False
            continue
        if ch == "\\":
            result.append(ch)
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if ch == "\n" and in_string:
            result.append("\\n")
            continue
        if ch == "\r" and in_string:
            continue
        result.append(ch)
    return "".join(result)


async def init_firestore():
    """Initialize Firestore connection. Called once at app startup."""
    global _db

    raw_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "")
    if not raw_json:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT_JSON no está configurada. "
            "Pega el JSON completo de la cuenta de servicio de Firebase."
        )

    service_account_info = {}
    try:
        service_account_info = json.loads(raw_json)
    except json.JSONDecodeError:
        try:
            sanitized = _escape_newlines_inside_json_strings(raw_json)
            service_account_info = json.loads(sanitized)
            logger.warning(
                "FIREBASE_SERVICE_ACCOUNT_JSON tenía saltos de línea sin escapar; "
                "se corrigió automáticamente."
            )
        except json.JSONDecodeError as e:
            raise RuntimeError(f"FIREBASE_SERVICE_ACCOUNT_JSON no es JSON válido: {e}")

    if not service_account_info.get("type") == "service_account":
        raise ValueError("FIREBASE_SERVICE_ACCOUNT_JSON debe ser un JSON de cuenta de servicio válido.")

    if not firebase_admin._apps:
        cred = credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(cred)

    _db = firestore.client()
    logger.info("Firestore conectado correctamente")


# Keep old name as alias for any stale imports
init_pocketbase = init_firestore


def _get_db():
    if _db is None:
        raise RuntimeError("Firestore no inicializado. Llama a init_firestore() primero.")
    return _db


# ─── Async CRUD ─────────────────────────────────────────────────────────────

async def pb_create(collection: str, data: dict) -> dict:
    db = _get_db()

    def _create():
        doc_ref = db.collection(collection).document()
        payload = {**data, "created": firestore.SERVER_TIMESTAMP}
        doc_ref.set(payload)
        snapshot = doc_ref.get()
        result = snapshot.to_dict() or {}
        result["id"] = doc_ref.id
        result["created"] = _serialize_timestamp(result.get("created"))
        return result

    return await _run_sync(_create)


async def pb_update(collection: str, record_id: str, data: dict) -> dict:
    db = _get_db()

    def _update():
        doc_ref = db.collection(collection).document(record_id)
        doc_ref.update(data)
        snapshot = doc_ref.get()
        result = snapshot.to_dict() or {}
        result["id"] = record_id
        result["created"] = _serialize_timestamp(result.get("created"))
        return result

    return await _run_sync(_update)


async def pb_get(collection: str, record_id: str) -> dict | None:
    db = _get_db()

    def _get():
        snapshot = db.collection(collection).document(record_id).get()
        if not snapshot.exists:
            return None
        result = snapshot.to_dict() or {}
        result["id"] = record_id
        result["created"] = _serialize_timestamp(result.get("created"))
        return result

    return await _run_sync(_get)


async def pb_list(
    collection: str,
    filter: str = "",
    sort: str = "-created",
    page: int = 1,
    per_page: int = 20,
    expand: str = "",
) -> dict:
    db = _get_db()

    def _list():
        query = db.collection(collection)

        for field, value in _parse_filter(filter):
            query = query.where(field, "==", value)

        if sort:
            if sort.startswith("-"):
                field = sort[1:]
                query = query.order_by(field, direction=firestore.Query.DESCENDING)
            else:
                query = query.order_by(sort, direction=firestore.Query.ASCENDING)

        docs = list(query.limit(per_page).offset((page - 1) * per_page).stream())

        items = []
        for doc in docs:
            item = doc.to_dict() or {}
            item["id"] = doc.id
            item["created"] = _serialize_timestamp(item.get("created"))
            items.append(item)

        # Count query (separate round-trip; needed for trial quota)
        count_query = db.collection(collection)
        for field, value in _parse_filter(filter):
            count_query = count_query.where(field, "==", value)
        total = count_query.count().get()[0][0].value

        return {"items": items, "page": page, "perPage": per_page, "totalItems": total}

    return await _run_sync(_list)


async def pb_get_first(collection: str, filter: str) -> dict | None:
    result = await pb_list(collection, filter=filter, per_page=1)
    items = result.get("items", [])
    return items[0] if items else None


async def pb_delete(collection: str, record_id: str):
    db = _get_db()
    await _run_sync(db.collection(collection).document(record_id).delete)


async def pb_upsert(collection: str, filter: str, data: dict) -> dict:
    existing = await pb_get_first(collection, filter)
    if existing:
        return await pb_update(collection, existing["id"], data)
    return await pb_create(collection, data)


def _parse_filter(filter: str) -> list[tuple[str, str]]:
    """Parse 'field="value"&&field2="value2"' to [(field, value), ...]."""
    if not filter:
        return []
    pairs = []
    for clause in filter.split("&&"):
        clause = clause.strip()
        if "=" not in clause:
            continue
        field, _, raw_value = clause.partition("=")
        value = raw_value.strip().strip('"')
        pairs.append((field.strip(), value))
    return pairs


def _serialize_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


# Compatibility alias
def _esc(value: str) -> str:
    return value
