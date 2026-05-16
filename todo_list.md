# SmartRAG 开发任务清单

> 本文档记录 SmartRAG 项目所有开发任务，完成后请划掉（使用删除线）。
> 更新日期：2026-05-16

---

## 项目概述

**项目名称**：SmartRAG 智能知识库系统
**项目目标**：支持文档上传、自动切片、向量检索与智能问答的 AI 知识库系统
**当前阶段**：阶段三完成

---

## 阶段一：最小可用 RAG ✅

### 1.1 项目初始化

- [x] ~~创建 Git 仓库~~
- [x] ~~创建项目目录结构~~
- [x] ~~配置 requirements.txt~~
- [x] ~~配置 .env.example~~
- [x] ~~配置 .gitignore~~
- [x] ~~创建 README.md~~

### 1.2 配置与基础设施

- [x] ~~创建 app/config.py 配置管理~~
- [x] ~~创建 app/db/database.py 数据库连接~~
- [x] ~~创建 app/db/redis.py Redis 连接~~
- [x] ~~创建 app/core/exceptions.py 自定义异常~~
- [x] ~~创建 app/core/security.py 安全认证基础~~

### 1.3 数据模型

- [x] ~~创建 app/models/document.py 文档模型~~
- [x] ~~创建 app/models/chunk.py 切片模型~~
- [x] ~~创建 app/models/knowledge_base.py 知识库模型~~
- [x] ~~创建 app/models/chat.py 对话模型~~
- [x] ~~创建 app/schemas/common.py 通用 Schema~~
- [x] ~~创建 app/schemas/document.py 文档 Schema~~
- [x] ~~创建 app/schemas/chat.py 对话 Schema~~

### 1.4 文档解析器

- [x] ~~创建 app/parsers/base.py 解析器基类~~
- [x] ~~创建 app/parsers/pdf_parser.py PDF 解析器~~
- [x] ~~创建 app/parsers/markdown_parser.py Markdown 解析器~~
- [x] ~~创建 app/parsers/word_parser.py Word 解析器~~
- [x] ~~创建 app/parsers/text_parser.py 文本解析器~~
- [x] ~~创建 app/parsers/__init__.py 解析器统一入口~~

### 1.5 文档切片

- [x] ~~创建 app/chunkers/base.py 切片基类~~
- [x] ~~创建 app/chunkers/recursive_chunker.py 递归切片器~~
- [x] ~~创建 app/chunkers/semantic_chunker.py 语义切片器（可选）~~

### 1.6 AI 能力封装

- [x] ~~创建 app/capabilities/embedding/bge.py BGE Embedding 模型~~
- [x] ~~创建 app/capabilities/llm/deepseek.py DeepSeek 集成~~
- [x] ~~创建 app/capabilities/llm/qwen.py Qwen 集成~~
- [x] ~~创建 app/capabilities/llm/openai.py OpenAI 集成~~
- [x] ~~创建 app/capabilities/llm/ollama.py Ollama 本地模型（可选）~~

### 1.7 向量存储

- [x] ~~创建 app/vectorstores/base.py 向量存储基类~~
- [x] ~~创建 app/vectorstores/chroma.py Chroma 实现~~
- [ ] 创建 app/vectorstores/milvus.py Milvus 实现（可选）

### 1.8 业务服务层

- [x] ~~创建 app/services/document_service.py 文档处理服务~~
- [x] ~~创建 app/services/chunk_service.py 切片处理服务~~
- [x] ~~创建 app/services/embedding_service.py 向量化服务~~
- [x] ~~创建 app/services/vector_store_service.py 向量存储服务~~
- [x] ~~创建 app/services/retrieval_service.py 检索服务~~
- [x] ~~创建 app/services/llm_service.py LLM 服务~~
- [x] ~~创建 app/services/chat_service.py 问答服务~~

### 1.9 API 路由

- [x] ~~创建 app/api/deps.py 依赖注入~~
- [x] ~~创建 app/api/v1/health.py 健康检查 API~~
- [x] ~~创建 app/api/v1/document.py 文档上传 API~~
- [x] ~~创建 app/api/v1/knowledge_base.py 知识库 API~~
- [x] ~~创建 app/api/v1/chat.py 问答 API~~

### 1.10 主应用入口

- [x] ~~创建 app/main.py FastAPI 入口~~
- [x] ~~创建 app/__init__.py~~

