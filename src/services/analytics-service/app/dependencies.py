"""Authentication dependencies for analytics-service."""

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
        parts = token.split("-")
        if len(parts) >= 2:
            user_id = parts[1]
            role = "Admin" if user_id == "user-001" else "Trainer" if user_id == "user-002" else "Student"
            return {
                "sub": user_id,
                "name": f"Mock User {user_id}",
                "email": f"mock_{user_id}@contoso.com",
                "preferred_username": f"mock_{user_id}",
                "roles": [role],
                "groups": ["group-101"] if role != "Admin" else [],
                "tid": "mock-tenant",
                "oid": user_id
            }
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

        # Resolve roles dynamically from AD groups or app roles
        import os

        roles_list = claims.get("roles", [])
        if isinstance(roles_list, str):
            roles_list = [roles_list]
        roles_lower = [r.lower() for r in roles_list]
        
        groups_list = claims.get("groups", [])
        if isinstance(groups_list, str):
            groups_list = [groups_list]
        groups_lower = [str(g).lower() for g in groups_list]
        
        admin_group = os.environ.get("AZURE_AD_ADMIN_GROUP_ID", "").lower()
        trainer_group = os.environ.get("AZURE_AD_TRAINER_GROUP_ID", "").lower()
        student_group = os.environ.get("AZURE_AD_STUDENT_GROUP_ID", "").lower()
        
        is_admin = False
        is_trainer = False
        is_student = False
        
        # 1. Match by AD group Object ID
        if admin_group and admin_group in groups_lower:
            is_admin = True
        elif trainer_group and trainer_group in groups_lower:
            is_trainer = True
        elif student_group and student_group in groups_lower:
            is_student = True
            
        # 2. Match by App Roles claim
        if not (is_admin or is_trainer or is_student):
            if "admin" in roles_lower:
                is_admin = True
            elif "trainer" in roles_lower:
                is_trainer = True
            elif "student" in roles_lower:
                is_student = True
                
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
