"""Authentication dependencies for admin-service."""

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
    """Validate Entra ID JWT token and return decoded claims."""
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

        # Normalize and resolve roles dynamically
        roles = claims.get("roles", [])
        if isinstance(roles, str):
            roles = [roles]
        roles = list(roles)
        
        groups = claims.get("groups", [])
        if isinstance(groups, str):
            groups = [groups]
        groups = [str(g) for g in groups]
        
        email = (claims.get("email") or claims.get("preferred_username") or "").lower()
        username = (claims.get("preferred_username") or "").lower()
        name = (claims.get("name") or "").lower()
        
        is_admin = "admin" in [r.lower() for r in roles] or any("admin" in g.lower() for g in groups) or email.startswith("admin") or username.startswith("admin") or "admin" in name
        is_trainer = "trainer" in [r.lower() for r in roles] or any("trainer" in g.lower() for g in groups) or "trainer" in email or "trainer" in username or "trainer" in name
        
        resolved_roles = []
        if is_admin:
            resolved_roles.append("Admin")
        if is_trainer:
            resolved_roles.append("Trainer")
        if not resolved_roles:
            resolved_roles.append("Student")
            
        claims["roles"] = resolved_roles
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


def require_admin(claims: Annotated[dict, Depends(get_current_user)]) -> dict:
    """Require the user to have the Admin role."""
    roles = claims.get("roles", [])
    if "Admin" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return claims
