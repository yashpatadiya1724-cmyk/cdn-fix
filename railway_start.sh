#!/bin/bash
# ──────────────────────────────────────────────
#  Railway Startup Script for CDN System
# ──────────────────────────────────────────────

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Railway provides PORT dynamically — dashboard listens on it
DASHBOARD_PORT=${PORT:-8090}

echo "[CDN] Railway deployment starting..."
echo "[CDN] Dashboard will bind to PORT=$DASHBOARD_PORT"

# Create required directories
mkdir -p logs cache/edge-1 cache/edge-2 static/images static/css static/js static/videos

export PYTHONPATH="$ROOT"

# Start Origin Server on internal port 8000
echo "[CDN] Starting Origin Server (port 8000)..."
python3 -m backend.origin_server &
ORIGIN_PID=$!

sleep 1

# Start Edge Server 1 on internal port 8001
echo "[CDN] Starting Edge Server 1 (port 8001)..."
python3 -m backend.edge_server --port 8001 --edge-id edge-1 &
EDGE1_PID=$!

sleep 0.5

# Start Edge Server 2 on internal port 8002
echo "[CDN] Starting Edge Server 2 (port 8002)..."
python3 -m backend.edge_server --port 8002 --edge-id edge-2 &
EDGE2_PID=$!

sleep 0.5

# Start Load Balancer on internal port 8081
echo "[CDN] Starting Load Balancer (port 8081)..."
python3 -m backend.load_balancer &
LB_PID=$!

sleep 0.5

# Start Dashboard on Railway's PORT (public-facing)
echo "[CDN] Starting Dashboard on PORT=$DASHBOARD_PORT ..."
python3 -m backend.dashboard --port "$DASHBOARD_PORT" &
DASH_PID=$!

echo "[CDN] All services launched!"
echo "[CDN]   Origin     → http://localhost:8000"
echo "[CDN]   Edge 1     → http://localhost:8001"
echo "[CDN]   Edge 2     → http://localhost:8002"
echo "[CDN]   LB         → http://localhost:8081"
echo "[CDN]   Dashboard  → 0.0.0.0:$DASHBOARD_PORT  (public)"

# Trap and clean up on exit
trap "echo '[CDN] Shutting down...'; kill $ORIGIN_PID $EDGE1_PID $EDGE2_PID $LB_PID $DASH_PID 2>/dev/null" EXIT INT TERM

wait $DASH_PID
