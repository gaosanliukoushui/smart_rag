#RAG 智能知识库系统（AI 项目）

项目定位：

一个支持文档上传、自动切片、向量检索与智能问答的 AI 知识库系统。

核心流程：
上传文档
→ 文档切片
→ 向量化
→ 向量检索
→ 大模型生成答案

目标：
- 体现 AI 工程化能力
- 避免“纯 API 套壳”项目
- 展示检索增强生成（RAG）理解

建议项目名称：
- SmartRAG
- InsightRAG
- VectorMind
- KnowledgeFlow

---

# 1. 技术栈

## AI 框架

- Python
- FastAPI
- LangChain / LlamaIndex

## 向量数据库

推荐任选其一：
- Milvus
- pgvector
- Chroma

## 大模型

可选：
- DeepSeek
- Qwen
- OpenAI API
- Ollama 本地模型

## Embedding 模型

推荐：
- bge-m3
- bge-large-zh
- jina-embedding

## 重排序（可选加分）

- bge-reranker

## 其他

- Redis
- PostgreSQL
- Docker

---

# 2. 核心功能模块

## （1）文档上传

支持：
- PDF
- Markdown
- Word
- TXT

技术重点：
- 文件解析
- 异步上传
- 文档管理

---

## （2）文档切片（重点）

功能：
- Chunk 切分
- overlap 重叠
- Token 控制

技术重点：
- chunk size 设计
- overlap 的作用
- 长文本处理

推荐参数：
- chunk size：500~800
- overlap：100~150

---

## （3）向量化

功能：
- 文本 embedding
- 向量存储

技术重点：
- Embedding 原理
- 向量相似度
- 向量维度

---

## （4）向量检索（核心）

功能：
- TopK 检索
- 相似度召回

技术重点：
- cosine similarity
- ANN（近似最近邻）
- 向量召回流程

---

## （5）RAG 问答（核心）

流程：
用户提问
→ 检索相关 chunk
→ 拼接 Prompt
→ 大模型生成答案

技术重点：
- Prompt Engineering
- 上下文拼接
- Token 控制

---

# 3. 高级增强（非常加分）

## （1）混合检索

实现：
BM25 + 向量检索。

技术重点：
- 关键词检索
- 语义检索
- Hybrid Search

---

## （2）Rerank 重排序

实现：
对召回结果再次排序。

技术重点：
- reranker 原理
- 召回与排序区别

---

## （3）流式输出

实现：
SSE/WebSocket 实时输出回答。

技术重点：
- 流式响应
- Token streaming

---

## （4）多知识库隔离

实现：
每个用户拥有独立知识库。

技术重点：
- 权限隔离
- 数据隔离
- 多租户设计

---

# 4. 推荐开发顺序

## 第一阶段（必须完成）

- 文档上传
- 文档切片
- 向量化
- 向量检索
- 基础问答

目标：
完成最小可用 RAG。

---

## 第二阶段（重点优化）

- 混合检索
- Prompt 优化
- 流式输出
- 对话历史

目标：
提升问答质量。

---

## 第三阶段（高级加分）

- rerank
- 多知识库
- Docker 部署
- 本地模型

目标：
体现 AI 工程能力。

---