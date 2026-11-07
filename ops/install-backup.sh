#!/usr/bin/env bash
# Install the daily backup cron job (03:17 server time) and run one backup now.
set -euo pipefail
chmod +x /opt/reels-engine/ops/backup.sh /opt/reels-engine/ops/restore.sh
cat > /etc/cron.d/reels-engine-backup <<'CRON'
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
17 3 * * * root /opt/reels-engine/ops/backup.sh >> /var/log/reels-engine-backup.log 2>&1
CRON
chmod 644 /etc/cron.d/reels-engine-backup
/opt/reels-engine/ops/backup.sh
echo "cron installed: /etc/cron.d/reels-engine-backup (daily 03:17)"
