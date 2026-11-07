# Scheduled task: บ้านนี้มีดี by ซี — Reels (backup copy)
- id: trig_01Rj2GcSxGoEeUB9T5SRDFeH
- cron: `CRON_TZ=Asia/Bangkok 7 8,11,14,16,18,21,22 * * *` (7 a day; plan: 10 a day = `7 7,9,11,12,14,16,18,19,21,22`)
- permission: auto, push notification on
- connectors used: Google Sheets, Make, web search
- prompt: the RUN section of the `shopee-affiliate-fb-reels` skill (script ≤ 280 chars, cached closing lines, animated SVG with data-anim, AI-voice disclosure line in caption, Make scenario 6940105 responsive false + poll, never auto re-run, log to ประวัติโพสต์ with "[Reel HH]").
The image-post task is trig_01PHLdfWWyftA1xCPj8ymzLU (cron `41 7,12,17,19,20`), skill `shopee-affiliate-fb-autopost`.
