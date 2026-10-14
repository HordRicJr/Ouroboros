#!/usr/bin/env bash
set -euo pipefail
sudo systemctl stop ouroboros-engine ouroboros-llm 2>/dev/null || true
sudo systemctl restart ouroboros-api
for i in $(seq 1 40); do
  if curl -fsS --max-time 3 http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    echo HEALTH_OK
    curl -fsS --max-time 10 http://127.0.0.1:8000/api/health
    echo
    curl -fsS --max-time 12 http://127.0.0.1:8000/universes/main | python3 -c 'import sys,json;d=json.load(sys.stdin);print("year",d.get("year"),"tick",d.get("tick"),"pop",d.get("population"),"running",d.get("is_running"))'
    free -h | head -2
    ps -o pid,rss,pcpu,cmd -C uvicorn --no-headers
    exit 0
  fi
  sleep 2
done
echo FAIL
journalctl -u ouroboros-api -n 30 --no-pager
exit 1
