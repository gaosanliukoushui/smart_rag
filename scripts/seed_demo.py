"""Seed a reproducible SmartRAG demo workspace.

This creates:
- demo user: demo / DemoPass123!
- one tenant workspace
- one knowledge base
- demo documents from demo/sample_docs
- chunks and vectors with source metadata

Use --mock-embeddings for a fast local/CI seed that does not download models.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select

from app.config import get_settings
from app.core.security import get_password_hash
from app.db.session import get_db_context, init_db
from app.models import KnowledgeBase, Role, Tenant, User, UserRole
from app.models.knowledge_base import Chunk, Document
from app.services.chunk_service import ChunkService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import get_vector_store


DEMO_USERNAME = "demo"
DEMO_PASSWORD = "DemoPass123!"
DEMO_EMAIL = "demo@smartrag.local"
DEMO_TENANT_SLUG = "demo-workspace"
DEMO_KB_NAME = "SmartRAG Demo Knowledge Base"


def mock_embedding(text: str, dim: int) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = [((digest[i % len(digest)] / 255.0) * 2) - 1 for i in range(dim)]
    norm = sum(v * v for v in values) ** 0.5 or 1.0
    return [v / norm for v in values]


def ensure_demo_identity(db):
    user = db.execute(select(User).where(User.username == DEMO_USERNAME)).scalar_one_or_none()
    if not user:
        user = User(
            username=DEMO_USERNAME,
            email=DEMO_EMAIL,
            full_name="SmartRAG Demo User",
            hashed_password=get_password_hash(DEMO_PASSWORD),
        )
        db.add(user)

    tenant = db.execute(select(Tenant).where(Tenant.slug == DEMO_TENANT_SLUG)).scalar_one_or_none()
    if not tenant:
        tenant = Tenant(name="SmartRAG Demo Workspace", slug=DEMO_TENANT_SLUG)
        db.add(tenant)

    role = db.execute(select(Role).where(Role.name == "admin")).scalar_one_or_none()
    if not role:
        role = Role(name="admin", description="Administrator role", is_system=True)
        db.add(role)

    db.flush()

    user_role = (
        db.execute(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.tenant_id == tenant.id,
                UserRole.role_id == role.id,
            )
        )
        .scalar_one_or_none()
    )
    if not user_role:
        db.add(UserRole(user_id=user.id, tenant_id=tenant.id, role_id=role.id))

    kb = (
        db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.tenant_id == tenant.id,
                KnowledgeBase.name == DEMO_KB_NAME,
            )
        )
        .scalar_one_or_none()
    )
    if not kb:
        kb = KnowledgeBase(
            name=DEMO_KB_NAME,
            description="Seeded demo data for SmartRAG resume/project walkthroughs.",
            tenant_id=tenant.id,
        )
        db.add(kb)
        db.flush()

    return user, tenant, kb


async def seed_documents(kb_id, docs_dir: Path, mock_embeddings: bool) -> tuple[int, int]:
    settings = get_settings()
    chunk_service = ChunkService(chunk_size=settings.CHUNK_SIZE, overlap=settings.CHUNK_OVERLAP)
    vector_store = get_vector_store()
    embedding_service = None if mock_embeddings else EmbeddingService(settings.EMBEDDING_MODEL, settings.EMBEDDING_DEVICE)
    docs_created = 0
    chunks_created = 0

    with get_db_context() as db:
        kb = db.get(KnowledgeBase, kb_id)
        for path in sorted(docs_dir.glob("*")):
            if path.suffix.lower() not in {".md", ".txt", ".text"}:
                continue

            existing = (
                db.execute(
                    select(Document).where(
                        Document.knowledge_base_id == kb.id,
                        Document.title == path.stem,
                    )
                )
                .scalar_one_or_none()
            )
            if existing:
                continue

            content = path.read_text(encoding="utf-8")
            doc = Document(
                title=path.stem,
                file_path=str(path),
                file_type=path.suffix.lower(),
                file_size=path.stat().st_size,
                status="processing",
                knowledge_base_id=kb.id,
                file_hash=hashlib.sha256(path.read_bytes()).hexdigest(),
            )
            db.add(doc)
            db.flush()

            chunks = chunk_service.create_chunks(doc.id, content)
            for chunk in chunks:
                db.add(chunk)
            db.flush()

            texts = [chunk.content for chunk in chunks]
            if mock_embeddings:
                embeddings = [mock_embedding(text, settings.EMBEDDING_DIM) for text in texts]
            else:
                embeddings = await embedding_service.embed_batch(texts)

            vector_ids = await vector_store.add_vectors_batch(
                texts,
                embeddings,
                metadata=[
                    {
                        "knowledge_base_id": str(kb.id),
                        "document_id": str(doc.id),
                        "document_title": doc.title,
                        "chunk_id": str(chunk.id),
                        "chunk_index": chunk.chunk_index,
                    }
                    for chunk in chunks
                ],
            )
            for chunk, vector_id in zip(chunks, vector_ids):
                chunk.embedding_id = vector_id

            doc.status = "ready"
            doc.chunk_count = len(chunks)
            docs_created += 1
            chunks_created += len(chunks)

        kb.document_count = db.execute(
            select(func.count(Document.id)).where(Document.knowledge_base_id == kb.id)
        ).scalar_one()
        kb.chunk_count = db.execute(
            select(func.count(Chunk.id)).join(Document).where(Document.knowledge_base_id == kb.id)
        ).scalar_one()
        db.commit()

    return docs_created, chunks_created


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs-dir", default="demo/sample_docs")
    parser.add_argument("--mock-embeddings", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    init_db(settings.DATABASE_URL)

    with get_db_context() as db:
        user, tenant, kb = ensure_demo_identity(db)
        kb_id = kb.id
        db.commit()
        print(f"Demo user: {user.username} / {DEMO_PASSWORD}")
        print(f"Tenant: {tenant.name} ({tenant.id})")
        print(f"Knowledge base: {kb.name} ({kb.id})")

    docs_created, chunks_created = await seed_documents(kb_id, ROOT / args.docs_dir, args.mock_embeddings)
    print(f"Seeded {docs_created} documents and {chunks_created} chunks.")
    print("Start the app, log in with the demo user, and open the demo knowledge base.")
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))
