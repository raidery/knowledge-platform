import httpx
import json
import os
import re
from typing import Optional, Dict, List, Generator, Any, Union


def remove_thinking_tags(text: str) -> str:
    """
    移除字符串中&lt;begin_thinking&gt;和&lt;end_thinking&gt;标签及其之间的所有内容。
    参数:
        text: 包含思考标签的原始文本
    返回:
        清理后的文本，不包含思考标签部分
    示例:
        &gt;&gt;&gt; input_text = "&lt;begin_thinking&gt;思考过程...&lt;end_thinking&gt;实际答案"
        &gt;&gt;&gt; remove_thinking_tags(input_text)
        '实际答案'
    """
    if not isinstance(text, str):
        raise TypeError("输入必须为字符串")
    # 使用正则表达式匹配并移除&lt;begin_thinking&gt;...&lt;end_thinking&gt;标签及其内容
    thinking_pattern = re.compile(r'&lt;begin_thinking&gt;.*?&lt;end_thinking&gt;', re.DOTALL)
    cleaned_text = thinking_pattern.sub('', text)
    return cleaned_text.strip()

class DifyChatClient:
    def __init__(self, api_key: str, base_url: str = "http://192.168.100.37/v1", client_type: str = "general"):
        """
        初始化 Dify 客户端
        :param api_key: 应用的 API Key (App Key)
        :param base_url: Dify API 的基础 URL
        :param client_type: 客户端类型标识 ("conversation" 或 "contract_review")
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.client_type = client_type
        # 基础 Header，仅包含认证信息
        self.default_headers = {
            "Authorization": f"Bearer {api_key}"
        }
        self.client = httpx.AsyncClient(timeout=60.0)

    def _get_json_headers(self) -> Dict:
        """获取用于 JSON 请求的 Headers"""
        headers = self.default_headers.copy()
        headers["Content-Type"] = "application/json"
        return headers

    async def close(self):
        """关闭 HTTP 连接"""
        await self.client.aclose()

    # =========================================================================
    # 1. 核心对话功能 (Core Chat)
    # =========================================================================

    async def chat_message(
        self,
        query: str,
        user: str,
        inputs: Optional[Dict] = None,
        conversation_id: str = "",
        response_mode: str = "blocking",
        files: Optional[List[Dict]] = None,
        auto_generate_name: bool = True
    ) -> Union[Dict, Generator[Dict, None, None]]:
        """
        发送对话消息
        :param query: 用户提问内容
        :param user: 用户唯一标识
        :param inputs: 提示词变量 inputs
        :param conversation_id: 会话 ID (若开启新会话则留空)
        :param response_mode: 'blocking' (阻塞) 或 'streaming' (流式)
        :param files: 文件列表 (包含 type, transfer_method, upload_file_id 等)
        :param auto_generate_name: 是否自动生成标题
        """
        url = f"{self.base_url}/chat-messages"
        payload = {
            "inputs": inputs if inputs is not None else {},
            "query": query,
            "response_mode": response_mode,
            "conversation_id": conversation_id,
            "user": user,
            "files": files or [],
            "auto_generate_name": auto_generate_name
        }

        if response_mode == "blocking":
            response = await self.client.post(url, headers=self._get_json_headers(), json=payload)
            response.raise_for_status()
            return response.json()

        elif response_mode == "streaming":
            return self._handle_stream_response(url, payload)

        else:
            raise ValueError("response_mode must be 'blocking' or 'streaming'")

    async def contract_review(
        self,
        content: str,
        user: str,
        review_depth: str = "standard",
        focus_areas: Optional[List[str]] = None,
        files: Optional[List[Dict]] = None,
        conversation_id: str = ""
    ) -> Union[Dict, Generator[Dict, None, None]]:
        """
        合同法合规性审查
        :param content: 待审查的内容
        :param user: 用户唯一标识
        :param review_depth: 审查深度 ('standard', 'deep', 'specialized')
        :param focus_areas: 审查关注重点列表
        :param files: 文件列表 (包含 type, transfer_method, upload_file_id 等)
        :param conversation_id: 会话 ID (若开启新会话则留空)
        """
        # 构造查询语句
        depth_descriptions = {
            "standard": "标准审查 (快速合规性检查，3-5分钟)",
            "deep": "深度审查 (多维度风险分析，10-15分钟)",
            "specialized": "专项审查 (针对特定领域深入分析，20-30分钟)"
        }

        depth_desc = depth_descriptions.get(review_depth, depth_descriptions["standard"])

        # 构建基础查询
        query = f"""请对以下内容进行合同法合规性审查:

{content}

审查要求:
1. 审查深度: {depth_desc}
"""

        # 添加关注重点
        if focus_areas:
            query += f"2. 关注重点: {', '.join(focus_areas)}\n"
        else:
            query += "2. 关注重点: 请全面审查合同的各个方面\n"

        # 添加输出格式要求
        query += """

输出要求：
请严格按照以下格式输出审查结果，不要添加额外的解释或文本：

总体评价：基本合规       置信度：87%

合规点：✓ 符合《具体法规名称》第X条
        ✓ 符合《具体法规名称》第X条
        （示例：✓ 符合《中华人民共和国民法典》第465条）

风险提示：
（列出具体的风险提示，每行一项）
（示例：合同金额未明确约定违约责任）

需补充莲湖区备案：
（列出需要补充的备案事项）
（示例：需向莲湖区市场监督管理局备案）

潜在风险：涉及民用土地使用问题
        （可以有多行）
        （示例：可能存在土地使用权争议）

