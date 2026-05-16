"""Tenant user management API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, get_tenant_from_header, get_user_tenant_role, get_current_active_user
from app.models import User, Tenant, UserRole, Role
from app.schemas.auth import UserResponse
from app.schemas.tenant import TenantUserRoleResponse, AssignRoleRequest, TenantResponse

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    data: dict,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Create a new tenant (any authenticated user)."""
    from app.models import Tenant
    import uuid as uuid_lib

    tenant = Tenant(
        name=data.get("name", "New Workspace"),
        slug=data.get("slug", f"ws-{uuid_lib.uuid4().hex[:8]}"),
        description=data.get("description"),
    )
    db.add(tenant)
    db.flush()

    admin_role = db.execute(select(Role).where(Role.name == "admin")).scalar_one_or_none()
    if not admin_role:
        admin_role = Role(name="admin", description="Administrator", is_system=True)
        db.add(admin_role)
        db.flush()

    user_role = UserRole(
        user_id=current_user.id,
        tenant_id=tenant.id,
        role_id=admin_role.id,
    )
    db.add(user_role)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Get tenant details."""
    tenant = db.execute(select(Tenant).where(Tenant.id == tenant_id)).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    user_role = get_user_tenant_role(current_user.id, tenant_id, db)
    if not user_role and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return tenant


@router.get("/{tenant_id}/users", response_model=list[TenantUserRoleResponse])
async def list_tenant_users(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """List all users belonging to a tenant."""
    tenant = get_tenant_from_header(tenant_id, db)
    user_role = get_user_tenant_role(current_user.id, tenant_id, db)
    if not user_role and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    user_roles = (
        db.execute(
            select(UserRole)
            .where(UserRole.tenant_id == tenant_id)
            .options(joinedload(UserRole.role))
        )
        .scalars()
        .all()
    )

    result = []
    for ur in user_roles:
        result.append(
            TenantUserRoleResponse(
                user_id=ur.user_id,
                tenant_id=ur.tenant_id,
                role_id=ur.role_id,
                role_name=ur.role.name if ur.role else "",
            )
        )
    return result


@router.post("/{tenant_id}/users/{user_id}/roles", status_code=status.HTTP_201_CREATED)
async def assign_user_role(
    tenant_id: UUID,
    user_id: UUID,
    data: AssignRoleRequest,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Assign a role to a user within a tenant (admin only in that tenant)."""
    requesting_role = get_user_tenant_role(current_user.id, tenant_id, db)
    if not requesting_role or requesting_role.name != "admin":
        if not current_user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role in tenant required")

    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    role = db.execute(select(Role).where(Role.id == data.role_id)).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    existing = (
        db.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.tenant_id == tenant_id,
                UserRole.role_id == data.role_id,
            )
        )
        .scalar_one_or_none()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already has this role")

    user_role = UserRole(user_id=user_id, tenant_id=tenant_id, role_id=data.role_id)
    db.add(user_role)
    db.commit()
    return {"message": "Role assigned"}


@router.delete("/{tenant_id}/users/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_role(
    tenant_id: UUID,
    user_id: UUID,
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """Remove a role from a user within a tenant (admin only)."""
    requesting_role = get_user_tenant_role(current_user.id, tenant_id, db)
    if not requesting_role or requesting_role.name != "admin":
        if not current_user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role in tenant required")

    user_role = (
        db.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.tenant_id == tenant_id,
                UserRole.role_id == role_id,
            )
        )
        .scalar_one_or_none()
    )
    if not user_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User role assignment not found")

    db.delete(user_role)
    db.commit()
