# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Vue FastAPI Admin - A FastAPI + Vue3 admin platform with RBAC, dynamic routing, and JWT authentication.

## Backend Development

### Commands
```sh
# Install dependencies (requires Python 3.11+)
uv add pyproject.toml

# Run dev server (port 9999)
python run.py

# Lint
ruff check .
black --check .

# Format
isort .
black .

# Database migrations (Aerich)
aerich upgrade
```

### Architecture
- **Framework**: FastAPI with Tortoise ORM (async)
- **Database**: SQLite by default (`db.sqlite3`), supports MySQL/PostgreSQL/SQLServer via config
- **Auth**: JWT with 7-day expiry
- **Entry**: `run.py` imports `app:app` which creates the FastAPI instance
- **App factory**: `app/__init__.py` contains `create_app()` with lifespan context manager
- **Config**: `app/settings/config.py` - `TORTOISE_ORM` dict contains all DB connection settings
- **Models**: `app/models/admin.py` - User, Role, Menu, Api, Dept, AuditLog
- **API routes**: `app/api/v1/{module}/` - follows controller pattern (api layer delegates to controllers)
- **Schemas**: Pydantic models in `app/schemas/` for request/response validation
- **Middleware**: CORS enabled for all origins by default

## Frontend Development

### Commands
```sh
cd web
pnpm install   # or npm i

# Dev server
pnpm dev

# Build
pnpm build

# Lint
pnpm lint
pnpm lint:fix
```

### Architecture
- **Framework**: Vue 3 + Vite + Naive UI
- **State**: Pinia stores in `web/src/store/modules/`
- **Router**: Vue Router with guards in `web/src/router/guard/`
- **HTTP**: Axios wrapped in `web/src/utils/http/`
- **API layer**: `web/src/api/` - mirrors backend API structure
- **Components**: CRUD table/modal components in `web/src/components/table/` and `web/src/components/query-bar/`
- **Views**: `web/src/views/system/` - admin management pages

## Key Conventions

- Backend API prefix: `/api` (e.g., `/api/v1/users`)
- DateTime format: `%Y-%m-%d %H:%M:%S`
- Many-to-many relationships between User-Role, Role-Menu, Role-Api
- AuditLog tracks user actions with request/response details
- Frontend uses `useCRUD` composable for data table operations

---

## OpenSpec + Superpowers 工作流

> ⚠️ **Gstack 暂未启用** - 待理解其功能后再开启

两个插件组成主干：

| 插件 | 职责 | 类比 |
|------|------|------|
| **OpenSpec** | 规范与需求层（propose / explore / archive） | 蓝图 |
| **Superpowers** | 思考与流程层（brainstorm / write-plan / execute-plan / debug / verify / review） | 大脑 |

### 核心原则

1. **规范先行**：任何需求变更必须先过 OpenSpec，产出 proposal + design + tasks，再动手写代码。
2. **流程归 Superpowers**：brainstorm、plan、debug、verify、code review。
3. **独立 Reviewer 通道**：verification 和 code-review 分两个 pass。
4. **证据优先**：没有测试/截图/QA 报告不算完成。
5. **歧义先 Brainstorm**：任何创造性工作前先调用 brainstorming。

### 任务分流

- **只读任务**：分析、解释、架构说明、代码阅读 —— 直接处理。
- **轻量任务**：单文件修改、明确 bug 修复、配置调整 —— 直接实现 + 定向验证。
- **中任务**：多文件但边界清晰 —— OpenSpec propose → brainstorming + writing-plans → 实现 → verification。
- **大任务**：跨模块、新架构 —— 完整闭环流程。

### 安全护栏

- `rm -rf` / `DROP TABLE` / `force-push` / `git reset --hard` / `kubectl delete` 必须先过 `/careful` 或 `/guard`
- `/ship` 和 `/land-and-deploy` 必须用户明确确认
- 密钥/凭证/API Key 不得硬编码

### Change Delivery Gate

声明完成、准备 commit / push / PR 之前必须满足：
1. 已完成相关验证，并如实报告结果
2. 已过对应质量门禁（review / verification）
3. 没有验证证据，不得声称"通过" / "完成"
