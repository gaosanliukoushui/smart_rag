"""Tenant service."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Tenant


class TenantService:
    """Service for tenant operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, tenant_id: UUID) -> Optional[Tenant]:
        return self.db.execute(select(Tenant).where(Tenant.id == tenant_id)).scalar_one_or_none()

    def get_by_slug(self, slug: str) -> Optional[Tenant]:
        return self.db.execute(select(Tenant).where(Tenant.slug == slug)).scalar_one_or_none()

    def list_all(self, skip: int = 0, limit: int = 50) -> list[Tenant]:
        return (
            self.db.execute(select(Tenant).offset(skip).limit(limit).order_by(Tenant.created_at.desc()))
            .scalars()
            .all()
        )

    def create(self, name: str, slug: str, description: Optional[str] = None) -> Tenant:
        tenant = Tenant(name=name, slug=slug, description=description)
        self.db.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def update(self, tenant: Tenant, **kwargs) -> Tenant:
        for key, value in kwargs.items():
            if value is not None and hasattr(tenant, key):
                setattr(tenant, key, value)
        self.db.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def delete(self, tenant: Tenant) -> None:
        self.db.delete(tenant)
        self.db.commit()

    def deactivate(self, tenant: Tenant) -> Tenant:
        return self.update(tenant, is_active=False)

    def activate(self, tenant: Tenant) -> Tenant:
        return self.update(tenant, is_active=True)
