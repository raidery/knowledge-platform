import uuid
from fastapi import APIRouter, Body

from apps.kb_service.pipelines.ingest import IngestPipeline

router = APIRouter()


@router.post("/batch/ingest")
async def batch_ingest(
    business_id: str = Body(...),
    directory_path: str = Body(...),
    file_patterns: list[str] = Body(["*.pdf", "*.docx", "*.txt"]),
):
    import glob
    import os

    files = []
    for pattern in file_patterns:
        files.extend(glob.glob(os.path.join(directory_path, pattern)))

    pipeline = IngestPipeline()
    jobs = []
    for file_path in files:
        result = await pipeline.run(file_path=file_path, business_id=business_id)
        jobs.append({"file": os.path.basename(file_path), "job_id": result["job_id"]})

    return {
        "batch_id": f"batch_{uuid.uuid4().hex[:16]}",
        "jobs": jobs,
        "total": len(jobs),
    }