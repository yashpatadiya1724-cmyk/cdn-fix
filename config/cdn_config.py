# cdn_config.py — Central configuration for the CDN system

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Origin Server ──────────────────────────────────────────────
ORIGIN_HOST = os.getenv("ORIGIN_HOST", "127.0.0.1")
ORIGIN_PORT = int(os.getenv("ORIGIN_PORT", 8000))
ORIGIN_STATIC_DIR = BASE_DIR / "static"

# ── Edge Servers ───────────────────────────────────────────────
EDGE_SERVERS = [
    {"id": "edge-1", "host": "127.0.0.1", "port": 8001},
    {"id": "edge-2", "host": "127.0.0.1", "port": 8002},
]

# ── Cache ──────────────────────────────────────────────────────
CACHE_DIR = BASE_DIR / "cache"
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL", 300))   # 5 min default
MAX_CACHE_SIZE_MB = int(os.getenv("MAX_CACHE_MB", 500))

# ── Logging ────────────────────────────────────────────────────
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "cdn.log"

# ── Rate Limiting ──────────────────────────────────────────────
RATE_LIMIT = os.getenv("RATE_LIMIT", "60/minute")

# ── MIME types we serve ────────────────────────────────────────
ALLOWED_EXTENSIONS = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
    ".css": "text/css", ".js": "application/javascript",
    ".mp4": "video/mp4", ".webm": "video/webm",
    ".woff": "font/woff", ".woff2": "font/woff2",
    ".html": "text/html", ".txt": "text/plain", ".json": "application/json",
}
