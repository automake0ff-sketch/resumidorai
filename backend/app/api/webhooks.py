import json
from fastapi import APIRouter, Request
from app.db.pocketbase import pb_create, pb_get_first, pb_update

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "ResumidorAI API"}


@router.post("/clerk")
async def clerk_webhook(request: Request):
    """Sincroniza usuarios de Clerk con PocketBase."""
    body = await request.body()
    payload = json.loads(body)
    event_type = payload.get("type")
    data = payload.get("data", {})

    clerk_id = data.get("id")
    emails = data.get("email_addresses", [{}])
    email = emails[0].get("email_address", "") if emails else ""
    name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()

    if event_type == "user.created":
        await pb_create("user_profiles", {
            "clerk_user_id": clerk_id,
            "email": email,
            "name": name,
            "plan": "free",
        })

    elif event_type == "user.updated":
        existing = await pb_get_first("user_profiles", f'clerk_user_id="{clerk_id}"')
        if existing:
            await pb_update("user_profiles", existing["id"], {
                "email": email,
                "name": name,
            })

    return {"received": True}
