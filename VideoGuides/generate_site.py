#!/usr/bin/env python3
"""
Generate a static Abiotic Factor item guide site from items.json.

Usage:
    python generate_site.py

Reads  items.json
Writes site/index.html, site/item/*.html, site/assets/..., site/images/...
"""

from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
ITEMS_FILE = ROOT / "items.json"
SITE_DIR = ROOT / "site"
IMG_DIR = SITE_DIR / "images"
ITEM_DIR = SITE_DIR / "item"

WIKI_API = "https://abioticfactor.wiki.gg/api.php"
HEADERS = {"User-Agent": "AbioticFactorItemGuide/1.0 (static site generator)"}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s)
    return s.strip("-") or "item"


def cargo_all_item_images() -> dict[str, str]:
    mapping: dict[str, str] = {}
    offset = 0
    while True:
        params = {
            "action": "cargoquery",
            "tables": "Items",
            "fields": "name,image",
            "format": "json",
            "limit": "500",
            "offset": str(offset),
        }
        r = SESSION.get(WIKI_API, params=params, timeout=30)
        r.raise_for_status()
        rows = r.json().get("cargoquery", [])
        if not rows:
            break
        for row in rows:
            t = row.get("title", {})
            name = (t.get("name") or "").strip()
            image = (t.get("image") or "").strip()
            if name and image:
                mapping[name] = image
        offset += len(rows)
        if len(rows) < 500:
            break
    return mapping


def get_image_url(filename: str) -> str | None:
    filename = re.sub(r"^File:", "", filename.strip(), flags=re.IGNORECASE)
    params = {
        "action": "query",
        "titles": f"File:{filename}",
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json",
    }
    r = SESSION.get(WIKI_API, params=params, timeout=15)
    r.raise_for_status()
    pages = r.json().get("query", {}).get("pages", {})
    for page in pages.values():
        info = page.get("imageinfo") or []
        if info:
            return info[0].get("url")
    return None


