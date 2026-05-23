# SmartRAG Demo Knowledge Base

SmartRAG is an AI knowledge base application built around retrieval augmented generation.

## Retrieval

SmartRAG supports vector retrieval, hybrid retrieval with BM25, and hybrid retrieval with BGE reranking. Each answer returns source metadata so users can trace the response back to the document chunk.

## Evaluation

The demo evaluation set measures Recall@5, MRR, nDCG, citation coverage, and latency percentiles. These metrics make retrieval quality visible instead of relying only on screenshots.

## Deployment

The application can run with Docker Compose, including FastAPI, PostgreSQL, Redis, and Nginx.
