from tortoise import fields
from tortoise.models import Model


class TimestampMixin:
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")


class BaseModel(Model):
    id = fields.UUIDField(pk=True)

    class Meta:
        abstract = True