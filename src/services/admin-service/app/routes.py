"""API routes for admin-service."""

import logging
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_current_user, require_admin
from app.models import (
    AuditLogEntry,
    AuditLogResponse,
    CreateGroupRequest,
    RoleAssignmentRequest,
    RoleAssignmentResponse,
    TrainingGroup,
    UserSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

# --- In-memory stores ---

_users_store: dict[str, UserSummary] = {
    "user-001": UserSummary(
        id="user-001",
        name="Alice Johnson",
        email="alice@contoso.com",
        roles=["Admin"],
        created_at=datetime(2026, 1, 15, 9, 0, 0),
    ),
    "user-002": UserSummary(
        id="user-002",
        name="Bob Smith",
        email="bob@contoso.com",
        roles=["Trainer"],
        created_at=datetime(2026, 2, 1, 10, 30, 0),
    ),
    "user-003": UserSummary(
        id="user-003",
        name="Carol Williams",
        email="carol@contoso.com",
        roles=["Student"],
        created_at=datetime(2026, 3, 10, 14, 0, 0),
    ),
    "user-004": UserSummary(
        id="user-004",
        name="Dave Brown",
        email="dave@contoso.com",
        roles=["Student"],
        created_at=datetime(2026, 3, 12, 8, 45, 0),
    ),
}

_audit_log: list[AuditLogEntry] = []

_groups_store: dict[str, TrainingGroup] = {}


def _add_audit_entry(
    actor_id: str, actor_name: str, action: str,
    resource_type: str = "", resource_id: str = "",
    details: dict | None = None,
) -> None:
    """Append an entry to the in-memory audit log."""
    entry = AuditLogEntry(
        id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        actor_id=actor_id,
        actor_name=actor_name,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
    )
    _audit_log.insert(0, entry)


@router.get("/users", response_model=list[UserSummary])
async def list_users(
    claims: Annotated[dict, Depends(require_admin)],
    role: str | None = Query(None, description="Filter by role"),
) -> list[UserSummary]:
    """List all users, optionally filtered by role."""
    users = list(_users_store.values())

    if role:
        users = [u for u in users if role in u.roles]

    return users


@router.post(
    "/users/{user_id}/role",
    response_model=RoleAssignmentResponse,
    status_code=status.HTTP_200_OK,
)
async def assign_role(
    user_id: str,
    body: RoleAssignmentRequest,
    claims: Annotated[dict, Depends(require_admin)],
) -> RoleAssignmentResponse:
    """Assign a role to a user."""
    user = _users_store.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    role_value = body.role.value
    if role_value in user.roles:
        return RoleAssignmentResponse(
            user_id=user_id,
            role=role_value,
            assigned=False,
            message=f"User already has role {role_value}",
        )

    user.roles.append(role_value)

    _add_audit_entry(
        actor_id=claims.get("sub", ""),
        actor_name=claims.get("name", ""),
        action="assign_role",
        resource_type="user",
        resource_id=user_id,
        details={"role": role_value},
    )

    return RoleAssignmentResponse(
        user_id=user_id,
        role=role_value,
        assigned=True,
        message=f"Role {role_value} assigned to user {user_id}",
    )


@router.get("/audit-log", response_model=AuditLogResponse)
async def get_audit_log(
    claims: Annotated[dict, Depends(require_admin)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> AuditLogResponse:
    """Retrieve paginated audit log."""
    total = len(_audit_log)
    start = (page - 1) * page_size
    end = start + page_size
    entries = _audit_log[start:end]

    return AuditLogResponse(
        entries=entries,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/groups",
    response_model=TrainingGroup,
    status_code=status.HTTP_201_CREATED,
)
async def create_group(
    body: CreateGroupRequest,
    claims: Annotated[dict, Depends(require_admin)],
) -> TrainingGroup:
    """Create a new training group."""
    group_id = str(uuid.uuid4())
    group = TrainingGroup(
        id=group_id,
        name=body.name,
        description=body.description,
        trainer_id=body.trainer_id,
        aws_account_id=body.aws_account_id,
        aws_region=body.aws_region,
        created_at=datetime.utcnow(),
    )
    _groups_store[group_id] = group

    _add_audit_entry(
        actor_id=claims.get("sub", ""),
        actor_name=claims.get("name", ""),
        action="create_group",
        resource_type="group",
        resource_id=group_id,
        details={"name": body.name},
    )

    return group


@router.get("/groups", response_model=list[TrainingGroup])
async def list_groups(
    claims: Annotated[dict, Depends(require_admin)],
) -> list[TrainingGroup]:
    """List all training groups."""
    return list(_groups_store.values())
