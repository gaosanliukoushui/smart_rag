"""API dependency injection."""

import uuid
from typing import Annotated, Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import get_db as _get_db_session
from app.core.security import decode_access_token
from app.models import User, Tenant, UserRole, Role
from app.services.error_tracker import error_tracker


def get_db() -> Generator[Session, None, None]:
    """Database session dependency."""
    yield from _get_db_session()


def get_settings_dep() -> Settings:
    """Settings dependency."""
    return get_settings()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme)] = None,
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate user from JWT token."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = db.execute(select(User).where(User.id == uuid.UUID(user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure the current user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Ensure the current user has admin privileges."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user


async def get_current_tenant(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> Optional[Tenant]:
    """Extract tenant from JWT token."""
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        return None

    return db.execute(select(Tenant).where(Tenant.id == uuid.UUID(tenant_id))).scalar_one_or_none()


async def get_tenant_from_header(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db),
) -> Tenant:
    """Resolve tenant from the current authenticated user's JWT token.

    The token is automatically decoded via the get_current_active_user dependency
    chain, making the tenant available without requiring an explicit header or
    path parameter on each endpoint.
    """
    user_role = (
        db.execute(
            select(UserRole)
            .where(UserRole.user_id == current_user.id)
            .order_by(UserRole.created_at.asc())
            .limit(1)
        )
        .scalar_one_or_none()
    )
    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tenant workspace found for current user",
        )

    tenant = db.execute(select(Tenant).where(Tenant.id == user_role.tenant_id)).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    if not tenant.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant is disabled")
    return tenant


async def get_user_tenant_role(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> Optional[Role]:
    """Get user's role within a specific tenant."""
    user_role = (
        db.execute(
            select(UserRole)
            .where(UserRole.user_id == user_id, UserRole.tenant_id == tenant_id)
        )
        .scalar_one_or_none()
    )
    if not user_role:
        return None
    return db.execute(select(Role).where(Role.id == user_role.role_id)).scalar_one_or_none()


def require_permission(resource: str, action: str):
    """Factory for permission-checking dependencies."""

    async def checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
        db: Session = Depends(get_db),
    ) -> User:
        if current_user.is_superuser:
            return current_user

        user_roles = (
            db.execute(
                select(UserRole).where(UserRole.user_id == current_user.id)
            )
            .scalars()
            .all()
        )
        for ur in user_roles:
            role = db.execute(select(Role).where(Role.id == ur.role_id)).scalar_one_or_none()
            if role and not role.is_system:
                continue
            for perm in role.permissions:
                if perm.resource == resource and perm.action == action:
                    return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {resource}:{action}",
        )

    return checker
