import httpx


class RagFlowClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=60.0)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def upload_document(self, file_path: str, doc_id: str) -> dict:
        # Phase 1: 占位实现
        return {"code": 0, "data": {"doc_id": doc_id}}

    async def get_document_status(self, doc_id: str) -> dict:
        # Phase 1: 占位实现
        return {"code": 0, "data": {"status": "processing"}}

    async def close(self):
        await self.client.aclose()