# SmartRAG 开发任务清单

> 本文档记录 SmartRAG 项目所有开发任务，完成后请划掉（使用删除线）。
> 更新日期：2026-05-15

---

## 项目概述

**项目名称**：SmartRAG 智能知识库系统
**项目目标**：支持文档上传、自动切片、向量检索与智能问答的 AI 知识库系统
**当前阶段**：准备开始

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

- [ ] 创建 app/config.py 配置管理
- [ ] 创建 app/db/database.py 数据库连接
- [ ] 创建 app/db/redis.py Redis 连接
- [ ] 创建 app/core/exceptions.py 自定义异常
- [ ] 创建 app/core/security.py 安全认证基础

### 1.3 数据模型

- [ ] 创建 app/models/document.py 文档模型
- [ ] 创建 app/models/chunk.py 切片模型
- [ ] 创建 app/models/knowledge_base.py 知识库模型
- [ ] 创建 app/models/chat.py 对话模型
- [ ] 创建 app/schemas/common.py 通用 Schema
- [ ] 创建 app/schemas/document.py 文档 Schema
- [ ] 创建 app/schemas/chat.py 对话 Schema

### 1.4 文档解析器

- [ ] 创建 app/parsers/base.py 解析器基类
- [ ] 创建 app/parsers/pdf_parser.py PDF 解析器
- [ ] 创建 app/parsers/markdown_parser.py Markdown 解析器
- [ ] 创建 app/parsers/word_parser.py Word 解析器
- [ ] 创建 app/parsers/text_parser.py 文本解析器
- [ ] 创建 app/parsers/__init__.py 解析器统一入口

### 1.5 文档切片

- [ ] 创建 app/chunkers/base.py 切片基类
- [ ] 创建 app/chunkers/recursive_chunker.py 递归切片器
- [ ] 创建 app/chunkers/semantic_chunker.py 语义切片器（可选）

### 1.6 AI 能力封装

- [ ] 创建 app/capabilities/embedding/bge.py BGE Embedding 模型
- [ ] 创建 app/capabilities/llm/deepseek.py DeepSeek 集成
- [ ] 创建 app/capabilities/llm/qwen.py Qwen 集成
- [ ] 创建 app/capabilities/llm/openai.py OpenAI 集成
- [ ] 创建 app/capabilities/llm/ollama.py Ollama 本地模型（可选）

### 1.7 向量存储

- [ ] 创建 app/vectorstores/base.py 向量存储基类
- [ ] 创建 app/vectorstores/chroma.py Chroma 实现
- [ ] 创建 app/vectorstores/milvus.py Milvus 实现（可选）

### 1.8 业务服务层

- [ ] 创建 app/services/document_service.py 文档处理服务
- [ ] 创建 app/services/chunk_service.py 切片处理服务
- [ ] 创建 app/services/embedding_service.py 向量化服务
- [ ] 创建 app/services/vector_store_service.py 向量存储服务
- [ ] 创建 app/services/retrieval_service.py 检索服务
- [ ] 创建 app/services/llm_service.py LLM 服务
- [ ] 创建 app/services/chat_service.py 问答服务

### 1.9 API 路由

- [ ] 创建 app/api/deps.py 依赖注入
- [ ] 创建 app/api/v1/health.py 健康检查 API
- [ ] 创建 app/api/v1/document.py 文档上传 API
- [ ] 创建 app/api/v1/knowledge_base.py 知识库 API
- [ ] 创建 app/api/v1/chat.py 问答 API

### 1.10 主应用入口

- [ ] 创建 app/main.py FastAPI 入口
- [ ] 创建 app/__init__.py

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

- [ ] 创建 app/services/bm25_retriever.py BM25 检索
- [ ] 创建 app/services/hybrid_retrieval_service.py 混合检索服务
- [ ] 实现 RRF 融合算法
- [ ] 编写混合检索测试

### 2.2 Prompt 工程

- [ ] 优化 System Prompt 模板
- [ ] 实现上下文压缩
- [ ] 实现 Query 改写（可选）

### 2.3 流式输出

- [ ] 实现 SSE 流式响应
- [ ] 集成到问答 API
- [ ] 前端流式显示

### 2.4 对话历史

- [ ] 实现对话历史存储
- [ ] 实现多轮对话上下文管理
- [ ] 实现会话管理 API

### 2.5 重排序 (Rerank)

- [ ] 创建 app/capabilities/rerank/bge_reranker.py
- [ ] 集成到检索流程
- [ ] 编写重排序测试

### 2.6 文档管理增强

- [ ] 实现文档列表 API
- [ ] 实现文档删除 API
- [ ] 实现文档状态查询
- [ ] 实现文档预览

### 2.7 性能优化

- [ ] 异步处理优化
- [ ] 缓存策略实现
- [ ] 批量处理优化

---

## 阶段三：高级特性 🔄

### 3.1 多知识库隔离

- [ ] 实现多租户架构
- [ ] 实现权限隔离
- [ ] 实现知识库隔离 API
- [ ] 编写多租户测试

### 3.2 Docker 部署

- [ ] 创建 docker/Dockerfile
- [ ] 创建 docker/docker-compose.yml
- [ ] 创建 docker/nginx.conf
- [ ] 编写部署文档

### 3.3 用户认证

- [ ] 实现 JWT 认证
- [ ] 实现用户注册/登录 API
- [ ] 实现权限管理
- [ ] 编写认证测试

### 3.4 本地模型支持

- [ ] 集成 Ollama
- [ ] 实现本地模型切换
- [ ] 性能测试

### 3.5 监控与日志

- [ ] 结构化日志配置
- [ ] 性能监控集成
- [ ] 错误追踪

### 3.6 API 限流

- [ ] 实现速率限制
- [ ] 实现资源配额

### 3.7 文档增量更新

- [ ] 实现知识库热更新
- [ ] 实现增量向量化

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

- [ ] 多知识库
- [ ] Docker 部署
- [ ] 用户认证
- [ ] 完成时间：_____

---

## 更新日志

| 日期 | 更新内容 | 更新人 |
|------|----------|--------|
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
