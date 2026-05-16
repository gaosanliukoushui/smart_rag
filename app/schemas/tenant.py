"""Tenant schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TenantBase(BaseModel):
    """Schema for tenant base."""

    name: str = Field(max_length=100)
    description: Optional[str] = None


class TenantCreate(TenantBase):
    """Schema for creating a tenant."""

    slug: Optional[str] = Field(default=None, max_length=50)


class TenantUpdate(BaseModel):
    """Schema for updating a tenant."""

    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    settings: Optional[dict] = None


class TenantResponse(TenantBase):
    """Schema for tenant response."""

    id: UUID
    slug: str
    is_active: bool
    settings: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TenantUserRoleResponse(BaseModel):
    """Schema for user role assignment within a tenant."""

    user_id: UUID
    tenant_id: UUID
    role_id: UUID
    role_name: str

    model_config = {"from_attributes": True}


class AssignRoleRequest(BaseModel):
    """Schema for assigning a role to a user."""

    role_id: UUID
