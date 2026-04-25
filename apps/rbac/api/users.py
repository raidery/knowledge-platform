import logging

from fastapi import APIRouter, Body, Query
from tortoise.expressions import Q

from apps.rbac.schemas.base import Fail, Success, SuccessExtra
from apps.rbac.schemas.user import UserCreate, UserUpdate
from apps.rbac.services.dept_service import dept_service
from apps.rbac.services.permission_service import DependPermission
from apps.rbac.services.user_service import user_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/list", summary="查看用户列表", dependencies=[DependPermission])
async def list_user(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    username: str = Query("", description="用户名称，用于搜索"),
    email: str = Query("", description="邮箱地址"),
    dept_id: int = Query(None, description="部门ID"),
):
    q = Q()
    if username:
        q &= Q(username__contains=username)
    if email:
        q &= Q(email__contains=email)
    if dept_id is not None:
        q &= Q(dept_id=dept_id)
    total, user_objs = await user_service.list(page=page, page_size=page_size, search=q)
    data = [await obj.to_dict(m2m=True, exclude_fields=["password"]) for obj in user_objs]
    for item in data:
        dept_id = item.pop("dept_id", None)
        item["dept"] = await (await dept_service.get(id=dept_id)).to_dict() if dept_id else {}

    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/get", summary="查看用户", dependencies=[DependPermission])
async def get_user(
    user_id: int = Query(..., description="用户ID"),
):
    user_obj = await user_service.get(id=user_id)
    user_dict = await user_obj.to_dict(exclude_fields=["password"])
    return Success(data=user_dict)


@router.post("/create", summary="创建用户", dependencies=[DependPermission])
async def create_user(
    user_in: UserCreate,
):
    user = await user_service.get_by_email(user_in.email)
    if user:
        return Fail(code=400, msg="The user with this email already exists in the system.")
    new_user = await user_service.create_user(obj_in=user_in)
    await user_service.update_roles(new_user, user_in.role_ids)
    return Success(msg="Created Successfully")


@router.post("/update", summary="更新用户", dependencies=[DependPermission])
async def update_user(
    user_in: UserUpdate,
):
    user = await user_service.update(id=user_in.id, obj_in=user_in)
    await user_service.update_roles(user, user_in.role_ids)
    return Success(msg="Updated Successfully")


@router.delete("/delete", summary="删除用户", dependencies=[DependPermission])
async def delete_user(
    user_id: int = Query(..., description="用户ID"),
):
    await user_service.remove(id=user_id)
    return Success(msg="Deleted Successfully")


@router.post("/reset_password", summary="重置密码", dependencies=[DependPermission])
async def reset_password(user_id: int = Body(..., description="用户ID", embed=True)):
    await user_service.reset_password(user_id)
    return Success(msg="密码已重置为123456")
