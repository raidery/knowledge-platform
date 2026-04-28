from enum import Enum

from tortoise import fields

from .base import BaseModel, TimestampMixin


class DocumentType(str, Enum):
    PLAIN_TEXT = "plain_text"
    COMPLEX_LAYOUT = "complex_layout"
    SCANNED_PDF = "scanned_pdf"
    TABLE_HEAVY = "table_heavy"
    IMAGE_RICH = "image_rich"


class Backend(str, Enum):
    RAGFLOW = "ragflow"
    DIFY = "dify"


class JobStatus(str, Enum):
    PROCESSING = "processing"
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    REJECTED = "rejected"
    FAILED = "failed"


class IngestJob(BaseModel, TimestampMixin):
    job_id = fields.CharField(max_length=64, unique=True, description="业务任务ID", index=True)
    trace_id = fields.CharField(max_length=64, description="追踪ID", index=True)
    doc_id = fields.CharField(max_length=64, description="文档唯一标识", index=True)
    business_id = fields.CharField(max_length=64, description="业务线ID", index=True)
    doc_type = fields.CharField(max_length=32, description="文档类型")
    backend = fields.CharField(max_length=16, description="目标引擎")
    status = fields.CharField(max_length=32, description="状态", index=True)
    file_path = fields.CharField(max_length=512, description="文件存储路径")
    file_name = fields.CharField(max_length=256, description="原始文件名")
    file_size = fields.IntField(description="文件大小")
    kb_version = fields.CharField(max_length=32, null=True, description="知识库版本")
    release_id = fields.CharField(max_length=64, null=True, description="发布记录ID")
    callback_url = fields.CharField(max_length=512, null=True, description="回调地址")
    error_message = fields.TextField(null=True, description="失败原因")
    reviewed_by = fields.CharField(max_length=64, null=True, description="审核人")
    reviewed_at = fields.DatetimeField(null=True, description="审核时间")

    class Meta:
        table = "kb_ingest_job"