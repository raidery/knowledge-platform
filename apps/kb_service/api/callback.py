from fastapi import APIRouter
from pydantic import BaseModel

from apps.kb_service.services.status import StatusTracker

router = APIRouter()
tracker = StatusTracker()


class CallbackPayload(BaseModel):
    status: str  # "success" | "failed"
    message: str | None = None
    result: dict | None = None


@router.post("/callback/{job_id}")
async def receive_callback(job_id: str, payload: CallbackPayload):
    await tracker.handle_callback(job_id, payload.status, payload.message)
    return {"received": True}