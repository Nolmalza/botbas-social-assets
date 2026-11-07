"""ElevenLabs TTS with character timestamps (+ dummy provider for testing)."""
import base64, os, subprocess, json, requests

API = "https://api.elevenlabs.io/v1"
KEY = os.environ.get("ELEVENLABS_API_KEY", "")
MODEL = os.environ.get("ELEVEN_MODEL", "eleven_v4")
FALLBACK_MODEL = os.environ.get("ELEVEN_FALLBACK_MODEL", "eleven_flash_v2_5")
FALLBACK_BELOW = int(os.environ.get("FALLBACK_WHEN_CREDITS_BELOW", "15000"))
PROVIDER = os.environ.get("TTS_PROVIDER", "elevenlabs")


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


def synth(text, out_mp3, voice_id, model):
    """Write mp3, return list of (char, start, end)."""
    if PROVIDER == "dummy":
        return _dummy(text, out_mp3)
    body = {"text": text, "model_id": model,
            "voice_settings": {"stability": float(os.environ.get("VOICE_STABILITY", "0.5")),
                               "similarity_boost": 0.75}}
    if "v2" in model:  # only v2.x models take language_code; v3/v4 auto-detect
        body["language_code"] = "th"
    last = None
    for attempt in range(3):
        try:
            r = requests.post(f"{API}/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128",
                              headers={"xi-api-key": KEY, "Content-Type": "application/json"},
                              data=json.dumps(body), timeout=120)
            if r.status_code == 200:
                j = r.json()
                open(out_mp3, "wb").write(base64.b64decode(j["audio_base64"]))
                a = j.get("alignment") or j.get("normalized_alignment") or {}
                return list(zip(a.get("characters", []), a.get("character_start_times_seconds", []),
                                a.get("character_end_times_seconds", [])))
            last = f"{r.status_code} {r.text[:300]}"
            if r.status_code in (400, 401, 403, 422):
                break
        except requests.RequestException as e:
            last = str(e)
    raise RuntimeError(f"ElevenLabs error: {last}")


def _dummy(text, out_mp3):
    dur = max(1.0, len(text) * 0.075)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"sine=frequency=220:duration={dur}", "-af", "volume=0.05", out_mp3], check=True)
    step = dur / max(1, len(text))
    return [(c, i * step, (i + 1) * step) for i, c in enumerate(text)]
