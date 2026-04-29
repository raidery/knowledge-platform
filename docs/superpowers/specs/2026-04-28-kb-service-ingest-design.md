# 知识库文档入库服务 (kb_service) 设计文档

**版本**: v1.0
**日期**: 2026-04-28
**状态**: 待 Review

---

## 1. 背景与目标

### 1.1 背景

`kb_service` 是 RAG 知识平台的核心编排层，负责文档从上传到发布的全生命周期管理。当前 `apps/kb_service` 还未创建，需从零实现。

### 1.2 设计原则

> **谁负责检索，谁负责 chunk** — kb_service 只做编排，不做解析/chunk/embedding。

RAGFlow/Dify 负责：
- 文档解析（PDF/DOCX/OCR）
- 分块（chunking）
- 向量化（embedding）

kb_service 负责：
- 文档分类（plain_text / complex_layout / ...）
- 路由决策（RAGFlow / Dify）
- 元数据管理
- 异步任务调度（ARQ）
- 状态跟踪（回调 + 轮询）
- 人工审核 + 发布控制

### 1.3 分阶段路线

| 阶段 | 范围 | 目标 |
|------|------|------|
| Phase 1 | 轻量编排层 | 上传入库 + RAGFlow/Dify 路由 + 异步任务 + 回调/轮询 + 人工审核 |
| Phase 2 | 增强可控性 | 自建解析/分块 + 标准化 chunk 策略 |
| Phase 3 | 企业级 | 多租户 + 灰度发布 + 多引擎 fallback |

---

## 2. 架构设计

### 2.1 整体架构

```
用户上传 / 定时扫描
       ↓
  FastAPI (kb_service)
       ↓
  ┌────────────────────────────┐
  │   ingest_pipeline          │
  │   ├─ document_preprocessor │
  │   ├─ router_service         │
  │   ├─ metadata_service      │
  │   └─ job_queue (ARQ)       │
  └────────────────────────────┘
       ↓                    ↓
   回调接收器           定时轮询器
       ↓                    ↓
  ┌────────────────────────────┐
  │   RAGFlow / Dify           │
  │   (解析 + chunk + embed)   │
  └────────────────────────────┘
       ↓
  Metadata 更新 → PostgreSQL
       ↓
   人工审核 → 发布
```

### 2.2 模块职责

| 模块 | 职责 | 所在文件 |
|------|------|----------|
| `document_preprocessor` | 文档清洗与拆分（去噪音、拆分大文件） | `services/preprocessor.py` |
| `router_service` | 根据文档类型路由到对应引擎 | `services/router.py` |
| `metadata_service` | 构建标准化元数据 | `services/metadata.py` |
| `metadata_repository` | 元数据持久化与版本回溯 | `repositories/metadata.py` |
| `ingest_pipeline` | 同步入口，提交异步任务 | `pipelines/ingest.py` |
| `job_service` | ARQ 任务调度（提交/查询/重试） | `services/job.py` |
| `status_tracker` | 回调 + 轮询双重状态同步 | `services/status.py` |
| `audit_service` | 操作审计日志 | `services/audit.py` |
| `ingest_api` | 单文档上传 API | `api/ingest.py` |
| `batch_api` | 批量入库 + 定时任务触发 | `api/batch.py` |
| `review_api` | 人工审核 API | `api/review.py` |
| `callback_api` | 外部回调接收 | `api/callback.py` |

### 2.3 Document Preprocessor 职责

文档预处理是入库的第一道工序，负责：

| 功能 | 说明 |
|------|------|
| 噪音清洗 | 去除水印、页眉页脚、重复内容、无用标记 |
| 大文件拆分 | 将大型文档按页拆分为多个小文档块（如 500 页拆为 10 个 50 页块） |
| 格式保留 | 源文档清洗后保留原格式（不做格式转换） |

**与 RAGFlow/Dify Chunking 的区别**：
- **物理拆分（Preprocessor）**：按页拆分文档，便于传输和并发处理
- **语义分块（RAGFlow/Dify）**：按语义段落/句子 chunk，是检索粒度

两者各司其职，kb_service 做物理拆分，RAGFlow/Dify 做语义分块。

