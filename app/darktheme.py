"""Dark 'trading card' theme (same look as the PipGuard image posts, but any brand).

Used when a job has "theme": "dark". Brand comes from job["brand"]:
  {"name": "BotBas", "hl": "Bas", "site": "botbas.com", "logo": "robot"|"shield",
   "footer": "เทรดอย่างมีวินัย · บริหารความเสี่ยงก่อนกำไร", "tag": "ความรู้ Forex"}
  name  = logo text, the part equal to `hl` is drawn in the accent colour
  site  = bottom-right of the cover
Cover hook (same keys as the light card cover):
  {"tag", "title": "line1 *accent*\\nline2", "badge" (yellow line), "points": [..3], "note", "footer"}
Palettes and background arts are the PipGuard template's (candles/line/hex/aurora/circuit/poly/bars);
history keeps palette != previous clip and art not in the last 3.
"""
import math, random
from PIL import Image, ImageDraw, ImageFilter

import cover as C   # fonts, svg illustration helpers

W, H = 1080, 1920


def _hx(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


PALETTES = [dict(name=n, bg=_hx(bg), a=_hx(a), b=_hx(b), c=_hx(c)) for n, bg, a, b, c in [
    ("blue",   "#060a18", "#3b82f6", "#6366f1", "#fbbf24"),
    ("violet", "#0a0714", "#a78bfa", "#4f46e5", "#fbbf24"),
    ("cyan",   "#04101a", "#06b6d4", "#1d4ed8", "#f59e0b"),
    ("gold",   "#0c0a05", "#fbbf24", "#b45309", "#60a5fa"),
    ("sky",    "#071019", "#60a5fa", "#0e7490", "#f472b6"),
]]
ARTS = ["candles", "line", "hex", "aurora", "circuit", "poly", "bars"]
INK = (255, 255, 255); MUTE = (148, 163, 184); PANEL = (13, 21, 48)
TAGINK = (6, 16, 26)


def palette(name):
    return next((p for p in PALETTES if p["name"] == name), PALETTES[0])


def pick_style(history, rnd):
    last = history[-1] if history else {}
    pals = [p["name"] for p in PALETTES if p["name"] != last.get("palette")]
    arts = [a for a in ARTS if a not in [h.get("art") for h in history[-3:]]] or ARTS
    return {"palette": rnd.choice(pals), "art": rnd.choice(arts)}


def mix(c1, c2, t): return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


# ---------------- background ----------------
def background(P, art, rnd, w=W, h=H, art_h=1150, fade_to=1350, strength=1.0):
    """1x RGBA background: art on top, fading into the plain bg colour."""
    rr = rnd.uniform; ri = rnd.randint
    K = 0.55 * strength
    A = lambda v: int(255 * max(0, min(1, v)))
    img = Image.new("RGBA", (w, h), P["bg"] + (255,))
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    cols = [P["a"], P["b"], P["c"]]; col = lambda: rnd.choice(cols)

    def g(cx, cy, rad, c, al):
        gd.ellipse([cx - rad * .6, cy - rad * .6, cx + rad * .6, cy + rad * .6], fill=c + (A(al),))

    H0 = art_h
    if art == "aurora":
        for _ in range(6): g(rr(0, w), rr(0, H0 * .8), rr(300, 560), col(), rr(.3, .55) * K)
    elif art == "circuit":
        g(rr(300, 800), 400, 520, P["b"], .3 * K)
        for _ in range(60):
            px, py = round(rr(0, w) / 30) * 30, round(rr(0, H0) / 30) * 30
            c = col() + (A(rr(.25, .55) * K),); pts = [(px, py)]
            for _k in range(ri(2, 5)):
                dd, l = ri(0, 3), ri(2, 8) * 30
                if dd == 0: px += l
                elif dd == 1: px -= l
                elif dd == 2: py += l
                else: px += l * .7; py += l * .7
                pts.append((px, py))
            d.line(pts, fill=c, width=3, joint="curve"); d.ellipse([px - 6, py - 6, px + 6, py + 6], fill=c)
    elif art == "hex":
        z = ri(44, 62); hh = z * math.sqrt(3); cx0, cy0 = rr(0, w), rr(0, H0 * .6)
        g(cx0, cy0, 500, P["a"], .25 * K)
        for r in range(-1, int(H0 / hh) + 2):
            for c in range(-1, int(w / (z * 1.5)) + 2):
                cx = c * z * 1.5; cy = r * hh + (hh / 2 if c % 2 else 0)
                al = max(.05, .5 - math.hypot(cx - cx0, cy - cy0) / 900) * K
                pts = [(cx + math.cos(k * math.pi / 3) * z * .92, cy + math.sin(k * math.pi / 3) * z * .92) for k in range(6)]
                d.polygon(pts, outline=P["a"] + (A(al),), width=2,
                          fill=(col() + (A(.3 * K),)) if rnd.random() < .06 else None)
    elif art == "poly":
        cs, rs = ri(140, 190), ri(120, 160)
        grid = [[(c * cs + rr(-.35, .35) * cs, r * rs + rr(-.35, .35) * rs) for c in range(w // cs + 2)] for r in range(H0 // rs + 2)]
        for r in range(len(grid) - 1):
            for c in range(len(grid[r]) - 1):
                q = [grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c]]
                for tri in ((0, 1, 2), (0, 2, 3)):
                    d.polygon([q[i] for i in tri], fill=(P["b"] if rnd.random() < .5 else P["a"]) + (A(rr(.04, .28) * K),))
    elif art == "candles":
        g(rr(200, 900), rr(150, 500), 560, P["b"], .35 * K)
        for gy in range(60, H0, 90): d.line([(0, gy), (w, gy)], fill=P["b"] + (A(.18 * K),), width=1)
        n = ri(28, 40); cw = w / n; p = rr(380, 560); tr = rr(-5, 5)
        for i in range(n):
            o = p; cl = o + rr(-50, 50) - tr; hi = min(o, cl) - rr(5, 50); lo = max(o, cl) + rr(5, 50)
            cc = P["a"] if cl < o else P["c"]; cx = i * cw + cw / 2
            d.line([(cx, hi), (cx, lo)], fill=cc + (A(.6 * K),), width=3)
            d.rectangle([cx - cw * .3, min(o, cl), cx + cw * .3, min(o, cl) + max(4, abs(cl - o))], fill=cc + (A(.45 * K),))
            p = max(120, min(H0 - 150, cl))
    elif art == "line":
        g(rr(200, 900), rr(150, 500), 560, P["a"], .3 * K)
        for k in range(3):
            y = rr(350, 650); pts = []
            for X in range(0, w + 18, 18):
                y += rr(-26, 24) - k; y = max(80, min(H0 - 120, y)); pts.append((X, y))
            if k == 0:
                area = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                ImageDraw.Draw(area).polygon(pts + [(w, H0), (0, H0)], fill=P["a"] + (A(.22 * K),))
                lay = Image.alpha_composite(lay, area); d = ImageDraw.Draw(lay)
            d.line(pts, fill=[P["a"], P["c"], P["b"]][k] + (A((.35 if k else .75) * K),), width=3 if k else 6, joint="curve")
    elif art == "bars":
        g(rr(200, 900), rr(150, 500), 560, P["b"], .3 * K)
        n = ri(9, 16); bw = w / n
        for i in range(n):
            hg = rr(120, H0 * .7); bx = i * bw + bw * .18
            d.rounded_rectangle([bx, H0 - hg, bx + bw * .64, H0 + 30], 14, fill=(P["a"] if i % 3 else P["c"]) + (A(rr(.2, .45) * K),))
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    lay = Image.alpha_composite(glow, lay)
    # film grain
    nd = ImageDraw.Draw(lay)
    for _ in range(9000):
        x, y = rr(0, w), rr(0, H0)
        nd.rectangle([x, y, x + 1.5, y + 1.5], fill=(255, 255, 255, A(rr(0, .045))))
    # fade out toward the text area
    m = Image.new("L", (1, h))
    f0 = art_h - 250
    for y in range(h): m.putpixel((0, y), 255 if y < f0 else max(0, int(255 * (1 - (y - f0) / max(1, fade_to - f0)))))
    lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", lay.size, 0), m.resize(lay.size)))
    img.alpha_composite(lay)
    # soft vignette glow low down (like the template)
    vg = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(vg).ellipse([w / 2 - 520, h * .62 - 420, w / 2 + 520, h * .62 + 420], fill=P["b"] + (34,))
    img.alpha_composite(vg.filter(ImageFilter.GaussianBlur(170)))
    return img


# ---------------- logo ----------------
def logo_icon(P, sz, kind="robot"):
    """Rounded square, accent->b gradient, robot head (BotBas mark) or shield + tick (brand.logo = "shield")."""
    s = 4; n = sz * s
    grad = Image.new("RGBA", (n, n))
    gd = ImageDraw.Draw(grad)
    for k in range(n):
        gd.line([(0, k), (n, k)], fill=mix(P["a"], P["b"], k / n) + (255,))
    m = Image.new("L", (n, n), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, n - 1, n - 1], int(n * .28), fill=255)
    grad.putalpha(m); d = ImageDraw.Draw(grad)
    if kind == "shield":
        u = n / 24; lw = int(u * 2)
        sh = [(12, 3), (20, 6), (20, 12), (17.5, 17.5), (12, 21), (6.5, 17.5), (4, 12), (4, 6), (12, 3)]
        d.line([(n * .2 + x * u * .6, n * .2 + y * u * .6) for x, y in sh], fill=TAGINK, width=lw, joint="curve")
        d.line([(n * .2 + x * u * .6, n * .2 + y * u * .6) for x, y in [(9, 12), (11, 14), (15, 10)]], fill=TAGINK, width=lw, joint="curve")
        return grad.resize((sz, sz), Image.LANCZOS)
    # robot head (BotBas mark): antenna, rounded head, two eyes, smile (drawn on a layer, shrunk 82%)
    rb = Image.new("RGBA", (n, n), (0, 0, 0, 0)); d = ImageDraw.Draw(rb)
    u = n / 24; lw = int(u * 1.9)
    d.line([(12 * u, 3.2 * u), (12 * u, 6.6 * u)], fill=TAGINK, width=lw)
    d.ellipse([10.6 * u, 1.8 * u, 13.4 * u, 4.6 * u], fill=TAGINK)
    d.rounded_rectangle([4.6 * u, 6.6 * u, 19.4 * u, 19.2 * u], int(4 * u), outline=TAGINK, width=lw)
    d.line([(3 * u, 11 * u), (3 * u, 15 * u)], fill=TAGINK, width=lw); d.line([(21 * u, 11 * u), (21 * u, 15 * u)], fill=TAGINK, width=lw)
    for ex in (9.2, 14.8): d.ellipse([(ex - 1.5) * u, 10.4 * u, (ex + 1.5) * u, 13.4 * u], fill=TAGINK)
    d.arc([8.6 * u, 12.4 * u, 15.4 * u, 17.2 * u], 20, 160, fill=TAGINK, width=lw)
    k = int(n * .82); rb = rb.resize((k, k), Image.LANCZOS); grad.alpha_composite(rb, ((n - k) // 2, (n - k) // 2 + int(n * .01)))
    return grad.resize((sz, sz), Image.LANCZOS)


def brand_segments(brand, P):
    name = brand.get("name") or "BotBas"; hl = brand.get("hl") or ""
    if hl and hl in name:
        a, b = name.split(hl, 1); return [(a, INK), (hl, P["a"]), (b, INK)]
    return [(name, INK)]


def draw_brand(img, P, brand, right_x, top, size=44, icon=92, scale=1):
    """Logo + name ending at right_x (coords in output px of img, scale = supersample)."""
    d = ImageDraw.Draw(img); f = C.F(size) if scale == C.S else None
    from PIL import ImageFont
    f = f or ImageFont.truetype(C.F_BOLD, int(size * scale))
    segs = [(t, c) for t, c in brand_segments(brand, P) if t]
    tw = sum(d.textlength(t, font=f) for t, _ in segs)
    x = right_x * scale - tw
    ic = logo_icon(P, int(icon * scale), brand.get("logo") or "robot")
    img.alpha_composite(ic, (int(x - ic.width - 22 * scale), int(top * scale)))
    ty = top * scale + (icon * scale - size * scale * 1.45) / 2
    for t, c in segs:
        d.text((x, ty), t, font=f, fill=c); x += d.textlength(t, font=f)


# ---------------- cover ----------------
def draw_cover(hook, brand, svg=None, image=None, style=None, seed=None):
    rnd = random.Random(seed)
    style = style or pick_style([], rnd)
    P = palette(style.get("palette")); S = C.S; s = C.s
    bg = background(P, style.get("art") or "candles", rnd)
    img = bg.resize((s(W), s(H)), Image.BICUBIC); d = ImageDraw.Draw(img)

    top = 150
    tag = hook.get("tag") or brand.get("tag") or "ความรู้ Forex"
    tf = C.F(42); tw = C._tw(d, tag, tf)
    d.rounded_rectangle([s(60), s(top), s(60 + tw + 56), s(top + 92)], s(18), fill=P["a"] + (255,))
    C._text(d, 88, top + 14, tag, tf, TAGINK)
    draw_brand(img, P, brand, W - 60, top, 46, 92, S); d = ImageDraw.Draw(img)

    footer_y = 1790
    note = hook.get("note"); points = [p for p in (hook.get("points") or []) if p][:3]
    y = footer_y - 40; note_y = None
    if note: y -= 70; note_y = y
    card = None; row = 112
    if points:
        ch = row * len(points) + 40; y -= 30 + ch; card = (60, y, W - 60, y + ch)
    badge = hook.get("badge")
    lines = [l for l in (hook.get("title") or "").split("\n") if l.strip()][:2]
    tsz = 132
    for l in lines:
        while C._tw(d, l.replace("*", ""), C.F(tsz)) > W - 140 and tsz > 70: tsz -= 4
    tlh = int(tsz * 1.18); bsz = 88
    if badge:
        while C._tw(d, badge, C.F(bsz)) > W - 160 and bsz > 50: bsz -= 2
    y -= 40; badge_y = None
    if badge: y -= int(bsz * 1.3); badge_y = y
    y -= tlh * len(lines); title_y = y

    ill_top, ill_bot = top + 130, title_y - 30
    box_h = max(200, ill_bot - ill_top); box_w = min(W - 100, box_h * 1.35)
    ill = C._illustration(svg, image, box_w, box_h)
    if ill is not None:
        iw, ih = ill.width / S, ill.height / S
        ix, iy = (W - iw) / 2, ill_top + (box_h - ih) / 2
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).ellipse([s(ix + iw * .06), s(iy + ih - 24), s(ix + iw * .94), s(iy + ih + 28)], fill=(0, 0, 0, 150))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(s(16))))
        img.alpha_composite(ill, (s(ix), s(iy))); d = ImageDraw.Draw(img)

    f = C.F(tsz)
    for i, l in enumerate(lines):
        segs = C._segments(l); ws = [C._tw(d, t, f) for t, _ in segs]
        x = (W - sum(ws)) / 2; ly = title_y + i * tlh - tsz * .12
        for (t, hl), w_ in zip(segs, ws):
            C._text(d, x, ly, t, f, P["a"] if hl else INK); x += w_
    if badge:
        bf = C.F(bsz); w_ = C._tw(d, badge, bf)
        C._text(d, (W - w_) / 2, badge_y - bsz * .1, badge, bf, P["c"])

    if card:
        x0, y0, x1, y1 = card
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([s(x0), s(y0 + 16), s(x1), s(y1 + 24)], s(40), fill=(0, 0, 0, 90))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(s(20)))); d = ImageDraw.Draw(img)
        d.rounded_rectangle([s(x0), s(y0), s(x1), s(y1)], s(40), fill=PANEL + (225,),
                            outline=mix(P["bg"], P["a"], .45) + (255,), width=s(3))
        for i, p in enumerate(points):
            ry = y0 + 20 + i * row; sz = 52
            while C._tw(d, p, C.F(sz, True)) > (x1 - x0) - 210 and sz > 34: sz -= 2
            cx, cy = x0 + 40 + 31, ry + row / 2
            d.ellipse([s(cx - 31), s(cy - 31), s(cx + 31), s(cy + 31)], fill=P["a"] + (255,))
            d.line([(s(cx - 13), s(cy + 1)), (s(cx - 4), s(cy + 10)), (s(cx + 14), s(cy - 9))], fill=TAGINK, width=s(6), joint="curve")
            C._text(d, x0 + 128, ry + (row - sz * 1.45) / 2, p, C.F(sz, True), INK)
            if i < len(points) - 1:
                ly = ry + row
                for dx in range(int(x0 + 40), int(x1 - 40), 14):
                    d.line([s(dx), s(ly), s(dx + 6), s(ly)], fill=(255, 255, 255, 46), width=s(2))

    if note:
        nf = C.F(42, True)
        while C._tw(d, note, nf) > W - 120: nf = C.F(nf.size / S - 2, True)
        w_ = C._tw(d, note, nf); C._text(d, (W - w_) / 2, note_y, note, nf, MUTE)
    ff = C.F(34, True)
    C._text(d, 60, footer_y, hook.get("footer") or brand.get("footer") or "เทรดอย่างมีวินัย · บริหารความเสี่ยงก่อนกำไร", ff, MUTE)
    site = brand.get("site") or ""
    if site:
        w_ = C._tw(d, site, ff); C._text(d, W - 60 - w_, footer_y, site, ff, MUTE)
    return img.resize((W, H), Image.LANCZOS)


