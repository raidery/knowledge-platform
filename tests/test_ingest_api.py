#!/usr/bin/env python3
"""
测试 ingest_document API 接口
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from fastapi import UploadFile
from apps.kb_service.api.ingest import ingest_document


async def test_ingest_document():
    """测试 ingest_document API"""
    # 测试文件路径
    file_path = "tests/rag-1.docx"

    if not os.path.exists(file_path):
        print(f"测试文件不存在: {file_path}")
        return

    print(f"使用测试文件: {file_path}")
    print(f"文件大小: {os.path.getsize(file_path)} bytes")

    try:
        # 模拟 UploadFile 对象
        with open(file_path, "rb") as f:
            file_content = f.read()

        # 创建一个简单的 UploadFile 模拟对象
        class MockUploadFile:
            def __init__(self, filename, content, content_type):
                self.filename = filename
                self.content = content
                self.content_type = content_type

            async def read(self):
                return self.content

        mock_file = MockUploadFile(
            filename="rag-1.docx",
            content=file_content,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        # 调用 ingest_document 函数
        print("开始调用 ingest_document...")
        result = await ingest_document(
            business_id="test_business_123",
            file=mock_file,
            dataset_id=None,  # 使用默认数据集
            callback_url=None,
            enable_split=False,  # 不启用切分
            pages_per_chunk=50,
            max_chunks=100,
            split_level=None,
            split_pattern=None,
            force_split=False
        )

        print("文档摄入成功!")
        print(f"Job ID: {result.job_id}")
        print(f"文档 ID: {result.doc_id}")
        print(f"状态: {result.status}")
        print(f"创建时间: {result.created_at}")
        if result.sections_count:
            print(f"章节数量: {result.sections_count}")
        if result.sections:
            print(f"章节详情: {result.sections}")

    except Exception as e:
        print(f"操作失败: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_ingest_document_with_split():
    """测试 ingest_document API 并启用文档切分"""
    # 测试文件路径
    file_path = "tests/rag-1.docx"

    if not os.path.exists(file_path):
        print(f"测试文件不存在: {file_path}")
        return

    print(f"使用测试文件: {file_path}")
    print(f"文件大小: {os.path.getsize(file_path)} bytes")

    try:
        # 模拟 UploadFile 对象
        with open(file_path, "rb") as f:
            file_content = f.read()

        # 创建一个简单的 UploadFile 模拟对象
        class MockUploadFile:
            def __init__(self, filename, content, content_type):
                self.filename = filename
                self.content = content
                self.content_type = content_type

            async def read(self):
                return self.content

        mock_file = MockUploadFile(
            filename="rag-1.docx",
            content=file_content,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        # 调用 ingest_document 函数，启用切分
        print("开始调用 ingest_document (启用切分)...")
        result = await ingest_document(
            business_id="test_business_123",
            file=mock_file,
            dataset_id=None,  # 使用默认数据集
            callback_url=None,
            enable_split=True,  # 启用切分
            pages_per_chunk=50,
            max_chunks=100,
            split_level=1,  # 按一级标题切分
            split_pattern=None,
            force_split=True  # 强制切分
        )

        print("文档摄入成功!")
        print(f"Job ID: {result.job_id}")
        print(f"文档 ID: {result.doc_id}")
        print(f"状态: {result.status}")
        print(f"创建时间: {result.created_at}")
        if result.sections_count:
            print(f"章节数量: {result.sections_count}")
        if result.sections:
            print(f"章节详情: {result.sections}")

    except Exception as e:
        print(f"操作失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=== 测试 ingest_document API ===")
    asyncio.run(test_ingest_document())

    print("\n=== 测试 ingest_document API (启用切分) ===")
    asyncio.run(test_ingest_document_with_split())