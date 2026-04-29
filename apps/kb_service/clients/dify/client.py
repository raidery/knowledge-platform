"""
Dify Client - Unified async client for Dify API
Integrates Chat and Dataset management capabilities
"""
import httpx
from typing import Optional, Dict, List, Any

from .chat import DifyChatClient
from .dataset import DifyDatasetClient


class DifyClient:
    """
    统一的 Dify API 客户端
    整合 Chat 对话和 Dataset 知识库管理功能
    """

    def __init__(self, api_key: str, base_url: str = "http://192.168.100.37/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.chat = DifyChatClient(api_key=api_key, base_url=base_url)
        self.dataset = DifyDatasetClient(api_key=api_key, base_url=base_url)

    async def close(self):
        """关闭所有 HTTP 连接"""
        await self.chat.close()
        await self.dataset.close()

    # ================= Chat API (代理到 DifyChatClient) =================

    async def chat_message(
        self,
        query: str,
        user: str,
        inputs: Optional[Dict] = None,
        conversation_id: str = "",
        response_mode: str = "blocking",
        files: Optional[List[Dict]] = None,
        auto_generate_name: bool = True
    ) -> Dict[str, Any]:
        """发送对话消息"""
        return await self.chat.chat_message(
            query=query,
            user=user,
            inputs=inputs,
            conversation_id=conversation_id,
            response_mode=response_mode,
            files=files,
            auto_generate_name=auto_generate_name
        )

    async def contract_review(
        self,
        content: str,
        user: str,
        review_depth: str = "standard",
        focus_areas: Optional[List[str]] = None,
        files: Optional[List[Dict]] = None,
        conversation_id: str = ""
    ) -> Dict[str, Any]:
        """合同法合规性审查"""
        return await self.chat.contract_review(
            content=content,
            user=user,
            review_depth=review_depth,
            focus_areas=focus_areas,
            files=files,
            conversation_id=conversation_id
        )

    async def get_suggested_questions(self, message_id: str, user: str) -> List[str]:
        """获取建议问题"""
        return await self.chat.get_suggested_questions(message_id=message_id, user=user)

    async def upload_file(self, file_path: str, user: str) -> Dict[str, Any]:
        """上传文件"""
        return await self.chat.upload_file(file_path=file_path, user=user)

    async def get_file_preview(
        self,
        file_id: str,
        save_path: Optional[str] = None,
        as_attachment: bool = False
    ) -> Any:
        """获取文件预览"""
        return await self.chat.get_file_preview(file_id=file_id, save_path=save_path, as_attachment=as_attachment)

    async def get_conversations(
        self,
        user: str,
        last_id: Optional[str] = None,
        limit: int = 20,
        sort_by: str = "-updated_at"
    ) -> Dict[str, Any]:
        """获取会话列表"""
        return await self.chat.get_conversations(user=user, last_id=last_id, limit=limit, sort_by=sort_by)

    async def get_conversation_history(
        self,
        user: str,
        conversation_id: str,
        first_id: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """获取会话历史"""
        return await self.chat.get_conversation_history(
            user=user,
            conversation_id=conversation_id,
            first_id=first_id,
            limit=limit
        )

    async def delete_conversation(self, conversation_id: str, user: str) -> str:
        """删除会话"""
        return await self.chat.delete_conversation(conversation_id=conversation_id, user=user)

    # ================= Dataset API (代理到 DifyDatasetClient) =================

    async def get_datasets(self, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """获取数据集列表"""
        return await self.dataset.get_datasets(page=page, limit=limit)

    async def get_dataset_detail(self, dataset_id: str) -> Dict[str, Any]:
        """获取数据集详情"""
        return await self.dataset.get_dataset_detail(dataset_id=dataset_id)

    async def create_dataset(self, name: str, permission: str = "only_me", provider: str = "vendor") -> Dict[str, Any]:
        """创建知识库"""
        return await self.dataset.create_dataset(name=name, permission=permission, provider=provider)

    async def delete_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """删除知识库"""
        return await self.dataset.delete_dataset(dataset_id=dataset_id)

    async def find_dataset_id_by_name(self, dataset_name: str) -> Optional[str]:
        """根据名称查找数据集"""
        return await self.dataset.find_dataset_id_by_name(dataset_name=dataset_name)

    async def get_documents(self, dataset_id: str, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """获取文档列表"""
        return await self.dataset.get_documents(dataset_id=dataset_id, page=page, limit=limit)

    async def get_document_detail(self, dataset_id: str, document_id: str) -> Dict[str, Any]:
        """获取文档详情"""
        return await self.dataset.get_document_detail(dataset_id=dataset_id, document_id=document_id)

    async def upload_document(self, dataset_id: str, document_info: Dict[str, Any]) -> Dict[str, Any]:
        """上传文档"""
        return await self.dataset.upload_document(dataset_id=dataset_id, document_info=document_info)

    async def create_document_by_text(
        self,
        dataset_id: str,
        name: str,
        text: str,
        indexing_technique: str = "high_quality",
        process_rule: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """通过文本创建文档"""
        return await self.dataset.create_document_by_text(
            dataset_id=dataset_id,
            name=name,
            text=text,
            indexing_technique=indexing_technique,
            process_rule=process_rule
        )

    async def create_document_by_file(
        self,
        dataset_id: str,
        file_path: str,
        indexing_technique: str = "high_quality",
        process_rule: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """通过文件创建文档"""
        return await self.dataset.create_document_by_file(
            dataset_id=dataset_id,
            file_path=file_path,
            indexing_technique=indexing_technique,
            process_rule=process_rule
        )

    async def update_document(self, dataset_id: str, document_id: str, update_info: Dict[str, Any]) -> Dict[str, Any]:
        """更新文档"""
        return await self.dataset.update_document(dataset_id=dataset_id, document_id=document_id, update_info=update_info)

    async def delete_document(self, dataset_id: str, document_id: str) -> Dict[str, Any]:
        """删除文档"""
        return await self.dataset.delete_document(dataset_id=dataset_id, document_id=document_id)

    async def trigger_document_process(self, dataset_id: str, document_id: str) -> Dict[str, Any]:
        """触发文档处理"""
        return await self.dataset.trigger_document_process(dataset_id=dataset_id, document_id=document_id)

    async def get_indexing_status(self, dataset_id: str, batch: str) -> Dict[str, Any]:
        """获取索引状态"""
        return await self.dataset.get_indexing_status(dataset_id=dataset_id, batch=batch)

    async def add_segments(self, dataset_id: str, document_id: str, segments: List[Dict]) -> Dict[str, Any]:
        """添加分段"""
        return await self.dataset.add_segments(dataset_id=dataset_id, document_id=document_id, segments=segments)

    async def list_segments(self, dataset_id: str, document_id: str, status: Optional[str] = None) -> Dict[str, Any]:
        """列出分段"""
        return await self.dataset.list_segments(dataset_id=dataset_id, document_id=document_id, status=status)

    async def delete_segment(self, dataset_id: str, document_id: str, segment_id: str) -> Dict[str, Any]:
        """删除分段"""
        return await self.dataset.delete_segment(dataset_id=dataset_id, document_id=document_id, segment_id=segment_id)

    async def update_segment(self, dataset_id: str, document_id: str, segment_id: str, segment_data: Dict) -> Dict[str, Any]:
        """更新分段"""
        return await self.dataset.update_segment(
            dataset_id=dataset_id,
            document_id=document_id,
            segment_id=segment_id,
            segment_data=segment_data
        )

    # ================= Metadata API =================

    async def list_metadata(self, dataset_id: str) -> Dict[str, Any]:
        """列出元数据"""
        return await self.dataset.list_metadata(dataset_id=dataset_id)

    async def add_metadata_field(self, dataset_id: str, field_type: str, name: str) -> Dict[str, Any]:
        """添加元数据字段"""
        return await self.dataset.add_metadata_field(dataset_id=dataset_id, field_type=field_type, name=name)

    async def update_metadata_field(self, dataset_id: str, metadata_id: str, name: str) -> Dict[str, Any]:
        """更新元数据字段"""
        return await self.dataset.update_metadata_field(dataset_id=dataset_id, metadata_id=metadata_id, name=name)

    async def delete_metadata_field(self, dataset_id: str, metadata_id: str) -> Dict[str, Any]:
        """删除元数据字段"""
        return await self.dataset.delete_metadata_field(dataset_id=dataset_id, metadata_id=metadata_id)
