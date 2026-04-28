from pydantic import BaseModel
from typing import Optional


class ReviewRequest(BaseModel):
    action: str  # "approve" | "reject"
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    job_id: str
    status: str
    reviewed_by: str
    reviewed_at: str