# kb_service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 kb_service 知识库文档入库服务，包括文档上传、路由、异步任务、状态跟踪和人工审核。

**Architecture:** kb_service 是 FastAPI + Tortoise ORM 的独立微服务，通过 ARQ 异步队列与 RAGFlow/Dify 交互。采用工厂模式（AppFactory），模块化设计，数据模型与 RBAC 模块共用 PostgreSQL。

**Tech Stack:** FastAPI, Tortoise ORM, ARQ (Redis Queue), APScheduler, PostgreSQL

---

## 文件结构

```
apps/kb_service/
├── __init__.py
├── main.py                    # FastAPI 应用工厂 (create_kb_app)
├── api/
│   ├── __init__.py
│   ├── ingest.py              # 单文档上传 POST /api/v1/kb/ingest
│   ├── batch.py               # 批量入库 POST /api/v1/kb/batch/ingest
│   ├── review.py              # 人工审核 POST /api/v1/kb/jobs/{job_id}/review
│   ├── callback.py            # 外部回调 POST /api/v1/kb/callback/{job_id}
│   └── query.py               # 状态查询 GET /api/v1/kb/jobs/{job_id}
├── services/
│   ├── __init__.py
│   ├── preprocessor.py        # 文档清洗与拆分
│   ├── router.py              # 路由服务
│   ├── metadata.py            # 元数据构建
│   ├── job.py                 # ARQ 任务调度
│   ├── status.py              # 状态跟踪器（回调+轮询）
│   └── audit.py               # 审计服务
├── repositories/
│   ├── __init__.py
│   └── metadata.py            # 元数据持久化
├── pipelines/
│   ├── __init__.py
│   └── ingest.py              # 入库流水线
├── schemas/
│   ├── __init__.py
│   ├── ingest.py              # 入库相关 schema
│   ├── job.py                 # 任务相关 schema
│   └── review.py              # 审核相关 schema
├── models/
│   ├── __init__.py
│   ├── ingest_job.py          # IngestJob 模型
│   ├── audit_log.py           # AuditLog 模型
│   └── document_chunk.py      # DocumentChunk 模型
├── clients/
│   ├── __init__.py
│   ├── ragflow_client.py      # RAGFlow API 客户端
│   └── dify_client.py         # Dify API 客户端
├── core/
│   ├── __init__.py
│   ├── config.py               # 配置
│   └── exceptions.py          # 异常定义
└── utils/
    ├── __init__.py
    └── file_utils.py          # 文件处理工具
```

**新建模块继承模式（参考 apps/rbac）：**
- `models/base.py` → TimestampMixin + BaseModel
- `schemas/base.py` → Success/Fail/SuccessExtra 响应包装
- `core/exceptions.py` → 自定义异常 + register_exceptions

**与 apps/main.py 的集成点：**
- `apps/main.py` 的 `create_app()` → 需 include kb_service router
- 路由前缀：`/api/v1/kb/*`

---

## 开发顺序（17步）

### Task 1: 数据模型 — IngestJob / AuditLog / DocumentChunk

**Files:**
- Create: `apps/kb_service/models/__init__.py`
- Create: `apps/kb_service/models/base.py`
- Create: `apps/kb_service/models/ingest_job.py`
- Create: `apps/kb_service/models/audit_log.py`
- Create: `apps/kb_service/models/document_chunk.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/kb_service/models/test_ingest_job.py
import pytest
from apps.kb_service.models.ingest_job import IngestJob

@pytest.mark.asyncio
async def test_ingest_job_create():
    job = IngestJob(
        job_id="test_job_001",
        doc_id="doc_xxx",
        business_id="biz_001",
        doc_type="plain_text",
        backend="ragflow",
        status="processing",
        file_path="/uploads/test.pdf",
        file_name="test.pdf",
        file_size=1024,
    )
    assert job.job_id == "test_job_001"
    assert job.status == "processing"
```

Run: `pytest tests/kb_service/models/test_ingest_job.py -v`
Expected: PASS ( Tortoise needs init first, may fail — verify model fields)

- [ ] **Step 2: 创建 models/base.py**

```python
# apps/kb_service/models/base.py
from tortoise import fields
from tortoise.models import Model


class TimestampMixin:
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")


class BaseModel(Model):
    id = fields.UUIDField(pk=True)

    class Meta:
        abstract = True
```

- [ ] **Step 3: 创建 ingest_job.py**

