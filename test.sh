#!/usr/bin/env bash
# ส่งงานทดสอบ 1 คลิป แล้วรอผล
cd "$(dirname "$0")"; set -a; . ./.env; set +a
R=$(curl -s -X POST "http://127.0.0.1:$ENGINE_PORT/render" -H "X-API-Key: $ENGINE_TOKEN" -H "Content-Type: application/json" -d @sample_job.json)
echo "$R"; ID=$(echo "$R" | sed -n 's/.*"job_id":"\([a-f0-9]*\)".*/\1/p')
[ -n "$ID" ] || exit 1
for i in $(seq 1 60); do
  S=$(curl -s "http://127.0.0.1:$ENGINE_PORT/jobs/$ID" -H "X-API-Key: $ENGINE_TOKEN")
  echo "$S" | grep -q '"status":"\(done\|error\)"' && { echo "$S"; exit 0; }
  sleep 5
done; echo "timeout"; docker logs --tail 50 reels-engine