**拆分参数（API 可配置）**：
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `enable_split` | 是否启用拆分 | `false` |
| `pages_per_chunk` | 每块页数 | `50` |
| `max_chunks` | 最大块数上限 | `100` |

**Preprocessor 输入**：
```python
file_path: str      # 文件路径
mime_type: str      # MIME 类型（如 application/pdf）
```

**Preprocessor 输出**：
```python
chunks: list[DocumentChunk]  # 拆分后的文档块列表
doc_type: DocumentType       # 检测到的文档类型
```

**设计原则**：
- 拆分粒度可配置（按页数）
- 保留元信息（所属文档、页码范围）
- 拆分后的小文档独立可处理
- **不做格式统一转换**，只做清洗和物理拆分
- 不做 OCR（保持轻量）

---

## 3. 核心数据模型

### 3.1 文档类型枚举

```python
class DocumentType(str, Enum):
    PLAIN_TEXT = "plain_text"        # 纯文本
    COMPLEX_LAYOUT = "complex_layout" # 复杂布局
    SCANNED_PDF = "scanned_pdf"      # 扫描 PDF
    TABLE_HEAVY = "table_heavy"      # 表格密集
    IMAGE_RICH = "image_rich"         # 图文混合
```

### 3.2 目标引擎枚举

```python
class Backend(str, Enum):
    RAGFLOW = "ragflow"   # 纯文本类文档
    DIFY = "dify"         # 复杂布局类文档
```

### 3.3 任务状态枚举

```python
class JobStatus(str, Enum):
    PROCESSING = "processing"       # 处理中
    PENDING_REVIEW = "pending_review" # 待审核
    PUBLISHED = "published"          # 已发布
    REJECTED = "rejected"            # 审核拒绝
    FAILED = "failed"                # 处理失败
```

### 3.4 IngestJob 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `job_id` | str | 业务任务 ID（外部可见） |
| `trace_id` | str | 端到端追踪 ID（用于日志串联） |
| `doc_id` | str | 文档唯一标识 |
| `business_id` | str | 业务线 ID |
| `doc_type` | DocumentType | 文档类型 |
| `backend` | Backend | 目标引擎 |
| `status` | JobStatus | 当前状态 |
| `file_path` | str | 文件存储路径 |
| `file_name` | str | 原始文件名 |
| `file_size` | int | 文件大小（字节） |
| `kb_version` | str | 知识库版本 |
| `release_id` | str \| null | 发布记录 ID |
| `callback_url` | str \| null | 回调地址 |
| `error_message` | str \| null | 失败原因 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |
| `reviewed_by` | str \| null | 审核人 |
| `reviewed_at` | datetime \| null | 审核时间 |

### 3.5 AuditLog 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `job_id` | str | 关联任务 ID |
| `action` | str | 操作类型（ingest/review/publish/rollback） |
| `operator` | str | 操作人 |
| `detail` | JSON | 详情 |
| `created_at` | datetime | 操作时间 |

### 3.6 DocumentChunk 数据模型

预处理拆分后的文档块：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `job_id` | str | 关联任务 ID |
| `chunk_index` | int | 块序号 |
| `file_path` | str | 块文件路径 |
| `page_start` | int | 起始页码 |
| `page_end` | int | 结束页码 |
| `title` | str \| null | 章节标题 |
| `word_count` | int | 字数 |
| `created_at` | datetime | 创建时间 |

---

## 4. API 设计

### 4.1 单文档上传入库

```
POST /api/v1/kb/ingest
Content-Type: multipart/form-data

请求参数：
  - file: 文件（二进制）
  - business_id: str (必填) 业务线 ID
  - callback_url: str (可选) 回调地址
  - enable_split: bool (可选) 是否启用拆分，默认 false
  - pages_per_chunk: int (可选) 每块页数，默认 50
  - max_chunks: int (可选) 最大块数上限，默认 100

响应：
  {
    "job_id": "uuid",
    "doc_id": "doc_xxx",
    "status": "processing",
    "created_at": "2026-04-28T10:00:00Z"
  }
```

### 4.2 批量入库触发

