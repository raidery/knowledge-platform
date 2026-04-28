# DOCX 节切分集成到 Ingest 服务 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `split_docx_by_section.py` 集成进 KB Service ingest 流程，实现智能自适应切分 + 结构化元数据入库

**Architecture:** 在 `IngestPipeline` 调用前增加 DOCX 节切分逻辑；`SplitDocxService` 封装切分核心；section 元数据通过调用层组装入库；`IngestPipeline` 签名不变

**Tech Stack:** Python 3.11+, FastAPI, Tortoise ORM, lxml, split_docx_by_section.py

---

## 文件结构

```
apps/kb_service/
  services/
    split_docx.py          # 新增：SplitDocxService（封装切分逻辑）
  api/
    ingest.py              # 修改：集成切分 + 改 IngestRequest/Response
  models/
    ingest_job.py          # 修改：新增 parent_job_id / section_title / section_index
  schemas/
    ingest.py              # 修改：IngestRequest 新增 split_level/split_pattern/force_split
                            # IngestResponse 新增 sections_count / sections
  utils/
    split_docx_by_section.py  # 已存在，依赖 lxml
```

---

## 任务分解

---

### Task 1: 修改 IngestJob 模型，新增切分字段

**Files:**
- Modify: `apps/kb_service/models/ingest_job.py:29-46`

- [ ] **Step 1: 添加字段**

在 `IngestJob` 类的 `reviewed_at` 字段后添加：

```python
parent_job_id = fields.CharField(max_length=64, null=True, description="父文档job_id，切分场景下指向原文档")
section_title = fields.CharField(max_length=255, null=True, description="节标题，如'第1节 问题分析'")
section_index = fields.IntField(null=True, description="节序号，0=前言，1+=正文节")
```

- [ ] **Step 2: Commit**

```bash
git add apps/kb_service/models/ingest_job.py
git commit -m "feat(kb_service): add parent_job_id/section_title/section_index to IngestJob"
```

---

### Task 2: 修改 IngestRequest / IngestResponse Schema

**Files:**
- Modify: `apps/kb_service/schemas/ingest.py:1-16`

- [ ] **Step 1: 修改 IngestRequest，添加切分参数**

在 `IngestRequest` 中 `max_chunks` 字段后添加：

```python
split_level: int | None = Field(None, description="手动指定切分级别，覆盖自适应（None=自适应）")
split_pattern: str | None = Field(None, description="正则模式覆盖默认节标题匹配")
force_split: bool = Field(False, description="True则忽略大小阈值强制切分")
```

- [ ] **Step 2: 添加 SectionMeta Pydantic 模型**

在 `IngestResponse` 前添加：

```python
class SectionMeta(BaseModel):
    job_id: str
    title: str
    index: int
```

- [ ] **Step 3: 修改 IngestResponse，新增切分场景字段**

将 `IngestResponse` 替换为：

```python
class IngestResponse(BaseModel):
    job_id: str
    doc_id: str
    status: str
    created_at: str
    sections_count: int | None = Field(None, description="切分出的section数量")
    sections: list[SectionMeta] | None = Field(None, description="切分场景下各section的元数据")
```

- [ ] **Step 4: Commit**

```bash
git add apps/kb_service/schemas/ingest.py
git commit -m "feat(kb_service): add split params to IngestRequest, add sections to IngestResponse"
```

---

### Task 3: 创建 SplitDocxService

**Files:**
- Create: `apps/kb_service/services/split_docx.py`

- [ ] **Step 1: 编写 SplitDocxService**

创建文件 `apps/kb_service/services/split_docx.py`：