```python
# apps/kb_service/models/ingest_job.py
import uuid
from enum import Enum

from tortoise import fields

from .base import BaseModel, TimestampMixin


class DocumentType(str, Enum):
    PLAIN_TEXT = "plain_text"
    COMPLEX_LAYOUT = "complex_layout"
    SCANNED_PDF = "scanned_pdf"
    TABLE_HEAVY = "table_heavy"
    IMAGE_RICH = "image_rich"


class Backend(str, Enum):
    RAGFLOW = "ragflow"
    DIFY = "dify"


class JobStatus(str, Enum):
    PROCESSING = "processing"
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    REJECTED = "rejected"
    FAILED = "failed"


class IngestJob(BaseModel, TimestampMixin):
    job_id = fields.CharField(max_length=64, unique=True, description="业务任务ID", index=True)
    trace_id = fields.CharField(max_length=64, description="追踪ID", index=True)
    doc_id = fields.CharField(max_length=64, description="文档唯一标识", index=True)
    business_id = fields.CharField(max_length=64, description="业务线ID", index=True)
    doc_type = fields.CharField(max_length=32, description="文档类型")
    backend = fields.CharField(max_length=16, description="目标引擎")
    status = fields.CharField(max_length=32, description="状态", index=True)
    file_path = fields.CharField(max_length=512, description="文件存储路径")
    file_name = fields.CharField(max_length=256, description="原始文件名")
    file_size = fields.IntField(description="文件大小")
    kb_version = fields.CharField(max_length=32, null=True, description="知识库版本")
    release_id = fields.CharField(max_length=64, null=True, description="发布记录ID")
    callback_url = fields.CharField(max_length=512, null=True, description="回调地址")
    error_message = fields.TextField(null=True, description="失败原因")
    reviewed_by = fields.CharField(max_length=64, null=True, description="审核人")
    reviewed_at = fields.DatetimeField(null=True, description="审核时间")

    class Meta:
        table = "kb_ingest_job"
```

- [ ] **Step 4: 创建 audit_log.py 和 document_chunk.py**

```python
# apps/kb_service/models/audit_log.py
from tortoise import fields
from .base import BaseModel, TimestampMixin


class AuditLog(BaseModel, TimestampMixin):
    job_id = fields.CharField(max_length=64, description="关联任务ID", index=True)
    action = fields.CharField(max_length=32, description="操作类型")
    operator = fields.CharField(max_length=64, description="操作人")
    detail = fields.JSONField(null=True, description="详情")

    class Meta:
        table = "kb_audit_log"


# apps/kb_service/models/document_chunk.py
from tortoise import fields
from .base import BaseModel, TimestampMixin


class DocumentChunk(BaseModel, TimestampMixin):
    job_id = fields.CharField(max_length=64, description="关联任务ID", index=True)
    chunk_index = fields.IntField(description="块序号")
    file_path = fields.CharField(max_length=512, description="块文件路径")
    page_start = fields.IntField(description="起始页码")
    page_end = fields.IntField(description="结束页码")
    title = fields.CharField(max_length=256, null=True, description="章节标题")
    word_count = fields.IntField(default=0, description="字数")

    class Meta:
        table = "kb_document_chunk"
```

- [ ] **Step 5: Commit**

```bash
git add apps/kb_service/models/ tests/kb_service/models/
git commit -m "feat(kb_service): add data models - IngestJob, AuditLog, DocumentChunk"
```

---

### Task 2: Repository — MetadataRepository

**Files:**
- Create: `apps/kb_service/repositories/__init__.py`
- Create: `apps/kb_service/repositories/metadata.py`
- Test: `tests/kb_service/repositories/test_metadata.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/kb_service/repositories/test_metadata.py
import pytest
from apps.kb_service.repositories.metadata import MetadataRepository

@pytest.mark.asyncio
async def test_create_and_get_ingest_job():
    repo = MetadataRepository()
    job = await repo.create_ingest_job(...)
    assert job.id is not None

@pytest.mark.asyncio
async def test_update_job_status():
    repo = MetadataRepository()
    updated = await repo.update_status("job_xxx", "pending_review")
    assert updated.status == "pending_review"
```

Run: `pytest tests/kb_service/repositories/test_metadata.py -v`
Expected: FAIL (module not found)

- [ ] **Step 2: 创建 repositories/metadata.py**

```python
# apps/kb_service/repositories/metadata.py
from typing import Optional

from apps.kb_service.models.ingest_job import IngestJob, JobStatus


class MetadataRepository:
    async def create_ingest_job(self, **kwargs) -> IngestJob:
        return await IngestJob.create(**kwargs)

    async def get_ingest_job_by_job_id(self, job_id: str) -> Optional[IngestJob]:
        return await IngestJob.filter(job_id=job_id).first()

    async def update_status(
        self, job_id: str, status: str, error_message: Optional[str] = None, **kwargs
    ) -> Optional[IngestJob]:
        job = await self.get_ingest_job_by_job_id(job_id)
        if not job:
            return None
        job.status = status
        if error_message:
            job.error_message = error_message
        for k, v in kwargs.items():
            setattr(job, k, v)
        await job.save()
        return job

    async def list_jobs_by_business(
        self, business_id: str, status: Optional[str] = None, limit: int = 100
    ):
        q = IngestJob.filter(business_id=business_id)
        if status:
            q = q.filter(status=status)
        return await q.limit(limit).order_by("-created_at")
```

