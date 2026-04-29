import os
import uuid
from fastapi import APIRouter, Body, File, UploadFile

from apps.kb_service.core.queue import QueueManager
from apps.kb_service.core.utils import get_queue_size_threshold
from apps.kb_service.schemas.ingest import IngestResponse, SectionMeta as SectionMetaResponse
from apps.kb_service.workers.tasks import process_ingest_task
from apps.kb_service.pipelines.ingest import IngestPipeline
from apps.kb_service.services.split_docx import SplitDocxService, SplitError, SectionMeta
from apps.kb_service.utils.file_utils import save_upload_file

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
    from apps.kb_service.models.ingest_job import IngestJob
    job = await IngestJob.get(job_id=job_id)
    job.parent_job_id = parent_job_id
    job.section_title = section_title
    job.section_index = section_index
    await job.save()


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

    # 获取文件大小
    file_size = os.path.getsize(file_path)

    # 判断是否走队列异步处理（>1MB 且无 sections）
    use_queue = file_size > QUEUE_SIZE_THRESHOLD

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
