"""API routes for auth-service."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from jose import JWTError, jwt

from app.config import Settings, get_settings
from app.dependencies import _fetch_jwks, _get_signing_key, get_current_user
from app.models import (
    RoleResponse,
    TokenValidationRequest,
    TokenValidationResponse,
    UserProfile,
    LoginRequest,
    LoginResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    claims: Annotated[dict, Depends(get_current_user)],
) -> UserProfile:
    """Return the current user's profile extracted from JWT claims."""
    return UserProfile(
        sub=claims.get("sub", ""),
        name=claims.get("name", ""),
        email=claims.get("email", claims.get("preferred_username", "")),
        preferred_username=claims.get("preferred_username", ""),
        roles=claims.get("roles", []),
        groups=claims.get("groups", []),
        tenant_id=claims.get("tid", ""),
        oid=claims.get("oid", ""),
    )


@router.post("/validate", response_model=TokenValidationResponse)
async def validate_token(
    body: TokenValidationRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenValidationResponse:
    """Validate a JWT token and return its claims if valid."""
    try:
        jwks = await _fetch_jwks(settings)
        signing_key = _get_signing_key(body.token, jwks)

        claims = jwt.decode(
            body.token,
            signing_key,
            algorithms=["RS256"],
            audience=settings.token_audience,
            issuer=settings.token_issuer,
            options={
                "verify_aud": bool(settings.AZURE_CLIENT_ID),
                "verify_iss": bool(settings.AZURE_TENANT_ID),
            },
        )

        return TokenValidationResponse(valid=True, claims=claims)

    except JWTError as e:
        return TokenValidationResponse(valid=False, error=str(e))
    except Exception as e:
        logger.error("Token validation error: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Token validation service unavailable",
        )


@router.get("/roles", response_model=RoleResponse)
async def get_user_roles(
    claims: Annotated[dict, Depends(get_current_user)],
) -> RoleResponse:
    """Return the current user's application roles."""
    roles = claims.get("roles", [])
    return RoleResponse(
        user_id=claims.get("sub", ""),
        roles=roles,
        is_admin="Admin" in roles,
        is_trainer="Trainer" in roles,
        is_student="Student" in roles,
    )


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    """Authenticate users with local credentials and return profile & mock token."""
    from app.database import SessionLocal, User
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == body.username).first()
        if not user or not user.verify_password(body.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )
        
        profile = UserProfile(
            sub=user.id,
            name=user.name or user.username,
            email=user.email or "",
            preferred_username=user.username,
            roles=[user.role],
            groups=[g.id for g in user.groups],
            tenant_id="mock-tenant",
            oid=user.id
        )
        
        return LoginResponse(
            token=f"mock-{user.id}",
            user=profile
        )
    finally:
        db.close()


@router.get("/invite", response_model=LoginResponse)
async def invite(token: str = Query(..., description="Invitation/auto-login token")) -> LoginResponse:
    """Verify an invitation token and automatically sign in the user."""
    from app.database import SessionLocal, User
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.invite_token == token).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid invitation token",
            )
        
        profile = UserProfile(
            sub=user.id,
            name=user.name or user.username,
            email=user.email or "",
            preferred_username=user.username,
            roles=[user.role],
            groups=[g.id for g in user.groups],
            tenant_id="mock-tenant",
            oid=user.id
        )
        
        return LoginResponse(
            token=f"mock-{user.id}",
            user=profile
        )
    finally:
        db.close()

