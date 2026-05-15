# SmartRAG 项目开发流程指南

> 本文档为 SmartRAG 智能知识库系统提供完整的开发流程指引，包括项目架构、技术实现步骤、代码组织规范，以及正确的 Vibe Coding 方法论。

---

## 目录

1. [项目愿景与目标](#1-项目愿景与目标)
2. [技术选型与架构](#2-技术选型与架构)
3. [项目目录结构](#3-项目目录结构)
4. [三阶段开发路线图](#4-三阶段开发路线图)
5. [Vibe Coding 方法论](#5-vibe-coding-方法论)
6. [核心模块实现指南](#6-核心模块实现指南)
7. [开发规范与质量标准](#7-开发规范与质量标准)

---

## 1. 项目愿景与目标

### 1.1 项目定位

SmartRAG 是一个支持**文档上传、自动切片、向量检索与智能问答**的 AI 知识库系统，核心目标是：

- **体现 AI 工程化能力**：不只是 API 调用的简单封装，而是展示对 RAG 核心原理的深入理解
- **避免"纯 API 套壳"**：通过精细的文档处理、检索策略和 Prompt 工程展示差异化能力
- **展示检索增强生成（RAG）理解**：从向量数据库原理到混合检索、重排序等高级技术

### 1.2 核心业务流程

```
用户上传文档
    ↓
文档解析（PDF/Markdown/Word/TXT）
    ↓
智能切片（Chunk + Overlap）
    ↓
向量化处理（Embedding Model）
    ↓
向量存储（Vector Database）
    ↓
用户提问
    ↓
向量检索（Top-K + 相似度）
    ↓
Prompt 拼接与增强
    ↓
大模型生成答案
    ↓
流式输出响应
```

---

## 2. 技术选型与架构

### 2.1 技术栈总览

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| **后端框架** | FastAPI | 高性能异步 API，支持自动文档生成 |
| **AI 框架** | LangChain / LlamaIndex | 封装 RAG 流程，简化开发 |
| **向量数据库** | Chroma（开发）/ Milvus（生产） | 轻量易用，支持本地部署 |
| **关系数据库** | PostgreSQL + pgvector | 生产级向量存储方案 |
| **大模型** | DeepSeek / Qwen / OpenAI API | 灵活切换，支持本地 Ollama |
| **Embedding** | bge-m3 / bge-large-zh | 中文优化，高性能 |
| **重排序** | bge-reranker | 提升检索精度 |
| **缓存** | Redis | 会话管理，性能优化 |
| **部署** | Docker + Docker Compose | 容器化，一键部署 |

### 2.2 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层 (Web UI)                        │
├─────────────────────────────────────────────────────────────┤
│                      FastAPI REST API                        │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │文档管理  │  │问答引擎  │  │知识库管理│  │用户认证  │        │
│  │  API   │  │  API   │  │  API   │  │  API   │        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
├─────────────────────────────────────────────────────────────┤
│                       服务层 (Business Logic)                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │文档解析  │  │切片引擎  │  │检索引擎  │  │问答引擎  │        │
│  │ Service │  │ Service │  │ Service │  │ Service │        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
├─────────────────────────────────────────────────────────────┤
│                       能力层 (AI Capabilities)                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │Embedding│  │向量检索  │  │重排序   │  │LLM生成  │        │
│  │  Model  │  │ (ANN)  │  │Reranker │  │  Model  │        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
├─────────────────────────────────────────────────────────────┤
│                       数据层 (Data Layer)                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │向量数据库│  │PostgreSQL│  │  Redis  │  │ 文件存储 │        │
│  │(Chroma) │  │(pgvector)│  │ (Cache) │  │ (Local) │        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 项目目录结构

```
SmartRAG/
├── README.md                 # 项目说明文档
├── requirements.txt          # Python 依赖
├── .env.example              # 环境变量示例
├── .gitignore               # Git 忽略配置
│
├── docker/                   # Docker 配置
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── nginx.conf
│
├── app/                     # 主应用目录
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── config.py             # 配置管理
│   │
│   ├── api/                  # API 路由
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── document.py   # 文档管理 API
│   │   │   ├── knowledge_base.py  # 知识库 API
│   │   │   ├── chat.py       # 问答 API
│   │   │   └── health.py     # 健康检查 API
│   │   └── deps.py           # API 依赖注入
│   │
│   ├── core/                 # 核心模块
│   │   ├── __init__.py
│   │   ├── security.py       # 安全认证
│   │   └── exceptions.py     # 自定义异常
│   │
│   ├── models/               # 数据模型
│   │   ├── __init__.py
│   │   ├── document.py       # 文档模型
│   │   ├── chunk.py          # 切片模型
│   │   ├── knowledge_base.py # 知识库模型
│   │   └── chat.py           # 对话模型
│   │
│   ├── schemas/              # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── document.py
│   │   ├── chat.py
│   │   └── common.py
│   │
│   ├── services/             # 业务逻辑服务
│   │   ├── __init__.py
│   │   ├── document_service.py    # 文档处理
│   │   ├── chunk_service.py       # 切片处理
│   │   ├── embedding_service.py    # 向量化
│   │   ├── vector_store_service.py # 向量存储
│   │   ├── retrieval_service.py    # 检索服务
│   │   ├── rerank_service.py      # 重排序
│   │   ├── chat_service.py        # 问答服务
│   │   └── llm_service.py         # LLM 服务
│   │
│   ├── capabilities/         # AI 能力封装
│   │   ├── __init__.py
│   │   ├── embedding/
│   │   │   ├── __init__.py
│   │   │   └── bge.py        # BGE Embedding
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── deepseek.py   # DeepSeek
│   │   │   ├── qwen.py       # Qwen
│   │   │   └── openai.py     # OpenAI
│   │   └── rerank/
│   │       ├── __init__.py
│   │       └── bge_reranker.py
│   │
│   ├── parsers/              # 文档解析器
│   │   ├── __init__.py
│   │   ├── base.py           # 解析器基类
│   │   ├── pdf_parser.py     # PDF 解析
│   │   ├── markdown_parser.py # Markdown 解析
│   │   ├── word_parser.py     # Word 解析
│   │   └── text_parser.py     # 文本解析
│   │
│   ├── chunkers/             # 切片策略
│   │   ├── __init__.py
│   │   ├── base.py           # 切片基类
│   │   ├── recursive_chunker.py  # 递归切片
│   │   └── semantic_chunker.py   # 语义切片
│   │
│   ├── vectorstores/         # 向量数据库
│   │   ├── __init__.py
│   │   ├── base.py           # 向量存储基类
│   │   ├── chroma.py         # Chroma 实现
│   │   └── milvus.py         # Milvus 实现
│   │
│   └── db/                    # 数据库
│       ├── __init__.py
│       ├── database.py        # 数据库连接
│       └── redis.py           # Redis 连接
│
├── tests/                    # 测试目录
│   ├── __init__.py
│   ├── conftest.py           # pytest 配置
│   ├── unit/
│   │   ├── test_parsers.py
│   │   ├── test_chunkers.py
│   │   ├── test_embedding.py
│   │   └── test_retrieval.py
│   └── integration/
│       └── test_api.py
│
├── scripts/                  # 脚本工具
│   ├── init_db.py           # 数据库初始化
│   ├── init_vector_db.py    # 向量库初始化
│   └── test_embedding.py    # Embedding 测试
│
├── docs/                     # 文档
│   ├── api.md
│   ├── architecture.md
│   └── deployment.md
│
└── frontend/                 # 前端（可选）
    └── (Vite + React/Vue)
```

---

## 4. 三阶段开发路线图

### 4.1 第一阶段：最小可用 RAG（核心基础）

**目标**：完成一个可工作的 RAG 系统，能够上传文档、切片、向量化，并进行基础问答。

#### 阶段一任务清单

| # | 任务 | 说明 | 优先级 |
|---|------|------|--------|
| 1 | 项目初始化 | 创建目录结构、Git 仓库、依赖配置 | P0 |
| 2 | 配置管理 | 环境变量、配置文件、日志配置 | P0 |
| 3 | 数据库模型 | Document、Chunk、KnowledgeBase 数据模型 | P0 |
| 4 | 文档解析器 | PDF、Markdown、Word、TXT 解析 | P0 |
| 5 | 文档切片 | Chunk 切分、Overlap 控制 | P0 |
| 6 | Embedding 服务 | BGE 模型集成 | P0 |
| 7 | 向量存储 | Chroma 本地向量库 | P0 |
| 8 | 向量检索 | Top-K 检索、相似度计算 | P0 |
| 9 | LLM 集成 | DeepSeek/Qwen API 集成 | P0 |
| 10 | 基础问答 API | 检索 + 生成完整流程 | P0 |
| 11 | 文档上传 API | 文件上传、状态管理 | P0 |
| 12 | 简单前端界面 | 上传文档、提问、查看答案 | P1 |

#### 阶段一交付物

- 一个完整可运行的 FastAPI 应用
- 支持文档上传和解析
- 支持向量检索和问答
- 基础 Web UI

---

### 4.2 第二阶段：重点优化（提升体验）

**目标**：提升问答质量，增加高级特性，使系统更接近生产级别。

#### 阶段二任务清单

| # | 任务 | 说明 | 优先级 |
|---|------|------|--------|
| 1 | 混合检索 | BM25 + 向量检索融合 | P0 |
| 2 | Prompt 优化 | System Prompt 工程、上下文管理 | P0 |
| 3 | 流式输出 | SSE/WebSocket 实时响应 | P0 |
| 4 | 对话历史 | 多轮对话上下文管理 | P0 |
| 5 | 重排序 (Rerank) | BGE Reranker 集成 | P1 |
| 6 | 错误处理 | 完善异常处理、用户反馈 | P1 |
| 7 | 性能优化 | 异步处理、缓存策略 | P1 |
| 8 | 文档管理 | 文档列表、删除、状态查看 | P1 |

#### 阶段二交付物

- 支持混合检索的增强版 RAG
- 实时流式输出
- 多轮对话能力
- 更专业的 Prompt 工程

---

### 4.3 第三阶段：高级特性（工程能力展示）

**目标**：展示 AI 工程化能力，体现差异化竞争优势。

#### 阶段三任务清单

| # | 任务 | 说明 | 优先级 |
|---|------|------|--------|
| 1 | 多知识库隔离 | 多租户设计、权限隔离 | P0 |
| 2 | Docker 部署 | 容器化、docker-compose 编排 | P0 |
| 3 | 本地模型支持 | Ollama 集成、本地 LLM | P1 |
| 4 | 用户认证 | JWT 认证、权限管理 | P1 |
| 5 | 监控与日志 | 结构化日志、性能监控 | P1 |
| 6 | API 限流 | 速率限制、资源保护 | P2 |
| 7 | 文档增量更新 | 知识库热更新 | P2 |

#### 阶段三交付物

- 生产级别的部署方案
- 多租户知识库系统
- 支持本地模型
- 完整的用户认证体系

---

## 5. Vibe Coding 方法论

### 5.1 什么是 Vibe Coding

Vibe Coding（氛围编程）是一种以**快速验证想法**为核心的开发方法，强调：

- **快速迭代**：先跑起来，再优化
- **最小可行**：用最少的代码验证核心逻辑
- **自然对话**：用自然语言描述需求，AI 辅助实现
- **持续重构**：在验证的基础上逐步完善

### 5.2 Vibe Coding 核心原则

```
┌─────────────────────────────────────────────────────────────┐
│                    Vibe Coding 四原则                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1️⃣ 先让核心流程跑起来                                       │
│     ├── 先实现最简单的版本                                   │
│     ├── 跳过"完美设计"，直奔主题                             │
│     └── 用 20% 的时间解决 80% 的问题                         │
│                                                              │
│  2️⃣ 每个功能独立验证                                         │
│     ├── 切片功能 → 单独测试                                  │
│     ├── 向量化 → 单独测试                                    │
│     ├── 检索 → 单独测试                                      │
│     └── 组合测试 → 集成测试                                  │
│                                                              │
│  3️⃣ 用自然语言描述需求                                       │
│     ├── "我想实现文档上传功能"                               │
│     ├── "支持 PDF 和 Markdown"                              │
│     └── "切片大小 500，overlap 100"                          │
│                                                              │
│  4️⃣ 快速反馈循环                                            │
│     ├── 写代码 → 测试 → 验证                                │
│     ├── 遇到问题 → 描述问题 → 修复                           │
│     └── 持续小步前进                                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 SmartRAG 的 Vibe Coding 工作流

#### Step 1：明确最小可行目标

```
用户故事：
作为一个用户，
我想要上传 PDF 文档，
以便系统能够回答我关于文档内容的问题。
```

**最小可行目标（MVP）**：
- 上传一个 PDF 文件
- 系统自动切片和向量化
- 输入问题，获得基于文档的回答

#### Step 2：快速搭建核心骨架

```bash
# 1. 创建项目结构
mkdir SmartRAG && cd SmartRAG
mkdir -p app/api app/services app/models app/schemas

# 2. 创建基础文件
touch app/__init__.py app/main.py
touch app/api/__init__.py app/services/__init__.py

# 3. 安装依赖
pip install fastapi uvicorn langchain langchain-community
pip install chromadb sentence-transformers pypdf
```

#### Step 3：实现 → 测试 → 验证 循环

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   写代码      │ →  │   本地测试    │ →  │   验证效果    │
│  (小块功能)   │    │  (curl/pytest)│    │  (手动体验)   │
└──────────────┘    └──────────────┘    └──────────────┘
        ↑                                          │
        └──────────────────────────────────────────┘
                    遇到问题 → 描述问题 → 修复
```

#### Step 4：逐步增强功能

```
基础 RAG → 混合检索 → 重排序 → 流式输出 → 多知识库
   ↓
每个功能都是独立的"小目标"，完成后验证，再进入下一个
```

### 5.4 Vibe Coding 会话模板

当你与 AI 协作时，使用以下模板：

```markdown
## 需求描述
[用一句话描述你想做什么]

## 当前状态
[你目前已有的代码/已完成的部分]

## 具体任务
1. [具体要实现的功能点]
2. [具体要实现的功能点]

## 约束条件
- 技术栈：FastAPI + Chroma + DeepSeek
- 参数要求：chunk_size=500, overlap=100
- [其他特定要求]

## 验证方式
[如何测试这个功能是否正常工作]
```

### 5.5 避免的陷阱

| ❌ 避免 | ✅ 正确做法 |
|--------|-----------|
| 追求完美的架构设计 | 先实现，跑起来再说 |
| 一次性写完所有功能 | 小步快走，每次只做一个功能 |
| 跳过测试直接上线 | 每个功能单独验证 |
| 深陷细节优化 | 先完成，再优化 |
| 从零开始造轮子 | 使用 LangChain 等成熟框架 |

---

## 6. 核心模块实现指南

### 6.1 文档解析模块

```python
# app/parsers/base.py
from abc import ABC, abstractmethod
from typing import List

class BaseParser(ABC):
    """文档解析器基类"""
    
    @abstractmethod
    def parse(self, file_path: str) -> str:
        """解析文档，返回纯文本内容"""
        pass
    
    @abstractmethod
    def get_metadata(self, file_path: str) -> dict:
        """提取文档元数据"""
        pass

# app/parsers/pdf_parser.py
from .base import BaseParser
import pypdf

class PDFParser(BaseParser):
    def parse(self, file_path: str) -> str:
        reader = pypdf.PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    
    def get_metadata(self, file_path: str) -> dict:
        reader = pypdf.PdfReader(file_path)
        return {
            "pages": len(reader.pages),
            "title": reader.metadata.title if reader.metadata else None
        }
```

### 6.2 文档切片模块

```python
# app/chunkers/recursive_chunker.py
from typing import List
from .base import BaseChunker

class RecursiveChunker(BaseChunker):
    """递归字符切片器"""
    
    def __init__(self, chunk_size: int = 500, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk(self, text: str) -> List[str]:
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            
            # 尝试在句子边界切割
            if end < len(text):
                last_period = chunk.rfind('。')
                last_newline = chunk.rfind('\n')
                cut_point = max(last_period, last_newline)
                
                if cut_point > self.chunk_size // 2:
                    chunk = chunk[:cut_point + 1]
                    end = start + cut_point + 1
            
            chunks.append(chunk.strip())
            start = end - self.overlap  # 重叠滑动
        
        return [c for c in chunks if c]  # 过滤空块
```

### 6.3 向量检索模块

```python
# app/services/retrieval_service.py
from typing import List, Tuple

class RetrievalService:
    """向量检索服务"""
    
    def __init__(self, vector_store, embedding_service):
        self.vector_store = vector_store
        self.embedding_service = embedding_service
    
    async def retrieve(
        self, 
        query: str, 
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[Tuple[str, float]]:
        """
        检索相关文档块
        
        Args:
            query: 用户查询
            top_k: 返回前 k 个结果
            similarity_threshold: 相似度阈值
        
        Returns:
            List[(chunk_text, similarity_score)]
        """
        # 1. 将查询向量化
        query_embedding = await self.embedding_service.embed([query])
        
        # 2. 在向量数据库中检索
        results = self.vector_store.similarity_search_with_score(
            query_embedding[0],
            k=top_k
        )
        
        # 3. 过滤低相似度结果
        filtered = [
            (doc, score) 
            for doc, score in results 
            if score >= similarity_threshold
        ]
        
        return filtered
```

### 6.4 RAG 问答模块

```python
# app/services/chat_service.py
from typing import AsyncGenerator

class ChatService:
    """RAG 问答服务"""
    
    def __init__(
        self,
        retrieval_service,
        llm_service,
        prompt_template: str = None
    ):
        self.retrieval_service = retrieval_service
        self.llm_service = llm_service
        self.prompt_template = prompt_template or self._default_template()
    
    def _default_template(self) -> str:
        return """你是一个专业的知识库问答助手。
        
参考信息：
{context}

用户问题：{question}

请根据参考信息回答用户的问题。如果参考信息中没有相关内容，请如实说明。
回答："""
    
    async def ask(
        self, 
        question: str, 
        knowledge_base_id: str,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """流式问答"""
        
        # 1. 检索相关文档
        chunks = await self.retrieval_service.retrieve(
            query=question,
            knowledge_base_id=knowledge_base_id,
            top_k=5
        )
        
        # 2. 构建上下文
        context = "\n\n".join([
            f"[文档 {i+1}]\n{chunk}" 
            for i, chunk in enumerate(chunks)
        ])
        
        # 3. 填充 Prompt
        prompt = self.prompt_template.format(
            context=context,
            question=question
        )
        
        # 4. 流式生成
        if stream:
            async for token in self.llm_service.stream_generate(prompt):
                yield token
        else:
            return await self.llm_service.generate(prompt)
```

### 6.5 混合检索模块（高级）

```python
# app/services/hybrid_retrieval_service.py
from typing import List, Tuple
import numpy as np

class HybridRetrievalService:
    """混合检索：BM25 + 向量检索"""
    
    def __init__(
        self,
        vector_retriever,
        bm25_retriever,
        reranker=None,
        vector_weight: float = 0.6,
        bm25_weight: float = 0.4
    ):
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        self.reranker = reranker
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
    
    async def retrieve(
        self, 
        query: str, 
        top_k: int = 10,
        final_k: int = 5
    ) -> List[Tuple[str, float]]:
        
        # 1. 向量检索
        vector_results = await self.vector_retriever.retrieve(
            query, top_k=top_k
        )
        
        # 2. BM25 检索
        bm25_results = await self.bm25_retriever.retrieve(
            query, top_k=top_k
        )
        
        # 3. RRF 融合 (Reciprocal Rank Fusion)
        fused_scores = self._rrf_fusion(
            vector_results,
            bm25_results,
            k=60  # RRF 参数
        )
        
        # 4. 可选：重排序
        if self.reranker:
            top_chunks = [chunk for chunk, _ in fused_scores[:final_k]]
            reranked = await self.reranker.rerank(
                query, top_chunks
            )
            return reranked
        
        return fused_scores[:final_k]
    
    def _rrf_fusion(
        self, 
        results1: List, 
        results2: List, 
        k: int = 60
    ) -> List:
        """RRF 融合算法"""
        scores = {}
        
        # 添加第一组结果
        for i, (doc, _) in enumerate(results1):
            scores[doc] = scores.get(doc, 0) + self.vector_weight * (1 / (k + i + 1))
        
        # 添加第二组结果
        for i, (doc, _) in enumerate(results2):
            scores[doc] = scores.get(doc, 0) + self.bm25_weight * (1 / (k + i + 1))
        
        # 排序
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results
```

---

## 7. 开发规范与质量标准

### 7.1 代码规范

```python
# 1. 使用类型提示
async def retrieve(
    self, 
    query: str, 
    top_k: int = 5
) -> List[Tuple[str, float]]:
    """检索相关文档"""
    pass

# 2. 文档字符串（Google 风格）
def process_document(self, file_path: str) -> Document:
    """
    处理文档并存储到数据库
    
    Args:
        file_path: 文档路径
        
    Returns:
        Document: 处理后的文档对象
        
    Raises:
        ParseError: 文档解析失败时抛出
    """
    pass

# 3. 异步优先
async def embedding_service():
    # 使用 asyncio 进行并发处理
    pass
```

### 7.2 测试策略

```
┌─────────────────────────────────────────────────────────────┐
│                    测试金字塔                                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│                        ▲                                     │
│                       /█\                                    │
│                      / █ \         E2E 测试                   │
│                     /  █  \       (关键流程)                  │
│                    /───────\                                 │
│                   /   █     \      集成测试                   │
│                  /  █   █    \    (模块交互)                  │
│                 /─────█████────\                             │
│                /   █     █     \    单元测试                  │
│               /  █   █   █   █  \   (函数/类)                │
│              /───────────────────\                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

```python
# tests/unit/test_chunkers.py
import pytest
from app.chunkers import RecursiveChunker

def test_chunker_basic():
    """测试基本切片功能"""
    chunker = RecursiveChunker(chunk_size=100, overlap=20)
    text = "这是测试文本。" * 50
    chunks = chunker.chunk(text)
    
    assert len(chunks) > 1
    assert all(len(c) <= 150 for c in chunks)  # 允许一定误差

def test_chunker_overlap():
    """测试切片重叠"""
    chunker = RecursiveChunker(chunk_size=100, overlap=20)
    text = "这是测试文本。" * 50
    chunks = chunker.chunk(text)
    
    # 验证重叠存在
    assert chunks[0][-20:] == chunks[1][:20] or len(chunks) == 1
```

### 7.3 提交规范

```bash
# 提交格式
<type>(<scope>): <subject>

# 示例
feat(document): 添加 PDF 解析功能
fix(retrieval): 修复向量检索精度问题
docs(api): 更新 API 文档
refactor(chunker): 重构切片器实现
test(chat): 添加问答服务测试

# 提交检查清单
- [ ] 功能完成并测试通过
- [ ] 代码符合规范
- [ ] 添加了必要的注释
- [ ] 更新了相关文档
```

### 7.4 环境配置

```bash
# .env.example
# 应用配置
APP_NAME=SmartRAG
APP_VERSION=1.0.0
DEBUG=true

# 数据库配置
DATABASE_URL=postgresql://user:pass@localhost:5432/smartrag

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# 向量数据库
VECTOR_DB_TYPE=chroma  # chroma / milvus
CHROMA_PERSIST_DIR=./data/chroma

# LLM 配置
LLM_PROVIDER=deepseek  # deepseek / qwen / openai / ollama
DEEPSEEK_API_KEY=your-api-key
DEEPSEEK_MODEL=deepseek-chat

# Embedding 配置
EMBEDDING_MODEL=bge-m3
EMBEDDING_DEVICE=cpu  # cpu / cuda

# Reranker 配置
RERANKER_MODEL=bge-reranker
```

---

## 快速开始

### 第一步：初始化项目

```bash
# 创建项目目录
mkdir SmartRAG && cd SmartRAG

# 初始化 Git
git init

# 创建基础目录结构（使用上述目录结构）
```

### 第二步：安装依赖

```bash
pip install fastapi uvicorn
pip install langchain langchain-community
pip install chromadb sentence-transformers
pip install pypdf python-docx
pip install python-dotenv pydantic
pip install httpx aiofiles
```

### 第三步：实现核心功能

按照本文档的模块顺序实现：
1. 配置管理 (`app/config.py`)
2. 数据模型 (`app/models/`)
3. 文档解析器 (`app/parsers/`)
4. 切片器 (`app/chunkers/`)
5. Embedding 服务 (`app/services/embedding_service.py`)
6. 向量存储 (`app/vectorstores/`)
7. 检索服务 (`app/services/retrieval_service.py`)
8. LLM 服务 (`app/services/llm_service.py`)
9. 问答服务 (`app/services/chat_service.py`)
10. API 路由 (`app/api/`)

### 第四步：测试和迭代

```bash
# 启动开发服务器
uvicorn app.main:app --reload

# 运行测试
pytest tests/ -v

# 检查代码质量
ruff check app/
```

---

## 下一步

- 开始实现第一阶段的代码
- 配置开发环境
- 创建 Git 分支，开始第一个功能的开发

---

*本文档将随着项目进展持续更新。*
