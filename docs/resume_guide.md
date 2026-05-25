# SmartRAG 简历写法与面试讲法

本文档回答两个问题：

1. SmartRAG 写在简历里应该怎么写。
2. 面试时如何把它讲成一个有竞争力的 Agent 项目，而不是普通 RAG demo。

## 1. 项目标题

推荐标题：

```text
SmartRAG：面向企业知识库的 RAG-powered Agent 系统
```

或者：

```text
企业知识库 Agent 系统：支持 RAG 检索、工具调用、Trace 可视化与 Agent Eval
```

不建议写：

```text
智能问答系统
```

这个说法太普通，容易被理解成“上传文档 + 调 LLM API”。

也不建议写：

```text
通用 Multi-Agent 框架
```

因为当前项目不是多 Agent 协作框架，而是单 Agent Runtime + 工具系统 + RAG 能力。写得过大反而容易被追问穿。

## 2. 简历项目描述

可以写成：

```text
SmartRAG 是一个面向企业知识库的 RAG-powered Agent 系统，支持文档解析、向量检索、BM25 混合检索、BGE rerank、SSE 流式问答、来源追溯、Agent 任务规划、工具调用、Human-in-the-loop 审批和 Trace 可视化。系统构建了 RAG/Agent 双评测脚本，输出 Recall@5、MRR、task_success_rate、tool_call_accuracy、citation_correctness、p95 latency 等指标，并通过 Docker Compose、Prometheus Metrics 和 CI 保证可复现部署。
```

如果简历空间有限，可以压缩为：

```text
实现企业知识库 RAG-powered Agent 系统，支持文档解析、Chroma 向量检索、BM25 混合检索、rerank、Agent Tool Registry、Plan-and-Execute、Human Approval、Trace UI 和 Agent Eval；构建 33 条 Agent 任务集，评估任务成功率、工具调用准确率、引用正确率和延迟。
```

## 3. 推荐简历 Bullet

### 版本 A：AI/RAG 应用开发岗

```text
- 设计并实现企业知识库 RAG 系统，支持 PDF/Markdown/Word/TXT 解析、chunk 切片、BGE embedding、Chroma 持久化向量库、BM25 混合检索、BGE rerank 和 SSE 流式问答。
- 构建可追溯回答链路，sources 返回 document_id、chunk_id、document_title、rank、score，并支持前端点击回溯到文档片段，降低模型幻觉风险。
- 编写 RAG 评测集与 run_rag_eval.py，对比 vector/hybrid/hybrid_rerank 三种链路，输出 Recall@5、MRR、nDCG、引用覆盖率和 p95 延迟。
- 接入 Prometheus Metrics，记录 embedding/retrieval/LLM latency、empty retrieval count 和 top-k score 分布，并通过 GitHub Actions 运行 pytest、ruff、前端 build 和 eval smoke test。
```

### 版本 B：Agent 应用开发岗

```text
- 将知识库 RAG 系统升级为 RAG-powered Agent，设计 AgentTask、AgentStep、ToolCall、AgentArtifact、ApprovalEvent 等运行时模型，支持任务规划、工具执行、trace 落库和 Markdown 报告产出。
- 实现 Tool Registry，封装 search_kb、list_documents、summarize_document、compare_documents、ask_rag、create_report、publish_report 等工具；每个工具具备 Pydantic JSON Schema 校验、权限声明和错误返回。
- 实现 Plan-and-Execute Executor，支持 rule/LLM planner、schema 校验、deterministic fallback、暂停/恢复/取消、step retry、空召回 query rewrite 和 no-sources failure artifact。
- 设计 Human-in-the-loop 审批机制，外部发布类写操作进入 needs_approval，审批/拒绝事件落库，并在任务恢复时重建已完成步骤上下文，避免 sources 丢失。
- 构建 Agent Eval，使用 33 条任务评测 task_success_rate、tool_call_accuracy、citation_correctness、schema_valid_rate、avg_steps 和 p95 latency；支持静态评测和真实执行评测两种模式。
- 实现 Agent 工作台前端，展示任务状态、执行进度、报告、证据来源、审批事件和 step 级恢复操作，使 Agent 执行过程可解释、可恢复、可演示。
```

### 版本 C：后端/平台工程岗

```text
- 基于 FastAPI + SQLAlchemy 设计多租户知识库后端，支持 JWT 认证、RBAC、租户隔离、文档上传、增量重解析、软删除和 Chroma 向量库持久化。
- 实现 Agent Runtime 状态机，支持 pending/planning/running/needs_approval/paused/cancelled/failed/completed 等状态，并提供任务暂停、恢复、取消和 step retry API。
- 建立可观测性体系，/metrics 暴露 RAG latency、Agent tool call、step latency、approval count、token/cost 等 Prometheus 指标。
- 完成 Docker Compose、Alembic baseline migration、CI、demo seed 和评测脚本，保证项目可复现、可测试、可部署。
```

## 4. 简历中建议保留的数字

可以写：

```text
141 个单元测试通过
33 条 Agent eval tasks
RAG eval 输出 Recall@5 / MRR / nDCG / citation coverage
Agent eval 输出 task_success_rate / tool_call_accuracy / citation_correctness / schema_valid_rate
```

