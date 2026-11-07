#!/usr/bin/env bash
# Restore reels-engine data from a backup archive.
# Usage: sudo bash /opt/reels-engine/ops/restore.sh [/opt/backups/reels-engine/reels-engine-YYYYMMDD-HHMM.tar.gz]
#        (no argument = latest local backup)
# On a NEW server first: git clone -b reels-engine --single-branch --depth 1 https://github.com/Nolmalza/botbas-social-assets /opt/reels-engine
set -euo pipefail
APP=/opt/reels-engine
DIR=/opt/backups/reels-engine
F=${1:-$(ls -1t "$DIR"/reels-engine-*.tar.gz 2>/dev/null | head -1)}
[ -n "${F:-}" ] && [ -f "$F" ] || { echo "no backup file found"; exit 1; }
tar -tzf "$F" > /dev/null
cd "$APP"
if [ -f .env ]; then cp .env ".env.before-restore-$(date +%Y%m%d-%H%M)"; fi
tar -xzf "$F" -C "$APP"
chmod 600 .env
echo "restored from $F"
if command -v docker >/dev/null; then docker compose up -d --build && sleep 5 && curl -fs "http://127.0.0.1:$({ grep -E '^ENGINE_PORT=' .env || echo ENGINE_PORT=8090; } | tail -1 | cut -d= -f2)/health" && echo; fi
echo "NOTE: if this is a new server with a new IP, update PUBLIC_URL in .env, the Make scenario URLs, and the ElevenLabs key IP restriction."
