"""API routes for billing-service."""

import logging
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])

# --- Mock Data ---
_mock_cost_records = []


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

    filtered_details = []
    total = 0.0

    for record in _mock_cost_records:
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


@router.get("/costs/group/{group_id}", response_model=GroupCostResponse)
async def get_costs_by_group(
    group_id: str,
    claims: Annotated[dict, Depends(get_current_user)],
) -> GroupCostResponse:
    """Retrieve cost aggregated for a specific training group."""
    filtered_details = []
    total = 0.0

    for record in _mock_cost_records:
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

    # Return empty list if no record but return successfully
    return GroupCostResponse(
        group_id=group_id,
        total_cost=round(total, 2),
        currency="USD",
        details=filtered_details,
    )


@router.get("/costs/student/{student_id}", response_model=StudentCostResponse)
async def get_costs_by_student(
    student_id: str,
    claims: Annotated[dict, Depends(get_current_user)],
) -> StudentCostResponse:
    """Retrieve cost aggregated for a specific student."""
    filtered_details = []
    total = 0.0

    for record in _mock_cost_records:
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


@router.get("/summary", response_model=BillingSummaryResponse)
async def get_billing_summary(
    claims: Annotated[dict, Depends(get_current_user)],
) -> BillingSummaryResponse:
    """Retrieve a summary overview for the billing dashboard."""
    # Sum all mock costs
    total = sum(r["amount"] for r in _mock_cost_records)
    
    # Calculate group totals to find the top spending group
    group_totals: dict[str, float] = {}
    for r in _mock_cost_records:
        group_totals[r["group_id"]] = group_totals.get(r["group_id"], 0.0) + r["amount"]
    
    top_group = max(group_totals, key=group_totals.get) if group_totals else "N/A"
    
    # Unique students/groups count in database
    unique_students = len(set(r["student_id"] for r in _mock_cost_records))
    unique_groups = len(set(r["group_id"] for r in _mock_cost_records))
    
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
