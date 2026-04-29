#!/bin/bash
# 启动 RQ Dashboard 和 Worker 的脚本

# 返回项目根目录
cd "$(dirname "$0")/.." || exit

# 解决 macOS fork + Objective-C 安全问题
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

# 加载 .env 文件
set -a
source .env
set +a

# 设置默认值
REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}
REDIS_PASSWORD=${REDIS_PASSWORD:-Pass@1234}
RQ_DASHBOARD_PORT=${RQ_DASHBOARD_PORT:-9090}

# 构建 Redis URL
if [ -z "$REDIS_PASSWORD" ] || [ "$REDIS_PASSWORD" = "None" ]; then
    REDIS_URL="redis://${REDIS_HOST}:${REDIS_PORT}"
else
    REDIS_URL="redis://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}"
fi

echo "🚀 启动 RQ Dashboard..."
echo "📡 Redis URL: ${REDIS_URL}"
echo "📍 Dashboard Port: ${RQ_DASHBOARD_PORT}"

# 启动 rq-dashboard
rq-dashboard-fast --redis-url "${REDIS_URL}" --port "${RQ_DASHBOARD_PORT}" &

echo "✅ RQ Dashboard 已启动在 http://localhost:${RQ_DASHBOARD_PORT}"

# 设置 PYTHONPATH 以便找到应用
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

echo "🚀 启动 RQ Worker..."
echo "📋 监听的队列: default, ingest, batch"

# 启动 RQ worker 监听多个队列
rq worker default ingest batch &
WORKER_PID=$!

echo "✅ RQ Worker 已启动 (PID: ${WORKER_PID})"
echo "📝 按 Ctrl+C 停止所有服务"

# 等待 worker 退出（这样脚本会一直运行直到用户中断）
wait $WORKER_PID
