from fastapi import APIRouter, HTTPException

from apps.kb_service.repositories.metadata import MetadataRepository
from apps.kb_service.schemas.job import JobStatusResponse

router = APIRouter()
repo = MetadataRepository()


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    job = await repo.get_ingest_job_by_job_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.job_id,
        doc_id=job.doc_id,
        status=job.status,
        backend=job.backend,
        doc_type=job.doc_type,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
    )