"""API routes for admin-service."""

import logging
import uuid
import json
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


def _add_audit_entry(
    db,
    actor_id: str, actor_name: str, action: str,
    resource_type: str = "", resource_id: str = "",
    details: dict | None = None,
) -> None:
    """Write an entry to the database audit log."""
    from app.database import AuditLog
    entry = AuditLog(
        id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        actor_id=actor_id,
        actor_name=actor_name,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=json.dumps(details or {}),
    )
    db.add(entry)
    db.commit()


@router.get("/users", response_model=list[UserSummary])
async def list_users(
    claims: Annotated[dict, Depends(require_admin)],
    role: str | None = Query(None, description="Filter by role"),
) -> list[UserSummary]:
    """List all users, optionally filtered by role."""
    from app.database import SessionLocal, User as DbUser
    db = SessionLocal()
    try:
        query = db.query(DbUser)
        if role:
            query = query.filter(DbUser.role == role)
        db_users = query.all()
        
        return [
            UserSummary(
                id=u.id,
                name=u.name or "",
                email=u.email or "",
                roles=[u.role],
                created_at=u.created_at or datetime.utcnow(),
            )
            for u in db_users
        ]
    finally:
        db.close()


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
    from app.database import SessionLocal, User as DbUser
    db = SessionLocal()
    try:
        user = db.query(DbUser).filter(DbUser.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )

        role_value = body.role.value
        if user.role == role_value:
            return RoleAssignmentResponse(
                user_id=user_id,
                role=role_value,
                assigned=False,
                message=f"User already has role {role_value}",
            )

        old_role = user.role
        user.role = role_value
        db.commit()

        _add_audit_entry(
            db=db,
            actor_id=claims.get("sub", ""),
            actor_name=claims.get("name", ""),
            action="assign_role",
            resource_type="user",
            resource_id=user_id,
            details={"old_role": old_role, "new_role": role_value},
        )

        return RoleAssignmentResponse(
            user_id=user_id,
            role=role_value,
            assigned=True,
            message=f"Role {role_value} assigned to user {user_id}",
        )
    finally:
        db.close()


@router.get("/audit-log", response_model=AuditLogResponse)
async def get_audit_log(
    claims: Annotated[dict, Depends(require_admin)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> AuditLogResponse:
    """Retrieve paginated audit log."""
    from app.database import SessionLocal, AuditLog as DbAuditLog
    db = SessionLocal()
    try:
        total = db.query(DbAuditLog).count()
        start = (page - 1) * page_size
        
        # Order by timestamp desc
        db_entries = db.query(DbAuditLog).order_by(DbAuditLog.timestamp.desc()).offset(start).limit(page_size).all()
        
        entries = []
        for entry in db_entries:
            try:
                details_dict = json.loads(entry.details) if entry.details else {}
            except Exception:
                details_dict = {"raw_value": entry.details} if entry.details else {}
                
            entries.append(
                AuditLogEntry(
                    id=entry.id,
                    timestamp=entry.timestamp or datetime.utcnow(),
                    actor_id=entry.actor_id or "system",
                    actor_name=entry.actor_name or "",
                    action=entry.action,
                    resource_type=entry.resource_type or "",
                    resource_id=entry.resource_id or "",
                    details=details_dict,
                )
            )
            
        return AuditLogResponse(
            entries=entries,
            total=total,
            page=page,
            page_size=page_size,
        )
    finally:
        db.close()


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
    from app.database import SessionLocal, TrainingGroup as DbGroup, User as DbUser
    db = SessionLocal()
    try:
        group_id = f"group-{uuid.uuid4().hex[:6]}"
        
        # Verify trainer exists if trainer_id is provided
        if body.trainer_id:
            trainer = db.query(DbUser).filter(DbUser.id == body.trainer_id).first()
            if not trainer:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Trainer user {body.trainer_id} does not exist"
                )
                
        group = DbGroup(
            id=group_id,
            name=body.name,
            description=body.description,
            trainer_id=body.trainer_id or None,
            aws_account_id=body.aws_account_id,
            aws_region=body.aws_region or "us-east-1",
            created_at=datetime.utcnow(),
        )
        db.add(group)
        db.commit()
        db.refresh(group)

        _add_audit_entry(
            db=db,
            actor_id=claims.get("sub", ""),
            actor_name=claims.get("name", ""),
            action="create_group",
            resource_type="group",
            resource_id=group_id,
            details={"name": body.name},
        )

        return TrainingGroup(
            id=group.id,
            name=group.name,
            description=group.description or "",
            trainer_id=group.trainer_id or "",
            student_ids=[s.id for s in group.students],
            created_at=group.created_at,
            aws_account_id=group.aws_account_id or "",
            aws_region=group.aws_region or "us-east-1",
        )
    finally:
        db.close()


@router.get("/groups", response_model=list[TrainingGroup])
async def list_groups(
    claims: Annotated[dict, Depends(require_admin)],
) -> list[TrainingGroup]:
    """List all training groups."""
    from app.database import SessionLocal, TrainingGroup as DbGroup
    db = SessionLocal()
    try:
        db_groups = db.query(DbGroup).all()
        return [
            TrainingGroup(
                id=g.id,
                name=g.name,
                description=g.description or "",
                trainer_id=g.trainer_id or "",
                student_ids=[s.id for s in g.students],
                created_at=g.created_at,
                aws_account_id=g.aws_account_id or "",
                aws_region=g.aws_region or "us-east-1",
            )
            for g in db_groups
        ]
    finally:
        db.close()
