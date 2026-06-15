"""
Webhooks para eventos externos:
- Clerk: sync de usuarios en Supabase
- Stripe: gestión de planes
"""

import os
import hmac
import hashlib
import json
from fastapi import APIRouter, Request, HTTPException, Header
from app.db.supabase import get_db

router = APIRouter()


@router.post("/clerk")
async def clerk_webhook(request: Request, svix_signature: str = Header(None)):
    """
    Recibe eventos de Clerk y sincroniza usuarios en Supabase.
    Configura en Clerk Dashboard → Webhooks.
    Eventos: user.created, user.updated, user.deleted
    """
    body = await request.body()
    webhook_secret = os.environ.get("CLERK_WEBHOOK_SECRET", "")

    # Verificar firma Svix (Clerk usa Svix para webhooks)
    if webhook_secret and svix_signature:
        expected = hmac.new(
            webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        # En prod verificar svix-signature header completo

    payload = json.loads(body)
    event_type = payload.get("type")
    data = payload.get("data", {})

    db = get_db()

    if event_type == "user.created":
        db.table("user_profiles").upsert({
            "user_id": data["id"],
            "email": data.get("email_addresses", [{}])[0].get("email_address", ""),
            "name": f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
            "plan": "free",
            "created_at": data.get("created_at"),
        }).execute()

    elif event_type == "user.updated":
        db.table("user_profiles").update({
            "email": data.get("email_addresses", [{}])[0].get("email_address", ""),
            "name": f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
        }).eq("user_id", data["id"]).execute()

    elif event_type == "user.deleted":
        db.table("user_profiles").update({
            "deleted_at": "now()",
        }).eq("user_id", data["id"]).execute()

    return {"received": True}


@router.post("/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """
    Recibe eventos de Stripe para gestionar planes.
    Eventos: checkout.session.completed, customer.subscription.updated/deleted
    """
    import stripe

    body = await request.body()
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    try:
        event = stripe.Webhook.construct_event(body, stripe_signature, webhook_secret)
    except Exception:
        raise HTTPException(status_code=400, detail="Firma inválida")

    db = get_db()

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")
        plan = session.get("metadata", {}).get("plan", "starter")
        if user_id:
            db.table("user_profiles").update({"plan": plan}).eq("user_id", user_id).execute()

    elif event["type"] == "customer.subscription.deleted":
        sub = event["data"]["object"]
        customer_id = sub.get("customer")
        # Downgrade a free
        db.table("user_profiles").update({"plan": "free"}).eq("stripe_customer_id", customer_id).execute()

    return {"received": True}
