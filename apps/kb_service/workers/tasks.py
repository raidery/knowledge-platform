"""
任务处理器 - 处理队列中的知识库任务
"""
import asyncio
import logging
from typing import Dict, Any

from apps.kb_service.core.queue import QueueManager
from apps.kb_service.pipelines.ingest import IngestPipeline
from apps.kb_service.repositories.metadata import MetadataRepository

logger = logging.getLogger(__name__)


async def process_ingest_task(
    file_path: str,
    business_id: str,
    callback_url: str = None,
    enable_split: bool = False,
    pages_per_chunk: int = 50,
    max_chunks: int = 100,
    split_level: int | None = None,
    split_pattern: str | None = None,
    force_split: bool = False,
) -> Dict[str, Any]:
    """
    处理文档摄入任务

    Args:
        file_path: 文件路径
        business_id: 业务ID
        callback_url: 回调URL
        enable_split: 是否启用分割
        pages_per_chunk: 每块页数
        max_chunks: 最大块数
        split_level: 手动指定切分级别，覆盖自适应（None=自适应）
        split_pattern: 正则模式覆盖默认节标题匹配
        force_split: True则忽略大小阈值强制切分

    Returns:
        处理结果
    """
    logger.info(f"开始处理文档摄入任务: {file_path}")

    try:
        pipeline = IngestPipeline()
        result = await pipeline.run(
            file_path=file_path,
            business_id=business_id,
            callback_url=callback_url,
            enable_split=enable_split,
            pages_per_chunk=pages_per_chunk,
            max_chunks=max_chunks,
            split_level=split_level,
            split_pattern=split_pattern,
            force_split=force_split,
        )

        logger.info(f"文档摄入任务完成: {result['job_id']}")
        return result
    except Exception as e:
        logger.error(f"文档摄入任务失败: {str(e)}")
        raise


async def process_batch_ingest_task(
    business_id: str,
    directory_path: str,
    file_patterns: list[str],
) -> Dict[str, Any]:
    """
    处理批量文档摄入任务

    Args:
        business_id: 业务ID
        directory_path: 目录路径
        file_patterns: 文件模式列表

    Returns:
        处理结果
    """
    logger.info(f"开始处理批量文档摄入任务: {directory_path}")

    try:
        import glob
        import os
        import uuid

        files = []
        for pattern in file_patterns:
            files.extend(glob.glob(os.path.join(directory_path, pattern)))

        pipeline = IngestPipeline()
        jobs = []
        for file_path in files:
            result = await pipeline.run(file_path=file_path, business_id=business_id)
            jobs.append({"file": os.path.basename(file_path), "job_id": result["job_id"]})

        result = {
            "batch_id": f"batch_{uuid.uuid4().hex[:16]}",
            "jobs": jobs,
            "total": len(jobs),
        }

        logger.info(f"批量文档摄入任务完成: {result['batch_id']}")
        return result
    except Exception as e:
        logger.error(f"批量文档摄入任务失败: {str(e)}")
        raise


def start_worker(queues: list = ["default", "ingest", "batch"]):
    """
    启动 RQ Worker

    Args:
        queues: 要监听的队列列表
    """
    import os
    from rq import Worker

    # 设置环境变量以便 worker 能找到 Django 设置
    os.environ.setdefault("PYTHONPATH", ".")

    # 创建队列管理器并获取队列
    queue_manager = QueueManager()
    rq_queues = [queue_manager.get_queue(q) for q in queues]

    # 创建并启动 worker
    worker = Worker(rq_queues, connection=queue_manager.redis_conn)
    worker.work()