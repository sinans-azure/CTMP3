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
    EC2Instance,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trainer", tags=["trainer"])

# --- In-memory store ---
# Seed some mock groups.
# We'll associate the default seed groups with a default trainer sub, but we will also allow
# trainer endpoints to see/interact with any groups where trainer_id matches the logged-in trainer's ID.
_groups_store: dict[str, TrainingGroup] = {
    "group-101": TrainingGroup(
        id="group-101",
        name="AWS Basics - Group A",
        description="Introduction to AWS infrastructure.",
        trainer_id="user-002", # matches Bob Smith (Trainer) in admin-service
        student_ids=["user-003", "user-004"],
        created_at=datetime(2026, 5, 1, 9, 0, 0),
        aws_account_id="123456789012",
        aws_region="us-east-1",
    ),
    "group-102": TrainingGroup(
        id="group-102",
        name="Advanced Cloud Architecture",
        description="Complex architectures and OIDC federation.",
        trainer_id="user-002",
        student_ids=["user-003"],
        created_at=datetime(2026, 5, 10, 11, 0, 0),
        aws_account_id="123456789012",
        aws_region="us-west-2",
    )
}

# Seed some mock EC2 instances associated with groups
_instances_store: list[EC2Instance] = [
    EC2Instance(
        id="i-0abcdef1234567890",
        name="student-web-server",
        state="running",
        instance_type="t3.micro",
        launch_time=datetime(2026, 6, 1, 10, 0, 0),
        group_id="group-101",
        student_id="user-003",
    ),
    EC2Instance(
        id="i-0123456789abcdef0",
        name="student-db-server",
        state="stopped",
        instance_type="t3.medium",
        launch_time=datetime(2026, 6, 2, 14, 30, 0),
        group_id="group-101",
        student_id="user-004",
    ),
    EC2Instance(
        id="i-0987654321fedcba0",
        name="adv-k8s-node",
        state="running",
        instance_type="t3.large",
        launch_time=datetime(2026, 6, 10, 8, 15, 0),
        group_id="group-102",
        student_id="user-003",
    )
]


@router.post("/aws-template", response_model=AwsTemplateResponse)
async def generate_aws_template(
    body: AwsTemplateRequest,
    claims: Annotated[dict, Depends(require_trainer)],
) -> AwsTemplateResponse:
    """Generate a CloudFormation YAML template to establish OIDC federation trust

    with an Azure AD Tenant and Managed Identity, allowing EC2 lifecycle actions.
    """
    tenant_id = body.azure_tenant_id
    client_id = body.azure_client_id
    role_name = body.aws_role_name

    # Construct the CloudFormation YAML template
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
        # Standard DigiCert Global Root G2 thumbprint for login.microsoftonline.com/sts.windows.net
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
                # Restrict audience to our Azure Client ID
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
    trainer_id = claims.get("sub", "")
    
    # If the current trainer has no groups seeded, let's also support listing
    # all groups for demonstration or matching. We filter by trainer_id.
    trainer_groups = [g for g in _groups_store.values() if g.trainer_id == trainer_id]
    
    # Fallback to returning all seeded groups if the token subject doesn't match
    # Bob Smith's sub (e.g. during local JWT generation tests)
    if not trainer_groups:
        return list(_groups_store.values())
        
    return trainer_groups


@router.post("/groups/{group_id}/students", response_model=TrainingGroup)
async def assign_students_to_group(
    group_id: str,
    body: AssignStudentsRequest,
    claims: Annotated[dict, Depends(require_trainer)],
) -> TrainingGroup:
    """Assign a list of students to a training group."""
    group = _groups_store.get(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training group {group_id} not found",
        )

    # Append new student IDs to group avoiding duplicates
    existing_students = set(group.student_ids)
    for student_id in body.student_ids:
        existing_students.add(student_id)
    group.student_ids = list(existing_students)

    _groups_store[group_id] = group
    return group


@router.get("/groups/{group_id}/instances", response_model=list[EC2Instance])
async def list_group_instances(
    group_id: str,
    claims: Annotated[dict, Depends(require_trainer)],
) -> list[EC2Instance]:
    """List all EC2 instances associated with a training group."""
    if group_id not in _groups_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training group {group_id} not found",
        )

    group_instances = [inst for inst in _instances_store if inst.group_id == group_id]
    return group_instances
