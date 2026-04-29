# 🧠 RAG Knowledge Platform — Ingest Pipeline Orchestrator（Plan Mode Prompt）

## 🎯 目标

实现一个**轻中台（Orchestrator）型知识库入库系统**，`kb_service` 仅负责：

* 文档分类（document classification）
* 路由决策（RAGFlow / Dify）
* 元数据管理（metadata）
* 异步任务调度（ingestion job）
* 状态跟踪（processing / success / failed）

⚠️ 不负责：

* 文档解析（PDF / DOCX parsing）
* 分段（chunking）
* embedding

👉 原则：**谁负责检索，谁负责分段**

---

## 🏗️ 系统设计

### 架构模式

```
Client → FastAPI(kb_service)
              ↓
      ingest_pipeline
              ↓
     document_classifier
              ↓
        router_service
         ↙        ↘
   RAGFlow       Dify
 (plain text) (complex layout)
              ↓
      async ingestion job
              ↓
     status tracking + metadata
```

---

## 📦 开发任务分解（按模块）

---

## 1️⃣ Document Classifier（轻量分类器）

### 📁 文件

```
services/document_classifier.py
```

### 🎯 功能

根据文件特征判断：

* `plain_text`
* `complex_layout`
* `scanned_pdf`
* `table_heavy`
* `image_rich`

### 🧩 输入

```python
file_path: str
mime_type: str
```

### 🧩 输出

```python
class DocumentType(str, Enum):
    PLAIN_TEXT = "plain_text"
    COMPLEX = "complex_layout"
```

### ⚙️ 实现要求

* 不做 OCR（保持轻量）
* 使用：

  * 文件大小
  * 页数
  * 图片数量（可选）
  * 简单 PDF metadata
* 预留扩展（后续接 ML classifier）

---

## 2️⃣ Router Service（路由决策）

### 📁 文件

```
services/router_service.py
```

### 🎯 功能

根据 `DocumentType` 决定入库引擎：

```python
def route(doc_type: DocumentType) -> Backend:
```

### 🧩 输出

```python
class Backend(str, Enum):
    RAGFLOW = "ragflow"
    DIFY = "dify"
```

### 🧠 路由规则

```python
if doc_type == PLAIN_TEXT:
    return RAGFLOW
else:
    return DIFY
```

---

## 3️⃣ Metadata Builder（元数据标准化）

### 📁 文件

```
services/metadata_service.py
```

### 🎯 生成统一 metadata

```python
{
    "doc_id": str,
    "business_id": str,
    "doc_type": str,
    "backend": str,
    "kb_version": str,
    "release_id": str,
    "status": "processing",
    "created_at": timestamp
}
```

⚠️ 必须保证：

* 可审计
* 可回滚
* 可追踪

---

## 4️⃣ Ingestion Job（异步任务调度）

### 📁 文件

```
pipelines/ingest_pipeline.py
```

### 🎯 流程

```python
def ingest_document(file):

    # 1. classify
    doc_type = classifier.detect(file)

    # 2. route
    backend = router.route(doc_type)

    # 3. build metadata
    metadata = metadata_service.build(...)

    # 4. submit async job
    job_id = job_queue.submit(
        backend=backend,
        file=file,
        metadata=metadata
    )

    # 5. save metadata
    metadata_repo.save(metadata)

    return job_id
```

---

## 5️⃣ Backend Clients（RAGFlow / Dify）

### 📁 文件

```
clients/ragflow_client.py
clients/dify_client.py
```

---

### 🎯 ragflow_client

```python
def upload(file, metadata):
    """
    调用 RAGFlow:
    - upload file
    - trigger parse
    - trigger chunk
    - build index
    """
```

---

### 🎯 dify_client

```python
def pipeline_run(file, metadata):
    """
    调用 Dify pipeline:
    extract → chunk → knowledge
    """
```

---

## 6️⃣ Job Queue（必须异步）

### 📁 文件

```
services/job_service.py
```

### 🎯 功能

* 提交任务
* 状态查询
* 重试机制

### 🧩 状态定义

```python
class JobStatus:
    PROCESSING
    SUCCESS
    FAILED
```

---

## 7️⃣ Status Tracking（状态回调/轮询）

### 📁 文件

```
services/status_service.py
```

### 🎯 功能

* 轮询 RAGFlow / Dify 状态
* 更新 metadata

---

## 8️⃣ Metadata Repository

### 📁 文件

```
repositories/metadata_repo.py
```

### 🎯 功能

* 存储 metadata（Postgres）
* 查询文档状态
* 支持版本回溯

---

## 🔁 完整流程（最终）

