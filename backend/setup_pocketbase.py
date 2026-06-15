"""
Script para crear las colecciones de PocketBase.
Ejecutar una sola vez: python setup_pocketbase.py

PocketBase Collections:
- users_profiles  → info del usuario + plan
- summary_jobs    → trabajos de resumen
- user_usage      → contador mensual
"""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ.get("POCKETBASE_URL", "http://localhost:8090")
ADMIN_EMAIL = os.environ.get("POCKETBASE_ADMIN_EMAIL", "admin@resumidorai.com")
ADMIN_PASSWORD = os.environ.get("POCKETBASE_ADMIN_PASSWORD", "change_me")


async def get_admin_token() -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PB_URL}/api/admins/auth-with-password",
            json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        resp.raise_for_status()
        return resp.json()["token"]


async def create_collection(token: str, schema: dict):
    headers = {"Authorization": token}
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PB_URL}/api/collections",
            json=schema,
            headers=headers,
        )
        if resp.status_code == 400 and "already exists" in resp.text:
            print(f"  ⚠️  '{schema['name']}' ya existe, omitiendo")
            return
        resp.raise_for_status()
        print(f"  ✅ Colección '{schema['name']}' creada")


async def main():
    print("🚀 Configurando PocketBase para ResumidorAI...")
    token = await get_admin_token()
    print("✅ Admin autenticado")

    collections = [
        {
            "name": "user_profiles",
            "type": "base",
            "schema": [
                {"name": "clerk_user_id", "type": "text", "required": True},
                {"name": "email", "type": "email", "required": True},
                {"name": "name", "type": "text"},
                {"name": "plan", "type": "select", "required": True,
                 "options": {"values": ["free", "starter", "pro", "unlimited"]},
                 "default": "free"},
                {"name": "stripe_customer_id", "type": "text"},
            ],
        },
        {
            "name": "summary_jobs",
            "type": "base",
            "schema": [
                {"name": "clerk_user_id", "type": "text", "required": True},
                {"name": "url", "type": "url", "required": True},
                {"name": "language", "type": "text", "default": "es"},
                {"name": "length", "type": "select",
                 "options": {"values": ["short", "medium", "detailed"]}},
                {"name": "include_chapters", "type": "bool", "default": True},
                {"name": "include_key_points", "type": "bool", "default": True},
                {"name": "include_transcript", "type": "bool", "default": False},
                {"name": "status", "type": "select", "required": True,
                 "options": {"values": ["pending", "processing", "completed", "failed"]}},
                {"name": "title", "type": "text"},
                {"name": "thumbnail", "type": "url"},
                {"name": "duration_seconds", "type": "number"},
                {"name": "summary", "type": "editor"},
                {"name": "key_points", "type": "json"},
                {"name": "chapters", "type": "json"},
                {"name": "transcript", "type": "editor"},
                {"name": "error", "type": "text"},
                {"name": "started_at", "type": "date"},
                {"name": "completed_at", "type": "date"},
            ],
        },
        {
            "name": "user_usage",
            "type": "base",
            "schema": [
                {"name": "clerk_user_id", "type": "text", "required": True},
                {"name": "month", "type": "text", "required": True},
                {"name": "count", "type": "number", "default": 0},
            ],
        },
    ]

    for col in collections:
        await create_collection(token, col)

    print("\n✅ PocketBase configurado correctamente")
    print(f"   Admin UI: {PB_URL}/_/")


if __name__ == "__main__":
    asyncio.run(main())
