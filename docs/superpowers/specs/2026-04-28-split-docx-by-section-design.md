# DOCX 节切分集成到 Ingest 服务 — 设计规格

**日期:** 2026-04-28
**状态:** 已批准
**关联文件:** `apps/kb_service/utils/split_docx_by_section.py`, `apps/kb_service/api/ingest.py`, `apps/kb_service/pipelines/ingest.py`

---

## 1. 背景与目标

当前 `IngestPipeline` 对 DOCX 文件是整体处理，没有按节拆分的概念。
本设计将 `split_docx_by_section.py` 集成进 KB Service ingest 流程，实现：

1. **智能自适应切分** — 小文件（< 5MB）不切，中等文件（5-20MB）按 level 3 切，大文件（> 20MB）按 level 2 切
2. **用户可覆盖** — 通过参数 `split_level` / `split_pattern` 手动指定切分策略
3. **结构化元数据** — 每个 section 的元数据（title、index、file_path）写入数据库，支持血缘追溯
4. **完全兼容** — `IngestPipeline` 签名不变，所有 section 复用同一套 pipeline 逻辑

---

## 2. 决策汇总

| 决策点 | 选择 |
|--------|------|
| 混合模式 | 智能自适应 + 用户可覆盖（默认 <5MB 不切，5-20MB → level 3，>20MB → level 2） |
| 文件处理 | B：写入临时目录 + 结构化元数据返回 |
| 元数据存储 | B：入库 `ingest_job` 表，字段 `parent_job_id / section_title / section_index` |
| 失败策略 | B：整体回滚，失败即停，temp 文件清理 |
| 用户覆盖 | 支持 `split_level` / `split_pattern` 参数覆盖默认行为 |

---

## 3. 架构图

```
POST /ingest (upload DOCX)
        │
        ▼
  FileUtils.save_upload_file() → temp path
        │
        ▼
   文件大小判定
        │
   ┌─────┼─────┐
   │     │     │
 <5MB 5-20MB  >20MB
   │     │     │
  不切  level3  level2
   │     │     │
   ▼     └─────┘
 IngestPipeline.run()  ← 原流程，不切分
        │
        └─► 切分场景:
              split_docx_by_section.py 返回 list[SectionMeta]
                    │
                    ▼
              遍历 sections:
                1. write section bytes → temp file
                2. IngestPipeline.run(file_path=section_temp)
                3. 记录 parent_job_id + section_title + section_index → DB
                4. 清理 section temp 文件
                    │
                    ▼
              return {sections: [{job_id, title, index}, ...]}
```

---

## 4. 数据模型变更

### IngestJob 表新增字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `parent_job_id` | `VARCHAR(64) / NULL` | 父文档 job_id，切分场景下指向原文档 |
| `section_title` | `VARCHAR(255) / NULL` | 节标题，如"第1节 问题分析" |
| `section_index` | `INT / NULL` | 节序号（从 1 开始），0 表示前言（_intro） |

> 父文档 job 的 `parent_job_id / section_title / section_index` 均为 NULL。

---

## 5. 核心接口设计

### 5.1 SplitDocxService（新增）

**文件位置:** `apps/kb_service/services/split_docx.py`

```python
from dataclasses import dataclass

@dataclass
class SectionMeta:
    title: str          # 节标题，"_intro" 表示前言
    index: int          # 节序号（0=intro, 1+=正文节）
    file_path: str      # 临时文件路径（调用方清理）
    file_size: int      # bytes

class SplitDocxService:
    def split(
        self,
        file_path: str,
        split_level: int | None = None,   # None = 自适应
        split_pattern: str | None = None, # None = 默认模式
    ) -> list[SectionMeta]:
        """
        切分 DOCX，返回 section 元数据列表。
        失败时 raise SplitError，已生成的 temp 文件自动清理。
        """
```

**自适应规则：**

| 文件大小 | split_level | 说明 |
|----------|-------------|------|
| < 5MB | `None`（不切分） | 视为小文件，直接走原 pipeline |
| 5MB ~ 20MB | `3` | 标题 3 级别，节数量适中 |
| > 20MB | `2` | 标题 2 级别，节数量更少，避免过多小节 |

### 5.2 IngestPipeline 变更（最小改动）

`IngestPipeline.run()` 签名**不变**，内部逻辑**不变**。
section 元数据的组装和入库由调用层负责，不侵入 pipeline 内部。

### 5.3 API 参数（ingest endpoint）

**POST /ingest** 新增参数：

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `split_level` | `int \| None` | `None` | 手动指定切分级别，覆盖自适应 |
| `split_pattern` | `str \| None` | `None` | 正则模式，覆盖默认节标题匹配 |
| `force_split` | `bool` | `False` | `True` 则忽略大小阈值，强制切分（用于 < 5MB 但仍想切分的场景） |

**响应结构（切分场景）：**

```json
{
  "job_id": "abc123",
  "doc_id": "doc_xxx",
  "status": "completed",
  "sections_count": 5,
  "sections": [
    {"job_id": "sec_001", "title": "第1节 问题分析", "index": 1},
    {"job_id": "sec_002", "title": "第2节 方案设计", "index": 2},
    {"job_id": "sec_003", "title": "第3节 实现细节", "index": 3}
  ]
}
```

---

## 6. 流程描述（切分场景）

1. **文件上传** → `FileUtils.save_upload_file()` → 临时路径
2. **判定** → 查文件大小，走自适应规则（`force_split=True` 则跳过阈值判定）
3. **切分** → `SplitDocxService.split(file_path, level, pattern)` → `list[SectionMeta]`
4. **遍历每个 section：**
   - 写 bytes 到 temp 文件 → `section.file_path`
   - 调用 `IngestPipeline.run(file_path=section.file_path, business_id=...)`
   - section job 的 `parent_job_id / section_title / section_index` 写入 DB
   - 清理 section temp 文件
5. **返回** → 父 job 响应 + sections 列表

**失败处理：**
- 切分或任何 section 处理失败 → 立即停止
- 已生成的 section temp 文件全部清理
- 父 job 标记为 `failed`，已入库的 section job 保留（便于追查）
- 返回错误信息，指明哪一节失败

---

## 7. 目录结构变更

```
apps/kb_service/
  services/
    split_docx.py        # 新增：SplitDocxService
  api/
    ingest.py            # 修改：集成切分逻辑
  pipelines/
    ingest.py            # 不变（签名不变）
```

---

## 8. 测试验证点

1. **小文件（< 5MB）** → 不切分，原 pipeline 处理
2. **中等文件（5-20MB）** → 按 level 3 切，多 section，各走独立 pipeline
3. **大文件（> 20MB）** → 按 level 2 切，section 数量明显少于 level 3
4. **强制切分（force_split=True on small file）** → 仍触发切分流程
5. **用户指定 level** → 覆盖自适应，精确按指定级别切
6. **用户指定 pattern** → 正则匹配标题，切分点由 pattern 决定
7. **corrupt docx** → 整体回滚，temp 文件清理，返回具体错误
8. **section 元数据** → parent_job_id / section_title / section_index 正确写入

---

## 9. 风险与约束

- `split_docx_by_section.py` 依赖 `lxml`，需确保 `apps/kb_service/utils/` 已在 Python path 中
- temp 文件清理：使用 try/finally 确保即使中间步骤崩溃也能清理
- 并发安全：多个大文件同时切分时，temp 目录隔离（uuid 前缀区分）