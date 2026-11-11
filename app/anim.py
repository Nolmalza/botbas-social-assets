"""Animated SVG scenes (cartoon, natural motion).

Claude writes a normal SVG and puts motion on groups with data-anim:
  <g data-anim="wipe" data-amp="120" data-speed="1.2">...</g>

Loop motions (with built-in natural variation, data-jitter 0-1, default 0.3; 0 = robotic):
  bob      move up/down            data-amp px (default 12)
  float    slow drift up/down      data-amp px (default 8)
  wipe     move left/right         data-amp px (default 80)
  scrub    small fast circles      data-amp px (default 18)  (scrubbing, stirring)
  sway     rotate back and forth   data-amp deg (default 8), pivot data-cx data-cy
  spin     continuous rotation     data-speed turns/s (default 0.5), pivot data-cx data-cy
  pulse    grow/shrink             data-amp fraction (default 0.06), pivot data-cx data-cy
  shake    quick jitter            data-amp px (default 4)
  rise     move up and fade, loop  data-amp px travel (default 140)
  drip     fall and fade, loop     data-amp px travel (default 160)
  blink    on/off flashing
One-shot:
  pop      squash-and-stretch pop in   pivot data-cx data-cy, data-delay s
  fadein   appear                  data-delay, data-dur (0.6)
  fadeout  disappear               data-delay, data-dur (2)
  slidein  slide in, overshoot     data-from=left|right|top|bottom, data-delay
  scrubout children (stain blobs) vanish one by one in random order, shrinking  data-delay, data-dur (3)

NEW - keyframes (acting: reach, grab, scrub, lift, hold):
  <g data-anim="keys" data-cx=".." data-cy=".." data-keys="0 0 0; 0.8 140 -30 -10 1 1 back; 1.6 140 -30 -10; 2.2 0 0 0 1 1 inout" data-loop="0">
  each key: t x y [rotate] [scale | sx*sy] [opacity] [ease]; ease = inout (default) | out | in | back | bounce | linear
  data-loop="1" repeats (period = last t). Nest groups for joints: shoulder <g keys> > elbow <g keys> > hand.
  A 1.1*0.9 scale = squash, 0.9*1.1 = stretch.

NEW - particles (the element is ONE template shape drawn at the emit point):
  <circle data-anim="emit" data-kind="bubble" data-count="8" data-spread="60" data-amp="220" data-speed="0.5" .../>
  kinds: bubble (wobble up, pop) | drop (fall with gravity) | stream (fast drops in a line = pouring water)
         | steam (rise, curl, grow, fade) | dust (burst out and fade, once) | sparkle (twinkle at random spots)

NEW - camera on the <svg> root: data-camera="push" (default) | pull | pan-left | pan-right | none,
  data-cam-amp (0.07), data-focus="x y" (zoom target). Groups with data-depth: 0.5 = far background
  (moves less), 1 = normal, 1.4 = foreground (moves more) -> parallax.
Common: data-speed (cycles/s), data-delay (s), data-phase (0-1).
"""
import copy, io, math, random
import xml.etree.ElementTree as ET
from PIL import Image

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")


def has_anim(svg):
    return bool(svg) and ("data-anim" in svg or "data-camera" in svg)


def _f(el, k, d):
    try: return float(el.get(k, d))
    except Exception: return d


