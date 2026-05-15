"""Load sample data script."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def load_sample_data():
    """Load sample data into the knowledge base."""
    from app.services.document_service import DocumentService
    from app.services.chunk_service import ChunkService
    from app.services.embedding_service import EmbeddingService
    from app.vectorstores.chroma import ChromaVectorStore
    from app.config import get_settings

    settings = get_settings()

    sample_documents = [
        {
            "title": "RAG技术介绍",
            "content": """
            RAG（检索增强生成）是一种结合检索系统和语言模型的技术。

            RAG的主要优势包括：
            1. 利用外部知识库提供更准确的答案
            2. 减少大模型的幻觉问题
            3. 可以更新知识而不需要重新训练模型

            RAG的工作流程：
            1. 文档上传和解析
            2. 文档切片处理
            3. 向量化存储
            4. 用户查询向量化
            5. 相似度检索
            6. 生成最终答案
            """,
        },
        {
            "title": "向量数据库基础",
            "content": """
            向量数据库是专门用于存储和检索高维向量的数据库系统。

            主要特点：
            - 高效的相似度搜索
            - 支持海量向量存储
            - 近似最近邻搜索（ANN）

            常见的向量数据库包括：
            - Chroma：轻量级，易于使用
            - Milvus：生产级，功能强大
            - pgvector：基于PostgreSQL

            向量检索的核心算法：
            - 余弦相似度
            - 欧氏距离
            - 点积
            """,
        },
    ]

    print("Initializing services...")
    doc_service = DocumentService(settings.upload_dir)
    chunk_service = ChunkService(chunk_size=200, overlap=50)
    embedding_service = EmbeddingService()
    vector_store = ChromaVectorStore(persist_directory=settings.CHROMA_PERSIST_DIR)

    print("Loading embedding model...")
    await embedding_service.load_model()

    print("\nProcessing sample documents...")
    for doc_data in sample_documents:
        print(f"\nProcessing: {doc_data['title']}")

        chunks = chunk_service.create_chunks("sample", doc_data["content"])
        print(f"Created {len(chunks)} chunks")

        texts = [c.content for c in chunks]
        embeddings = await embedding_service.embed(texts)
        print(f"Generated {len(embeddings)} embeddings")

        metadatas = [
            {"document_title": doc_data["title"], "chunk_index": c.chunk_index}
            for c in chunks
        ]

        await vector_store.add_texts(texts, embeddings, metadatas)
        print(f"Stored in vector database")

    print("\nSample data loaded successfully!")


if __name__ == "__main__":
    asyncio.run(load_sample_data())
