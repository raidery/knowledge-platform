from fastapi import APIRouter

from .auth import router as auth_router
from .users import router as users_router
from .roles import router as roles_router
from .menus import router as menus_router
from .apis import router as apis_router
from .depts import router as depts_router
from .auditlog import router as auditlog_router

rbac_router = APIRouter()

rbac_router.include_router(auth_router, prefix="/base")
rbac_router.include_router(users_router, prefix="/user")
rbac_router.include_router(roles_router, prefix="/role")
rbac_router.include_router(menus_router, prefix="/menu")
rbac_router.include_router(apis_router, prefix="/api")
rbac_router.include_router(depts_router, prefix="/dept")
rbac_router.include_router(auditlog_router, prefix="/auditlog")