```
POST /api/v1/kb/batch/ingest
Content-Type: application/json

请求参数：
  - business_id: str (必填) 业务线 ID
  - directory_path: str (必填) 要扫描的目录路径
  - file_patterns: list[str] (可选) 文件匹配模式，如 ["*.pdf", "*.docx"]

响应：
  {
    "batch_id": "uuid",
    "jobs": [
      {"file": "xxx.pdf", "job_id": "uuid"},
      {"file": "yyy.docx", "job_id": "uuid"}
    ],
    "total": 2
  }
```

### 4.3 定时批量扫描

定时任务触发，扫描配置目录，找出新文件自动入库。

```
触发方式：定时任务（apscheduler）
扫描目录：从配置读取
```

### 4.4 任务状态查询

```
GET /api/v1/kb/jobs/{job_id}

响应：
  {
    "job_id": "uuid",
    "doc_id": "doc_xxx",
    "status": "pending_review",
    "backend": "dify",
    "doc_type": "complex_layout",
    "created_at": "2026-04-28T10:00:00Z",
    "updated_at": "2026-04-28T10:05:00Z"
  }
```

### 4.5 人工审核

```
POST /api/v1/kb/jobs/{job_id}/review

请求参数：
  - action: "approve" | "reject"
  - comment: str (可选) 审核意见

响应：
  {
    "job_id": "uuid",
    "status": "published",  // 或 "rejected"
    "reviewed_by": "admin",
    "reviewed_at": "2026-04-28T10:10:00Z"
  }
```

### 4.6 外部回调接收

```
POST /api/v1/kb/callback/{job_id}
Content-Type: application/json

请求参数：
  - status: "success" | "failed"
  - message: str (可选)
  - result: dict (可选) 额外结果

响应：
  {"received": true}
```

---

## 5. 核心流程

### 5.1 文档入库流程（Phase 1）

```
1. 用户上传文件 / 定时扫描发现新文件
2. 生成 trace_id（端到端追踪）
3. document_preprocessor 清洗文档（去噪音、无用文字）
4. document_preprocessor 拆分大文档（500页 → 多个小文档块）
5. router_service 根据文档类型决定目标引擎
   - plain_text → RAGFlow
   - complex_layout/scanned_pdf/table_heavy/image_rich → Dify
6. metadata_service 生成标准化元数据（doc_id, business_id, trace_id, ...）
7. ingest_pipeline 保存元数据（status=processing）到 PostgreSQL
8. ARQ 提交异步任务（携带 trace_id）
9. 返回 job_id 给调用方

（异步执行）
9. ARQ Worker 调用 RAGFlow/Dify API 上传文件
10. RAGFlow/Dify 处理中（解析 + chunk + embedding）
11. 处理完成，回调 kb_service
12. 若无回调，status_tracker 定时轮询兜底
13. kb_service 更新 metadata（status=pending_review）
14. 人工审核 → approve → status=published
```

### 5.2 状态流转

```
[上传]
  ↓
processing (处理中)
  ↓
pending_review (待审核)
  ↙        ↘
published    rejected
(已发布)    (可重新提交)
```

### 5.3 回调 + 轮询混合模式

| 场景 | 处理方式 |
|------|----------|
| RAGFlow/Dify 主动回调 | 接收回调，更新状态 |
| 回调超时/失败 | status_tracker 轮询（每 30s，最多 10 次） |
| 轮询确认完成 | 更新状态为 pending_review |
| 轮询确认失败 | 更新状态为 failed，记录原因 |

---

## 6. 文件结构