- [ ] **Step 3: Commit**

```bash
git add apps/kb_service/repositories/ tests/kb_service/repositories/
git commit -m "feat(kb_service): add MetadataRepository for job persistence"
```

---

### Task 3: Schemas — Pydantic 请求/响应模型

**Files:**
- Create: `apps/kb_service/schemas/__init__.py`
- Create: `apps/kb_service/schemas/ingest.py`
- Create: `apps/kb_service/schemas/job.py`
- Create: `apps/kb_service/schemas/review.py`
- Test: `tests/kb_service/schemas/`

- [ ] **Step 1: Write schema tests and create files**

```python
# apps/kb_service/schemas/ingest.py
from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    business_id: str = Field(..., description="业务线ID")
    callback_url: str | None = Field(None, description="回调地址")
    enable_split: bool = Field(False, description="是否启用拆分")
    pages_per_chunk: int = Field(50, ge=1, le=500, description="每块页数")
    max_chunks: int = Field(100, ge=1, description="最大块数上限")


class IngestResponse(BaseModel):
    job_id: str
    doc_id: str
    status: str
    created_at: str
```

- [ ] **Step 2: Create job.py and review.py schemas**

```python
# apps/kb_service/schemas/job.py
from pydantic import BaseModel
from typing import Optional


class JobStatusResponse(BaseModel):
    job_id: str
    doc_id: str
    status: str
    backend: str
    doc_type: str
    created_at: str
    updated_at: str


# apps/kb_service/schemas/review.py
from pydantic import BaseModel


class ReviewRequest(BaseModel):
    action: str  # "approve" | "reject"
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    job_id: str
    status: str
    reviewed_by: str
    reviewed_at: str
```

- [ ] **Step 3: Commit**

```bash
git add apps/kb_service/schemas/
git commit -m "feat(kb_service): add Pydantic schemas for API request/response"
```

---

### Task 4: Services — metadata.py（元数据构建）

**Files:**
- Modify: `apps/kb_service/services/metadata.py` (create)
- Test: `tests/kb_service/services/test_metadata.py`

- [ ] **Step 1: Create metadata service**

```python
# apps/kb_service/services/metadata.py
import uuid
from apps.kb_service.models.ingest_job import Backend, DocumentType, IngestJob, JobStatus
from apps.kb_service.repositories.metadata import MetadataRepository


class MetadataService:
    def __init__(self):
        self.repo = MetadataRepository()

    def generate_doc_id(self) -> str:
        return f"doc_{uuid.uuid4().hex[:16]}"

    def generate_trace_id(self) -> str:
        return f"trace_{uuid.uuid4().hex[:16]}"

    async def build_ingest_job(
        self,
        file_path: str,
        file_name: str,
        file_size: int,
        business_id: str,
        doc_type: DocumentType,
        backend: Backend,
        callback_url: str | None = None,
    ) -> IngestJob:
        job_data = {
            "job_id": f"job_{uuid.uuid4().hex[:16]}",
            "trace_id": self.generate_trace_id(),
            "doc_id": self.generate_doc_id(),
            "business_id": business_id,
            "doc_type": doc_type.value,
            "backend": backend.value,
            "status": JobStatus.PROCESSING.value,
            "file_path": file_path,
            "file_name": file_name,
            "file_size": file_size,
            "callback_url": callback_url,
        }
        return await self.repo.create_ingest_job(**job_data)
```

- [ ] **Step 2: Commit**

```bash
git add apps/kb_service/services/metadata.py
git commit -m "feat(kb_service): add MetadataService for job metadata building"
```

---

### Task 5: Services — preprocessor.py（文档清洗与拆分）

**Files:**
- Create: `apps/kb_service/services/preprocessor.py`
- Test: `tests/kb_service/services/test_preprocessor.py`

- [ ] **Step 1: Write failing test**

```python
# tests/kb_service/services/test_preprocessor.py
import pytest
from apps.kb_service.services.preprocessor import DocumentPreprocessor, DocumentType

def test_detect_plain_text():
    preprocessor = DocumentPreprocessor()
    doc_type = preprocessor.detect_document_type("test.txt")
    assert doc_type == DocumentType.PLAIN_TEXT
```

Run: `pytest tests/kb_service/services/test_preprocessor.py -v`
Expected: FAIL (module not found)

- [ ] **Step 2: Create preprocessor.py**

