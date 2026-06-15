"""
Middleware de autenticación con Clerk.
Verifica JWT tokens en cada request protegido.
"""

import os
import httpx
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient

security = HTTPBearer()

_jwks_client: PyJWKClient | None = None


def get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        clerk_issuer = os.environ["CLERK_ISSUER_URL"]  # ej: https://your-app.clerk.accounts.dev
        _jwks_client = PyJWKClient(f"{clerk_issuer}/.well-known/jwks.json")
    return _jwks_client


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """
    Dependency que verifica el JWT de Clerk y devuelve el payload.
    Uso: user = Depends(get_current_user)
    """
    token = credentials.credentials

    try:
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_exp": True},
        )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido: sin user_id")

        return {
            "user_id": user_id,
            "email": payload.get("email", ""),
            "name": payload.get("name", ""),
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Token inválido: {str(e)}")
