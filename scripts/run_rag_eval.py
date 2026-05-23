"""Run a lightweight RAG retrieval evaluation from a JSONL dataset.

The dataset is intentionally self-contained so CI can run without downloading
embedding or LLM models. It evaluates the retriever contract and reports the
same metrics used to compare live retrieval modes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
import time
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings
from app.services.bm25_retriever import BM25Retriever


def load_cases(path: Path) -> list[dict]:
    cases = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def dcg(hits: Iterable[int]) -> float:
    return sum(hit / math.log2(rank + 2) for rank, hit in enumerate(hits))


def deterministic_embedding(text: str, dim: int = 64) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = [((digest[i % len(digest)] / 255.0) * 2) - 1 for i in range(dim)]
    norm = sum(v * v for v in values) ** 0.5 or 1.0
    return [v / norm for v in values]


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def keyword_overlap(query: str, text: str) -> float:
    q_chars = {ch for ch in query.lower() if ch.strip()}
    t_chars = {ch for ch in text.lower() if ch.strip()}
    if not q_chars:
        return 0.0
    return len(q_chars & t_chars) / len(q_chars)


def rrf_fuse(*ranked_lists: list[tuple[str, float, dict]], k: int = 60) -> list[tuple[str, float, dict]]:
    scores: dict[str, float] = {}
    payload: dict[str, tuple[str, dict]] = {}
    for ranked in ranked_lists:
        for rank, (text, _score, meta) in enumerate(ranked, start=1):
            key = meta.get("chunk_id", text)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            payload[key] = (text, meta)
    fused = [(payload[key][0], score, payload[key][1]) for key, score in scores.items()]
    fused.sort(key=lambda item: item[1], reverse=True)
    return fused


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int((len(ordered) - 1) * pct))
    return ordered[index]


def retrieve_case(case: dict, top_k: int, tokenizer: str, mode: str) -> list[tuple[str, float, dict]]:
    docs = case["documents"]
    metadata = [{"document_id": doc["document_id"], "chunk_id": doc["chunk_id"]} for doc in docs]

    query_embedding = deterministic_embedding(case["question"])
    vector_results = [
        (doc["text"], dot(query_embedding, deterministic_embedding(doc["text"])), meta)
        for doc, meta in zip(docs, metadata)
    ]
    vector_results.sort(key=lambda item: item[1], reverse=True)

    if mode == "vector":
        return vector_results[:top_k]

    retriever = BM25Retriever(tokenizer=tokenizer)
    retriever.build_index([doc["text"] for doc in docs], metadata)
    bm25_results = retriever.search_with_scores(case["question"], top_k=max(top_k * 3, len(docs)))
    fused = rrf_fuse(vector_results, bm25_results)

    if mode == "hybrid_rerank":
        candidates = fused[: max(top_k * 3, top_k)]
        reranked = [
            (text, keyword_overlap(case["question"], text) + score, meta)
            for text, score, meta in candidates
        ]
        reranked.sort(key=lambda item: item[1], reverse=True)
        return reranked[:top_k]

    return fused[:top_k]


def evaluate_case(case: dict, top_k: int, tokenizer: str, mode: str) -> dict:
    start = time.perf_counter()
    results = retrieve_case(case, top_k, tokenizer, mode)
    latency_ms = (time.perf_counter() - start) * 1000

    expected_docs = set(case.get("expected_doc_ids", []))
    expected_chunks = set(case.get("expected_chunk_ids", []))
    retrieved_docs = [meta.get("document_id") for _, _, meta in results]
    retrieved_chunks = [meta.get("chunk_id") for _, _, meta in results]

    doc_hits = [1 if doc_id in expected_docs else 0 for doc_id in retrieved_docs]
    chunk_hits = [1 if chunk_id in expected_chunks else 0 for chunk_id in retrieved_chunks]
    chunk_hit = any(chunk_id in expected_chunks for chunk_id in retrieved_chunks)
    first_hit_rank = next((idx + 1 for idx, hit in enumerate(doc_hits) if hit), None)
    ideal_hits = [1] * min(len(expected_chunks or expected_docs), top_k)

    return {
        "id": case["id"],
        "recall": 1.0 if any(doc_hits) else 0.0,
        "mrr": 1.0 / first_hit_rank if first_hit_rank else 0.0,
        "ndcg": dcg(chunk_hits if expected_chunks else doc_hits) / dcg(ideal_hits) if ideal_hits else 0.0,
        "citation_coverage": 1.0 if chunk_hit else 0.0,
        "latency_ms": latency_ms,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=settings.RAG_EVAL_DATASET)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--tokenizer", default=settings.BM25_TOKENIZER)
    parser.add_argument("--mode", choices=["vector", "hybrid", "hybrid_rerank"], default="hybrid")
    parser.add_argument("--compare-modes", action="store_true")
    args = parser.parse_args()

    cases = load_cases(Path(args.dataset))
    modes = ["vector", "hybrid", "hybrid_rerank"] if args.compare_modes else [args.mode]
    output = {}
    for mode in modes:
        results = [evaluate_case(case, args.top_k, args.tokenizer, mode) for case in cases]
        output[mode] = {
            "summary": {
                "cases": len(results),
                f"recall@{args.top_k}": statistics.fmean(r["recall"] for r in results) if results else 0.0,
                "mrr": statistics.fmean(r["mrr"] for r in results) if results else 0.0,
                "ndcg": statistics.fmean(r["ndcg"] for r in results) if results else 0.0,
                "citation_coverage": statistics.fmean(r["citation_coverage"] for r in results) if results else 0.0,
                "p50_latency_ms": percentile([r["latency_ms"] for r in results], 0.50),
                "p95_latency_ms": percentile([r["latency_ms"] for r in results], 0.95),
            },
            "cases": results,
        }
    print(json.dumps(output if args.compare_modes else output[args.mode], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
