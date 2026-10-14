#!/usr/bin/env bash
set -euo pipefail
sudo systemctl stop ouroboros-engine ouroboros-llm 2>/dev/null || true
sudo systemctl restart ouroboros-api
sleep 5
ok=0
fail=0
for i in $(seq 1 20); do
  if curl -fsS --max-time 4 http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    ok=$((ok + 1))
  else
    fail=$((fail + 1))
  fi
  sleep 0.4
done
echo "health_ok=$ok health_fail=$fail"
curl -fsS --max-time 8 http://127.0.0.1:8000/api/health || true
echo
curl -fsS --max-time 12 http://127.0.0.1:8000/universes/main | python3 -c 'import sys,json;d=json.load(sys.stdin);print("year",d.get("year"),"tick",d.get("tick"),"pop",d.get("population"),"running",d.get("is_running"))' || echo MAIN_FAIL
free -h | head -2
ps -o pid,rss,pcpu,cmd -C uvicorn --no-headers || true
# Verify new loop markers in code
grep -n "Fenêtre HTTP libre\|deferred_start\|_deferred_start" /home/ubuntu/ouroboros/app/api/main.py | head -5
