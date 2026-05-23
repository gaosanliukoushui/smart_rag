# SmartRAG Demo Walkthrough

This walkthrough is designed for resume/project reviews. It proves the app can be booted, seeded, queried, and evaluated with reproducible commands.

## 1. Start Services

```bash
cd docker
docker-compose up -d
```

## 2. Seed Demo Data

Fast local demo without downloading embedding models:

```bash
python scripts/seed_demo.py --mock-embeddings
```

Full RAG path with the configured embedding model:

```bash
python scripts/seed_demo.py
```

Demo login:

```text
username: demo
password: DemoPass123!
```

## 3. Run Retrieval Evaluation

```bash
python scripts/run_rag_eval.py --dataset evals/qa_set.jsonl --compare-modes
```

Expected smoke-test signal:

| Mode | Recall@5 | MRR | nDCG | Citation Coverage |
|------|----------|-----|------|-------------------|
| vector | 1.00 | 1.00 | ~0.75 | 1.00 |
| hybrid | 1.00 | 1.00 | ~0.75 | 1.00 |
| hybrid_rerank | 1.00 | 1.00 | 1.00 | 1.00 |

## 4. Run Agent Evaluation

```bash
python scripts/run_agent_eval.py --dataset agent_evals/tasks.jsonl
python scripts/run_agent_eval.py --dataset agent_evals/tasks.jsonl --mode execute
```

Record one real LLM planner artifact after configuring an API key:

```bash
python scripts/record_llm_planner_demo.py --output docs/assets/llm-planner-demo.json
```

Expected smoke-test signal:

| Metric | Expected |
|--------|----------|
| task_success_rate | 1.00 |
| tool_call_accuracy | 1.00 |
| citation_correctness | 1.00 |
| schema_valid_rate | 1.00 |

## 5. Try Agent Trace UI

Open `/agent`, select `SmartRAG Demo Knowledge Base`, then submit:

```text
根据知识库里的部署文档，生成一份上线 checklist，并指出缺失的监控项。
```

The page should show the final Markdown report and a trace timeline with every tool call, input/output, status, and latency.
The trace header also shows planner mode, total tool calls, estimated token usage, and estimated cost.
The Sources block links each citation back to its document/chunk endpoint for evidence inspection.

## 6. Screenshot / GIF Checklist

Capture these screens for README or portfolio use:

1. Login with the demo user.
2. Open `SmartRAG Demo Knowledge Base`.
3. Ask: `SmartRAG 支持哪些检索方式？`
4. Show the streaming answer and source card with `document_id`, `chunk_id`, score, and rank available in the API payload.
5. Open `/agent`, run the checklist task, and show the trace timeline.
6. Open `/metrics` and show RAG plus Agent metrics.
7. Run `scripts/run_rag_eval.py --compare-modes` and `scripts/run_agent_eval.py` in a terminal beside the browser.
8. Save the final GIF as `docs/assets/agent-trace-demo.gif` if you want README playback.

Suggested recording length: 30-45 seconds.
