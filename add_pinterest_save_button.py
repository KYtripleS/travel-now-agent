#!/usr/bin/env python3
"""
add_pinterest_save_button.py

Injects Pinterest's official hover-Save SDK into every published HTML page
(articles, country profiles, city guides, the home page). When loaded, the
SDK watches inline <img> elements and shows a red "Save" button on hover,
enabling readers to one-click pin our photos to their own Pinterest boards.

This compounds with the Pinterest pin pipeline: each reader who hovers an
article photo and saves it creates a new outbound link back to that article.

Idempotent — running twice does not insert duplicates.
Usage:
  python add_pinterest_save_button.py        # dry run
  python add_pinterest_save_button.py --write
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

# Targets: any HTML file inside site/ and docs/ that is part of the
# public-facing surface. We exclude the GSC verification page.
SKIP_NAMES = {"googlee46af4b13b14f75e.html"}

TAG = '<script async defer src="https://assets.pinterest.com/js/pinit.js" data-pin-hover="true"></script>'
MARKER_BEGIN = "<!-- BEGIN Pinterest hover-Save SDK -->"
MARKER_END = "<!-- END Pinterest hover-Save SDK -->"
BLOCK = f"  {MARKER_BEGIN}\n  {TAG}\n  {MARKER_END}\n"


def iter_html(root: Path):
    for path in root.rglob("*.html"):
        if path.name in SKIP_NAMES:
            continue
        yield path


def inject(html: str) -> tuple[str, bool]:
    """Insert the script block right before </body>. Returns (new_html, changed)."""
    if MARKER_BEGIN in html:
        return html, False
    needle = "</body>"
    idx = html.rfind(needle)
    if idx == -1:
        return html, False
    return html[:idx] + BLOCK + html[idx:], True


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--write", action="store_true", help="apply changes (otherwise dry run)")
    args = p.parse_args()

    counts = {"changed": 0, "skipped": 0, "noop": 0}
    for root_name in ("site", "docs"):
        root = REPO_ROOT / root_name
        if not root.exists():
            continue
        for path in iter_html(root):
            text = path.read_text(encoding="utf-8")
            new_text, changed = inject(text)
            if not changed:
                if MARKER_BEGIN in text:
                    counts["noop"] += 1
                else:
                    counts["skipped"] += 1
                continue
            if args.write:
                path.write_text(new_text, encoding="utf-8")
            counts["changed"] += 1
            print(f"  {'wrote' if args.write else 'would write'} {path.relative_to(REPO_ROOT)}")

    print()
    print(f"changed: {counts['changed']}   noop (already had it): {counts['noop']}   skipped (no </body>): {counts['skipped']}")
    if not args.write and counts["changed"]:
        print("(dry run — pass --write to apply)")


if __name__ == "__main__":
    main()
