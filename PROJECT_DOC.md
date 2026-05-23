# SmartRAG 项目技术文档

> 本文档是 SmartRAG 智能知识库系统的完整技术参考手册。
> 每次对话开始时阅读即可，无需通读整个项目。

## 一、项目概述

**SmartRAG** 是一个基于 RAG（检索增强生成）架构的 AI 知识库系统，支持文档上传、自动切片、向量检索与智能问答。

**技术栈**

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI + Uvicorn + SQLAlchemy 2.0 |
| 数据库 | PostgreSQL + Redis |
| 向量库 | Chroma（默认，支持 Milvus 可选） |
| Embedding | BAAI/bge-m3（默认） |
| 重排序 | BAAI/bge-reranker-v2-m3 |
| LLM 支持 | DeepSeek / Qwen / OpenAI / Ollama |
| 前端 | React + TypeScript + Vite |
| 部署 | Docker + Nginx |
| 日志 | structlog + Prometheus Metrics |

**项目结构**

```
SmartRAG/
├── app/
│   ├── api/v1/          # API 路由（auth, chat, document, knowledge_base, session, users, roles, metrics...）
│   ├── capabilities/     # LLM/Embedding/Rerank 能力封装（deepseek, qwen, openai, ollama, bge）
│   ├── chunkers/        # 文档切片器（recursive, semantic）
│   ├── core/            # 核心模块（config, security, exceptions, logging）
│   ├── db/              # 数据库连接（database.py, redis.py）
│   ├── middleware/      # 中间件（rate_limit, logging_middleware）
│   ├── models/          # SQLAlchemy ORM 模型（User, Tenant, Role, Permission, KnowledgeBase, Document, Chunk, ChatSession）
│   ├── parsers/         # 文档解析器（pdf, markdown, word, text）
│   ├── schemas/         # Pydantic 请求/响应模型
│   ├── services/        # 业务服务层（chat, document, retrieval, llm, session, quota...）
│   ├── vectorstores/    # 向量存储（chroma 实现）
│   └── main.py         # FastAPI 入口
├── frontend/src/
│   ├── api/client.ts    # API 客户端封装
│   ├── pages/           # 页面（ChatPage, DocumentPage, KnowledgeBasePage, LoginPage）
│   └── components/      # 组件（SourceCard, FileUpload, Header, KnowledgeBaseCard...）
├── data/                # 数据目录（uploads, chroma, smartrag.db）
├── docs/                # 文档（api.md, architecture.md, deployment.md）
├── docker/              # Docker 配置
├── scripts/             # 工具脚本（init_db, test_embedding...）
└── tests/              # 单元测试
```

---

## 二、配置管理

配置文件：`app/config.py`，从 `.env` 读取。

**关键环境变量**

```bash
# 数据库
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/smartrag
REDIS_URL=redis://localhost:6379/0

# LLM（默认 DeepSeek）
LLM_PROVIDER=deepseek           # deepseek / qwen / openai / ollama
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 向量
VECTOR_DB_TYPE=chroma           # chroma（默认）/ milvus
CHROMA_PERSIST_DIR=./data/chroma
EMBEDDING_MODEL=BAAI/bge-m3
RERANKER_MODEL=BAAI/bge-reranker-v2-m3

# 文档处理
CHUNK_SIZE=500                 # 切片 token 数
CHUNK_OVERLAP=100              # 切片重叠 token 数
UPLOAD_DIR=./data/uploads
MAX_UPLOAD_SIZE=104857600      # 100MB
```

---

## 三、数据模型

### 3.1 核心实体关系

```
Tenant (租户)
  ├── KnowledgeBase (知识库) ─── 1:N ──→ Document (文档) ─── 1:N ──→ Chunk (切片)
  ├── User (用户)
  └── UserRole (用户角色关联) ──→ Role ──N:N─→ Permission
```

### 3.2 主要模型

| 模型 | 表名 | 说明 |
|------|------|------|
| `Tenant` | `tenants` | 租户，支持多租户隔离 |
| `User` | `users` | 用户，含 email/username/hashed_password |
| `Role` | `roles` | 角色，含 is_system 系统角色标识 |
| `Permission` | `permissions` | 权限，resource + action 复合唯一 |
| `UserRole` | `user_roles` | 用户-角色-租户三元关联 |
| `KnowledgeBase` | `knowledge_bases` | 知识库，属某租户 |
| `Document` | `documents` | 文档，含 file_hash/version/is_deleted 增量更新字段 |
| `Chunk` | `chunks` | 文档切片，含 embedding_id 指向向量库 |
| `ChatSession` | （Redis + 内存，非 ORM 表） | 对话会话 |

### 3.3 ChatSession 模型

位于 `app/models/chat.py`，**非数据库表**，纯内存对象，通过 `SessionService` 序列化到 Redis：

