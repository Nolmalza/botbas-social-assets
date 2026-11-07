#!/usr/bin/env bash
# reels-engine installer for Ubuntu 22.04 / 24.04 — run:  sudo bash install.sh
set -euo pipefail
cd "$(dirname "$0")"
[ "$(id -u)" -eq 0 ] || { echo "กรุณารันด้วย sudo: sudo bash install.sh"; exit 1; }

if ! command -v docker >/dev/null 2>&1; then
  echo ">> ติดตั้ง Docker..."; curl -fsSL https://get.docker.com | sh
fi
docker compose version >/dev/null 2>&1 || apt-get install -y docker-compose-plugin

PORT=8090
if ss -ltn | grep -q ":$PORT "; then
  echo "พอร์ต $PORT ถูกใช้อยู่แล้ว"; read -rp "ใส่พอร์ตอื่น (เช่น 8091): " PORT
fi

if [ ! -f .env ]; then
  IP=$(curl -fsS https://api.ipify.org || hostname -I | awk '{print $1}')
  echo; echo "=== ตั้งค่า ==="
  read -rsp "ElevenLabs API key (พิมพ์แล้วจะไม่แสดงบนจอ): " KEY; echo
  read -rp  "ElevenLabs Voice ID: " VOICE
  read -rp  "ชื่อแบรนด์บนคลิป [บ้านนี้มีดี by ซี]: " BRAND; BRAND=${BRAND:-บ้านนี้มีดี by ซี}
  TOKEN=$(openssl rand -hex 24)
  sed -e "s|^ELEVENLABS_API_KEY=.*|ELEVENLABS_API_KEY=$KEY|" \
      -e "s|^ELEVEN_VOICE_ID=.*|ELEVEN_VOICE_ID=$VOICE|" \
      -e "s|^BRAND_NAME=.*|BRAND_NAME=\"$BRAND\"|" \
      -e "s|^ENGINE_TOKEN=.*|ENGINE_TOKEN=$TOKEN|" \
      -e "s|^ENGINE_PORT=.*|ENGINE_PORT=$PORT|" \
      -e "s|^PUBLIC_URL=.*|PUBLIC_URL=http://$IP:$PORT|" .env.example > .env
  chmod 600 .env
fi
set -a; . ./.env; set +a

# quick key check
code=$(curl -s -o /dev/null -w "%{http_code}" -H "xi-api-key: $ELEVENLABS_API_KEY" https://api.elevenlabs.io/v1/user/subscription || true)
[ "$code" = "200" ] && echo ">> ElevenLabs key OK" || echo "!! ElevenLabs ตอบกลับ $code — เช็ก key/สิทธิ์ User:Access (แก้ได้ใน .env แล้วรัน: docker compose up -d)"

mkdir -p data
docker compose up -d --build

if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then ufw allow "$ENGINE_PORT"/tcp; fi

echo ">> รอระบบเริ่มทำงาน..."; for i in $(seq 1 30); do curl -fs "http://127.0.0.1:$ENGINE_PORT/health" >/dev/null && break; sleep 2; done
curl -fs "http://127.0.0.1:$ENGINE_PORT/health" && echo
echo
echo "================ เสร็จแล้ว ================"
echo "Render URL : $PUBLIC_URL/render"
echo "X-API-Key  : $ENGINE_TOKEN"
echo "(เก็บสองค่านี้ไว้ใส่ใน Make — ดูอีกครั้งได้ที่ไฟล์ .env)"
echo "ทดสอบ     : bash test.sh"
