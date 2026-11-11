"""Render a 9:16 Reel from scenes: image card + karaoke Thai subtitles + voice + lofi."""
import io, math, os, subprocess, json, random
import numpy as np, requests, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageOps

import tts, lofi, bright, anim, cover, assets

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
F_BOLD = os.path.join(HERE, "fonts/Kanit-Bold.ttf")
F_SEMI = os.path.join(HERE, "fonts/Kanit-SemiBold.ttf")
BRAND = os.environ.get("BRAND_NAME", "บ้านนี้มีดี by ซี")
BG = (255, 246, 229); BLOB = (255, 232, 196)
INK = (52, 62, 74); ACC = (255, 122, 69); RED = (210, 70, 60); GREEN = (46, 160, 110)
HL = (255, 213, 74)
CARD = (80, 400, 1000, 1290)          # x0,y0,x1,y1
SUB_Y = 1330

_fc = {}
def font(sz, semi=False):
    k = (sz, semi)
    if k not in _fc: _fc[k] = ImageFont.truetype(F_SEMI if semi else F_BOLD, sz)
    return _fc[k]

def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def back(x):
    x = max(0.0, min(1.0, x)); c = 1.7
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def load_svg(svg):
    """Rasterize an inline SVG string (scene illustration) to a PIL image."""
    if not svg: return None
    try:
        import cairosvg
        png = cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=1100)
        return Image.open(io.BytesIO(png)).convert("RGB")
    except Exception as e:
        print("svg render failed", e); return None


def load_image(url, cache_dir):
    if not url: return None
    try:
        if url.startswith("file://"):
            im = Image.open(url[7:])
        else:
            r = requests.get(url, timeout=30, headers={"User-Agent": "reels-engine/1.0"})
            r.raise_for_status(); im = Image.open(io.BytesIO(r.content))
        im = ImageOps.exif_transpose(im).convert("RGB")
        return im
    except Exception as e:
        print("image load failed", url, e); return None