def _c(x): return max(0.0, min(1.0, x))
def _ease(x): x = _c(x); return 1 - (1 - x) ** 3
def _inout(x): x = _c(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def _back(x):
    x = _c(x); c = 1.7
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
def _bounce(x):
    x = _c(x); n, d = 7.5625, 2.75
    if x < 1 / d: return n * x * x
    if x < 2 / d: x -= 1.5 / d; return n * x * x + .75
    if x < 2.5 / d: x -= 2.25 / d; return n * x * x + .9375
    x -= 2.625 / d; return n * x * x + .984375
EASE = {"inout": _inout, "out": _ease, "in": lambda x: _c(x) ** 3, "back": _back, "bounce": _bounce,
        "linear": _c}


def _noise(t, seed):
    """smooth 1D value noise in [-1, 1]"""
    i = math.floor(t); f = t - i; u = f * f * (3 - 2 * f)
    h = lambda n: (math.sin(n * 127.1 + seed * 311.7) * 43758.5453) % 1.0 * 2 - 1
    return h(i) * (1 - u) + h(i + 1) * u


def _parse_keys(s):
    keys = []
    for part in (s or "").split(";"):
        tok = part.split()
        if len(tok) < 3: continue
        ease = "inout"
        if tok[-1].isalpha(): ease = tok.pop()
        num = []
        for k, v in enumerate(tok):
            if k == 4 and "*" in v:
                a, b = v.split("*"); num.append((float(a), float(b)))
            else: num.append(float(v))
        while len(num) < 6: num.append([0, 0, 0, 0, 1, 1][len(num)])
        sc = num[4] if isinstance(num[4], tuple) else (num[4], num[4])
        keys.append(dict(t=num[0], x=num[1], y=num[2], r=num[3], sx=sc[0], sy=sc[1], o=num[5], ease=ease))
    keys.sort(key=lambda k: k["t"])
    return keys


class AnimSVG:
    def __init__(self, svg):
        self.root = ET.fromstring(svg)
        parent = {c: p for p in self.root.iter() for c in p}
        vb = (self.root.get("viewBox") or "0 0 920 890").split()
        self.vb = [float(v) for v in vb]
        self.items = []; self.parts = []; self.depth = []
        for el in list(self.root.iter()):
            a = (el.get("data-anim") or "").strip().lower()
            if el.get("data-depth"):
                self.depth.append((el, el.get("transform", ""), _f(el, "data-depth", 1.0)))
            if not a: continue
            if a == "emit":
                self._make_emitter(el, parent); continue
            if a == "scrubout":
                rnd = random.Random(hash(ET.tostring(el)) & 0xffff)
                kids = [k for k in el]; dl = _f(el, "data-delay", 0.0); dur = _f(el, "data-dur", 3.0)
                order = list(range(len(kids))); rnd.shuffle(order)
                for rank, k in zip(order, kids):
                    bb = _bbox_center(k)
                    st = dl + dur * rank / max(1, len(kids)) * 0.85
                    self.parts.append(("out", k, k.get("transform", ""), k.get("opacity"), st, max(0.35, dur / len(kids) * 1.4), bb))
                continue
            item = dict(el=el, a=a, tf=el.get("transform", ""), op=el.get("opacity"))
            if a == "keys": item["keys"] = _parse_keys(el.get("data-keys"))
            self.items.append(item)

    def _make_emitter(self, el, parent):
        p = parent.get(el)
        if p is None: return
        n = int(_f(el, "data-count", 8)); kind = el.get("data-kind", "bubble")
        g = ET.Element(f"{{{SVG_NS}}}g")
        idx = list(p).index(el); p.remove(el); p.insert(idx, g)
        for k in ("data-anim", "data-kind", "data-count"): el.attrib.pop(k, None)
        cx, cy = _bbox_center(el)
        rnd = random.Random(n * 7919 + len(self.parts))
        for i in range(n):
            c = copy.deepcopy(el); g.append(c)
            self.parts.append(("emit", c, c.get("transform", ""), c.get("opacity"), kind, i, n, rnd.random(), rnd.random(),
                               (cx, cy), _f(el, "data-spread", 50), _f(el, "data-amp", 200), _f(el, "data-speed", 0.5),
                               _f(el, "data-delay", 0.0)))

    # ---------- camera ----------
    def _camera(self, t, D):
        mode = (self.root.get("data-camera") or "push").lower()
        x0, y0, w, h = self.vb
        if mode == "none": return (x0, y0, w, h), 0.0
        amp = _f(self.root, "data-cam-amp", 0.07)
        p = _inout(t / max(D, 0.5))
        fx, fy = [float(v) for v in (self.root.get("data-focus") or f"{x0 + w / 2} {y0 + h / 2}").split()]
        if mode in ("push", "pull"):
            z = 1 + amp * (p if mode == "push" else 1 - p)
            drift = w * amp * 0.25 * (p - 0.5)
            nw, nh = w / z, h / z
            nx = fx - (fx - x0) / z + drift; ny = fy - (fy - y0) / z
            return (nx, ny, nw, nh), drift
        z = 1 + amp; nw, nh = w / z, h / z
        span = w - nw; dx = span * (p if mode == "pan-right" else 1 - p)
        return (x0 + dx, y0 + (h - nh) / 2, nw, nh), dx - span / 2

    def frame(self, t, width, height, D=8.0):
        vb, pan = self._camera(t, D)
        self.root.set("viewBox", " ".join(f"{v:.2f}" for v in vb))
        for el, base, dep in self.depth:
            el.set("transform", (base + f" translate({pan * (1 - dep):.2f},0)").strip())
        for it in self.items:
            tf, op = self._state(it, t)
            base_tf = it["tf"]
            if it["el"].get("data-depth"):
                base_tf = (base_tf + f" translate({pan * (1 - _f(it['el'], 'data-depth', 1)):.2f},0)").strip()
            it["el"].set("transform", (base_tf + " " + tf).strip())
            self._op(it["el"], it["op"], op)
        for pt in self.parts:
            if pt[0] == "out": self._scrubout(pt, t)
            else: self._emit(pt, t)
        data = ET.tostring(self.root, encoding="unicode")
        import cairosvg
        png = cairosvg.svg2png(bytestring=data.encode("utf-8"), output_width=width, output_height=height)
        return Image.open(io.BytesIO(png)).convert("RGB")

    @staticmethod
    def _op(el, base_op, op):
        o = float(base_op) if base_op is not None else 1.0
        if op is not None: el.set("opacity", f"{_c(o * op):.3f}")
        elif base_op is not None: el.set("opacity", base_op)

    def _scrubout(self, pt, t):
        _, el, tf, bop, st, dur, (cx, cy) = pt
        p = _ease((t - st) / dur) if t >= st else 0.0
        s = 1 - 0.6 * p
        el.set("transform", (tf + f" translate({cx:.1f},{cy:.1f}) scale({max(.001, s):.3f}) translate({-cx:.1f},{-cy:.1f})").strip())
        self._op(el, bop, 1 - p)

    def _emit(self, pt, t):
        _, el, tf, bop, kind, i, n, r1, r2, (cx, cy), spread, amp, sp, dl = pt
        tt = t - dl
        if tt < 0: el.set("opacity", "0"); return
        once = kind == "dust"
        life = tt * sp + (0 if once else i / n + r1 * 0.5)
        if once:
            p = _c(tt / (1.0 / max(sp, .1)) * (0.8 + 0.4 * r1)); cyc = 0
        else:
            cyc = math.floor(life); p = life - cyc
        rr = random.Random(int(r2 * 1e6) + cyc * 31)
        ox = (rr.random() * 2 - 1) * spread
        dx = dy = 0.0; s = 1.0; o = 1.0; rot = 0.0
        if kind == "bubble":
            dy = -amp * p; dx = ox + 14 * math.sin(p * 9 + r1 * 6)
            s = 0.5 + 0.6 * p
            o = _c(p / 0.1)
            if p > 0.9: s *= 1 + (p - 0.9) * 4; o *= 1 - (p - 0.9) / 0.1
        elif kind == "drop":
            dy = amp * p * p; dx = ox * 0.4; s = 0.8 + 0.3 * (1 - p); o = 1 - _c((p - 0.8) / 0.2)
        elif kind == "stream":
            dy = amp * p; dx = ox * 0.15; s = 0.9; o = 1 - _c((p - 0.85) / 0.15)
        elif kind == "steam":
            dy = -amp * p; dx = ox * 0.3 + 30 * p * math.sin(p * 5 + r1 * 6)
            s = 0.6 + 1.1 * p; o = math.sin(math.pi * p) * 0.8
        elif kind == "dust":
            ang = r1 * 6.283; dist = amp * _ease(p) * (0.6 + 0.4 * r2)
            dx, dy = math.cos(ang) * dist, math.sin(ang) * dist * 0.7 - 20 * p
            s = 0.5 + 1.0 * p; o = 1 - p
        elif kind == "sparkle":
            dx = ox; dy = (rr.random() * 2 - 1) * spread
            s = math.sin(math.pi * p) ** 2 * 1.2; rot = 90 * p; o = 1.0
        el.set("transform", (tf + f" translate({dx:.1f},{dy:.1f}) translate({cx:.1f},{cy:.1f}) rotate({rot:.1f}) "
                             f"scale({max(.001, s):.3f}) translate({-cx:.1f},{-cy:.1f})").strip())
        self._op(el, bop, o)

    @staticmethod
    def _state(it, t):
        el, a = it["el"], it["a"]
        sp = _f(el, "data-speed", 1.0); dl = _f(el, "data-delay", 0.0); ph = _f(el, "data-phase", 0.0)
        cx = _f(el, "data-cx", 0.0); cy = _f(el, "data-cy", 0.0)
        jit = _f(el, "data-jitter", 0.3); seed = (id(el) % 997) / 10
        tt = max(0.0, t - dl)
        # natural variation: amplitude breathes, tempo drifts a little
        ja = 1 + jit * 0.45 * _noise(tt * 0.9, seed)
        jt = jit * 0.35 * _noise(tt * 0.6, seed + 3)
        w = 2 * math.pi * (sp * tt + ph + jt)
        about = lambda inner: f"translate({cx:.1f},{cy:.1f}) {inner} translate({-cx:.1f},{-cy:.1f})"
        A = lambda d: _f(el, "data-amp", d) * ja
        if a == "keys":
            ks = it["keys"]
            if not ks: return "", None
            T = ks[-1]["t"]
            k_t = (tt % T) if (el.get("data-loop") == "1" and T > 0) else tt
            if k_t <= ks[0]["t"]: k = ks[0]; v = k
            elif k_t >= T: v = ks[-1]
            else:
                j = next(j for j in range(1, len(ks)) if ks[j]["t"] >= k_t)
                k0, k1 = ks[j - 1], ks[j]
                e = EASE.get(k1["ease"], _inout)((k_t - k0["t"]) / max(1e-6, k1["t"] - k0["t"]))
                v = {q: k0[q] + (k1[q] - k0[q]) * e for q in ("x", "y", "r", "sx", "sy", "o")}
            tf = (f"translate({v['x']:.2f},{v['y']:.2f}) " +
                  about(f"rotate({v['r']:.2f}) scale({max(.001, v['sx']):.4f},{max(.001, v['sy']):.4f})"))
            return tf, (v["o"] if v["o"] != 1 else None)
        if a == "bob":   return f"translate(0,{A(12)*math.sin(w):.2f})", None
        if a == "float": return f"translate({4*jit*_noise(tt*0.5, seed+7):.2f},{A(8)*math.sin(w*0.5):.2f})", None
        if a == "wipe":
            x = A(80) * math.sin(w); y = 6 * jit * math.sin(w * 2 + 1)     # slight arc, like a real hand
            return f"translate({x:.2f},{y:.2f})", None
        if a == "scrub":
            r = A(18); return f"translate({r*math.cos(w*2):.2f},{r*0.6*math.sin(w*2):.2f})", None
        if a == "sway":  return about(f"rotate({A(8)*math.sin(w):.2f})"), None
        if a == "spin":  return about(f"rotate({360*_f(el,'data-speed',0.5)*tt:.2f})"), None
        if a == "pulse": return about(f"scale({1+_f(el,'data-amp',0.06)*ja*math.sin(w):.4f})"), None
        if a == "shake":
            s = A(4); return f"translate({s*math.sin(w*7):.2f},{s*math.cos(w*11):.2f})", None
        if a in ("rise", "drip"):
            p = (sp * tt + ph) % 1.0; d = _f(el, "data-amp", 140 if a == "rise" else 160)
            dy = -d * p if a == "rise" else d * p * p
            op = math.sin(math.pi * p) if a == "rise" else (1 - p) ** 0.7
            return f"translate({8*jit*math.sin(p*7):.2f},{dy:.2f})", op
        if a == "blink": return "", 0.25 + 0.75 * (0.5 + 0.5 * math.sin(w * 2))
        if a == "pop":
            if t < dl: return about("scale(0.001)"), 0.0
            x = tt / 0.55; s = _back(x)
            # squash and stretch: tall while growing, wide on landing, settle
            st = 0.18 * math.sin(math.pi * _c(x * 1.4)) * (1 - _c(x))
            return about(f"scale({max(.001, s*(1-st)):.4f},{max(.001, s*(1+st)):.4f})"), 1.0
        if a == "fadein":
            return "", (_ease(tt / _f(el, "data-dur", 0.6)) if t >= dl else 0.0)
        if a == "fadeout":
            return "", 1 - _ease(tt / _f(el, "data-dur", 2.0)) if t >= dl else 1.0
        if a == "slidein":
            p = _back(tt / 0.7) if t >= dl else 0.0; d = 700 * (1 - p)
            fr = el.get("data-from", "left")
            dx, dy = {"left": (-d, 0), "right": (d, 0), "top": (0, -d), "bottom": (0, d)}.get(fr, (-d, 0))
            return f"translate({dx:.1f},{dy:.1f})", (1.0 if t >= dl else 0.0)
        return "", None


def _bbox_center(el):
    """rough centre of a shape/group (for pivots of particles and stain blobs)"""
    xs, ys = [], []
    for e in el.iter():
        tag = e.tag.split("}")[-1]
        try:
            if tag in ("circle", "ellipse"):
                xs.append(float(e.get("cx", 0))); ys.append(float(e.get("cy", 0)))
            elif tag == "rect":
                xs.append(float(e.get("x", 0)) + float(e.get("width", 0)) / 2)
                ys.append(float(e.get("y", 0)) + float(e.get("height", 0)) / 2)
            elif tag in ("path", "polygon", "polyline"):
                import re
                src = e.get("d") or e.get("points") or ""
                nums = [float(v) for v in re.findall(r"-?\d+\.?\d*", src)]
                if tag == "path" and re.search(r"[a-ln-z]", src):   # relative commands: use the start point
                    if len(nums) >= 2: xs.append(nums[0]); ys.append(nums[1])
                elif len(nums) >= 2: xs.append(sum(nums[0::2]) / len(nums[0::2])); ys.append(sum(nums[1::2]) / len(nums[1::2]))
        except Exception: pass
    return (sum(xs) / len(xs), sum(ys) / len(ys)) if xs else (0.0, 0.0)
