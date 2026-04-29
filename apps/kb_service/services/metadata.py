# apps/kb_service/services/metadata.py
import uuid
from apps.kb_service.models.ingest_job import Backend, DocumentType, IngestJob, JobStatus
from apps.kb_service.repositories.metadata import MetadataRepository


class MetadataService:
    def __init__(self):
        self.repo = MetadataRepository()

    def generate_doc_id(self) -> str:
        return f"doc_{uuid.uuid4().hex[:16]}"

    def generate_trace_id(self) -> str:
        return f"trace_{uuid.uuid4().hex[:16]}"

    async def build_ingest_job(
        self,
        file_path: str,
        file_name: str,
        file_size: int,
        business_id: str,
        doc_type: DocumentType,
        backend: Backend,
        dataset_id: str | None = None,
        callback_url: str | None = None,
    ) -> IngestJob:
        job_data = {
            "job_id": f"job_{uuid.uuid4().hex[:16]}",
            "trace_id": self.generate_trace_id(),
            "doc_id": self.generate_doc_id(),
            "business_id": business_id,
            "doc_type": doc_type.value,
            "backend": backend.value,
            "status": JobStatus.PROCESSING.value,
            "file_path": file_path,
            "file_name": file_name,
            "file_size": file_size,
            "callback_url": callback_url,
            "dataset_id": dataset_id,
        }
        return await self.repo.create_ingest_job(**job_data)
