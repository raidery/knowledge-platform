from pydantic import BaseModel
from typing import Optional


class JobStatusResponse(BaseModel):
    job_id: str
    doc_id: str
    status: str
    backend: str
    doc_type: str
    created_at: str
    updated_at: str