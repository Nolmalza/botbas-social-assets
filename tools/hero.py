#!/usr/bin/env python3
"""Fetch a hero image for every card that has no PNG yet.

Card file names look like cards/YYYY-MM-DD__<owner>__<repo>.html.
For each one we look, in order, for:
  1. the repo's custom social preview (set by the author in GitHub settings)
  2. the first real image in the README (banner / screenshot; badges skipped)
  3. GitHub's own generated preview card for the repo
and save it as cards/hero/<card name>.png (1600px max side).
Nothing found -> no file, and the card falls back to its generated background.
"""
import io, json, os, re, sys, urllib.parse, urllib.request
from PIL import Image

UA = {"User-Agent": "botbas-social-assets-render"}
TOKEN = os.environ.get("GITHUB_TOKEN")
SKIP = re.compile(r"shields\.io|badgen|badge|/actions/workflows|star-history|contrib\.rocks|"
                  r"codecov|coveralls|deepwiki|trendshift|producthunt|discord|twitter|"
                  r"buymeacoffee|ko-fi|sponsor|\.svg(\?|$)|avatars\.githubusercontent", re.I)


def get(url, api=False, limit=15_000_000):
    h = dict(UA)
    if api:
        h["Accept"] = "application/vnd.github.raw"
        if TOKEN:
            h["Authorization"] = "Bearer " + TOKEN
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=20) as r:
        return r.read(limit), r.geturl()


def as_image(data, min_w=600):
    try:
        im = Image.open(io.BytesIO(data))
        im.seek(0)
        im = im.convert("RGB")
    except Exception:
        return None
    w, h = im.size
    if w < min_w or not (0.9 <= w / h <= 4.0):
        return None
    im.thumbnail((1600, 1600))
    return im


def og_images(owner, repo):
    html, _ = get(f"https://github.com/{owner}/{repo}", limit=3_000_000)
    m = re.search(rb'<meta property="og:image" content="([^"]+)"', html)
    if not m:
        return None, None
    url = m.group(1).decode().replace("&amp;", "&")
    custom = "repository-images.githubusercontent.com" in url
    return (url, None) if custom else (None, url)


def readme_images(owner, repo):
    md, _ = get(f"https://api.github.com/repos/{owner}/{repo}/readme", api=True)
    md = md.decode("utf-8", "ignore")
    urls = re.findall(r'<img[^>]+src=["\']([^"\']+)', md) + re.findall(r'!\[[^\]]*\]\(\s*<?([^)\s>]+)', md)
    # keep README order
    urls.sort(key=lambda u: md.find(u))
    out = []
    for u in urls:
        if SKIP.search(u):
            continue
        if u.startswith("//"):
            u = "https:" + u
        elif not u.startswith("http"):
            u = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/" + u.lstrip("./")
        u = re.sub(r"https://github\.com/([^/]+)/([^/]+)/blob/", r"https://raw.githubusercontent.com/\1/\2/", u)
        if u not in out:
            out.append(u)
    return out[:8]


def hero_for(owner, repo):
    custom, generated = None, None
    try:
        custom, generated = og_images(owner, repo)
    except Exception as e:
        print("  og lookup failed:", e)
    candidates = ([("custom social preview", custom)] if custom else [])
    try:
        candidates += [("README image", u) for u in readme_images(owner, repo)]
    except Exception as e:
        print("  readme lookup failed:", e)
    if generated:
        candidates.append(("GitHub preview card", generated))
    for label, url in candidates:
        try:
            data, _ = get(url)
            im = as_image(data)
            if im:
                return label, url, im
        except Exception as e:
            print("  skip", url, e)
    return None


def main():
    os.makedirs("cards/hero", exist_ok=True)
    for f in sorted(os.listdir("cards")):
        if not f.endswith(".html"):
            continue
        name = f[:-5]
        if os.path.exists(f"images/{name}.png") or os.path.exists(f"cards/hero/{name}.png"):
            continue
        parts = name.split("__")
        if len(parts) != 3:
            continue
        owner, repo = parts[1], parts[2]
        print(f"{name}: looking for hero image of {owner}/{repo}")
        found = hero_for(owner, repo)
        if found:
            label, url, im = found
            im.save(f"cards/hero/{name}.png")
            print(f"  using {label}: {url}")
        else:
            print("  none found, card keeps generated background")


if __name__ == "__main__":
    sys.exit(main())
