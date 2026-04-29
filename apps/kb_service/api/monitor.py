"""
队列监控 API
"""
from fastapi import APIRouter, Query
from typing import List, Dict, Any

from apps.kb_service.core.queue import QueueManager

router = APIRouter()

# 初始化队列管理器
queue_manager = QueueManager()


class QueueInfoResponse:
    def __init__(self, name: str, length: int, jobs: List[Dict[str, Any]]):
        self.name = name
        self.length = length
        self.jobs = jobs


@router.get("/queues")
async def list_queues() -> Dict[str, Any]:
    """列出所有队列信息"""
    queues_info = {}

    # 默认队列
    queue_names = ["default", "ingest", "batch"]

    for queue_name in queue_names:
        queue = queue_manager.get_queue(queue_name)
        length = len(queue)

        # 获取队列中的作业信息
        jobs_info = []
        for job_id in queue.job_ids:
            try:
                job = queue.fetch_job(job_id)
                if job:
                    jobs_info.append({
                        "id": job.id,
                        "status": job.get_status(),
                        "created_at": str(job.created_at),
                        "enqueued_at": str(job.enqueued_at) if job.enqueued_at else None,
                        "ended_at": str(job.ended_at) if job.ended_at else None,
                        "exc_info": job.exc_info,
                    })
            except Exception as e:
                jobs_info.append({
                    "id": job_id,
                    "error": str(e)
                })

        queues_info[queue_name] = {
            "length": length,
            "jobs": jobs_info
        }

    return queues_info


@router.get("/queues/{queue_name}")
async def get_queue_info(queue_name: str) -> Dict[str, Any]:
    """获取特定队列的信息"""
    queue = queue_manager.get_queue(queue_name)
    length = len(queue)

    # 获取队列中的作业信息
    jobs_info = []
    for job_id in queue.job_ids:
        try:
            job = queue.fetch_job(job_id)
            if job:
                jobs_info.append({
                    "id": job.id,
                    "status": job.get_status(),
                    "created_at": str(job.created_at),
                    "enqueued_at": str(job.enqueued_at) if job.enqueued_at else None,
                    "ended_at": str(job.ended_at) if job.ended_at else None,
                    "exc_info": job.exc_info,
                })
        except Exception as e:
            jobs_info.append({
                "id": job_id,
                "error": str(e)
            })

    return {
        "name": queue_name,
        "length": length,
        "jobs": jobs_info
    }


@router.delete("/queues/{queue_name}")
async def clear_queue(queue_name: str) -> Dict[str, Any]:
    """清空特定队列"""
    queue = queue_manager.get_queue(queue_name)
    job_count = len(queue)
    queue.empty()

    return {
        "message": f"队列 '{queue_name}' 已清空",
        "cleared_jobs": job_count
    }