```
apps/kb_service/
├── __init__.py
├── main.py                    # FastAPI 应用工厂
├── api/
│   ├── __init__.py
│   ├── ingest.py              # 单文档上传
│   ├── batch.py               # 批量入库
│   ├── review.py              # 人工审核
│   ├── callback.py            # 外部回调接收
│   └── query.py               # 状态查询
├── services/
│   ├── __init__.py
│   ├── preprocessor.py          # 文档清洗与拆分（去噪音、拆分大文件）
│   ├── router.py              # 路由服务
│   ├── metadata.py            # 元数据构建
│   ├── job.py                 # ARQ 任务服务
│   ├── status.py              # 状态跟踪器（回调 + 轮询）
│   └── audit.py               # 审计服务
├── repositories/
│   ├── __init__.py
│   └── metadata.py            # 元数据持久化与版本回溯
├── pipelines/
│   ├── __init__.py
│   ├── ingest.py              # 入库流水线
│   └── batch.py               # 批量入库流水线
├── schemas/
│   ├── __init__.py
│   ├── ingest.py              # 入库相关 schema
│   ├── job.py                  # 任务相关 schema
│   └── review.py               # 审核相关 schema
├── models/
│   ├── __init__.py
│   ├── ingest_job.py           # IngestJob 模型
│   └── audit_log.py            # AuditLog 模型
├── clients/
│   ├── __init__.py
│   ├── ragflow_client.py       # RAGFlow API 客户端
│   └── dify_client.py          # Dify API 客户端（已有）
├── core/
│   ├── __init__.py
│   ├── config.py               # 配置
│   └── exceptions.py           # 异常定义
└── utils/
    ├── __init__.py
    └── file_utils.py           # 文件处理工具

pipelines/
├── __init__.py
├── ingest.py                   # 入库主流程
├── update.py                   # 更新流程（Phase 2）
├── publish.py                  # 发布流程
└── rollback.py                # 回滚流程（Phase 2）
```

---

## 7. 技术选型

| 组件 | 选型 | 说明 |
|------|------|------|
| 异步队列 | ARQ（Asynchronous Redis Queue） | Python 专用，轻量，支持重试 |
| 元数据库 | PostgreSQL | 与 RBAC 模块共用 |
| 状态同步 | 回调 + 轮询混合 | 回调优先，轮询兜底 |
| 定时任务 | APScheduler | 批量扫描触发 |
| API 框架 | FastAPI | 与现有架构一致 |

---

## 8. Phase 2 扩展点

| 扩展点 | 说明 |
|--------|------|
| 自建解析 | 接入 pypdf/docx/python-docx 解析文档 |
| 标准化分块 | 实现 chunk_service，支持多种分块策略 |
| 自建 Embedding | 可选接入 sentence-transformers |
| 灰度发布 | 支持版本灰度，渐进式曝光 |
| 多租户 | 租户隔离，元数据加上 tenant_id |

---

## 8.1 重要约束（必须遵守）

> **谁负责检索，谁负责 chunk** — kb_service **不做**以下操作：

| 约束 | 说明 |
|------|------|
| ❌ 不做 chunk | chunking 由 RAGFlow/Dify 负责 |
| ❌ 不做 OCR | 保持轻量，不做光学字符识别 |
| ❌ 不做格式转换 | 保留原格式，不统一转 Markdown |

---

## 9. 验收标准

- [ ] 支持上传 docx/pdf 文件
- [ ] 自动分类并路由到 RAGFlow/Dify
- [ ] 异步任务通过 ARQ 调度
- [ ] 元数据存入 PostgreSQL，可查询状态
- [ ] 回调 + 轮询双重状态同步
- [ ] 人工审核通过后才发布
- [ ] 操作审计日志完整记录
- [ ] 定时批量扫描触发入库
- [ ] 审核后可 approve/reject
- [ ] 可扩展（新增引擎不影响主流程）

---

## 11. 开发顺序

1. `models/ingest_job.py` + `models/audit_log.py` + `models/document_chunk.py` — 数据模型
2. `repositories/metadata.py` — 元数据持久化与版本回溯
3. `schemas/` — Pydantic 请求/响应模型
4. `services/metadata.py` — 元数据构建
5. `services/preprocessor.py` — 文档清洗与拆分
6. `services/router.py` — 路由服务
7. `pipelines/ingest.py` — 入库流水线（同步版）
8. `services/job.py` — ARQ 任务调度
9. `clients/ragflow_client.py` — RAGFlow 客户端
10. `clients/dify_client.py` — Dify 客户端（扩展）
11. `services/status.py` — 状态跟踪器
12. `services/audit.py` — 审计服务
13. `api/ingest.py` — 上传 API
14. `api/batch.py` — 批量 API + 定时任务
15. `api/review.py` — 审核 API
16. `api/callback.py` — 回调 API
17. `main.py` — 应用工厂集成

---

**下一步**：设计文档 Review 通过后 → writing-plans skill → 实现计划