法规依据：
1. 《中华人民共和国兵役法》第XX条
2. 《陕西省民兵预备役工作条例》第XX条
3. 《中华人民共和国民法典》第XX条
（根据实际情况引用相关法规条款）

请详细分析是否存在违反《民法典》合同编相关规定的情况，并给出具体建议。"""

        focus_areas_result = ", ".join(focus_areas)
        # 构造输入参数
        inputs: Dict[str, Any] = {
            "review_depth": review_depth,
            "focus_areas": focus_areas_result or ''
        }

        query = content
        return await self.chat_message(
            query=query,
            user=user,
            inputs=inputs,
            conversation_id=conversation_id,
            response_mode="blocking",
            files=files
        )

    async def _handle_stream_response(self, url: str, payload: Dict) -> Generator[Dict, None, None]:
        """内部方法：处理 SSE 流式响应"""
        async with self.client.stream("POST", url, headers=self._get_json_headers(), json=payload) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if line:
                    line_str = line.strip()
                    # 解析 SSE 格式: "data: {...}"
                    if line_str.startswith("data: "):
                        try:
                            yield json.loads(line_str[6:])
                        except json.JSONDecodeError:
                            continue

    async def get_suggested_questions(self, message_id: str, user: str) -> List[str]:
        """
        获取下一轮建议问题列表
        :param message_id: 消息 ID (通常是 assistant 回复的消息 ID)
        :param user: 用户标识
        """
        url = f"{self.base_url}/messages/{message_id}/suggested"
        params = {"user": user}

        response = await self.client.get(url, headers=self._get_json_headers(), params=params)
        response.raise_for_status()

        data = response.json()
        if data.get("result") == "success":
            return data.get("data", [])
        return []

    # =========================================================================
    # 2. 文件管理功能 (File Management)
    # =========================================================================

    async def upload_file(self, file_path: str, user: str) -> Dict:
        """
        上传文件 (用于多模态理解)
        :param file_path: 本地文件路径
        :param user: 用户标识
        :return: 包含 id, name, url 等信息的字典
        """
        url = f"{self.base_url}/files/upload"

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # 使用 with 语句确保文件句柄被正确关闭
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            data = {'user': user}
            # 注意：httpx 处理 files 时会自动设置 Content-Type 为 multipart/form-data
            response = await self.client.post(url, headers=self.default_headers, files=files, data=data)

        response.raise_for_status()
        return response.json()

    async def get_file_preview(
        self,
        file_id: str,
        save_path: Optional[str] = None,
        as_attachment: bool = False
    ) -> Union[bytes, str]:
        """
        文件预览或下载
        :param file_id: 文件 ID
        :param save_path: (可选) 本地保存路径，若提供则写入文件并返回路径
        :param as_attachment: 是否强制作为附件下载
        :return: 二进制内容 (bytes) 或 保存路径 (str)
        """
        url = f"{self.base_url}/files/{file_id}/preview"
        params = {"as_attachment": str(as_attachment).lower()}

        # 使用 stream=True 防止大文件撑爆内存
        async with self.client.stream("GET", url, headers=self.default_headers, params=params) as response:
            response.raise_for_status()

            if save_path:
                with open(save_path, 'wb') as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
                return save_path

            content = b""
            async for chunk in response.aiter_bytes():
                content += chunk
            return content

    # =========================================================================
    # 3. 会话与历史记录管理 (Conversation & History)
    # =========================================================================

    async def get_conversations(
        self,
        user: str,
        last_id: Optional[str] = None,
        limit: int = 20,
        sort_by: str = "-updated_at"
    ) -> Dict:
        """
        获取会话列表
        :param user: 用户标识
        :param last_id: 当前页最后一条记录的 ID (用于翻页)
        :param limit: 返回条数 (1-100)
        :param sort_by: 排序方式 (默认按更新时间倒序)
        """
        url = f"{self.base_url}/conversations"
        params = {
            "user": user,
            "limit": limit,
            "sort_by": sort_by
        }
        if last_id:
            params["last_id"] = last_id

        response = await self.client.get(url, headers=self._get_json_headers(), params=params)
        response.raise_for_status()
        return response.json()

    async def get_conversation_history(
        self,
        user: str,
        conversation_id: str,
        first_id: Optional[str] = None,
        limit: int = 20
    ) -> Dict:
        """
        获取某个会话的历史消息 (倒序返回)
        :param user: 用户标识
        :param conversation_id: 会话 ID
        :param first_id: 当前页第一条记录的 ID (用于加载更早的消息)
        :param limit: 返回条数
        """
        url = f"{self.base_url}/messages"
        params = {
            "user": user,
            "conversation_id": conversation_id,
            "limit": limit
        }
        if first_id:
            params["first_id"] = first_id

        response = await self.client.get(url, headers=self._get_json_headers(), params=params)
        response.raise_for_status()
        return response.json()

    async def delete_conversation(self, conversation_id: str, user: str) -> str:
        """
        删除会话
        :param conversation_id: 会话 ID
        :param user: 用户标识，由开发者定义规则，需保证用户标识在应用内唯一
        :return: 固定返回 success
        """
        url = f"{self.base_url}/conversations/{conversation_id}"
        payload = {
            "user": user
        }

        response = await self.client.delete(url, headers=self._get_json_headers(), json=payload)
        response.raise_for_status()

        # 根据API文档，删除成功返回204状态码，无内容
        if response.status_code == 204:
            return "success"
        else:
            # 如果返回其他内容，尝试解析JSON
            try:
                result = response.json()
                return result.get("result", "success")
            except:
                return "success"