"""ElevenLabs TTS with character timestamps (+ dummy provider for testing)."""
import base64, os, subprocess, json, hashlib, shutil, requests

API = "https://api.elevenlabs.io/v1"
KEY = os.environ.get("ELEVENLABS_API_KEY", "")
MODEL = os.environ.get("ELEVEN_MODEL", "eleven_v4")
FALLBACK_MODEL = os.environ.get("ELEVEN_FALLBACK_MODEL", "eleven_v4_turbo")
FALLBACK_BELOW = int(os.environ.get("FALLBACK_WHEN_CREDITS_BELOW", "15000"))
PROVIDER = os.environ.get("TTS_PROVIDER", "elevenlabs")


def resolve_voice(name):
    """ElevenLabs voice name (as shown in My Voices) -> voice_id. Cached in DATA_DIR/voice_ids.json.
    Exact (case-insensitive) match first, then names starting with / containing it."""
    path = os.path.join(os.environ.get("DATA_DIR", "/data"), "voice_ids.json")
    try: cache = json.load(open(path))
    except Exception: cache = {}
    k = name.strip().lower()
    if k in cache: return cache[k]
    if PROVIDER == "dummy": return "dummy"
    r = requests.get(f"{API}/voices", headers={"xi-api-key": KEY}, timeout=30); r.raise_for_status()
    vs = r.json().get("voices", [])
    nm = lambda v: (v.get("name") or "").strip().lower()
    hit = next((v for v in vs if nm(v) == k), None) or next((v for v in vs if nm(v).startswith(k)), None) \
        or next((v for v in vs if k in nm(v)), None)
    if not hit:
        raise RuntimeError(f"voice '{name}' not found in My Voices ({len(vs)} voices). Add it from the Voice Library first.")
    cache[k] = hit["voice_id"]
    try: json.dump(cache, open(path, "w"))
    except Exception: pass
    return hit["voice_id"]


def credits_left():
    """Remaining characters in this billing period, or None if unknown."""
    try:
        r = requests.get(f"{API}/user/subscription", headers={"xi-api-key": KEY}, timeout=15)
        r.raise_for_status(); j = r.json()
        return int(j["character_limit"]) - int(j["character_count"])
    except Exception:
        return None


def pick_model():
    left = credits_left()
    if left is not None and left < FALLBACK_BELOW:
        return FALLBACK_MODEL, left
    return MODEL, left


CACHE = os.path.join(os.environ.get("DATA_DIR", "/data"), "tts_cache")
STATS = {"hits": 0, "misses": 0, "chars_billed": 0}


SPEED = float(os.environ.get("VOICE_SPEED", "1.0"))   # 0.7-1.2; >1 = faster, less drawn-out speech


def _key(text, voice_id, model):
    parts = [text.strip(), voice_id, model, os.environ.get("VOICE_STABILITY", "0.5")]
    if SPEED != 1.0: parts.append(f"speed={SPEED}")   # keeps old cache valid when speed is 1.0
    raw = json.dumps(parts, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


STITCH = os.environ.get("TTS_STITCH", "1") != "0"   # send neighbour sentences as context (smoother prosody)
_STITCH_OK = {"v": True}
_SPEED_OK = {"v": True}


def synth(text, out_mp3, voice_id, model, prev_text=None, next_text=None):
    """Cached TTS: same sentence + voice + model + settings = reuse audio from disk (no credits).
    prev_text/next_text are sent only as context (not billed, not spoken) so each scene keeps the
    intonation of one continuous talk; the cache key stays text-only so fixed CTA lines stay cached."""
    os.makedirs(CACHE, exist_ok=True)
    k = _key(text, voice_id, model); mp3 = f"{CACHE}/{k}.mp3"; js = f"{CACHE}/{k}.json"
    if os.path.exists(mp3) and os.path.exists(js):
        shutil.copyfile(mp3, out_mp3); os.utime(mp3); STATS["hits"] += 1
        return [tuple(x) for x in json.load(open(js))]
    align = _synth_api(text, out_mp3, voice_id, model, prev_text, next_text)
    shutil.copyfile(out_mp3, mp3 + ".tmp"); os.replace(mp3 + ".tmp", mp3)
    json.dump(align, open(js, "w"), ensure_ascii=False)
    STATS["misses"] += 1; STATS["chars_billed"] += len(text)
    return align


def _synth_api(text, out_mp3, voice_id, model, prev_text=None, next_text=None):
    """Write mp3, return list of (char, start, end)."""
    if PROVIDER == "dummy":
        return _dummy(text, out_mp3)
    body = {"text": text, "model_id": model,
            "voice_settings": {"stability": float(os.environ.get("VOICE_STABILITY", "0.5")),
                               "similarity_boost": 0.75}}
    if SPEED != 1.0 and _SPEED_OK["v"]:
        body["voice_settings"]["speed"] = max(0.7, min(1.2, SPEED))
    if "v2" in model:  # only v2.x models take language_code; v3/v4 auto-detect
        body["language_code"] = "th"
    if STITCH and _STITCH_OK["v"]:
        if prev_text: body["previous_text"] = prev_text[-300:]
        if next_text: body["next_text"] = next_text[:300]
    last = None
    for attempt in range(4):
        try:
            r = requests.post(f"{API}/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128",
                              headers={"xi-api-key": KEY, "Content-Type": "application/json"},
                              data=json.dumps(body), timeout=120)
            if r.status_code == 200:
                j = r.json()
                open(out_mp3, "wb").write(base64.b64decode(j["audio_base64"]))
                a = j.get("alignment") or j.get("normalized_alignment") or {}
                al = list(zip(a.get("characters", []), a.get("character_start_times_seconds", []),
                              a.get("character_end_times_seconds", [])))
                if SPEED != 1.0 and "speed" not in body["voice_settings"]:
                    al = _tempo(out_mp3, al, SPEED)   # model ignored/refused speed: speed up the audio instead
                return al
            last = f"{r.status_code} {r.text[:300]}"
            if r.status_code in (400, 422) and "speed" in body["voice_settings"] and "speed" in r.text.lower():
                body["voice_settings"].pop("speed"); _SPEED_OK["v"] = False
                continue
            if r.status_code in (400, 422) and ("previous_text" in body or "next_text" in body):
                # model does not accept context: drop it for this and later requests, retry
                body.pop("previous_text", None); body.pop("next_text", None); _STITCH_OK["v"] = False
                continue
            if r.status_code in (400, 401, 403, 422):
                break
        except requests.RequestException as e:
            last = str(e)
    raise RuntimeError(f"ElevenLabs error: {last}")


def _tempo(mp3, align, speed):
    """Pitch-preserving speed change with ffmpeg atempo; scale the character timestamps to match."""
    tmp = mp3 + ".tempo.mp3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-filter:a", f"atempo={speed}",
                    "-b:a", "128k", tmp], check=True)
    os.replace(tmp, mp3)
    return [(c, st / speed, en / speed) for c, st, en in align]


def _dummy(text, out_mp3):
    dur = max(1.0, len(text) * 0.075)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"sine=frequency=220:duration={dur}", "-af", "volume=0.05", out_mp3], check=True)
    step = dur / max(1, len(text))
    return [(c, i * step, (i + 1) * step) for i, c in enumerate(text)]
