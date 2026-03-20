"""
load_balancer.py
Round-robin + health-aware load balancer. Exposed on port 8081.
Distributes CDN requests across healthy edge servers.
"""

import sys
import time
import asyncio
import logging
from pathlib import Path
from itertools import cycle
from typing import List, Dict
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, JSONResponse
import httpx
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.cdn_config import EDGE_SERVERS, LOG_DIR, LOG_FILE

# ── Logging ────────────────────────────────────────────────────
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [LB] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("cdn.lb")

# ── State ──────────────────────────────────────────────────────
app = FastAPI(title="CDN Load Balancer", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

server_pool: List[Dict] = [
    {**s, "healthy": True, "requests": 0, "errors": 0, "last_check": 0.0}
    for s in EDGE_SERVERS
]
_rr = cycle(range(len(server_pool)))
lb_stats = {"total_requests": 0, "total_errors": 0, "start_time": time.time()}


# ── Health checker ──────────────────────────────────────────────
async def health_check_loop():
    while True:
        await asyncio.sleep(10)
        for srv in server_pool:
            url = f"http://{srv['host']}:{srv['port']}/health"
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    r = await client.get(url)
                srv["healthy"] = r.status_code == 200
            except Exception:
                srv["healthy"] = False
            srv["last_check"] = time.time()
            logger.debug(f"Health {srv['id']}: {'UP' if srv['healthy'] else 'DOWN'}")


@app.on_event("startup")
async def startup():
    asyncio.create_task(health_check_loop())
    logger.info("Load Balancer started. Health checks every 10 s.")


# ── Request routing ─────────────────────────────────────────────
def pick_server() -> Dict:
    """Round-robin over healthy servers."""
    healthy = [s for s in server_pool if s["healthy"]]
    if not healthy:
        raise HTTPException(status_code=503, detail="No healthy edge servers")
    # Simple round-robin within healthy pool
    healthy.sort(key=lambda s: s["requests"])
    return healthy[0]


@app.get("/cdn/{file_path:path}")
async def proxy(request: Request, file_path: str):
    """Forward request to an edge server."""
    lb_stats["total_requests"] += 1
    srv = pick_server()
    srv["requests"] += 1
    target = f"http://{srv['host']}:{srv['port']}/cdn/{file_path}"
    logger.info(f"→ {srv['id']}  {file_path}")

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(target)
    except httpx.RequestError as exc:
        srv["errors"] += 1
        srv["healthy"] = False
        lb_stats["total_errors"] += 1
        logger.error(f"Edge {srv['id']} failed: {exc}")
        raise HTTPException(status_code=503, detail="Edge server error")

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/octet-stream"),
        headers={
            "X-Routed-To": srv["id"],
            "X-Cache": resp.headers.get("X-Cache", "UNKNOWN"),
        },
    )


@app.delete("/cache")
async def clear_all_caches():
    """Broadcast cache clear to all edge servers."""
    results = []
    async with httpx.AsyncClient(timeout=5.0) as client:
        for srv in server_pool:
            url = f"http://{srv['host']}:{srv['port']}/cache"
            try:
                r = await client.delete(url)
                results.append({"edge": srv["id"], "status": "cleared"})
            except Exception as e:
                results.append({"edge": srv["id"], "status": "error", "detail": str(e)})
    return {"results": results}


@app.get("/stats")
async def stats():
    """Aggregate stats from all edge servers."""
    edge_stats = []
    async with httpx.AsyncClient(timeout=5.0) as client:
        for srv in server_pool:
            url = f"http://{srv['host']}:{srv['port']}/stats"
            try:
                r = await client.get(url)
                edge_stats.append(r.json())
            except Exception:
                edge_stats.append({"edge_id": srv["id"], "error": "unreachable"})

    uptime = round(time.time() - lb_stats["start_time"])
    return {
        "load_balancer": {
            "uptime_seconds": uptime,
            "total_requests": lb_stats["total_requests"],
            "total_errors": lb_stats["total_errors"],
        },
        "servers": [
            {
                "id": s["id"],
                "port": s["port"],
                "healthy": s["healthy"],
                "requests_routed": s["requests"],
                "errors": s["errors"],
            }
            for s in server_pool
        ],
        "edge_details": edge_stats,
    }


@app.get("/health")
async def health():
    healthy = sum(1 for s in server_pool if s["healthy"])
    return {"status": "up", "server": "load_balancer", "healthy_edges": healthy}


if __name__ == "__main__":
    logger.info("Starting Load Balancer on port 8081")
    uvicorn.run("backend.load_balancer:app", host="0.0.0.0", port=8081, reload=False)
