"""API routes for student-service."""

import json
import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from azure.storage.queue import QueueClient
from azure.identity import DefaultAzureCredential

from app.config import get_settings, Settings
from app.dependencies import require_student
from app.models import (
    TrainingGroup,
    EC2Instance,
    InstanceActionRequest,
    InstanceActionResponse,
    InstanceStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/student", tags=["student"])

# --- In-memory mock data (matches trainer-service) ---
_groups_store: dict[str, TrainingGroup] = {
    "group-101": TrainingGroup(
        id="group-101",
        name="AWS Basics - Group A",
        description="Introduction to AWS infrastructure.",
        trainer_id="user-002",
        created_at=datetime(2026, 5, 1, 9, 0, 0),
        aws_region="us-east-1",
    ),
    "group-102": TrainingGroup(
        id="group-102",
        name="Advanced Cloud Architecture",
        description="Complex architectures and OIDC federation.",
        trainer_id="user-002",
        created_at=datetime(2026, 5, 10, 11, 0, 0),
        aws_region="us-west-2",
    )
}

# Seeded mapping from groups to student IDs
_group_student_map = {
    "group-101": ["user-003", "user-004"],
    "group-102": ["user-003"],
}

# Seeded EC2 instances
_instances_store: dict[str, EC2Instance] = {
    "i-0abcdef1234567890": EC2Instance(
        id="i-0abcdef1234567890",
        name="student-web-server",
        state="running",
        instance_type="t3.micro",
        launch_time=datetime(2026, 6, 1, 10, 0, 0),
        group_id="group-101",
    ),
    "i-0123456789abcdef0": EC2Instance(
        id="i-0123456789abcdef0",
        name="student-db-server",
        state="stopped",
        instance_type="t3.medium",
        launch_time=datetime(2026, 6, 2, 14, 30, 0),
        group_id="group-101",
    ),
    "i-0987654321fedcba0": EC2Instance(
        id="i-0987654321fedcba0",
        name="adv-k8s-node",
        state="running",
        instance_type="t3.large",
        launch_time=datetime(2026, 6, 10, 8, 15, 0),
        group_id="group-102",
    )
}


def _get_queue_client(settings: Settings) -> QueueClient | None:
    """Initialize Azure Queue Client based on connection string or Managed Identity."""
    try:
        if settings.AZURE_STORAGE_CONNECTION_STRING:
            logger.info("Initializing QueueClient via Connection String.")
            return QueueClient.from_connection_string(
                conn_str=settings.AZURE_STORAGE_CONNECTION_STRING,
                queue_name=settings.AZURE_STORAGE_QUEUE_NAME,
            )
        elif settings.AZURE_STORAGE_QUEUE_URL:
            logger.info("Initializing QueueClient via Managed Identity URL.")
            credential = DefaultAzureCredential()
            return QueueClient(
                account_url=settings.AZURE_STORAGE_QUEUE_URL,
                queue_name=settings.AZURE_STORAGE_QUEUE_NAME,
                credential=credential,
            )
    except Exception as e:
        logger.error("Failed to initialize Azure Queue Client: %s", str(e))
    return None


@router.get("/groups", response_model=list[TrainingGroup])
async def get_student_groups(
    claims: Annotated[dict, Depends(require_student)],
) -> list[TrainingGroup]:
    """Get training groups assigned to the current student."""
    student_id = claims.get("sub", "")
    
    # Filter groups where student is assigned
    student_groups = []
    for group_id, student_ids in _group_student_map.items():
        if student_id in student_ids:
            if group_id in _groups_store:
                student_groups.append(_groups_store[group_id])

    # Fallback to all groups if no matches found (for development/mock testing)
    if not student_groups:
        return list(_groups_store.values())

    return student_groups


@router.get("/instances", response_model=list[EC2Instance])
async def get_visible_instances(
    claims: Annotated[dict, Depends(require_student)],
) -> list[EC2Instance]:
    """Get EC2 instances visible to the current student based on group assignments."""
    student_id = claims.get("sub", "")

    # Get student's assigned group IDs
    assigned_group_ids = [
        group_id for group_id, student_ids in _group_student_map.items()
        if student_id in student_ids
    ]

    # Filter instances belonging to these groups
    visible_instances = [
        inst for inst in _instances_store.values()
        if inst.group_id in assigned_group_ids
    ]

    # Fallback to all instances if no groups matched (development/mock testing)
    if not visible_instances:
        return list(_instances_store.values())

    return visible_instances


@router.post("/instances/{instance_id}/action", response_model=InstanceActionResponse)
async def dispatch_instance_action(
    instance_id: str,
    body: InstanceActionRequest,
    claims: Annotated[dict, Depends(require_student)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> InstanceActionResponse:
    """Dispatch an EC2 lifecycle action (start, stop, reboot, terminate) to the Azure Storage Queue."""
    # Validate instance exists
    instance = _instances_store.get(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EC2 Instance {instance_id} not found",
        )

    # Validate student belongs to the group of this instance
    student_id = claims.get("sub", "")
    group_id = instance.group_id
    allowed_students = _group_student_map.get(group_id, [])
    
    # Check if student is authorized (with fallback if list is empty for mock tests)
    if allowed_students and student_id not in allowed_students and "Admin" not in claims.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to perform actions on instances in this training group.",
        )

    # Prepare message body
    action_message = {
        "instance_id": instance_id,
        "action": body.action.value,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "student_id": student_id,
        "group_id": group_id,
        "aws_region": _groups_store.get(group_id).aws_region if group_id in _groups_store else "us-east-1",
        "aws_role_arn": f"arn:aws:iam::123456789012:role/AzureMIFederatedRole" # Mock target Role ARN
    }

    # Dispatch to Storage Queue
    queue_client = _get_queue_client(settings)
    if queue_client:
        try:
            # Send message (base64 encoded as required by standard Queue storage trigger for functions)
            import base64
            msg_bytes = json.dumps(action_message).encode('utf-8')
            msg_base64 = base64.b64encode(msg_bytes).decode('utf-8')
            queue_client.send_message(msg_base64)
            logger.info("Successfully sent message to queue for instance %s", instance_id)
            
            # Update state in memory for immediate UI feedback (simulated progress)
            if body.action == "start":
                instance.state = "pending"
            elif body.action == "stop":
                instance.state = "stopping"
            elif body.action == "terminate":
                instance.state = "shutting-down"
            
            return InstanceActionResponse(
                instance_id=instance_id,
                action=body.action.value,
                status="dispatched",
                message=f"Action '{body.action.value}' dispatched successfully to Azure queue.",
            )
        except Exception as e:
            logger.error("Failed to send message to Azure Storage Queue: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not queue action: {str(e)}",
            )
    else:
        # Fallback/Mock mode when Azure Queue config is not provided
        logger.warning("Azure Storage Queue not configured. Running in MOCK mode.")
        if body.action == "start":
            instance.state = "running"
        elif body.action == "stop":
            instance.state = "stopped"
        elif body.action == "terminate":
            instance.state = "terminated"

        return InstanceActionResponse(
            instance_id=instance_id,
            action=body.action.value,
            status="mocked",
            message=f"Azure storage queue not configured. Simulated action '{body.action.value}' successfully.",
        )


@router.get("/instances/{instance_id}/status", response_model=InstanceStatusResponse)
async def get_instance_status(
    instance_id: str,
    claims: Annotated[dict, Depends(require_student)],
) -> InstanceStatusResponse:
    """Get status of a specific EC2 instance."""
    instance = _instances_store.get(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EC2 Instance {instance_id} not found",
        )

    return InstanceStatusResponse(
        instance_id=instance.id,
        state=instance.state,
    )
