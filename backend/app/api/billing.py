import logging
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth.clerk import get_current_user
from app.services.stripe_service import create_checkout_session, create_billing_portal_session
from app.services.job_processor import ensure_user_profile
from app.db.firestore_client import pb_get_first

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

    # El JWT de Clerk por defecto NO incluye email/name (solo 'sub'), así que
    # leemos el email real desde el perfil en Firestore, sincronizado por el
    # webhook de Clerk. Si por algún motivo el perfil no existe aún, lo creamos
    # como red de seguridad (aunque normalmente ya lo crea ensure_user_profile
    # en /api/summaries la primera vez que el usuario interactúa).
    await ensure_user_profile(user["user_id"], user.get("email", ""), user.get("name", ""))
    profile = await pb_get_first("user_profiles", f'clerk_user_id="{user["user_id"]}"')
    raw_email = profile.get("email", "") if profile else ""
    # No mandamos a Stripe el email sintético de placeholder que usa
    # ensure_user_profile cuando el webhook de Clerk aún no sincronizó el
    # email real; en ese caso Stripe Checkout lo pedirá directamente en su
    # propio formulario, que es preferible a generar un recibo con un email
    # inválido tipo "user_xyz@pending.resumidorai.internal".
    email = "" if raw_email.endswith("@pending.resumidorai.internal") else raw_email

    try:
        url = create_checkout_session(
            plan=request.plan,
            clerk_user_id=user["user_id"],
            email=email,
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
