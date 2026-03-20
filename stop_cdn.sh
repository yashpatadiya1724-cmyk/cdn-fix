#!/bin/bash
echo "Stopping CDN services..."
pkill -f "origin_server" 2>/dev/null && echo "  Origin stopped"  || true
pkill -f "edge_server"   2>/dev/null && echo "  Edges stopped"   || true
pkill -f "load_balancer" 2>/dev/null && echo "  LB stopped"      || true
pkill -f "dashboard"     2>/dev/null && echo "  Dashboard stopped" || true
echo "Done."
