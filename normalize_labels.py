#!/usr/bin/env python3
"""Rewrite every article's eyebrow label to its canonical form (site_taxonomy).

Touches three places so they cannot disagree: the hero <p class="label">, the
JSON-LD Article articleSection, and content_drafts/<slug>.meta.json "category"
(publish_article.py reads the label from there, so a republish keeps it).

    python normalize_labels.py            # dry run
    python normalize_labels.py --write
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bs4 import BeautifulSoup

import site_taxonomy as T

REPO = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    changed = 0
    for src in sorted((REPO / "site" / "articles").glob("*.html")):
        slug = src.stem
        html = src.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")
        tag = soup.select_one("header .label")
        if tag is None:
            continue
        new = T.label_for(slug, tag.get_text(" ", strip=True))
        tag.clear()
        tag.append(new)
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                data = json.loads(script.string or "")
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and data.get("@type") == "Article":
                data["articleSection"] = new
                script.string = json.dumps(data, indent=2, ensure_ascii=False)
        out = str(soup)
        if out != html:
            changed += 1
            if args.write:
                src.write_text(out, encoding="utf-8")
                (REPO / "docs" / "articles" / src.name).write_text(out, encoding="utf-8")
        meta = REPO / "content_drafts" / f"{slug}.meta.json"
        if args.write and meta.exists():
            m = json.loads(meta.read_text(encoding="utf-8"))
            if m.get("category") != new:
                m["category"] = new
                meta.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"articles relabelled: {changed}" + ("" if args.write else "  (dry run)"))


if __name__ == "__main__":
    main()