```python
"""
SplitDocxService — 封装 split_docx_by_section.py 的核心逻辑
"""
import os
import uuid
import re
import io
import shutil
import zipfile
from pathlib import Path
from dataclasses import dataclass

from apps.kb_service.utils.split_docx_by_section import split_docx


# 5MB / 20MB 阈值（bytes）
SIZE_SMALL = 5 * 1024 * 1024
SIZE_LARGE = 20 * 1024 * 1024

# 默认节标题正则
DEFAULT_PATTERN = r"(第\s*[一二三四五六七八九十百千万0-9]+\s*节|Section\s+\d+)"


@dataclass
class SectionMeta:
    """切分出的单个 section 的元数据"""
    title: str           # 节标题，"_intro" 表示前言
    index: int           # 节序号（0=intro, 1+=正文节）
    file_path: str       # 临时文件路径（调用方清理）
    file_size: int       # bytes


class SplitError(Exception):
    """切分失败异常"""
    pass


class SplitDocxService:
    """DOCX 节切分服务"""

    def __init__(self):
        self._temp_dirs: list[str] = []

    def _get_split_level(self, file_size: int, split_level: int | None) -> int | None:
        """
        根据文件大小返回 split_level。
        - split_level 显式传入 → 直接使用
        - split_level=None → 自适应
        - 返回 None 表示不切分
        """
        if split_level is not None:
            return split_level
        if file_size < SIZE_SMALL:
            return None  # 不切分
        if file_size < SIZE_LARGE:
            return 3
        return 2

    def _get_pattern(self, split_pattern: str | None) -> str | None:
        return split_pattern if split_pattern else DEFAULT_PATTERN

    def _ensure_temp_dir(self) -> str:
        """创建隔离的临时目录"""
        temp_dir = f"/tmp/docx_split_{uuid.uuid4().hex[:8]}"
        os.makedirs(temp_dir, exist_ok=True)
        self._temp_dirs.append(temp_dir)
        return temp_dir

    def _write_section_bytes(self, data: bytes, temp_dir: str, index: int, title: str) -> str:
        """将 section bytes 写入临时文件，返回文件路径"""
        safe = re.sub(r'[\\/:*?"<>|]', "_", title)[:60]
        filename = f"section_{index:02d}_{safe}.docx"
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, "wb") as f:
            f.write(data)
        return file_path

    def split(
        self,
        file_path: str,
        split_level: int | None = None,
        split_pattern: str | None = None,
        force_split: bool = False,
    ) -> list[SectionMeta]:
        """
        切分 DOCX，返回 section 元数据列表。

        Args:
            file_path: 原始 DOCX 文件路径
            split_level: 手动指定切分级别（None=自适应）
            split_pattern: 正则模式覆盖默认匹配
            force_split: True 则忽略大小阈值强制切分

        Returns:
            list[SectionMeta]: 各 section 的元数据列表

        Raises:
            SplitError: 切分失败
        """
        file_size = os.path.getsize(file_path)
        level = self._get_split_level(file_size, split_level)
        pattern = self._get_pattern(split_pattern)

        # 不切分的场景
        if level is None and not force_split:
            return []

        # 实际执行切分
        try:
            # 调用原 split_docx，将结果写入临时目录
            out_dir = self._ensure_temp_dir()
            split_docx(
                input_path=file_path,
                out_dir=out_dir,
                heading_level=level or 3,
                pattern_str=pattern,
                keep_intro=True,
                disable_fonts=True,
            )
        except Exception as e:
            self.cleanup()
            raise SplitError(f"切分失败: {e}") from e

        # 解析临时目录中的输出文件，构建 SectionMeta 列表
        sections: list[SectionMeta] = []
        temp_dir_path = Path(out_dir)
        for f in sorted(temp_dir_path.glob("*.docx")):
            name = f.stem  # e.g. "原文件_intro" / "原文件_01_第1节"
            data = f.read_bytes()

            # 解析 index 和 title
            # 格式: {stem}_intro.docx 或 {stem}_{index:02d}_{title}.docx
            if "_intro" in name:
                title = "_intro"
                index = 0
            else:
                # 找到最后一个 _ 分隔的位置，提取 index 和 title
                parts = name.split("_")
                # 最后一段是 index（两位数字），倒数第二段是 title
                # 但 title 本身可能含有下划线，所以用 rsplit 取最后两部分
                index_part = parts[-1]
                title_part = "_".join(parts[2:])  # 跳过 原文件名(index)
                try:
                    index = int(index_part)
                except ValueError:
                    index = 0
                title = title_part

            sections.append(SectionMeta(
                title=title,
                index=index,
                file_path=str(f),
                file_size=len(data),
            ))

        return sections

    def cleanup(self):
        """清理所有临时目录"""
        for temp_dir in self._temp_dirs:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        self._temp_dirs.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False
```

