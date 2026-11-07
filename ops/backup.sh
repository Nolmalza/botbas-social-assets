#!/usr/bin/env bash
# reels-engine backup: .env (secrets) + voice cache + music history + job records.
# Code is in git (branch reels-engine), so it is not backed up here.
# Usage: sudo bash /opt/reels-engine/ops/backup.sh      (cron runs it daily)
# Config (optional, in /opt/reels-engine/.env):
#   BACKUP_DIR=/opt/backups/reels-engine   BACKUP_KEEP_DAYS=14
#   BACKUP_RCLONE_REMOTE=gdrive:reels-engine-backup   (offsite copy via rclone, if configured)
set -euo pipefail
APP=/opt/reels-engine
cd "$APP"
get() { { grep -E "^$1=" .env 2>/dev/null || true; } | tail -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//'; }
DIR=$(get BACKUP_DIR); DIR=${DIR:-/opt/backups/reels-engine}
KEEP=$(get BACKUP_KEEP_DAYS); KEEP=${KEEP:-14}
REMOTE=$(get BACKUP_RCLONE_REMOTE)
mkdir -p "$DIR"; chmod 700 "$DIR"
TS=$(date +%Y%m%d-%H%M)
OUT="$DIR/reels-engine-$TS.tar.gz"
ITEMS=(.env)
[ -d data/tts_cache ] && ITEMS+=(data/tts_cache)
[ -f data/music_history.json ] && ITEMS+=(data/music_history.json)
[ -d data/jobs ] && ITEMS+=(data/jobs)
tar -czf "$OUT.tmp" "${ITEMS[@]}"
mv "$OUT.tmp" "$OUT"; chmod 600 "$OUT"
# integrity check
tar -tzf "$OUT" > /dev/null
COMMIT=$(git -C "$APP" rev-parse --short HEAD 2>/dev/null || echo "?")
echo "$TS commit=$COMMIT size=$(du -h "$OUT" | cut -f1) files=$(tar -tzf "$OUT" | wc -l)" >> "$DIR/backup.log"
# retention
find "$DIR" -name 'reels-engine-*.tar.gz' -mtime +"$KEEP" -delete
# offsite (optional)
if [ -n "$REMOTE" ] && command -v rclone >/dev/null 2>&1; then
  rclone copy "$OUT" "$REMOTE" && echo "$TS offsite ok -> $REMOTE" >> "$DIR/backup.log" \
    || echo "$TS offsite FAILED -> $REMOTE" >> "$DIR/backup.log"
  rclone delete --min-age "${KEEP}d" "$REMOTE" 2>/dev/null || true
fi
echo "backup ok: $OUT"
