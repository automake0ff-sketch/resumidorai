import logging
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth.clerk import get_current_user
from app.services.stripe_service import create_checkout_session, create_billing_portal_session
from app.db.pocketbase import pb_get_first

logger = logging.getLogger(__name__)
router = APIRouter()

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")


class CheckoutRequest(BaseModel):
    plan: str  # "starter" | "pro"


class CheckoutResponse(BaseModel):
    checkout_url: str


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(request: CheckoutRequest, user: dict = Depends(get_current_user)):
    """Crea una sesión de Stripe Checkout para suscribirse a Starter o Pro."""
    if request.plan not in ("starter", "pro"):
        raise HTTPException(status_code=400, detail="Plan inválido. Usa 'starter' o 'pro'.")

    try:
        url = create_checkout_session(
            plan=request.plan,
            clerk_user_id=user["user_id"],
            email=user.get("email", ""),
            success_url=f"{FRONTEND_URL}/dashboard?checkout=success",
            cancel_url=f"{FRONTEND_URL}/pricing?checkout=cancelled",
        )
        return CheckoutResponse(checkout_url=url)
    except Exception as e:
        logger.error(f"Error creando checkout: {e}")
        raise HTTPException(status_code=500, detail="No se pudo iniciar el pago. Inténtalo de nuevo.")


@router.post("/portal", response_model=CheckoutResponse)
async def create_portal(user: dict = Depends(get_current_user)):
    """Crea una sesión del portal de Stripe para gestionar/cancelar la suscripción."""
    profile = await pb_get_first("user_profiles", f'clerk_user_id="{user["user_id"]}"')
    if not profile or not profile.get("stripe_customer_id"):
        raise HTTPException(status_code=400, detail="No tienes una suscripción activa todavía.")

    try:
        url = create_billing_portal_session(
            stripe_customer_id=profile["stripe_customer_id"],
            return_url=f"{FRONTEND_URL}/dashboard",
        )
        return CheckoutResponse(checkout_url=url)
    except Exception as e:
        logger.error(f"Error creando portal de facturación: {e}")
        raise HTTPException(status_code=500, detail="No se pudo abrir el portal de facturación.")