- [ ] **Step 2: Commit**

```bash
git add apps/kb_service/services/split_docx.py
git commit -m "feat(kb_service): add SplitDocxService for DOCX section splitting"
```

---

### Task 4: 修改 ingest API，集成切分逻辑

**Files:**
- Modify: `apps/kb_service/api/ingest.py:1-77`

- [ ] **Step 1: 重写 ingest_document 函数**

将整个 `ingest_document` 函数替换为：

```python
from apps.kb_service.services.split_docx import SplitDocxService, SplitError, SectionMeta

@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    business_id: str = Body(...),
    file: UploadFile = File(...),
    callback_url: str | None = Body(None),
    enable_split: bool = Body(False),
    pages_per_chunk: int = Body(50),
    max_chunks: int = Body(100),
    split_level: int | None = Body(None),
    split_pattern: str | None = Body(None),
    force_split: bool = Body(False),
):
    """
    文档写入知识库。

    - 小文件（< 5MB）不切分，直接走原 pipeline
    - 中等文件（5-20MB）按 level 3 切分
    - 大文件（> 20MB）按 level 2 切分
    - split_level / split_pattern 可覆盖默认行为
    - force_split=True 则忽略大小阈值强制切分
    """
    # 1. 保存上传文件
    upload_dir = os.environ.get("UPLOAD_DIR", "/tmp/kb_uploads")
    file_path = save_upload_file(await file.read(), file.filename, upload_dir)

    with SplitDocxService() as split_svc:
        # 2. 判定是否切分
        sections: list[SectionMeta] = []
        if file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            sections = split_svc.split(
                file_path=file_path,
                split_level=split_level,
                split_pattern=split_pattern,
                force_split=force_split,
            )

        pipeline = IngestPipeline()

        if not sections:
            # 不切分场景：原流程
            result = await pipeline.run(
                file_path=file_path,
                business_id=business_id,
                callback_url=callback_url,
                enable_split=enable_split,
                pages_per_chunk=pages_per_chunk,
                max_chunks=max_chunks,
            )
            return IngestResponse(
                job_id=result["job_id"],
                doc_id=result["doc_id"],
                status=result["status"],
                created_at=result["created_at"],
                sections_count=None,
                sections=None,
            )

        # 3. 切分场景：遍历各 section
        section_jobs: list[dict] = []
        parent_job_id = None

        for sec in sections:
            try:
                result = await pipeline.run(
                    file_path=sec.file_path,
                    business_id=business_id,
                    callback_url=callback_url,
                    enable_split=enable_split,
                    pages_per_chunk=pages_per_chunk,
                    max_chunks=max_chunks,
                )
                # 记录 parent_job_id / section_title / section_index 到 DB
                await update_section_metadata(
                    job_id=result["job_id"],
                    parent_job_id=parent_job_id,
                    section_title=sec.title,
                    section_index=sec.index,
                )
                section_jobs.append({
                    "job_id": result["job_id"],
                    "title": sec.title,
                    "index": sec.index,
                })
                # 第一个 section 的 job_id 作为父 job
                if parent_job_id is None:
                    parent_job_id = result["job_id"]
            except Exception as e:
                raise SplitError(f"处理节 '{sec.title}' 时失败: {e}") from e

    return IngestResponse(
        job_id=parent_job_id,
        doc_id=section_jobs[0]["job_id"] if section_jobs else "",
        status="completed",
        created_at=section_jobs[0]["job_id"] if section_jobs else "",
        sections_count=len(section_jobs),
        sections=[SectionMetaResponse(**s) for s in section_jobs],
    )
```

- [ ] **Step 2: 添加 save_upload_file 导入和辅助函数**

在 `ingest.py` 顶部 import 区域添加：

