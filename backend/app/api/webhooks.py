import json
import logging
import os
from fastapi import APIRouter, Request, HTTPException, Header
from svix.webhooks import Webhook, WebhookVerificationError
from app.db.pocketbase import pb_create, pb_get_first, pb_update

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "ResumidorAI API"}


@router.post("/clerk")
async def clerk_webhook(
    request: Request,
    svix_id: str = Header(None, alias="svix-id"),
    svix_timestamp: str = Header(None, alias="svix-timestamp"),
    svix_signature: str = Header(None, alias="svix-signature"),
):
    """
    Sincroniza usuarios de Clerk con PocketBase.
    Verifica la firma Svix para confirmar que el request viene realmente de Clerk.
    """
    body = await request.body()
    secret = os.environ.get("CLERK_WEBHOOK_SECRET", "")

    if not secret:
        logger.warning("CLERK_WEBHOOK_SECRET no configurado: webhook sin verificar")
    else:
        if not (svix_id and svix_timestamp and svix_signature):
            raise HTTPException(status_code=400, detail="Headers Svix faltantes")
        try:
            wh = Webhook(secret)
            wh.verify(body, {
                "svix-id": svix_id,
                "svix-timestamp": svix_timestamp,
                "svix-signature": svix_signature,
            })
        except WebhookVerificationError:
            raise HTTPException(status_code=401, detail="Firma de webhook inválida")

    payload = json.loads(body)
    event_type = payload.get("type")
    data = payload.get("data", {})

    clerk_id = data.get("id")
    if not clerk_id:
        raise HTTPException(status_code=400, detail="Payload sin id de usuario")

    emails = data.get("email_addresses", [{}])
    email = emails[0].get("email_address", "") if emails else ""
    name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()

    if event_type == "user.created":
        existing = await pb_get_first("user_profiles", f'clerk_user_id="{clerk_id.replace(chr(34), chr(92)+chr(34))}"')
        if not existing:
            await pb_create("user_profiles", {
                "clerk_user_id": clerk_id,
                "email": email,
                "name": name,
                "plan": "free",
            })
            logger.info(f"Perfil creado para usuario {clerk_id}")

    elif event_type == "user.updated":
        existing = await pb_get_first("user_profiles", f'clerk_user_id="{clerk_id.replace(chr(34), chr(92)+chr(34))}"')
        if existing:
            await pb_update("user_profiles", existing["id"], {
                "email": email,
                "name": name,
            })
            logger.info(f"Perfil actualizado para usuario {clerk_id}")

    elif event_type == "user.deleted":
        existing = await pb_get_first("user_profiles", f'clerk_user_id="{clerk_id.replace(chr(34), chr(92)+chr(34))}"')
        if existing:
            await pb_update("user_profiles", existing["id"], {"plan": "free"})
            logger.info(f"Usuario {clerk_id} eliminado en Clerk, plan reseteado")

    return {"received": True}
