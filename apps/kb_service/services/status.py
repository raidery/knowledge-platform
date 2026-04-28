import asyncio
from apps.kb_service.models.ingest_job import JobStatus
from apps.kb_service.repositories.metadata import MetadataRepository


class StatusTracker:
    def __init__(self):
        self.repo = MetadataRepository()

    async def handle_callback(self, job_id: str, status: str, message: str | None = None):
        """处理外部回调"""
        job = await self.repo.get_ingest_job_by_job_id(job_id)
        if not job:
            return False

        if status == "success":
            await self.repo.update_status(job_id, JobStatus.PENDING_REVIEW.value)
        else:
            await self.repo.update_status(job_id, JobStatus.FAILED.value, error_message=message)
        return True

    async def poll_job_status(self, job_id: str, max_retries: int = 10, interval: int = 30) -> str | None:
        """轮询兜底：每30s查询一次，最多10次"""
        for _ in range(max_retries):
            await asyncio.sleep(interval)
            status = await self._check_external_status(job_id)
            if status in ("success", "failed"):
                await self.handle_callback(job_id, status)
                return status
        return None

    async def _check_external_status(self, job_id: str) -> str:
        # Phase 1: 占位，后续接入客户端查询
        return "pending"