注意：

- 如果你没有真实线上流量，不要写 QPS、DAU。
- 如果 token/cost 是估算，不要写“真实成本优化 xx%”。
- 如果 LLM planner 还没用真实 API 跑 demo，不要写“已在线上稳定使用 LLM planner”，可以写“支持 LLM planner + fallback”。

## 5. 面试 1 分钟讲法

可以这样说：

```text
这个项目最开始是一个企业知识库 RAG 系统，支持文档上传、解析、切片、embedding、Chroma 向量检索、BM25 混合检索、rerank 和流式问答。后来我把它升级成了任务型 Agent：用户不只是问一个问题，而是提交一个目标，例如“根据部署文档生成上线 checklist 并指出缺失监控项”。

系统会先由 Planner 生成结构化步骤，再通过 Tool Registry 校验每个工具调用，Executor 按步骤执行 search_kb、summarize_document、compare_documents、create_report 等工具。每一步的 input、output、latency、error、token usage 都会落库形成 trace。外部发布类操作会进入 human approval，审批后可以恢复执行。

为了证明它不是 demo，我还做了 RAG eval 和 Agent eval。Agent eval 有 33 条任务，统计 task_success_rate、tool_call_accuracy、citation_correctness、schema_valid_rate 和 p95 latency。同时前端有 Agent 工作台，可以看到报告、证据来源、执行进度、审批事件和 step retry。
```

## 6. 面试 3 分钟讲法

### 6.1 背景

```text
我做这个项目的目标不是单纯做“知识库问答”，而是想把企业知识库里的文档变成可执行任务的上下文。例如上线前检查、文档对比、监控项审计、报告生成，这些任务需要多步检索、阅读、归纳和输出，普通 RAG 的一次问答不够。
```

### 6.2 RAG 基础

```text
底层 RAG 链路包括文档解析、chunk 切片、embedding、Chroma 持久化向量库和知识库过滤。检索模式支持 vector、hybrid 和 hybrid_rerank。hybrid 使用 BM25 + 向量检索融合，BM25 针对中文做了 char n-gram tokenizer，rerank 使用 BGE reranker。
```

### 6.3 Agent Runtime

```text
Agent 层我设计了 AgentTask、AgentStep、ToolCall、AgentArtifact 和 ApprovalEvent。Task 记录整体目标和状态，Step 记录计划步骤，ToolCall 记录每次工具输入输出，Artifact 记录最终报告，ApprovalEvent 记录人工审批。
```

### 6.4 Planner 和工具系统

```text
Planner 支持 rule、llm_fallback 和 llm 三种模式。LLM planner 只能输出结构化 JSON，并且 tool_name 必须来自 Tool Registry，每个 tool_input 都要经过 Pydantic schema 校验。如果 LLM 输出非法 JSON、非法工具或缺字段，llm_fallback 会回退到 deterministic planner，并记录 planner_error。
```

### 6.5 可靠性

```text
我做了几类恢复能力：任务可以 pause、resume、cancel，也可以从某个 step retry；恢复时会重建已完成步骤的上下文，避免后续报告丢失 sources。search_kb 如果空召回，会做一次 query rewrite 并提高 top_k。没有 sources 时不会生成普通报告，而是生成 failure artifact，提示需要补充证据。
```

### 6.6 评测和观测

```text
项目有两套评测：RAG eval 评估 Recall@5、MRR、nDCG、引用覆盖率；Agent eval 评估 task_success_rate、tool_call_accuracy、citation_correctness、schema_valid_rate、avg_steps 和 p95 latency。/metrics 暴露 RAG latency、Agent tool call、approval count、token/cost 等 Prometheus 指标。
```

## 7. 高频追问与回答

### Q1：你这个和普通 RAG 有什么区别？

回答：

```text
普通 RAG 是一次问答链路：问题 -> 检索 -> 生成。这个项目在 RAG 之上做了 Agent Runtime：用户提交的是任务，系统会规划步骤、调用多个工具、保存 trace、生成 artifact，并且支持审批、暂停、恢复和 step retry。RAG 是 Agent 的一个工具能力，不是整个系统的边界。
```

### Q2：怎么防止 LLM planner 乱调工具？

回答：

```text
LLM planner 只负责生成结构化 JSON plan，不能直接执行。执行前会检查 tool_name 是否在 Tool Registry 中，并用 Pydantic schema 校验 tool_input。工具本身还有 permission 和 requires_approval，高风险写操作会进入人工审批。如果 planner 输出不合法，llm_fallback 会回退到规则 planner。
```

### Q3：任务执行失败怎么办？

回答：

```text
失败分几层处理。工具输入缺字段会自动补齐；search 空召回会 query rewrite 后重试；单个 step 失败可以从该 step retry；任务可以 pause/resume/cancel。恢复执行时会重建前面已完成步骤的 context，保证后续报告和 sources 不丢失。没有证据时会生成 failure artifact，而不是编造报告。
```

### Q4：怎么证明效果？

回答：

