import os
import uuid
from fastapi import APIRouter, Body, File, UploadFile

from apps.kb_service.core.config import kb_settings
from apps.kb_service.core.queue import QueueManager
from apps.kb_service.core.utils import get_queue_size_threshold
from apps.kb_service.schemas.ingest import IngestResponse, SectionMeta as SectionMetaResponse
from apps.kb_service.workers.tasks import process_ingest_task
from apps.kb_service.pipelines.ingest import IngestPipeline
from apps.kb_service.services.split_docx import SplitDocxService, SplitError, SectionMeta
from apps.kb_service.utils.file_utils import save_upload_file
from apps.kb_service.models.ingest_job import IngestJob

router = APIRouter()

# 初始化队列管理器
queue_manager = QueueManager()

# 从环境变量读取文件大小阈值，默认为 1MB
QUEUE_SIZE_THRESHOLD = get_queue_size_threshold()  # 1MB


async def update_section_metadata(
    job_id: str,
    parent_job_id: str,
    section_title: str,
    section_index: int,
):
    """将 section 元数据写入 IngestJob 表"""

    job = await IngestJob.get(job_id=job_id)
    job.parent_job_id = parent_job_id
    job.section_title = section_title
    job.section_index = section_index
    await job.save()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    business_id: str = Body(..., description="业务 ID，用于关联文档"),
    file: UploadFile = File(..., description="待上传的文档文件"),
    dataset_id: str | None = Body(None, description="Dify 数据集 ID，不传则使用环境变量配置"),
    callback_url: str | None = Body(None, description="处理完成后的回调通知 URL"),
    enable_split: bool = Body(False, description="是否启用文档切分"),
    pages_per_chunk: int = Body(50, description="每个切分块的最大页数，用于控制切分粒度"),
    max_chunks: int = Body(100, description="最大切分块数量上限"),
    split_level: int | None = Body(None, description="切分级别，控制切分深度"),
    split_pattern: str | None = Body(None, description="切分正则表达式，用于识别章节分隔符"),
    force_split: bool = Body(False, description="是否强制切分，忽略文件大小阈值"),
):
    """
    文档写入知识库。

    处理流程：
    - 文件 > 阈值（默认 10MB，可配置）：入队列异步处理
    - 文件 ≤ 阈值：同步处理

    切分逻辑（由调用方控制，非文件大小决定）：
    - enable_split=True 启用切分
    - split_level / split_pattern 可精确控制切分方式
    - force_split=True 则忽略大小阈值强制切分
    """
    # 0. dataset_id 解析：参数优先，否则读 .env
    resolved_dataset_id = dataset_id or kb_settings.DIFY_DATASET_ID or None

    # 1. 保存上传文件
    upload_dir = os.environ.get("UPLOAD_DIR", "/tmp/kb_uploads")
    file_path = save_upload_file(await file.read(), file.filename, upload_dir)

    # 获取文件大小
    file_size = os.path.getsize(file_path)

    # 判断是否走队列异步处理（>1MB）
    use_queue = file_size > QUEUE_SIZE_THRESHOLD

    # 2. 判定是否切分（仅大文件走队列时才切分）
    split_svc = SplitDocxService()
    sections: list[SectionMeta] = []
    if use_queue and file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        sections = split_svc.split(
            file_path=file_path,
            split_level=split_level,
            split_pattern=split_pattern,
            force_split=force_split,
        )

    pipeline = IngestPipeline()

    if use_queue:
        # 大文件走队列异步处理
        if sections:
            # 有章节：每个 section 单独入队
            parent_job_id = None
            for sec in sections:
                job = queue_manager.enqueue_task(
                    process_ingest_task,
                    file_path=sec.file_path,
                    business_id=business_id,
                    dataset_id=resolved_dataset_id,
                    callback_url=callback_url,
                    enable_split=enable_split,
                    pages_per_chunk=pages_per_chunk,
                    max_chunks=max_chunks,
                    split_level=split_level,
                    split_pattern=split_pattern,
                    force_split=force_split,
                    is_split_file=True,
                    section_title=sec.title,
                    section_index=sec.index,
                    queue_name="ingest"
                )
                if parent_job_id is None:
                    parent_job_id = job.id
            return IngestResponse(
                job_id=parent_job_id,
                doc_id="",
                status="queued",
                created_at=str(job.created_at),
                sections_count=len(sections),
                sections=None,
            )
        else:
            # 无章节：单个文件入队
            job = queue_manager.enqueue_task(
                process_ingest_task,
                file_path=file_path,
                business_id=business_id,
                dataset_id=resolved_dataset_id,
                callback_url=callback_url,
                enable_split=enable_split,
                pages_per_chunk=pages_per_chunk,
                max_chunks=max_chunks,
                split_level=split_level,
                split_pattern=split_pattern,
                force_split=force_split,
                is_split_file=False,
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

    # 小文件（≤1MB）：同步处理
    if not sections:
        result = await pipeline.run(
            file_path=file_path,
            business_id=business_id,
            dataset_id=resolved_dataset_id,
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

    # 3. 切分场景：遍历各 section（同步）
    section_jobs: list[dict] = []
    parent_job_id = None

    for sec in sections:
        try:
            result = await pipeline.run(
                file_path=sec.file_path,
                business_id=business_id,
                dataset_id=resolved_dataset_id,
                callback_url=callback_url,
                enable_split=enable_split,
                pages_per_chunk=pages_per_chunk,
                max_chunks=max_chunks,
            )
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
