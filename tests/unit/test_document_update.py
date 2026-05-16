"""Tests for document incremental update service."""

import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestFileHash:
    """Test file hash computation for change detection."""

    def test_compute_file_hash_deterministic(self, tmp_path):
        """Hash of same file content should be identical."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        content = b"Hello, World! This is test content."
        file1.write_bytes(content)
        file2.write_bytes(content)

        hash1 = DocumentUpdateService.compute_file_hash(str(file1))
        hash2 = DocumentUpdateService.compute_file_hash(str(file2))

        assert hash1 == hash2

    def test_compute_file_hash_changes_with_content(self, tmp_path):
        """Different content should produce different hashes."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("Content A")
        file2.write_text("Content B")

        hash1 = DocumentUpdateService.compute_file_hash(str(file1))
        hash2 = DocumentUpdateService.compute_file_hash(str(file2))

        assert hash1 != hash2

    def test_compute_file_hash_length(self, tmp_path):
        """SHA-256 hash should be 64 hex characters."""
        file = tmp_path / "test.txt"
        file.write_text("Any content")

        hash_val = DocumentUpdateService.compute_file_hash(str(file))
        assert len(hash_val) == 64
        assert all(c in "0123456789abcdef" for c in hash_val)

    def test_compute_file_hash_binary_content(self, tmp_path):
        """Hash should work correctly with binary content."""
        file = tmp_path / "test.pdf"
        binary_content = bytes(range(256))
        file.write_bytes(binary_content)

        hash_val = DocumentUpdateService.compute_file_hash(str(file))
        assert len(hash_val) == 64
        assert hash_val == hashlib.sha256(binary_content).hexdigest()

    def test_compute_file_hash_large_file(self, tmp_path):
        """Hash should work correctly with large files (tests chunked reading)."""
        file = tmp_path / "large.bin"
        content = b"X" * (8 * 1024 + 100)
        file.write_bytes(content)

        hash_val = DocumentUpdateService.compute_file_hash(str(file))
        assert hash_val == hashlib.sha256(content).hexdigest()


