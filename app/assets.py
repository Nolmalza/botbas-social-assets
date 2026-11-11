"""Reusable drawing library ("draw once, reuse forever").

In a scene svg, instead of drawing an object again, reference it:
  <g data-asset="sponge" transform="translate(520 690) scale(1)"/>
The origin of every asset is its BOTTOM-CENTRE (where it stands on the table), size is in scene units
(scene viewBox 920x890). data-anim on the same <g> still works (it wraps the asset).

Special assets:
  zee  - the page mascot (boy, spiky hair, apron with house patch). Origin = between the feet, ~675 tall
         at scale 1 (use scale 0.5-0.8).
         data-expr="0 shock; 3.2 point"   pose timeline: shock | happy | point | hold | normal
         data-hold="spray_bottle"         item in the right hand for pose hold
         data-talk="0"                    turn off lip-sync (default on: mouth moves with the voice)
         blinks and breathes by itself; small pop on every pose change.
  arm  - a jointed cartoon arm. Shoulder at the origin, hand at (-355, 205) (reaching left-down).
         data-shoulder-keys / data-elbow-keys = keyframes (see anim.py "keys"), looped,
         data-joint-delay (s), data-hold="sponge", data-sleeve="#3DA5F0". Mirror with scale(-1 1).

New objects: draw them normally inside <g data-save="snake_case_name" data-desc="short English description">...</g>.
The engine renders them as usual AND stores them in the library (only if the name is new), so next time
they are just a data-asset reference. GET /assets lists everything.

Lookup order: job "assets" {name: svg} -> DATA_DIR/assets (saved) -> built-in assets/ -> GitHub raw.
"""
import io, json, os, re, time
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
HERE = os.path.dirname(os.path.abspath(__file__))
BUILTIN = os.path.join(HERE, "assets_builtin")
SAVED = os.path.join(os.environ.get("DATA_DIR", "/data"), "assets")
RAW = os.environ.get("ASSETS_RAW_URL",
                     "https://raw.githubusercontent.com/Nolmalza/botbas-social-assets/reels-engine/assets/{}.svg")
NAME_OK = re.compile(r"^[a-z][a-z0-9_]{1,40}$")
O = "#34404A"; SKIN = "#FFD9B8"


def _q(tag): return f"{{{SVG_NS}}}{tag}"


def frag(xml):
    """parse an svg fragment (no namespace needed)"""
    return ET.fromstring(f'<g xmlns="{SVG_NS}">{xml}</g>')


# ---------------- library ----------------
_cache = {}

def _parse_asset_doc(text):
    root = ET.fromstring(text)
    ax, ay = [float(v) for v in (root.get("data-anchor") or "0 0").split()]
    vb = [float(v) for v in (root.get("viewBox") or "0 0 100 100").split()]
    return dict(root=root, anchor=(ax, ay), w=vb[2], h=vb[3], desc=root.get("data-desc", ""))


def get(name, job_assets=None):
    if job_assets and name in job_assets:
        return _parse_asset_doc(job_assets[name])
    if name in _cache: return _cache[name]
    for d in (SAVED, BUILTIN):
        p = os.path.join(d, f"{name}.svg")
        if os.path.exists(p):
            _cache[name] = _parse_asset_doc(open(p, encoding="utf-8").read()); return _cache[name]
    try:
        import requests
        r = requests.get(RAW.format(name), timeout=15)
        if r.status_code == 200 and "<svg" in r.text:
            os.makedirs(SAVED, exist_ok=True)
            open(os.path.join(SAVED, f"{name}.svg"), "w", encoding="utf-8").write(r.text)
            _cache[name] = _parse_asset_doc(r.text); return _cache[name]
    except Exception as e:
        print("asset fetch failed", name, e)
    return None


def catalog():
    out = {}
    for src, d in (("builtin", BUILTIN), ("saved", SAVED)):
        if not os.path.isdir(d): continue
        for f in sorted(os.listdir(d)):
            if not f.endswith(".svg"): continue
            try:
                a = _parse_asset_doc(open(os.path.join(d, f), encoding="utf-8").read())
                out[f[:-4]] = dict(desc=a["desc"], w=round(a["w"]), h=round(a["h"]), source=src)
            except Exception: pass
    out["zee"] = dict(desc="page mascot boy: spiky hair, blue shirt, white apron with house patch; poses shock/happy/point/hold/normal, lip-sync", w=330, h=540, source="special")
    out["arm"] = dict(desc="jointed cartoon arm from the right edge, shoulder at origin, hand at (-355,205); can hold an asset", w=400, h=260, source="special")
    return out


