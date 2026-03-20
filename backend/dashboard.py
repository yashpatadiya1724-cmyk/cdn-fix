"""
dashboard.py
Serves the CDN monitoring dashboard on port 8090.
"""

import sys
import os
import time
import logging
import argparse
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import httpx
import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.cdn_config import EDGE_SERVERS, LOG_FILE, LOG_DIR

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cdn.dashboard")

from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(title="CDN Dashboard")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/proxy/lb-stats")
async def proxy_lb_stats():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("http://127.0.0.1:8081/stats")
            return r.json()
    except Exception as e:
        return {"error": str(e)}

@app.get("/proxy/origin-health")
async def proxy_origin_health():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("http://127.0.0.1:8000/health")
            return r.json()
    except Exception as e:
        return {"error": str(e)}

@app.get("/proxy/origin-logs")
async def proxy_origin_logs():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("http://127.0.0.1:8000/logs")
            return r.json()
    except Exception as e:
        return {"error": str(e)}

@app.delete("/proxy/clear-cache")
async def proxy_clear_cache():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.delete("http://127.0.0.1:8081/cache")
            return r.json()
    except Exception as e:
        return {"error": str(e)}

@app.get("/cdn/{file_path:path}")
async def proxy_cdn(file_path: str, request: Request):
    from fastapi.responses import Response
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"http://127.0.0.1:8081/cdn/{file_path}")
            return Response(
                content=r.content,
                status_code=r.status_code,
                media_type=r.headers.get("content-type", "application/octet-stream"),
                headers={"X-CDN-Proxy": "dashboard"},
            )
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=f"CDN unavailable: {e}")

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CDN Control Tower</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;600&display=swap');
  
  :root {
    --bg: #0a0c10;
    --surface: #12151c;
    --surface2: #1a1e28;
    --border: #1f2535;
    --accent: #00e5ff;
    --accent2: #7c3aed;
    --green: #10b981;
    --red: #ef4444;
    --yellow: #f59e0b;
    --text: #e2e8f0;
    --muted: #64748b;
    --mono: 'Space Mono', monospace;
    --sans: 'DM Sans', sans-serif;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  
  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--sans);
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* Grid noise texture overlay */
  body::before {
    content: '';
    position: fixed; inset: 0;
    background-image: 
      linear-gradient(rgba(0,229,255,0.02) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,229,255,0.02) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
  }

  .header {
    padding: 24px 32px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: relative;
    z-index: 1;
    background: linear-gradient(180deg, rgba(0,229,255,0.04) 0%, transparent 100%);
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .logo-icon {
    width: 40px; height: 40px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
  }

  .logo-text {
    font-family: var(--mono);
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 0.05em;
  }

  .logo-sub {
    font-size: 11px;
    color: var(--muted);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-top: 2px;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 8px var(--green);
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  .live-badge {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--green);
    letter-spacing: 0.1em;
  }

  .btn {
    padding: 8px 16px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text);
    font-family: var(--mono);
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn:hover {
    border-color: var(--accent);
    color: var(--accent);
    box-shadow: 0 0 12px rgba(0,229,255,0.15);
  }

  .btn-danger {
    border-color: rgba(239,68,68,0.4);
    color: var(--red);
  }

  .btn-danger:hover {
    border-color: var(--red);
    box-shadow: 0 0 12px rgba(239,68,68,0.2);
  }

  .main { padding: 28px 32px; position: relative; z-index: 1; }

  .section-title {
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .section-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
  }

  /* ── KPI Row ── */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
  }

  .kpi {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 20px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.3s;
  }

  .kpi:hover { border-color: var(--accent); }

  .kpi::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    opacity: 0;
    transition: opacity 0.3s;
  }

  .kpi:hover::before { opacity: 1; }

  .kpi-label {
    font-size: 11px;
    color: var(--muted);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 10px;
  }

  .kpi-value {
    font-family: var(--mono);
    font-size: 28px;
    font-weight: 700;
    color: var(--accent);
    line-height: 1;
    margin-bottom: 6px;
  }

  .kpi-sub {
    font-size: 12px;
    color: var(--muted);
  }

  /* ── Server Grid ── */
  .server-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
  }

  .server-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 20px;
    transition: all 0.3s;
  }

  .server-card.online { border-color: rgba(16,185,129,0.3); }
  .server-card.offline { border-color: rgba(239,68,68,0.3); }

  .server-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }

  .server-name {
    font-family: var(--mono);
    font-size: 14px;
    font-weight: 700;
  }

  .server-badge {
    font-size: 10px;
    padding: 3px 8px;
    border-radius: 4px;
    font-family: var(--mono);
    letter-spacing: 0.05em;
  }

  .badge-online { background: rgba(16,185,129,0.15); color: var(--green); }
  .badge-offline { background: rgba(239,68,68,0.15); color: var(--red); }
  .badge-origin { background: rgba(124,58,237,0.15); color: #a78bfa; }

  .server-stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .srv-stat { }
  .srv-stat-label { font-size: 11px; color: var(--muted); margin-bottom: 2px; }
  .srv-stat-val { font-family: var(--mono); font-size: 15px; font-weight: 700; }

  /* ── Hit Rate Bar ── */
  .hit-bar-wrap {
    margin-top: 14px;
  }

  .hit-bar-label {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: var(--muted);
    margin-bottom: 6px;
  }

  .hit-bar {
    height: 6px;
    background: var(--border);
    border-radius: 3px;
    overflow: hidden;
  }

  .hit-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), var(--green));
    border-radius: 3px;
    transition: width 0.8s cubic-bezier(0.4,0,0.2,1);
  }

  /* ── Cache Table ── */
  .cache-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
    margin-bottom: 32px;
  }

  .cache-panel-header {
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--surface2);
  }

  .cache-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }

  .cache-table th {
    padding: 10px 16px;
    text-align: left;
    font-family: var(--mono);
    font-size: 10px;
    letter-spacing: 0.1em;
    color: var(--muted);
    text-transform: uppercase;
    border-bottom: 1px solid var(--border);
    background: var(--surface2);
  }

  .cache-table td {
    padding: 10px 16px;
    border-bottom: 1px solid rgba(31,37,53,0.5);
    font-family: var(--mono);
    font-size: 12px;
  }

  .cache-table tr:last-child td { border-bottom: none; }

  .cache-table tr:hover td { background: rgba(0,229,255,0.03); }

  .expires-bar {
    width: 60px;
    height: 4px;
    background: var(--border);
    border-radius: 2px;
    overflow: hidden;
    display: inline-block;
    vertical-align: middle;
    margin-left: 8px;
  }

  .expires-fill {
    height: 100%;
    border-radius: 2px;
    background: var(--green);
  }

  .expires-fill.low { background: var(--red); }
  .expires-fill.mid { background: var(--yellow); }

  /* ── Log Panel ── */
  .log-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
    margin-bottom: 32px;
  }

  .log-panel-header {
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
    background: var(--surface2);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .log-body {
    padding: 12px 16px;
    height: 220px;
    overflow-y: auto;
    font-family: var(--mono);
    font-size: 11px;
    line-height: 1.8;
  }

  .log-body::-webkit-scrollbar { width: 4px; }
  .log-body::-webkit-scrollbar-track { background: transparent; }
  .log-body::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

  .log-hit { color: var(--green); }
  .log-miss { color: var(--yellow); }
  .log-err { color: var(--red); }
  .log-time { color: var(--muted); margin-right: 8px; }

  /* ── Toast ── */
  .toast {
    position: fixed;
    bottom: 24px; right: 24px;
    background: var(--surface2);
    border: 1px solid var(--accent);
    border-radius: 10px;
    padding: 12px 20px;
    font-family: var(--mono);
    font-size: 13px;
    color: var(--accent);
    z-index: 999;
    display: none;
    animation: slideUp 0.3s ease;
  }

  @keyframes slideUp {
    from { transform: translateY(20px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }

  .empty-state {
    padding: 40px;
    text-align: center;
    color: var(--muted);
    font-family: var(--mono);
    font-size: 13px;
  }

  .refresh-spinner {
    display: inline-block;
    width: 14px; height: 14px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-right: 8px;
    vertical-align: middle;
  }

  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>

<header class="header">
  <div class="logo">
    <div class="logo-icon">⚡</div>
    <div>
      <div class="logo-text">CDN CONTROL TOWER</div>
      <div class="logo-sub">Real-time monitoring dashboard</div>
    </div>
  </div>
  <div class="header-right">
    <div class="status-dot"></div>
    <span class="live-badge">LIVE</span>
    <button class="btn" onclick="refresh()">⟳ Refresh</button>
    <button class="btn btn-danger" onclick="clearCache()">🗑 Clear All Cache</button>
    <a href="/cdn/perf.html" target="_blank" style="text-decoration:none;"><button class="btn" style="background:rgba(29,158,117,0.15);border-color:#1D9E75;color:#1D9E75;">📊 Performance</button></a>
  </div>
</header>

<main class="main">

  <!-- KPIs -->
  <div class="section-title">Network Overview</div>
  <div class="kpi-grid" id="kpi-grid">
    <div class="kpi"><div class="kpi-label">Total Requests</div><div class="kpi-value" id="kpi-req">—</div><div class="kpi-sub">via load balancer</div></div>
    <div class="kpi"><div class="kpi-label">Cache Hit Rate</div><div class="kpi-value" id="kpi-hit">—</div><div class="kpi-sub">across all edges</div></div>
    <div class="kpi"><div class="kpi-label">Bytes Served</div><div class="kpi-value" id="kpi-bytes">—</div><div class="kpi-sub">total delivered</div></div>
    <div class="kpi"><div class="kpi-label">Cached Files</div><div class="kpi-value" id="kpi-files">—</div><div class="kpi-sub">active cache entries</div></div>
    <div class="kpi"><div class="kpi-label">LB Uptime</div><div class="kpi-value" id="kpi-uptime">—</div><div class="kpi-sub">load balancer</div></div>
    <div class="kpi"><div class="kpi-label">Healthy Edges</div><div class="kpi-value" id="kpi-edges">—</div><div class="kpi-sub">of total edge servers</div></div>
  </div>

  <!-- Servers -->
  <div class="section-title">Server Health</div>
  <div class="server-grid" id="server-grid">
    <div class="kpi empty-state">Loading server status…</div>
  </div>

  <!-- Cache entries -->
  <div class="section-title">Cache Entries</div>
  <div class="cache-panel">
    <div class="cache-panel-header">
      <span style="font-family:var(--mono);font-size:13px;">Hot Files</span>
      <span id="cache-count" style="font-family:var(--mono);font-size:11px;color:var(--muted);">0 entries</span>
    </div>
    <table class="cache-table">
      <thead>
        <tr>
          <th>Path</th>
          <th>Type</th>
          <th>Size (KB)</th>
          <th>Hits</th>
          <th>Expires In</th>
        </tr>
      </thead>
      <tbody id="cache-tbody">
        <tr><td colspan="5" class="empty-state">No cached files yet</td></tr>
      </tbody>
    </table>
  </div>

  <!-- Logs -->
  <div class="section-title">Request Log</div>
  <div class="log-panel">
    <div class="log-panel-header">
      <span style="font-family:var(--mono);font-size:13px;">Live Feed</span>
      <span style="font-family:var(--mono);font-size:11px;color:var(--muted);" id="log-count">0 entries</span>
    </div>
    <div class="log-body" id="log-body">
      <div style="color:var(--muted)">Waiting for requests…</div>
    </div>
  </div>

</main>

<div class="toast" id="toast"></div>

<script>
const LB = '';   // use proxy endpoints on same origin
const ORIGIN = '';

function showToast(msg, ok=true) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.display = 'block';
  t.style.borderColor = ok ? 'var(--accent)' : 'var(--red)';
  t.style.color = ok ? 'var(--accent)' : 'var(--red)';
  setTimeout(() => t.style.display = 'none', 3000);
}

function fmt(n) {
  if (n >= 1e6) return (n/1e6).toFixed(1)+'M';
  if (n >= 1e3) return (n/1e3).toFixed(1)+'K';
  return n;
}

function fmtBytes(mb) {
  if (mb >= 1024) return (mb/1024).toFixed(2)+' GB';
  if (mb >= 1) return mb.toFixed(2)+' MB';
  return (mb*1024).toFixed(0)+' KB';
}

function fmtUptime(s) {
  if (s < 60) return s+'s';
  if (s < 3600) return Math.floor(s/60)+'m '+( s%60)+'s';
  return Math.floor(s/3600)+'h '+Math.floor((s%3600)/60)+'m';
}

async function refresh() {
  let lbData = null, originData = null;

  try {
    const r = await fetch('/proxy/lb-stats');
    lbData = await r.json();
  } catch(e) {}

  try {
    const r = await fetch('/proxy/origin-health');
    originData = await r.json();
  } catch(e) {}

  if (!lbData) {
    showToast('Load balancer offline', false);
    return;
  }

  // KPIs
  const edges = lbData.edge_details || [];
  const totalReqs = edges.reduce((s,e) => s+(e.requests||0), 0);
  const totalHits = edges.reduce((s,e) => s+(e.cache_hits||0), 0);
  const totalMiss = edges.reduce((s,e) => s+(e.cache_misses||0), 0);
  const hitRate = totalHits+totalMiss > 0 ? ((totalHits/(totalHits+totalMiss))*100).toFixed(1) : '0.0';
  const totalBytes = edges.reduce((s,e) => s+(e.bytes_served_mb||0), 0);
  const totalFiles = edges.reduce((s,e) => s+((e.cache&&e.cache.active_entries)||0), 0);
  const lb = lbData.load_balancer;

  document.getElementById('kpi-req').textContent = fmt(lb.total_requests);
  document.getElementById('kpi-hit').textContent = hitRate+'%';
  document.getElementById('kpi-bytes').textContent = fmtBytes(totalBytes);
  document.getElementById('kpi-files').textContent = totalFiles;
  document.getElementById('kpi-uptime').textContent = fmtUptime(lb.uptime_seconds);
  document.getElementById('kpi-edges').textContent =
    lbData.servers.filter(s=>s.healthy).length + '/' + lbData.servers.length;

  // Server cards
  const grid = document.getElementById('server-grid');
  grid.innerHTML = '';

  // Origin card
  const originOnline = !!originData;
  grid.innerHTML += `
    <div class="server-card ${originOnline?'online':'offline'}">
      <div class="server-header">
        <div class="server-name">⬡ origin-server</div>
        <span class="server-badge badge-origin">ORIGIN</span>
      </div>
      <div class="server-stats">
        <div class="srv-stat"><div class="srv-stat-label">Port</div><div class="srv-stat-val">8000</div></div>
        <div class="srv-stat"><div class="srv-stat-label">Status</div>
          <div class="srv-stat-val" style="color:${originOnline?'var(--green)':'var(--red)'}">${originOnline?'ONLINE':'OFFLINE'}</div>
        </div>
      </div>
    </div>
  `;

  // Edge cards
  edges.forEach((e, i) => {
    const srv = (lbData.servers||[])[i] || {};
    const hitR = (e.hit_rate_pct||0).toFixed(1);
    grid.innerHTML += `
      <div class="server-card ${srv.healthy?'online':'offline'}">
        <div class="server-header">
          <div class="server-name">◈ ${e.edge_id||'edge-'+i}</div>
          <span class="server-badge ${srv.healthy?'badge-online':'badge-offline'}">${srv.healthy?'ONLINE':'OFFLINE'}</span>
        </div>
        <div class="server-stats">
          <div class="srv-stat"><div class="srv-stat-label">Port</div><div class="srv-stat-val">${e.port||'—'}</div></div>
          <div class="srv-stat"><div class="srv-stat-label">Requests</div><div class="srv-stat-val">${fmt(e.requests||0)}</div></div>
          <div class="srv-stat"><div class="srv-stat-label">Cache Hits</div><div class="srv-stat-val" style="color:var(--green)">${fmt(e.cache_hits||0)}</div></div>
          <div class="srv-stat"><div class="srv-stat-label">Cache Size</div><div class="srv-stat-val">${(e.cache&&e.cache.total_size_mb||0).toFixed(1)} MB</div></div>
        </div>
        <div class="hit-bar-wrap">
          <div class="hit-bar-label"><span>Hit Rate</span><span style="color:var(--accent)">${hitR}%</span></div>
          <div class="hit-bar"><div class="hit-bar-fill" style="width:${hitR}%"></div></div>
        </div>
      </div>
    `;
  });

  // LB card
  grid.innerHTML += `
    <div class="server-card online">
      <div class="server-header">
        <div class="server-name">⚖ load-balancer</div>
        <span class="server-badge badge-online">ONLINE</span>
      </div>
      <div class="server-stats">
        <div class="srv-stat"><div class="srv-stat-label">Port</div><div class="srv-stat-val">8080</div></div>
        <div class="srv-stat"><div class="srv-stat-label">Total Req</div><div class="srv-stat-val">${fmt(lb.total_requests)}</div></div>
        <div class="srv-stat"><div class="srv-stat-label">Errors</div><div class="srv-stat-val" style="color:${lb.total_errors>0?'var(--red)':'var(--green)'}">${lb.total_errors}</div></div>
        <div class="srv-stat"><div class="srv-stat-label">Uptime</div><div class="srv-stat-val">${fmtUptime(lb.uptime_seconds)}</div></div>
      </div>
    </div>
  `;

  // Cache table (aggregate from all edges)
  const allEntries = edges.flatMap(e => (e.cache&&e.cache.entries)||[]);
  allEntries.sort((a,b) => b.hits - a.hits);
  const ttl = edges[0]?.cache?.ttl_seconds || 300;
  document.getElementById('cache-count').textContent = allEntries.length + ' entries';

  if (allEntries.length === 0) {
    document.getElementById('cache-tbody').innerHTML = 
      '<tr><td colspan="5" class="empty-state">No cached files yet — make some requests!</td></tr>';
  } else {
    document.getElementById('cache-tbody').innerHTML = allEntries.slice(0,30).map(e => {
      const pct = Math.round((e.expires_in / ttl) * 100);
      const cls = pct < 20 ? 'low' : pct < 50 ? 'mid' : '';
      return `<tr>
        <td style="color:var(--text)">/${e.path}</td>
        <td style="color:var(--muted)">${e.content_type.split('/')[1]||'—'}</td>
        <td>${e.size_kb}</td>
        <td style="color:var(--accent)">${e.hits}</td>
        <td>
          ${e.expires_in}s
          <span class="expires-bar"><span class="expires-fill ${cls}" style="width:${pct}%"></span></span>
        </td>
      </tr>`;
    }).join('');
  }

  // Logs
  try {
    const lr = await fetch('/proxy/origin-logs');
    const ld = await lr.json();
    const logs = (ld.logs||[]).slice(-60).reverse();
    document.getElementById('log-count').textContent = logs.length + ' entries';
    document.getElementById('log-body').innerHTML = logs.map(l => {
      const cls = l.status < 300 ? 'log-hit' : l.status < 500 ? 'log-miss' : 'log-err';
      return `<div class="${cls}"><span class="log-time">${l.time}</span>${l.method} ${l.path} → <strong>${l.status}</strong> [${l.client}]</div>`;
    }).join('') || '<div style="color:var(--muted)">No logs yet</div>';
  } catch(e) {}
}

async function clearCache() {
  if (!confirm('Clear ALL cached files across all edge servers?')) return;
  try {
    const r = await fetch('/proxy/clear-cache', {method:'DELETE'});
    const d = await r.json();
    showToast('✓ Cache cleared on all edges');
    setTimeout(refresh, 500);
  } catch(e) {
    showToast('Failed to clear cache', false);
  }
}

// Auto refresh every 5 seconds
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 8090)))
    args, _ = parser.parse_known_args()
    logger.info(f"Starting Dashboard on port {args.port}")
    uvicorn.run("backend.dashboard:app", host="0.0.0.0", port=args.port, reload=False)
