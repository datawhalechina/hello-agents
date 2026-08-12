#!/bin/bash
# ============================================================
# Restart script for GuessWhoAmI
# Backend:  FastAPI on port 8000
# Frontend: Python http.server on port 3000
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
# python解释器路径
VENV_PYTHON="/home/afei/hello_agent_venv/bin/python"

BACKEND_PORT=8000
FRONTEND_PORT=3000

LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

# ── Color helpers ──────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }

# ── Kill processes on a given port ─────────────────────────
kill_port() {
    local port=$1
    local pids
    pids=$(lsof -ti tcp:"$port" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill -9 2>/dev/null || true
        warn "Killed existing process(es) on port $port: $pids"
    fi
}

# ── Also kill by process name pattern ──────────────────────
kill_pattern() {
    local pattern=$1
    local pids
    pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill -9 2>/dev/null || true
        warn "Killed process(es) matching '$pattern': $pids"
    fi
}

# ── Wait for a port to become available ────────────────────
wait_for_port() {
    local port=$1
    local name=$2
    local max_wait=15
    local count=0
    while ! lsof -ti tcp:"$port" >/dev/null 2>&1; do
        sleep 1
        count=$((count + 1))
        if [ "$count" -ge "$max_wait" ]; then
            error "$name failed to start on port $port within ${max_wait}s"
            error "Check log: $LOG_DIR/${name,,}.log"
            exit 1
        fi
    done
    info "$name is up on port $port ✓"
}

# ══════════════════════════════════════════════════════════
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║      GuessWhoAmI — Restart Script           ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── Step 1: Stop existing services ────────────────────────
info "Stopping existing services..."
kill_port "$BACKEND_PORT"
kill_port "$FRONTEND_PORT"
kill_pattern "main.py"
kill_pattern "GuessWhoAmI/frontend"
sleep 1

# ── Step 2: Start backend ──────────────────────────────────
info "Starting backend (port $BACKEND_PORT)..."
# backend.log is managed by Python's FileHandler; stdout/stderr go to /dev/null
cd "$BACKEND_DIR"
nohup "$VENV_PYTHON" main.py > /dev/null 2>&1 &
BACKEND_PID=$!
info "Backend PID: $BACKEND_PID"

wait_for_port "$BACKEND_PORT" "Backend"

# ── Step 3: Start frontend ─────────────────────────────────
info "Starting frontend (port $FRONTEND_PORT)..."
> "$FRONTEND_LOG"  # clear log on each restart
cd "$FRONTEND_DIR"
nohup "$VENV_PYTHON" -m http.server "$FRONTEND_PORT" > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
info "Frontend PID: $FRONTEND_PID"

wait_for_port "$FRONTEND_PORT" "Frontend"

# ── Done ───────────────────────────────────────────────────
echo ""
echo -e "${GREEN}✅ All services started successfully!${NC}"
echo ""
echo "  🔧 Backend  → http://localhost:$BACKEND_PORT"
echo "  🔧 API Docs → http://localhost:$BACKEND_PORT/docs"
echo "  🌐 Frontend → http://localhost:$FRONTEND_PORT"
echo ""
echo "  📄 Logs:"
echo "     Backend  : $BACKEND_LOG"
echo "     Frontend : $FRONTEND_LOG"
echo ""
echo "  To stop all services:"
echo "     kill $BACKEND_PID $FRONTEND_PID"
echo "  Or run:  bash $PROJECT_DIR/stop.sh"
echo ""
