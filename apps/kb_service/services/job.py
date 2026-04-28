from apps.kb_service.models.ingest_job import IngestJob, JobStatus
from apps.kb_service.repositories.metadata import MetadataRepository


class JobService:
    def __init__(self):
        self.repo = MetadataRepository()

    async def submit_ingest_job(self, job_id: str, backend: str) -> str:
        # Phase 1: 打印任务信息，实际ARQ调度在 Task 10 后完善
        job = await self.repo.get_ingest_job_by_job_id(job_id)
        if job:
            job.status = JobStatus.PROCESSING.value
            await job.save()
        return job_id

    async def get_job_status(self, job_id: str) -> str | None:
        job = await self.repo.get_ingest_job_by_job_id(job_id)
        return job.status if job else None