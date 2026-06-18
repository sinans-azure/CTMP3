"""API routes for analytics-service."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.dependencies import get_current_user
from app.models import DashboardMetrics, InstanceMetricsPoint, CostMetricsPoint

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    claims: Annotated[dict, Depends(get_current_user)],
) -> DashboardMetrics:
    """Retrieve overall platform metrics for the admin dashboard."""
    return DashboardMetrics(
        active_instances=4,
        total_users=24,
        cpu_utilization_avg=34.8,
        active_groups=5,
        total_spend_usd=138.20,
    )


@router.get("/activity")
async def stream_activity(
    # We allow token in query param or headers for SSE since standard EventSource does not support headers
    token: str | None = Query(None, description="Optional authentication token via query parameters"),
    # claims: Annotated[dict | None, Depends(get_current_user)] = None,
) -> StreamingResponse:
    """Stream user and instance activity using Server-Sent Events (SSE)."""
    async def event_generator():
        activities = [
            {"event": "instance_state_change", "user": "Student Carol", "instance_id": "i-0abcdef1234567890", "action": "start"},
            {"event": "group_created", "user": "Admin Alice", "group_name": "Cloud Security Labs"},
            {"event": "role_assignment", "user": "Admin Alice", "target_user": "Dave Brown", "role": "Student"},
            {"event": "instance_state_change", "user": "Student Dave", "instance_id": "i-0123456789abcdef0", "action": "stop"},
            {"event": "template_generated", "user": "Trainer Bob", "role_name": "AzureMIFederatedRole"},
        ]
        
        counter = 0
        try:
            while True:
                # Loop through mock activities periodically to simulate live stream
                act = activities[counter % len(activities)]
                data = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    **act
                }
                yield f"data: {json.dumps(data)}\n\n"
                counter += 1
                await asyncio.sleep(4.0)
        except asyncio.CancelledError:
            logger.info("SSE activity stream client disconnected.")

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/metrics/instances", response_model=list[InstanceMetricsPoint])
async def get_instance_metrics(
    claims: Annotated[dict, Depends(get_current_user)],
) -> list[InstanceMetricsPoint]:
    """Retrieve time-series instance metrics (running vs stopped counts)."""
    now = datetime.utcnow()
    points = []
    
    # Generate mock time series for the last 24 hours
    for i in range(12):
        time_point = now - timedelta(hours=(12 - i) * 2)
        points.append(
            InstanceMetricsPoint(
                timestamp=time_point,
                running_count=3 + (i % 2),
                stopped_count=1 + (i % 3),
            )
        )
    return points


@router.get("/metrics/costs", response_model=list[CostMetricsPoint])
async def get_cost_metrics(
    claims: Annotated[dict, Depends(get_current_user)],
) -> list[CostMetricsPoint]:
    """Retrieve time-series cost metrics (cumulative spend)."""
    now = datetime.utcnow()
    points = []
    
    # Generate mock cumulative cost trajectory
    cumulative_spend = 50.0
    for i in range(12):
        time_point = now - timedelta(hours=(12 - i) * 2)
        cumulative_spend += 7.35 + (i * 0.4)
        points.append(
            CostMetricsPoint(
                timestamp=time_point,
                cumulative_cost_usd=round(cumulative_spend, 2),
            )
        )
    return points
