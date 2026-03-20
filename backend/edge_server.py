"""
edge_server.py
Edge (cache) server. Sits between clients and the origin.
Run on port 8001 or 8002 (pass --port argument).
"""

import sys
import time
import logging
import argparse
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import httpx
import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.cdn_config import (
    ORIGIN_HOST, ORIGIN_PORT, CACHE_DIR, CACHE_TTL_SECONDS,
    MAX_CACHE_SIZE_MB, LOG_DIR, LOG_FILE, ALLOWED_EXTENSIONS, RATE_LIMIT
)
from backend.cache_manager import CacheManager

# ── Args ───────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=8001)
parser.add_argument("--edge-id", type=str, default="edge-1")
args, _ = parser.parse_known_args()

EDGE_ID   = args.edge_id
EDGE_PORT = args.port
EDGE_CACHE_DIR = CACHE_DIR / EDGE_ID

# ── Logging ────────────────────────────────────────────────────
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format=f"%(asctime)s [{EDGE_ID.upper()}] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(f"cdn.{EDGE_ID}")

# ── App & Rate Limiter ─────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT])
app = FastAPI(title=f"CDN Edge Server ({EDGE_ID})", version="1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Cache & Stats ──────────────────────────────────────────────
cache = CacheManager(EDGE_CACHE_DIR, ttl=CACHE_TTL_SECONDS, max_size_mb=MAX_CACHE_SIZE_MB)
stats = {"requests": 0, "cache_hits": 0, "cache_misses": 0, "bytes_served": 0, "start_time": time.time()}


@app.middleware("http")
async def track_requests(request: Request, call_next):
    stats["requests"] += 1
    response = await call_next(request)
    return response


@app.get("/cdn/{file_path:path}")
@limiter.limit(RATE_LIMIT)
async def serve(request: Request, file_path: str):
    """Main CDN delivery endpoint."""
    # 1️⃣ Check edge cache
    cached = await cache.get(file_path)
    if cached:
        data, content_type = cached
        stats["cache_hits"] += 1
        stats["bytes_served"] += len(data)
        logger.info(f"CACHE HIT  {file_path}")
        return Response(
            content=data,
            media_type=content_type,
            headers={
                "X-Cache": "HIT",
                "X-Edge-Server": EDGE_ID,
                "X-Cache-TTL": str(CACHE_TTL_SECONDS),
            },
        )

    # 2️⃣ Fetch from origin
    stats["cache_misses"] += 1
    origin_url = f"http://{ORIGIN_HOST}:{ORIGIN_PORT}/files/{file_path}"
    logger.info(f"CACHE MISS {file_path} → fetching from origin")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            origin_resp = await client.get(origin_url)
        if origin_resp.status_code == 404:
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        if origin_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Origin server error")
    except httpx.RequestError as exc:
        logger.error(f"Origin unreachable: {exc}")
        raise HTTPException(status_code=503, detail="Origin server unreachable")

    data = origin_resp.content
    content_type = origin_resp.headers.get("content-type", "application/octet-stream")

    # 3️⃣ Cache & return
    await cache.put(file_path, data, content_type)
    stats["bytes_served"] += len(data)
    logger.info(f"SERVED     {file_path}  ({len(data)//1024} KB)")

    return Response(
        content=data,
        media_type=content_type,
        headers={
            "X-Cache": "MISS",
            "X-Edge-Server": EDGE_ID,
            "X-Cache-TTL": str(CACHE_TTL_SECONDS),
        },
    )


@app.delete("/cache")
async def clear_cache():
    """Clear entire edge cache."""
    await cache.clear_all()
    logger.info(f"Cache cleared by API request")
    return {"status": "cleared", "edge": EDGE_ID}


@app.delete("/cache/{file_path:path}")
async def evict_file(file_path: str):
    """Evict a specific file from cache."""
    removed = await cache.delete(file_path)
    return {"evicted": removed, "path": file_path, "edge": EDGE_ID}


@app.get("/stats")
async def get_stats():
    uptime = round(time.time() - stats["start_time"])
    hit_rate = (
        round(stats["cache_hits"] / max(stats["cache_hits"] + stats["cache_misses"], 1) * 100, 1)
    )
    return {
        "edge_id": EDGE_ID,
        "port": EDGE_PORT,
        "uptime_seconds": uptime,
        "requests": stats["requests"],
        "cache_hits": stats["cache_hits"],
        "cache_misses": stats["cache_misses"],
        "hit_rate_pct": hit_rate,
        "bytes_served_mb": round(stats["bytes_served"] / (1024 * 1024), 2),
        "cache": cache.stats(),
    }


@app.get("/health")
async def health():
    return {"status": "up", "server": "edge", "id": EDGE_ID, "port": EDGE_PORT}


if __name__ == "__main__":
    logger.info(f"Starting Edge Server [{EDGE_ID}] on port {EDGE_PORT}")
    uvicorn.run("backend.edge_server:app", host="0.0.0.0", port=EDGE_PORT, reload=False)
