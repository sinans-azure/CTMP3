"""API routes for billing-service."""

import logging
import json
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_current_user
from app.models import (
    CostResponse,
    CostDetail,
    GroupCostResponse,
    StudentCostResponse,
    BillingSummaryResponse,
)
from app.database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])


def get_db_costs(db, user_oid=None):
    from app.database import EC2Instance, TrainingGroup
    
    query = db.query(EC2Instance)
    if user_oid:
        # Get groups managed by the trainer
        group_ids = [g.id for g in db.query(TrainingGroup).filter(TrainingGroup.trainer_id == user_oid).all()]
        if not group_ids:
            return []
        query = query.filter(EC2Instance.group_id.in_(group_ids))
        
    db_instances = query.all()
    now = datetime.utcnow()
    
    records = []
    for inst in db_instances:
        launch_time = inst.launch_time or now
        duration_hours = (now - launch_time).total_seconds() / 3600.0
        # If duration is negative or very small, default to 0.1 hour
        if duration_hours < 0:
            duration_hours = 0.1
        
        # Calculate cost
        rate = 0.02 if inst.state == "running" else 0.005
        amount = duration_hours * rate
        
        records.append({
            "id": inst.id,
            "group_id": inst.group_id,
            "student_id": inst.student_id or "system",
            "date": launch_time,
            "amount": round(amount, 4)
        })
    return records


@router.get("/costs", response_model=CostResponse)
async def get_costs(
    claims: Annotated[dict, Depends(get_current_user)],
    start_date: datetime | None = Query(None, description="Start date of range"),
    end_date: datetime | None = Query(None, description="End date of range"),
) -> CostResponse:
    """Retrieve aggregated costs, optionally filtered by a date range."""
    # Defaults
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    roles = claims.get("roles", [])
    is_admin = "Admin" in roles
    user_oid = claims.get("oid") or claims.get("sub", "")
    
    db = SessionLocal()
    try:
        if is_admin:
            records = get_db_costs(db)
        else:
            records = get_db_costs(db, user_oid=user_oid)
            
        filtered_details = []
        total = 0.0

        for record in records:
            if start_date <= record["date"] <= end_date:
                amount = record["amount"]
                total += amount
                filtered_details.append(
                    CostDetail(
                        date=record["date"],
                        amount=amount,
                        currency="USD",
                        resource_type="EC2",
                    )
                )

        return CostResponse(
            total_cost=round(total, 2),
            currency="USD",
            start_date=start_date,
            end_date=end_date,
            details=filtered_details,
        )
    finally:
        db.close()


@router.get("/costs/group/{group_id}", response_model=GroupCostResponse)
async def get_costs_by_group(
    group_id: str,
    claims: Annotated[dict, Depends(get_current_user)],
) -> GroupCostResponse:
    """Retrieve cost aggregated for a specific training group."""
    roles = claims.get("roles", [])
    is_admin = "Admin" in roles
    user_oid = claims.get("oid") or claims.get("sub", "")
    
    db = SessionLocal()
    try:
        # Check if trainer owns the group
        if not is_admin:
            from app.database import TrainingGroup
            group = db.query(TrainingGroup).filter(TrainingGroup.id == group_id, TrainingGroup.trainer_id == user_oid).first()
            if not group:
                return GroupCostResponse(group_id=group_id, total_cost=0.0, currency="USD", details=[])
                
        records = get_db_costs(db)
        filtered_details = []
        total = 0.0

        for record in records:
            if record["group_id"] == group_id:
                amount = record["amount"]
                total += amount
                filtered_details.append(
                    CostDetail(
                        date=record["date"],
                        amount=amount,
                        currency="USD",
                        resource_type="EC2",
                    )
                )

        return GroupCostResponse(
            group_id=group_id,
            total_cost=round(total, 2),
            currency="USD",
            details=filtered_details,
        )
    finally:
        db.close()


@router.get("/costs/student/{student_id}", response_model=StudentCostResponse)
async def get_costs_by_student(
    student_id: str,
    claims: Annotated[dict, Depends(get_current_user)],
) -> StudentCostResponse:
    """Retrieve cost aggregated for a specific student."""
    roles = claims.get("roles", [])
    is_admin = "Admin" in roles
    user_oid = claims.get("oid") or claims.get("sub", "")
    
    db = SessionLocal()
    try:
        if not is_admin:
            # Check if student is in trainer's groups
            from app.database import user_group_association, TrainingGroup
            group_ids = [g.id for g in db.query(TrainingGroup).filter(TrainingGroup.trainer_id == user_oid).all()]
            is_student_in_group = False
            if group_ids:
                is_student_in_group = db.query(user_group_association).filter(
                    user_group_association.c.user_id == student_id,
                    user_group_association.c.group_id.in_(group_ids)
                ).first() is not None
                
            if not is_student_in_group:
                return StudentCostResponse(student_id=student_id, total_cost=0.0, currency="USD", details=[])
                
        records = get_db_costs(db)
        filtered_details = []
        total = 0.0

        for record in records:
            if record["student_id"] == student_id:
                amount = record["amount"]
                total += amount
                filtered_details.append(
                    CostDetail(
                        date=record["date"],
                        amount=amount,
                        currency="USD",
                        resource_type="EC2",
                    )
                )

        return StudentCostResponse(
            student_id=student_id,
            total_cost=round(total, 2),
            currency="USD",
            details=filtered_details,
        )
    finally:
        db.close()


@router.get("/summary", response_model=BillingSummaryResponse)
async def get_billing_summary(
    claims: Annotated[dict, Depends(get_current_user)],
) -> BillingSummaryResponse:
    """Retrieve a summary overview for the billing dashboard."""
    roles = claims.get("roles", [])
    is_admin = "Admin" in roles
    user_oid = claims.get("oid") or claims.get("sub", "")
    
    db = SessionLocal()
    try:
        if is_admin:
            records = get_db_costs(db)
            
            from app.database import TrainingGroup, User
            unique_groups = db.query(TrainingGroup).count()
            unique_students = db.query(User).filter(User.role == "Student").count()
        else:
            records = get_db_costs(db, user_oid=user_oid)
            
            from app.database import TrainingGroup, user_group_association
            group_ids = [g.id for g in db.query(TrainingGroup).filter(TrainingGroup.trainer_id == user_oid).all()]
            unique_groups = len(group_ids)
            if group_ids:
                unique_students = db.query(user_group_association.c.user_id).filter(
                    user_group_association.c.group_id.in_(group_ids)
                ).distinct().count()
            else:
                unique_students = 0
                
        total = sum(r["amount"] for r in records)
        
        # Calculate group totals to find the top spending group
        group_totals: dict[str, float] = {}
        for r in records:
            group_totals[r["group_id"]] = group_totals.get(r["group_id"], 0.0) + r["amount"]
        
        top_group = max(group_totals, key=group_totals.get) if group_totals else "N/A"
        
        monthly_budget = 500.0
        utilization = (total / monthly_budget) * 100.0

        return BillingSummaryResponse(
            total_platform_cost=round(total, 2),
            active_groups_count=unique_groups,
            active_students_count=unique_students,
            top_spending_group_id=top_group,
            currency="USD",
            monthly_budget=monthly_budget,
            budget_utilization_percentage=round(utilization, 2),
        )
    finally:
        db.close()

