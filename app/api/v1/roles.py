"""Role management API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_admin_user, get_current_active_user
from app.models import User, Role, Permission, UserRole
from app.schemas.role import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleWithPermissions,
    PermissionResponse,
    RolePermissionUpdate,
)

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("", response_model=list[RoleResponse])
async def list_roles(
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """List all roles."""
    roles = db.execute(select(Role).order_by(Role.is_system.desc(), Role.name)).scalars().all()
    return roles


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_admin_user)] = None,
):
    """Create a new custom role (admin only)."""
    existing = db.execute(select(Role).where(Role.name == data.name)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role already exists")

    role = Role(name=data.name, description=data.description, is_system=False)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.get("/{role_id}", response_model=RoleWithPermissions)
async def get_role(
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Get role with its permissions."""
    role = db.execute(select(Role).where(Role.id == role_id)).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_admin_user)] = None,
):
    """Update a custom role (admin only)."""
    role = db.execute(select(Role).where(Role.id == role_id)).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify system role")

    if data.name is not None:
        role.name = data.name
    if data.description is not None:
        role.description = data.description

    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.get("/{role_id}/permissions", response_model=list[PermissionResponse])
async def get_role_permissions(
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Get all permissions assigned to a role."""
    role = db.execute(select(Role).where(Role.id == role_id)).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role.permissions


@router.put("/{role_id}/permissions", response_model=RoleWithPermissions)
async def update_role_permissions(
    role_id: UUID,
    data: RolePermissionUpdate,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_admin_user)] = None,
):
    """Update permissions for a role (admin only)."""
    role = db.execute(select(Role).where(Role.id == role_id)).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify system role permissions")

    perms = db.execute(
        select(Permission).where(Permission.id.in_(data.permission_ids))
    ).scalars().all()
    role.permissions = perms
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.get("/permissions/all", response_model=list[PermissionResponse])
async def list_all_permissions(
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """List all available permissions."""
    perms = db.execute(select(Permission)).scalars().all()
    return perms