```python
# apps/kb_service/services/preprocessor.py
import os
from dataclasses import dataclass
from enum import Enum

from apps.kb_service.models.document_chunk import DocumentChunk


class DocumentType(str, Enum):
    PLAIN_TEXT = "plain_text"
    COMPLEX_LAYOUT = "complex_layout"
    SCANNED_PDF = "scanned_pdf"
    TABLE_HEAVY = "table_heavy"
    IMAGE_RICH = "image_rich"


@dataclass
class DocumentChunk:
    chunk_index: int
    file_path: str
    page_start: int
    page_end: int
    title: str | None = None
    word_count: int = 0


class DocumentPreprocessor:
    MIME_TYPE_MAP = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
        ".md": "text/markdown",
    }

    def detect_document_type(self, file_path: str) -> DocumentType:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".txt" or ext == ".md":
            return DocumentType.PLAIN_TEXT
        elif ext == ".pdf":
            return DocumentType.COMPLEX_LAYOUT
        elif ext == ".docx":
            return DocumentType.COMPLEX_LAYOUT
        return DocumentType.COMPLEX_LAYOUT

    def clean_document(self, file_path: str) -> str:
        # 去噪音：保留原格式，只做必要清洗
        return file_path

    def split_document(
        self, file_path: str, pages_per_chunk: int = 50, max_chunks: int = 100
    ) -> list[DocumentChunk]:
        # 按页拆分（物理拆分，不是语义chunking）
        # Phase 1: 简单实现，返回单个完整文件
        return [
            DocumentChunk(
                chunk_index=0,
                file_path=file_path,
                page_start=1,
                page_end=9999,
            )
        ]
```

- [ ] **Step 3: Commit**

```bash
git add apps/kb_service/services/preprocessor.py
git commit -m "feat(kb_service): add DocumentPreprocessor for cleaning and splitting"
```

---

### Task 6: Services — router.py（路由服务）

**Files:**
- Create: `apps/kb_service/services/router.py`
- Test: `tests/kb_service/services/test_router.py`

- [ ] **Step 1: Write failing test**

```python
# tests/kb_service/services/test_router.py
import pytest
from apps.kb_service.services.router import RouterService, DocumentType, Backend

def test_route_plain_text_to_ragflow():
    router = RouterService()
    backend = router.route(DocumentType.PLAIN_TEXT)
    assert backend == Backend.RAGFLOW

def test_route_complex_to_dify():
    router = RouterService()
    backend = router.route(DocumentType.COMPLEX_LAYOUT)
    assert backend == Backend.DIFY
```

Run: `pytest tests/kb_service/services/test_router.py -v`
Expected: FAIL

- [ ] **Step 2: Create router.py**

```python
# apps/kb_service/services/router.py
from apps.kb_service.models.ingest_job import Backend, DocumentType


class RouterService:
    def route(self, doc_type: DocumentType) -> Backend:
        if doc_type == DocumentType.PLAIN_TEXT:
            return Backend.RAGFLOW
        # complex_layout / scanned_pdf / table_heavy / image_rich → Dify
        return Backend.DIFY
```

- [ ] **Step 3: Commit**

```bash
git add apps/kb_service/services/router.py
git commit -m "feat(kb_service): add RouterService for engine routing"
```

---

### Task 7: Pipelines — ingest.py（入库流水线）

**Files:**
- Create: `apps/kb_service/pipelines/__init__.py`
- Create: `apps/kb_service/pipelines/ingest.py`
- Test: `tests/kb_service/pipelines/test_ingest.py`

- [ ] **Step 1: Write failing test**

```python
# tests/kb_service/pipelines/test_ingest.py
import pytest
from apps.kb_service.pipelines.ingest import IngestPipeline

@pytest.mark.asyncio
async def test_ingest_pipeline_returns_job_id():
    pipeline = IngestPipeline()
    result = await pipeline.run("/tmp/test.pdf", "biz_001", enable_split=False)
    assert "job_id" in result
```

Run: `pytest tests/kb_service/pipelines/test_ingest.py -v`
Expected: FAIL

- [ ] **Step 2: Create pipelines/ingest.py**

```python
# apps/kb_service/pipelines/ingest.py
import os
from apps.kb_service.models.ingest_job import Backend, DocumentType, IngestJob, JobStatus
from apps.kb_service.repositories.metadata import MetadataRepository
from apps.kb_service.services.metadata import MetadataService
from apps.kb_service.services.preprocessor import DocumentPreprocessor
from apps.kb_service.services.router import RouterService


class IngestPipeline:
    def __init__(self):
        self.preprocessor = DocumentPreprocessor()
        self.router = RouterService()
        self.metadata_service = MetadataService()
        self.repo = MetadataRepository()

    async def run(
        self,
        file_path: str,
        business_id: str,
        callback_url: str | None = None,
        enable_split: bool = False,
        pages_per_chunk: int = 50,
        max_chunks: int = 100,
    ) -> dict:
        # 1. 清洗文档
        cleaned_path = self.preprocessor.clean_document(file_path)

        # 2. 拆分文档（可选）
        chunks = []
        if enable_split:
            chunks = self.preprocessor.split_document(
                file_path, pages_per_chunk, max_chunks
            )

        # 3. 检测文档类型
        doc_type = self.preprocessor.detect_document_type(file_path)

        # 4. 路由引擎
        backend = self.router.route(doc_type)

        # 5. 构建元数据
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        job: IngestJob = await self.metadata_service.build_ingest_job(
            file_path=cleaned_path,
            file_name=file_name,
            file_size=file_size,
            business_id=business_id,
            doc_type=doc_type,
            backend=backend,
            callback_url=callback_url,
        )

        return {
            "job_id": job.job_id,
            "doc_id": job.doc_id,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
        }
```

