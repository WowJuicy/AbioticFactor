# Abiotic Factor — Item Video Guide Site

Static website: grid of item icons → click → page with YouTube embeds + text guide.

## Setup

```bash
pip install requests
cd abiotic_guide
python generate_site.py
```

Open `site/index.html` in your browser (or host the `site/` folder on any static host).

## Add / edit items

Edit **`items.json`** only:

```json
{
  "site_title": "Abiotic Factor - Where to Get Items",
  "items": [
    {
      "name": "Circuit Board",
      "text_guide": "Plain text guide. Line breaks are kept.",
      "videos": [
        {
          "title": "Farming route",
          "youtube_id": "dQw4w9WgXcQ",
          "note": "Optional note under the video"
        }
      ]
    }
  ]
}
```

- **`name`** — must match the wiki item name (used to pull the icon).
- **`youtube_id`** — only the ID from the URL:
  - `https://www.youtube.com/watch?v=abc123` → `abc123`
  - `https://youtu.be/abc123` → `abc123`
- Leave `videos` as `[]` if you only want text for now.

Then run:

```bash
python generate_site.py
```

## Features

- Responsive icon grid (columns adjust as the window shrinks)
- Hover a tile to see the item name
- Click → detail page with text guide + embedded videos
- Icons downloaded from the official wiki and stored under `site/images/`