```python
class ChatSession:
    id: str
    tenant_id: str
    knowledge_base_id: str
    messages: list[Message]   # [{role: "user"|"assistant", content: str, created_at: datetime}]
    created_at: datetime
    updated_at: datetime
```

---

## 四、API 路由概览

基础路径：`/api/v1`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/auth/register` | POST | 用户注册（限流 5/hour） |
| `/auth/login` | POST | 登录，返回 access_token + refresh_token（限流 10/min） |
| `/auth/refresh` | POST | 刷新 Token |
| `/auth/me` | GET | 当前用户信息 |
| `/knowledge-bases` | GET/POST | 知识库列表/创建 |
| `/knowledge-bases/{id}` | GET/DELETE | 知识库详情/删除 |
| `/knowledge-bases/{id}/reload` | POST | 全量重载知识库 |
| `/documents/upload` | POST | 上传文档（限流 30/min） |
| `/documents` | GET | 文档列表（支持按知识库筛选） |
| `/documents/{id}` | GET/DELETE | 文档详情/删除 |
| `/documents/{id}/preview` | GET | 文档预览（max_chars 参数） |
| `/documents/{id}/reparse` | POST | 增量重解析（SHA-256 检测变更，限流 10/min） |
| `/documents/{id}/version` | GET | 获取文档版本信息 |
| `/chat` | POST | 非流式问答，返回 {answer, sources, session_id} |
| `/chat/stream` | POST | **SSE 流式问答**（限流 60/min） |
| `/chat/history/{session_id}` | GET | 获取会话历史 |
| `/chat/session` | POST | 创建新会话 |
| `/chat/sessions` | GET | 列出所有会话 |
| `/users` | GET | 用户列表 |
| `/roles` | GET/POST | 角色管理 |
| `/metrics` | GET | Prometheus 指标 |

---

## 五、核心服务

### 5.1 ChatService (`app/services/chat_service.py`)

RAG 问答核心服务，处理用户问题并返回答案。

**关键方法**

- `ask(question, knowledge_base_id, session, top_k=5, stream=False)` — 非流式问答，返回 `(answer, sources)`
- `stream_ask(question, knowledge_base_id, session, top_k=5)` — 流式问答，返回 `(token_generator, sources, session)`
- `create_session(knowledge_base_id, tenant_id)` — 创建新会话
- `regenerate_last_response(...)` — 重新生成上一条回答

**问答流程**

```
用户问题
  ↓
Query 改写（可选，use_rewrite=True）
  ↓
列表查询检测 → 是 → 直接查 Document 表返回文档清单
  ↓
向量检索（RetrievalService）→ 获取 top_k 相关切片
  ↓
上下文压缩（_compress_context，按 token 预算截断）
  ↓
构建 Prompt（含参考信息 + 历史对话 + 当前问题）
  ↓
LLM 生成答案
  ↓
记录到 ChatSession
```

**列表查询检测**（`_is_list_query`）

当用户问"有哪些文档"、"有什么文档"、"列出文档"等时，直接查 Document 表，不走 RAG 流程：

```python
# 检测模式（支持中文）
_LIST_QUERY_PATTERNS = [
    r"有哪些文档", r"有什么文档", r"文档列表",
    r"上传了哪些", r"有哪些文件", r"列出.*文档",
    r".*文档.*列表", r"知识库.*包含.*文档", r"有几.*文档",
]
```

**对话历史管理**

- 最多保留 20 条消息（`MAX_HISTORY_MESSAGES`）
- 超出时使用滑动窗口，保留最近的消息
- 通过 `SessionService` 持久化到 Redis

**Prompt 模板**

```
你是一个专业的知识库问答助手，基于提供的参考信息回答用户问题。

## 参考信息
{context}

## 历史对话
{history}

## 当前问题
{question}

