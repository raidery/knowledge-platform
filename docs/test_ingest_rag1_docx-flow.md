# test_ingest_rag1_docx 全流程分析

## 1. 测试入口

**文件**: `tests/test_queue_functionality.py:38`

```python
test_ingest_rag1_docx()
├── 读取 tests/rag-1.docx
├── POST /api/v1/kb/ingest
│   ├── Content-Type: multipart/form-data
│   ├── file: rag-1.docx
│   └── data: { business_id: "test_rag1_docx" }
└── 断言 status == 'queued'（大文件走队列）
```

---

## 2. API 层

**文件**: `apps/kb_service/api/ingest.py:38`

```
ingest_document()
├── 1. save_upload_file()           # 保存到 /tmp/kb_uploads/
├── 2. 获取文件大小
├── 3. file_size > 1MB?             # 判断是否走队列
│   └── YES → use_queue = True
├── 4. split_docx()                 # 尝试解析 docx 章节
│   └── rag-1.docx → sections (可能有章节)
└── 5. if use_queue:
        queue_manager.enqueue_task(
            process_ingest_task,
            queue_name="ingest"
        )
        → 返回 IngestResponse(status="queued", job_id=<job.id>)
```

---

## 3. 队列任务

**文件**: `apps/kb_service/workers/tasks.py:48`

```
process_ingest_task()  [异步 Worker 消费]
├── _ensure_tortoise_initialized()  # Worker 进程惰性初始化 ORM
├── IngestPipeline()
└── pipeline.run()
```

---

## 4. 核心处理管道

**文件**: `apps/kb_service/pipelines/ingest.py:16`

```
IngestPipeline.run()
├── 1. preprocessor.clean_document()    # 清洗文档
├── 2. preprocessor.split_document()   # 拆分 chunks (enable_split=True 时)
├── 3. preprocessor.detect_document_type()  # 检测文档类型
├── 4. router.route()                   # 路由到后端 (Dify 等)
└── 5. metadata_service.build_ingest_job()   # 构建 IngestJob 写入 DB
    → 返回 { job_id, doc_id, status, created_at }
```

---

## 5. 流程图

```
Client                      API                          Queue (Redis)              Worker
  │                           │                               │                        │
  │─ POST /kb/ingest ────────>│                               │                        │
  │                           │─ 1. 保存文件                    │                        │
  │                           │─ 2. 检测文件大小 > 1MB?         │                        │
  │                           │─ 3. split_docx()              │                        │
  │                           │─ 4. enqueue_task() ──────────>│                        │
  │<─ {status:"queued"} ──────│                               │                        │
  │                           │                               │<─ dequeue ──────────────|
  │                           │                               │                        │
  │                           │                               │  process_ingest_task()  │
  │                           │                               │  ├── clean_document()    │
  │                           │                               │  ├── split_document()   │
  │                           │                               │  ├── detect_type()      │
  │                           │                               │  ├── route()            │
  │                           │                               │  └── build_ingest_job() │
  │                           │                               │                        │
  │                           │                               │  ──> 返回 result        │
```

---

## 关键判定点

| 条件 | 行为 |
|------|------|
| 文件 > `QUEUE_SIZE_THRESHOLD`(1MB) | 入 `ingest` 队列，异步处理 |
| 文件 ≤ `QUEUE_SIZE_THRESHOLD`(1MB) | 同步处理，直接返回结果 |
| docx 有章节 (sections) | 每个 section 单独入队 |
| docx 无章节 | 单个文件入队 |

---

## 涉及的关键文件

| 文件 | 职责 |
|------|------|
| `tests/test_queue_functionality.py` | 测试入口 |
| `apps/kb_service/api/ingest.py` | API 入口，队列分发 |
| `apps/kb_service/core/queue.py` | QueueManager，Redis RQ 封装 |
| `apps/kb_service/workers/tasks.py` | Worker 任务处理器 |
| `apps/kb_service/pipelines/ingest.py` | 核心处理管道 |
