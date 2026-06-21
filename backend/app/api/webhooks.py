import json
import logging
import os
import stripe
from fastapi import APIRouter, Request, HTTPException, Header
from svix.webhooks import Webhook, WebhookVerificationError
from app.db.firestore_client import pb_create, pb_get_first, pb_update
from app.services.stripe_service import plan_from_product_id

logger = logging.getLogger(__name__)
router = APIRouter()


def _require_webhook_secret(secret: str, provider: str) -> None:
    """Fail-closed: in production, missing webhook secret returns 500/503."""
    if not secret:
        if os.environ.get("NODE_ENV") == "production" or os.environ.get("ENV") == "production":
            raise HTTPException(
                status_code=503,
                detail=f"{provider} webhook misconfigurado: variable de entorno no esta definida"
            )
        logger.warning(f"{provider} webhook secret no configurado: continuando en modo desarrollo")


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
    Sincroniza usuarios de Clerk con Firestore.
    Verifica la firma Svix para confirmar que el request viene realmente de Clerk.
    FAIL-CLOSED: Si falta el secreto en producción, rechaza todos los eventos.
    """
    body = await request.body()
    secret = os.environ.get("CLERK_WEBHOOK_SECRET", "")

    _require_webhook_secret(secret, "CLERK_WEBHOOK_SECRET")

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
        raise HTTPException(status_code=401, detail="Firma de webhook invalida")

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
                "plan": "trial",
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
            await pb_update("user_profiles", existing["id"], {"plan": "none"})
            logger.info(f"Usuario {clerk_id} eliminado en Clerk, acceso revocado")

    return {"received": True}


@router.post("/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None, alias="stripe-signature")):
    """
    Activa/actualiza el plan del usuario tras eventos de Stripe:
    - checkout.session.completed: primera suscripcion, guarda stripe_customer_id y activa el plan
    - customer.subscription.updated: cambios de plan (upgrade/downgrade) o renovacion
    - customer.subscription.deleted: cancelacion, revoca el acceso

    FAIL-CLOSED: Si falta el secreto en producción, rechaza todos los eventos.
    """
    body = await request.body()
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    _require_webhook_secret(secret, "STRIPE_WEBHOOK_SECRET")

    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Header stripe-signature faltante")

    try:
        event = stripe.Webhook.construct_event(body, stripe_signature, secret)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=401, detail="Firma de webhook de Stripe invalida")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Payload invalido: {e}")

    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        clerk_user_id = obj.get("client_reference_id") or obj.get("metadata", {}).get("clerk_user_id")
        plan = obj.get("metadata", {}).get("plan")
        customer_id = obj.get("customer")

        if not clerk_user_id:
            logger.warning("checkout.session.completed sin clerk_user_id, ignorando")
            return {"received": True}

        existing = await pb_get_first("user_profiles", f'clerk_user_id="{clerk_user_id}"')
        update = {"plan": plan or "starter", "stripe_customer_id": customer_id}
        if existing:
            await pb_update("user_profiles", existing["id"], update)
        else:
            await pb_create("user_profiles", {"clerk_user_id": clerk_user_id, "email": "", "name": "", **update})
        logger.info(f"Checkout completado: usuario {clerk_user_id} -> plan {plan}")

    elif event_type == "customer.subscription.updated":
        customer_id = obj.get("customer")
        status = obj.get("status")
        items = obj.get("items", {}).get("data", [])
        product_id = items[0]["price"]["product"] if items else None
        plan = plan_from_product_id(product_id) if product_id else None

        existing = await pb_get_first("user_profiles", f'stripe_customer_id="{customer_id}"')
        if existing and plan:
            new_plan = plan if status == "active" else "none"
            await pb_update("user_profiles", existing["id"], {"plan": new_plan})
            logger.info(f"Suscripcion actualizada para customer {customer_id}: plan={new_plan} status={status}")

    elif event_type == "customer.subscription.deleted":
        customer_id = obj.get("customer")
        existing = await pb_get_first("user_profiles", f'stripe_customer_id="{customer_id}"')
        if existing:
            await pb_update("user_profiles", existing["id"], {"plan": "none"})
            logger.info(f"Suscripcion cancelada para customer {customer_id}, acceso revocado")

    return {"received": True}
