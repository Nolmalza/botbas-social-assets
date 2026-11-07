"""reels-engine API.
POST /render      (X-API-Key)  -> {job_id, status_url}
GET  /jobs/{id}   (X-API-Key)  -> {status, video_url, ...}
GET  /files/{id}.mp4           -> the video (public, unguessable id; deleted after KEEP_DAYS)
GET  /health
"""
import os, json, time, uuid, shutil, threading, queue, traceback
import requests
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import render

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
    headline: str | None = None
    step: str | None = None


class Job(BaseModel):
    scenes: list[Scene]
    product_image_url: str | None = None
    cta: str | None = "ลิงก์อยู่ในคอมเมนต์"
    show_cta: bool = True
    voice_id: str | None = None
    seed: int | None = None
    music_style: str | None = None    # "bright" (default) or "lofi"
    callback_url: str | None = None   # e.g. a Make custom webhook
    meta: dict | None = None          # passed back untouched (caption, comment, page id ...)


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
            j.update(status="done", video_url=f"{PUBLIC_URL}/files/{jid}.mp4", duration=res["duration"],
                     chars=res["chars"], model=res["model"], credits_left=res["credits_left"], music=res.get("music"))
        except Exception as e:
            traceback.print_exc(); j.update(status="error", error=str(e))
        finally:
            shutil.rmtree(wd, ignore_errors=True); j["finished_at"] = time.time(); save(jid)
        cb = j["request"].get("callback_url")
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
    chars = sum(len(s.text) for s in job.scenes); mx = int(os.environ.get("MAX_CHARS", "320"))
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


@app.get("/files/{name}")
def files(name: str):
    if not name.endswith(".mp4") or "/" in name or ".." in name: raise HTTPException(404)
    p = f"{DATA}/files/{name}"
    if not os.path.exists(p): raise HTTPException(404)
    return FileResponse(p, media_type="video/mp4")
