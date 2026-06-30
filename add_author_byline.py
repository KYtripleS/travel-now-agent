#!/usr/bin/env python3
"""
add_author_byline.py

Give every article and profile a visible human byline and a Person author
in its structured data, pointing at our editor persona's bio page
(editors.html). This is the E-E-A-T "who wrote this" signal Google looks
for, and the human anchor the brand wants — using a disclosed pen name
(Casey), never a real identity.

Two changes per page, both idempotent:
  1. Inserts <p class="article-byline">By <a>Casey</a>, Travel Now
     editor</p> right after the first </h1>.
  2. Swaps the JSON-LD author from Organization to Person (publisher stays
     the Organization). Handles both single-line and multi-line author
     objects.

Relative paths to editors.html are computed per file depth. Mirrors
site/ -> docs/.

Usage:
  python add_author_byline.py            # dry run
  python add_author_byline.py --write
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent
SITE = REPO / "site"
DOCS = REPO / "docs"
BASE_URL = "https://kytriples.github.io/travel-now-agent"
EDITOR_NAME = "Casey"
EDITOR_URL = f"{BASE_URL}/editors.html"

# author Organization object (flat, no nested braces) -> Person
AUTHOR_RE = re.compile(
    r'"author"\s*:\s*\{[^{}]*?"@type"\s*:\s*"Organization"[^{}]*?\}',
    re.DOTALL,
)
PERSON = (f'"author": {{ "@type": "Person", "name": "{EDITOR_NAME}", '
          f'"url": "{EDITOR_URL}" }}')


def targets() -> list[Path]:
    out: list[Path] = []
    out += sorted((SITE / "articles").glob("*.html"))
    out += sorted((SITE / "countries").glob("*/index.html"))
    out += sorted((SITE / "cities").glob("*/*.html"))
    return out


def rel_to_editors(file_path: Path) -> str:
    return os.path.relpath(SITE / "editors.html", file_path.parent).replace(os.sep, "/")


def byline_html(rel: str) -> str:
    return (f'<p class="article-byline">By <a href="{rel}">{EDITOR_NAME}</a>, '
            f'Travel Now editor</p>')


def process(html: str, rel: str) -> tuple[str, list[str]]:
    actions: list[str] = []

    # 1) visible byline after first </h1>
    if 'class="article-byline"' not in html:
        idx = html.find("</h1>")
        if idx != -1:
            insert_at = idx + len("</h1>")
            html = html[:insert_at] + "\n" + byline_html(rel) + html[insert_at:]
            actions.append("byline")

    # 2) author Organization -> Person (skip if already Person)
    if '"author": { "@type": "Person"' not in html and '"@type": "Person", "name": "Casey' not in html:
        new_html, n = AUTHOR_RE.subn(PERSON, html, count=1)
        if n:
            html = new_html
            actions.append("person-schema")

    return html, actions


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    changed = 0
    for src in targets():
        html = src.read_text(encoding="utf-8")
        rel = rel_to_editors(src)
        new, actions = process(html, rel)
        if not actions:
            continue
        changed += 1
        print(f"  {src.relative_to(REPO)}  [{', '.join(actions)}]")
        if args.write:
            src.write_text(new, encoding="utf-8")
            dst = DOCS / src.relative_to(SITE)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(new, encoding="utf-8")

    print(f"\n  changed: {changed}")
    if not args.write and changed:
        print("  (dry run — pass --write to apply and mirror to docs/)")


if __name__ == "__main__":
    main()
