"""Pytest configuration and fixtures."""

import os
import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil
from typing import Generator
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.models.base import Base
from app.models import Tenant, KnowledgeBase, Document, User, Role, UserRole

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-jwt-testing-only-1234567890")


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_engine():
    """Create a test database engine using SQLite.

    Function-scoped so each test gets a fresh in-memory database,
    ensuring complete test isolation. This avoids cross-test data pollution
    in the auth/permission tests where users and roles must be unique.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db(db_engine) -> Generator[Session, None, None]:
    """Provide a test database session with per-test rollback."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_text():
    """Sample text for testing."""
    return """
    这是一段测试文本。

    第一段落的内容。
    第二段落的内容。

    第三段落，包含更多详细信息。
    """


@pytest.fixture
def sample_long_text():
    """Long sample text for chunking tests."""
    sentences = [
        "这是第一个句子。",
        "这是第二个句子。",
        "这是第三个句子，包含更多内容。",
        "这是第四个句子。",
        "这是第五个句子，也是最后一个。",
    ]
    return " ".join([s * 20 for s in sentences])


@pytest.fixture
def tenant_a(db: Session) -> Tenant:
    """Create a test tenant A."""
    tenant = Tenant(name="Tenant A", slug=f"tenant-a-{uuid4().hex[:8]}")
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture
def tenant_b(db: Session) -> Tenant:
    """Create a test tenant B."""
    tenant = Tenant(name="Tenant B", slug=f"tenant-b-{uuid4().hex[:8]}")
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture
def role_admin(db: Session) -> Role:
    """Create an admin role."""
    role = Role(name="admin", description="Administrator", is_system=True)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@pytest.fixture
def kb_a(db: Session, tenant_a: Tenant) -> KnowledgeBase:
    """Create a knowledge base for tenant A."""
    kb = KnowledgeBase(name="KB A", description="Tenant A's knowledge base", tenant_id=tenant_a.id)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb


@pytest.fixture
def kb_b(db: Session, tenant_b: Tenant) -> KnowledgeBase:
    """Create a knowledge base for tenant B."""
    kb = KnowledgeBase(name="KB B", description="Tenant B's knowledge base", tenant_id=tenant_b.id)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb

