#!/bin/bash
# ──────────────────────────────────────────────
#  CDN System Startup Script
# ──────────────────────────────────────────────

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'
YELLOW='\033[1;33m'; NC='\033[0m'; BOLD='\033[1m'

log() { echo -e "${CYAN}[CDN]${NC} $1"; }
ok()  { echo -e "${GREEN}[✓]${NC} $1"; }
err() { echo -e "${RED}[✗]${NC} $1"; }

echo ""
echo -e "${BOLD}${CYAN}  ⚡ CDN System Starting...${NC}"
echo "  ─────────────────────────────"

# Ensure venv exists
if [ ! -d "venv" ]; then
  log "Creating virtual environment..."
  python3 -m venv venv
  source venv/bin/activate
  pip install -q -r requirements.txt
  ok "Dependencies installed"
else
  source venv/bin/activate
fi

# Create dirs
mkdir -p logs cache/edge-1 cache/edge-2 static/{images,css,js,videos}

PYTHONPATH="$ROOT"
export PYTHONPATH

# Kill any old instances
pkill -f "origin_server" 2>/dev/null || true
pkill -f "edge_server"   2>/dev/null || true
pkill -f "load_balancer" 2>/dev/null || true
pkill -f "dashboard"     2>/dev/null || true
sleep 0.5

# Start Origin Server
log "Starting Origin Server (port 8000)..."
python3 -m backend.origin_server > logs/origin.log 2>&1 &
ORIGIN_PID=$!
sleep 1
ok "Origin Server started (PID $ORIGIN_PID)"

# Start Edge Servers
log "Starting Edge Server 1 (port 8001)..."
python3 -m backend.edge_server --port 8001 --edge-id edge-1 > logs/edge1.log 2>&1 &
EDGE1_PID=$!
sleep 0.5
ok "Edge Server 1 started (PID $EDGE1_PID)"

log "Starting Edge Server 2 (port 8002)..."
python3 -m backend.edge_server --port 8002 --edge-id edge-2 > logs/edge2.log 2>&1 &
EDGE2_PID=$!
sleep 0.5
ok "Edge Server 2 started (PID $EDGE2_PID)"

# Start Load Balancer
log "Starting Load Balancer (port 8080)..."
python3 -m backend.load_balancer > logs/lb.log 2>&1 &
LB_PID=$!
sleep 0.5
ok "Load Balancer started (PID $LB_PID)"

# Start Dashboard
log "Starting Dashboard (port 8090)..."
python3 -m backend.dashboard > logs/dashboard.log 2>&1 &
DASH_PID=$!
sleep 0.5
ok "Dashboard started (PID $DASH_PID)"

echo ""
echo -e "${BOLD}  ✅ All services running!${NC}"
echo "  ─────────────────────────────"
echo -e "  ${YELLOW}Origin Server  ${NC}→ http://localhost:8000"
echo -e "  ${YELLOW}Edge Server 1  ${NC}→ http://localhost:8001"
echo -e "  ${YELLOW}Edge Server 2  ${NC}→ http://localhost:8002"
echo -e "  ${YELLOW}Load Balancer  ${NC}→ http://localhost:8080"
echo -e "  ${GREEN}Dashboard      ${NC}→ http://localhost:8090  ← Open this!"
echo ""
echo -e "  ${CYAN}Serve a file:${NC}"
echo "  curl http://localhost:8080/cdn/css/styles.css"
echo ""
echo -e "  ${CYAN}Clear cache:${NC}"
echo "  curl -X DELETE http://localhost:8080/cache"
echo ""
echo -e "  Press ${RED}Ctrl+C${NC} to stop all services"
echo ""

# Trap Ctrl+C
trap "echo ''; log 'Shutting down...'; kill $ORIGIN_PID $EDGE1_PID $EDGE2_PID $LB_PID $DASH_PID 2>/dev/null; echo '  Bye!'; exit 0" INT

wait
