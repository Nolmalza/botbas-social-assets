"""Reel cover in the 'card' style of the page's image posts (light-blue dotted background,
blue tag + logo, illustration, big title with blue highlight, orange sub line, white checklist
card, warning note, footer). Drawn at 2x and downscaled for smooth edges.

hook = {
  "style": "card",                       # default; "pop" = old dimmed overlay
  "tag":   "ทริคบ้านน่ารู้",                # blue pill, top-left
  "title": "พัดลม*ฝุ่นเกาะ*\nลมเบา ฝุ่นฟุ้ง",   # 1-2 lines, *word* = blue
  "badge": "ล้างเองได้ ไม่ต้องจ้าง",          # orange line under the title
  "points": ["ถอดปลั๊กก่อนทุกครั้ง", "...", "..."],  # 0-3 checklist items
  "note":  "ห้ามให้น้ำเข้ามอเตอร์เด็ดขาด",      # small grey line (optional)
  "footer": "แก้ปัญหาในบ้าน · ของใช้ดีบอกต่อ"   # optional
}
"""
import io, os, re
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
F_BOLD = os.path.join(HERE, "fonts/Kanit-Bold.ttf")
F_SEMI = os.path.join(HERE, "fonts/Kanit-SemiBold.ttf")

S = 2                                   # supersample
W, H = 1080, 1920
BG_TOP = (232, 243, 251); BG_BOT = (244, 249, 253)
DOT = (196, 223, 243)
BLUE = (16, 124, 206); BLUE_D = (10, 98, 170)
INK = (38, 34, 32); GREY = (110, 112, 118)
ORANGE = (238, 98, 18)
LINE = (210, 222, 232)

_fc = {}
def F(sz, semi=False):
    k = (int(sz * S), semi)
    if k not in _fc: _fc[k] = ImageFont.truetype(F_SEMI if semi else F_BOLD, k[0])
    return _fc[k]

def s(v): return int(round(v * S))


def _tw(d, txt, f): return d.textlength(txt, font=f) / S


def _text(d, x, y, txt, f, fill):
    d.text((s(x), s(y)), txt, font=f, fill=fill)


def _segments(line):
    out = []; hl = False
    for part in line.split("*"):
        if part: out.append((part, hl))
        hl = not hl
    return out


def strip_bg(svg):
    """Remove the scene's full-size background rect and full-width floor strip so the drawing
    sits directly on the cover background (like the image posts)."""
    try:
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        root = ET.fromstring(svg)
        vb = (root.get("viewBox") or "0 0 920 890").split()
        vw, vh = float(vb[2]), float(vb[3])
        for el in list(root):
            if el.tag.split("}")[-1] != "rect": continue
            w, h = el.get("width", ""), el.get("height", "")
            num = lambda v, full: full if v.endswith("%") else float(re.sub(r"[^0-9.]", "", v) or 0)
            # full-width rects = background and floor/table strip
            if num(w, vw) >= vw * 0.95 and num(h, vh) >= vh * 0.08:
                root.remove(el)
        return ET.tostring(root, encoding="unicode")
    except Exception as e:
        print("strip_bg failed", e); return svg


def _illustration(svg, img, box_w, box_h):
    """Return RGBA illustration fitted into box (px at 1x)."""
    im = None
    if svg:
        try:
            import cairosvg
            png = cairosvg.svg2png(bytestring=strip_bg(svg).encode("utf-8"), output_width=s(box_w))
            im = Image.open(io.BytesIO(png)).convert("RGBA")
        except Exception as e:
            print("cover svg failed", e)
    if im is None and img is not None:
        im = img.convert("RGBA")
        # rounded photo card
        m = Image.new("L", im.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width, im.height], int(min(im.size) * 0.08), fill=255)
        im.putalpha(m)
    if im is None: return None
    bb = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if bb: im = im.crop(bb)                      # trim empty space so it sits on the shadow
    sc = min(s(box_w) / im.width, s(box_h) / im.height)
    return im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS)


def _house(sz):
    im = Image.new("RGBA", (sz, sz), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, sz, sz], int(sz * 0.26), fill=BLUE + (255,))
    w = sz * 0.07
    pts = [(sz * 0.27, sz * 0.47), (sz * 0.5, sz * 0.27), (sz * 0.73, sz * 0.47)]
    d.line(pts, fill="white", width=int(w), joint="curve")
    d.line([(sz * 0.33, sz * 0.43), (sz * 0.33, sz * 0.72), (sz * 0.67, sz * 0.72), (sz * 0.67, sz * 0.43)],
           fill="white", width=int(w), joint="curve")
    d.rounded_rectangle([sz * 0.45, sz * 0.56, sz * 0.55, sz * 0.72], int(sz * 0.02), outline="white", width=int(w * 0.8))
    return im


def _check(sz):
    im = Image.new("RGBA", (sz, sz), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, sz - 1, sz - 1], fill=BLUE_D + (255,))
    d.line([(sz * 0.28, sz * 0.52), (sz * 0.44, sz * 0.67), (sz * 0.73, sz * 0.37)], fill="white",
           width=int(sz * 0.11), joint="curve")
    return im


def _background():
    img = Image.new("RGBA", (s(W), s(H)))
    d = ImageDraw.Draw(img)
    for y in range(0, s(H), 4):
        k = y / s(H)
        c = tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * k) for i in range(3))
        d.rectangle([0, y, s(W), y + 4], fill=c + (255,))
    dots = Image.new("RGBA", img.size, (0, 0, 0, 0)); dd = ImageDraw.Draw(dots)
    step, r = 50, 10
    for gy in range(40, 1250, step):
        for gx in range(26, W, step):
            side = abs(gx - W / 2) / (W / 2)               # stronger at the sides
            top = max(0.0, 1 - gy / 1250)                   # fade out downward
            a = (0.08 + 0.92 * side ** 1.6) * top
            if a < 0.08: continue
            dd.ellipse([s(gx - r), s(gy - r), s(gx + r), s(gy + r)], fill=DOT + (int(255 * a),))
    img.alpha_composite(dots)
    return img