### 1.11 前端界面（可选）

- [ ] 创建基础 Web UI
- [ ] 实现文档上传页面
- [ ] 实现问答页面

### 1.12 测试

- [ ] 创建 tests/conftest.py pytest 配置
- [ ] 编写解析器单元测试
- [ ] 编写切片器单元测试
- [ ] 编写 Embedding 服务测试
- [ ] 编写检索服务测试

---

## 阶段二：重点优化 🔄

### 2.1 混合检索

- [x] ~~创建 app/services/bm25_retriever.py BM25 检索~~
- [x] ~~创建 app/services/hybrid_retrieval_service.py 混合检索服务~~
- [x] ~~实现 RRF 融合算法~~
- [x] ~~编写混合检索测试~~

### 2.2 Prompt 工程

- [x] ~~优化 System Prompt 模板~~
- [x] ~~实现上下文压缩~~
- [x] ~~实现 Query 改写（可选）~~

### 2.3 流式输出

- [x] ~~实现 SSE 流式响应~~
- [x] ~~集成到问答 API~~
- [x] ~~前端流式显示~~

### 2.4 对话历史

- [x] ~~实现对话历史存储~~
- [x] ~~实现多轮对话上下文管理~~
- [x] ~~实现会话管理 API~~

### 2.5 重排序 (Rerank)

- [x] ~~创建 app/capabilities/rerank/bge_reranker.py~~
- [x] ~~RerankService 已实现 (app/services/rerank_service.py)~~
- [x] ~~将 RerankService 集成到 HybridRetrievalService.retrieve_with_rerank()（当前只是截断，未调用 reranker）~~
- [x] ~~编写重排序测试~~

### 2.6 文档管理增强

- [x] ~~实现文档列表 API (GET /documents)~~
- [x] ~~实现文档删除 API (DELETE /documents/{id})~~
- [x] ~~实现文档状态查询 (GET /documents/{id} 含 status 字段)~~
- [x] ~~实现文档预览 API (GET /documents/{id}/preview，支持 max_chars 参数)~~

### 2.7 性能优化

- [x] ~~异步处理优化（服务层已全面使用 async/await）~~
- [x] ~~缓存策略实现（Redis 集成用于会话存储）~~
- [x] ~~批量处理优化（EmbeddingService.embed_batch() + VectorStoreService.add_vectors_batch()）~~

---

## 阶段三：高级特性 ✅

### 3.1 多知识库隔离

- [x] ~~实现多租户架构~~
- [x] ~~实现权限隔离~~
- [x] ~~实现知识库隔离 API~~
- [x] ~~编写多租户测试~~

### 3.2 Docker 部署

- [x] ~~创建 docker/Dockerfile~~
- [x] ~~创建 docker/docker-compose.yml~~
- [x] ~~创建 docker/nginx.conf~~
- [ ] 编写部署文档

### 3.3 用户认证

- [x] ~~实现 JWT 认证~~
- [x] ~~实现用户注册/登录 API~~
- [x] ~~实现权限管理~~
- [x] ~~编写认证测试~~

### 3.4 本地模型支持

- [x] ~~创建 app/capabilities/llm/ollama.py Ollama 本地模型封装~~
- [x] ~~添加 Ollama 专用参数支持（num_ctx, temperature, timeout）~~
- [x] ~~完善 scripts/test_ollama.py 测试脚本~~
- [x] ~~更新 app/config.py 和 .env.example 添加新配置字段~~

### 3.5 监控与日志

- [x] ~~结构化日志配置（app/core/logging.py + structlog）~~
- [x] ~~日志中间件（app/middleware/logging_middleware.py）~~
- [x] ~~Prometheus metrics 端点（GET /metrics, GET /metrics/summary, POST /metrics/reset）~~
- [x] ~~错误追踪服务（app/services/error_tracker.py + Redis）~~
- [x] ~~集成日志到 AuthService、DocumentService~~

### 3.6 API 限流

- [x] ~~slowapi 双层限流中间件（app/middleware/rate_limit.py）~~
- [x] ~~限流端点：登录 10/min、注册 5/hour、聊天 60/min、文档上传 30/min~~
- [x] ~~资源配额服务（app/services/quota_service.py + Redis）~~
- [x] ~~配额规则：document_upload、chat、reparse、auth_login、auth_register~~

