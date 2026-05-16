"""Tests for multi-tenant isolation."""

import pytest
from uuid import uuid4

from app.models import Tenant, KnowledgeBase, Document
from app.services.knowledge_base_service import KnowledgeBaseService, KnowledgeBaseNotFoundError
from app.schemas.knowledge_base import KnowledgeBaseCreate


class TestTenantCreation:
    """Tests for tenant creation and activation/disabling."""

    def test_create_tenant(self, db, tenant_a: Tenant):
        assert tenant_a.name == "Tenant A"
        assert tenant_a.is_active is True
        assert tenant_a.slug is not None

    def test_disable_tenant(self, db, tenant_a: Tenant):
        tenant_a.is_active = False
        db.commit()
        db.refresh(tenant_a)
        assert tenant_a.is_active is False

    def test_enable_tenant(self, db, tenant_a: Tenant):
        tenant_a.is_active = False
        db.commit()
        tenant_a.is_active = True
        db.commit()
        db.refresh(tenant_a)
        assert tenant_a.is_active is True


class TestKnowledgeBaseIsolation:
    """Tests for cross-tenant knowledge base isolation."""

    def test_tenant_a_cannot_see_tenant_b_kb(
        self, db, tenant_a: Tenant, tenant_b: Tenant, kb_a: KnowledgeBase, kb_b: KnowledgeBase
    ):
        """Tenant A should not be able to access Tenant B's knowledge base."""
        service = KnowledgeBaseService(db)

        with pytest.raises(KnowledgeBaseNotFoundError):
            service.get_by_id(kb_b.id, tenant_a.id)

    def test_tenant_b_cannot_see_tenant_a_kb(
        self, db, tenant_a: Tenant, tenant_b: Tenant, kb_a: KnowledgeBase, kb_b: KnowledgeBase
    ):
        """Tenant B should not be able to access Tenant A's knowledge base."""
        service = KnowledgeBaseService(db)

        with pytest.raises(KnowledgeBaseNotFoundError):
            service.get_by_id(kb_a.id, tenant_b.id)

    def test_tenant_a_only_sees_own_kbs(self, db, tenant_a: Tenant, kb_a: KnowledgeBase, tenant_b: Tenant, kb_b: KnowledgeBase):
        """Listing KBs for Tenant A should only return Tenant A's KBs."""
        service = KnowledgeBaseService(db)

        kbs, total = service.list_by_tenant(tenant_a.id)
        kb_ids = {kb.id for kb in kbs}
        assert kb_a.id in kb_ids
        assert kb_b.id not in kb_ids
        assert total == 1

    def test_tenant_b_only_sees_own_kbs(self, db, tenant_a: Tenant, kb_a: KnowledgeBase, tenant_b: Tenant, kb_b: KnowledgeBase):
        """Listing KBs for Tenant B should only return Tenant B's KBs."""
        service = KnowledgeBaseService(db)

        kbs, total = service.list_by_tenant(tenant_b.id)
        kb_ids = {kb.id for kb in kbs}
        assert kb_b.id in kb_ids
        assert kb_a.id not in kb_ids
        assert total == 1

    def test_tenant_a_cannot_delete_tenant_b_kb(
        self, db, tenant_a: Tenant, tenant_b: Tenant, kb_b: KnowledgeBase
    ):
        """Tenant A should not be able to delete Tenant B's knowledge base."""
        service = KnowledgeBaseService(db)

        with pytest.raises(KnowledgeBaseNotFoundError):
            service.delete(kb_b.id, tenant_a.id)

    def test_tenant_a_cannot_update_tenant_b_kb(
        self, db, tenant_a: Tenant, tenant_b: Tenant, kb_b: KnowledgeBase
    ):
        """Tenant A should not be able to update Tenant B's knowledge base."""
        service = KnowledgeBaseService(db)

        with pytest.raises(KnowledgeBaseNotFoundError):
            service.update(kb_b.id, tenant_a.id, KnowledgeBaseCreate(name="Hijacked"))