def draw_cover(hook, svg=None, image=None, brand="บ้านนี้มีดี by ซี"):
    """Full opaque 1080x1920 cover (RGBA)."""
    img = _background(); d = ImageDraw.Draw(img)

    # ---- top bar ----
    top = 150
    tag = hook.get("tag") or "ทริคบ้านน่ารู้"
    tf = F(42); tw = _tw(d, tag, tf)
    d.rounded_rectangle([s(60), s(top), s(60 + tw + 56), s(top + 92)], s(18), fill=BLUE + (255,))
    _text(d, 88, top + 14, tag, tf, "white")
    # logo: house icon + brand ("มีดี" in blue if present)
    bf = F(44); parts = brand.split("มีดี", 1)
    segs = [(parts[0], INK), ("มีดี", BLUE), (parts[1], INK)] if len(parts) == 2 else [(brand, INK)]
    bw = sum(_tw(d, t, bf) for t, _ in segs)
    x = W - 60 - bw; icon = _house(s(92))
    img.alpha_composite(icon, (s(x - 92 - 22), s(top)))
    for t, c in segs:
        _text(d, x, top + 14, t, bf, c); x += _tw(d, t, bf)

    # ---- measure the text block (bottom-up) ----
    footer_y = 1790
    note = hook.get("note"); points = [p for p in (hook.get("points") or []) if p][:3]
    y = footer_y - 40
    note_y = None
    if note:
        nf = F(44, True); y -= 70; note_y = y
    card = None
    if points:
        pf = F(54); row = 112
        ch = row * len(points) + 40
        y -= 30 + ch; card = (60, y, W - 60, y + ch)
    badge = hook.get("badge")
    lines = [l for l in (hook.get("title") or "").split("\n") if l.strip()][:2]
    tsz = 132
    for l in lines:
        while _tw(d, l.replace("*", ""), F(tsz)) > W - 140 and tsz > 70: tsz -= 4
    tlh = int(tsz * 1.18)
    bsz = 92
    if badge:
        while _tw(d, badge, F(bsz)) > W - 160 and bsz > 50: bsz -= 2
    y -= 40
    badge_y = None
    if badge: y -= int(bsz * 1.3); badge_y = y
    y -= tlh * len(lines); title_y = y

    # ---- illustration fills the space between the top bar and the title ----
    ill_top, ill_bot = top + 120, title_y - 20
    box_h = max(200, ill_bot - ill_top); box_w = min(W - 80, box_h * 1.2)
    ill = _illustration(svg, image, box_w, box_h)
    if ill is not None:
        iw, ih = ill.width / S, ill.height / S
        ix, iy = (W - iw) / 2, ill_top + (box_h - ih) / 2
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).ellipse([s(ix + iw * 0.08), s(iy + ih - 22), s(ix + iw * 0.92), s(iy + ih + 22)],
                                   fill=(120, 150, 175, 70))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(s(12))))
        img.alpha_composite(ill, (s(ix), s(iy)))
        d = ImageDraw.Draw(img)

    # ---- title ----
    f = F(tsz)
    for i, l in enumerate(lines):
        segs = _segments(l); ws = [_tw(d, t, f) for t, _ in segs]
        x = (W - sum(ws)) / 2; ly = title_y + i * tlh - tsz * 0.12
        for (t, hl), w in zip(segs, ws):
            _text(d, x, ly, t, f, BLUE if hl else INK); x += w
    if badge:
        bf = F(bsz); w = _tw(d, badge, bf)
        _text(d, (W - w) / 2, badge_y - bsz * 0.1, badge, bf, ORANGE)

    # ---- checklist card ----
    if card:
        x0, y0, x1, y1 = card
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([s(x0), s(y0 + 10), s(x1), s(y1 + 14)], s(40), fill=(90, 130, 170, 45))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(s(14))))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([s(x0), s(y0), s(x1), s(y1)], s(40), fill=(255, 255, 255, 255),
                            outline=(178, 212, 234, 255), width=s(3))
        ck = _check(s(66))
        for i, p in enumerate(points):
            ry = y0 + 20 + i * row
            sz = 54
            while _tw(d, p, F(sz)) > (x1 - x0) - 210 and sz > 34: sz -= 2
            img.alpha_composite(ck, (s(x0 + 40), s(ry + (row - 66) / 2)))
            _text(d, x0 + 132, ry + (row - sz * 1.45) / 2, p, F(sz), INK)
            if i < len(points) - 1:
                ly = ry + row
                for dx in range(int(x0 + 40), int(x1 - 40), 14):
                    d.line([s(dx), s(ly), s(dx + 6), s(ly)], fill=LINE + (255,), width=s(2))

    # ---- note + footer ----
    if note:
        while _tw(d, note, nf) > W - 120: nf = F(nf.size / S - 2, True)
        w = _tw(d, note, nf); _text(d, (W - w) / 2, note_y, note, nf, GREY)
    ff = F(38, True)
    _text(d, 60, footer_y, hook.get("footer") or "แก้ปัญหาในบ้าน · ของใช้ดีบอกต่อ", ff, GREY)
    w = _tw(d, brand, ff); _text(d, W - 60 - w, footer_y, brand, ff, GREY)

    return img.resize((W, H), Image.LANCZOS)
