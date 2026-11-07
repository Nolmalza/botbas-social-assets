# reels-engine — ระบบทำคลิป Reels อัตโนมัติ (บ้านนี้มีดี by ซี)

Make ส่งสคริปต์ → VPS สร้างเสียง ElevenLabs + ภาพ + ซับไทยไฮไลต์ตามเสียง + เพลงประกอบ → ได้ลิงก์ MP4 9:16 กลับไปโพสต์ Reels

ทำงานใน Docker แยกขาดจากงานเดิมบนเครื่อง ใช้พอร์ต 8090 (เปลี่ยนได้ตอนติดตั้ง)

---

## 1) ติดตั้งบน VPS

จากเครื่องคุณ อัปโหลดไฟล์ zip ขึ้น VPS:
```
scp reels-engine.zip root@31.97.188.182:/opt/
```
SSH เข้า VPS แล้วรัน:
```
cd /opt && apt-get install -y unzip && unzip reels-engine.zip && cd reels-engine
sudo bash install.sh
```
ตัวติดตั้งจะถาม **API key** (พิมพ์แล้วไม่แสดงบนจอ) และ **Voice ID** แล้วสร้างทุกอย่างให้
จบแล้วจะแสดง **Render URL** และ **X-API-Key** — เก็บไว้ใส่ใน Make

ทดสอบ 1 คลิป:
```
bash test.sh
```
ได้ `"status":"done"` พร้อม `video_url` → เปิดลิงก์ในเบราว์เซอร์ดูคลิปได้เลย

หลังติดตั้งเสร็จ: กลับไปที่ ElevenLabs → API key → เปิด **Restrict by IP address** ใส่ `31.97.188.182`

คำสั่งที่ใช้บ่อย:
| งาน | คำสั่ง |
|---|---|
| ดู log | `docker logs -f reels-engine` |
| รีสตาร์ต | `docker compose restart` |
| แก้ค่า (.env) แล้วใช้ค่าใหม่ | `docker compose up -d` |
| อัปเดตโค้ด | แตก zip ใหม่ทับ (เก็บ .env ไว้) แล้ว `docker compose up -d --build` |

คลิปเก็บไว้ 3 วันแล้วลบอัตโนมัติ (`KEEP_DAYS` ใน .env)

---

## 2) รูปแบบงานที่ส่งเข้า (POST /render)

Header: `X-API-Key: <token>` , `Content-Type: application/json`

```json
{
  "scenes": [
    {"text": "ไมโครเวฟเหม็น คราบแห้งกรัง ใช้มะนาวลูกเดียวจบ!", "headline": "ไมโครเวฟเหม็น?", "image_url": "https://..."},
    {"text": "หั่นมะนาวครึ่งลูก บีบใส่ถ้วยน้ำ แล้วใส่เปลือกลงไปด้วย", "step": "ขั้นที่ 1", "image_url": "https://..."},
    {"text": "อยากได้ตัวช่วยที่เร็วกว่านี้ ลิงก์อยู่ในคอมเมนต์เลยค่ะ", "headline": "อยากเร็วกว่านี้?"}
  ],
  "product_image_url": "https://...รูปสินค้าจาก feed...",
  "cta": "ลิงก์อยู่ในคอมเมนต์",
  "callback_url": "https://hook.eu2.make.com/....",
  "meta": {"caption": "แคปชันโพสต์", "comment": "ลิงก์ Shopee ..."}
}
```
- `scenes` 1–8 ฉาก, ข้อความรวมไม่เกิน **320 ตัวอักษร** (เกินจะตอบ 422 ให้ย่อ)
- **เว้นวรรคระหว่างวลี** — ซับจะตัดบรรทัดและไฮไลต์ทีละวลีตามช่องว่าง
- `image_url` ไม่ใส่ก็ได้ (ใช้พื้นหลังแบรนด์) — ฉากสุดท้ายใช้ `product_image_url` อัตโนมัติ
- ภาพควรเป็นสี่เหลี่ยมจัตุรัสหรือแนวตั้ง
- `callback_url` = เมื่อเสร็จ VPS จะยิงผลไปที่นี่ (พร้อม `meta` เดิม)
- เปลี่ยนเสียงเฉพาะงานได้ด้วย `"voice_id": "..."`
- เพลง: `"music_style": "bright"` (สดใส ค่าเริ่มต้น) หรือ `"lofi"` — ตั้งค่าเริ่มต้นได้ที่ `MUSIC_STYLE` ใน .env; `seed` ต่างกัน = ทำนอง/คีย์/จังหวะต่างกัน

ผลที่ได้ (callback หรือ GET /jobs/{job_id}):
```json
{"job_id":"...","status":"done","video_url":"http://31.97.188.182:8090/files/xxx.mp4",
 "duration":27.4,"chars":265,"model":"eleven_v3","credits_left":98000,"meta":{...}}
```
**แคชเสียง:** ประโยคที่เคยสร้างแล้ว (ข้อความ+เสียง+โมเดลเดียวกัน) ดึงจาก VPS ไม่เสียเครดิต — ผลลัพธ์บอก `tts_cache_hits`, `tts_new`, `chars_billed`; เสียงที่ไม่ได้ใช้ 120 วันลบอัตโนมัติ

ถ้า credits เหลือน้อยกว่า 15,000 ระบบสลับไป `eleven_v4_turbo` ให้เอง (ถ้าตัวสำรองใช้ไม่ได้จะกลับไปใช้โมเดลหลัก)

