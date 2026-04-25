from tortoise import fields

from .base import BaseModel, TimestampMixin


class Role(BaseModel, TimestampMixin):
    name = fields.CharField(max_length=20, unique=True, description="角色名称", index=True)
    desc = fields.CharField(max_length=500, null=True, description="角色描述")
    menus = fields.ManyToManyField("rbac.Menu", related_name="role_menus")
    apis = fields.ManyToManyField("rbac.Api", related_name="role_apis")

    class Meta:
        table = "role"
