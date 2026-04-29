from fastapi import APIRouter, Query

from apps.kb_service.clients.dify_client import DifyClient
from apps.kb_service.core.config import kb_settings

router = APIRouter()


def get_dify_client() -> DifyClient:
    return DifyClient(api_key=kb_settings.DIFY_API_KEY, base_url=kb_settings.DIFY_BASE_URL)


@router.get("/datasets")
async def get_datasets(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    """查询 Dify 知识库数据集列表"""
    client = get_dify_client()
    return await client.get_datasets(page=page, limit=limit)