```python
from apps.kb_service.utils.file_utils import save_upload_file
from apps.kb_service.schemas.ingest import SectionMetaResponse
```

并添加 helper 函数（在 router 之前）：

```python
async def update_section_metadata(
    job_id: str,
    parent_job_id: str,
    section_title: str,
    section_index: int,
):
    """将 section 元数据写入 IngestJob 表"""
    from apps.kb_service.models.ingest_job import IngestJob
    job = await IngestJob.get(job_id=job_id)
    job.parent_job_id = parent_job_id
    job.section_title = section_title
    job.section_index = section_index
    await job.save()
```

- [ ] **Step 3: Commit**

```bash
git add apps/kb_service/api/ingest.py
git commit -m "feat(kb_service): integrate DOCX split into ingest API"
```

---

### Task 5: 处理错误处理和回滚逻辑

**Files:**
- Modify: `apps/kb_service/api/ingest.py`（在 Task 4 基础上补充）

- [ ] **Step 1: 添加 SplitError 异常处理**

在 `ingest_document` 函数中，在 `except Exception as e` 处加入回滚逻辑：

```python
except SplitError as e:
    # 整体回滚：已入库的 section job 保留（便于追查），temp 文件由 SplitDocxService.cleanup() 处理
    raise HTTPException(status_code=500, detail=str(e))
```

并添加 `from fastapi import HTTPException` 导入。

- [ ] **Step 2: Commit**

```bash
git add apps/kb_service/api/ingest.py
git commit -m "fix(kb_service): add rollback on split failure in ingest API"
```

---

### Task 6: 验证切分元数据入库

**Files:**
- Create: `tests/kb_service_test_split_docx.py`

- [ ] **Step 1: 编写测试**

```python
import pytest
from apps.kb_service.services.split_docx import SplitDocxService, SectionMeta

class TestSplitDocxService:
    """SplitDocxService 单元测试"""

    def test_get_split_level_small_file(self):
        svc = SplitDocxService()
        assert svc._get_split_level(1 * 1024 * 1024, None) is None  # <5MB 不切
        assert svc._get_split_level(1 * 1024 * 1024, 2) == 2        # 强制指定

    def test_get_split_level_medium_file(self):
        svc = SplitDocxService()
        assert svc._get_split_level(10 * 1024 * 1024, None) == 3    # 5-20MB

    def test_get_split_level_large_file(self):
        svc = SplitDocxService()
        assert svc._get_split_level(30 * 1024 * 1024, None) == 2    # >20MB

    def test_get_pattern_default(self):
        svc = SplitDocxService()
        assert svc._get_pattern(None) == r"(第\s*[一二三四五六七八九十百千万0-9]+\s*节|Section\s+\d+)"

    def test_get_pattern_custom(self):
        svc = SplitDocxService()
        assert svc._get_pattern(r"Part\s+\d+") == r"Part\s+\d+"

    def test_cleanup(self):
        svc = SplitDocxService()
        temp_dir = svc._ensure_temp_dir()
        assert os.path.exists(temp_dir)
        svc.cleanup()
        assert not os.path.exists(temp_dir)

    def test_context_manager(self):
        with SplitDocxService() as svc:
            temp_dir = svc._ensure_temp_dir()
        # exit 自动 cleanup
        assert not os.path.exists(temp_dir)
```

- [ ] **Step 2: 运行测试验证**

```bash
pytest tests/kb_service_test_split_docx.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/kb_service_test_split_docx.py
git commit -m "test(kb_service): add SplitDocxService unit tests"
```

---

## 依赖检查

实施前确认：
1. `lxml` 已安装：`pip install lxml`（split_docx_by_section.py 依赖）
2. `apps/kb_service/utils/` 在 Python path 中（正常情况是的）
3. 数据库迁移：`IngestJob` 新增字段需要执行 `aerich upgrade` 或手动 ALTER TABLE

---

## 执行顺序

1. Task 1 → 修改模型
2. Task 2 → 修改 Schema
3. Task 3 → 创建 SplitDocxService
4. Task 4 → 修改 ingest API
5. Task 5 → 完善错误处理
6. Task 6 → 单元测试