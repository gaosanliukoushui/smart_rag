"""Vector database initialization script."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings


def init_vector_db():
    """Initialize the vector database."""
    from app.vectorstores.chroma import ChromaVectorStore

    settings = get_settings()
    print(f"Initializing vector database: {settings.CHROMA_PERSIST_DIR}")

    vector_store = ChromaVectorStore(
        persist_directory=settings.CHROMA_PERSIST_DIR,
        collection_name="smartrag",
    )

    print("Vector database initialized successfully!")
    return vector_store


if __name__ == "__main__":
    init_vector_db()
