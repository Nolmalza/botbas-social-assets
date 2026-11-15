# ติดตั้ง Codex ให้ทำ Reels บ้านนี้มีดี by ซี (ให้ Hermes ทำบน VPS)

เป้าหมาย: ให้ Codex CLI บน VPS ทำ Reels ของเพจ "บ้านนี้มีดี by ซี" **5 ใน 10 รอบ/วัน**
(11:07, 15:07, 17:07, 19:07, 21:07 เวลาไทย) ส่วน Claude ทำอีก 5 รอบ (13:07, 16:07, 18:07, 20:07, 22:07)
ใช้ reels-engine และ Make scenario 6940105 ตัวเดิมทั้งหมด ไม่ต้องแก้อะไรใน engine หรือ Make

> ห้ามแตะ /opt/reels-engine (ใช้อ่านอย่างเดียว) และห้ามใส่ key/token ใดๆ ลงใน git

## สิ่งที่ BAS ต้องเตรียมเอง (Hermes ทำแทนไม่ได้)
1. **Make API token** — Make → Profile → API access → Add token, เลือก scope อย่างน้อย
   `scenarios:read`, `scenarios:run`, `executions:read` แล้วส่ง token ให้ Hermes ใส่ใน `.env`
   (หรือพิมพ์ใส่ `.env` เอง)
2. **Google service account** สำหรับอ่าน/เขียนชีต
   - Google Cloud Console → สร้าง project (หรือใช้ที่มี) → เปิด **Google Sheets API**
   - IAM → Service accounts → Create → Keys → Add key → JSON → ได้ไฟล์ .json
   - เปิดชีต ShopeeProducts_06112026 → Share → ใส่อีเมล service account (…@….iam.gserviceaccount.com) สิทธิ์ **Editor**
   - เอาไฟล์ JSON ไปวางบน VPS ที่ `/opt/codex-reels/gsa.json` (chmod 600)
3. **ล็อกอิน Codex** ด้วยบัญชี ChatGPT (ขั้นที่ 3 ด้านล่าง) — ต้องทำเองเพราะต้องยืนยันในเบราว์เซอร์

## ขั้นตอนสำหรับ Hermes
```bash
# 1) ติดตั้ง Node 20+ (ถ้ายังไม่มี) และ Codex CLI
node -v || (curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt-get install -y nodejs)
sudo npm i -g @openai/codex
codex --version

# 2) ดึงชุดไฟล์ runner
sudo git clone -b codex-reels --single-branch --depth 1 https://github.com/Nolmalza/botbas-social-assets /opt/codex-reels
sudo chown -R "$USER":"$USER" /opt/codex-reels
cd /opt/codex-reels
python3 -m pip install --break-system-packages -r requirements.txt
cp .env.example .env && chmod 600 .env      # แล้วใส่ MAKE_TOKEN (และ TELEGRAM_* ถ้าต้องการ)
chmod +x run-reel.sh tools/*.py

# 3) ล็อกอิน Codex (บน server ที่ไม่มีเบราว์เซอร์ ให้ใช้แบบ device code)
codex login --help        # ดูชื่อ option ของเวอร์ชันที่ติดตั้ง
codex login --device-auth # หรือคำสั่งที่ --help แนะนำ → BAS เปิดลิงก์แล้วใส่รหัส
```
ให้ล็อกอินด้วย **user เดียวกับที่จะรัน cron** (ไฟล์ auth อยู่ใน ~/.codex ของ user นั้น)

**เปิด web search ให้ Codex** (ใช้ตรวจข้อเท็จจริงของทริค): ดู `codex --help` / เอกสาร config ของเวอร์ชันที่ติดตั้ง
แล้วเปิดใน `~/.codex/config.toml` ถ้าเปิดไม่ได้ก็ยังรันได้ (skill สั่งให้ใช้แต่ทริคที่ปลอดภัยและรู้แน่)

## ทดสอบ (ก่อนตั้ง cron)
```bash
cd /opt/codex-reels && set -a && . ./.env && set +a
python3 tools/sheet.py get "ตั้งค่า!A1:B3"          # ต้องได้ JSON ข้อมูลชีต
python3 tools/sheet.py tail "ประวัติโพสต์" 3
curl -s http://127.0.0.1:8090/health                # engine ต้องตอบ
```
ถ้าผ่านทั้งหมด ให้ลองรันจริง 1 คลิป (จะโพสต์ขึ้นเพจจริง):
```bash
./run-reel.sh; ls logs/; cat logs/*-summary.txt
```
**สำคัญ:** รันทดสอบในชั่วโมงที่ Claude ไม่ได้ทำ (เช่น 14:xx หรือ 23:xx เวลาไทย) เพื่อไม่ให้ชนกัน
แล้วเช็คว่าคลิปขึ้นเพจ, คอมเมนต์แรกมีลิงก์, และมีแถวใหม่ใน "ประวัติโพสต์" ลงท้าย "(codex)"

## ตั้ง cron (หลังทดสอบผ่าน)
เช็ค timezone ของเครื่องก่อน: `timedatectl | grep "Time zone"`

ถ้าเครื่องเป็น **UTC** — `crontab -e` (user เดียวกับที่ล็อกอิน codex) แล้วใส่:
```
PATH=/usr/local/bin:/usr/bin:/bin
7 4,8,10,12,14 * * * /opt/codex-reels/run-reel.sh
```
ถ้าเครื่องเป็น **Asia/Bangkok**:
```
PATH=/usr/local/bin:/usr/bin:/bin
7 11,15,17,19,21 * * * /opt/codex-reels/run-reel.sh
```
(ถ้า `which codex` ไม่ได้อยู่ใน /usr/local/bin ให้เพิ่ม path นั้นใน PATH)

เสร็จแล้วแจ้ง BAS ว่า "Codex พร้อมแล้ว" เพื่อให้ Claude ตัดรอบของตัวเองเหลือ 13,16,18,20,22

## ดูผล / แก้ปัญหา
- log ของแต่ละรอบ: `/opt/codex-reels/logs/YYYY-MM-DD-HH.log`, สรุป: `...-summary.txt`
- ส่งสรุปเข้า Telegram: ใส่ `TELEGRAM_BOT_TOKEN` และ `TELEGRAM_CHAT_ID` ใน `.env`
- `401` จาก Make → token ผิดหรือ scope ไม่ครบ
- `PermissionError` / `SpreadsheetNotFound` จากชีต → ยังไม่ได้ share ชีตให้อีเมล service account
- Codex ต่อเน็ตไม่ได้ใน sandbox → ใน run-reel.sh เปลี่ยน
  `-s workspace-write -c sandbox_workspace_write.network_access=true` เป็น `--dangerously-bypass-approvals-and-sandbox`
  (ใช้ได้เพราะเครื่องนี้รันงานนี้งานเดียวในโฟลเดอร์นี้)
- อัปเดตชุดไฟล์: `cd /opt/codex-reels && git pull`
- หยุด Codex ชั่วคราว: comment บรรทัดใน crontab แล้วบอก BAS ให้ Claude กลับไปทำครบ 10 รอบ
