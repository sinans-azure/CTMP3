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
        active_instances=0,
        total_users=0,
        cpu_utilization_avg=0.0,
        active_groups=0,
        total_spend_usd=0.0,
    )


@router.get("/activity")
async def stream_activity(
    token: str | None = Query(None, description="Optional authentication token via query parameters"),
) -> StreamingResponse:
    """Stream user and instance activity using Server-Sent Events (SSE)."""
    async def event_generator():
        try:
            while True:
                # Yield a standard keepalive heartbeat event every 15 seconds to keep connection open
                yield ": heartbeat\n\n"
                await asyncio.sleep(15.0)
        except asyncio.CancelledError:
            logger.info("SSE activity stream client disconnected.")

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/metrics/instances", response_model=list[InstanceMetricsPoint])
async def get_instance_metrics(
    claims: Annotated[dict, Depends(get_current_user)],
) -> list[InstanceMetricsPoint]:
    """Retrieve time-series instance metrics (running vs stopped counts)."""
    return []


@router.get("/metrics/costs", response_model=list[CostMetricsPoint])
async def get_cost_metrics(
    claims: Annotated[dict, Depends(get_current_user)],
) -> list[CostMetricsPoint]:
    """Retrieve time-series cost metrics (cumulative spend)."""
    return []
