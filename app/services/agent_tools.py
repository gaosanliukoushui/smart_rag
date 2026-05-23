"""Tool registry for the SmartRAG agent runtime."""

from __future__ import annotations

import difflib
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge_base import Chunk, Document, KnowledgeBase
from app.services.bm25_retriever import BM25Retriever


@dataclass
class ToolResult:
    """Structured tool result."""

    ok: bool
    data: dict[str, Any]
    error: str | None = None
    latency_ms: float = 0.0


@dataclass
class ToolSpec:
    """A registered agent tool."""

    name: str
    description: str
    input_model: type[BaseModel]
    handler: Callable[[Session, uuid.UUID, BaseModel], ToolResult]
    permission: str = "read"
    requires_approval: bool = False

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.input_model.model_json_schema()


class SearchKBInput(BaseModel):
    knowledge_base_id: str
    query: str
    top_k: int = Field(default=5, ge=1, le=20)


class ListDocumentsInput(BaseModel):
    knowledge_base_id: str
    limit: int = Field(default=20, ge=1, le=100)


class DocumentPreviewInput(BaseModel):
    document_id: str
    max_chars: int = Field(default=4000, ge=200, le=20000)


class SummarizeDocumentInput(BaseModel):
    document_id: str
    max_chars: int = Field(default=6000, ge=200, le=30000)


class CompareDocumentsInput(BaseModel):
    left_document_id: str
    right_document_id: str
    max_chars: int = Field(default=5000, ge=200, le=30000)


class CreateReportInput(BaseModel):
    title: str
    sections: list[dict[str, Any]]
    sources: list[dict[str, Any]] = Field(default_factory=list)


class PublishReportInput(BaseModel):
    title: str
    content: str
    destination: str = "internal_demo_channel"


class AskRAGInput(BaseModel):
    knowledge_base_id: str
    question: str
    top_k: int = Field(default=5, ge=1, le=10)


def _timed(fn):
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            data = fn(*args, **kwargs)
            return ToolResult(ok=True, data=data, latency_ms=(time.perf_counter() - start) * 1000)
        except Exception as exc:
            return ToolResult(ok=False, data={}, error=str(exc), latency_ms=(time.perf_counter() - start) * 1000)

    return wrapper


def _get_document(db: Session, document_id: str) -> Document:
    doc = db.get(Document, uuid.UUID(document_id))
    if not doc or doc.is_deleted:
        raise ValueError(f"Document not found: {document_id}")
    return doc


def _doc_text(db: Session, doc: Document, max_chars: int) -> str:
    chunks = (
        db.execute(select(Chunk).where(Chunk.document_id == doc.id).order_by(Chunk.chunk_index.asc()))
        .scalars()
        .all()
    )
    if chunks:
        return "\n\n".join(chunk.content for chunk in chunks)[:max_chars]
    path = doc.file_path
    try:
        from pathlib import Path

        return Path(path).read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except Exception:
        return ""


@_timed
def _search_kb(db: Session, tenant_id: uuid.UUID, params: SearchKBInput) -> dict[str, Any]:
    kb_id = uuid.UUID(params.knowledge_base_id)
    kb = db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id, KnowledgeBase.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if not kb:
        raise ValueError(f"Knowledge base not found: {params.knowledge_base_id}")

    rows = (
        db.execute(
            select(Chunk, Document)
            .join(Document, Chunk.document_id == Document.id)
            .where(Document.knowledge_base_id == kb_id, Document.is_deleted == False)  # noqa: E712
            .order_by(Document.created_at.desc(), Chunk.chunk_index.asc())
        )
        .all()
    )
    retriever = BM25Retriever(tokenizer="char_ngram")
    retriever.build_index(
        [chunk.content for chunk, _ in rows],
        [
            {
                "document_id": str(doc.id),
                "document_title": doc.title,
                "chunk_id": str(chunk.id),
                "chunk_index": chunk.chunk_index,
            }
            for chunk, doc in rows
        ],
    )
    results = retriever.search_with_scores(params.query, params.top_k)
    return {
        "query": params.query,
        "results": [
            {
                "text": text[:600],
                "score": score,
                **meta,
                "rank": rank,
            }
            for rank, (text, score, meta) in enumerate(results, start=1)
        ],
    }


@_timed
def _list_documents(db: Session, tenant_id: uuid.UUID, params: ListDocumentsInput) -> dict[str, Any]:
    kb_id = uuid.UUID(params.knowledge_base_id)
    docs = (
        db.execute(
            select(Document)
            .join(KnowledgeBase)
            .where(Document.knowledge_base_id == kb_id, KnowledgeBase.tenant_id == tenant_id, Document.is_deleted == False)  # noqa: E712
            .order_by(Document.created_at.desc())
            .limit(params.limit)
        )
        .scalars()
        .all()
    )
    return {
        "documents": [
            {
                "document_id": str(doc.id),
                "title": doc.title,
                "file_type": doc.file_type,
                "chunk_count": doc.chunk_count,
                "status": doc.status,
            }
            for doc in docs
        ]
    }


