import re
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_size(value: str) -> int:
    """Parse size string like '1M', '1MB', '1GB', '1m' to bytes."""
    if isinstance(value, int):
        return value
    match = re.match(r"^(\d+(?:\.\d+)?)\s*([KMGT]?B?)$", value.strip(), re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid size format: {value}")
    number, unit = match.groups()
    multipliers = {"": 1, "K": 1024, "KB": 1024, "M": 1024**2, "MB": 1024**2,
                   "G": 1024**3, "GB": 1024**3, "T": 1024**4, "TB": 1024**4}
    return int(float(number) * multipliers.get(unit.upper(), 1))


class KBSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_TITLE: str = "kb_service"
    VERSION: str = "1.0.0"
    UPLOAD_DIR: str = "/tmp/kb_uploads"

    # RAGFlow
    RAGFLOW_BASE_URL: str = "http://localhost:9380"
    RAGFLOW_API_KEY: str = ""

    # Dify
    DIFY_BASE_URL: str = "http://localhost:8000"
    DIFY_API_KEY: str = ""
    DIFY_DATASET_ID: str = ""

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    # Queue
    QUEUE_SIZE_THRESHOLD: int = 1048576  # 1MB

    @field_validator("QUEUE_SIZE_THRESHOLD", mode="before")
    @classmethod
    def parse_size_threshold(cls, v):
        if isinstance(v, str):
            return _parse_size(v)
        return v


kb_settings = KBSettings()