def download_image(filename: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    url = get_image_url(filename)
    if not url:
        print(f"  [!] No URL for {filename}")
        return False
    try:
        r = SESSION.get(url, timeout=20)
        r.raise_for_status()
        dest.write_bytes(r.content)
        return True
    except Exception as e:
        print(f"  [!] Download failed {filename}: {e}")
        return False


def local_image_name(filename: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)


CSS = r"""
:root {
  --bg: #0f1218;
  --panel: #1a1f2a;
  --panel-2: #242b3a;
  --text: #e8ecf4;
  --muted: #9aa3b5;
  --accent: #5b9dff;
  --border: #2e3648;
  --shadow: 0 8px 24px rgba(0,0,0,.35);
  --radius: 14px;
}

* { box-sizing: border-box; }
html, body {
  margin: 0;
  padding: 0;
  background: var(--bg);
  color: var(--text);
  font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
  line-height: 1.5;
}

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

.wrap {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 18px 64px;
}

header.site-header {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 20px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 28px;
}

header.site-header h1 {
  margin: 0;
  font-size: clamp(1.35rem, 2.5vw, 1.85rem);
  font-weight: 700;
  letter-spacing: -0.02em;
}

.subtitle {
  color: var(--muted);
  margin: 4px 0 0;
  font-size: 0.95rem;
}

.search-box {
  display: flex;
  gap: 8px;
  align-items: center;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 8px 14px;
  min-width: min(320px, 100%);
}

.search-box input {
  flex: 1;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--text);
  font-size: 0.95rem;
}

.item-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(104px, 1fr));
  gap: 12px;
}

@media (min-width: 600px) {
  .item-grid { grid-template-columns: repeat(auto-fill, minmax(112px, 1fr)); gap: 14px; }
}
@media (min-width: 900px) {
  .item-grid { grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 16px; }
}

.item-card {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  aspect-ratio: 1;
  background: linear-gradient(180deg, var(--panel-2), var(--panel));
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  transition: transform .15s ease, border-color .15s ease, box-shadow .15s ease;
  overflow: hidden;
  cursor: pointer;
  text-decoration: none;
  color: inherit;
}

.item-card:hover,
.item-card:focus-visible {
  transform: translateY(-3px);
  border-color: var(--accent);
  box-shadow: 0 12px 28px rgba(91,157,255,.18);
  outline: none;
  text-decoration: none;
}

.item-card img {
  width: 72%;
  height: 72%;
  object-fit: contain;
  pointer-events: none;
}

.item-card .placeholder {
  font-size: 1.6rem;
  color: var(--muted);
}

.item-card .tip {
  position: absolute;
  left: 50%;
  bottom: 8px;
  transform: translateX(-50%) translateY(6px);
  background: rgba(8,10,16,.92);
  color: var(--text);
  font-size: 0.72rem;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 8px;
  border: 1px solid var(--border);
  white-space: nowrap;
  max-width: 95%;
  overflow: hidden;
  text-overflow: ellipsis;
  opacity: 0;
  pointer-events: none;
  transition: opacity .12s ease, transform .12s ease;
  z-index: 2;
}

.item-card:hover .tip,
.item-card:focus-visible .tip {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}

.item-card.hidden { display: none; }

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--muted);
  font-size: 0.9rem;
  margin-bottom: 18px;
}
.back-link:hover { color: var(--accent); }

.detail-hero {
  display: flex;
  gap: 20px;
  align-items: center;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px;
  margin-bottom: 28px;
  box-shadow: var(--shadow);
}

.detail-hero img {
  width: 96px;
  height: 96px;
  object-fit: contain;
  background: var(--panel-2);
  border-radius: 12px;
  padding: 8px;
  border: 1px solid var(--border);
}

.detail-hero h1 {
  margin: 0;
  font-size: clamp(1.4rem, 3vw, 1.9rem);
}

.video-list {
  display: grid;
  gap: 22px;
}

.video-embed {
  position: relative;
  width: 100%;
  padding-top: 56.25%;
  background: #000;
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow);
  border: 1px solid var(--border);
}

.video-embed iframe {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border: 0;
}

.empty-state {
  color: var(--muted);
  font-style: italic;
}

footer {
  margin-top: 48px;
  color: var(--muted);
  font-size: 0.85rem;
  border-top: 1px solid var(--border);
  padding-top: 16px;
}
"""

INDEX_JS = r"""
(function () {
  const input = document.getElementById("filter");
  const cards = Array.from(document.querySelectorAll(".item-card"));
  if (!input) return;
  input.addEventListener("input", () => {
    const q = input.value.trim().toLowerCase();
    cards.forEach((card) => {
      const name = (card.dataset.name || "").toLowerCase();
      card.classList.toggle("hidden", q && !name.includes(q));
    });
  });
})();
"""


def html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_index(site_title: str, items: list[dict]) -> str:
    cards = []
    for it in items:
        name = it["name"]
        slug = it["slug"]
        img = it.get("local_image")
        img_html = (
            f'<img src="images/{img}" alt="{html_escape(name)}" loading="lazy">'
            if img
            else '<div class="placeholder">?</div>'
        )
        cards.append(
            f'''<a class="item-card" href="item/{slug}.html" data-name="{html_escape(name)}">
  {img_html}
  <span class="tip">{html_escape(name)}</span>
</a>'''
        )

    cards_html = (
        "\n        ".join(cards)
        if cards
        else '<p class="empty-state">No items yet. Edit items.json and push to update.</p>'
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="referrer" content="strict-origin-when-cross-origin">
  <title>{html_escape(site_title)}</title>
  <link rel="stylesheet" href="assets/style.css">
</head>
<body>
  <div class="wrap">
    <header class="site-header">
      <div>
        <h1>{html_escape(site_title)}</h1>
        <p class="subtitle">Click an item for videos</p>
      </div>
      <div class="search-box">
        <input id="filter" type="search" placeholder="Filter items..." autocomplete="off">
      </div>
    </header>

    <main class="item-grid">
        {cards_html}
    </main>

    <footer>
      Item icons from <a href="https://abioticfactor.wiki.gg/" target="_blank" rel="noopener">Abiotic Factor Wiki</a>.
      Videos from
      <a href="https://www.youtube.com/@ReaperrGamingg" target="_blank" rel="noopener">Good Shark</a>
      and
      <a href="https://www.youtube.com/@Good_Shark" target="_blank" rel="noopener">ReaperrGamingg</a>.
    </footer>
  </div>
  <script src="assets/index.js"></script>
</body>
</html>
"""


def render_item_page(site_title: str, item: dict) -> str:
    name = item["name"]
    img = item.get("local_image")
    videos = item.get("videos") or []

    img_html = (
        f'<img src="../images/{img}" alt="{html_escape(name)}">'
        if img
        else '<div class="placeholder" style="width:96px;height:96px;display:grid;place-items:center;background:var(--panel-2);border-radius:12px">?</div>'
    )

    video_blocks = []
    for v in videos:
        vid = (v.get("youtube_id") or "").strip()
        if not vid or vid.startswith("REPLACE_"):
            continue

        video_blocks.append(
            f'''<div class="video-embed">
  <iframe
    src="https://www.youtube.com/embed/{html_escape(vid)}"
    title="YouTube video"
    frameborder="0"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
    referrerpolicy="strict-origin-when-cross-origin"
    allowfullscreen
    loading="lazy"></iframe>
</div>'''
        )

    videos_html = "\n        ".join(video_blocks)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="referrer" content="strict-origin-when-cross-origin">
  <title>{html_escape(name)} — {html_escape(site_title)}</title>
  <link rel="stylesheet" href="../assets/style.css">
</head>
<body>
  <div class="wrap">
    <a class="back-link" href="../index.html">← Back to all items</a>

    <div class="detail-hero">
      {img_html}
      <div>
        <h1>{html_escape(name)}</h1>
      </div>
    </div>

    <div class="video-list">
        {videos_html}
    </div>
  </div>
</body>
</html>
"""


def main() -> int:
    if not ITEMS_FILE.exists():
        print(f"Missing {ITEMS_FILE}")
        return 1

    data = json.loads(ITEMS_FILE.read_text(encoding="utf-8"))
    site_title = data.get("site_title") or "Abiotic Factor Item Guide"
    raw_items = data.get("items") or []

    if not raw_items:
        print("items.json has no items.")
        return 1

    print("Fetching wiki image index...")
    image_map = cargo_all_item_images()
    print(f"  {len(image_map)} items in wiki cargo.")

    (SITE_DIR / "assets").mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    ITEM_DIR.mkdir(parents=True, exist_ok=True)

    items: list[dict] = []
    download_jobs: list[tuple[str, Path]] = []

    for entry in raw_items:
        name = (entry.get("name") or "").strip()
        if not name:
            continue
        slug = slugify(name)
        wiki_image = image_map.get(name) or f"Item Icon - {name}.png"
        local = local_image_name(wiki_image)
        dest = IMG_DIR / local

        item = {
            "name": name,
            "slug": slug,
            "videos": entry.get("videos") or [],
            "wiki_image": wiki_image,
            "local_image": local,
        }
        items.append(item)
        download_jobs.append((wiki_image, dest))

    print(f"Downloading up to {len(download_jobs)} icons...")
    ok = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(download_image, fn, dest): fn
            for fn, dest in download_jobs
        }
        for fut in as_completed(futures):
            if fut.result():
                ok += 1
    print(f"  {ok}/{len(download_jobs)} images ready.")

    (SITE_DIR / "assets" / "style.css").write_text(CSS, encoding="utf-8")
    (SITE_DIR / "assets" / "index.js").write_text(INDEX_JS, encoding="utf-8")
    (SITE_DIR / "index.html").write_text(
        render_index(site_title, items), encoding="utf-8"
    )
    for item in items:
        path = ITEM_DIR / f"{item['slug']}.html"
        path.write_text(render_item_page(site_title, item), encoding="utf-8")

    print(f"\nDone. Site written to {SITE_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
