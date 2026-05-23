"""Document incremental update service."""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db_context
from app.models.knowledge_base import Document, Chunk
from app.services.chunk_service import ChunkService
from app.services.vector_store_service import VectorStoreService, get_vector_store
from app.core.logging import get_logger

logger = get_logger(__name__)


class DocumentUpdateService:
    """Service for document incremental updates: change detection, reparse, and re-vectorization."""

    def __init__(self):
        self.chunk_service = ChunkService()
        self.vector_store_service = get_vector_store()

    @staticmethod
    def compute_file_hash(file_path: str | Path) -> str:
        """Compute SHA-256 hash of file content for change detection."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def check_for_changes(self, document_id: UUID) -> tuple[bool, Optional[str]]:
        """
        Check if a document's file has changed since last parse.

        Returns:
            Tuple of (has_changed, current_hash)
            If file doesn't exist, returns (False, None)
        """
        with get_db_context() as db:
            doc = db.get(Document, document_id)
            if not doc or not doc.file_path:
                return False, None

            try:
                current_hash = self.compute_file_hash(doc.file_path)
            except FileNotFoundError:
                logger.warning("document_file_not_found", document_id=str(document_id))
                return False, None

            has_changed = doc.file_hash is None or doc.file_hash != current_hash
            return has_changed, current_hash

    async def reparse_document(
        self,
        document_id: UUID,
        force: bool = False,
    ) -> dict:
        """
        Reparse a document and update its chunks + vectors.

        If the file has not changed and force=False, returns early with status="unchanged".

        Args:
            document_id: Document UUID
            force: If True, re-parse even if file hasn't changed

        Returns:
            Dict with status, chunk counts, and new version
        """
        with get_db_context() as db:
            doc = db.get(Document, document_id)
            if not doc:
                raise ValueError(f"Document {document_id} not found")

            if not doc.file_path:
                raise ValueError(f"Document {document_id} has no file path")

            has_changed, new_hash = self.check_for_changes(document_id)
            if not has_changed and not force:
                logger.info("document_unchanged", document_id=str(document_id))
                return {
                    "status": "unchanged",
                    "document_id": str(document_id),
                    "old_chunk_count": doc.chunk_count,
                    "new_chunk_count": doc.chunk_count,
                    "new_version": doc.version,
                    "message": "Document file unchanged, no reparse needed",
                }

            old_chunk_count = doc.chunk_count

            # Delete old chunks and their vectors
            old_chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
            old_vector_ids = [c.embedding_id for c in old_chunks if c.embedding_id]
            if old_vector_ids:
                await self.vector_store_service.delete_vectors(old_vector_ids)

            db.query(Chunk).filter(Chunk.document_id == document_id).delete()

            # Parse the file again
            try:
                from app.parsers import get_parser
                parser = get_parser(doc.file_path)
                content = parser.parse(doc.file_path)
                metadata = parser.get_metadata(doc.file_path)
            except Exception as e:
                logger.exception("document_reparse_failed", document_id=str(document_id), error=str(e))
                doc.status = "failed"
                db.commit()
                raise

            # Create new chunks
            new_chunk_records = self.chunk_service.create_chunks(document_id, content)

            for chunk in new_chunk_records:
                db.add(chunk)

            db.flush()

            # Generate embeddings and add to vector store
            texts = [c.content for c in new_chunk_records]
            from app.services.embedding_service import EmbeddingService
            embedding_service = EmbeddingService()

            try:
                embeddings = await embedding_service.embed_batch(texts)
            except Exception as e:
                logger.exception("embedding_failed", document_id=str(document_id), error=str(e))
                raise

            vector_metadata = [
                {
                    "knowledge_base_id": str(doc.knowledge_base_id),
                    "document_id": str(doc.id),
                    "chunk_id": str(chunk.id),
                    "chunk_index": chunk.chunk_index,
                    "document_title": doc.title,
                }
                for chunk in new_chunk_records
            ]
            vector_ids = await self.vector_store_service.add_vectors_batch(
                texts,
                embeddings,
                metadata=vector_metadata,
            )

            # Link embeddings to chunks
            for chunk, vector_id in zip(new_chunk_records, vector_ids):
                chunk.embedding_id = vector_id

            # Update document record
            doc.version += 1
            doc.file_hash = new_hash
            doc.chunk_count = len(new_chunk_records)
            doc.status = "ready"
            if metadata:
                doc.meta = metadata

            db.commit()

            logger.info(
                "document_reparsed",
                document_id=str(document_id),
                old_chunks=old_chunk_count,
                new_chunks=len(new_chunk_records),
                new_version=doc.version,
            )

            return {
                "status": "success",
                "document_id": str(document_id),
                "old_chunk_count": old_chunk_count,
                "new_chunk_count": len(new_chunk_records),
                "new_version": doc.version,
                "message": f"Reparsed: {old_chunk_count} -> {len(new_chunk_records)} chunks (v{doc.version})",
            }

    async def reload_knowledge_base(
        self,
        knowledge_base_id: UUID,
        force: bool = False,
    ) -> dict:
        """
        Reload all documents in a knowledge base.

        Parses each document and re-adds vectors to the vector store.

        Args:
            knowledge_base_id: Knowledge base UUID
            force: If True, re-parse even unchanged files

        Returns:
            Summary dict with counts
        """
        with get_db_context() as db:
            docs = db.query(Document).filter(
                Document.knowledge_base_id == knowledge_base_id,
                Document.is_deleted == False,
            ).all()

            total_chunks = 0
            success_count = 0
            failed_docs = []

            for doc in docs:
                try:
                    result = await self.reparse_document(doc.id, force=force)
                    if result["status"] == "success":
                        total_chunks += result["new_chunk_count"]
                        success_count += 1
                except Exception as e:
                    failed_docs.append({"document_id": str(doc.id), "error": str(e)})
                    logger.warning(
                        "document_reload_failed",
                        document_id=str(doc.id),
                        error=str(e),
                    )

            return {
                "status": "completed",
                "documents_processed": success_count,
                "documents_failed": len(failed_docs),
                "total_chunks": total_chunks,
                "failed_documents": failed_docs,
                "message": f"Processed {success_count}/{len(docs)} documents, {total_chunks} total chunks",
            }

    def get_version_info(self, document_id: UUID) -> dict:
        """Get current version info for a document."""
        with get_db_context() as db:
            doc = db.get(Document, document_id)
            if not doc:
                raise ValueError(f"Document {document_id} not found")

            return {
                "document_id": doc.id,
                "version": doc.version,
                "file_hash": doc.file_hash,
                "chunk_count": doc.chunk_count,
                "is_deleted": doc.is_deleted,
                "updated_at": doc.updated_at,
                "status": doc.status,
            }
