# KB Service /ingest 队列化设计

**日期**: 2026-04-29
**状态**: Approved
**范围**: 单文件 ingest API 队列化

---

## 1. 概述

在 `/ingest` API 中添加文件大小判断逻辑：
- 文件 ≤ 1MB：同步处理（现有逻辑）
- 文件 > 1MB：enqueue 到 Redis 队列异步处理，立即返回 `job_id` + `status: queued`

**目标**：先跑通流程，后续再添加更复杂的切分逻辑。

---

## 2. 修改文件

| 文件 | 改动 |
|------|------|
| `apps/kb_service/api/ingest.py` | 添加队列分支逻辑 |
| `apps/kb_service/workers/tasks.py` | 确认 `process_ingest_task` 可用 |

---

## 3. 数据流

### 同步路径（≤ 1MB）

```
POST /ingest (file ≤ 1MB)
  → save_upload_file()
  → SplitDocxService.split() [docx]
  → IngestPipeline.run() [直接调用]
  → return IngestResponse(status="completed")
```

### 异步路径（> 1MB）

```
POST /ingest (file > 1MB)
  → save_upload_file()
  → SplitDocxService.split() [docx]
  → queue_manager.enqueue_task(process_ingest_task, ..., queue_name="ingest")
  → return IngestResponse(job_id=<rq_job_id>, status="queued")

Worker (异步):
  → process_ingest_task(...)
  → IngestPipeline.run()
  → 更新 IngestJob status="completed"
```

---

## 4. API 层改动

### `apps/kb_service/api/ingest.py`

在 `ingest_document` 函数中添加文件大小判断：

```python
import os

QUEUE_SIZE_THRESHOLD = get_queue_size_threshold()  # 1MB

@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(...):
    # 1. 保存上传文件
    upload_dir = os.environ.get("UPLOAD_DIR", "/tmp/kb_uploads")
    file_path = save_upload_file(await file.read(), file.filename, upload_dir)

    # 2. 获取文件大小
    file_size = os.path.getsize(file_path)

    # 3. DOCX 切分判定（提前执行）
    with SplitDocxService() as split_svc:
        sections = []
        if file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            sections = split_svc.split(...)

        # 4. 根据文件大小判断是否走队列
        if file_size > QUEUE_SIZE_THRESHOLD and not sections:
            # 异步队列处理
            job = queue_manager.enqueue_task(
                process_ingest_task,
                file_path=file_path,
                business_id=business_id,
                callback_url=callback_url,
                enable_split=enable_split,
                pages_per_chunk=pages_per_chunk,
                max_chunks=max_chunks,
                split_level=split_level,
                split_pattern=split_pattern,
                force_split=force_split,
                queue_name="ingest"
            )
            return IngestResponse(
                job_id=job.id,
                doc_id="",
                status="queued",
                created_at=str(job.created_at),
                sections_count=None,
                sections=None,
            )

        # 5. 小文件或已有 sections：同步处理
        pipeline = IngestPipeline()
        ...
```

**注意**：
- `sections` 非空时（DOCX 已切分），不走队列，遍历每个 section 调用 `pipeline.run()`
- 这与 `batch.py` 的逻辑保持一致

---

## 5. Worker 层

### `apps/kb_service/workers/tasks.py`

`process_ingest_task` 已存在，签名：

```python
async def process_ingest_task(
    file_path: str,
    business_id: str,
    callback_url: str = None,
    enable_split: bool = False,
    pages_per_chunk: int = 50,
    max_chunks: int = 100,
    split_level: int = None,
    split_pattern: str = None,
    force_split: bool = False,
) -> Dict[str, Any]:
```

worker 内部会：
1. 调用 `IngestPipeline.run()` 执行处理
2. 创建/更新 `IngestJob` 记录
3. 设置 `status="completed"` 或 `status="failed"`

---

## 6. 队列配置

- **队列名称**: `ingest`
- **阈值**: 1MB（与 `batch.py` 保持一致，通过 `get_queue_size_threshold()` 获取）
- **Worker 启动**: `rq worker ingest` 已包含在 `start_rq_dashboard.sh` 中

---

## 7. 错误处理

| 场景 | 处理 |
|------|------|
| enqueue 失败 | 返回 500 + 错误信息 |
| worker 处理失败 | IngestJob status 设为 `failed` |
| 队列任务超时 | RQ 默认超时处理 |

---

## 8. 测试验证

1. 上传 < 1MB 文件 → 同步处理，立即返回 `status: completed`
2. 上传 > 1MB 文件 → 立即返回 `status: queued`
3. 队列监控 `GET /monitor/queues` 显示 `ingest` 队列有任务
4. worker 处理完成后 job 状态更新为 `completed`

---

## 9. 后续扩展（不在本次范围）

- `GET /monitor/jobs/{job_id}` 查询单个任务状态
- 更复杂的切分策略（按 5MB/20MB 分级）
- Callback 回调机制实现
- 切分场景（sections 非空）也走队列

