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
                "link": r["article_url"].strip(),
                "title": r.get("title", "").strip(),
                "description": r.get("description", "").strip(),
                "board": r.get("board_primary", "").strip(),
            })
    payload = {"count": len(rows), "pins": rows}
    for base in ("docs", "site"):
        out = REPO / base / "data" / "pins.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  wrote {out.relative_to(REPO)} ({len(rows)} pins)")


if __name__ == "__main__":
    main()
