"""Test embedding model script."""

import asyncio
import sys
from pathlib import Path

__test__ = False

sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_embedding():
    """Test embedding model."""
    from app.services.embedding_service import EmbeddingService

    service = EmbeddingService(model_name="BAAI/bge-m3")

    test_texts = [
        "这是一个测试文本。",
        "RAG是检索增强生成技术。",
        "向量数据库用于存储和检索向量。",
    ]

    print("Loading embedding model...")
    await service.load_model()
    print("Model loaded successfully!")

    print("\nTesting embeddings...")
    embeddings = await service.embed(test_texts)

    for i, (text, emb) in enumerate(zip(test_texts, embeddings)):
        print(f"\nText {i + 1}: {text}")
        print(f"Embedding dimension: {len(emb)}")
        print(f"First 5 values: {emb[:5]}")

    print("\nTesting query embedding...")
    query_emb = await service.embed_query("测试RAG技术")
    print(f"Query embedding dimension: {len(query_emb)}")

    print("\nTesting similarity...")
    similarity = await service.similarity("第一个文本", "第二个文本")
    print(f"Similarity between texts: {similarity:.4f}")

    print("\nAll tests passed!")


if __name__ == "__main__":
    asyncio.run(test_embedding())
