# CDN System - Windows PowerShell Startup Script
# Run this from inside the cdn_system folder

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT

# Activate venv
& "$ROOT\venv\Scripts\Activate.ps1"
$env:PYTHONPATH = "."

Write-Host ""
Write-Host "  ⚡ CDN System - Starting all servers..." -ForegroundColor Cyan
Write-Host "  ─────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Open 5 PowerShell tabs and run one command per tab:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Tab 1 (Origin):      python backend/origin_server.py" -ForegroundColor Green
Write-Host "  Tab 2 (Edge 1):      python backend/edge_server.py --port 8001 --edge-id edge-1" -ForegroundColor Green
Write-Host "  Tab 3 (Edge 2):      python backend/edge_server.py --port 8002 --edge-id edge-2" -ForegroundColor Green
Write-Host "  Tab 4 (LB):          python backend/load_balancer.py" -ForegroundColor Green
Write-Host "  Tab 5 (Dashboard):   python backend/dashboard.py" -ForegroundColor Green
Write-Host ""
Write-Host "  Dashboard: http://localhost:8090" -ForegroundColor Cyan
Write-Host "  CDN URL:   http://localhost:8081/cdn/css/styles.css" -ForegroundColor Cyan
Write-Host ""
