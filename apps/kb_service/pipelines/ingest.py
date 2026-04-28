import os
from apps.kb_service.models.ingest_job import Backend, DocumentType, IngestJob, JobStatus
from apps.kb_service.repositories.metadata import MetadataRepository
from apps.kb_service.services.metadata import MetadataService
from apps.kb_service.services.preprocessor import DocumentPreprocessor
from apps.kb_service.services.router import RouterService


class IngestPipeline:
    def __init__(self):
        self.preprocessor = DocumentPreprocessor()
        self.router = RouterService()
        self.metadata_service = MetadataService()
        self.repo = MetadataRepository()

    async def run(
        self,
        file_path: str,
        business_id: str,
        callback_url: str | None = None,
        enable_split: bool = False,
        pages_per_chunk: int = 50,
        max_chunks: int = 100,
    ) -> dict:
        # 1. 清洗文档
        cleaned_path = self.preprocessor.clean_document(file_path)

        # 2. 拆分文档（可选）
        chunks = []
        if enable_split:
            chunks = self.preprocessor.split_document(
                file_path, pages_per_chunk, max_chunks
            )

        # 3. 检测文档类型
        doc_type = self.preprocessor.detect_document_type(file_path)

        # 4. 路由引擎
        backend = self.router.route(doc_type)

        # 5. 构建元数据
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        job: IngestJob = await self.metadata_service.build_ingest_job(
            file_path=cleaned_path,
            file_name=file_name,
            file_size=file_size,
            business_id=business_id,
            doc_type=doc_type,
            backend=backend,
            callback_url=callback_url,
        )

        return {
            "job_id": job.job_id,
            "doc_id": job.doc_id,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
        }