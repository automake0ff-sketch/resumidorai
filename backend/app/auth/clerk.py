import os
import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()
_jwks_client: PyJWKClient | None = None


def _get_jwks():
    global _jwks_client
    issuer = os.environ.get("CLERK_ISSUER_URL")
    if not issuer:
        raise RuntimeError(
            "CLERK_ISSUER_URL no está configurada. "
            "Obtén el issuer desde el dashboard de Clerk (Settings -> API -> Issuer URL)."
        )
    if _jwks_client is None:
        _jwks_client = PyJWKClient(f"{issuer}/.well-known/jwks.json")
    return _jwks_client


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """Validate Clerk JWT token with full security checks:
    - Signature verification (RS256)
    - Expiration check
    - Issuer (iss) validation
    - Audience (aud) validation
    - Authorized Party (azp) check if present
    """
    token = credentials.credentials
    try:
        signing_key = _get_jwks().get_signing_key_from_jwt(token)
        
        # Full validation options
        issuer = os.environ.get("CLERK_ISSUER_URL")
        audience = os.environ.get("CLERK_AUDIENCE") or os.environ.get("VITE_APP_ID")
        
        decode_options = {
            "verify_exp": True,
        }
        
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            audience=audience,
            options=decode_options,
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token sin user_id (sub claim)")
        
        # Validate azp (authorized party) if present - prevents token substitution attacks
        azp = payload.get("azp")
        if azp:
            expected_azp = os.environ.get("CLERK_AUTHORIZED_PARTY")
            if expected_azp and azp != expected_azp:
                raise HTTPException(status_code=401, detail="Token azp no coincide")
        
        return {
            "user_id": user_id,
            "email": payload.get("email", ""),
            "name": payload.get("name", ""),
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidIssuerError:
        raise HTTPException(status_code=401, detail="Issuer de token inválido")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="Audiencia de token inválida")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Token inválido: {e}")
