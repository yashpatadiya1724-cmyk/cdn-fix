"""
cache_manager.py
Handles local disk cache with TTL expiration and size management.
"""

import hashlib
import json
import time
import shutil
from pathlib import Path
from typing import Optional, Tuple
import aiofiles
import asyncio
import logging

logger = logging.getLogger("cdn.cache")


class CacheManager:
    def __init__(self, cache_dir: Path, ttl: int = 300, max_size_mb: int = 500):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._meta: dict = {}          # key → {expires, size, hits, content_type}
        self._lock = asyncio.Lock()
        self._load_meta()

    # ── Internal helpers ────────────────────────────────────────

    def _key(self, file_path: str) -> str:
        return hashlib.md5(file_path.encode()).hexdigest()

    def _meta_path(self) -> Path:
        return self.cache_dir / "_meta.json"

    def _file_path(self, key: str) -> Path:
        return self.cache_dir / key

    def _load_meta(self):
        p = self._meta_path()
        if p.exists():
            try:
                self._meta = json.loads(p.read_text())
            except Exception:
                self._meta = {}

    def _save_meta(self):
        self._meta_path().write_text(json.dumps(self._meta, indent=2))

    # ── Public API ──────────────────────────────────────────────

    async def get(self, file_path: str) -> Optional[Tuple[bytes, str]]:
        """Return (data, content_type) if cached and not expired, else None."""
        key = self._key(file_path)
        async with self._lock:
            meta = self._meta.get(key)
            if not meta:
                return None
            if time.time() > meta["expires"]:
                await self._evict(key)
                return None
            # Update hit counter
            meta["hits"] = meta.get("hits", 0) + 1
            meta["last_accessed"] = time.time()
            self._save_meta()

        fp = self._file_path(key)
        if not fp.exists():
            async with self._lock:
                self._meta.pop(key, None)
                self._save_meta()
            return None

        async with aiofiles.open(fp, "rb") as f:
            data = await f.read()
        return data, meta["content_type"]

    async def put(self, file_path: str, data: bytes, content_type: str):
        """Store data in cache."""
        await self._ensure_capacity(len(data))
        key = self._key(file_path)
        fp = self._file_path(key)
        async with aiofiles.open(fp, "wb") as f:
            await f.write(data)
        async with self._lock:
            self._meta[key] = {
                "path": file_path,
                "expires": time.time() + self.ttl,
                "size": len(data),
                "hits": 0,
                "content_type": content_type,
                "cached_at": time.time(),
                "last_accessed": time.time(),
            }
            self._save_meta()
        logger.info(f"CACHE PUT  {file_path}  ({len(data)//1024} KB)")

    async def delete(self, file_path: str) -> bool:
        key = self._key(file_path)
        async with self._lock:
            if key not in self._meta:
                return False
            await self._evict(key)
        return True

    async def clear_all(self):
        async with self._lock:
            for key in list(self._meta.keys()):
                await self._evict(key)
        logger.info("CACHE CLEARED (all entries)")

    def stats(self) -> dict:
        now = time.time()
        entries = list(self._meta.values())
        total_size = sum(e["size"] for e in entries)
        active = [e for e in entries if e["expires"] > now]
        expired = [e for e in entries if e["expires"] <= now]
        total_hits = sum(e.get("hits", 0) for e in entries)
        return {
            "total_entries": len(entries),
            "active_entries": len(active),
            "expired_entries": len(expired),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "max_size_mb": self.max_size_bytes // (1024 * 1024),
            "total_hits": total_hits,
            "ttl_seconds": self.ttl,
            "entries": [
                {
                    "path": e["path"],
                    "size_kb": round(e["size"] / 1024, 1),
                    "hits": e.get("hits", 0),
                    "expires_in": max(0, round(e["expires"] - now)),
                    "content_type": e["content_type"],
                }
                for e in sorted(entries, key=lambda x: -x.get("hits", 0))[:50]
            ],
        }

    # ── Private helpers ─────────────────────────────────────────

    async def _evict(self, key: str):
        fp = self._file_path(key)
        if fp.exists():
            fp.unlink()
        self._meta.pop(key, None)
        self._save_meta()

    async def _ensure_capacity(self, needed: int):
        async with self._lock:
            current = sum(e["size"] for e in self._meta.values())
            if current + needed <= self.max_size_bytes:
                return
            # Evict LRU entries
            sorted_keys = sorted(
                self._meta, key=lambda k: self._meta[k].get("last_accessed", 0)
            )
            for key in sorted_keys:
                if current + needed <= self.max_size_bytes:
                    break
                current -= self._meta[key]["size"]
                await self._evict(key)
                logger.info(f"CACHE EVICT (capacity) {key}")
