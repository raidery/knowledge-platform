#!/bin/bash

# ============================================
# RAG知识问答管理平台 开发服务管理脚本
# ============================================

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="$BASE_DIR/.dev_pids"

mkdir -p "$PID_DIR"

BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查进程是否在运行
is_running() {
    local pid=$1
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# 启动后端服务
start_backend() {
    if [ -f "$BACKEND_PID_FILE" ] && is_running "$(cat "$BACKEND_PID_FILE")"; then
        log_warn "后端服务已在运行 (PID: $(cat "$BACKEND_PID_FILE"))"
        return 1
    fi

    log_info "启动后端服务..."
    cd "$BASE_DIR" && python run.py > "$PID_DIR/backend.log" 2>&1 &
    local pid=$!
    echo $pid > "$BACKEND_PID_FILE"
    sleep 2

    if is_running "$pid"; then
        log_info "后端服务已启动 (PID: $pid, 端口: 9999)"
    else
        log_error "后端服务启动失败，请查看日志: $PID_DIR/backend.log"
        rm -f "$BACKEND_PID_FILE"
        return 1
    fi
}

# 启动前端服务
start_frontend() {
    if [ -f "$FRONTEND_PID_FILE" ] && is_running "$(cat "$FRONTEND_PID_FILE")"; then
        log_warn "前端服务已在运行 (PID: $(cat "$FRONTEND_PID_FILE"))"
        return 1
    fi

    log_info "启动前端服务..."
    cd "$BASE_DIR/web" && pnpm dev > "$PID_DIR/frontend.log" 2>&1 &
    local pid=$!
    echo $pid > "$FRONTEND_PID_FILE"
    sleep 3

    if is_running "$pid"; then
        log_info "前端服务已启动 (PID: $pid)"
    else
        log_error "前端服务启动失败，请查看日志: $PID_DIR/frontend.log"
        rm -f "$FRONTEND_PID_FILE"
        return 1
    fi
}

# 停止后端服务
stop_backend() {
    if [ -f "$BACKEND_PID_FILE" ]; then
        local pid=$(cat "$BACKEND_PID_FILE")
        if is_running "$pid"; then
            log_info "停止后端服务 (PID: $pid)..."
            kill "$pid" 2>/dev/null
            sleep 1
            if is_running "$pid"; then
                kill -9 "$pid" 2>/dev/null
            fi
            log_info "后端服务已停止"
        else
            log_warn "后端服务未在运行"
        fi
        rm -f "$BACKEND_PID_FILE"
    else
        log_warn "未找到后端服务PID文件"
    fi

    # 额外清理：杀死占用9999端口的进程
    local backend_pids=$(lsof -ti:9999 2>/dev/null)
    if [ -n "$backend_pids" ]; then
        log_info "清理残留的后端进程..."
        echo "$backend_pids" | xargs kill -9 2>/dev/null
    fi
}

# 停止前端服务
stop_frontend() {
    if [ -f "$FRONTEND_PID_FILE" ]; then
        local pid=$(cat "$FRONTEND_PID_FILE")
        if is_running "$pid"; then
            log_info "停止前端服务 (PID: $pid)..."
            kill "$pid" 2>/dev/null
            sleep 1
            if is_running "$pid"; then
                kill -9 "$pid" 2>/dev/null
            fi
            log_info "前端服务已停止"
        else
            log_warn "前端服务未在运行"
        fi
        rm -f "$FRONTEND_PID_FILE"
    else
        log_warn "未找到前端服务PID文件"
    fi

    # 额外清理：杀死占用5173端口的node进程
    local frontend_pids=$(lsof -ti:5173 2>/dev/null)
    if [ -n "$frontend_pids" ]; then
        log_info "清理残留的前端进程..."
        echo "$frontend_pids" | xargs kill -9 2>/dev/null
    fi
}

# 查看服务状态
status() {
    echo "=========================================="
    echo "         RAG知识问答管理平台 服务状态"
    echo "=========================================="
    echo ""

    # 后端状态
    if [ -f "$BACKEND_PID_FILE" ]; then
        local backend_pid=$(cat "$BACKEND_PID_FILE")
        if is_running "$backend_pid"; then
            echo -e "后端服务: ${GREEN}运行中${NC} (PID: $backend_pid, 端口: 9999)"
        else
            echo -e "后端服务: ${RED}已停止${NC} (PID文件过期)"
        fi
    else
        echo -e "后端服务: ${YELLOW}未启动${NC}"
    fi

    # 前端状态
    if [ -f "$FRONTEND_PID_FILE" ]; then
        local frontend_pid=$(cat "$FRONTEND_PID_FILE")
        if is_running "$frontend_pid"; then
            echo -e "前端服务: ${GREEN}运行中${NC} (PID: $frontend_pid, 端口: 5173)"
        else
            echo -e "前端服务: ${RED}已停止${NC} (PID文件过期)"
        fi
    else
        echo -e "前端服务: ${YELLOW}未启动${NC}"
    fi

    echo ""
    echo "日志目录: $PID_DIR"
    echo "  - backend.log"
    echo "  - frontend.log"
}

# 主函数
case "${1:-}" in
    start)
        start_backend
        start_frontend
        echo ""
        log_info "所有服务启动完成!"
        echo "  - 后端: http://localhost:9999"
        echo "  - 前端: http://localhost:5173"
        ;;
    stop)
        stop_backend
        stop_frontend
        rm -rf "$PID_DIR"
        log_info "所有服务已停止"
        ;;
    restart)
        log_info "重启服务..."
        stop_backend
        stop_frontend
        sleep 2
        start_backend
        start_frontend
        log_info "重启完成"
        ;;
    status)
        status
        ;;
    backend)
        case "${2:-}" in
            start)
                start_backend
                ;;
            stop)
                stop_backend
                ;;
            *)
                echo "用法: $0 backend {start|stop}"
                exit 1
                ;;
        esac
        ;;
    frontend)
        case "${2:-}" in
            start)
                start_frontend
                ;;
            stop)
                stop_frontend
                ;;
            *)
                echo "用法: $0 frontend {start|stop}"
                exit 1
                ;;
        esac
        ;;
    *)
        echo "=========================================="
        echo "  RAG知识问答管理平台 开发服务管理脚本"
        echo "=========================================="
        echo ""
        echo "用法: $0 {command}"
        echo ""
        echo "命令:"
        echo "  start       启动所有服务 (后端 + 前端)"
        echo "  stop        停止所有服务"
        echo "  restart     重启所有服务"
        echo "  status      查看服务状态"
        echo "  backend     后端单独操作"
        echo "    start     启动后端"
        echo "    stop      停止后端"
        echo "  frontend    前端单独操作"
        echo "    start     启动前端"
        echo "    stop      停止前端"
        echo ""
        echo "示例:"
        echo "  $0 start      # 启动所有服务"
        echo "  $0 stop       # 停止所有服务"
        echo "  $0 restart    # 重启所有服务"
        echo "  $0 status     # 查看状态"
        exit 1
        ;;
esac
