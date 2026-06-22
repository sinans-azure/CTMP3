"""API routes for trainer-service."""

import logging
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import require_trainer
from app.models import (
    AwsTemplateRequest,
    AwsTemplateResponse,
    TrainingGroup,
    AssignStudentsRequest,
    CreateGroupAndStudentsRequest,
    CreateGroupAndStudentsResponse,
    EC2Instance,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trainer", tags=["trainer"])

# --- Database routes ---

@router.post("/aws-template", response_model=AwsTemplateResponse)
async def generate_aws_template(
    body: AwsTemplateRequest,
    claims: Annotated[dict, Depends(require_trainer)],
) -> AwsTemplateResponse:
    """Generate a CloudFormation YAML template to establish OIDC federation trust."""
    tenant_id = body.azure_tenant_id
    client_id = body.azure_client_id
    role_name = body.aws_role_name

    cf_template = f"""AWSTemplateFormatVersion: '2010-09-09'
Description: OIDC Trust Federation with Azure Active Directory (Entra ID) for EC2 management.

Parameters:
  AzureTenantID:
    Type: String
    Default: "{tenant_id}"
    Description: The Azure AD (Entra ID) Tenant ID.
  AzureClientID:
    Type: String
    Default: "{client_id}"
    Description: The Client ID of the Azure Managed Identity to trust.

Resources:
  AzureOIDCProvider:
    Type: AWS::IAM::OIDCProvider
    Properties:
      Url: !Sub "https://sts.windows.net/${{AzureTenantID}}/"
      ClientIdList:
        - !Ref AzureClientID
      ThumbprintList:
        - df3c24f9bfd666761b268073fe06d1cc8d4f82a4

  AzureFederatedRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: "{role_name}"
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Federated: !Ref AzureOIDCProvider
            Action: sts:AssumeRoleWithWebIdentity
          Condition:
            StringEquals:
              sts.windows.net/{tenant_id}/:aud: !Ref AzureClientID
      Policies:
        - PolicyName: EC2LifecycleManagement
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - ec2:StartInstances
                  - ec2:StopInstances
                  - ec2:RebootInstances
                  - ec2:DescribeInstances
                  - ec2:DescribeInstanceStatus
                Resource: '*'

Outputs:
  RoleArn:
    Description: ARN of the federated IAM Role to assume.
    Value: !GetAtt AzureFederatedRole.Arn
"""
    return AwsTemplateResponse(template_yaml=cf_template)


@router.get("/groups", response_model=list[TrainingGroup])
async def get_trainer_groups(
    claims: Annotated[dict, Depends(require_trainer)],
) -> list[TrainingGroup]:
    """Retrieve all training groups assigned to the currently authenticated trainer."""
    from app.database import SessionLocal, TrainingGroup as DbGroup
    db = SessionLocal()
    try:
        trainer_id = claims.get("sub", "")
        db_groups = db.query(DbGroup).filter(DbGroup.trainer_id == trainer_id).all()
        
        # Fallback to all groups if none assigned to this trainer (e.g. for demo)
        if not db_groups:
            db_groups = db.query(DbGroup).all()
            
        result = []
        for g in db_groups:
            result.append(TrainingGroup(
                id=g.id,
                name=g.name,
                description=g.description or "",
                trainer_id=g.trainer_id or "",
                student_ids=[s.id for s in g.students],
                created_at=g.created_at,
                aws_account_id=g.aws_account_id or "",
                aws_region=g.aws_region or "us-east-1"
            ))
        return result
    finally:
        db.close()


@router.post("/groups", response_model=CreateGroupAndStudentsResponse)
async def create_group_with_students(
    body: CreateGroupAndStudentsRequest,
    claims: Annotated[dict, Depends(require_trainer)]
) -> CreateGroupAndStudentsResponse:
    """Create a new training group and generate its student user accounts in one step."""
    from app.database import SessionLocal, User as DbUser, TrainingGroup as DbGroup, EC2Instance as DbInstance
    from app.models import GeneratedStudentCredentials
    import string
    import random
    
    db = SessionLocal()
    try:
        group_id = f"group-{uuid.uuid4().hex[:6]}"
        db_group = DbGroup(
            id=group_id,
            name=body.name,
            description=body.description,
            trainer_id=claims.get("sub"),
            aws_account_id=body.aws_account_id,
            aws_region=body.aws_region
        )
        db.add(db_group)
        db.commit()
        
        created_students = []
        students_to_create = []
        
        # Parse email strings
        for email in body.student_emails:
            email = email.strip()
            if not email:
                continue
            username = email.split("@")[0]
            name = username.replace(".", " ").title()
            students_to_create.append((username, email, name))
            
        # Parse auto-generation count
        for i in range(body.auto_generate_count):
            rand_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
            username = f"student_{i+1}_{rand_suffix}"
            email = f"{username}@training.sneakertail.online"
            name = f"Student {i+1} ({rand_suffix})"
            students_to_create.append((username, email, name))
            
        for username, email, name in students_to_create:
            student_id = f"user-{uuid.uuid4().hex[:6]}"
            raw_password = "CTMP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            invite_token = str(uuid.uuid4())
            
            db_user = DbUser(
                id=student_id,
                username=username,
                email=email,
                hashed_password=DbUser.hash_password(raw_password),
                name=name,
                role="Student",
                invite_token=invite_token
            )
            db.add(db_user)
            db.commit()
            
            # Associate user with group
            db_group.students.append(db_user)
            db.commit()
            
            # Seed a mock EC2 instance for the student
            inst_id = f"i-{uuid.uuid4().hex[:17]}"
            db_instance = DbInstance(
                id=inst_id,
                name=f"sandbox-vm-{username}",
                state="stopped",
                instance_type="t3.micro",
                group_id=group_id,
                student_id=student_id
            )
            db.add(db_instance)
            db.commit()
            
            login_link = f"http://localhost:3000/login?token={invite_token}"
            
            created_students.append(GeneratedStudentCredentials(
                id=student_id,
                username=username,
                password=raw_password,
                name=name,
                invite_token=invite_token,
                login_link=login_link
            ))
            
        db.refresh(db_group)
        
        return CreateGroupAndStudentsResponse(
            group_id=group_id,
            name=db_group.name,
            student_count=len(db_group.students),
            created_students=created_students
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create group and students: {str(e)}"
        )
    finally:
        db.close()


@router.post("/groups/{group_id}/students", response_model=TrainingGroup)
async def assign_students_to_group(
    group_id: str,
    body: AssignStudentsRequest,
    claims: Annotated[dict, Depends(require_trainer)],
) -> TrainingGroup:
    """Assign existing students to a training group."""
    from app.database import SessionLocal, TrainingGroup as DbGroup, User as DbUser
    db = SessionLocal()
    try:
        group = db.query(DbGroup).filter(DbGroup.id == group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Training group {group_id} not found",
            )
            
        for s_id in body.student_ids:
            student = db.query(DbUser).filter(DbUser.id == s_id).first()
            if student and student not in group.students:
                group.students.append(student)
                
        db.commit()
        db.refresh(group)
        
        return TrainingGroup(
            id=group.id,
            name=group.name,
            description=group.description or "",
            trainer_id=group.trainer_id or "",
            student_ids=[s.id for s in group.students],
            created_at=group.created_at,
            aws_account_id=group.aws_account_id or "",
            aws_region=group.aws_region or "us-east-1"
        )
    finally:
        db.close()


@router.get("/groups/{group_id}/instances", response_model=list[EC2Instance])
async def list_group_instances(
    group_id: str,
    claims: Annotated[dict, Depends(require_trainer)],
) -> list[EC2Instance]:
    """List all EC2 instances associated with a training group."""
    from app.database import SessionLocal, TrainingGroup as DbGroup
    db = SessionLocal()
    try:
        group = db.query(DbGroup).filter(DbGroup.id == group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Training group {group_id} not found",
            )
            
        result = []
        for inst in group.instances:
            result.append(EC2Instance(
                id=inst.id,
                name=inst.name or "",
                state=inst.state,
                instance_type=inst.instance_type,
                launch_time=inst.launch_time,
                group_id=inst.group_id,
                student_id=inst.student_id or ""
            ))
        return result
    finally:
        db.close()
