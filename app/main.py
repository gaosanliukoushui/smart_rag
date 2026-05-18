"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1 import auth, document, health, knowledge_base, chat
from app.api.v1 import session as session_router
from app.api.v1 import users as users_router
from app.api.v1 import roles as roles_router
from app.api.v1 import tenant_users as tenant_users_router
from app.api.v1.metrics import router as metrics_router
from app.config import settings
from app.core.logging import setup_logging, get_logger
from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler

# Initialize structured logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("app_startup", message="SmartRAG application starting")
    yield
    logger.info("app_shutdown", message="SmartRAG application shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="SmartRAG - AI Knowledge Base System with RAG capabilities",
    lifespan=lifespan,
)

# Add rate limiter state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add logging middleware
from app.middleware.logging_middleware import LoggingMiddleware
app.add_middleware(LoggingMiddleware)

app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(auth.router, prefix=settings.API_V1_PREFIX, tags=["Auth"])
app.include_router(document.router, prefix=settings.API_V1_PREFIX, tags=["Documents"])
app.include_router(knowledge_base.router, prefix=settings.API_V1_PREFIX, tags=["KnowledgeBase"])
app.include_router(chat.router, prefix=settings.API_V1_PREFIX, tags=["Chat"])
app.include_router(session_router.router, prefix=settings.API_V1_PREFIX, tags=["Sessions"])
app.include_router(users_router.router, prefix=settings.API_V1_PREFIX, tags=["Users"])
app.include_router(roles_router.router, prefix=settings.API_V1_PREFIX, tags=["Roles"])
app.include_router(tenant_users_router.router, prefix=settings.API_V1_PREFIX, tags=["TenantUsers"])
app.include_router(metrics_router, tags=["Metrics"])

# Serve frontend static files (Vite build output)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


@app.get("/")
async def root():
    return {"message": "SmartRAG API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Root-level health check for load balancers and orchestrators."""
    return {"status": "healthy"}
