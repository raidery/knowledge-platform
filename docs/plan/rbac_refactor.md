# RBAC 模块重构计划

## Context

根据 `docs/project_structure.md` 项目结构定义，需要将 `app/` 目录下的 RBAC 相关代码重构到独立 `apps/rbac/` 模块。当前 RBAC 代码混在 `app/` 中，需要拆分为独立模块以支持未来 `apps/kb_service/` 等其他模块的扩展。

**目标结构:**
```
apps/rbac/
├── main.py                 # App factory
├── api/                    # 用户/角色/菜单/API 管理接口
├── services/               # 权限校验逻辑 + 业务逻辑
├── models/                 # User, Role, Menu, Api, Dept, AuditLog
├── schemas/                 # Pydantic models
└── utils/                  # jwt_utils, password
```

---

## Phase 1: 创建目录结构

**创建以下空文件:**
```
apps/rbac/
├── __init__.py
├── main.py                  # placeholder
├── api/
│   ├── __init__.py
│   ├── auth.py              # placeholder
│   ├── users.py             # placeholder
│   ├── roles.py             # placeholder
│   ├── menus.py             # placeholder
│   ├── apis.py              # placeholder
│   ├── depts.py             # placeholder
│   └── auditlog.py          # placeholder
├── services/
│   ├── __init__.py
│   ├── crud_base.py         # placeholder
│   ├── auth_service.py      # placeholder
│   ├── permission_service.py # placeholder
│   ├── user_service.py      # placeholder
│   ├── role_service.py      # placeholder
│   ├── menu_service.py      # placeholder
│   ├── api_service.py       # placeholder
│   └── dept_service.py      # placeholder
├── models/
│   ├── __init__.py
│   ├── base.py              # 从 app/models/base.py 复制
│   ├── enums.py             # 从 app/models/enums.py 复制
│   ├── user.py              # placeholder
│   ├── role.py              # placeholder
│   ├── menu.py              # placeholder
│   ├── api.py               # placeholder
│   ├── dept.py              # placeholder
│   └── auditlog.py          # placeholder
├── schemas/
│   ├── __init__.py
│   ├── base.py              # 从 app/schemas/base.py 复制
│   ├── user.py              # placeholder
│   ├── role.py              # placeholder
│   ├── menu.py              # placeholder
│   ├── api.py               # placeholder
│   ├── dept.py              # placeholder
│   ├── auth.py              # placeholder
│   └── auditlog.py          # placeholder
└── utils/
    ├── __init__.py
    ├── jwt_utils.py          # 从 app/utils/jwt_utils.py 复制
    └── password.py          # 从 app/utils/password.py 复制
```

**验证:**
```bash
find apps/rbac -type f -name "*.py" | head -30
```

---

## Phase 2: 拆分 Models

**源文件:** `app/models/admin.py` → 拆分为 `apps/rbac/models/` 下的多个文件

**关键修改 - ManyToMany 引用必须使用 `"rbac.ModelName"`:**
```python
# apps/rbac/models/user.py
roles = fields.ManyToManyField("rbac.Role", related_name="user_roles")  # NOT "models.Role"

# apps/rbac/models/role.py
menus = fields.ManyToManyField("rbac.Menu", related_name="role_menus")
apis = fields.ManyToManyField("rbac.Api", related_name="role_apis")
```

**新文件:**
- `apps/rbac/models/__init__.py` - 导出所有模型
- `apps/rbac/models/base.py` - 复制自 `app/models/base.py`
- `apps/rbac/models/enums.py` - 复制自 `app/models/enums.py`
- `apps/rbac/models/user.py` - User 模型
- `apps/rbac/models/role.py` - Role 模型
- `apps/rbac/models/menu.py` - Menu 模型
- `apps/rbac/models/api.py` - Api 模型
- `apps/rbac/models/dept.py` - Dept, DeptClosure 模型
- `apps/rbac/models/auditlog.py` - AuditLog 模型

**向后兼容:** 保持 `app/models/__init__.py` 从 `app/models/admin.py` 导入，直到 Phase 8

