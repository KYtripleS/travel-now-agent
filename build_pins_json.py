#!/usr/bin/env python3
"""
build_pins_json.py

Publish the pin library as a clean JSON feed that an n8n workflow (or any
scheduler) can fetch and post. Reads marketing/pinterest_kit/pins.csv and
writes:
  docs/data/pins.json   (served at https://gentlyyonder.com/data/pins.json)
  site/data/pins.json   (mirror)

Each entry: image (public PNG URL), link (article URL), title, description,
board. Nothing secret — all of this is already public on the pins.

Usage:
  python build_pins_json.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent
CSV = REPO / "marketing" / "pinterest_kit" / "pins.csv"
BASE = "https://gentlyyonder.com"


# Pinterest's app often opens links without a referrer, so an untagged pin
# visit lands in GA4 as "Direct" and is lost among the bots. The tag credits it
# to Pinterest (Organic Social). Links already tagged in pins.csv keep theirs.
UTM = "utm_source=pinterest&utm_medium=pin&utm_campaign=autopost"


def tagged(url: str) -> str:
    if "utm_" in url:
        return url
    base, hash_, frag = url.partition("#")
    return f"{base}{'&' if '?' in base else '?'}{UTM}{hash_}{frag}"


def public_image(pin_filename: str) -> str:
    # "site/images/pinterest/x.png" -> "https://gentlyyonder.com/images/pinterest/x.png"
    rel = pin_filename.replace("site/", "").replace("docs/", "").lstrip("/")
    return f"{BASE}/{rel}"


def main() -> None:
    rows = []
    with CSV.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r.get("pin_filename") or not r.get("article_url"):
                continue
            rows.append({
                "slug": r.get("slug", ""),
                "image": public_image(r["pin_filename"]),
                "link": tagged(r["article_url"].strip()),
                "title": r.get("title", "").strip(),
                "description": r.get("description", "").strip(),
                "board": r.get("board_primary", "").strip(),
            })
    # Since July 2026, pins have also been appended to pins.json directly (the
    # city and product pins), so the CSV no longer holds them all. Rebuilding
    # from the CSV alone would silently drop those pins from the live feed.
    live = REPO / "site" / "data" / "pins.json"
    if live.exists():
        ours = {r["image"] for r in rows}
        missing = [p["slug"] for p in json.loads(live.read_text(encoding="utf-8"))["pins"]
                   if p["image"] not in ours]
        if missing:
            raise SystemExit(f"refusing to rebuild: {len(missing)} live pins are not in "
                             f"{CSV.relative_to(REPO)} (e.g. {', '.join(missing[:3])}). "
                             "Add them to the CSV first, or edit site/data/pins.json directly.")
    payload = {"count": len(rows), "pins": rows}
    for base in ("docs", "site"):
        out = REPO / base / "data" / "pins.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  wrote {out.relative_to(REPO)} ({len(rows)} pins)")


if __name__ == "__main__":
    main()
