from tortoise import fields
from .base import BaseModel, TimestampMixin


class DocumentChunk(BaseModel, TimestampMixin):
    job_id = fields.CharField(max_length=64, description="关联任务ID", index=True)
    chunk_index = fields.IntField(description="块序号")
    file_path = fields.CharField(max_length=512, description="块文件路径")
    page_start = fields.IntField(description="起始页码")
    page_end = fields.IntField(description="结束页码")
    title = fields.CharField(max_length=256, null=True, description="章节标题")
    word_count = fields.IntField(default=0, description="字数")

    class Meta:
        table = "kb_document_chunk"