### 3.7 文档增量更新

- [x] ~~Document 模型新增字段（file_hash, version, is_deleted, deleted_at）~~
- [x] ~~DocumentUpdateService（变更检测 SHA-256 + reparse + 增量向量化）~~
- [x] ~~API 端点：POST /documents/{id}/reparse、GET /documents/{id}/version~~
- [x] ~~API 端点：POST /knowledge-bases/{id}/reload（全量重载）~~
- [x] ~~单元测试（tests/unit/test_document_update.py）~~

---

## 脚本工具 🔄

- [ ] 创建 scripts/init_db.py 数据库初始化
- [ ] 创建 scripts/init_vector_db.py 向量库初始化
- [ ] 创建 scripts/test_embedding.py Embedding 测试
- [ ] 创建 scripts/load_sample_data.py 示例数据加载

---

## 文档 🔄

- [ ] 创建 docs/api.md API 文档
- [ ] 创建 docs/architecture.md 架构文档
- [ ] 创建 docs/deployment.md 部署文档
- [ ] 更新 README.md

---

## 项目里程碑 🔄

### Milestone 1: 核心功能 (MVP)
> 目标：完成一个可工作的 RAG 系统

- [ ] 文档上传和解析
- [ ] 向量化和检索
- [ ] 基础问答
- [ ] 完成时间：_____

### Milestone 2: 生产就绪
> 目标：提升质量和稳定性

- [ ] 混合检索
- [ ] 流式输出
- [ ] 对话历史
- [ ] 完成时间：_____

### Milestone 3: 企业级功能
> 目标：生产级别部署

- [x] ~~多知识库~~
- [x] ~~Docker 部署~~
- [x] ~~用户认证~~
- [ ] 完成时间：2026-05-16

---

## 更新日志

| 日期 | 更新内容 | 更新人 |
|------|----------|--------|
| 2026-05-16 | 完成阶段三全部内容：多租户架构(Tenant/User/Role/Permission ORM模型)、Docker部署完善(多阶段Dockerfile/健康检查/nginx)、完整RBAC认证(JWT注册登录/刷新/权限管理API)、119个测试全部通过 | - |
| 2026-05-16 | 完成 2.3 前端流式显示：重构 chatApi.stream() 使用 ReadableStream API + 正确解析 event 分支 + 自动补全 session_id + sources 事件驱动获取；修复 ChatPage 流式逻辑（消除重复/无效代码）；SourceCard 兼容后端 StreamSource 格式；更新日志：前端修复/后端优化/2.3 全部完成 | - |
| 2026-05-16 | 完成 2.4 对话历史管理：新增 Redis 持久化存储 + SessionService + 滑动窗口上下文裁剪 + 会话管理 API（list/delete/clear）；重构 ChatService 使用 SessionService；ChatSession 模型新增 trim_messages/get_messages_summary 方法 |
| 2026-05-16 | 同步 todo_list 状态：2.5 重排序(BGE reranker 文件已创建，RerankService 已实现，集成步骤待完成)、2.6 文档管理(列表/删除/状态查询已实现，预览待完成)、2.7 性能优化(异步/缓存已实现，批量处理待完成) | - |
| 2026-05-16 | 完成 2.5 重排序：RerankService 集成到 HybridRetrievalService/RetrievalService；新增 28 个测试全部通过；完成 2.6 文档预览 API (GET /documents/{id}/preview)；完成 2.7 批量处理优化（embed_batch + add_vectors_batch） | - |
| 2026-05-15 | 初始创建任务清单 | - |
| 2026-05-15 | 完成 Git 仓库初始化，连接 GitHub，上传初始提交 | - |

---

## 使用说明

1. **添加新任务**：在对应阶段添加 `- [ ] 任务名称`
2. **完成任务**：将 `- [ ]` 改为 `- [x]`，文字使用删除线 `~~任务名称~~`
3. **添加里程碑**：在项目里程碑部分添加新的里程碑
4. **记录更新**：在更新日志中记录每次更新

### 标记说明

| 标记 | 含义 |
|------|------|
| `[ ]` | 未开始 |
| `[x]` | 已完成 |
| `[~]` | 进行中 |
| `~~text~~` | 已删除/完成（删除线） |

---

*保持这个文档更新，每个任务完成后及时标记。*
