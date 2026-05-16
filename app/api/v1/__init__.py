"""API v1 package."""

from fastapi import APIRouter

from app.api.v1 import auth, users, roles, tenant_users, knowledge_base, document

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(tenant_users.router)
api_router.include_router(knowledge_base.router)
api_router.include_router(document.router)