---

## 3) ต่อกับ Make (2 scenario)

### Scenario A — สั่งทำคลิป
1. (ของเดิม) เลือกหัวข้อ + สินค้าจาก feed
2. **Claude / Anthropic** — ให้เขียน JSON ตาม prompt ด้านล่าง
3. **JSON › Parse JSON**
4. **HTTP › Make a request**
   - URL: `http://31.97.188.182:8090/render` · Method: POST
   - Headers: `X-API-Key` = token จากตอนติดตั้ง
   - Body type: Raw · JSON · ใส่ scenes จากข้อ 3 + `product_image_url` + `callback_url` (URL webhook ของ Scenario B) + `meta` (caption, comment)

### Scenario B — โพสต์ Reels เมื่อคลิปเสร็จ
1. **Webhooks › Custom webhook** (เอา URL ไปใส่เป็น callback_url)
2. **Filter**: `status = done`
3. **HTTP** POST `https://graph.facebook.com/v21.0/{PAGE_ID}/video_reels`
   body: `upload_phase=start`, `access_token={PAGE_TOKEN}` → ได้ `video_id`
4. **HTTP** POST `https://rupload.facebook.com/video-upload/v21.0/{video_id}`
   headers: `Authorization: OAuth {PAGE_TOKEN}`, `file_url: {video_url}`
5. **HTTP** POST `https://graph.facebook.com/v21.0/{PAGE_ID}/video_reels`
   body: `upload_phase=finish`, `video_id`, `video_state=PUBLISHED`, `description={meta.caption}`, `access_token`
6. **Tools › Sleep** 60–120 วินาที (รอ Facebook ประมวลผล)
7. **HTTP** POST `https://graph.facebook.com/v21.0/{video_id}/comments` body: `message={meta.comment}` → ลิงก์ Shopee ในคอมเมนต์แรก

(ใช้ Graph API version เดียวกับที่ scenario โพสต์รูปใช้อยู่ได้เลย)

### Prompt สำหรับ Claude ใน Scenario A
```
เขียนสคริปต์ Reels 25-30 วินาที สำหรับเพจ "บ้านนี้มีดี by ซี"
หัวข้อ: {{topic}}  สินค้า: {{product_name}}
กติกา:
- 4-5 ฉาก ข้อความรวมไม่เกิน 280 ตัวอักษร ภาษาพูดเป็นกันเอง ลงท้าย "ค่ะ"  (เสียงผู้ชายเปลี่ยนเป็น "ครับ")
- ฉาก 1 = hook ปัญหาที่คนเจอ (มี headline สั้นไม่เกิน 22 ตัวอักษร)
- ฉากกลาง = วิธีแก้แบบทำเองได้ ใส่ step "ขั้นที่ 1", "ขั้นที่ 2" ...
- ฉากสุดท้าย = เลือก 1 ประโยคจากรายการนี้แบบคำต่อคำ ห้ามแก้แม้แต่ตัวเดียว (ระบบเก็บเสียงไว้แล้ว ไม่เสียเครดิตซ้ำ):
  1. อยากได้ตัวช่วยที่เร็วกว่านี้ ลิงก์อยู่ในคอมเมนต์เลยค่ะ
  2. ใครขี้เกียจทำเอง มีตัวช่วยดีๆ ลิงก์อยู่ในคอมเมนต์ค่ะ
  3. ตัวช่วยที่ทำให้ง่ายขึ้นอีกเท่าตัว ดูได้ในคอมเมนต์เลยค่ะ
  4. ของใช้ชิ้นนี้ช่วยได้เยอะมาก ลิงก์อยู่ในคอมเมนต์นะคะ
  5. อยากให้งานบ้านง่ายขึ้น ไปดูตัวช่วยในคอมเมนต์กันค่ะ
  6. ใครอยากได้แบบไม่ต้องเหนื่อย กดลิงก์ในคอมเมนต์ได้เลยค่ะ
  (headline สั้นๆ เช่น "อยากเร็วกว่านี้?" "ขี้เกียจทำเอง?" "ง่ายกว่านี้มีไหม?")
- เว้นวรรคระหว่างวลีทุก 2-4 คำ, เขียนตัวเลขเป็นคำอ่าน (สามนาที ไม่ใช่ 3 นาที)
- ห้ามใส่ลิงก์หรืออีโมจิใน text
ตอบเป็น JSON อย่างเดียว:
{"scenes":[{"text":"...","headline":"...","step":null}],"caption":"...","comment":"..."}
```

---

## ปัญหาที่พบบ่อย
- `ElevenLabs error: 401` → key ผิด หรือเปิด IP restriction แต่ IP ไม่ตรง
- `403 ... missing_permissions` → เปิดสิทธิ์ Text to Speech: Access / Voices: Read / User: Access
- `script too long` → ให้ Claude ย่อสคริปต์ (หรือปรับ `MAX_CHARS`)
- Facebook ดึงวิดีโอไม่ได้ → เช็กว่าเปิด `PUBLIC_URL` จากข้างนอกได้ (พอร์ต 8090 เปิดใน firewall ของผู้ให้บริการ VPS ด้วย)
- อยากได้ HTTPS → ชี้โดเมน เช่น `reels.pipvps.cloud` มาที่ VPS แล้วตั้ง reverse proxy (nginx/Caddy) → แก้ `PUBLIC_URL` ใน .env
