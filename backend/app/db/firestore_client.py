"""
Cliente de Firestore para ResumidorAI.

Reemplaza a PocketBase. Usa el SDK Admin de Firebase (firebase-admin),
que se autentica con una cuenta de servicio (Service Account JSON) y tiene
privilegios totales sobre Firestore -- no aplica reglas de seguridad de
cliente, así que toda la validación de "quién puede leer/escribir qué"
vive en el backend (en los endpoints de FastAPI), no en Firestore mismo.

Credenciales: la cuenta de servicio se carga desde una variable de entorno
con el JSON completo (FIREBASE_SERVICE_ACCOUNT_JSON), nunca desde un archivo
en el repo. Esto evita que la clave privada termine en git por accidente.
"""
import os
import json
import logging
from typing import Any

import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger(__name__)

_db = None


async def init_pocketbase():
    """
    Se mantiene el nombre 'init_pocketbase' por compatibilidad con el resto
    del código (main.py la llama en el lifespan de FastAPI) -- internamente
    ahora inicializa Firestore. Renombrar todos los call sites no aporta
    nada funcional y aumenta el riesgo de un fix a medias.
    """
    global _db

    raw_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "")
    if not raw_json:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT_JSON no está configurada. "
            "Pega el JSON completo de la cuenta de servicio de Firebase "
            "(Project Settings -> Service Accounts -> Generate new private key) "
            "como variable de entorno en Railway."
        )

    try:
        service_account_info = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"FIREBASE_SERVICE_ACCOUNT_JSON no es JSON válido: {e}")

    if not firebase_admin._apps:
        cred = credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(cred)

    _db = firestore.client()
    logger.info("Firestore conectado correctamente")


def _get_db():
    if _db is None:
        raise RuntimeError("Firestore no inicializado. Llama a init_pocketbase() primero.")
    return _db


def _esc(value: str) -> str:
    """
    Se mantiene por compatibilidad con el código que llama a _esc() antes de
    construir filtros de texto (heredado de la sintaxis de filtros de
    PocketBase). Firestore no tiene ese problema: las queries usan
    comparaciones estructuradas (where("campo", "==", valor)), no strings
    interpolados, así que no hay riesgo de inyección que escapar. La función
    es un passthrough que existe solo para no tener que tocar las llamadas
    existentes en job_processor.py, webhooks.py, etc.
    """
    return value


# ─────────────────────────────────────────────
# Operaciones CRUD genéricas, con la misma forma que las de pocketbase.py
# para minimizar cambios en el resto del código.
# ─────────────────────────────────────────────

async def pb_create(collection: str, data: dict) -> dict:
    db = _get_db()
    doc_ref = db.collection(collection).document()
    payload = {**data, "created": firestore.SERVER_TIMESTAMP}
    doc_ref.set(payload)
    snapshot = doc_ref.get()
    result = snapshot.to_dict() or {}
    result["id"] = doc_ref.id
    result["created"] = _serialize_timestamp(result.get("created"))
    return result


async def pb_update(collection: str, record_id: str, data: dict) -> dict:
    db = _get_db()
    doc_ref = db.collection(collection).document(record_id)
    doc_ref.update(data)
    snapshot = doc_ref.get()
    result = snapshot.to_dict() or {}
    result["id"] = record_id
    result["created"] = _serialize_timestamp(result.get("created"))
    return result


async def pb_get(collection: str, record_id: str) -> dict | None:
    db = _get_db()
    snapshot = db.collection(collection).document(record_id).get()
    if not snapshot.exists:
        return None
    result = snapshot.to_dict() or {}
    result["id"] = record_id
    result["created"] = _serialize_timestamp(result.get("created"))
    return result


async def pb_list(
    collection: str,
    filter: str = "",
    sort: str = "-created",
    page: int = 1,
    per_page: int = 20,
    expand: str = "",
) -> dict:
    """
    'filter' aquí sigue el formato simple usado en el resto del código:
    'campo="valor"' o 'campo1="valor1"&&campo2="valor2"' (heredado de la
    sintaxis de filtros de PocketBase). Se parsea a queries .where() de
    Firestore. No soporta operadores distintos de igualdad porque el
    código existente solo los necesita así.
    """
    db = _get_db()
    query = db.collection(collection)

    for field, value in _parse_filter(filter):
        query = query.where(field, "==", value)

    # Firestore no soporta count() barato en todas las versiones del SDK de
    # forma uniforme: pedimos solo lo necesario y devolvemos totalItems con
    # el conteo de la página actual cuando per_page=1 se usa típicamente
    # para checks de "¿existe algo?" más que para paginación real.
    docs = list(query.limit(per_page).offset((page - 1) * per_page).stream())

    items = []
    for doc in docs:
        item = doc.to_dict() or {}
        item["id"] = doc.id
        item["created"] = _serialize_timestamp(item.get("created"))
        items.append(item)

    if sort.startswith("-"):
        field = sort[1:]
        items.sort(key=lambda x: x.get(field) or "", reverse=True)
    elif sort:
        items.sort(key=lambda x: x.get(sort) or "")

    # totalItems real (sin paginar) -- necesario para el conteo de por vida
    # del plan trial. Se pide aparte porque .stream() ya vino limitado arriba.
    count_query = db.collection(collection)
    for field, value in _parse_filter(filter):
        count_query = count_query.where(field, "==", value)
    total = count_query.count().get()[0][0].value

    return {"items": items, "page": page, "perPage": per_page, "totalItems": total}


async def pb_get_first(collection: str, filter: str) -> dict | None:
    result = await pb_list(collection, filter=filter, per_page=1)
    items = result.get("items", [])
    return items[0] if items else None


async def pb_delete(collection: str, record_id: str):
    db = _get_db()
    db.collection(collection).document(record_id).delete()


async def pb_upsert(collection: str, filter: str, data: dict) -> dict:
    existing = await pb_get_first(collection, filter)
    if existing:
        return await pb_update(collection, existing["id"], data)
    return await pb_create(collection, data)


def _parse_filter(filter: str) -> list[tuple[str, str]]:
    """Parsea 'campo="valor"&&campo2="valor2"' a [(campo, valor), ...]."""
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
    """Convierte un Timestamp de Firestore a ISO 8601 string, igual que
    devolvía PocketBase, para no romper el resto del código que espera
    strings en el campo 'created'."""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
