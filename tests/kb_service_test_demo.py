#!/usr/bin/env python3
"""
KB Service API 测试演示脚本
测试 http://localhost:9999/api/v1/kb/ 模块的所有主要功能
"""

import os
import sys
import time
import requests
import json
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://localhost:9999/api/v1/kb"
TEST_FILE_PATH = "test_sample.txt"


def create_test_file():
    """创建测试文件"""
    content = """
这是一个用于测试的知识库文档。
它包含了一些示例文本，用于验证文档上传和处理功能。
文档内容可以是任意文本，用于模拟真实的业务文档。
    """.strip()

    with open(TEST_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ 创建测试文件: {TEST_FILE_PATH}")


def test_ingest_document():
    """测试文档上传接口"""
    print("\n=== 测试文档上传接口 ===")

    if not os.path.exists(TEST_FILE_PATH):
        create_test_file()

    with open(TEST_FILE_PATH, "rb") as f:
        files = {"file": (TEST_FILE_PATH, f, "text/plain")}
        data = {
            "business_id": "test_business_001",
            "callback_url": "http://localhost:9999/callback/test",
            "enable_split": "false",
            "pages_per_chunk": "50",
            "max_chunks": "100"
        }

        try:
            response = requests.post(
                f"{BASE_URL}/ingest",
                files=files,
                data=data
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ 文档上传成功")
                print(f"  Job ID: {result.get('job_id')}")
                print(f"  Doc ID: {result.get('doc_id')}")
                print(f"  Status: {result.get('status')}")
                return result.get('job_id')
            else:
                print(f"✗ 文档上传失败: {response.status_code}")
                print(f"  Response: {response.text}")
                return None

        except Exception as e:
            print(f"✗ 请求异常: {str(e)}")
            return None


def test_get_job_status(job_id):
    """测试查询任务状态接口"""
    if not job_id:
        print("⚠️  无效的 Job ID")
        return

    print(f"\n=== 测试查询任务状态接口 (Job ID: {job_id}) ===")

    try:
        response = requests.get(f"{BASE_URL}/jobs/{job_id}")

        if response.status_code == 200:
            result = response.json()
            print(f"✓ 查询任务状态成功")
            print(f"  Job ID: {result.get('job_id')}")
            print(f"  Status: {result.get('status')}")
            print(f"  Backend: {result.get('backend')}")
            print(f"  Doc Type: {result.get('doc_type')}")
            print(f"  Created At: {result.get('created_at')}")
            return result
        else:
            print(f"✗ 查询任务状态失败: {response.status_code}")
            print(f"  Response: {response.text}")
            return None

    except Exception as e:
        print(f"✗ 请求异常: {str(e)}")
        return None


def test_batch_ingest():
    """测试批量上传接口"""
    print(f"\n=== 测试批量上传接口 ===")

    # 创建测试目录和文件
    test_dir = "test_batch_dir"
    os.makedirs(test_dir, exist_ok=True)

    # 创建多个测试文件
    for i in range(3):
        file_path = os.path.join(test_dir, f"batch_test_{i}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"这是批量测试文件 {i}\n包含一些示例内容用于测试。")

    payload = {
        "business_id": "test_batch_business_001",
        "directory_path": os.path.abspath(test_dir),
        "file_patterns": ["*.txt"]
    }

    try:
        response = requests.post(
            f"{BASE_URL}/batch/ingest",
            json=payload
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✓ 批量上传请求成功")
            print(f"  Batch ID: {result.get('batch_id')}")
            print(f"  Total Jobs: {result.get('total')}")
            for job in result.get('jobs', []):
                print(f"    - File: {job.get('file')}, Job ID: {job.get('job_id')}")
            return result
        else:
            print(f"✗ 批量上传失败: {response.status_code}")
            print(f"  Response: {response.text}")
            return None

    except Exception as e:
        print(f"✗ 请求异常: {str(e)}")
        return None
    finally:
        # 清理测试文件
        import shutil
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)


def test_review_job(job_id):
    """测试审核任务接口"""
    if not job_id:
        print("⚠️  无效的 Job ID")
        return

    print(f"\n=== 测试审核任务接口 (Job ID: {job_id}) ===")

    # 先查询当前状态
    job_info = test_get_job_status(job_id)
    if not job_info:
        return

    # 提交审核请求 (approve)
    payload = {
        "action": "approve",
        "comment": "测试审核通过"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/jobs/{job_id}/review",
            json=payload,
            params={"operator": "test_admin"}
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✓ 审核任务成功")
            print(f"  Job ID: {result.get('job_id')}")
            print(f"  New Status: {result.get('status')}")
            print(f"  Reviewed By: {result.get('reviewed_by')}")
            print(f"  Reviewed At: {result.get('reviewed_at')}")
            return result
        else:
            print(f"✗ 审核任务失败: {response.status_code}")
            print(f"  Response: {response.text}")
            return None

    except Exception as e:
        print(f"✗ 请求异常: {str(e)}")
        return None


def test_callback(job_id):
    """测试回调接口"""
    if not job_id:
        print("⚠️  无效的 Job ID")
        return

    print(f"\n=== 测试回调接口 (Job ID: {job_id}) ===")

    payload = {
        "status": "success",
        "message": "处理完成",
        "result": {"processed_pages": 10, "chunks": 2}
    }

    try:
        response = requests.post(
            f"{BASE_URL}/callback/{job_id}",
            json=payload
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✓ 回调接口调用成功")
            print(f"  Received: {result.get('received')}")
            return result
        else:
            print(f"✗ 回调接口调用失败: {response.status_code}")
            print(f"  Response: {response.text}")
            return None

    except Exception as e:
        print(f"✗ 请求异常: {str(e)}")
        return None


def main():
    """主测试函数"""
    print("🚀 开始 KB Service API 测试演示")
    print(f"📍 Base URL: {BASE_URL}")

    # 1. 测试文档上传
    job_id = test_ingest_document()

    # 等待一段时间让任务处理
    if job_id:
        print("\n⏳ 等待任务处理...")
        time.sleep(2)

        # 2. 测试查询任务状态
        test_get_job_status(job_id)

        # 3. 测试审核功能
        test_review_job(job_id)

        # 4. 测试回调功能
        test_callback(job_id)

    # 5. 测试批量上传
    test_batch_ingest()

    # 清理测试文件
    if os.path.exists(TEST_FILE_PATH):
        os.remove(TEST_FILE_PATH)

    print("\n🎉 所有测试完成!")


if __name__ == "__main__":
    main()