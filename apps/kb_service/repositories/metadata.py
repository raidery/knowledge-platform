from typing import Optional

from apps.kb_service.models.ingest_job import IngestJob


class MetadataRepository:
    async def create_ingest_job(self, **kwargs) -> IngestJob:
        return await IngestJob.create(**kwargs)

    async def get_ingest_job_by_job_id(self, job_id: str) -> Optional[IngestJob]:
        return await IngestJob.filter(job_id=job_id).first()

    async def update_status(
        self, job_id: str, status: str, error_message: Optional[str] = None, **kwargs
    ) -> Optional[IngestJob]:
        job = await self.get_ingest_job_by_job_id(job_id)
        if not job:
            return None
        job.status = status
        if error_message:
            job.error_message = error_message
        for k, v in kwargs.items():
            setattr(job, k, v)
        await job.save()
        return job

    async def list_jobs_by_business(
        self, business_id: str, status: Optional[str] = None, limit: int = 100
    ):
        q = IngestJob.filter(business_id=business_id)
        if status:
            q = q.filter(status=status)
        return await q.limit(limit).order_by("-created_at")