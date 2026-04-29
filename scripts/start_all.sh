#!/bin/bash
# 启动 KB Service 和 RQ Dashboard 的脚本

# 返回项目根目录
cd "$(dirname "$0")/.." || exit

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

# 设置 PYTHONPATH 以便找到应用
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

echo "🚀 启动 KB Service、RQ Dashboard 和 RQ Worker..."

# 启动主应用 (在后台运行)
echo "🔧 启动 KB Service..."
python run.py &
MAIN_APP_PID=$!

# 等待几秒钟让主应用启动
sleep 3

# 启动 RQ Dashboard (在后台运行)
echo "📊 启动 RQ Dashboard..."
echo "   Redis URL: ${REDIS_URL}"
echo "   Port: ${RQ_DASHBOARD_PORT}"
rq-dashboard-fast --redis-url "${REDIS_URL}" --port "${RQ_DASHBOARD_PORT}" &
DASHBOARD_PID=$!

# 启动 RQ Worker
echo "👷 启动 RQ Worker..."
echo "   监听队列: default, ingest, batch"
rq worker default ingest batch &
WORKER_PID=$!

# 显示访问信息
echo ""
echo "✅ 服务启动完成!"
echo "   KB Service API: http://localhost:9999/docs"
echo "   RQ Dashboard: http://localhost:${RQ_DASHBOARD_PORT}"
echo "   RQ Worker PID: ${WORKER_PID}"
echo ""
echo "🔄 按 Ctrl+C 停止所有服务"

# 等待任一进程结束
wait $MAIN_APP_PID $DASHBOARD_PID $WORKER_PID

# 如果任一进程结束，则终止其他进程
kill $MAIN_APP_PID 2>/dev/null
kill $DASHBOARD_PID 2>/dev/null
kill $WORKER_PID 2>/dev/null

echo ""
echo "🛑 所有服务已停止"
