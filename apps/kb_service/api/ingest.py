import os
import uuid
from fastapi import APIRouter, File, Form, UploadFile

from apps.kb_service.pipelines.ingest import IngestPipeline
from apps.kb_service.schemas.ingest import IngestResponse

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    business_id: str = Form(...),
    callback_url: str | None = Form(None),
    enable_split: bool = Form(False),
    pages_per_chunk: int = Form(50),
    max_chunks: int = Form(100),
):
    # 保存上传文件
    upload_dir = "/tmp/kb_uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{uuid.uuid4().hex}_{file.filename}")

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    pipeline = IngestPipeline()
    result = await pipeline.run(
        file_path=file_path,
        business_id=business_id,
        callback_url=callback_url,
        enable_split=enable_split,
        pages_per_chunk=pages_per_chunk,
        max_chunks=max_chunks,
    )
    return result