class TestKnowledgeBaseCRUD:
    """Tests for knowledge base CRUD operations."""

    def test_create_knowledge_base(self, db, tenant_a: Tenant):
        service = KnowledgeBaseService(db)
        data = KnowledgeBaseCreate(name="Test KB", description="A test knowledge base")
        kb = service.create(data, tenant_a.id)

        assert kb.id is not None
        assert kb.name == "Test KB"
        assert kb.description == "A test knowledge base"
        assert kb.tenant_id == tenant_a.id
        assert kb.document_count == 0
        assert kb.chunk_count == 0

    def test_update_knowledge_base(self, db, tenant_a: Tenant, kb_a: KnowledgeBase):
        service = KnowledgeBaseService(db)
        updated = service.update(
            kb_a.id, tenant_a.id, KnowledgeBaseCreate(name="Updated KB", description="New description")
        )
        assert updated.name == "Updated KB"
        assert updated.description == "New description"

    def test_delete_knowledge_base(self, db, tenant_a: Tenant, kb_a: KnowledgeBase):
        service = KnowledgeBaseService(db)
        service.delete(kb_a.id, tenant_a.id)

        kbs, total = service.list_by_tenant(tenant_a.id)
        assert total == 0

    def test_not_found_raises(self, db, tenant_a: Tenant):
        service = KnowledgeBaseService(db)
        fake_id = uuid4()
        with pytest.raises(KnowledgeBaseNotFoundError):
            service.get_by_id(fake_id, tenant_a.id)

    def test_pagination(self, db, tenant_a: Tenant):
        service = KnowledgeBaseService(db)
        for i in range(5):
            service.create(KnowledgeBaseCreate(name=f"KB {i}"), tenant_a.id)

        kbs_page1, total = service.list_by_tenant(tenant_a.id, skip=0, limit=2)
        assert len(kbs_page1) == 2
        assert total == 5

        kbs_page2, _ = service.list_by_tenant(tenant_a.id, skip=2, limit=2)
        assert len(kbs_page2) == 2

        kbs_page3, _ = service.list_by_tenant(tenant_a.id, skip=4, limit=2)
        assert len(kbs_page3) == 1


class TestDocumentIsolation:
    """Tests for cross-tenant document isolation."""

    def test_tenant_a_cannot_see_tenant_b_documents(
        self, db, tenant_a: Tenant, tenant_b: Tenant, kb_a: KnowledgeBase, kb_b: KnowledgeBase
    ):
        """Tenant A should not be able to list Tenant B's documents."""
        from app.services.document_service import DocumentService, DocumentCreateData

        doc_a = Document(
            title="Doc A", file_path="/tmp/a.txt", file_type=".txt",
            file_size=100, knowledge_base_id=kb_a.id
        )
        doc_b = Document(
            title="Doc B", file_path="/tmp/b.txt", file_type=".txt",
            file_size=100, knowledge_base_id=kb_b.id
        )
        db.add(doc_a)
        db.add(doc_b)
        db.commit()

        service = DocumentService(db)

        docs_a, total_a = service.list_by_tenant(tenant_a.id)
        doc_ids_a = {d.id for d in docs_a}
        assert doc_a.id in doc_ids_a
        assert doc_b.id not in doc_ids_a
        assert total_a == 1

    def test_tenant_a_cannot_get_tenant_b_document(
        self, db, tenant_a: Tenant, tenant_b: Tenant, kb_a: KnowledgeBase, kb_b: KnowledgeBase
    ):
        """Tenant A should not be able to get Tenant B's document."""
        from app.services.document_service import DocumentService
        from app.core.exceptions import DocumentNotFoundError

        doc_b = Document(
            title="Doc B Private", file_path="/tmp/b_private.txt", file_type=".txt",
            file_size=100, knowledge_base_id=kb_b.id
        )
        db.add(doc_b)
        db.commit()

        service = DocumentService(db)
        with pytest.raises(DocumentNotFoundError):
            service.get_by_id(doc_b.id, tenant_a.id)

    def test_tenant_a_cannot_delete_tenant_b_document(
        self, db, tenant_a: Tenant, tenant_b: Tenant, kb_b: KnowledgeBase
    ):
        """Tenant A should not be able to delete Tenant B's document."""
        from app.services.document_service import DocumentService
        from app.core.exceptions import DocumentNotFoundError

        doc_b = Document(
            title="Doc B Delete Test", file_path="/tmp/b_del.txt", file_type=".txt",
            file_size=100, knowledge_base_id=kb_b.id
        )
        db.add(doc_b)
        db.commit()

        service = DocumentService(db)
        with pytest.raises(DocumentNotFoundError):
            service.delete(doc_b.id, tenant_a.id)
