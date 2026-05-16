"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import document, health, knowledge_base, chat
from app.api.v1 import session as session_router
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="SmartRAG - AI Knowledge Base System with RAG capabilities",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(document.router, prefix=settings.API_V1_PREFIX, tags=["Documents"])
app.include_router(knowledge_base.router, prefix=settings.API_V1_PREFIX, tags=["KnowledgeBase"])
app.include_router(chat.router, prefix=settings.API_V1_PREFIX, tags=["Chat"])
app.include_router(session_router.router, prefix=settings.API_V1_PREFIX, tags=["Sessions"])

# Serve frontend static files (Vite build output)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


@app.get("/")
async def root():
    return {"message": "SmartRAG API", "version": "1.0.0"}
