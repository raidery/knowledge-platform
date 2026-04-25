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