## 回答要求
1. 仅根据参考信息回答，不要编造信息
2. 如果参考信息不足以回答，请明确说明
3. 回答使用清晰的格式，重要内容可加粗
4. 注明每条信息的来源序号（如"[来源1]"）
5. 保持回答简洁、专业、易读
```

### 5.2 RetrievalService (`app/services/retrieval_service.py`)

向量检索服务，将用户查询转为向量后在 Chroma 中搜索。

```python
async def retrieve(query, top_k=5, similarity_threshold=0.0) -> List[Tuple[str, float, dict]]
# 返回: [(chunk文本, 相似度分数, metadata), ...]
```

### 5.3 HybridRetrievalService (`app/services/hybrid_retrieval_service.py`)

混合检索：向量搜索 + BM25 关键词搜索 → RRF 融合。

```python
async def retrieve(query, top_k=5, fusion_method="rrf")
async def retrieve_with_rerank(query, top_k=5, final_k=3, fusion_method="rrf")
```

### 5.4 LLMService (`app/services/llm_service.py`)

LLM 统一封装，支持 DeepSeek / Qwen / OpenAI / Ollama。

```python
async def generate(prompt) -> str
async def stream_generate(prompt) -> AsyncGenerator[str]
```

### 5.5 SessionService (`app/services/session_service.py`)

对话会话持久化管理。优先 Redis，Redis 不可用时回退到内存字典。

```python
save_session(session)           # 持久化
get_session(session_id)         # 获取
get_session_for_tenant(...)     # 带租户校验的获取
list_sessions(knowledge_base_id) # 列表
delete_session(session_id)      # 删除
clear_history(session_id)       # 清空历史
```

### 5.6 DocumentUpdateService (`app/services/document_update_service.py`)

文档增量更新服务。

```python
async def reparse_document(document_id, force=False)
# 流程：计算文件 SHA-256 → 对比旧 hash → 变化则重新解析切片 → 增量更新向量库
```

### 5.7 QuotaService (`app/services/quota_service.py`)

资源配额服务，基于 Redis 实现。

支持的配额类型：`document_upload`、`chat`、`reparse`、`auth_login`、`auth_register`

### 5.8 ErrorTracker (`app/services/error_tracker.py`)

错误追踪，Redis 存储近期错误记录。

---

## 六、中间件

### 6.1 Rate Limiter (`app/middleware/rate_limit.py`)

基于 SlowAPI 的双层限流：

| 端点 | 限制 |
|------|------|
| 登录 | 10/min |
| 注册 | 5/hour |
| 聊天 | 60/min |
| 文档上传 | 30/min |
| 文档重解析 | 10/min |

### 6.2 Logging Middleware (`app/middleware/logging_middleware.py`)

记录所有请求的 Method、Path、Status、Duration。

---

## 七、向量存储

`app/vectorstores/chroma.py` 实现 `BaseVectorStore` 接口：

- `add_texts()` — 批量添加文本 + 向量
- `similarity_search()` — 向量相似度搜索，返回 `(text, score, metadata)`
- `delete()` — 按 ID 删除向量

向量元数据包含 `{knowledge_base_id, document_id}`，支持按知识库过滤检索结果。

---

## 八、文档解析与切片

### 8.1 解析器 (`app/parsers/`)

| 解析器 | 支持格式 |
|--------|----------|
| `PdfParser` | .pdf |
| `MarkdownParser` | .md, .markdown |
| `WordParser` | .docx |
| `TextParser` | .txt, .text |

统一入口：`get_parser(file_path)` 根据文件扩展名返回对应解析器。

### 8.2 切片器 (`app/chunkers/`)

- `RecursiveChunker` — 按字符数递归切片，默认 500 token，重叠 100 token
- `SemanticChunker` — 语义切片（可选）

---

## 九、前端

### 9.1 API 客户端 (`frontend/src/api/client.ts`)

基于 Axios，特性：
- 自动附加 Bearer Token
- 401 时自动用 refresh_token 刷新
- 刷新队列避免并发刷新雪崩

### 9.2 流式对话 (`ChatPage.tsx`)

`chatApi.stream(data)` 使用 `ReadableStream` API 消费 SSE 事件：

```typescript
// SSE 事件流：
event: session    → data: sessionId      // 首次返回会话 ID
event: message    → data: token字符串     // 流式 token
event: sources    → data: JSON数组        // 来源列表
event: done       → data: ""             // 结束
event: error      → data: {"error":"..."} // 错误
```

### 9.3 页面

| 页面 | 路由 | 说明 |
|------|------|------|
| `LoginPage` | `/login` | 登录/注册 |
| `ChatPage` | `/chat/:kbId` | 对话页面 |
| `DocumentPage` | `/documents/:kbId` | 文档管理 |
| `KnowledgeBasePage` | `/knowledge-bases` | 知识库管理 |

---

## 十、部署

### 10.1 环境要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+

### 10.2 启动

```bash
# 后端
pip install -r requirements.txt
python scripts/init_db.py          # 初始化数据库
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端
cd frontend
npm install && npm run dev
```

### 10.3 Docker

```bash
cd docker
docker-compose up -d
```

---

## 十一、测试

```bash
pytest tests/ -v
```

---

## 十二、最近修改记录

| 日期 | 修改内容 |
|------|----------|
| 2026-05-23 | 文档查询功能：`chat_service.py` 新增 `_is_list_query()` 和 `_list_kb_documents()`，直接查 Document 表返回文档清单；`chat.py` 流式和非流式端点均已集成列表检测 |
| 2026-05-18 | 修复 `_list_kb_documents` 中 UUID 类型转换问题（`kb_id` 字符串需用 `uuid.UUID()` 转换后与 `Document.knowledge_base_id` 比较） |
| 2026-05-16 | 完成全部三个 Milestone：核心 RAG、流式输出+对话历史、企业级多租户+Docker+认证 |
