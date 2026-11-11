"""Add new drawings (groups marked data-save="name" data-desc="...") from scene svgs to the library.

Usage (from a clone of branch reels-engine):
  pip install --break-system-packages cairosvg pillow
  python3 ops/save_assets.py scene1.svg scene2.svg ...
Writes assets/<name>.svg (only names that do not exist yet) and updates assets/catalog.json, then prints
the new names. Commit + push assets/ afterwards so the next runs (and the engine) see them.
"""
import json, os, sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
os.environ.setdefault("DATA_DIR", "/tmp/reels-assets-tmp")
import assets  # noqa: E402

assets.SAVED = os.path.join(ROOT, "assets"); assets.BUILTIN = "/nonexistent"
assets.RAW = "http://127.0.0.1:9/{}"     # no network: only look at the local library

cat_p = os.path.join(ROOT, "assets", "catalog.json")
cat = json.load(open(cat_p)) if os.path.exists(cat_p) else {}
new = []
for f in sys.argv[1:]:
    root = ET.fromstring(open(f, encoding="utf-8").read())
    for el in list(root.iter()):
        nm = el.get("data-save")
        if not nm or nm in cat: continue
        try:
            if assets._save_group(root, el, nm, el.get("data-desc", "")):
                a = assets._parse_asset_doc(open(os.path.join(ROOT, "assets", f"{nm}.svg"), encoding="utf-8").read())
                cat[nm] = dict(desc=a["desc"], w=round(a["w"]), h=round(a["h"])); new.append(nm)
        except Exception as e:
            print("skip", nm, e, file=sys.stderr)
json.dump(cat, open(cat_p, "w"), ensure_ascii=False, indent=1)
print(json.dumps(new))
