"""Authentication dependencies for JWT validation against Entra ID."""

import logging
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

security = HTTPBearer()

_jwks_cache: dict | None = None


async def _fetch_jwks(settings: Settings) -> dict:
    """Fetch and cache JWKS from Azure AD endpoint."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(settings.jwks_uri)
        response.raise_for_status()
        _jwks_cache = response.json()
        return _jwks_cache


def _get_signing_key(token: str, jwks: dict) -> dict:
    """Extract the correct signing key from JWKS based on token header kid."""
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token header missing key ID (kid)",
        )

    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unable to find matching signing key",
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """Validate Entra ID JWT token and return decoded claims.

    This dependency:
    1. Extracts the Bearer token from Authorization header
    2. Fetches JWKS from Azure AD (or queries PostgreSQL if mock-)
    3. Validates signature, expiry, issuer, and audience
    4. Returns decoded claims dict
    """
    token = credentials.credentials

    if token.startswith("mock-"):
        from app.database import SessionLocal, User
        parts = token.split("-")
        if len(parts) >= 2:
            user_id = parts[1]
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    return {
                        "sub": user.id,
                        "name": user.name,
                        "email": user.email,
                        "preferred_username": user.username,
                        "roles": [user.role],
                        "groups": [g.id for g in user.groups],
                        "tid": "mock-tenant",
                        "oid": user.id
                    }
            finally:
                db.close()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid mock token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        jwks = await _fetch_jwks(settings)
        signing_key = _get_signing_key(token, jwks)

        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=settings.token_audience,
            issuer=settings.token_issuer,
            options={
                "verify_aud": bool(settings.AZURE_CLIENT_ID),
                "verify_iss": bool(settings.AZURE_TENANT_ID),
            },
        )

        return claims

    except JWTError as e:
        logger.warning("JWT validation failed: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except httpx.HTTPError as e:
        logger.error("Failed to fetch JWKS: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to validate token: identity provider unavailable",
        )


def clear_jwks_cache() -> None:
    """Clear the cached JWKS data. Useful for testing or key rotation."""
    global _jwks_cache
    _jwks_cache = None
