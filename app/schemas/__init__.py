"""Schemas package."""

from app.schemas.auth import (
    Token,
    TokenPayload,
    UserCreate,
    UserLogin,
    UserUpdate,
    UserResponse,
    PasswordChange,
)
from app.schemas.role import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleWithPermissions,
    PermissionResponse,
    RolePermissionUpdate,
)
from app.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantUserRoleResponse,
    AssignRoleRequest,
)
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    KnowledgeBaseListResponse,
    KnowledgeBaseWithDocuments,
    DocumentBrief,
)

__all__ = [
    "Token",
    "TokenPayload",
    "UserCreate",
    "UserLogin",
    "UserUpdate",
    "UserResponse",
    "PasswordChange",
    "RoleCreate",
    "RoleUpdate",
    "RoleResponse",
    "RoleWithPermissions",
    "PermissionResponse",
    "RolePermissionUpdate",
    "TenantCreate",
    "TenantUpdate",
    "TenantResponse",
    "TenantUserRoleResponse",
    "AssignRoleRequest",
    "KnowledgeBaseCreate",
    "KnowledgeBaseUpdate",
    "KnowledgeBaseResponse",
    "KnowledgeBaseListResponse",
    "KnowledgeBaseWithDocuments",
    "DocumentBrief",
]