class TestDocumentUpdateService:
    """Test DocumentUpdateService with mocked database."""

    @pytest.fixture
    def service(self):
        from app.services.document_update_service import DocumentUpdateService
        return DocumentUpdateService()

    def test_compute_file_hash_integration(self, tmp_path):
        """Integration test: create file, hash, modify, hash again."""
        from app.services.document_update_service import DocumentUpdateService

        file = tmp_path / "doc.txt"
        file.write_text("Initial content")
        hash1 = DocumentUpdateService.compute_file_hash(str(file))

        file.write_text("Modified content")
        hash2 = DocumentUpdateService.compute_file_hash(str(file))

        file.write_text("Initial content")
        hash3 = DocumentUpdateService.compute_file_hash(str(file))

        assert hash1 != hash2
        assert hash1 == hash3

    @pytest.mark.asyncio
    async def test_reparse_document_not_found(self, service):
        """Reparse should raise ValueError for non-existent document."""
        import uuid

        fake_id = uuid.uuid4()

        mock_db = MagicMock()
        mock_db.get = MagicMock(return_value=None)
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.__exit__ = MagicMock(return_value=False)

        with patch("app.services.document_update_service.get_db_context", return_value=mock_ctx):
            with pytest.raises(ValueError, match="not found"):
                await service.reparse_document(fake_id)

    @pytest.mark.asyncio
    async def test_reparse_unchanged_document(self, service, tmp_path):
        """If file hasn't changed and force=False, should return unchanged status."""
        import uuid
        from app.services.document_update_service import DocumentUpdateService

        file = tmp_path / "doc.txt"
        file.write_text("Some content")
        file_hash = DocumentUpdateService.compute_file_hash(str(file))

        mock_doc = MagicMock()
        mock_doc.id = uuid.uuid4()
        mock_doc.file_path = str(file)
        mock_doc.file_hash = file_hash
        mock_doc.chunk_count = 5
        mock_doc.version = 1
        mock_doc.status = "ready"

        mock_db = MagicMock()
        mock_db.get = MagicMock(return_value=mock_doc)
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.__exit__ = MagicMock(return_value=False)

        with patch("app.services.document_update_service.get_db_context", return_value=mock_ctx):
            result = await service.reparse_document(mock_doc.id, force=False)

        assert result["status"] == "unchanged"
        assert result["old_chunk_count"] == 5
        assert result["new_version"] == 1

    @pytest.mark.asyncio
    async def test_reparse_changed_document_success(self, service, tmp_path):
        """Reparse should update chunks when file has changed."""
        import uuid
        from app.services.document_update_service import DocumentUpdateService

        file = tmp_path / "doc.txt"
        file.write_text("Original content.")
        old_hash = DocumentUpdateService.compute_file_hash(str(file))

        doc_id = uuid.uuid4()
        kb_id = uuid.uuid4()

        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.knowledge_base_id = kb_id
        mock_doc.file_path = str(file)
        mock_doc.file_hash = old_hash
        mock_doc.chunk_count = 2
        mock_doc.version = 1
        mock_doc.status = "ready"
        mock_doc.meta = {}

        mock_chunk = MagicMock()
        mock_chunk.embedding_id = "vec1"

        mock_db = MagicMock()
        mock_db.get = MagicMock(return_value=mock_doc)
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_chunk]
        mock_db.query.return_value.filter.return_value.delete.return_value = None
        mock_db.flush = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.__exit__ = MagicMock(return_value=False)

        mock_chunks = [MagicMock(), MagicMock()]

        with patch("app.services.document_update_service.get_db_context", return_value=mock_ctx):
            with patch.object(service, "check_for_changes", return_value=(True, "newhash")):
                service.vector_store_service = MagicMock()
                service.vector_store_service.delete_vectors = AsyncMock(return_value=True)
                service.vector_store_service.add_vectors_batch = AsyncMock(return_value=["v1", "v2"])

                with patch.object(service.chunk_service, "create_chunks", return_value=mock_chunks):
                    with patch("app.services.embedding_service.EmbeddingService") as mock_es_cls:
                        mock_es = MagicMock()
                        mock_es.embed_batch = AsyncMock(return_value=[[0.1, 0.2], [0.3, 0.4]])
                        mock_es_cls.return_value = mock_es
                        result = await service.reparse_document(doc_id, force=False)

        assert result["status"] == "success"
        assert result["new_version"] == 2
        assert result["old_chunk_count"] == 2
        assert result["new_chunk_count"] == 2

    def test_get_version_info_not_found(self, service):
        """get_version_info should raise for non-existent document."""
        import uuid

        fake_id = uuid.uuid4()
        mock_db = MagicMock()
        mock_db.get = MagicMock(return_value=None)
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.__exit__ = MagicMock(return_value=False)

        with patch("app.services.document_update_service.get_db_context", return_value=mock_ctx):
            with pytest.raises(ValueError, match="not found"):
                service.get_version_info(fake_id)

    @pytest.mark.asyncio
    async def test_reload_knowledge_base_success(self, service, tmp_path):
        """Reload should process all non-deleted documents."""
        import uuid
        from app.services.document_update_service import DocumentUpdateService

        kb_id = uuid.uuid4()
        doc_id = uuid.uuid4()

        file = tmp_path / "doc.txt"
        file.write_text("Content")
        file_hash = DocumentUpdateService.compute_file_hash(str(file))

        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.knowledge_base_id = kb_id
        mock_doc.file_path = str(file)
        mock_doc.file_hash = file_hash
        mock_doc.chunk_count = 1
        mock_doc.version = 1
        mock_doc.status = "ready"
        mock_doc.meta = {}

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_doc]
        mock_db.get = MagicMock(return_value=mock_doc)
        mock_db.query.return_value.filter.return_value.delete.return_value = None
        mock_db.flush = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.__exit__ = MagicMock(return_value=False)

        mock_chunks = [MagicMock()]

        with patch("app.services.document_update_service.get_db_context", return_value=mock_ctx):
            with patch.object(service, "check_for_changes", return_value=(True, "newhash")):
                service.vector_store_service = MagicMock()
                service.vector_store_service.delete_vectors = AsyncMock(return_value=True)
                service.vector_store_service.add_vectors_batch = AsyncMock(return_value=["v1"])

                with patch.object(service.chunk_service, "create_chunks", return_value=mock_chunks):
                    with patch("app.services.embedding_service.EmbeddingService") as mock_es_cls:
                        mock_es = MagicMock()
                        mock_es.embed_batch = AsyncMock(return_value=[[0.1]])
                        mock_es_cls.return_value = mock_es
                        result = await service.reload_knowledge_base(kb_id, force=False)

        assert result["status"] == "completed"
        assert result["documents_processed"] == 1
        assert result["documents_failed"] == 0

    @pytest.mark.asyncio
    async def test_reload_knowledge_base_with_failures(self, service, tmp_path):
        """Reload should track failed documents."""
        import uuid
        from app.services.document_update_service import DocumentUpdateService

        kb_id = uuid.uuid4()
        doc_id = uuid.uuid4()

        file = tmp_path / "doc.txt"
        file.write_text("Content")

        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.knowledge_base_id = kb_id
        mock_doc.file_path = str(file)
        mock_doc.file_hash = "oldhash"
        mock_doc.chunk_count = 1
        mock_doc.version = 1
        mock_doc.status = "ready"
        mock_doc.meta = {}

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_doc]
        mock_db.get = MagicMock(return_value=mock_doc)
        mock_db.query.return_value.filter.return_value.delete.return_value = None
        mock_db.flush = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_db)
        mock_ctx.__exit__ = MagicMock(return_value=False)

        with patch("app.services.document_update_service.get_db_context", return_value=mock_ctx):
            with patch.object(service, "check_for_changes", side_effect=Exception("File deleted")):
                result = await service.reload_knowledge_base(kb_id, force=False)

        assert result["status"] == "completed"
        assert result["documents_processed"] == 0
        assert result["documents_failed"] == 1
        assert len(result["failed_documents"]) == 1


# Import at module level for test class access
from app.services.document_update_service import DocumentUpdateService
