#!/bin/bash
# PaperGraph(知脉) 一键启动：后端 + 前端

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

# shellcheck source=ports.env
source "$ROOT/ports.env"

cleanup() {
    echo ""
    echo "正在关闭服务..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "已关闭。"
}
trap cleanup EXIT INT TERM

echo "============================================"
echo "  PaperGraph(知脉) 启动中..."
echo "============================================"

cd "$ROOT/backend"
echo "→ 后端 http://localhost:${BACKEND_PORT}"
export PORT="$BACKEND_PORT"
PAPERGRAPH_UVICORN_RELOAD=0 python run.py &
BACKEND_PID=$!

cd "$ROOT/frontend"
export VITE_BACKEND_PORT="$BACKEND_PORT" VITE_DEV_PORT="$FRONTEND_PORT"
echo "→ 前端 http://127.0.0.1:${FRONTEND_PORT}"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "  前端: http://127.0.0.1:${FRONTEND_PORT}"
echo "  后端: http://127.0.0.1:${BACKEND_PORT}"
echo "  健康: http://127.0.0.1:${BACKEND_PORT}/health"
echo "  Ctrl+C 停止"
echo "============================================"

wait