def house_icon(sz=64):
    s = 2; im = Image.new("RGBA", (sz * s, sz * s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon([(sz / 2 * s, 4 * s), (4 * s, sz * 0.48 * s), ((sz - 4) * s, sz * 0.48 * s)], fill=ACC)
    d.rectangle([12 * s, sz * 0.45 * s, (sz - 12) * s, (sz - 4) * s], fill=ACC)
    d.rectangle([sz * 0.4 * s, sz * 0.62 * s, sz * 0.6 * s, (sz - 4) * s], fill=(255, 255, 255))
    return im.resize((sz, sz), Image.LANCZOS)


def pill(d, y, s, sz, bg, fg=(255, 255, 255), pad=36):
    while d.textlength(s, font=font(sz)) > W - 160 and sz > 30: sz -= 2
    f = font(sz); w = d.textlength(s, font=f); x0 = (W - w) / 2 - pad
    d.rounded_rectangle([x0, y, x0 + w + 2 * pad, y + sz * 1.55], int(sz * 0.6), fill=bg)
    d.text(((W - w) / 2, y + sz * 0.12), s, font=f, fill=fg)


def static_base():
    img = Image.new("RGBA", (W, H), BG + (255,)); d = ImageDraw.Draw(img)
    d.ellipse([-260, -200, 520, 520], fill=BLOB); d.ellipse([700, 1450, 1400, 2150], fill=BLOB)
    f0 = font(60); w0 = d.textlength(BRAND, font=f0); x0 = (W - w0) / 2 + 40
    img.alpha_composite(house_icon(), (int(x0 - 80), 128))
    d.text((x0, 112), BRAND, font=f0, fill=INK)
    return img


# ---------- subtitle layout ----------
def phrases_with_times(text, align, voice_offset):
    words = text.split()
    chars = "".join(c for c, _, _ in align)
    out = []; pos = 0; n = max(1, len(text))
    total = align[-1][2] if align else len(text) * 0.075
    for w in words:
        i = text.find(w, pos); pos = i + len(w)
        if align and len(align) == len(text):
            t = align[i][1]
        elif align:
            j = chars.find(w)
            t = align[j][1] if j >= 0 else total * i / n
        else:
            t = total * i / n
        out.append([w, t + voice_offset])
    return out


def wrap(phrases, d, sz):
    lines = [[]]; f = font(sz, True); sp = d.textlength(" ", font=f)
    for k, (w, _) in enumerate(phrases):
        cur = sum(d.textlength(phrases[j][0], font=f) for j in lines[-1]) + sp * len(lines[-1])
        if lines[-1] and cur + d.textlength(w, font=f) > W - 220:
            lines.append([])
        lines[-1].append(k)
    return lines


def draw_subs(img, phrases, t, layout):
    lines, sz = layout
    d = ImageDraw.Draw(img); f = font(sz, True); sp = d.textlength(" ", font=f)
    cur = 0
    for k, (_, st) in enumerate(phrases):
        if t >= st - 0.05: cur = k
    li = next(i for i, L in enumerate(lines) if cur in L)
    start = (li // 2) * 2; shown = lines[start:start + 2]
    a = ease(t / 0.25); lh = int(sz * 1.42)
    if a < 0.02: return
    d.rounded_rectangle([60, SUB_Y, W - 60, SUB_Y + len(shown) * lh + 44], 36, fill=(52, 62, 74, int(230 * a)))
    for r, L in enumerate(shown):
        widths = [d.textlength(phrases[k][0], font=f) for k in L]
        x = (W - (sum(widths) + sp * (len(L) - 1))) / 2; y = SUB_Y + 20 + r * lh
        for k, wd in zip(L, widths):
            col = HL if k == cur else (255, 255, 255)
            d.text((x, y), phrases[k][0], font=f, fill=col + (int(255 * a),)); x += wd + sp


def sub_layout(phrases):
    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    sz = 64
    while sz > 44:
        biggest = max(d.textlength(w, font=font(sz, True)) for w, _ in phrases)
        if biggest <= W - 220: break
        sz -= 2
    return wrap(phrases, d, sz), sz


# ---------- card ----------
def make_card_src(im, idx):
    cw, ch = CARD[2] - CARD[0], CARD[3] - CARD[1]
    if im is None:
        g = Image.new("RGB", (cw, ch), (255, 225, 180)); d = ImageDraw.Draw(g)
        for k in range(0, ch, 6):
            c = int(255 - 30 * k / ch); d.line([(0, k), (cw, k)], fill=(255, c - 20, c - 70), width=6)
        g.paste(house_icon(260).convert("RGB"), ((cw - 260) // 2, (ch - 260) // 2), house_icon(260))
        im = g
    # cover-fit at 1.12x so we can pan/zoom
    sc = max(cw * 1.12 / im.width, ch * 1.12 / im.height)
    return im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)


def card_mask():
    cw, ch = CARD[2] - CARD[0], CARD[3] - CARD[1]
    m = Image.new("L", (cw * 2, ch * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, cw * 2, ch * 2], 80, fill=255)
    return m.resize((cw, ch), Image.LANCZOS)


def draw_card(img, src, mask, t, D, idx, live=None, still_start=False, talk=None):
    """live: AnimSVG -> render the animated frame directly (no Ken Burns)."""
    cw, ch = CARD[2] - CARD[0], CARD[3] - CARD[1]
    if live is not None:
        crop = live.frame(t, cw, ch, D, talk)
    else:
        p = t / max(D, 0.1)
        z = 1.0 + 0.10 * (p if idx % 2 == 0 else 1 - p)
        vw, vh = cw / z, ch / z
        vw *= src.width / (cw * 1.12); vh *= src.height / (ch * 1.12)
        vw = min(vw, src.width); vh = min(vh, src.height)
        cx = src.width / 2 + (src.width - vw) / 2 * (0.6 * math.sin(idx * 1.7)) * (2 * p - 1) * 0.8
        cy = src.height / 2
        box = (cx - vw / 2, cy - vh / 2, cx + vw / 2, cy + vh / 2)
        crop = src.resize((cw, ch), Image.BILINEAR, box=box)
    # scene transition: first scene pops in, later scenes slide in from alternating sides with a small tilt
    sh = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); sh.paste(Image.new("RGBA", (cw, ch), (0, 0, 0, 50)), (0, 0), mask)
    card = crop.convert("RGBA"); card.putalpha(mask)
    dx = 0; rot = 0.0
    if idx == 0 and still_start:
        pass
    elif idx == 0:
        a = back(t / 0.45); s = 0.85 + 0.15 * a
        if s != 1:
            nw, nh = int(cw * s), int(ch * s)
            card = card.resize((nw, nh), Image.BILINEAR); sh = sh.resize((nw, nh), Image.BILINEAR)
    else:
        p = back(t / 0.5); side = 1 if idx % 2 else -1
        dx = int(side * W * (1 - p)); rot = side * -6 * (1 - min(1, t / 0.5))
    if rot:
        card = card.rotate(rot, Image.BICUBIC, expand=True); sh = sh.rotate(rot, Image.BICUBIC, expand=True)
    x = int((CARD[0] + CARD[2]) / 2 - card.width / 2) + dx; y = int((CARD[1] + CARD[3]) / 2 - card.height / 2)
    img.alpha_composite(sh, (x + 10, y + 16)); img.alpha_composite(card, (x, y))
    if not rot:
        ImageDraw.Draw(img).rounded_rectangle([x, y, x + card.width, y + card.height], 40, outline=INK, width=6)


# ---------- hook cover (first ~3 s; frame 0 = Reel cover) ----------
HOOK_DUR = float(os.environ.get("HOOK_SECONDS", "3.0"))


def _hook_segments(line):
    """'ตื่นกลางดึก *หลับต่อไม่ได้*' -> [(text, highlighted)]"""
    out = []; hl = False
    for k, part in enumerate(line.split("*")):
        if part: out.append((part, hl))
        hl = not hl
    return out


def _outlined(d, xy, txt, f, fill, stroke, sw):
    d.text(xy, txt, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke)


def draw_hook(img, hook, t, cover_img=None):
    """card style: full opaque cover (same look as the page's image posts), fades out at the end."""
    if cover_img is not None:
        if t >= HOOK_DUR: return
        fade = 1.0 if t < HOOK_DUR - 0.35 else max(0.0, (HOOK_DUR - t) / 0.35)
        if fade >= 1: img.alpha_composite(cover_img); return
        c = cover_img.copy(); c.putalpha(int(255 * fade)); img.alpha_composite(c); return
    _draw_hook_pop(img, hook, t)


def _draw_hook_pop(img, hook, t):
    """Big bold title card over a dimmed scene. Fully visible from frame 0 (no fade-in) so the
    auto-picked cover / first frame already reads well; fades out at the end of HOOK_DUR."""
    if t >= HOOK_DUR: return
    fade = 1.0 if t < HOOK_DUR - 0.35 else max(0.0, (HOOK_DUR - t) / 0.35)
    a = int(255 * fade)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    d.rectangle([0, 0, W, H], fill=(30, 36, 44, int(150 * fade)))
    lines = [l for l in (hook.get("title") or "").split("\n") if l.strip()][:3]
    # size every line to fit, cap 150 px; whole block uses the smallest so it looks even
    sz = 150
    for l in lines:
        while d.textlength(l.replace("*", ""), font=font(sz)) > W - 150 and sz > 70: sz -= 4
    f = font(sz); lh = int(sz * 1.32)
    block = lh * len(lines)
    y = int(H * 0.47 - block / 2)
    tag = hook.get("tag")
    if tag:
        tf = font(56); tw = d.textlength(tag, font=tf)
        ty = y - 140; d.rounded_rectangle([(W - tw) / 2 - 40, ty, (W + tw) / 2 + 40, ty + 96], 48, fill=RED + (a,))
        d.text(((W - tw) / 2, ty + 10), tag, font=tf, fill=(255, 255, 255, a))
    pulse = 1 + 0.03 * math.sin(t * 7)
    for i, l in enumerate(lines):
        segs = _hook_segments(l)
        widths = [d.textlength(sg, font=f) for sg, _ in segs]; x = (W - sum(widths)) / 2
        ly = y + i * lh
        for (sg, hl), wd in zip(segs, widths):
            if hl:
                pad = 18 * pulse
                d.rounded_rectangle([x - pad, ly + sz * 0.08 - pad / 2, x + wd + pad, ly + sz * 1.22 + pad / 2], 24,
                                    fill=HL + (a,))
                _outlined(d, (x, ly), sg, f, RED + (a,), (255, 255, 255, a), 0)
            else:
                _outlined(d, (x, ly), sg, f, (255, 255, 255, a), INK + (a,), 10)
            x += wd
    badge = hook.get("badge")
    if badge:
        bf = font(64); bw = d.textlength(badge, font=bf); by = y + block + 60
        d.rounded_rectangle([(W - bw) / 2 - 50, by, (W + bw) / 2 + 50, by + 112], 56, fill=GREEN + (a,))
        d.text(((W - bw) / 2, by + 14), badge, font=bf, fill=(255, 255, 255, a))
        ay = by + 140 + 14 * math.sin(t * 8)
        d.polygon([(W / 2 - 40, ay), (W / 2 + 40, ay), (W / 2, ay + 46)], fill=(255, 255, 255, a))
    img.alpha_composite(ov)


def draw_cta(img, t, text):
    a = back((t - 0.6) / 0.5)
    if a <= 0: return
    d = ImageDraw.Draw(img); sz = int(72 * max(0.3, min(a, 1.05)))
    while d.textlength(text, font=font(sz)) > W - 340 and sz > 30: sz -= 2
    w = d.textlength(text, font=font(sz))
    y0 = CARD[3] - 210
    d.rounded_rectangle([(W - w) / 2 - 50, y0, (W + w) / 2 + 50, y0 + sz * 1.7], 36, fill=(255, 255, 255), outline=ACC, width=8)
    d.text(((W - w) / 2, y0 + sz * 0.22), text, font=font(sz), fill=ACC)
    ay = y0 + sz * 1.7 + 10 + 12 * math.sin(t * 6)
    d.polygon([(W / 2 - 34, ay), (W / 2 + 34, ay), (W / 2, ay + 40)], fill=ACC)


# ---------- main ----------
def render_job(job, workdir, log=print):
    os.makedirs(workdir, exist_ok=True)
    scenes = job["scenes"]; assert 1 <= len(scenes) <= 8, "scenes must be 1..8"
    voice = job.get("voice_id") or os.environ.get("ELEVEN_VOICE_ID", "")
    total_chars = sum(len(s["text"]) for s in scenes)
    max_chars = int(os.environ.get("MAX_CHARS", "700"))
    if total_chars > max_chars:
        raise ValueError(f"script too long: {total_chars} chars > {max_chars}. Shorten it.")
    tts.STATS.update(hits=0, misses=0, chars_billed=0)
    model, left = tts.pick_model()
    log(f"model={model} credits_left={left} chars={total_chars}")

    # reusable drawings: expand data-asset references, store new data-save objects
    job_assets = job.get("assets") or {}
    saved_assets = []
    for s in scenes:
        if s.get("svg"):
            s["svg"], sv = assets.expand(s["svg"], job_assets, log); saved_assets += sv
    if saved_assets: log(f"assets saved {saved_assets}")
    cta_text = job.get("cta", "ลิงก์อยู่ในคอมเมนต์")
    hook = job.get("hook") or None
    prod = load_image(job.get("product_image_url"), workdir)
    base = static_base(); mask = card_mask()
    plan = []; t_cursor = 0.0; VO = 0.15
    GAP = float(os.environ.get("SCENE_GAP", "0.2"))   # pause after each scene's voice (was 0.4)
    texts = [x["text"] for x in scenes]
    for i, s in enumerate(scenes):
        mp3 = os.path.join(workdir, f"v{i}.mp3")
        try:
            align = tts.synth(s["text"], mp3, voice, model,
                              " ".join(texts[:i]) or None, " ".join(texts[i + 1:]) or None)
        except RuntimeError:
            if model == tts.MODEL: raise
            log(f"fallback {model} failed, retry with {tts.MODEL}"); model = tts.MODEL
            align = tts.synth(s["text"], mp3, voice, model,
                              " ".join(texts[:i]) or None, " ".join(texts[i + 1:]) or None)
        a, sr = sf.read(mp3) if mp3.endswith(".wav") else _decode(mp3)
        dur = len(a) / sr + VO + (1.3 if i == len(scenes) - 1 else GAP)
        last = i == len(scenes) - 1
        live = None
        if s.get("svg"):   # every svg scene is rendered live (camera move + any data-anim parts)
            try: live = anim.AnimSVG(s["svg"])
            except Exception as e: log(f"anim parse failed: {e}")
        im = load_svg(s.get("svg")) or load_image(s.get("image_url"), workdir)
        if last and prod is not None and im is None: im = prod
        ph = phrases_with_times(s["text"], align, VO)
        # loudness envelope of this scene's voice (mascot lip-sync), one value per video frame
        mono = a.mean(axis=1) if a.ndim > 1 else a
        hop = max(1, int(sr / FPS)); nfr = int(len(mono) / hop) + 1
        env = np.array([np.sqrt(np.mean(mono[k * hop:(k + 1) * hop] ** 2)) if k * hop < len(mono) else 0.0 for k in range(nfr)])
        env = env / (env.max() or 1)
        plan.append(dict(i=i, start=t_cursor, dur=dur, audio=(a, sr), src=make_card_src(im, i), live=live,
                         phrases=ph, layout=sub_layout(ph), env=env, headline=s.get("headline"), step=s.get("step"),
                         cta=last and job.get("show_cta", True)))
        t_cursor += dur
    T = t_cursor; log(f"duration {T:.1f}s")
    cover_img = None
    if hook and (hook.get("style") or "card") == "card":
        s0 = scenes[0]
        hist_p = os.path.join(os.environ.get("DATA_DIR", "/data"), "cover_history.json")
        try: chist = json.load(open(hist_p))
        except Exception: chist = []
        cstyle = {k: hook[k] for k in ("palette", "art") if hook.get(k)} or cover.pick_style(chist, random.Random())
        if "palette" not in cstyle or "art" not in cstyle: cstyle = {**cover.pick_style(chist, random.Random()), **cstyle}
        try: json.dump((chist + [cstyle])[-30:], open(hist_p, "w"))
        except Exception as e: log(f"cover history save failed {e}")
        log(f"cover {cstyle}")
        cover_img = cover.draw_cover(hook, style=cstyle, svg=s0.get("svg"),
                                     image=None if s0.get("svg") else load_image(s0.get("image_url"), workdir) or prod,
                                     brand=BRAND)

    # video
    vtmp = os.path.join(workdir, "video.tmp.mp4"); vout = os.path.join(workdir, "video.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                          "-crf", "20", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
                          "-g", str(FPS * 2), "-keyint_min", str(FPS * 2), "-sc_threshold", "0", "-flags", "+cgop",
                          "-r", str(FPS), vtmp], stdin=subprocess.PIPE)
    for sc in plan:
        n = round(sc["dur"] * FPS)
        for f in range(n):
            t = f / FPS
            img = base.copy(); d = ImageDraw.Draw(img)
            if sc["step"]: pill(d, 196, sc["step"], 54, ACC)
            ev = sc["env"]
            talk = (lambda tt, ev=ev: float(ev[min(len(ev) - 1, max(0, int((tt - VO) * FPS)))]) if tt >= VO else 0.0)
            draw_card(img, sc["src"], mask, t, sc["dur"], sc["i"], sc.get("live"), still_start=bool(hook), talk=talk)
            if sc["headline"]:
                a = back((t - 0.15 - (HOOK_DUR - 0.3 if hook and sc["i"] == 0 else 0)) / 0.45)
                if a > 0:
                    pill(d, 300, sc["headline"], int(76 * max(0.3, min(a, 1.05))),
                         RED if sc["i"] == 0 or sc["cta"] else GREEN)
            if sc["cta"]: draw_cta(img, t, cta_text)
            if hook and sc["i"] == 0: draw_hook(img, hook, t, cover_img)
            if not (cover_img is not None and sc["i"] == 0 and t < HOOK_DUR - 0.35):
                draw_subs(img, sc["phrases"], t, sc["layout"])
            if sc["i"] == 0 and f == 0:
                img.convert("RGB").save(os.path.join(workdir, "cover.jpg"), quality=92)
            p.stdin.write(img.convert("RGB").tobytes())
    p.stdin.close()
    if p.wait() != 0: raise RuntimeError("video encode failed")
    os.replace(vtmp, vout)

    # audio: voice + ducked lofi
    SR = 44100; N = int(T * SR); voice_tr = np.zeros(N)
    for sc in plan:
        a, sr = sc["audio"]
        if a.ndim > 1: a = a.mean(axis=1)
        if sr != SR: a = np.interp(np.linspace(0, len(a) - 1, int(len(a) * SR / sr)), np.arange(len(a)), a)
        s0 = int((sc["start"] + VO) * SR); e = min(N, s0 + len(a)); voice_tr[s0:e] += a[:e - s0]
    lw = os.path.join(workdir, "lofi.wav")
    seed = job.get("seed")
    style = job.get("music_style") or os.environ.get("MUSIC_STYLE", "bright")
    music_info = {"style": style}
    if style == "lofi":
        lofi.make_lofi(T, lw, int(seed) if seed is not None else random.randint(0, 9999))
    else:
        hist_path = os.path.join(os.environ.get("DATA_DIR", "/data"), "music_history.json")
        try: hist = json.load(open(hist_path))
        except Exception: hist = []
        if seed is None: seed = bright.pick_seed(hist)
        fl = bright.make_bright(T, lw, int(seed)); music_info.update(fl)
        try: json.dump((hist + [fl])[-50:], open(hist_path, "w"))
        except Exception as e: log(f"history save failed {e}")
        log(f"music {fl}")
    music, _ = sf.read(lw); music = music[:N]
    if len(music) < N: music = np.pad(music, (0, N - len(music)))
    env = np.convolve(np.abs(voice_tr), np.ones(2205) / 2205, "same")
    peak = env.max() or 1
    under = float(os.environ.get("MUSIC_UNDER_VOICE", "0.07"))   # music level while speaking
    gap = float(os.environ.get("MUSIC_IN_GAPS", "0.20"))           # music level between lines
    duck = np.where(env > 0.03 * peak, under, gap); duck = np.convolve(duck, np.ones(8820) / 8820, "same")
    # carve the voice band out of the music a little (300 Hz - 3.4 kHz) so words stay clear
    from scipy.signal import butter, sosfilt
    music = music - 0.5 * sosfilt(butter(2, [300, 3400], "bandpass", fs=SR, output="sos"), music)
    vpk = np.abs(voice_tr).max() or 1
    mix = voice_tr / vpk * 0.9 + music * duck
    mix /= np.abs(mix).max() or 1
    aw = os.path.join(workdir, "mix.wav"); sf.write(aw, (mix * 0.95).astype(np.float32), SR)

    out_tmp = os.path.join(workdir, "reel.tmp.mp4"); out = os.path.join(workdir, "reel.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vout, "-i", aw, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-profile:a", "aac_low", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                    "-af", "loudnorm=I=-14:TP=-1.5,aresample=48000",
                    "-shortest", "-movflags", "+faststart", out_tmp], check=True)
    os.replace(out_tmp, out)
    return dict(path=out, cover=os.path.join(workdir, "cover.jpg"), duration=round(T, 2), chars=total_chars, model=model, credits_left=left, music=music_info,
                assets_saved=saved_assets, tts_cache_hits=tts.STATS['hits'], tts_new=tts.STATS['misses'], chars_billed=tts.STATS['chars_billed'])


def _decode(mp3):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", mp3, "-f", "f32le", "-ac", "1", "-ar", "44100", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.float32).astype(np.float64), 44100
