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

# --- Database integration ---

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
    from app.database import SessionLocal, User as DbUser
    db = SessionLocal()
    try:
        student_id = claims.get("sub", "")
        student = db.query(DbUser).filter(DbUser.id == student_id).first()
        if not student:
            return []
            
        result = []
        for g in student.groups:
            result.append(TrainingGroup(
                id=g.id,
                name=g.name,
                description=g.description or "",
                trainer_id=g.trainer_id or "",
                created_at=g.created_at,
                aws_region=g.aws_region or "us-east-1"
            ))
        return result
    finally:
        db.close()


@router.get("/instances", response_model=list[EC2Instance])
async def get_visible_instances(
    claims: Annotated[dict, Depends(require_student)],
) -> list[EC2Instance]:
    """Get EC2 instances visible to the current student based on group assignments."""
    from app.database import SessionLocal, User as DbUser
    db = SessionLocal()
    try:
        student_id = claims.get("sub", "")
        student = db.query(DbUser).filter(DbUser.id == student_id).first()
        if not student:
            return []
            
        assigned_group_ids = [g.id for g in student.groups]
        
        from app.database import EC2Instance as DbInstance
        db_instances = db.query(DbInstance).filter(DbInstance.group_id.in_(assigned_group_ids)).all()
        
        # Fallback to all instances if no groups assigned (demo helper)
        if not db_instances:
            db_instances = db.query(DbInstance).all()
            
        result = []
        for inst in db_instances:
            result.append(EC2Instance(
                id=inst.id,
                name=inst.name or "",
                state=inst.state,
                instance_type=inst.instance_type,
                launch_time=inst.launch_time,
                group_id=inst.group_id
            ))
        return result
    finally:
        db.close()


@router.post("/instances/{instance_id}/action", response_model=InstanceActionResponse)
async def dispatch_instance_action(
    instance_id: str,
    body: InstanceActionRequest,
    claims: Annotated[dict, Depends(require_student)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> InstanceActionResponse:
    """Dispatch an EC2 lifecycle action to the Azure Storage Queue or execute immediately in mock mode."""
    from app.database import SessionLocal, EC2Instance as DbInstance, TrainingGroup as DbGroup
    db = SessionLocal()
    try:
        instance = db.query(DbInstance).filter(DbInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"EC2 Instance {instance_id} not found",
            )

        student_id = claims.get("sub", "")
        group_id = instance.group_id
        
        # Verify access
        from app.database import User as DbUser
        student = db.query(DbUser).filter(DbUser.id == student_id).first()
        allowed = False
        if student:
            allowed = group_id in [g.id for g in student.groups]
        if not allowed and "Admin" in claims.get("roles", []):
            allowed = True
            
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to perform actions on instances in this training group.",
            )

        group = db.query(DbGroup).filter(DbGroup.id == group_id).first()
        aws_region = group.aws_region if group else "us-east-1"
        aws_role_arn = f"arn:aws:iam::{group.aws_account_id if group else '123456789012'}:role/AzureMIFederatedRole"

        # Prepare message body
        action_message = {
            "instance_id": instance_id,
            "action": body.action.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "student_id": student_id,
            "group_id": group_id,
            "aws_region": aws_region,
            "aws_role_arn": aws_role_arn
        }

        queue_client = _get_queue_client(settings)
        if queue_client:
            try:
                import base64
                msg_bytes = json.dumps(action_message).encode('utf-8')
                msg_base64 = base64.b64encode(msg_bytes).decode('utf-8')
                queue_client.send_message(msg_base64)
                logger.info("Successfully sent message to queue for instance %s", instance_id)
                
                # Update status in db for immediate visual progress
                if body.action.value == "start":
                    instance.state = "pending"
                elif body.action.value == "stop":
                    instance.state = "stopping"
                elif body.action.value == "terminate":
                    instance.state = "shutting-down"
                db.commit()
                
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
            logger.warning("Azure Storage Queue not configured. Running in MOCK mode.")
            if body.action.value == "start":
                instance.state = "running"
            elif body.action.value == "stop":
                instance.state = "stopped"
            elif body.action.value == "terminate":
                instance.state = "terminated"
            db.commit()

            return InstanceActionResponse(
                instance_id=instance_id,
                action=body.action.value,
                status="mocked",
                message=f"Azure storage queue not configured. Simulated action '{body.action.value}' successfully.",
            )
    finally:
        db.close()


@router.get("/instances/{instance_id}/status", response_model=InstanceStatusResponse)
async def get_instance_status(
    instance_id: str,
    claims: Annotated[dict, Depends(require_student)],
) -> InstanceStatusResponse:
    """Get status of a specific EC2 instance."""
    from app.database import SessionLocal, EC2Instance as DbInstance
    db = SessionLocal()
    try:
        instance = db.query(DbInstance).filter(DbInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"EC2 Instance {instance_id} not found",
            )

        return InstanceStatusResponse(
            instance_id=instance.id,
            state=instance.state,
        )
    finally:
        db.close()

