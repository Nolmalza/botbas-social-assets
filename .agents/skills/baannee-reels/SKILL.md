---
name: baannee-reels
description: Make and publish ONE Facebook Reel (Thai home tip + Shopee affiliate link in the first comment) for the page บ้านนี้มีดี by ซี, using the reels-engine on this VPS and Make scenario 6940105.
---

# บ้านนี้มีดี by ซี — one Reel per run (Codex version)

Port of BAS's Claude skill "shopee-affiliate-fb-reels" with all of BAS's overrides up to Nov 16 2026 merged in.
Claude runs the other slots of the same page from a scheduled task; both share the same Google Sheet and log, so
always read the log first and never repeat a topic.

A 28–38 s 9:16 Reel (never over 40 s): a naturally spoken Thai home problem-solving tip with fresh animated
illustrations, Thai karaoke subtitles and upbeat music, plus one Shopee affiliate product in the first comment as
the faster/easier way. Rendered by the reels-engine on this VPS, posted by Make.

## Config
| key | value |
|---|---|
| PAGE | บ้านนี้มีดี by ซี / page_id 1373565455841925 / PAGE_KEY baannee |
| SHEET | 1IKNyEA6vhfeQH8Z6SYcLMTHHv5_fsdO66cOYDSf1XtE — tabs ค้นหา, ตั้งค่า, ประวัติโพสต์, feed_home_06112026 (A item_id … F image URL, G category, H aff_link, I posted_at, J sub_id) |
| ENGINE | http://127.0.0.1:8090 (code + docs in /opt/reels-engine, READ ONLY — never edit, pull or restart it) |
| MAKE | scenario 6940105, inputs job_json, page_id, caption, comment (it renders, waits, posts the Reel and adds the comment itself) |
| VOICE | engine default (Oaw1). Send NO voice field |
| SIGNATURE / HASHTAGS | — บ้านนี้มีดี by ซี 🏠 / #บ้านนี้มีดี #ทริคบ้าน #Reels + 1 |

Engine features (cover, animation attributes, asset library, voice, music): read `engine-notes.md` in this folder,
then the docs at the top of `/opt/reels-engine/app/anim.py` and `/opt/reels-engine/app/assets.py`, and the examples
`/opt/reels-engine/examples/scene_natural_motion.svg`, `scene_assets_1..3.svg`.

## Tools (use these instead of Claude connectors)
- Sheet: `python3 tools/sheet.py get|all|tail|set|append ...` (see the script header).
- Make: `python3 tools/make.py run work/job.json work/caption.txt work/comment.txt`, then
  `python3 tools/make.py wait <executionId>` (exit 0 success, 2 error, 3 unconfirmed).
- Asset library: `/opt/reels-engine/assets/catalog.json` and `curl -s http://127.0.0.1:8090/assets`.
- Put every working file in `work/` (overwrite freely).

## RUN
1. SLOT = current Bangkok hour, 2 digits (`TZ=Asia/Bangkok date +%H`). Read ประวัติโพสต์ (`tail ประวัติโพสต์ 120` is
   enough for today + recent history). If a row has posted_at today and a topic starting "[Reel <SLOT>]", stop:
   this slot is done.
2. Read `ตั้งค่า!A1:B22`: B2 = product cooldown days, B5 = content and caption rules (follow them), A9:A21 =
   categories, B9:B21 = topic ideas. No topic may repeat anything in the log (image posts or Reels).
3. Category: from A9:A21 exclude every category already used TODAY (Bangkok date) in the log by image posts or
   Reels; among the rest pick the least recently used. Only if all were used today, pick the oldest-used one that
   is not the same as the previous log row. Write it to `ค้นหา!B2`, set `ค้นหา!B1` to "" (or a narrowing Thai
   keyword), then read `ค้นหา!A6:H25` (item_id, title, price, rating, sold, category, aff_link, row). If it shows
   ไม่พบสินค้า, clear B1 or try the next category. Pick the ONE product that fits a real home problem; read its
   image URL from `feed_home_06112026!F<row>`.