# ---------------- expansion ----------------
def expand(svg, job_assets=None, log=print):
    """Replace data-asset references with their drawing, save data-save groups. Returns (svg, saved_names)."""
    if not svg or ("data-asset" not in svg and "data-save" not in svg): return svg, []
    root = ET.fromstring(svg)
    saved = []
    for el in list(root.iter()):
        nm = el.get("data-save")
        if nm:
            try:
                if _save_group(root, el, nm, el.get("data-desc", "")): saved.append(nm)
            except Exception as e: log(f"asset save failed {nm}: {e}")
            el.attrib.pop("data-save", None); el.attrib.pop("data-desc", None)
    for el in list(root.iter()):
        nm = el.get("data-asset")
        if not nm: continue
        el.attrib.pop("data-asset")
        if nm == "zee": _build_zee(el, job_assets)
        elif nm == "arm": _build_arm(el, job_assets)
        else:
            a = get(nm, job_assets)
            if a is None:
                log(f"asset missing: {nm}"); continue
            _append_asset(el, a)
    return ET.tostring(root, encoding="unicode"), saved


def _append_asset(el, a, extra=""):
    ax, ay = a["anchor"]
    g = ET.SubElement(el, _q("g")); g.set("transform", f"{extra} translate({-ax:.1f},{-ay:.1f})".strip())
    import copy
    for ch in a["root"]: g.append(copy.deepcopy(ch))


def _save_group(root, el, name, desc):
    if not NAME_OK.match(name): raise ValueError("bad name (snake_case a-z0-9_)")
    if name in ("zee", "arm") or get(name) is not None: return False
    import cairosvg, copy
    from PIL import Image
    vb = root.get("viewBox") or "0 0 920 890"
    body = copy.deepcopy(el)
    for k in ("data-save", "data-desc", "data-anim", "transform"): body.attrib.pop(k, None)
    inner = ET.tostring(body, encoding="unicode")
    probe = f'<svg xmlns="{SVG_NS}" viewBox="{vb}">{inner}</svg>'
    x0, y0, w, h = [float(v) for v in vb.split()]
    S = 2
    im = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=probe.encode(), output_width=int(w * S)))).convert("RGBA")
    bb = im.getchannel("A").getbbox()
    if not bb: return False
    bx0, by0, bx1, by1 = [v / S for v in bb]
    bx0 += x0; bx1 += x0; by0 += y0; by1 += y0
    pad = 6
    doc = (f'<svg xmlns="{SVG_NS}" viewBox="{bx0-pad:.0f} {by0-pad:.0f} {bx1-bx0+2*pad:.0f} {by1-by0+2*pad:.0f}" '
           f'data-anchor="{(bx0+bx1)/2:.1f} {by1:.1f}" data-desc="{_esc(desc)}" data-created="{time.strftime("%Y-%m-%d")}">'
           f'{inner}</svg>')
    os.makedirs(SAVED, exist_ok=True)
    open(os.path.join(SAVED, f"{name}.svg"), "w", encoding="utf-8").write(doc)
    _cache.pop(name, None)
    return True


