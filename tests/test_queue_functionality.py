#!/usr/bin/env python3
"""
测试 KB Service 队列功能的脚本
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


def create_test_files():
    """创建不同大小的测试文件"""
    # 创建小文件 (< 1MB)
    small_file = "test_small.txt"
    with open(small_file, "w", encoding="utf-8") as f:
        f.write("这是一个小文件测试内容。\n" * 100)  # 约 3KB

    # 创建大文件 (> 1MB)
    large_file = "test_large.txt"
    with open(large_file, "w", encoding="utf-8") as f:
        f.write("这是一个大文件测试内容。\n" * 50000)  # 约 1.2MB

    print(f"✓ 创建测试文件:")
    print(f"  小文件: {small_file} ({os.path.getsize(small_file)} bytes)")
    print(f"  大文件: {large_file} ({os.path.getsize(large_file)} bytes)")

    return small_file, large_file


def test_ingest_rag1_docx():
    """测试大文件 rag-1.docx 的摄入（应使用队列异步处理）"""
    print(f"\n=== 测试大文件 rag-1.docx ===")

    file_path = "tests/rag-1.docx"
    #file_path = "/tmp/test_document1.txt"
    if not os.path.exists(file_path):
        print(f"✗ 文件不存在: {file_path}")
        return None

    file_size = os.path.getsize(file_path)
    print(f"  文件大小: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")

    with open(file_path, "rb") as f:
        files = {"file": ("rag-1.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        data = {"business_id": "test_rag1_docx", "dataset_id": "2136ae74-ea3f-45d3-90d0-c65fc5257470"}

        try:
            response = requests.post(
                f"{BASE_URL}/ingest",
                files=files,
                data=data
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ 文件摄入请求成功")
                print(f"  Job ID: {result.get('job_id')}")
                print(f"  Status: {result.get('status')}")
                print(f"  Created At: {result.get('created_at')}")

                assert result.get('status') == 'queued', f"大文件应返回 queued，实际: {result.get('status')}"
                print(f"  ✓ 队列逻辑验证通过 (大文件走队列)")

                return result.get('job_id')
            else:
                print(f"✗ 文件摄入失败: {response.status_code}")
                print(f"  Response: {response.text}")
                return None

        except Exception as e:
            print(f"✗ 请求异常: {str(e)}")
            return None


def test_ingest_with_queue(file_path, business_id):
    """测试文档摄入接口（自动使用队列）"""
    print(f"\n=== 测试文件摄入: {file_path} ===")

    file_size = os.path.getsize(file_path)
    print(f"  文件大小: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")

    with open(file_path, "rb") as f:
        files = {"file": (file_path, f, "text/plain")}
        data = {"business_id": business_id}

        try:
            response = requests.post(
                f"{BASE_URL}/ingest",
                files=files,
                data=data
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ 文件摄入请求成功")
                print(f"  Job ID: {result.get('job_id')}")
                print(f"  Status: {result.get('status')}")
                print(f"  Created At: {result.get('created_at')}")

                # 验证队列逻辑
                if file_size > 1024 * 1024:  # > 1MB
                    assert result.get('status') == 'queued', f"大文件应返回 queued，实际: {result.get('status')}"
                    print(f"  ✓ 队列逻辑验证通过 (>1MB 走队列)")
                else:
                    assert result.get('status') in ['completed', 'processing'], f"小文件应同步完成，实际: {result.get('status')}"
                    print(f"  ✓ 同步逻辑验证通过 (≤1MB 同步处理)")

                return result.get('job_id')
            else:
                print(f"✗ 文件摄入失败: {response.status_code}")
                print(f"  Response: {response.text}")
                return None

        except Exception as e:
            print(f"✗ 请求异常: {str(e)}")
            return None


def test_queue_monitoring():
    """测试队列监控功能"""
    print(f"\n=== 测试队列监控 ===")

    try:
        # 查看所有队列信息
        response = requests.get(f"{BASE_URL}/monitor/queues")

        if response.status_code == 200:
            result = response.json()
            print(f"✓ 队列监控请求成功")
            for queue_name, queue_info in result.items():
                print(f"  队列 '{queue_name}': {queue_info['length']} 个任务")
                for job in queue_info['jobs'][:3]:  # 只显示前3个任务
                    print(f"    - Job ID: {job.get('id')}, Status: {job.get('status')}")
            return result
        else:
            print(f"✗ 队列监控请求失败: {response.status_code}")
            print(f"  Response: {response.text}")
            return None

    except Exception as e:
        print(f"✗ 请求异常: {str(e)}")
        return None


def main():
    """主测试函数"""
    print("🚀 开始测试 KB Service 队列功能")
    print(f"📍 Base URL: {BASE_URL}")

    # 1. 测试大文件 rag-1.docx（应使用队列异步处理）
    rag1_job_id = test_ingest_rag1_docx()

    # # 2. 创建测试文件
    #small_file, large_file = create_test_files()

    # # 3. 测试小文件摄入（应同步处理）
    #small_job_id = test_ingest_with_queue(small_file, "test_business_small")

    # # 3. 测试大文件摄入（应使用队列异步处理）
    # large_job_id = test_ingest_with_queue(large_file, "test_business_large")

    # # 4. 等待一段时间让队列任务处理
    # print("\n⏳ 等待队列任务处理...")
    # time.sleep(5)

    # # 5. 测试队列监控
    # test_queue_monitoring()

    # # 6. 清理测试文件
    # for file_path in [small_file, large_file]:
    #     if os.path.exists(file_path):
    #         os.remove(file_path)
    #         print(f"✓ 清理测试文件: {file_path}")

    # print("\n🎉 队列功能测试完成!")


if __name__ == "__main__":
    main()