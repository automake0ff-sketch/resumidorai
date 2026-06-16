"""
Script para crear las colecciones de PocketBase a partir de pocketbase_schema.json.

Uso:
    python setup_pocketbase.py

Alternativa sin terminal:
    Admin UI -> Settings -> Import collections -> sube pocketbase_schema.json directamente.

Este script hace lo mismo via API, util para CI/CD o despliegues automatizados.
"""

import asyncio
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ.get("POCKETBASE_URL", "http://localhost:8090").rstrip("/")
ADMIN_EMAIL = os.environ.get("POCKETBASE_ADMIN_EMAIL", "admin@resumidorai.com")
ADMIN_PASSWORD = os.environ.get("POCKETBASE_ADMIN_PASSWORD", "change_me")

SCHEMA_FILE = Path(__file__).parent.parent / "pocketbase_schema.json"


async def get_admin_token() -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{PB_URL}/api/admins/auth-with-password",
            json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        resp.raise_for_status()
        return resp.json()["token"]


async def get_existing_collections(token: str) -> set:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{PB_URL}/api/collections",
            params={"perPage": 200},
            headers={"Authorization": token},
        )
        resp.raise_for_status()
        return {c["name"] for c in resp.json().get("items", [])}


async def create_collection(token: str, schema: dict, existing: set):
    if schema["name"] in existing:
        print(f"  already exists, skipping: {schema['name']}")
        return

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{PB_URL}/api/collections",
            json=schema,
            headers={"Authorization": token},
        )
        if resp.status_code >= 400:
            print(f"  ERROR creating '{schema['name']}': {resp.text}")
            return
        print(f"  OK created: {schema['name']}")


async def main():
    print("Configurando PocketBase para ResumidorAI...")
    print(f"  URL: {PB_URL}")
    print(f"  Schema: {SCHEMA_FILE}")

    if not SCHEMA_FILE.exists():
        print(f"ERROR: no se encontro {SCHEMA_FILE}")
        return

    collections = json.loads(SCHEMA_FILE.read_text())

    token = await get_admin_token()
    print("Admin autenticado")

    existing = await get_existing_collections(token)

    for col in collections:
        await create_collection(token, col, existing)

    print(f"\nListo. Admin UI: {PB_URL}/_/")


if __name__ == "__main__":
    asyncio.run(main())
