# SmartRAG - AI 智能知识库系统

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-18.3-blue.svg" alt="React">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>

SmartRAG 是一个基于 RAG（检索增强生成）技术的智能知识库系统，支持文档上传、自动切片、向量检索与智能问答。

---

## 特性

- **多格式文档支持**: PDF、Markdown、Word、TXT
- **智能文档切片**: 可配置的 chunk size 和 overlap
- **向量检索**: 基于 Chroma 的高效向量存储和检索
- **混合检索**: BM25 + 向量检索融合（可选）
- **重排序**: BGE Reranker 提升检索精度（可选）
- **流式输出**: SSE 实时流式响应
- **多知识库**: 支持多租户知识库隔离
- **对话历史**: 支持多轮对话上下文
- **用户认证**: JWT + RBAC 权限管理
- **API 限流**: 基于 IP 和用户的双层限流
- **监控指标**: Prometheus 格式 metrics 端点
- **Docker 部署**: 一键部署到生产环境

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| 前端框架 | React + TypeScript + Vite + Tailwind CSS |
| AI 框架 | LangChain / LlamaIndex |
| 向量数据库 | Chroma / Milvus / pgvector |
| 大模型 | DeepSeek / Qwen / OpenAI / Ollama |
| Embedding | BGE-M3 / BGE-Large |
| 重排序 | BGE-Reranker-v2-m3 |
| 数据库 | PostgreSQL |
| 缓存 | Redis |
| 部署 | Docker + Nginx |

---

## 快速开始

### 前置要求

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker (可选)

### 安装

```bash
# 克隆项目
git clone https://github.com/gaosanliukoushui/smart_rag.git
cd smart_rag

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 复制环境变量配置
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

### 配置

编辑 `.env` 文件，填入你的配置：

```env
# DeepSeek API
DEEPSEEK_API_KEY=your-api-key

# 或使用 Qwen
LLM_PROVIDER=qwen
QWEN_API_KEY=your-api-key
```

### 运行（手动部署）

```bash
# 启动开发服务器
uvicorn app.main:app --reload --port 8000
```

### 运行（Docker 部署）

```bash
cd docker
docker-compose up -d
```

访问 http://localhost:8000/docs 查看 API 文档。

前端开发服务器：

```bash
cd frontend
npm install
npm run dev
```

---

## 项目结构

```
SmartRAG/
├── app/
│   ├── api/              # API 路由
│   │   └── v1/           # API v1 版本
│   ├── capabilities/     # AI 能力封装
│   │   ├── embedding/    # Embedding 模型
│   │   ├── llm/         # LLM 模型
│   │   └── rerank/       # 重排序模型
│   ├── chunkers/         # 文档切片
│   ├── core/             # 核心模块
│   ├── db/               # 数据库连接
│   ├── middleware/       # 中间件（限流、日志）
│   ├── models/           # 数据模型
│   ├── parsers/          # 文档解析器
│   ├── schemas/          # Pydantic Schema
│   ├── services/         # 业务服务
│   └── vectorstores/     # 向量存储
├── docker/               # Docker 配置
├── docs/                 # 详细文档
│   ├── api.md            # API 文档
│   ├── architecture.md   # 架构文档
│   └── deployment.md    # 部署文档
├── frontend/             # React 前端
├── scripts/              # 工具脚本
└── tests/                # 测试
```

---

## API 文档

### 健康检查

```bash
GET /api/v1/health
```

### 文档管理

```bash
# 上传文档
POST /api/v1/documents/upload

# 文档列表
GET /api/v1/documents

# 获取文档
GET /api/v1/documents/{document_id}

# 删除文档
DELETE /api/v1/documents/{document_id}
```

### 知识库管理

```bash
# 创建知识库
POST /api/v1/knowledge-bases

# 知识库列表
GET /api/v1/knowledge-bases

# 获取知识库
GET /api/v1/knowledge-bases/{kb_id}

# 删除知识库
DELETE /api/v1/knowledge-bases/{kb_id}
```

### 问答

```bash
# 发送消息
POST /api/v1/chat
{
  "message": "你的问题",
  "knowledge_base_id": "知识库ID",
  "stream": true
}

# 获取历史
GET /api/v1/chat/history/{session_id}
```

---

## 开发

### 运行测试

```bash
# 运行所有测试
pytest

# 运行带覆盖率
pytest --cov=app tests/

# 运行特定测试
pytest tests/unit/test_chunkers.py
```

### 代码规范

```bash
# 检查代码
ruff check app/

# 格式化代码
ruff format app/
```

---

## 开发路线图

### 阶段一：最小可用 RAG

- [x] ~~项目初始化~~
- [x] ~~配置与基础设施~~
- [x] ~~数据模型~~
- [x] ~~文档解析器~~
- [x] ~~文档切片~~
- [x] ~~AI 能力封装~~
- [x] ~~向量存储~~
- [x] ~~业务服务层~~
- [x] ~~API 路由~~
- [x] ~~主应用入口~~

### 阶段二：重点优化

- [x] ~~混合检索~~
- [x] ~~Prompt 工程~~
- [x] ~~流式输出~~
- [x] ~~对话历史~~
- [x] ~~重排序 (Rerank)~~
- [x] ~~文档管理增强~~
- [x] ~~性能优化~~

### 阶段三：高级特性

- [x] ~~多知识库隔离~~
- [x] ~~Docker 部署~~
- [x] ~~用户认证~~
- [x] ~~本地模型支持~~
- [x] ~~监控与日志~~
- [x] ~~API 限流~~
- [x] ~~文档增量更新~~

详见 [todo_list.md](todo_list.md) 和 [docs/](docs/) 目录下的详细文档：

- [API 文档](docs/api.md) - 所有 API 端点的完整参考
- [架构文档](docs/architecture.md) - 系统架构、RBAC 模型、数据流
- [部署文档](docs/deployment.md) - Docker 部署、手动部署、环境变量说明

---

---

## 贡献

欢迎提交 Issue 和 Pull Request！

---

## 许可证

MIT License
