"""Animated SVG scenes.

Claude writes a normal SVG and puts motion on groups with data-anim:
  <g data-anim="wipe" data-amp="120" data-speed="1.2">...</g>

Supported data-anim values (all loop smoothly unless noted):
  bob      move up/down            data-amp px (default 12)
  float    slow drift up/down      data-amp px (default 8)
  wipe     move left/right         data-amp px (default 80)
  scrub    small fast circles      data-amp px (default 18)  (scrubbing, stirring)
  sway     rotate back and forth   data-amp deg (default 8), pivot data-cx data-cy
  spin     continuous rotation     data-speed turns/s (default 0.5), pivot data-cx data-cy
  pulse    grow/shrink             data-amp fraction (default 0.06), pivot data-cx data-cy
  shake    quick jitter            data-amp px (default 4)
  rise     move up and fade, loop  data-amp px travel (default 140)   (steam, smell, bubbles)
  drip     fall and fade, loop     data-amp px travel (default 160)   (drops, water)
  blink    on/off flashing         (sparkles, warning)
  pop      scale in from 0 (once)  pivot data-cx data-cy, data-delay s
  fadein   appear (once)           data-delay s, data-dur s (default 0.6)
  fadeout  disappear over time (once) data-delay s, data-dur s (default 2)  (stains being cleaned)
  slidein  slide in from data-from=left|right|top|bottom (once), data-delay s
Common: data-speed (cycles per second, default 1), data-delay (seconds), data-phase (0-1).
"""
import io, math, re
import xml.etree.ElementTree as ET
from PIL import Image

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")


def has_anim(svg):
    return bool(svg) and "data-anim" in svg


def _f(el, k, d):
    try: return float(el.get(k, d))
    except Exception: return d


def _ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def _back(x):
    x = max(0.0, min(1.0, x)); c = 1.7
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


class AnimSVG:
    def __init__(self, svg):
        self.root = ET.fromstring(svg)
        self.items = []
        for el in self.root.iter():
            a = el.get("data-anim")
            if a:
                self.items.append((el, a.strip().lower(), el.get("transform", ""), el.get("opacity")))

    def frame(self, t, width, height):
        for el, a, base_tf, base_op in self.items:
            tf, op = self._state(el, a, t)
            el.set("transform", (base_tf + " " + tf).strip())
            o = float(base_op) if base_op is not None else 1.0
            if op is not None: el.set("opacity", f"{max(0.0, min(1.0, o * op)):.3f}")
            elif base_op is not None: el.set("opacity", base_op)
        data = ET.tostring(self.root, encoding="unicode")
        import cairosvg
        png = cairosvg.svg2png(bytestring=data.encode("utf-8"), output_width=width, output_height=height)
        return Image.open(io.BytesIO(png)).convert("RGB")

    @staticmethod
    def _state(el, a, t):
        sp = _f(el, "data-speed", 1.0); dl = _f(el, "data-delay", 0.0); ph = _f(el, "data-phase", 0.0)
        cx = _f(el, "data-cx", 0.0); cy = _f(el, "data-cy", 0.0)
        tt = max(0.0, t - dl); w = 2 * math.pi * (sp * tt + ph)
        about = lambda inner: f"translate({cx:.1f},{cy:.1f}) {inner} translate({-cx:.1f},{-cy:.1f})"
        if a == "bob":   return f"translate(0,{_f(el,'data-amp',12)*math.sin(w):.2f})", None
        if a == "float": return f"translate(0,{_f(el,'data-amp',8)*math.sin(w*0.5):.2f})", None
        if a == "wipe":  return f"translate({_f(el,'data-amp',80)*math.sin(w):.2f},0)", None
        if a == "scrub":
            r = _f(el, "data-amp", 18); return f"translate({r*math.cos(w*2):.2f},{r*0.6*math.sin(w*2):.2f})", None
        if a == "sway":  return about(f"rotate({_f(el,'data-amp',8)*math.sin(w):.2f})"), None
        if a == "spin":  return about(f"rotate({360*_f(el,'data-speed',0.5)*tt:.2f})"), None
        if a == "pulse": return about(f"scale({1+_f(el,'data-amp',0.06)*math.sin(w):.4f})"), None
        if a == "shake":
            s = _f(el, "data-amp", 4); return f"translate({s*math.sin(w*7):.2f},{s*math.cos(w*11):.2f})", None
        if a in ("rise", "drip"):
            p = (sp * tt + ph) % 1.0; d = _f(el, "data-amp", 140 if a == "rise" else 160)
            dy = -d * p if a == "rise" else d * p
            op = math.sin(math.pi * p) if a == "rise" else (1 - p) ** 0.7
            return f"translate(0,{dy:.2f})", op
        if a == "blink": return "", 0.25 + 0.75 * (0.5 + 0.5 * math.sin(w * 2))
        if a == "pop":
            s = _back(tt / 0.5) if t >= dl else 0.0
            return about(f"scale({max(0.001, s):.4f})"), (1.0 if t >= dl else 0.0)
        if a == "fadein":
            return "", (_ease(tt / _f(el, "data-dur", 0.6)) if t >= dl else 0.0)
        if a == "fadeout":
            return "", 1 - _ease(tt / _f(el, "data-dur", 2.0)) if t >= dl else 1.0
        if a == "slidein":
            p = _ease(tt / 0.6) if t >= dl else 0.0; d = 700 * (1 - p)
            fr = el.get("data-from", "left")
            dx, dy = {"left": (-d, 0), "right": (d, 0), "top": (0, -d), "bottom": (0, d)}.get(fr, (-d, 0))
            return f"translate({dx:.1f},{dy:.1f})", (1.0 if t >= dl else 0.0)
        return "", None
