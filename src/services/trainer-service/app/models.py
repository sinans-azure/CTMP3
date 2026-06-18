"""Pydantic models for trainer-service."""

from datetime import datetime
from pydantic import BaseModel, Field


class AwsTemplateRequest(BaseModel):
    """Request schema for generating AWS CloudFormation template."""

    azure_tenant_id: str = Field(..., description="Azure Active Directory Tenant ID")
    azure_client_id: str = Field(..., description="Azure Managed Identity Client ID to trust")
    aws_role_name: str = Field(default="AzureMIFederatedRole", description="Name of the AWS IAM Role to create")


class AwsTemplateResponse(BaseModel):
    """Response schema containing the generated CloudFormation template."""

    template_yaml: str = Field(..., description="CloudFormation YAML template")


class TrainingGroup(BaseModel):
    """Details of a training group."""

    id: str = Field(..., description="Group ID")
    name: str = Field(..., description="Group name")
    description: str = Field(default="", description="Group description")
    trainer_id: str = Field(..., description="Assigned trainer ID")
    student_ids: list[str] = Field(default_factory=list, description="Assigned student IDs")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    aws_account_id: str = Field(default="", description="Associated AWS account ID")
    aws_region: str = Field(default="us-east-1", description="AWS region")


class AssignStudentsRequest(BaseModel):
    """Request to assign students to a training group."""

    student_ids: list[str] = Field(..., description="List of student user IDs to assign")


class EC2Instance(BaseModel):
    """Details of an EC2 instance."""

    id: str = Field(..., description="EC2 Instance ID")
    name: str = Field(..., description="Instance name/tag")
    state: str = Field(..., description="State of the instance (running, stopped, etc.)")
    instance_type: str = Field(..., description="Instance type (e.g. t3.micro)")
    launch_time: datetime = Field(default_factory=datetime.utcnow)
    group_id: str = Field(..., description="Associated group ID")
    student_id: str = Field(default="", description="Assigned student ID")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