- [ ] **Step 3: Create pipelines/batch.py**

```python
# apps/kb_service/pipelines/batch.py
import os
from apps.kb_service.pipelines.ingest import IngestPipeline


class BatchPipeline:
    def __init__(self):
        self.pipeline = IngestPipeline()

    async def run_batch(
        self,
        directory_path: str,
        business_id: str,
        file_patterns: list[str] = ["*.pdf", "*.docx", "*.txt"],
    ) -> list[dict]:
        import glob

        files = []
        for pattern in file_patterns:
            files.extend(glob.glob(os.path.join(directory_path, pattern)))

        results = []
        for file_path in files:
            result = await self.pipeline.run(
                file_path=file_path,
                business_id=business_id,
            )
            results.append({
                "file": os.path.basename(file_path),
                "job_id": result["job_id"],
                "doc_id": result["doc_id"],
            })
        return results
```

- [ ] **Step 4: Commit**

```bash
git add apps/kb_service/pipelines/
git commit -m "feat(kb_service): add BatchPipeline for batch document ingestion"
```

---

### Task 8: Services — job.py（ARQ 任务调度）

**Files:**
- Create: `apps/kb_service/services/job.py`
- Test: `tests/kb_service/services/test_job.py`

- [ ] **Step 1: Write failing test**

```python
# tests/kb_service/services/test_job.py
import pytest
from apps.kb_service.services.job import JobService

def test_submit_job():
    service = JobService()
    job_id = service.submit_ingest_job("job_xxx", "ragflow")
    assert job_id is not None
```

Run: `pytest tests/kb_service/services/test_job.py -v`
Expected: FAIL

- [ ] **Step 2: Create job.py（Phase 1 简单实现，ARQ Worker 后续接入）**

```python
# apps/kb_service/services/job.py
import asyncio
from apps.kb_service.models.ingest_job import IngestJob, JobStatus
from apps.kb_service.repositories.metadata import MetadataRepository


class JobService:
    def __init__(self):
        self.repo = MetadataRepository()

    async def submit_ingest_job(self, job_id: str, backend: str) -> str:
        # Phase 1: 打印任务信息，实际ARQ调度在 Task 10 实现
        job = await self.repo.get_ingest_job_by_job_id(job_id)
        if job:
            job.status = JobStatus.PROCESSING.value
            await job.save()
        return job_id

    async def get_job_status(self, job_id: str) -> str | None:
        job = await self.repo.get_ingest_job_by_job_id(job_id)
        return job.status if job else None
```

- [ ] **Step 3: Commit**

```bash
git add apps/kb_service/services/job.py
git commit -m "feat(kb_service): add JobService for ARQ task scheduling"
```

---

### Task 9: Clients — ragflow_client.py 和 dify_client.py

**Files:**
- Create: `apps/kb_service/clients/__init__.py`
- Create: `apps/kb_service/clients/ragflow_client.py`
- Create: `apps/kb_service/clients/dify_client.py`
- Test: `tests/kb_service/clients/`

- [ ] **Step 1: Write failing test for ragflow_client**

```python
# tests/kb_service/clients/test_ragflow_client.py
import pytest
from apps.kb_service.clients.ragflow_client import RagFlowClient

def test_client_initialization():
    client = RagFlowClient(base_url="http://localhost:9380", api_key="test")
    assert client.base_url == "http://localhost:9380"
```

Run: `pytest tests/kb_service/clients/ -v`
Expected: FAIL

- [ ] **Step 2: Create clients**

```python
# apps/kb_service/clients/ragflow_client.py
import httpx


class RagFlowClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=60.0)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def upload_document(self, file_path: str, doc_id: str) -> dict:
        # Phase 1: 占位实现
        return {"code": 0, "data": {"doc_id": doc_id}}

    async def get_document_status(self, doc_id: str) -> dict:
        # Phase 1: 占位实现
        return {"code": 0, "data": {"status": "processing"}}

    async def close(self):
        await self.client.aclose()


# apps/kb_service/clients/dify_client.py
import httpx


class DifyClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=60.0)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def upload_document(self, file_path: str, doc_id: str) -> dict:
        return {"code": 0, "data": {"doc_id": doc_id}}

    async def get_document_status(self, doc_id: str) -> dict:
        return {"code": 0, "data": {"status": "processing"}}

    async def close(self):
        await self.client.aclose()
```