@_timed
def _get_document_preview(db: Session, tenant_id: uuid.UUID, params: DocumentPreviewInput) -> dict[str, Any]:
    doc = _get_document(db, params.document_id)
    if doc.knowledge_base.tenant_id != tenant_id:
        raise ValueError("Document not found in current tenant")
    text = _doc_text(db, doc, params.max_chars)
    return {"document_id": str(doc.id), "title": doc.title, "preview": text, "truncated": len(text) >= params.max_chars}


@_timed
def _summarize_document(db: Session, tenant_id: uuid.UUID, params: SummarizeDocumentInput) -> dict[str, Any]:
    doc = _get_document(db, params.document_id)
    if doc.knowledge_base.tenant_id != tenant_id:
        raise ValueError("Document not found in current tenant")
    text = _doc_text(db, doc, params.max_chars)
    sentences = [s.strip() for s in text.replace("\n", "。").split("。") if s.strip()]
    summary = "。".join(sentences[:5])
    return {"document_id": str(doc.id), "title": doc.title, "summary": summary}


@_timed
def _compare_documents(db: Session, tenant_id: uuid.UUID, params: CompareDocumentsInput) -> dict[str, Any]:
    left = _get_document(db, params.left_document_id)
    right = _get_document(db, params.right_document_id)
    if left.knowledge_base.tenant_id != tenant_id or right.knowledge_base.tenant_id != tenant_id:
        raise ValueError("Document not found in current tenant")
    left_text = _doc_text(db, left, params.max_chars)
    right_text = _doc_text(db, right, params.max_chars)
    ratio = difflib.SequenceMatcher(a=left_text, b=right_text).ratio()
    left_terms = set(left_text.split())
    right_terms = set(right_text.split())
    return {
        "left_document_id": str(left.id),
        "right_document_id": str(right.id),
        "similarity": round(ratio, 4),
        "left_unique_terms": sorted(list(left_terms - right_terms))[:20],
        "right_unique_terms": sorted(list(right_terms - left_terms))[:20],
    }


@_timed
def _create_report(db: Session, tenant_id: uuid.UUID, params: CreateReportInput) -> dict[str, Any]:
    lines = [f"# {params.title}", ""]
    for section in params.sections:
        heading = section.get("heading", "Section")
        content = section.get("content", "")
        lines += [f"## {heading}", "", str(content), ""]
    if params.sources:
        lines += ["## Sources", ""]
        for idx, src in enumerate(params.sources, start=1):
            title = src.get("document_title") or src.get("title") or src.get("document_id") or "source"
            lines.append(f"{idx}. {title} ({src.get('chunk_id', src.get('document_id', 'n/a'))})")
    return {"title": params.title, "content": "\n".join(lines), "sources": params.sources}


@_timed
def _publish_report(db: Session, tenant_id: uuid.UUID, params: PublishReportInput) -> dict[str, Any]:
    return {
        "published": True,
        "destination": params.destination,
        "title": params.title,
        "content_preview": params.content[:500],
    }


@_timed
def _ask_rag(db: Session, tenant_id: uuid.UUID, params: AskRAGInput) -> dict[str, Any]:
    result = _search_kb(db, tenant_id, SearchKBInput(
        knowledge_base_id=params.knowledge_base_id,
        query=params.question,
        top_k=params.top_k,
    ))
    sources = result.data.get("results", []) if result.ok else []
    if not sources:
        answer = "未检索到足够相关的知识库内容，无法基于当前资料回答。"
    else:
        answer = "基于检索到的资料：" + "；".join(src["text"][:120] for src in sources[:3])
    return {"answer": answer, "sources": sources}


class ToolRegistry:
    """In-process tool registry."""

    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def list_specs(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def get(self, name: str) -> ToolSpec:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name]

    def run(self, db: Session, tenant_id: uuid.UUID, name: str, raw_input: dict[str, Any]) -> ToolResult:
        spec = self.get(name)
        try:
            params = spec.input_model.model_validate(raw_input)
        except ValidationError as exc:
            return ToolResult(ok=False, data={}, error=exc.json(), latency_ms=0.0)
        return spec.handler(db, tenant_id, params)


registry = ToolRegistry()
registry.register(ToolSpec("search_kb", "Search knowledge base chunks with BM25 recall.", SearchKBInput, _search_kb))
registry.register(ToolSpec("list_documents", "List documents in a knowledge base.", ListDocumentsInput, _list_documents))
registry.register(ToolSpec("get_document_preview", "Read a document preview from chunks or file.", DocumentPreviewInput, _get_document_preview))
registry.register(ToolSpec("summarize_document", "Create an extractive document summary.", SummarizeDocumentInput, _summarize_document))
registry.register(ToolSpec("compare_documents", "Compare two documents and return differences.", CompareDocumentsInput, _compare_documents))
registry.register(ToolSpec("create_report", "Create a Markdown report artifact.", CreateReportInput, _create_report, permission="write"))
registry.register(ToolSpec(
    "publish_report",
    "Publish a report to an external destination. Requires human approval.",
    PublishReportInput,
    _publish_report,
    permission="write",
    requires_approval=True,
))
registry.register(ToolSpec("ask_rag", "Answer a question with retrieved sources.", AskRAGInput, _ask_rag))
