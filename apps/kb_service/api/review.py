from datetime import datetime
from fastapi import APIRouter, HTTPException

from apps.kb_service.models.ingest_job import JobStatus
from apps.kb_service.repositories.metadata import MetadataRepository
from apps.kb_service.schemas.review import ReviewRequest, ReviewResponse
from apps.kb_service.services.audit import AuditService

router = APIRouter()
repo = MetadataRepository()
audit = AuditService()


@router.post("/jobs/{job_id}/review", response_model=ReviewResponse)
async def review_job(job_id: str, request: ReviewRequest, operator: str = "admin"):
    job = await repo.get_ingest_job_by_job_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if request.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Invalid action")

    new_status = JobStatus.PUBLISHED.value if request.action == "approve" else JobStatus.REJECTED.value

    await repo.update_status(
        job_id,
        new_status,
        reviewed_by=operator,
        reviewed_at=datetime.now(),
    )

    await audit.log(job_id, f"review_{request.action}", operator, {"comment": request.comment})

    updated_job = await repo.get_ingest_job_by_job_id(job_id)
    return ReviewResponse(
        job_id=job_id,
        status=new_status,
        reviewed_by=operator,
        reviewed_at=updated_job.reviewed_at.isoformat() if updated_job.reviewed_at else "",
    )