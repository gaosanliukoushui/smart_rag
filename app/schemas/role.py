"""Role schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class PermissionResponse(BaseModel):
    """Schema for permission response."""

    id: UUID
    resource: str
    action: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class RoleBase(BaseModel):
    """Schema for role base."""

    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    """Schema for creating a role."""

    pass


class RoleUpdate(BaseModel):
    """Schema for updating a role."""

    name: Optional[str] = None
    description: Optional[str] = None


class RoleResponse(RoleBase):
    """Schema for role response."""

    id: UUID
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoleWithPermissions(RoleResponse):
    """Schema for role with permissions."""

    permissions: list[PermissionResponse] = []


class RolePermissionUpdate(BaseModel):
    """Schema for updating role permissions."""

    permission_ids: list[UUID]
