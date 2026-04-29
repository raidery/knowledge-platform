from fastapi import APIRouter, Query

from apps.rbac.schemas.base import Success
from apps.rbac.schemas.dept import DeptCreate, DeptUpdate
from apps.rbac.services.dept_service import dept_service
from apps.rbac.services.permission_service import DependPermission

router = APIRouter(tags=["RBAC"])


@router.get("/list", summary="查看部门列表", dependencies=[DependPermission])
async def list_dept(
    name: str = Query(None, description="部门名称"),
):
    dept_tree = await dept_service.get_dept_tree(name)
    return Success(data=dept_tree)


@router.get("/get", summary="查看部门", dependencies=[DependPermission])
async def get_dept(
    id: int = Query(..., description="部门ID"),
):
    dept_obj = await dept_service.get(id=id)
    data = await dept_obj.to_dict()
    return Success(data=data)


@router.post("/create", summary="创建部门", dependencies=[DependPermission])
async def create_dept(
    dept_in: DeptCreate,
):
    await dept_service.create_dept(obj_in=dept_in)
    return Success(msg="Created Successfully")


@router.post("/update", summary="更新部门", dependencies=[DependPermission])
async def update_dept(
    dept_in: DeptUpdate,
):
    await dept_service.update_dept(obj_in=dept_in)
    return Success(msg="Update Successfully")


@router.delete("/delete", summary="删除部门", dependencies=[DependPermission])
async def delete_dept(
    dept_id: int = Query(..., description="部门ID"),
):
    await dept_service.delete_dept(dept_id=dept_id)
    return Success(msg="Deleted Success")
