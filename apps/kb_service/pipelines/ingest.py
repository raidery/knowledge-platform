import logging
import os

from apps.kb_service.clients.dify import DifyDatasetClient
from apps.kb_service.core.config import kb_settings
from apps.kb_service.models.ingest_job import Backend, IngestJob
from apps.kb_service.repositories.metadata import MetadataRepository
from apps.kb_service.services.metadata import MetadataService
from apps.kb_service.services.preprocessor import DocumentPreprocessor
from apps.kb_service.services.router import RouterService, RouteResult

logger = logging.getLogger(__name__)


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
        split_level: int | None = None,
        split_pattern: str | None = None,
        force_split: bool = False,
        dataset_id: str | None = None,
    ) -> dict:
        # 1. 清洗文档
        cleaned_path = self.preprocessor.clean_document(file_path)

        # 2. 拆分文档（可选）
        if enable_split:
            self.preprocessor.split_document(
                file_path, pages_per_chunk, max_chunks, split_level, split_pattern, force_split
            )

        # 3. 检测文档类型
        doc_type = self.preprocessor.detect_document_type(file_path)

        # 4. 路由引擎
        route_result: RouteResult = self.router.route(doc_type, dataset_id=dataset_id)
        backend = route_result.backend
        resolved_dataset_id = route_result.dataset_id or dataset_id

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
            dataset_id=resolved_dataset_id,
            callback_url=callback_url,
        )

        # 6. 推送到后端
        await self._push_to_backend(job, cleaned_path, backend, resolved_dataset_id)

        return {
            "job_id": job.job_id,
            "doc_id": job.doc_id,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
        }

    async def _push_to_backend(
        self,
        job: IngestJob,
        file_path: str,
        backend: Backend,
        dataset_id: str | None,
    ) -> None:
        """将文档推送到指定后端"""
        if backend == Backend.DIFY and dataset_id:
            result = await self._push_to_dify(job, file_path, dataset_id)
            # 可以在这里处理 Dify 返回的结果
        elif backend == Backend.RAGFLOW:
            # TODO: 实现 RagFlow 上传
            logger.info(f"[RAGFlow] 上传暂未实现，job_id={job.job_id}")

    async def _push_to_dify(self, job: IngestJob, file_path: str, dataset_id: str) -> dict:
        """推送文档到 Dify 知识库"""
        client = DifyDatasetClient(
            api_key=kb_settings.DIFY_API_KEY,
            base_url=kb_settings.DIFY_BASE_URL,
        )
        try:
            logger.info(f"[Dify] 开始上传文档: job_id={job.job_id}, file_path={file_path}, dataset_id={dataset_id}")
            # 测试获取数据集详情
            #dataset_info = await client.get_dataset_detail(dataset_id)
            #logger.info(f"[Dify] 数据集详情: {dataset_info}")

            result = await client.create_document_by_file(
                dataset_id=dataset_id,
                file_path=file_path,
                indexing_technique="high_quality",
            )
            logger.info(f"[Dify] 文档上传成功: job_id={job.job_id}, result={result}")
            return result
        except Exception as e:
            logger.error(f"[Dify] 文档上传失败: job_id={job.job_id}, error={str(e)}")
            raise
        finally:
            await client.close()