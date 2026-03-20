"""
origin_server.py
The master storage server. Serves raw static files from the /static directory.
Run on port 8000.
"""

import sys
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ── Setup paths ────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.cdn_config import ORIGIN_STATIC_DIR, LOG_DIR, LOG_FILE, ALLOWED_EXTENSIONS

# ── Logging ────────────────────────────────────────────────────
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ORIGIN] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("cdn.origin")

# ── App ────────────────────────────────────────────────────────
app = FastAPI(title="CDN Origin Server", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

request_log = []  # simple in-memory request history


@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    entry = {
        "time": __import__("time").strftime("%H:%M:%S"),
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "client": request.client.host if request.client else "unknown",
    }
    request_log.append(entry)
    if len(request_log) > 500:
        request_log.pop(0)
    logger.info(f"{request.method} {request.url.path} → {response.status_code}")
    return response


@app.get("/files/{file_path:path}")
async def serve_file(file_path: str):
    """Serve a file from the static directory."""
    full_path = ORIGIN_STATIC_DIR / file_path
    if not full_path.exists() or not full_path.is_file():
        logger.warning(f"NOT FOUND: {file_path}")
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    suffix = full_path.suffix.lower()
    media_type = ALLOWED_EXTENSIONS.get(suffix, "application/octet-stream")
    logger.info(f"SERVING: {file_path} ({media_type})")
    return FileResponse(full_path, media_type=media_type)


@app.get("/list")
async def list_files():
    """List all available files on the origin server."""
    files = []
    for f in ORIGIN_STATIC_DIR.rglob("*"):
        if f.is_file():
            rel = f.relative_to(ORIGIN_STATIC_DIR)
            files.append({
                "path": str(rel),
                "size_kb": round(f.stat().st_size / 1024, 1),
                "type": ALLOWED_EXTENSIONS.get(f.suffix.lower(), "unknown"),
            })
    return {"origin": "up", "file_count": len(files), "files": files}


@app.get("/health")
async def health():
    return {"status": "up", "server": "origin", "port": 8000}


@app.get("/logs")
async def get_logs():
    return {"logs": request_log[-100:]}


if __name__ == "__main__":
    logger.info("Starting Origin Server on port 8000")
    uvicorn.run("backend.origin_server:app", host="0.0.0.0", port=8000, reload=False)