```text
我没有只靠主观 demo，而是写了 eval。RAG eval 会输出 Recall@5、MRR、nDCG、引用覆盖率和延迟；Agent eval 有 33 条任务，覆盖问答、摘要、对比、报告、审批、失败恢复等场景，输出 task_success_rate、tool_call_accuracy、citation_correctness、schema_valid_rate 和 p95 latency。CI 会跑单测、lint、前端 build 和 eval smoke test。
```

### Q5：为什么现在用 BackgroundTasks，不用 Celery？

回答：

```text
当前项目定位是可复现的简历项目和轻量 demo，FastAPI BackgroundTasks 能证明异步 task_id 返回、后台执行和前端状态轮询这条链路。生产化下一步我会换成 Redis + RQ/Celery/Arq，用持久化队列支持 worker 重启恢复、并发控制、超时和取消。
```

### Q6：权限和审批怎么做？

回答：

```text
系统本身有 JWT、Tenant 和 RBAC。Agent tool 也声明 permission，比如 read/write。read 工具可以直接执行，write 或外部发布工具会检查权限并进入 needs_approval。审批事件会落库为 ApprovalEvent，包括 requested、approved、rejected。
```

### Q7：你在项目里最有技术含量的部分是什么？

回答：

```text
我认为不是接 LLM API，而是把 Agent 当成一个可控的工程系统：工具 schema 校验、权限和审批、trace 落库、任务状态机、恢复执行、failure artifact、eval 指标和 metrics。这样面试官可以看到系统能力，而不只是一个最终回答。
```

## 8. 不要这样写

不要写：

```text
实现了一个智能 Agent，可自动完成所有任务。
```

问题：太泛，容易被追问泛化能力。

不要写：

```text
实现 Multi-Agent 协作。
```

问题：当前项目不是多 Agent 协作，写了会被追问。

不要写：

```text
显著提升大模型推理能力。
```

问题：项目偏应用工程，不是模型算法训练或推理优化。

## 9. 最推荐的一版简历成稿

如果只能放一个项目，可以这样写：

```text
SmartRAG：企业知识库 RAG-powered Agent 系统

- 基于 FastAPI + React + SQLAlchemy 实现多租户企业知识库系统，支持文档解析、chunk 切片、BGE embedding、Chroma 持久化向量库、BM25 混合检索、BGE rerank、SSE 流式问答和来源追溯。
- 设计 Agent Runtime，抽象 AgentTask、AgentStep、ToolCall、AgentArtifact、ApprovalEvent，支持任务规划、工具执行、trace 落库、Markdown 报告产出和 Human-in-the-loop 审批。
- 实现 Tool Registry 与 Plan-and-Execute Executor，工具调用经过 Pydantic JSON Schema 校验和 RBAC 权限控制；支持 rule/LLM planner、deterministic fallback、暂停/恢复/取消和 step 级 retry。
- 构建 Agent 工作台，展示任务状态、执行进度、报告、证据来源、审批事件和恢复操作；sources 支持 document_id/chunk_id 回溯，降低幻觉和不可验证回答风险。
- 编写 RAG/Agent 评测脚本，输出 Recall@5、MRR、nDCG、task_success_rate、tool_call_accuracy、citation_correctness、schema_valid_rate 和 p95 latency；通过 pytest、ruff、前端 build、Docker Compose 和 Prometheus Metrics 保证可复现部署。
```

## 10. 按岗位调整

### Agent 应用开发岗

突出：

- Agent Runtime
- Tool Registry
- Planner/Executor
- Human approval
- Trace UI
- Agent eval

少写：

- 普通 CRUD
- 前端样式细节

### RAG 应用开发岗

突出：

- Chroma 持久化
- hybrid retrieval
- rerank
- 中文 BM25
- sources 回溯
- RAG eval

少写：

- 复杂任务状态机

### 后端工程岗

突出：

- 多租户
- RBAC
- SQLAlchemy 模型
- 异步任务
- metrics
- CI/Docker/Alembic

少写：

- 模型算法名堆砌

## 11. 30 秒 Demo 讲解稿

```text
这里我演示一个知识库 Agent 任务。用户提交“根据部署文档生成上线 checklist，并指出缺失监控项”。系统会先生成执行计划，然后调用 list_documents、search_kb、ask_rag 和 create_report 等工具。左侧是任务列表，中间是最终报告和证据来源，右侧是执行进度。每个 source 都可以回溯到具体 document 和 chunk。如果任务需要外部发布，会进入 needs_approval，审批后才继续执行 publish_report。整个过程会落库为 trace，并可以用 Agent Eval 评估工具调用准确率、引用正确率和延迟。
```

## 12. 项目当前最适合投的岗位

适合：

- Agent 应用开发
- RAG 应用开发
- AI 应用后端工程师
- LLMOps / AgentOps 初级到中级岗位
- 企业知识库/智能客服/智能办公方向岗位

不太适合作为唯一项目投：

- 大模型预训练算法岗
- 强化学习研究岗
- 多模态基础模型研究岗
- 高性能推理引擎开发岗

如果投算法/研究岗，需要额外准备模型训练、论文复现、评测实验或推理优化项目。
