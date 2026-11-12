"""reels-engine API.
POST /render      (X-API-Key)  -> {job_id, status_url}
GET  /jobs/{id}   (X-API-Key)  -> {status, video_url, ...}
GET  /files/{id}.mp4           -> the video (public, unguessable id; deleted after KEEP_DAYS)
GET  /assets                   -> drawing library catalog {name: {desc, w, h, source}} (public)
GET  /assets/{name}.svg        -> one library drawing (public)
GET  /health

Themes: default = light baannee card look; "theme":"dark" + "brand":{name,hl,site,footer,tag} = PipGuard-style
trading look for any brand (app/darktheme.py, example sample_job_botbas.json). "voice_name" picks an ElevenLabs
voice by its My Voices name (cached in DATA_DIR/voice_ids.json) instead of voice_id.
"""
import os, json, time, uuid, shutil, threading, queue, traceback
import requests
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import render, assets

TOKEN = os.environ["ENGINE_TOKEN"]
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")
DATA = os.environ.get("DATA_DIR", "/data")
KEEP_DAYS = float(os.environ.get("KEEP_DAYS", "3"))
os.makedirs(f"{DATA}/jobs", exist_ok=True); os.makedirs(f"{DATA}/files", exist_ok=True)

app = FastAPI(title="reels-engine")
Q = queue.Queue(); JOBS = {}


class Scene(BaseModel):
    text: str
    image_url: str | None = None
    svg: str | None = None            # inline SVG illustration (no text), rendered on the VPS
    headline: str | None = None
    step: str | None = None


class Job(BaseModel):
    scenes: list[Scene]
    product_image_url: str | None = None
    cta: str | None = "ลิงก์อยู่ในคอมเมนต์"
    show_cta: bool = True
    voice_id: str | None = None
    voice_name: str | None = None     # ElevenLabs voice name (My Voices), resolved on the VPS, e.g. "zie"
    theme: str | None = None          # None/"light" = baannee card look, "dark" = PipGuard-style trading look
    brand: dict | None = None         # dark theme: {"name","hl","site","footer","tag"}
    seed: int | None = None
    music_style: str | None = None    # "bright" (default) or "lofi"
    callback_url: str | None = None   # e.g. a Make custom webhook
    hook: dict | None = None          # cover, first ~3 s: {"style":"card"(default)|"pop", "tag", "title":"line1\nline *blue*", "badge", "points":[..3], "note", "footer"}
    meta: dict | None = None          # passed back untouched (caption, comment, page id ...)
    assets: dict | None = None        # optional {name: "<svg ...>"} library drawings sent with the job


def auth(k):
    if k != TOKEN: raise HTTPException(401, "bad X-API-Key")


def save(jid):
    json.dump(JOBS[jid], open(f"{DATA}/jobs/{jid}.json", "w"), ensure_ascii=False)


def worker():
    while True:
        jid = Q.get(); j = JOBS[jid]; j["status"] = "rendering"; save(jid)
        wd = f"/tmp/work/{jid}"
        try:
            res = render.render_job(j["request"], wd, log=lambda m: print(jid, m, flush=True))
            shutil.move(res["path"], f"{DATA}/files/{jid}.mp4")
            if os.path.exists(res.get("cover") or ""):
                shutil.move(res["cover"], f"{DATA}/files/{jid}.jpg"); j["cover_url"] = f"{PUBLIC_URL}/files/{jid}.jpg"
            j.update(status="done", video_url=f"{PUBLIC_URL}/files/{jid}.mp4", duration=res["duration"],
                     chars=res["chars"], model=res["model"], credits_left=res["credits_left"], music=res.get("music"),
                     tts_cache_hits=res.get("tts_cache_hits"), tts_new=res.get("tts_new"), chars_billed=res.get("chars_billed"), assets_saved=res.get("assets_saved"))
        except Exception as e:
            traceback.print_exc(); j.update(status="error", error=str(e))
        finally:
            shutil.rmtree(wd, ignore_errors=True); j["finished_at"] = time.time(); save(jid)
        cb = j["request"].get("callback_url") or os.environ.get("DEFAULT_CALLBACK_URL")
        if cb:
            try:
                out = {k: v for k, v in j.items() if k != "request"}; out["meta"] = j["request"].get("meta")
                requests.post(cb, json=out, timeout=30)
            except Exception as e:
                print("callback failed", e)


def janitor():
    while True:
        cut = time.time() - KEEP_DAYS * 86400
        for d in ("files", "jobs"):
            for f in os.listdir(f"{DATA}/{d}"):
                p = f"{DATA}/{d}/{f}"
                if os.path.getmtime(p) < cut: os.remove(p)
        cdir = f"{DATA}/tts_cache"; ccut = time.time() - 120 * 86400
        if os.path.isdir(cdir):
            for f in os.listdir(cdir):
                if os.path.getmtime(f"{cdir}/{f}") < ccut: os.remove(f"{cdir}/{f}")
        time.sleep(3600)


threading.Thread(target=worker, daemon=True).start()
threading.Thread(target=janitor, daemon=True).start()


@app.get("/health")
def health():
    return {"ok": True, "queue": Q.qsize()}


@app.post("/render")
def create(job: Job, x_api_key: str = Header(None)):
    auth(x_api_key)
    if not job.scenes: raise HTTPException(422, "scenes required")
    chars = sum(len(s.text) for s in job.scenes); mx = int(os.environ.get("MAX_CHARS", "700"))
    if chars > mx: raise HTTPException(422, f"script too long: {chars} chars > {mx}")
    jid = uuid.uuid4().hex
    JOBS[jid] = {"job_id": jid, "status": "queued", "created_at": time.time(), "request": job.model_dump()}
    save(jid); Q.put(jid)
    return {"job_id": jid, "status": "queued", "status_url": f"{PUBLIC_URL}/jobs/{jid}"}


@app.get("/jobs/{jid}")
def status(jid: str, x_api_key: str = Header(None)):
    auth(x_api_key)
    j = JOBS.get(jid)
    if not j and os.path.exists(f"{DATA}/jobs/{jid}.json"): j = json.load(open(f"{DATA}/jobs/{jid}.json"))
    if not j: raise HTTPException(404, "not found")
    return {k: v for k, v in j.items() if k != "request"}


@app.get("/assets")
def asset_list():
    return assets.catalog()


@app.get("/assets/{name}")
def asset_file(name: str):
    n = name[:-4] if name.endswith(".svg") else name
    if not assets.NAME_OK.match(n): raise HTTPException(404)
    for d in (assets.SAVED, assets.BUILTIN):
        p = f"{d}/{n}.svg"
        if os.path.exists(p): return FileResponse(p, media_type="image/svg+xml")
    raise HTTPException(404)


@app.get("/files/{name}")
def files(name: str):
    if not name.endswith((".mp4", ".jpg")) or "/" in name or ".." in name: raise HTTPException(404)
    p = f"{DATA}/files/{name}"
    if not os.path.exists(p): raise HTTPException(404)
    return FileResponse(p, media_type="video/mp4" if name.endswith(".mp4") else "image/jpeg")