# ---------------- video background ----------------
def static_base(P, brand, art, seed=None):
    """Background behind the scene card during the clip: same art, softer, logo centred on top."""
    rnd = random.Random(seed)
    img = background(P, art, rnd, art_h=1000, fade_to=1500, strength=.75)
    # second soft glow low in the frame so the bottom is not flat
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(gl).ellipse([700, 1450, 1400, 2150], fill=P["a"] + (40,))
    img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(120)))
    # centred logo
    from PIL import ImageFont
    f = ImageFont.truetype(C.F_BOLD, 60); d = ImageDraw.Draw(img)
    segs = [(t, c) for t, c in brand_segments(brand, P) if t]
    tw = sum(d.textlength(t, font=f) for t, _ in segs); ic = 72
    x = (W - tw - ic - 20) / 2 + ic + 20
    img.alpha_composite(logo_icon(P, ic, brand.get("logo") or "robot"), (int(x - ic - 20), 82))
    for t, c in segs:
        d.text((x, 78), t, font=f, fill=c); x += d.textlength(t, font=f)
    return img


def card_fallback(P, brand, cw, ch):
    """Last-scene card when there is no product image: dark panel, glow, big logo + site."""
    img = Image.new("RGBA", (cw, ch), PANEL + (255,))
    gl = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)
    gd.ellipse([cw * .15, ch * .1, cw * .85, ch * .75], fill=P["a"] + (90,))
    img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(120)))
    d = ImageDraw.Draw(img)
    for gy in range(40, ch, 70): d.line([(0, gy), (cw, gy)], fill=P["b"] + (40,), width=2)
    ic = 300; img.alpha_composite(logo_icon(P, ic, brand.get("logo") or "robot"), ((cw - ic) // 2, int(ch * .16)))
    from PIL import ImageFont
    f = ImageFont.truetype(C.F_BOLD, 96); segs = [(t, c) for t, c in brand_segments(brand, P) if t]
    tw = sum(d.textlength(t, font=f) for t, _ in segs); x = (cw - tw) / 2; y = ch * .16 + ic + 30
    for t, c in segs: d.text((x, y), t, font=f, fill=c); x += d.textlength(t, font=f)
    return img.convert("RGB")