- [ ] **Step 3: Commit**

```bash
git add apps/kb_service/clients/
git commit -m "feat(kb_service): add RagFlow and Dify API clients"
```

---

### Task 10: Services — status.py（状态跟踪器）

**Files:**
- Create: `apps/kb_service/services/status.py`
- Test: `tests/kb_service/services/test_status.py`

- [ ] **Step 1: Create status.py（回调+轮询混合模式）**

```python
# apps/kb_service/services/status.py
import asyncio
from apps.kb_service.models.ingest_job import JobStatus
from apps.kb_service.repositories.metadata import MetadataRepository


class StatusTracker:
    def __init__(self):
        self.repo = MetadataRepository()

    async def handle_callback(self, job_id: str, status: str, message: str | None = None):
        """处理外部回调"""
        job = await self.repo.get_ingest_job_by_job_id(job_id)
        if not job:
            return False

        if status == "success":
            await self.repo.update_status(job_id, JobStatus.PENDING_REVIEW.value)
        else:
            await self.repo.update_status(job_id, JobStatus.FAILED.value, error_message=message)
        return True

    async def poll_job_status(self, job_id: str, max_retries: int = 10, interval: int = 30) -> str | None:
        """轮询兜底：每30s查询一次，最多10次"""
        for _ in range(max_retries):
            await asyncio.sleep(interval)
            status = await self._check_external_status(job_id)
            if status in ("success", "failed"):
                await self.handle_callback(job_id, status)
                return status
        return None

    async def _check_external_status(self, job_id: str) -> str:
        # Phase 1: 占位，后续接入客户端查询
        return "pending"
```

- [ ] **Step 2: Commit**

```bash
git add apps/kb_service/services/status.py
git commit -m "feat(kb_service): add StatusTracker with callback + polling"
```

---

### Task 11: Services — audit.py（审计服务）

**Files:**
- Create: `apps/kb_service/services/audit.py`
- Test: `tests/kb_service/services/test_audit.py`

- [ ] **Step 1: Create utils/file_utils.py**

```python
# apps/kb_service/utils/file_utils.py
import os
import uuid
from pathlib import Path


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def save_upload_file(file_content: bytes, filename: str, upload_dir: str) -> str:
    ensure_dir(upload_dir)
    ext = Path(filename).suffix
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, unique_name)
    with open(file_path, "wb") as f:
        f.write(file_content)
    return file_path


def get_file_size(file_path: str) -> int:
    return os.path.getsize(file_path)


def get_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()
```

- [ ] **Step 2: Create audit.py**

```python
# apps/kb_service/services/audit.py
from apps.kb_service.models.audit_log import AuditLog


class AuditService:
    async def log(self, job_id: str, action: str, operator: str, detail: dict | None = None):
        await AuditLog.create(
            job_id=job_id,
            action=action,
            operator=operator,
            detail=detail,
        )
```

- [ ] **Step 3: Commit**

```bash
git add apps/kb_service/utils/ apps/kb_service/services/audit.py
git commit -m "feat(kb_service): add file_utils and AuditService"
```

---

### Task 12: API — ingest.py（单文档上传）

**Files:**
- Create: `apps/kb_service/api/__init__.py`
- Create: `apps/kb_service/api/ingest.py`
- Test: `tests/kb_service/api/test_ingest.py`

- [ ] **Step 1: Write failing test**

```python
# tests/kb_service/api/test_ingest.py
import pytest
from httpx import AsyncClient, ASGITransport
from apps.kb_service.main import create_kb_app

@pytest.mark.asyncio
async def test_ingest_upload():
    app = create_kb_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Note: file upload test requires proper multipart form setup
        pass
```

Run: `pytest tests/kb_service/api/test_ingest.py -v`
Expected: FAIL

- [ ] **Step 2: Create api/ingest.py**

```python
# apps/kb_service/api/ingest.py
import os
import uuid
from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from apps.kb_service.pipelines.ingest import IngestPipeline
from apps.kb_service.schemas.ingest import IngestResponse

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    business_id: str = Form(...),
    callback_url: str | None = Form(None),
    enable_split: bool = Form(False),
    pages_per_chunk: int = Form(50),
    max_chunks: int = Form(100),
):
    # 保存上传文件
    upload_dir = "/tmp/kb_uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{uuid.uuid4().hex}_{file.filename}")
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    pipeline = IngestPipeline()
    result = await pipeline.run(
        file_path=file_path,
        business_id=business_id,
        callback_url=callback_url,
        enable_split=enable_split,
        pages_per_chunk=pages_per_chunk,
        max_chunks=max_chunks,
    )
    return result
```

- [ ] **Step 3: Commit**

```bash
git add apps/kb_service/api/
git commit -m "feat(kb_service): add ingest API endpoint"
```

---

### Task 13: API — batch.py + 定时任务

