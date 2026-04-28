from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    business_id: str = Field(..., description="业务线ID")
    callback_url: str | None = Field(None, description="回调地址")
    enable_split: bool = Field(False, description="是否启用拆分")
    pages_per_chunk: int = Field(50, ge=1, le=500, description="每块页数")
    max_chunks: int = Field(100, ge=1, description="最大块数上限")


class IngestResponse(BaseModel):
    job_id: str
    doc_id: str
    status: str
    created_at: str