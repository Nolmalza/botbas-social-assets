# Codex Reels runner (BAS / บ้านนี้มีดี by ซี)

You run unattended from cron on BAS's VPS. Each run = publish exactly ONE Facebook Reel for the page
"บ้านนี้มีดี by ซี", by following the skill `baannee-reels` (.agents/skills/baannee-reels/SKILL.md) step by step.

Rules:
- No one is watching: never ask questions; take the most reasonable choice and say which in the final message.
- Work only inside this folder (`work/` for scratch files). Treat /opt/reels-engine as read-only reference.
- Never print, log or commit secrets (.env, gsa.json, tokens, API keys).
- Never edit the Make scenario, the engine, cron or any Claude scheduled task.
- Start Make at most once per run. If anything fails after Make started, log what you know and stop.
- Your last message is forwarded to BAS: keep it a short Thai summary.