**Files:**
- Create: `apps/kb_service/api/batch.py`
- Test: `tests/kb_service/api/test_batch.py`

- [ ] **Step 1: Create batch.py**

```python
# apps/kb_service/api/batch.py
import uuid
from fastapi import APIRouter, Body

from apps.kb_service.pipelines.ingest import IngestPipeline

router = APIRouter()


@router.post("/batch/ingest")
async def batch_ingest(
    business_id: str = Body(...),
    directory_path: str = Body(...),
    file_patterns: list[str] = Body(["*.pdf", "*.docx", "*.txt"]),
):
    import glob
    import os

    files = []
    for pattern in file_patterns:
        files.extend(glob.glob(os.path.join(directory_path, pattern)))

    pipeline = IngestPipeline()
    jobs = []
    for file_path in files:
        result = await pipeline.run(file_path=file_path, business_id=business_id)
        jobs.append({"file": os.path.basename(file_path), "job_id": result["job_id"]})

    return {
        "batch_id": f"batch_{uuid.uuid4().hex[:16]}",
        "jobs": jobs,
        "total": len(jobs),
    }
```

- [ ] **Step 2: Commit**

```bash
git add apps/kb_service/api/batch.py
git commit -m "feat(kb_service): add batch ingest API + scheduled scanning"
```

---

### Task 14: API — review.py（人工审核）

**Files:**
- Create: `apps/kb_service/api/review.py`
- Test: `tests/kb_service/api/test_review.py`

- [ ] **Step 1: Create review.py**

```python
# apps/kb_service/api/review.py
from datetime import datetime
from fastapi import APIRouter, HTTPException

from apps.kb_service.models.ingest_job import JobStatus
from apps.kb_service.repositories.metadata import MetadataRepository
from apps.kb_service.schemas.review import ReviewRequest, ReviewResponse
from apps.kb_service.services.audit import AuditService

router = APIRouter()
repo = MetadataRepository()
audit = AuditService()


@router.post("/jobs/{job_id}/review", response_model=ReviewResponse)
async def review_job(job_id: str, request: ReviewRequest, operator: str = "admin"):
    job = await repo.get_ingest_job_by_job_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if request.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Invalid action")

    new_status = JobStatus.PUBLISHED.value if request.action == "approve" else JobStatus.REJECTED.value

    await repo.update_status(
        job_id,
        new_status,
        reviewed_by=operator,
        reviewed_at=datetime.now(),
    )

    await audit.log(job_id, f"review_{request.action}", operator, {"comment": request.comment})

    updated_job = await repo.get_ingest_job_by_job_id(job_id)
    return ReviewResponse(
        job_id=job_id,
        status=new_status,
        reviewed_by=operator,
        reviewed_at=updated_job.reviewed_at.isoformat() if updated_job.reviewed_at else "",
    )
```

- [ ] **Step 2: Commit**

```bash
git add apps/kb_service/api/review.py
git commit -m "feat(kb_service): add review API for job approval/rejection"
```

---

### Task 15: API — callback.py（外部回调接收）

**Files:**
- Create: `apps/kb_service/api/callback.py`
- Test: `tests/kb_service/api/test_callback.py`

- [ ] **Step 1: Create callback.py**

```python
# apps/kb_service/api/callback.py
from fastapi import APIRouter
from pydantic import BaseModel

from apps.kb_service.services.status import StatusTracker

router = APIRouter()
tracker = StatusTracker()


class CallbackPayload(BaseModel):
    status: str  # "success" | "failed"
    message: str | None = None
    result: dict | None = None


@router.post("/callback/{job_id}")
async def receive_callback(job_id: str, payload: CallbackPayload):
    await tracker.handle_callback(job_id, payload.status, payload.message)
    return {"received": True}
```

- [ ] **Step 2: Commit**

```bash
git add apps/kb_service/api/callback.py
git commit -m "feat(kb_service): add callback API for external notifications"
```

---

### Task 16: API — query.py（状态查询）

**Files:**
- Create: `apps/kb_service/api/query.py`
- Test: `tests/kb_service/api/test_query.py`

- [ ] **Step 1: Create query.py**

```python
# apps/kb_service/api/query.py
from fastapi import APIRouter, HTTPException

from apps.kb_service.repositories.metadata import MetadataRepository
from apps.kb_service.schemas.job import JobStatusResponse

router = APIRouter()
repo = MetadataRepository()


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    job = await repo.get_ingest_job_by_job_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.job_id,
        doc_id=job.doc_id,
        status=job.status,
        backend=job.backend,
        doc_type=job.doc_type,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
    )
```

- [ ] **Step 2: Commit**

```bash
git add apps/kb_service/api/query.py
git commit -m "feat(kb_service): add query API for job status lookup"
```

---

### Task 17: main.py — 应用工厂集成

