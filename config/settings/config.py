import os
import typing

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    VERSION: str = "0.1.0"
    APP_TITLE: str = "知识问答管理平台"
    PROJECT_NAME: str = "知识问答管理平台"
    APP_DESCRIPTION: str = "Description"

    CORS_ORIGINS: typing.List = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: typing.List = ["*"]
    CORS_ALLOW_HEADERS: typing.List = ["*"]

    DEBUG: bool = True

    PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
    BASE_DIR: str = os.path.abspath(os.path.join(PROJECT_ROOT, os.pardir))
    LOGS_ROOT: str = os.path.join(BASE_DIR, "logs")
    SECRET_KEY: str = "3488a63e1765035d386f05409663f55c83bfae3b3c61a932744b20ad14244dcf"  # openssl rand -hex 32
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 day
    TORTOISE_ORM: dict = {
        "connections": {
            # SQLite configuration
            "sqlite": {
                "engine": "tortoise.backends.sqlite",
                "credentials": {"file_path": f"{BASE_DIR}/db.sqlite3"},
            },
            # MySQL/MariaDB configuration
            # Install with: tortoise-orm[asyncmy]
            # "mysql": {
            #     "engine": "tortoise.backends.mysql",
            #     "credentials": {
            #         "host": "localhost",
            #         "port": 3306,
            #         "user": "yourusername",
            #         "password": "yourpassword",
            #         "database": "yourdatabase",
            #     },
            # },
            # PostgreSQL configuration (Docker: host.docker.internal, native: localhost)
            "postgres": {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "host": "localhost",
                    "port": 5432,
                    "user": "pgsql",
                    "password": "Pass@1234",
                    "database": "rag_db",
                },
            },
            # MSSQL/Oracle configuration
            # Install with: tortoise-orm[asyncodbc]
            # "oracle": {
            #     "engine": "tortoise.backends.asyncodbc",
            #     "credentials": {
            #         "host": "localhost",
            #         "port": 1433,
            #         "user": "yourusername",
            #         "password": "yourpassword",
            #         "database": "yourdatabase",
            #     },
            # },
            # SQLServer configuration
            # Install with: tortoise-orm[asyncodbc]
            # "sqlserver": {
            #     "engine": "tortoise.backends.asyncodbc",
            #     "credentials": {
            #         "host": "localhost",
            #         "port": 1433,
            #         "user": "yourusername",
            #         "password": "yourpassword",
            #         "database": "yourdatabase",
            #     },
            # },
        },
        "apps": {
            "rbac": {
                "models": ["apps.rbac.models", "aerich.models"],
                "default_connection": "postgres",
            },
            "kb_service": {
                "models": ["apps.kb_service.models", "aerich.models"],
                "default_connection": "postgres",
            },
        },
        "use_tz": False,
        "timezone": "Asia/Shanghai",
    }
    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"


settings = Settings()