**验证:**
```python
from apps.rbac.models import User, Role, Menu, Api, Dept, DeptClosure, AuditLog
```

---

## Phase 3: 拆分 Schemas

**源文件:** `app/schemas/*.py` → `apps/rbac/schemas/`

**新文件:**
- `apps/rbac/schemas/__init__.py` - 导出所有 schemas
- `apps/rbac/schemas/base.py` - Success, Fail, SuccessExtra
- `apps/rbac/schemas/user.py` - UserCreate, UserUpdate, UpdatePassword (从 users.py 复制)
- `apps/rbac/schemas/role.py` - RoleCreate, RoleUpdate, RoleUpdateMenusApis (从 roles.py 复制)
- `apps/rbac/schemas/menu.py` - MenuCreate, MenuUpdate, MenuType (从 menus.py 复制)
- `apps/rbac/schemas/api.py` - ApiCreate, ApiUpdate (从 apis.py 复制)
- `apps/rbac/schemas/dept.py` - DeptCreate, DeptUpdate (从 depts.py 复制)
- `apps/rbac/schemas/auth.py` - CredentialsSchema, JWTOut, JWTPayload (从 login.py 复制)
- `apps/rbac/schemas/auditlog.py` - 如需要

**验证:**
```python
from apps.rbac.schemas import UserCreate, RoleCreate, MenuType, Success
```

---

## Phase 4: 创建 Services

**核心:** 将 `app/controllers/` + `app/core/dependency.py` 转换为 `apps/rbac/services/`

**新文件:**
- `apps/rbac/services/crud_base.py` - 复制自 `app/core/crud.py`
- `apps/rbac/services/user_service.py` - UserController → UserService
- `apps/rbac/services/role_service.py` - RoleController → RoleService
- `apps/rbac/services/menu_service.py` - MenuController → MenuService
- `apps/rbac/services/api_service.py` - ApiController → ApiService
- `apps/rbac/services/dept_service.py` - DeptController → DeptService
- `apps/rbac/services/auth_service.py` - 登录逻辑
- `apps/rbac/services/permission_service.py` - AuthControl, PermissionControl (从 dependency.py 移入)

**关键修改 - `api_service.refresh_api()` 不能直接 import app:**
```python
# OLD (app/controllers/api.py)
from app import app

# NEW (apps/rbac/services/api_service.py)
async def refresh_api(self, app: FastAPI):
    for route in app.routes:
        ...
```

**向后兼容:** 保持 `app/core/crud.py` 和 `app/controllers/` 继续工作

**验证:**
```python
from apps.rbac.services import user_service, role_service, auth_service, permission_service
```

---

## Phase 5: 创建 API Endpoints

**源文件:** `app/api/v1/*/` → `apps/rbac/api/`

**新文件:**
- `apps/rbac/api/__init__.py` - 聚合所有 router
- `apps/rbac/api/auth.py` - 从 `app/api/v1/base/base.py` 移入 (login, userinfo, usermenu, userapi, update_password)
- `apps/rbac/api/users.py` - 从 `app/api/v1/users/users.py` 移入
- `apps/rbac/api/roles.py` - 从 `app/api/v1/roles/roles.py` 移入
- `apps/rbac/api/menus.py` - 从 `app/api/v1/menus/menus.py` 移入
- `apps/rbac/api/apis.py` - 从 `app/api/v1/apis/apis.py` 移入
- `apps/rbac/api/depts.py` - 从 `app/api/v1/depts/depts.py` 移入
- `apps/rbac/api/auditlog.py` - 从 `app/api/v1/auditlog/auditlog.py` 移入

**apps/rbac/api/__init__.py 路由聚合:**
```python
from fastapi import APIRouter
from .auth import router as auth_router
from .users import router as users_router
# ... etc

rbac_router = APIRouter()
rbac_router.include_router(auth_router, prefix="/base")
rbac_router.include_router(users_router, prefix="/user", dependencies=[DependPermission])
# ... etc
```

**验证:**
```bash
curl http://localhost:9999/api/v1/base/access_token
```