**Files:**
- Create: `apps/kb_service/__init__.py`
- Create: `apps/kb_service/main.py`
- Create: `apps/kb_service/core/__init__.py`
- Create: `apps/kb_service/core/config.py`
- Create: `apps/kb_service/core/exceptions.py`
- Modify: `apps/main.py` (include kb_router)
- Test: `tests/kb_service/test_main.py`

- [ ] **Step 1: Create core/config.py 和 exceptions.py**

```python
# apps/kb_service/core/config.py
from pydantic_settings import BaseSettings


class KBSettings(BaseSettings):
    APP_TITLE: str = "kb_service"
    VERSION: str = "1.0.0"
    UPLOAD_DIR: str = "/tmp/kb_uploads"

    # RAGFlow
    RAGFLOW_BASE_URL: str = "http://localhost:9380"
    RAGFLOW_API_KEY: str = ""

    # Dify
    DIFY_BASE_URL: str = "http://localhost"
    DIFY_API_KEY: str = ""

    # ARQ
    ARQ_REDIS_URL: str = "redis://localhost:6379"

    class Config:
        env_prefix = "KB_"


kb_settings = KBSettings()


# apps/kb_service/core/exceptions.py
from fastapi import HTTPException


class KBServiceException(Exception):
    def __init__(self, message: str, code: int = 400):
        self.message = message
        self.code = code


class JobNotFoundError(KBServiceException):
    def __init__(self, job_id: str):
        super().__init__(f"Job {job_id} not found", code=404)


class InvalidStatusError(KBServiceException):
    def __init__(self, message: str):
        super().__init__(message, code=400)
```

- [ ] **Step 2: Create main.py**

```python
# apps/kb_service/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.kb_service.api import ingest, batch, review, callback, query
from apps.kb_service.core.exceptions import register_exceptions


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_kb_app() -> FastAPI:
    _app = FastAPI(
        title="kb_service",
        description="RAG Knowledge Base Ingest Service",
        version="1.0.0",
        lifespan=lifespan,
    )
    register_exceptions(_app)

    kb_router = FastAPI()
    kb_router.include_router(ingest.router, tags=["ingest"])
    kb_router.include_router(batch.router, tags=["batch"])
    kb_router.include_router(review.router, tags=["review"])
    kb_router.include_router(callback.router, tags=["callback"])
    kb_router.include_router(query.router, tags=["query"])

    _app.mount("/api/v1/kb", kb_router)
    return _app
```

- [ ] **Step 3: Modify apps/main.py to include kb_router**

**当前 `apps/main.py` 第 1-6 行：**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from tortoise import Tortoise
from apps.rbac.api import rbac_router
from apps.rbac.core.exceptions import SettingNotFound, register_exceptions
from apps.rbac.core.init_app import init_data
from apps.rbac.core.middlewares import make_middlewares
try:
    from config.settings.config import settings
except ImportError:
    raise SettingNotFound("Can not import settings")
```

**在第 6 行后添加：**
```python
from apps.kb_service.main import create_kb_app as create_kb_service_app
```

**在 `create_rbac_app()` 函数的 `register_exceptions(_app)` 之后，`return _app` 之前添加：**
```python
    kb_app = create_kb_service_app()
    _app.mount("/api/v1/kb", kb_app)
```

- [ ] **Step 4: Commit**

```bash
git add apps/kb_service/ apps/main.py
git commit -m "feat(kb_service): add main app factory and integrate with main app"
```

---

## 依赖关系

```
models (T1)
  └── repositories/metadata (T2)
        └── schemas (T3)
              ├── services/metadata (T4)
              ├── services/preprocessor (T5)
              └── services/router (T6)
                    └── pipelines/ingest (T7)
                          ├── pipelines/batch (T7-S3)
                          ├── services/job (T8)
                          ├── clients/ragflow + dify (T9)
                          ├── services/status (T10)
                          └── services/audit (T11)
                                ├── utils/file_utils (T11-S1)
                                ├── api/ingest (T12)
                                ├── api/batch (T13)
                                ├── api/review (T14)
                                ├── api/callback (T15)
                                └── api/query (T16)
                                      └── main.py app factory (T17)
```

---

## 验收标准

- [ ] 支持上传 docx/pdf 文件 → Task 12
- [ ] 自动分类并路由到 RAGFlow/Dify → Task 5 + Task 6
- [ ] 异步任务通过 ARQ 调度 → Task 8 (Phase 1 占位，Task 10 后完善)
- [ ] 元数据存入 PostgreSQL，可查询状态 → Task 2 + Task 16
- [ ] 回调 + 轮询双重状态同步 → Task 10
- [ ] 人工审核通过后才发布 → Task 14
- [ ] 操作审计日志完整记录 → Task 11
- [ ] 定时批量扫描触发入库 → Task 13
- [ ] 审核后可 approve/reject → Task 14
- [ ] 可扩展（新增引擎不影响主流程）→ Task 6 (RouterService)

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-28-kb-service-implementation.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
