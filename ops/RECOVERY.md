# Backup & recovery — reels-engine (บ้านนี้มีดี by ซี Reels)

## What is backed up, where
| Piece | Where it lives | Backup |
|---|---|---|
| Engine code | GitHub `Nolmalza/botbas-social-assets`, branch `reels-engine` | git (every change is a commit) |
| `.env` (ElevenLabs key, voice, token, settings) | VPS `/opt/reels-engine/.env` | daily `ops/backup.sh` → `/opt/backups/reels-engine/` (chmod 600) |
| Voice cache (paid audio) | VPS `data/tts_cache/` | daily `ops/backup.sh` |
| Music anti-repeat history, job records | VPS `data/` | daily `ops/backup.sh` |
| Make scenario 6940105 | Make | `ops/make-reels-scenario.blueprint.json` (token/URL/connection masked) |
| Scheduled task prompts | Claude scheduled tasks | `ops/scheduled-task-reels.md` + the `shopee-affiliate-fb-reels` skill |
| Products, post log, settings | Google Sheet `1IKNyEA6vhfeQH8Z6SYcLMTHHv5_fsdO66cOYDSf1XtE` | Google version history (File → Version history) |

Daily backup runs at 03:17 server time (`/etc/cron.d/reels-engine-backup`), keeps 14 days (`BACKUP_KEEP_DAYS`), log at `/opt/backups/reels-engine/backup.log`.
Optional offsite copy: install rclone, configure a remote (e.g. Google Drive), then set `BACKUP_RCLONE_REMOTE=gdrive:reels-engine-backup` in `.env`.
Backups contain the ElevenLabs key: never put them in a public place.

## Restore on the same VPS
`sudo bash /opt/reels-engine/ops/restore.sh` (latest) or pass a file path. It saves the current .env as `.env.before-restore-*`, restores, rebuilds and checks /health.

## Rebuild on a new VPS
1. Install Docker; `git clone -b reels-engine --single-branch --depth 1 https://github.com/Nolmalza/botbas-social-assets /opt/reels-engine`
2. Copy the newest backup archive to `/opt/backups/reels-engine/` and run `sudo bash /opt/reels-engine/ops/restore.sh`
3. New IP? Update `PUBLIC_URL` in .env (`docker compose up -d`), the 3 URLs in the Make scenario, and the ElevenLabs key IP restriction.
4. `sudo bash /opt/reels-engine/ops/install-backup.sh` to re-create the daily backup.

## Rebuild the Make scenario
Make → Create scenario → ⋯ → Import Blueprint → `ops/make-reels-scenario.blueprint.json`; replace `{{ENGINE_URL}}` (3×) and `{{ENGINE_TOKEN}}` (3×), choose the Facebook Pages connection in the 4 Facebook modules, scheduling = on-demand, activate. Update the scenario id in the scheduled task prompt if it changed.
