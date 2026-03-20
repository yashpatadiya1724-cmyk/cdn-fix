# ⚡ CDN System — Full Stack Content Delivery Network

A production-style CDN built with Python (FastAPI) featuring origin/edge servers,
caching, load balancing, rate limiting, and a live monitoring dashboard.

---

## Architecture

```
Client → Load Balancer (8080)
              ├─ Edge Server 1 (8001)  ←── cache/edge-1/
              └─ Edge Server 2 (8002)  ←── cache/edge-2/
                        │
                   Origin Server (8000)  ←── static/
                        
Dashboard (8090)  →  polls all servers
```

## Folder Structure

```
cdn_system/
├── backend/
│   ├── origin_server.py    # Master file storage server
│   ├── edge_server.py      # Cache + delivery server (run multiple)
│   ├── load_balancer.py    # Round-robin LB with health checks
│   ├── cache_manager.py    # TTL cache with LRU eviction
│   └── dashboard.py        # Real-time monitoring UI
├── config/
│   └── cdn_config.py       # Central configuration
├── static/
│   ├── images/             # Put your images here
│   ├── css/                # CSS files
│   ├── js/                 # JavaScript files
│   └── videos/             # Video files
├── cache/
│   ├── edge-1/             # Edge 1 disk cache
│   └── edge-2/             # Edge 2 disk cache
├── logs/
│   └── cdn.log             # Unified log file
├── requirements.txt
├── start_cdn.sh            # One-command startup
└── stop_cdn.sh             # Graceful shutdown
```

---

## Quick Start

### 1. Install dependencies

```bash
cd cdn_system
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start everything (one command)

```bash
./start_cdn.sh
```

Or start each server manually:

```bash
# Terminal 1 — Origin
PYTHONPATH=. python3 -m backend.origin_server

# Terminal 2 — Edge 1
PYTHONPATH=. python3 -m backend.edge_server --port 8001 --edge-id edge-1

# Terminal 3 — Edge 2
PYTHONPATH=. python3 -m backend.edge_server --port 8002 --edge-id edge-2

# Terminal 4 — Load Balancer
PYTHONPATH=. python3 -m backend.load_balancer

# Terminal 5 — Dashboard
PYTHONPATH=. python3 -m backend.dashboard
```

---

## Usage

### Serve a file via CDN (load balanced)
```bash
curl http://localhost:8080/cdn/css/styles.css
curl http://localhost:8080/cdn/js/app.js
curl http://localhost:8080/cdn/images/sample.png
```

Response headers:
```
X-Cache: MISS   (first request — fetched from origin)
X-Cache: HIT    (subsequent requests — served from cache)
X-Edge-Server: edge-1
```

### Check server health
```bash
curl http://localhost:8000/health  # Origin
curl http://localhost:8001/health  # Edge 1
curl http://localhost:8080/health  # Load Balancer
```

### View aggregated stats
```bash
curl http://localhost:8080/stats | python3 -m json.tool
```

### Clear entire cache
```bash
curl -X DELETE http://localhost:8080/cache
```

### Evict a specific file
```bash
curl -X DELETE http://localhost:8001/cache/css/styles.css
```

### List all files on origin
```bash
curl http://localhost:8000/list
```

### Open Dashboard
```
http://localhost:8090
```

---

## Configuration (`config/cdn_config.py`)

| Setting | Default | Description |
|---|---|---|
| `CACHE_TTL_SECONDS` | 300 (5 min) | How long files stay cached |
| `MAX_CACHE_SIZE_MB` | 500 | Max disk cache per edge |
| `RATE_LIMIT` | 60/minute | Requests per IP per edge |
| `EDGE_SERVERS` | ports 8001,8002 | Add more edges here |

Override via environment variables:
```bash
CACHE_TTL=600 MAX_CACHE_MB=1024 ./start_cdn.sh
```

---

## Features

| Feature | Details |
|---|---|
| **Origin Server** | Serves raw files from `/static`, lists inventory |
| **Edge Cache** | Disk-backed TTL cache with hit tracking & LRU eviction |
| **Load Balancer** | Round-robin across healthy edges, auto health checks |
| **Cache Expiry** | Per-file TTL with visual countdown in dashboard |
| **Rate Limiting** | Per-IP slowapi limit on each edge |
| **Cache API** | Clear all / evict single file via REST |
| **Dashboard** | Live KPIs, server health, cache table, request log |
| **Logging** | Unified file + console log with cache hit/miss labels |

---

## Adding Static Files

Drop files into the `static/` directory:

```bash
cp my-video.mp4   static/videos/
cp logo.png       static/images/
cp theme.css      static/css/
cp bundle.js      static/js/
```

Then request them:
```bash
curl http://localhost:8080/cdn/videos/my-video.mp4
```

## Stop CDN

```bash
./stop_cdn.sh
```
