"""
Dify Dataset Client - Async httpx based client for Dify Dataset API
"""
import httpx
import json
import os
from typing import Optional, Dict, List, Any


class DifyDatasetClient:
    """
    Dify 知识库 (Dataset) API 封装类 - 纯 API 调用，无数据库操作
    文档参考：https://docs.dify.ai/versions/3-0-x/zh/user-guide/knowledge-base/knowledge-and-documents-maintenance/maintain-dataset-via-api
    """

    def __init__(self, api_key: str, base_url: str = "http://localhost:8000"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=60.0)

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def close(self):
        await self.client.aclose()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        通用请求方法
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        headers = self._headers()
        if files:
            # 当使用 files 参数时，不要设置 Content-Type，让 httpx 自动设置 multipart/form-data
            headers.pop("Content-Type", None)

        try:
            # 构造请求参数
            request_kwargs = {
                "method": method,
                "url": url,
                "headers": headers,
                "params": params or {},
                "timeout": timeout
            }

            # 根据不同情况设置请求体
            if files:
                request_kwargs["files"] = files
                # 对于文件上传，data 应该作为额外的表单字段
                if data:
                    request_kwargs["data"] = data
            elif json_data:
                request_kwargs["json"] = json_data
            elif data:
                request_kwargs["data"] = data

            print(f"[DEBUG] _make_request: {method} {url}")
            print(f"[DEBUG] headers: {headers}")
            if files:
                print(f"[DEBUG] files: {{'file': ('{files['file'][0]}', <{len(files['file'][1])} bytes>)}}")
            print(f"[DEBUG] data: {data}")
            print(f"[DEBUG] json_data: {json_data}")

            response = await self.client.request(**request_kwargs)
            print(f"[DEBUG] response status={response.status_code}, body={response.text[:500]}")
            response.raise_for_status()

            if response.status_code == 204:
                return {"result": "success", "status": 204}

            return response.json()

        except httpx.TimeoutException:
            raise Exception(f"请求超时（{timeout}秒）：{url}")
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP错误 {e.response.status_code}："
            try:
                error_detail = e.response.json()
                error_msg += f"{error_detail.get('message', '未知错误')}"
            except:
                error_msg += e.response.text
            raise Exception(error_msg)
        except httpx.RequestError as e:
            raise Exception(f"请求失败：{str(e)}")

    # ================= 数据集 (Dataset) 管理 =================

    async def get_datasets(self, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """获取数据集列表"""
        params = {"page": page, "limit": limit}
        return await self._make_request("GET", "datasets", params=params)

    async def get_dataset_detail(self, dataset_id: str) -> Dict[str, Any]:
        """获取单个数据集详情"""
        if not dataset_id:
            raise ValueError("dataset_id 不能为空")
        return await self._make_request("GET", f"datasets/{dataset_id}")

    async def create_dataset(self, name: str, permission: str = "only_me", provider: str = "vendor") -> Dict[str, Any]:
        """创建空知识库"""
        payload = {"name": name, "permission": permission, "provider": provider}
        return await self._make_request("POST", "datasets", json_data=payload)

    async def delete_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """删除知识库"""
        return await self._make_request("DELETE", f"datasets/{dataset_id}")

    async def find_dataset_id_by_name(self, dataset_name: str) -> Optional[str]:
        """根据知识库名称查找 ID"""
        page = 1
        limit = 50

        while True:
            res = await self.get_datasets(page=page, limit=limit)

            if 'data' not in res or not res['data']:
                break

            for dataset in res['data']:
                if dataset['name'] == dataset_name:
                    return dataset['id']

            if not res.get('has_more', False):
                break

            page += 1

        return None

    # ================= 文档 (Document) 管理 =================

    async def get_documents(self, dataset_id: str, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """获取数据集下的文档列表"""
        if not dataset_id:
            raise ValueError("dataset_id 不能为空")
        params = {"page": page, "limit": limit}
        return await self._make_request("GET", f"datasets/{dataset_id}/documents", params=params)

    async def get_document_detail(self, dataset_id: str, document_id: str) -> Dict[str, Any]:
        """获取单个文档详情"""
        if not (dataset_id and document_id):
            raise ValueError("dataset_id 和 document_id 均不能为空")
        return await self._make_request("GET", f"datasets/{dataset_id}/documents/{document_id}")

    async def upload_document(self, dataset_id: str, document_info: Dict[str, Any]) -> Dict[str, Any]:
        """上传文档到数据集"""
        if not dataset_id:
            raise ValueError("dataset_id 不能为空")
        if not document_info:
            raise ValueError("document_info 不能为空")
        if not any([document_info.get("content"), document_info.get("file_url"), document_info.get("file")]):
            raise ValueError("document_info 必须包含 content/file_url/file 中的一个")
        return await self._make_request("POST", f"datasets/{dataset_id}/documents", json_data=document_info)

    async def create_document_by_text(
        self,
        dataset_id: str,
        name: str,
        text: str,
        indexing_technique: str = "high_quality",
        process_rule: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """通过文本创建文档"""
        if process_rule is None:
            process_rule = {"mode": "automatic"}

        payload = {
            "name": name,
            "text": text,
            "indexing_technique": indexing_technique,
            "process_rule": process_rule
        }
        return await self._make_request("POST", f"/datasets/{dataset_id}/document/create_by_text", json_data=payload)

    async def create_document_by_file(
        self,
        dataset_id: str,
        file_path: str,
        indexing_technique: str = "high_quality",
        process_rule: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """通过文件创建文档"""
        if process_rule is None:
            process_rule = {"mode": "automatic"}

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # 读取文件内容到内存，避免文件句柄在 async 请求执行前被关闭
        with open(file_path, 'rb') as f:
            file_content = f.read()

        print(f"[DEBUG] create_document_by_file: file_path={file_path}, file_size={len(file_content)}")

        files = {'file': (os.path.basename(file_path), file_content)}
        data = {
            'data': json.dumps({
                "indexing_technique": indexing_technique,
                "process_rule": process_rule
            })
        }
        return await self._make_request(
            "POST",
            f"datasets/{dataset_id}/document/create_by_file",
            files=files,
            data=data
        )

    async def update_document(self, dataset_id: str, document_id: str, update_info: Dict[str, Any]) -> Dict[str, Any]:
        """更新数据集内的文档"""
        if not (dataset_id and document_id):
            raise ValueError("dataset_id 和 document_id 均不能为空")
        if not update_info:
            raise ValueError("update_info 不能为空")
        return await self._make_request("PUT", f"datasets/{dataset_id}/documents/{document_id}", json_data=update_info)

    async def update_document_by_text(self, dataset_id: str, document_id: str, name: str, text: str) -> Dict[str, Any]:
        """通过文本更新文档"""
        payload = {"name": name, "text": text}
        return await self._make_request("POST", f"datasets/{dataset_id}/documents/{document_id}/update_by_text", json_data=payload)

    async def delete_document(self, dataset_id: str, document_id: str) -> Dict[str, Any]:
        """删除数据集内的文档"""
        if not (dataset_id and document_id):
            raise ValueError("dataset_id 和 document_id 均不能为空")
        return await self._make_request("DELETE", f"datasets/{dataset_id}/documents/{document_id}")

    async def trigger_document_process(self, dataset_id: str, document_id: str) -> Dict[str, Any]:
        """触发文档重新处理"""
        if not (dataset_id and document_id):
            raise ValueError("dataset_id 和 document_id 均不能为空")
        return await self._make_request("POST", f"datasets/{dataset_id}/documents/{document_id}/process")

    async def get_indexing_status(self, dataset_id: str, batch: str) -> Dict[str, Any]:
        """获取文档嵌入状态"""
        return await self._make_request("GET", f"datasets/{dataset_id}/documents/{batch}/indexing-status")

    # ================= 分段 (Segment) 管理 =================

    async def add_segments(self, dataset_id: str, document_id: str, segments: List[Dict]) -> Dict[str, Any]:
        """新增分段"""
        payload = {"segments": segments}
        return await self._make_request("POST", f"datasets/{dataset_id}/documents/{document_id}/segments", json_data=payload)

    async def list_segments(self, dataset_id: str, document_id: str, status: Optional[str] = None) -> Dict[str, Any]:
        """查询文档分段"""
        params = {}
        if status:
            params['status'] = status
        return await self._make_request("GET", f"datasets/{dataset_id}/documents/{document_id}/segments", params=params)

    async def delete_segment(self, dataset_id: str, document_id: str, segment_id: str) -> Dict[str, Any]:
        """删除文档分段"""
        return await self._make_request("DELETE", f"datasets/{dataset_id}/documents/{document_id}/segments/{segment_id}")

    async def update_segment(self, dataset_id: str, document_id: str, segment_id: str, segment_data: Dict) -> Dict[str, Any]:
        """更新文档分段"""
        payload = {"segment": segment_data}
        return await self._make_request("POST", f"datasets/{dataset_id}/documents/{document_id}/segments/{segment_id}", json_data=payload)

    # ================= 元数据 (Metadata) 管理 =================

    async def list_metadata(self, dataset_id: str) -> Dict[str, Any]:
        """数据集的元数据列表"""
        return await self._make_request("GET", f"datasets/{dataset_id}/metadata")

    async def add_metadata_field(self, dataset_id: str, field_type: str, name: str) -> Dict[str, Any]:
        """新增知识库元数据字段"""
        payload = {"type": field_type, "name": name}
        return await self._make_request("POST", f"datasets/{dataset_id}/metadata", json_data=payload)

    async def update_metadata_field(self, dataset_id: str, metadata_id: str, name: str) -> Dict[str, Any]:
        """更新知识库元数据字段"""
        payload = {"name": name}
        return await self._make_request("PATCH", f"datasets/{dataset_id}/metadata/{metadata_id}", json_data=payload)

    async def delete_metadata_field(self, dataset_id: str, metadata_id: str) -> Dict[str, Any]:
        """删除知识库元数据字段"""
        return await self._make_request("DELETE", f"datasets/{dataset_id}/metadata/{metadata_id}")
