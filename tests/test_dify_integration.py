#!/usr/bin/env python3
"""
简化测试 ingest_document 功能，专注于 Dify 集成部分
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.kb_service.clients.dify import DifyDatasetClient
from apps.kb_service.core.config import kb_settings


async def test_dify_integration():
    """直接测试 Dify 集成"""
    # 测试文件路径
    file_path = "tests/rag-1.docx"

    if not os.path.exists(file_path):
        print(f"测试文件不存在: {file_path}")
        return

    print(f"使用测试文件: {file_path}")
    print(f"文件大小: {os.path.getsize(file_path)} bytes")

    # 检查必要的配置
    if not kb_settings.DIFY_API_KEY:
        print("错误: DIFY_API_KEY 未设置")
        return

    if not kb_settings.DIFY_DATASET_ID:
        print("错误: DIFY_DATASET_ID 未设置")
        return

    try:
        # 初始化 Dify 客户端
        client = DifyDatasetClient(
            api_key=kb_settings.DIFY_API_KEY,
            base_url=kb_settings.DIFY_BASE_URL,
        )

        print(f"使用API Key: {kb_settings.DIFY_API_KEY[:10]}...")
        print(f"使用Base URL: {kb_settings.DIFY_BASE_URL}")
        print(f"使用Dataset ID: {kb_settings.DIFY_DATASET_ID}")

        # 测试获取数据集详情
        print("获取数据集详情...")
        dataset_info = await client.get_dataset_detail(kb_settings.DIFY_DATASET_ID)
        print("数据集详情:", dataset_info.get("name", "Unknown"))

        # 测试创建文档
        print("开始上传文档...")
        result = await client.create_document_by_file(
            dataset_id=kb_settings.DIFY_DATASET_ID,
            file_path=file_path,
            indexing_technique="high_quality",
        )
        print("文档创建成功:", result.get("document", {}).get("id", "Unknown"))

        # 清理客户端
        await client.close()

    except Exception as e:
        print(f"操作失败: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_simple_text_upload():
    """测试简单的文本上传"""
    # 创建一个简单的测试文件
    test_file_path = "/tmp/simple_test.txt"
    with open(test_file_path, "w") as f:
        f.write("这是一个简单的测试文档，用于验证 Dify 集成。")

    try:
        # 初始化 Dify 客户端
        client = DifyDatasetClient(
            api_key=kb_settings.DIFY_API_KEY,
            base_url=kb_settings.DIFY_BASE_URL,
        )

        print("开始上传简单文本文件...")
        result = await client.create_document_by_file(
            dataset_id=kb_settings.DIFY_DATASET_ID,
            file_path=test_file_path,
            indexing_technique="high_quality",
        )
        print("文档创建成功:", result.get("document", {}).get("id", "Unknown"))

        # 清理客户端
        await client.close()

    except Exception as e:
        print(f"操作失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理测试文件
        if os.path.exists(test_file_path):
            os.remove(test_file_path)


if __name__ == "__main__":
    print("=== 测试 Dify 集成 ===")
    asyncio.run(test_dify_integration())

    print("\n=== 测试简单文本上传 ===")
    asyncio.run(test_simple_text_upload())