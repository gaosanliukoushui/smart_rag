"""Custom exceptions for the application."""


class SmartRAGException(Exception):
    """Base exception for SmartRAG."""

    def __init__(self, message: str, code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class DocumentParseError(SmartRAGException):
    """Raised when document parsing fails."""

    def __init__(self, message: str):
        super().__init__(message, code="DOCUMENT_PARSE_ERROR")


class VectorStoreError(SmartRAGException):
    """Raised when vector store operations fail."""

    def __init__(self, message: str):
        super().__init__(message, code="VECTOR_STORE_ERROR")


class EmbeddingError(SmartRAGException):
    """Raised when embedding generation fails."""

    def __init__(self, message: str):
        super().__init__(message, code="EMBEDDING_ERROR")


class LLMError(SmartRAGException):
    """Raised when LLM operations fail."""

    def __init__(self, message: str):
        super().__init__(message, code="LLM_ERROR")


class KnowledgeBaseNotFoundError(SmartRAGException):
    """Raised when knowledge base is not found."""

    def __init__(self, kb_id: str):
        super().__init__(f"Knowledge base not found: {kb_id}", code="KB_NOT_FOUND")


class DocumentNotFoundError(SmartRAGException):
    """Raised when document is not found."""

    def __init__(self, doc_id: str):
        super().__init__(f"Document not found: {doc_id}", code="DOC_NOT_FOUND")
