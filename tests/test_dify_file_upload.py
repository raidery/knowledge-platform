#!/usr/bin/env python3
"""
测试 Dify 客户端文件上传功能
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.kb_service.clients.dify.dataset import DifyDatasetClient
from apps.kb_service.core.config import kb_settings

async def test_dify_file_upload():
    # 创建测试文件
    test_file_path = "/tmp/test_document1.txt"
    with open(test_file_path, "w") as f:
         f.write("这是一个测试文档内容，用于验证Dify客户端文件上传功能。")

    test_file_path = "/tmp/rag-1.docx"
    # 初始化客户端
    client = DifyDatasetClient(
        api_key=kb_settings.DIFY_API_KEY,
        base_url=kb_settings.DIFY_BASE_URL,
    )

    try:
        print(f"使用API Key: {kb_settings.DIFY_API_KEY}")
        print(f"使用Base URL: {kb_settings.DIFY_BASE_URL}")
        print(f"使用Dataset ID: {kb_settings.DIFY_DATASET_ID}")

        # 测试获取数据集详情
        dataset_info = await client.get_dataset_detail(kb_settings.DIFY_DATASET_ID)
        print("数据集详情:", dataset_info)

        # 测试创建文档
        print("开始上传文档...")
        result = await client.create_document_by_file(
            dataset_id=kb_settings.DIFY_DATASET_ID,
            file_path=test_file_path,
            indexing_technique="high_quality",
        )
        print("文档创建成功:", result)

    except Exception as e:
        print("操作失败:", str(e))
        import traceback
        traceback.print_exc()
    finally:
        # 清理测试文件
        # if os.path.exists(test_file_path):
        #     os.remove(test_file_path)
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_dify_file_upload())