from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    business_id: str = Field(..., description="业务线ID")
    callback_url: str | None = Field(None, description="回调地址")
    enable_split: bool = Field(False, description="是否启用拆分")
    pages_per_chunk: int = Field(50, ge=1, le=500, description="每块页数")
    max_chunks: int = Field(100, ge=1, description="最大块数上限")
    split_level: int | None = Field(None, description="手动指定切分级别，覆盖自适应（None=自适应）")
    split_pattern: str | None = Field(None, description="正则模式覆盖默认节标题匹配")
    force_split: bool = Field(False, description="True则忽略大小阈值强制切分")


class SectionMeta(BaseModel):
    job_id: str
    title: str
    index: int


class IngestResponse(BaseModel):
    job_id: str
    doc_id: str
    status: str
    created_at: str
    sections_count: int | None = Field(None, description="切分出的section数量")
    sections: list[SectionMeta] | None = Field(None, description="切分场景下各section的元数据")