import json
import logging
import os
import stripe
from fastapi import APIRouter, Request, HTTPException, Header
from svix.webhooks import Webhook, WebhookVerificationError
from app.db.pocketbase import pb_create, pb_get_first, pb_update
from app.services.stripe_service import plan_from_product_id

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
            # Sin suscripción activa tras borrar la cuenta de Clerk: sin acceso.
            await pb_update("user_profiles", existing["id"], {"plan": "none"})
            logger.info(f"Usuario {clerk_id} eliminado en Clerk, acceso revocado")

    return {"received": True}


@router.post("/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None, alias="stripe-signature")):
    """
    Activa/actualiza el plan del usuario tras eventos de Stripe:
    - checkout.session.completed: primera suscripción, guarda stripe_customer_id y activa el plan
    - customer.subscription.updated: cambios de plan (upgrade/downgrade) o renovación
    - customer.subscription.deleted: cancelación, revoca el acceso
    """
    body = await request.body()
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    if not secret:
        logger.warning("STRIPE_WEBHOOK_SECRET no configurado: webhook de Stripe sin verificar")
        event = json.loads(body)
    else:
        try:
            event = stripe.Webhook.construct_event(body, stripe_signature, secret)
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=401, detail="Firma de webhook de Stripe inválida")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Payload inválido: {e}")

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
            logger.info(f"Suscripción actualizada para customer {customer_id}: plan={new_plan} status={status}")

    elif event_type == "customer.subscription.deleted":
        customer_id = obj.get("customer")
        existing = await pb_get_first("user_profiles", f'stripe_customer_id="{customer_id}"')
        if existing:
            await pb_update("user_profiles", existing["id"], {"plan": "none"})
            logger.info(f"Suscripción cancelada para customer {customer_id}, acceso revocado")

    return {"received": True}
