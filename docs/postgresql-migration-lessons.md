# KB Service 数据库迁移经验教训

## 问题 1：host.docker.internal vs localhost

**错误**：`socket.gaierror: [Errno 8] nodename nor servname provided, or known`

**原因**：配置中写了 `host.docker.internal`，但 Python 运行在宿主机（macOS）而非容器内。`host.docker.internal` 仅在 Docker 容器内部解析用。

**正确做法**：
- Python 运行在宿主机 → 用 `localhost` 或 `127.0.0.1`
- Python 运行在容器内 → 用 `host.docker.internal`

## 问题 2：DSN 连接字符串解析失败

**错误**：用 `postgresql://user:pass@127.0.0.1:5432/db` 格式报错 `nodename nor servname provided`

**原因**：`asyncpg` 对 DSN 字符串解析有问题，但用关键字参数 `host=`, `port=`, `user=`, `password=`, `database=` 可以正常连接。

**正确做法**：连接时用关键字参数而非 DSN 字符串：
```python
conn = await asyncpg.connect(
    host='127.0..1', port=5432, user='pgsql',
    password='Pass@1234', database='rag_db'
)
```

## 问题 3：worktree 没有 migrations 目录

**错误**：`FileNotFoundError: [Errno 2] No such file or directory: 'migrations/kb_service'`

**原因**：从 main 分支 clone 的 worktree 没有 `migrations/` 目录（该目录在 .gitignore 中，未被 track）

**正确做法**：在 worktree 中手动创建 migrations 目录：
```bash
mkdir -p migrations/kb_service
mkdir -p migrations/rbac
```

## 问题 4：Tortoise ORM 配置未注册 kb_service

**现象**：PostgreSQL 中没有 KB service 相关表

**原因**：`config/settings/config.py` 的 `TORTOISE_ORM.apps` 中只注册了 `rbac`，没有 `kb_service`

**正确做法**：在 `TORTOISE_ORM.apps` 中添加：
```python
"kb_service": {
    "models": ["apps.kb_service.models", "aerich.models"],
    "default_connection": "postgres",
},
```

## 问题 5：worktree 和 main 分支配置不同步

**现象**：在 main 分支更新了 config，但 worktree 看不到效果

**原因**：worktree 有独立的 `config/settings/config.py`，需要单独更新

**正确做法**：任何配置变更需要同步到 worktree 的 config

## 问题 6：Command.init() 是同步方法而非协程

**错误**：`RuntimeWarning: coroutine 'Command.init' was never awaited`

**原因**：`cmd.init()` 是普通方法调用，不应该 `await cmd.init()`

**正确做法**：
```python
cmd = Command(tortoise_config=settings.TORTOISE_ORM, app='kb_service')
await cmd.init_db(safe=True)  # 异步
cmd.init()                      # 同步
```

## 问题 7：aerich migrate 需要已有的版本文件

**错误**：`'NoneType' object has no attribute 'pop'`

**原因**：aerich 的 `migrate()` 需要数据库中已有 `aerich` 表和版本记录，首次运行时找不到历史版本

**正确做法**：首次为新 app 创建表，应该直接用 `upgrade` 生成表，而非先 `migrate`：
```python
cmd = Command(tortoise_config=settings.TORTOISE_ORM, app='kb_service')
await cmd.init_db(safe=True)
cmd.init()
await cmd.upgrade(run_in_transaction=True)
```

## 正确的迁移步骤（从零为新 app 创建表）

1. 确保 `config/settings/config.py` 的 `TORTOISE_ORM.apps` 已注册该 app
2. 在 worktree 中创建 `migrations/<app_name>/` 目录
3. 运行：
```python
from aerich import Command
import asyncio
import os
os.chdir('/path/to/worktree')
from config.settings.config import settings

async def migrate():
    cmd = Command(tortoise_config=settings.TORTOISE_ORM, app='kb_service')
    await cmd.init_db(safe=True)  # 创建 aerich 表
    cmd.init()
    await cmd.upgrade(run_in_transaction=True)  # 直接生成表

asyncio.run(migrate())
```
4. 验证：`SELECT tablename FROM pg_tables WHERE schemaname = 'public'`
