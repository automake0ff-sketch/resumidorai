"""
Integración de Stripe para ResumidorAI.

Modelo de negocio: sin plan gratis. Todo usuario nuevo se crea con plan
"trial" (acceso limitado de cortesía) y debe suscribirse a Starter o Pro
para usar el servicio de forma continuada.

Product IDs reales del usuario:
  - Starter: prod_UiLxrL4q3jo0d5
  - Pro:     prod_UiLxoqpYqemCDN

Stripe Checkout se crea contra un Price ID (no un Product ID directamente),
así que en runtime resolvemos el primer Price activo de cada Product.
"""
import os
import logging
import stripe

logger = logging.getLogger(__name__)

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

PRODUCT_IDS = {
    "starter": os.environ.get("STRIPE_PRODUCT_STARTER", "prod_UiLxrL4q3jo0d5"),
    "pro": os.environ.get("STRIPE_PRODUCT_PRO", "prod_UiLxoqpYqemCDN"),
}

PLAN_LIMITS = {"trial": 3, "starter": 50, "pro": 200}

_price_cache: dict[str, str] = {}


def get_price_id_for_plan(plan: str) -> str:
    """Resuelve el Price ID activo de un Product ID. Se cachea en memoria
    porque los precios no cambian en caliente durante la vida del proceso."""
    if plan in _price_cache:
        return _price_cache[plan]

    product_id = PRODUCT_IDS.get(plan)
    if not product_id:
        raise ValueError(f"Plan desconocido: {plan}")

    prices = stripe.Price.list(product=product_id, active=True, limit=1)
    if not prices.data:
        raise ValueError(f"El producto {product_id} ({plan}) no tiene ningún precio activo en Stripe")

    price_id = prices.data[0].id
    _price_cache[plan] = price_id
    return price_id


def create_checkout_session(plan: str, clerk_user_id: str, email: str, success_url: str, cancel_url: str) -> str:
    """Crea una sesión de Stripe Checkout y devuelve la URL a la que redirigir al usuario."""
    price_id = get_price_id_for_plan(plan)

    params = {
        "mode": "subscription",
        "payment_method_types": ["card"],
        "line_items": [{"price": price_id, "quantity": 1}],
        "client_reference_id": clerk_user_id,
        "metadata": {"clerk_user_id": clerk_user_id, "plan": plan},
        "subscription_data": {"metadata": {"clerk_user_id": clerk_user_id, "plan": plan}},
        "success_url": success_url,
        "cancel_url": cancel_url,
    }
    if email:
        # Si no hay email confiable, omitimos el parámetro y dejamos que
        # Stripe Checkout lo pida directamente en su propio formulario.
        params["customer_email"] = email

    session = stripe.checkout.Session.create(**params)
    return session.url


def create_billing_portal_session(stripe_customer_id: str, return_url: str) -> str:
    """Crea una sesión del portal de facturación de Stripe (cancelar, cambiar tarjeta, etc.)."""
    session = stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=return_url,
    )
    return session.url


def plan_from_product_id(product_id: str) -> str | None:
    for plan, pid in PRODUCT_IDS.items():
        if pid == product_id:
            return plan
    return None
