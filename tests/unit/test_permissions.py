"""Tests for RBAC permissions and tenant role assignments."""

import pytest
from uuid import uuid4

from app.models import Tenant, Role, Permission, UserRole, User
from app.services.auth_service import AuthService
from app.schemas.auth import UserCreate


class TestRoleModel:
    """Tests for Role and Permission models."""

    def test_create_role(self, db, role_admin: Role):
        assert role_admin.name == "admin"
        assert role_admin.is_system is True

    def test_role_repr(self, db, role_admin: Role):
        r = repr(role_admin)
        assert "Role" in r or "admin" in r


class TestUserRoleAssignment:
    """Tests for user-role assignments within tenants."""

    def test_assign_role_to_user_in_tenant(self, db, tenant_a: Tenant, role_admin: Role):
        from app.models import User, UserRole
        from app.core.security import get_password_hash

        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=get_password_hash("password123"),
        )
        db.add(user)
        db.flush()

        user_role = UserRole(user_id=user.id, tenant_id=tenant_a.id, role_id=role_admin.id)
        db.add(user_role)
        db.commit()

        db.refresh(user_role)
        assert user_role.user_id == user.id
        assert user_role.tenant_id == tenant_a.id
        assert user_role.role_id == role_admin.id

    def test_user_can_have_multiple_roles_in_different_tenants(
        self, db, tenant_a: Tenant, tenant_b: Tenant, role_admin: Role
    ):
        from app.models import User, UserRole
        from app.core.security import get_password_hash

        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=get_password_hash("password123"),
        )
        db.add(user)
        db.flush()

        role_viewer = Role(name="viewer", description="Viewer role")
        db.add(role_viewer)
        db.flush()

        ur_a = UserRole(user_id=user.id, tenant_id=tenant_a.id, role_id=role_admin.id)
        ur_b = UserRole(user_id=user.id, tenant_id=tenant_b.id, role_id=role_viewer.id)
        db.add(ur_a)
        db.add(ur_b)
        db.commit()

        db.refresh(user)
        assert len(user.user_roles) == 2


class TestPermissionModel:
    """Tests for Permission model."""

    def test_create_permission(self, db):
        perm = Permission(resource="knowledge_base", action="create", description="Create KB")
        db.add(perm)
        db.commit()
        db.refresh(perm)

        assert perm.resource == "knowledge_base"
        assert perm.action == "create"

    def test_permission_unique_constraint(self, db):
        perm1 = Permission(resource="document", action="read", description="Read docs")
        db.add(perm1)
        db.commit()

        perm2 = Permission(resource="document", action="read", description="Duplicate")
        db.add(perm2)
        with pytest.raises(Exception):
            db.commit()


class TestRolePermissionAssignment:
    """Tests for assigning permissions to roles."""

    def test_assign_permission_to_role(self, db, role_admin: Role):
        perm = Permission(resource="knowledge_base", action="create", description="Create KB")
        db.add(perm)
        db.flush()

        role_admin.permissions.append(perm)
        db.commit()
        db.refresh(role_admin)

        assert len(role_admin.permissions) == 1
        assert role_admin.permissions[0].resource == "knowledge_base"

    def test_role_has_all_kb_permissions(self, db):
        role_editor = Role(name="editor", description="Editor role")
        db.add(role_editor)
        db.flush()

        for action in ["create", "read", "update", "delete"]:
            perm = Permission(resource="knowledge_base", action=action)
            db.add(perm)
            db.flush()
            role_editor.permissions.append(perm)
        db.commit()
        db.refresh(role_editor)

        assert len(role_editor.permissions) == 4
        actions = {p.action for p in role_editor.permissions}
        assert actions == {"create", "read", "update", "delete"}


class TestTenantIsolation:
    """Tests for cross-tenant role/permission isolation."""

    def test_user_different_roles_per_tenant(
        self, db, tenant_a: Tenant, tenant_b: Tenant, role_admin: Role
    ):
        from app.models import User, UserRole
        from app.core.security import get_password_hash

        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=get_password_hash("password123"),
        )
        db.add(user)
        db.flush()

        role_viewer = Role(name="viewer", description="Viewer role")
        db.add(role_viewer)
        db.flush()

        db.add(UserRole(user_id=user.id, tenant_id=tenant_a.id, role_id=role_admin.id))
        db.add(UserRole(user_id=user.id, tenant_id=tenant_b.id, role_id=role_viewer.id))
        db.commit()
        db.refresh(user)

        roles_by_tenant = {ur.tenant_id: ur.role_id for ur in user.user_roles}
        assert roles_by_tenant[tenant_a.id] == role_admin.id
        assert roles_by_tenant[tenant_b.id] == role_viewer.id

    def test_kb_belongs_to_correct_tenant(
        self, db, tenant_a: Tenant, tenant_b: Tenant, kb_a, kb_b
    ):
        assert kb_a.tenant_id == tenant_a.id
        assert kb_b.tenant_id == tenant_b.id


class TestRegisterCreatesDefaultTenant:
    """Tests that user registration creates a default tenant and role."""

    def test_register_creates_workspace_tenant(self, db):
        service = AuthService(db)
        data = UserCreate(
            email="alice@example.com",
            username="alice",
            password="strongpassword123",
        )
        user = service.register(data)
        assert user.user_roles[0].tenant is not None
        assert user.user_roles[0].role.name == "admin"

    def test_register_assigns_admin_role(self, db):
        service = AuthService(db)
        data = UserCreate(
            email="bob@example.com",
            username="bob",
            password="strongpassword123",
        )
        user = service.register(data)
        assert len(user.user_roles) == 1
        assert user.user_roles[0].role.name == "admin"
