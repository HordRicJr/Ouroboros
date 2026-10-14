#!/usr/bin/env bash
set -euo pipefail
for i in $(seq 1 60); do
  h=$(curl -fsS --max-time 3 http://127.0.0.1:8000/api/health 2>/dev/null || echo '{"status":"down"}')
  echo "$i $h"
  if echo "$h" | grep -q 'universe_ready":"yes'; then
    curl -fsS --max-time 12 http://127.0.0.1:8000/universes/main | python3 -c 'import sys,json;d=json.load(sys.stdin);print("READY year",d.get("year"),"tick",d.get("tick"),"pop",d.get("population"),"running",d.get("is_running"))'
    # stability sample
    ok=0; fail=0
    for j in $(seq 1 25); do
      if curl -fsS --max-time 4 http://127.0.0.1:8000/api/health >/dev/null 2>&1; then ok=$((ok+1)); else fail=$((fail+1)); fi
      sleep 0.25
    done
    echo "stability ok=$ok fail=$fail"
    free -h | head -2
    exit 0
  fi
  sleep 2
done
echo TIMEOUT_LOADING
journalctl -u ouroboros-api -n 40 --no-pager
exit 1
