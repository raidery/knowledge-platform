from pydantic_settings import BaseSettings


class KBSettings(BaseSettings):
    APP_TITLE: str = "kb_service"
    VERSION: str = "1.0.0"
    UPLOAD_DIR: str = "/tmp/kb_uploads"

    # RAGFlow
    RAGFLOW_BASE_URL: str = "http://localhost:9380"
    RAGFLOW_API_KEY: str = ""

    # Dify
    DIFY_BASE_URL: str = "http://localhost"
    DIFY_API_KEY: str = ""

    # ARQ
    ARQ_REDIS_URL: str = "redis://localhost:6379"

    class Config:
        env_prefix = "KB_"


kb_settings = KBSettings()