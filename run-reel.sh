#!/usr/bin/env bash
# One Codex Reel run for บ้านนี้มีดี by ซี. Called by cron (see README-HERMES.md).
set -uo pipefail
cd "$(dirname "$0")"
set -a; . ./.env; set +a
mkdir -p logs work

SLOT=$(TZ=Asia/Bangkok date +%H)
DAY=$(TZ=Asia/Bangkok date +%F)
LOG="logs/$DAY-$SLOT.log"
LAST="logs/$DAY-$SLOT-summary.txt"

# never two runs at once
exec 9>/tmp/codex-reels.lock
if ! flock -n 9; then echo "$(date) another run is active, skip" >>"$LOG"; exit 0; fi

rm -f work/*
timeout 45m codex exec \
  --skip-git-repo-check \
  -s workspace-write -c sandbox_workspace_write.network_access=true \
  -o "$LAST" \
  "Run ONE Reel for slot $SLOT now (Bangkok date $DAY). Follow AGENTS.md and the skill baannee-reels exactly." \
  >>"$LOG" 2>&1
echo "$(date) codex exit $?" >>"$LOG"

# optional: forward the summary to Telegram
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ] && [ -s "$LAST" ]; then
  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="$TELEGRAM_CHAT_ID" --data-urlencode text@"$LAST" >/dev/null || true
fi

# keep 14 days of logs
find logs -type f -mtime +14 -delete 2>/dev/null || true