```
上传文档
  ↓
Document Classifier
  ↓
Router（RAGFlow / Dify）
  ↓
Metadata 创建
  ↓
异步任务提交
  ↓
RAGFlow / Dify 内部解析 + chunk
  ↓
状态回调
  ↓
Metadata 更新（success / failed）
```

---

## 🚫 重要约束（必须遵守）

* ❌ 不在 kb_service 做 chunk
* ❌ 不在 kb_service 做 OCR
* ❌ 不统一转 Markdown
* ✅ chunk 在 RAGFlow / Dify 内部完成

---

## 🧪 可选增强（后续阶段）

* Document Classifier → ML模型
* 多引擎 fallback（RAGFlow失败 → Dify）
* 灰度发布（不同版本 KB）
* 多租户支持
* 审计日志（trace_id）

---

## ✅ 验收标准

* 支持上传 docx/pdf
* 能自动路由到 RAGFlow / Dify
* metadata 可查询状态
* ingestion 异步执行
* 可扩展（新增引擎不影响主流程）

---

## 🧩 开发顺序（建议）

1. metadata + repo
2. classifier
3. router
4. ingest_pipeline（同步版本）
5. job queue（改异步）
6. ragflow/dify client
7. status tracking

---

## 🚀 最终目标

构建一个：

👉 可扩展 / 可审计 / 可回滚 / 多引擎兼容
👉 银行级 RAG 知识库入库编排系统

---

如果你下一步要继续，我可以帮你直接补：
👉 可运行的 FastAPI + Redis Queue + RAGFlow/Dify mock demo（完整代码）
👉 或者把这一套升级成 LangGraph Orchestrator 版本（企业级）


flowchart TD
    %% =========================
    %% 客户端
    %% =========================
    A[用户上传文档]

    %% =========================
    %% 编排层（kb_service）
    %% =========================
    subgraph KB_Service[编排层 kb_service]
        B[FastAPI 接口]
        C[文档清洗处理]
        D{文档类型判断}
        E[路由 → RAGFlow]
        F[路由 → Dify]
        G[构建元数据]
        H[保存元数据<br/>状态=处理中]
        I[提交异步任务]
    end

    %% =========================
    %% 异步任务层
    %% =========================
    subgraph Async_Job[异步任务执行]
        J{目标引擎}
        K[RAGFlow 入库调用]
        L[Dify Pipeline 调用]
    end

    %% =========================
    %% RAGFlow 引擎
    %% =========================
    subgraph RAGFlow[RAGFlow 引擎]
        K1[文件上传]
        K2[文档解析]
        K3[分段 Chunk]
        K4[向量化 Embedding]
        K5[索引构建]
    end

    %% =========================
    %% Dify 管道
    %% =========================
    subgraph Dify[Dify 知识处理管道]
        L1[内容抽取（文本/图片/表格）]
        L2[分段 Chunk]
        L3[多模态向量化]
        L4[知识索引构建]
    end

    %% =========================
    %% 状态管理
    %% =========================
    subgraph Status[状态跟踪与回调]
        M[回调 / 轮询]
        N{执行结果}
        O[更新状态=成功]
        P[更新状态=失败]
        Q[可用于问答]
        R[重试 / 告警]
    end

    %% =========================
    %% 存储层
    %% =========================
    subgraph Storage[元数据存储]
        S[(PostgreSQL)]
    end

    %% =========================
    %% 流程连接
    %% =========================
    A --> B --> C --> D
    D -->|纯文本| E
    D -->|复杂结构/图文| F

    E --> G
    F --> G

    G --> H --> I --> J

    J -->|RAGFlow| K --> K1 --> K2 --> K3 --> K4 --> K5 --> M
    J -->|Dify| L --> L1 --> L2 --> L3 --> L4 --> M

    M --> N
    N -->|成功| O --> Q
    N -->|失败| P --> R

    H --> S
    O --> S
    P --> S

    %% =========================
    %% 样式定义（颜色）
    %% =========================
    classDef orchestrator fill:#e3f2fd,stroke:#1e88e5,stroke-width:2px,color:#0d47a1
    classDef async fill:#fff3e0,stroke:#fb8c00,stroke-width:2px,color:#e65100
    classDef ragflow fill:#e8f5e9,stroke:#43a047,stroke-width:2px,color:#1b5e20
    classDef dify fill:#f3e5f5,stroke:#8e24aa,stroke-width:2px,color:#4a148c
    classDef status fill:#ffebee,stroke:#e53935,stroke-width:2px,color:#b71c1c
    classDef storage fill:#efebe9,stroke:#6d4c41,stroke-width:2px,color:#3e2723

    class B,C,D,E,F,G,H,I orchestrator
    class J,K,L async
    class K1,K2,K3,K4,K5 ragflow
    class L1,L2,L3,L4 dify
    class M,N,O,P,Q,R status
    class S storage