4. Topic and plan: problem → 2–3 DIY steps that work without buying → the product as the shortcut. Only state facts
   you can verify (web-search if you can; otherwise use only well-known, safe tips). Never suggest dangerous chemical
   mixes (bleach + ammonia/acids etc.), no electrical/gas work beyond safe basics, no medical claims.
   Topics that work: a common, instantly recognisable home annoyance + a quick surprising fix, best of all a
   surprising everyday item used as the fix (salt on an iron plate, rice in a bottle, vinegar on limescale, a can
   tab as a hanger link). Best performers: kitchen hacks (peeling eggs, peeling garlic, stale bread), plants/garden,
   bathroom/smells, dusty dim room, limescale on taps/spoons. Avoid product-showcase clips.
5. Script: 3–4 content scenes + 1 very short closing scene. Content scenes together 280–350 characters (spaces
   count), closing line ≤ 25 characters, whole script hard max 375 (count with Python `len`). Each content scene
   1–2 full spoken sentences (~70–100 chars): the problem, concrete steps with the reason each works, and the "อ๋อ"
   insight. No greetings, filler, repetition or slogans.
   - Scene 1 starts straight with the hook, result-first: the surprising result or surprising item in the first
     ~8 words (e.g. "เกลือกำมือเดียว ทำให้หน้าเตารีดกลับมาเงาได้ค่ะ"), then the pain in one line. The hook may break a
     common belief ("หลายบ้าน<ทำแบบนี้> แต่จริงๆ แล้ว…") but must be true and answered by the clip.
   - Middle scenes: `step` "ขั้นที่ N", short action headlines ≤ 18 chars (e.g. "โรยเบกกิ้งโซดา"), never "วิธีที่ 1".
   - The scene before the last = the REVEAL: the one insight that answers the hook (usually WHY it works).
   - Voice of a Thai woman chatting to a friend, spoken Thai with particles (บอกเลยว่า, จริงๆ แล้ว, ก็คือ, เนี่ย,
     แค่นี้เอง), reasons with เพราะว่า…, varied endings (ค่ะ/นะคะ/เลยค่ะ/ได้เลย). Never written words: ดังนั้น,
     อย่างไรก็ตาม, ทำการ, ซึ่ง, โดยการ, ดำเนินการ, ประการแรก, นอกจากนี้, สามารถ…ได้. Spaces only at breath points
     every 3–6 words; numbers as Thai words; no URLs, emoji or brands.
   - Inside the CLIP (voice, subtitles, headlines, step pills, cover text, CTA box) never use ลิงก์, ลิ้ง, คอมเมนต์,
     คอมเม้น or ซี.
   - Last scene text = EXACTLY one of (random, not the same as the previous Reel in the log if you can tell):
     "ตัวช่วยอยู่ข้างล่างค่ะ" | "ของในคลิปอยู่ข้างล่างนะคะ" | "อยากง่ายกว่านี้ ดูข้างล่างเลย" | "มีตัวช่วยอยู่ใต้คลิปค่ะ" |
     "ขี้เกียจทำเอง ดูข้างล่างเลยค่ะ" | "ตัวช่วยที่เร็วกว่า อยู่ข้างล่างค่ะ"; its headline one of "อยากเร็วกว่านี้?" /
     "ขี้เกียจทำเอง?" / "มีตัวช่วยนะ!".
   - ALWAYS send job `cta` (the engine default says ลิงก์อยู่ในคอมเมนต์): one of "ตัวช่วยอยู่ข้างล่าง" |
     "ดูตัวช่วยใต้คลิป" | "เลื่อนลงดูตัวช่วย" | "ของดีอยู่ข้างล่าง".
6. Card cover `hook` = {tag, title, badge, points, note}: `title` 2 lines (split by \n) ≤ ~10 Thai chars each,
   naming the problem AND hinting at the payoff (e.g. "ปอกไข่*ไม่ติดเปลือก*\nใน 3 วินาที"), 1–2 key words of line 1
   in *asterisks*; `badge` = the promise as one short line (ล้างเองได้ ไม่ต้องจ้าง / แก้ได้ใน 3 ขั้น / ใช้ของในบ้าน);
   `points` = exactly 3 step summaries ≤ ~22 chars; `note` = one safety line ≤ ~30 chars if relevant, else omit;
   `tag` ทริคบ้านน่ารู้ (or หลายบ้านเป็น! / ทริกที่ต้องรู้). No emoji, brands, prices or anything untrue.