def _esc(s): return (s or "").replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def _limb(x1, y1, x2, y2, col, w=34):
    return (f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{O}" stroke-width="{w+14}" stroke-linecap="round" fill="none"/>'
            f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{col}" stroke-width="{w}" stroke-linecap="round" fill="none"/>')


def _hand(x, y, r=24): return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{SKIN}" stroke="{O}" stroke-width="7"/>'


# ---------------- jointed arm ----------------
def _build_arm(el, job_assets):
    sleeve = el.get("data-sleeve", SKIN)
    sk = el.get("data-shoulder-keys", "0 0 0 0"); ek = el.get("data-elbow-keys", "0 0 0 0")
    dl = el.get("data-joint-delay", "0"); loop = el.get("data-joint-loop", "1")
    hold = el.get("data-hold"); hs = float(el.get("data-hold-scale", "1"))
    held = ""
    if hold:
        a = get(hold, job_assets)
        if a is not None:
            # centre of the item in the hand, tilted a little
            held_g = ET.Element(_q("g")); _append_asset(held_g, a, f"translate(-345,{205 + a['h'] * hs / 2:.0f}) rotate(-14 0 {-a['h']*hs/2:.0f}) scale({hs})")
            held = ET.tostring(held_g, encoding="unicode")
    xml = (f'<g data-anim="keys" data-cx="0" data-cy="0" data-delay="{dl}" data-loop="{loop}" data-keys="{sk}">'
           + _limb(0, 0, -205, 145, sleeve, 48) +
           f'<g data-anim="keys" data-cx="-205" data-cy="145" data-delay="{dl}" data-loop="{loop}" data-keys="{ek}">'
           + _limb(-205, 145, -355, 205, SKIN, 40) + held + _hand(-355, 205, 30) + '</g></g>')
    for ch in frag(xml): el.append(ch)


# ---------------- mascot ----------------
POSES = ("shock", "happy", "point", "hold", "normal")


def _zee_arms(pose):
    if pose == "shock":  return [(225, 485, 190, 330), (375, 485, 410, 330)]
    if pose == "happy":  return [(225, 485, 150, 300), (375, 485, 450, 300)]
    if pose == "point":  return [(225, 485, 205, 560), (375, 485, 470, 330)]
    if pose == "hold":   return [(225, 485, 205, 560), (375, 485, 455, 455)]
    return [(225, 485, 200, 570), (375, 485, 400, 570)]


def zee_xml(hold_xml=""):
    """All variants in one group; visibility switched per frame by anim.py (data-z)."""
    shirt = "#3DA5F0"
    body = ('<ellipse cx="300" cy="672" rx="150" ry="20" fill="#000" opacity="0.1"/>'
            + _limb(262, 590, 255, 650, "#2E4A7A", 36) + _limb(338, 590, 345, 650, "#2E4A7A", 36)
            + f'<ellipse cx="248" cy="656" rx="34" ry="18" fill="#FFFFFF" stroke="{O}" stroke-width="7"/>'
            f'<ellipse cx="352" cy="656" rx="34" ry="18" fill="#FFFFFF" stroke="{O}" stroke-width="7"/>'
            f'<path d="M215 470 Q300 430 385 470 L395 600 H205z" fill="{shirt}" stroke="{O}" stroke-width="8" stroke-linejoin="round"/>'
            f'<path d="M245 488 h110 v108 h-110z" fill="#FFFFFF" stroke="{O}" stroke-width="6" stroke-linejoin="round"/>'
            f'<path d="M300 512 l26 20 v28 h-52 v-28z" fill="#FF7A45" stroke="{O}" stroke-width="5" stroke-linejoin="round"/>')
    arms_back = ""; arms_front = ""
    for p in POSES:
        s = "".join(_limb(a, b, c, d, shirt if True else SKIN) for a, b, c, d in _zee_arms(p))
        if p == "hold": s += hold_xml
        s += "".join(_hand(c, d) for a, b, c, d in _zee_arms(p))
        if p == "point": s += _limb(470, 330, 492, 282, SKIN, 14)
        tgt = f'<g data-z="pose-{p}">{s}</g>'
        if p == "shock": arms_front += tgt
        else: arms_back += tgt
    head = (f'<ellipse cx="300" cy="300" rx="160" ry="150" fill="{SKIN}" stroke="{O}" stroke-width="8"/>'
            f'<ellipse cx="142" cy="320" rx="22" ry="30" fill="{SKIN}" stroke="{O}" stroke-width="7"/>'
            f'<ellipse cx="458" cy="320" rx="22" ry="30" fill="{SKIN}" stroke="{O}" stroke-width="7"/>'
            f'<path d="M140 290 Q150 150 300 148 Q450 150 460 290 Q420 220 380 230 L360 200 L330 228 L300 190 L270 228 L240 200 L222 232 Q170 230 140 290z" fill="#3B2A22" stroke="{O}" stroke-width="8" stroke-linejoin="round"/>'
            f'<path d="M290 152 Q300 100 340 92 Q318 120 322 152z" fill="#3B2A22" stroke="{O}" stroke-width="7" stroke-linejoin="round"/>'
            '<ellipse cx="192" cy="358" rx="26" ry="15" fill="#FF9DB0" opacity="0.9"/><ellipse cx="408" cy="358" rx="26" ry="15" fill="#FF9DB0" opacity="0.9"/>')
    cx, ey = 300, 310
    eyes_open = "".join(f'<ellipse cx="{cx+k*62}" cy="{ey}" rx="20" ry="27" fill="{O}"/><circle cx="{cx+k*62+6}" cy="{ey-9}" r="8" fill="#fff"/>' for k in (-1, 1))
    eyes_blink = "".join(f'<path d="M{cx+k*62-20} {ey} Q{cx+k*62} {ey+10} {cx+k*62+20} {ey}" stroke="{O}" stroke-width="8" fill="none" stroke-linecap="round"/>' for k in (-1, 1))
    eyes_happy = "".join(f'<path d="M{cx+k*62-24} {ey+6} Q{cx+k*62} {ey-24} {cx+k*62+24} {ey+6}" stroke="{O}" stroke-width="9" fill="none" stroke-linecap="round"/>' for k in (-1, 1))
    eyes_shock = "".join(f'<circle cx="{cx+k*62}" cy="{ey}" r="30" fill="#fff" stroke="{O}" stroke-width="7"/><circle cx="{cx+k*62}" cy="{ey+4}" r="11" fill="{O}"/>'
                         f'<path d="M{cx+k*62-24} {ey-52} Q{cx+k*62} {ey-70} {cx+k*62+24} {ey-52}" stroke="{O}" stroke-width="7" fill="none" stroke-linecap="round"/>' for k in (-1, 1))
    m_smile = f'<path d="M266 360 Q300 398 334 360" fill="#C0394F" stroke="{O}" stroke-width="7" stroke-linejoin="round"/>'
    m_happy = (f'<path d="M256 352 Q300 420 344 352 Z" fill="#C0394F" stroke="{O}" stroke-width="7" stroke-linejoin="round"/>'
               '<path d="M278 384 Q300 370 322 384 Q300 400 278 384z" fill="#FF8FA3"/>')
    m_shock = f'<ellipse cx="300" cy="378" rx="22" ry="28" fill="#C0394F" stroke="{O}" stroke-width="7"/>'
    m_talk = f'<ellipse cx="300" cy="372" rx="26" ry="20" fill="#C0394F" stroke="{O}" stroke-width="7"/><ellipse cx="300" cy="382" rx="14" ry="7" fill="#FF8FA3"/>'
    sweat = f'<path d="M420 230 q-16 26 0 36 q16 -10 0 -36z" fill="#7CC6FF" stroke="{O}" stroke-width="5"/>'
    return (f'<g data-z="root">{body}{arms_back}{head}'
            f'<g data-z="eyes-open">{eyes_open}</g><g data-z="eyes-blink">{eyes_blink}</g>'
            f'<g data-z="eyes-happy">{eyes_happy}</g><g data-z="eyes-shock">{eyes_shock}</g>'
            f'<g data-z="mouth-smile">{m_smile}</g><g data-z="mouth-happy">{m_happy}</g>'
            f'<g data-z="mouth-shock">{m_shock}</g><g data-z="mouth-talk">{m_talk}</g>'
            f'<g data-z="sweat">{sweat}</g>{arms_front}</g>')


def zee_visible(pose, blink=False, talk=False):
    """which data-z parts are visible"""
    v = {f"pose-{pose}"}
    if pose == "shock": v |= {"eyes-shock", "mouth-shock", "sweat"}
    elif pose == "happy": v |= {"eyes-happy", "mouth-happy"}
    else:
        v.add("eyes-blink" if blink else "eyes-open")
        v.add("mouth-talk" if talk else "mouth-smile")
    return v


def _build_zee(el, job_assets):
    hold_xml = ""
    h = el.get("data-hold")
    if h:
        a = get(h, job_assets)
        if a is not None:
            g = ET.Element(_q("g")); s = float(el.get("data-hold-scale", "1.3"))
            # grip the item around its middle, in front of the hand
            _append_asset(g, a, f"translate(462,{455 + a['h'] * s * 0.5:.0f}) scale({s})")
            hold_xml = ET.tostring(g, encoding="unicode")
    inner = ET.SubElement(el, _q("g")); inner.set("transform", "translate(-300,-675)")
    inner.set("data-zee", "1")
    for k in ("data-expr", "data-talk"):
        if el.get(k) is not None: inner.set(k, el.get(k))
    for ch in frag(zee_xml(hold_xml)): inner.append(ch)
    # static default (cover / non-animated renders): first pose of the timeline
    first = (el.get("data-expr") or "0 normal").split(";")[0].split()[-1]
    vis = zee_visible(first if first in POSES else "normal")
    for e in inner.iter():
        z = e.get("data-z")
        if z and z != "root" and z not in vis: e.set("display", "none")
