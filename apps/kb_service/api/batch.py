import os
import uuid
from fastapi import APIRouter, Body

from apps.kb_service.core.queue import QueueManager
from apps.kb_service.core.utils import get_queue_size_threshold
from apps.kb_service.workers.tasks import process_batch_ingest_task
from apps.kb_service.pipelines.ingest import IngestPipeline

router = APIRouter()

# 初始化队列管理器
queue_manager = QueueManager()

# 从环境变量读取文件大小阈值，默认为 1MB
QUEUE_SIZE_THRESHOLD = get_queue_size_threshold()  # 1MB


@router.post("/batch/ingest")
async def batch_ingest(
    business_id: str = Body(...),
    directory_path: str = Body(...),
    file_patterns: list[str] = Body(["*.pdf", "*.docx", "*.txt"]),
):
    import glob

    # 计算所有匹配文件的总大小
    files = []
    total_size = 0
    for pattern in file_patterns:
        matched_files = glob.glob(os.path.join(directory_path, pattern))
        files.extend(matched_files)

        # 计算文件大小
        for file_path in matched_files:
            if os.path.exists(file_path):
                total_size += os.path.getsize(file_path)

    # 根据文件总大小决定是否使用队列处理
    use_queue = total_size > QUEUE_SIZE_THRESHOLD

    if use_queue:
        # 将批量任务加入队列异步处理
        job = queue_manager.enqueue_task(
            process_batch_ingest_task,
            business_id,
            directory_path,
            file_patterns,
            queue_name="batch"
        )

        # 返回作业ID而不是直接结果
        return {
            "batch_id": job.id,
            "jobs": [],
            "total": 0,
            "status": "queued",
            "created_at": str(job.created_at)
        }
    else:
        # 同步处理（保持原有行为）
        

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