7. Animated svg for every scene but the last (the last shows the product image):
   - Library first: everything in catalog.json is used ONLY as `<g data-asset="name" transform="translate(x y)
     scale(s)"/>`, never redrawn. Draw only objects missing from the catalog. Do NOT use `data-save` (this runner
     cannot push new assets).
   - NO CHARACTERS: never use the mascot `zee` or draw any person, face, body or cartoon character, in scenes or on
     the cover. A hand/arm alone is fine (`arm` asset, or two thick round-cap strokes: dark outline + skin #F2C29B).
   - New flat vector, viewBox 0 0 920 890, xmlns set, light full background rect + a table/floor strip, bold shapes
     with #34404A outlines, objects large (middle ~70%), NO text/letters/numbers/logos, < ~9 KB, no
     images/filters/fonts/<style>/CSS/SMIL.
   - Every scene acts out its voice line: (a) a main action with `data-anim="keys"` (hand enters with back ease,
     does the job with nested shoulder/elbow joints, lifts away near the end); (b) the result (`scrubout` stains,
     state changes with keys); (c) 1–2 fitting particle emitters (bubble/stream/drop/steam/dust/sparkle);
     (d) `data-camera="push"` with `data-focus` on the action and the wall group `data-depth="0.55"`.
     Sine-only scenes (just wipe/bob) are not acceptable. Spread one-shot delays over 0–7 s.
   - Scene 1 is the cover illustration (main objects big) and sits behind the cover for 3 s: show the problem big
     and start the visible result right after ~3 s.
   - Check every svg parses: `python3 -c "import sys,xml.etree.ElementTree as E; E.parse(sys.argv[1])" file.svg`.
8. Caption (Thai) per B5: pick a structure A–G from B5 that differs from the last 3 rows of ประวัติโพสต์, vary first
   emoji, emoji set, bullet marker and tip header. First line = positive hook ≤ ~60 chars. POSITIVE EMOJI ONLY, 3–6,
   never 😩 😫 😭 😱 😡 🤢 ⚠️ 🚫 ❌. Then a follow line (vary wording) like "📌 กดติดตามเพจไว้ มีทริคบ้านใหม่ๆ ทุกวันค่ะ",
   then "🎙️ เสียงพากย์สร้างด้วย AI", then the signature, then hashtags. No URLs, brands or prices.
   SUB = `fb-baannee-reel-<slug>` (lowercase letters, digits, dashes; ≤ 40 chars). LINK = aff_link + `&sub_id=` + SUB.
   Comment ≤ 60 words: DIY → product as the shortcut with a varied opening line, 1–2 benefits, 1–2 positive emoji,
   LINK alone on the last line, no affiliate label.
9. Write `work/job.json` = {"hook", "scenes": [{"text","headline","step"?,"svg"?}...], "product_image_url", "cta"}
   (UTF-8, ensure_ascii False), `work/caption.txt`, `work/comment.txt`. Re-check the script length rules.
   Run `python3 tools/make.py run work/job.json work/caption.txt work/comment.txt` → executionId.
   Then `python3 tools/make.py wait <executionId>` (one long wait, max 3 checks, ~17 min). NEVER start Make a second
   time for this slot, whatever happens (the Reel may already be live).
10. Log (only if Make returned an executionId):
   - `feed_home_06112026!I<row>` = `=DATE(y,m,d)` (today, Bangkok) and `J<row>` = SUB (one `set` on `I<row>:J<row>`).
   - Append to ประวัติโพสต์: ["YYYY-MM-DD HH:MM", item_id, category, "[Reel <SLOT>] <Thai topic>", SUB, product title,
     LINK, first 200 chars of caption, "reel exec <executionId> (codex)" + " (unconfirmed)" if wait exited 3 or
     " (error)" if it exited 2].
11. Final message (it is sent to BAS): short Thai summary — slot, topic, hook title, product, script chars
   (content + closing), Make result, problems.
