from tortoise import fields
from .base import BaseModel, TimestampMixin


class AuditLog(BaseModel, TimestampMixin):
    job_id = fields.CharField(max_length=64, description="关联任务ID", index=True)
    action = fields.CharField(max_length=32, description="操作类型")
    operator = fields.CharField(max_length=64, description="操作人")
    detail = fields.JSONField(null=True, description="详情")

    class Meta:
        table = "kb_audit_log"