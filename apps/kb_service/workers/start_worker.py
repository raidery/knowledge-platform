#!/usr/bin/env python3
"""
KB Service Worker 启动脚本
用于启动处理队列任务的 RQ Worker
"""

import sys
import os

# 解决 macOS fork + Objective-C 安全问题
os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apps.kb_service.workers.tasks import start_worker


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="启动 KB Service Worker")
    parser.add_argument(
        "--queues",
        nargs="+",
        default=["default", "ingest", "batch"],
        help="要监听的队列名称 (默认: default ingest batch)"
    )

    args = parser.parse_args()

    print(f"🚀 启动 KB Service Worker...")
    print(f"📡 监听队列: {', '.join(args.queues)}")

    try:
        start_worker(queues=args.queues)
    except KeyboardInterrupt:
        print("\n🛑 Worker 已停止")
    except Exception as e:
        print(f"❌ Worker 启动失败: {e}")
        sys.exit(1)