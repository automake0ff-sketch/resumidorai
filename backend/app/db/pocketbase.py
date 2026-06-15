"""
Cliente PocketBase para ResumidorAI.
PocketBase expone una REST API en /api/collections/...
"""
import os
import httpx
from typing import Any

_pb_url: str = ""
_admin_token: str = ""


async def init_pocketbase():
    global _pb_url, _admin_token
    _pb_url = os.environ["POCKETBASE_URL"].rstrip("/")
    email = os.environ["POCKETBASE_ADMIN_EMAIL"]
    password = os.environ["POCKETBASE_ADMIN_PASSWORD"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_pb_url}/api/admins/auth-with-password",
            json={"identity": email, "password": password},
        )
        resp.raise_for_status()
        _admin_token = resp.json()["token"]


def _headers() -> dict:
    return {"Authorization": _admin_token, "Content-Type": "application/json"}


async def pb_create(collection: str, data: dict) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_pb_url}/api/collections/{collection}/records",
            json=data,
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.json()


async def pb_update(collection: str, record_id: str, data: dict) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{_pb_url}/api/collections/{collection}/records/{record_id}",
            json=data,
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.json()


async def pb_get(collection: str, record_id: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_pb_url}/api/collections/{collection}/records/{record_id}",
            headers=_headers(),
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
) -> dict:
    params: dict[str, Any] = {"page": page, "perPage": per_page, "sort": sort}
    if filter:
        params["filter"] = filter
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_pb_url}/api/collections/{collection}/records",
            params=params,
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.json()


async def pb_get_first(collection: str, filter: str) -> dict | None:
    result = await pb_list(collection, filter=filter, per_page=1)
    items = result.get("items", [])
    return items[0] if items else None


async def pb_delete(collection: str, record_id: str):
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{_pb_url}/api/collections/{collection}/records/{record_id}",
            headers=_headers(),
        )
        resp.raise_for_status()
