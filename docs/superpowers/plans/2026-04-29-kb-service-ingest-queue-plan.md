# KB Service /ingest 队列化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `/ingest` API 添加文件大小判断，>1MB 文件走 Redis 队列异步处理

**Architecture:** 在 `ingest.py` 中添加 `file_size > QUEUE_SIZE_THRESHOLD` 判断，走 `queue_manager.enqueue_task()` 异步分支；≤1MB 保持同步处理

**Tech Stack:** FastAPI, RQ (Redis Queue), Tortoise ORM

---

## 文件映射

| 文件 | 职责 |
|------|------|
| `apps/kb_service/api/ingest.py` | 添加队列分支逻辑 |
| `apps/kb_service/workers/tasks.py` | 确认 `process_ingest_task` 签名正确 |
| `tests/test_queue_functionality.py` | 更新测试用例验证队列逻辑 |

---

## 任务列表

### Task 1: 确认 worker task 签名

**Files:**
- Read: `apps/kb_service/workers/tasks.py`

- [ ] **Step 1: 读取 tasks.py 确认 process_ingest_task 函数签名**

确认参数包含：`file_path`, `business_id`, `callback_url`, `enable_split`, `pages_per_chunk`, `max_chunks`, `split_level`, `split_pattern`, `force_split`

---

### Task 2: 修改 ingest.py 添加队列分支

**Files:**
- Modify: `apps/kb_service/api/ingest.py`

- [ ] **Step 1: 读取当前 ingest.py 完整代码**

- [ ] **Step 2: 在 `file_path = save_upload_file(...)` 后添加文件大小判断逻辑**

在 `with SplitDocxService() as split_svc:` 之前添加：

```python
    # 获取文件大小
    file_size = os.path.getsize(file_path)

    # 判断是否走队列异步处理（>1MB 且无 sections）
    use_queue = file_size > QUEUE_SIZE_THRESHOLD
```

- [ ] **Step 3: 在 `if not sections:` 判断中添加队列分支**

修改第 75 行附近的 `if not sections:` 条件，添加队列分支：

```python
        pipeline = IngestPipeline()

        if not sections and use_queue:
            # 大文件走队列异步处理
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

        # 小文件或已有 sections：同步处理
        if not sections:
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
```

- [ ] **Step 4: 验证修改完整性**

确认 `use_queue` 变量在 `sections` 判断之前定义，且只在 `not sections` 条件下检查 `use_queue`

---

### Task 3: 更新测试用例

**Files:**
- Modify: `tests/test_queue_functionality.py`

- [ ] **Step 1: 读取当前测试文件**

- [ ] **Step 2: 修改 test_ingest_with_queue 函数添加文件大小检查逻辑**

更新测试，使大于 1MB 的文件能触发队列：

```python
def test_ingest_with_queue(file_path, business_id):
    """测试文档摄入接口（自动使用队列）"""
    print(f"\n=== 测试文件摄入: {file_path} ===")

    file_size = os.path.getsize(file_path)
    print(f"  文件大小: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")

    with open(file_path, "rb") as f:
        files = {"file": (file_path, f, "text/plain")}
        data = {"business_id": business_id}

        try:
            response = requests.post(
                f"{BASE_URL}/ingest",
                files=files,
                data=data
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ 文件摄入请求成功")
                print(f"  Job ID: {result.get('job_id')}")
                print(f"  Status: {result.get('status')}")
                print(f"  Created At: {result.get('created_at')}")

                # 验证队列逻辑
                if file_size > 1024 * 1024:  # > 1MB
                    assert result.get('status') == 'queued', f"大文件应返回 queued，实际: {result.get('status')}"
                    print(f"  ✓ 队列逻辑验证通过 (>1MB 走队列)")
                else:
                    assert result.get('status') in ['completed', 'processing'], f"小文件应同步完成，实际: {result.get('status')}"
                    print(f"  ✓ 同步逻辑验证通过 (≤1MB 同步处理)")

                return result.get('job_id')
            else:
                print(f"✗ 文件摄入失败: {response.status_code}")
                print(f"  Response: {response.text}")
                return None

        except Exception as e:
            print(f"✗ 请求异常: {str(e)}")
            return None
```

- [ ] **Step 3: 更新主函数增加更清晰的测试输出**

```python
def main():
    """主测试函数"""
    print("🚀 开始测试 KB Service 队列功能")
    print(f"📍 Base URL: {BASE_URL}")

    # 1. 创建测试文件
    small_file, large_file = create_test_files()

    # 2. 测试小文件摄入（应同步处理）
    small_job_id = test_ingest_with_queue(small_file, "test_business_small")

    # 3. 测试大文件摄入（应使用队列异步处理）
    large_job_id = test_ingest_with_queue(large_file, "test_business_large")

    # 4. 等待一段时间让队列任务处理
    print("\n⏳ 等待队列任务处理...")
    time.sleep(5)

    # 5. 测试队列监控
    test_queue_monitoring()

    # 6. 清理测试文件
    for file_path in [small_file, large_file]:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"✓ 清理测试文件: {file_path}")

    print("\n🎉 队列功能测试完成!")
```

---

### Task 4: 手动验证

**Files:**
- None (manual verification)

- [ ] **Step 1: 启动服务**

```bash
# 终端 1: 启动 FastAPI
cd /Users/raidery/bench/datago/rag/workspace/knowledge-platform
python run.py

# 终端 2: 启动 RQ Worker
./scripts/start_rq_dashboard.sh
```

- [ ] **Step 2: 运行测试**

```bash
cd /Users/raidery/bench/datago/rag/workspace/knowledge-platform
python tests/test_queue_functionality.py
```

- [ ] **Step 3: 验证输出**

预期输出：
```
🚀 开始测试 KB Service 队列功能
📍 Base URL: http://localhost:9999/api/v1/kb
✓ 创建测试文件:
  小文件: test_small.txt (3072 bytes)
  大文件: test_large.txt (1310720 bytes)

=== 测试文件摄入: test_small.txt ===
  文件大小: 3072 bytes (0.00 MB)
✓ 文件摄入请求成功
  Job ID: job_xxx
  Status: completed
  ✓ 同步逻辑验证通过 (≤1MB 同步处理)

=== 测试文件摄入: test_large.txt ===
  文件大小: 1310720 bytes (1.25 MB)
✓ 文件摄入请求成功
  Job ID: job_xxx
  Status: queued
  ✓ 队列逻辑验证通过 (>1MB 走队列)

⏳ 等待队列任务处理...

=== 测试队列监控 ===
✓ 队列监控请求成功
  队列 'default': 0 个任务
  队列 'ingest': 0 个任务 或 1 个任务（取决于处理速度）
  队列 'batch': 0 个任务
```

---

## 执行方式

**Plan complete and saved to `docs/superpowers/plans/2026-04-29-kb-service-ingest-queue-plan.md`**

两个执行选项：

**1. Subagent-Driven (recommended)** - 每次执行一个 task，带检查点

**2. Inline Execution** - 在当前 session 批量执行任务

选择哪个？

