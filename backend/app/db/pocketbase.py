"""
Cliente PocketBase para ResumidorAI.
Incluye reconexión automática cuando el token expira (cada 12h).
"""
import os
import time
import httpx
from typing import Any

_pb_url: str = ""
_admin_token: str = ""
_token_created_at: float = 0
TOKEN_TTL = 3600 * 11  # renovar cada 11h (PocketBase expira a las 12h)


async def _auth() -> str:
    global _admin_token, _token_created_at
    if _admin_token and (time.time() - _token_created_at) < TOKEN_TTL:
        return _admin_token

    email = os.environ["POCKETBASE_ADMIN_EMAIL"]
    password = os.environ["POCKETBASE_ADMIN_PASSWORD"]
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{_pb_url}/api/admins/auth-with-password",
            json={"identity": email, "password": password},
        )
        resp.raise_for_status()
        _admin_token = resp.json()["token"]
        _token_created_at = time.time()
    return _admin_token


async def init_pocketbase():
    global _pb_url
    _pb_url = os.environ["POCKETBASE_URL"].rstrip("/")
    await _auth()
    print(f"✅ PocketBase conectado: {_pb_url}")


async def _headers() -> dict:
    token = await _auth()
    return {"Authorization": token, "Content-Type": "application/json"}


async def pb_create(collection: str, data: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{_pb_url}/api/collections/{collection}/records",
            json=data, headers=await _headers(),
        )
        resp.raise_for_status()
        return resp.json()


async def pb_update(collection: str, record_id: str, data: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.patch(
            f"{_pb_url}/api/collections/{collection}/records/{record_id}",
            json=data, headers=await _headers(),
        )
        resp.raise_for_status()
        return resp.json()


async def pb_get(collection: str, record_id: str) -> dict | None:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{_pb_url}/api/collections/{collection}/records/{record_id}",
            headers=await _headers(),
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()


async def pb_list(
    collection: str,
    filter: str = "",
    sort: str = "-created",
    page: int = 1,
    per_page: int = 20,
    expand: str = "",
) -> dict:
    params: dict[str, Any] = {"page": page, "perPage": per_page, "sort": sort}
    if filter:
        params["filter"] = filter
    if expand:
        params["expand"] = expand
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{_pb_url}/api/collections/{collection}/records",
            params=params, headers=await _headers(),
        )
        resp.raise_for_status()
        return resp.json()


async def pb_get_first(collection: str, filter: str) -> dict | None:
    result = await pb_list(collection, filter=filter, per_page=1)
    items = result.get("items", [])
    return items[0] if items else None


async def pb_delete(collection: str, record_id: str):
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.delete(
            f"{_pb_url}/api/collections/{collection}/records/{record_id}",
            headers=await _headers(),
        )
        resp.raise_for_status()


async def pb_upsert(collection: str, filter: str, data: dict) -> dict:
    """Create or update based on filter."""
    existing = await pb_get_first(collection, filter)
    if existing:
        return await pb_update(collection, existing["id"], data)
    return await pb_create(collection, data)
