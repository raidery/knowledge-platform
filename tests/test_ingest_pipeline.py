#!/usr/bin/env python3
"""
测试 IngestPipeline 类的 run 方法
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.kb_service.pipelines.ingest import IngestPipeline


async def test_ingest_pipeline():
    """测试 IngestPipeline 类"""
    # 测试文件路径
    file_path = "tests/rag-1.docx"

    if not os.path.exists(file_path):
        print(f"测试文件不存在: {file_path}")
        return

    print(f"使用测试文件: {file_path}")
    print(f"文件大小: {os.path.getsize(file_path)} bytes")

    try:
        # 创建 IngestPipeline 实例
        pipeline = IngestPipeline()

        # 调用 pipeline.run 方法（小文件同步处理）
        print("开始调用 IngestPipeline.run...")
        result = await pipeline.run(
            file_path=file_path,
            business_id="test_business_123",
            callback_url=None,
            enable_split=False,  # 不启用切分
            pages_per_chunk=50,
            max_chunks=100,
            dataset_id="2136ae74-ea3f-45d3-90d0-c65fc5257470"  # 使用默认数据集
        )

        print("文档摄入成功!")
        print(f"Job ID: {result['job_id']}")
        print(f"文档 ID: {result['doc_id']}")
        print(f"状态: {result['status']}")
        print(f"创建时间: {result['created_at']}")

    except Exception as e:
        print(f"操作失败: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_ingest_pipeline_small_file():
    """测试 IngestPipeline 类处理小文件"""
    # 创建一个小的测试文件
    test_file_path = "/tmp/small_test.txt"
    with open(test_file_path, "w") as f:
        f.write("这是一个小测试文档，用于测试小文件的同步处理。")

    try:
        # 创建 IngestPipeline 实例
        pipeline = IngestPipeline()

        # 调用 pipeline.run 方法（小文件同步处理）
        print("开始调用 IngestPipeline.run (小文件)...")
        result = await pipeline.run(
            file_path=test_file_path,
            business_id="test_business_123",
            callback_url=None,
            enable_split=False,
            pages_per_chunk=50,
            max_chunks=100,
            dataset_id="2136ae74-ea3f-45d3-90d0-c65fc5257470"  # 使用默认数据集
        )

        print("文档摄入成功!")
        print(f"Job ID: {result['job_id']}")
        print(f"文档 ID: {result['doc_id']}")
        print(f"状态: {result['status']}")
        print(f"创建时间: {result['created_at']}")

    except Exception as e:
        print(f"操作失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理测试文件
        if os.path.exists(test_file_path):
            os.remove(test_file_path)


if __name__ == "__main__":
    print("=== 测试 IngestPipeline 类 ===")
    asyncio.run(test_ingest_pipeline())

    print("\n=== 测试 IngestPipeline 类 (小文件) ===")
    asyncio.run(test_ingest_pipeline_small_file())