---

## Phase 6: 创建 apps/rbac/main.py

**创建 `apps/rbac/main.py` - RBAC 应用工厂:**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from tortoise import Tortoise
from apps.rbac.core.exceptions import register_exceptions
from apps.rbac.core.middlewares import make_middlewares
from apps.rbac.api import rbac_router
# ... import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_data()
    yield
    await Tortoise.close_connections()

def create_rbac_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        middleware=make_middlewares(),
        lifespan=lifespan,
    )
    register_exceptions(app)
    app.include_router(rbac_router, prefix="/api")
    return app
```

**需要先复制到 `apps/rbac/core/`:**
- `apps/rbac/core/exceptions.py` - 从 `app/core/exceptions.py` 复制
- `apps/rbac/core/middlewares.py` - 从 `app/core/middlewares.py` 复制 (修复 imports)
- `apps/rbac/core/ctx.py` - 从 `app/core/ctx.py` 复制
- `apps/rbac/core/bgtask.py` - 从 `app/core/bgtask.py` 复制

**验证:**
```python
from apps.rbac.main import create_rbac_app
```

---

## Phase 7: 接入主应用入口

**目标:** 确保 `run.py` 导入 `app:app` 继续工作

**修改 `app/__init__.py`:**
```python
from apps.rbac.main import create_rbac_app as _create_rbac_app

def create_app() -> FastAPI:
    app = _create_rbac_app()
    # 保留主应用的 lifespan 逻辑
    return app

app = create_app()
```

**修改 `app/settings/config.py` - 更新 TORTOISE_ORM:**
```python
TORTOISE_ORM = {
    "apps": {
        "models": {
            "models": ["app.models", "apps.rbac.models", "aerich.models"],
            "default_connection": "postgres",
        },
    },
}
```

**验证:**
```bash
python run.py &
curl http://localhost:9999/docs
```

---

## Phase 8: 更新引用并清理

**修复所有 import:**
```bash
# 搜索需要修复的引用
grep -r "from app\.controllers\." --include="*.py" apps/rbac/
grep -r "from app\.core\.(crud|dependency)" --include="*.py" apps/rbac/
grep -r "from app\.schemas\." --include="*.py" apps/rbac/
```

**常见修复:**
```python
# OLD
from app.core.crud import CRUDBase
from app.schemas.base import Success, Fail

# NEW
from apps.rbac.services.crud_base import CRUDBase
from apps.rbac.schemas.base import Success, Fail
```

**清理 (Phase 8 完成后):**
- 删除 `app/controllers/` (如不再需要)
- 删除 `app/api/v1/` (已迁移到 `apps/rbac/api/`)
- 删除 `app/schemas/` (已迁移到 `apps/rbac/schemas/`)
- 删除 `app/models/admin.py` (已迁移到 `apps/rbac/models/`)

**验证:**
```bash
pytest
curl http://localhost:9999/api/v1/user/list
curl http://localhost:9999/api/v1/role/list
```

---

## 关键风险

| 风险 | 缓解 |
|------|------|
| Tortoise ORM 模型发现 | 确保 `TORTOISE_ORM` 包含 `"apps.rbac.models"` |
| 循环导入 | `api_service.refresh_api()` 不能 import app，需传参数 |
| JWT 依赖 | 保持 `app.settings` 共享配置 |
| Aerich 迁移 | 检查 `pyproject.toml` 中 `tool.aerich.tortoise_orm` 配置 |

---

## 关键文件

| 文件 | 作用 |
|------|------|
| `app/__init__.py` | 主应用入口，修改为委托给 apps/rbac |
| `app/core/dependency.py` | AuthControl/PermissionControl 移动到 services |
| `app/models/admin.py` | 所有模型的源文件，需拆分 |
| `app/api/v1/__init__.py` | 路由聚合，替换为 apps/rbac/api/__init__.py |
| `app/core/init_app.py` | init_data, make_middlewares 等逻辑拆分 |
| `app/settings/config.py` | 更新 TORTOISE_ORM 添加 apps.rbac.models |
