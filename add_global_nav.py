#!/usr/bin/env python3
"""
add_global_nav.py

Inject a Vogue-style sticky global navigation bar (brand + category links,
always visible) as the first element inside <body> on every public page.
Idempotent — re-running replaces the existing block, so link/label edits
here propagate everywhere. Paths are computed per page depth, so it works
at any nesting level and survives a domain move.

Usage:
  python add_global_nav.py            # dry run
  python add_global_nav.py --write
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent
SKIP = {"googlee46af4b13b14f75e.html"}
MARK_BEGIN = "<!-- BEGIN global-nav (managed by add_global_nav.py) -->"
MARK_END = "<!-- END global-nav -->"

# (href relative to site root, label)
LINKS = [
    ("index.html#guides", "Guides"),
    ("index.html#profiles", "Destinations"),
    ("articles/esim-activation-and-preparation.html", "eSIM &amp; Tech"),
    ("articles/travel-insurance-compared.html", "Insurance"),
    ("tools/esim-finder.html", "Tools"),
    ("about.html", "About"),
]
BODY_RE = re.compile(r"<body[^>]*>", re.IGNORECASE)


def rel_root(path: Path, base: Path) -> str:
    depth = len(path.relative_to(base).parts) - 1
    return "../" * depth


def block(root: str) -> str:
    links = "".join(f'<a href="{root}{href}">{label}</a>' for href, label in LINKS)
    return (
        f'{MARK_BEGIN}\n'
        f'<nav class="gy-topnav" aria-label="Primary"><div class="gy-topnav-inner">'
        f'<a class="gy-topnav-brand" href="{root}index.html">Gently Yonder</a>'
        f'<div class="gy-topnav-links">{links}</div>'
        f'</div></nav>\n{MARK_END}'
    )


def inject(html: str, snippet: str) -> tuple[str, bool]:
    if MARK_BEGIN in html and MARK_END in html:
        b = html.find(MARK_BEGIN)
        e = html.find(MARK_END, b) + len(MARK_END)
        if html[b:e] == snippet:
            return html, False
        return html[:b] + snippet + html[e:], True
    m = BODY_RE.search(html)
    if not m:
        return html, False
    at = m.end()
    return html[:at] + "\n" + snippet + html[at:], True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    counts = {"changed": 0, "noop": 0, "skip": 0}
    for base_name in ("site", "docs"):
        base = REPO / base_name
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.html")):
            if path.name in SKIP:
                counts["skip"] += 1
                continue
            text = path.read_text(encoding="utf-8")
            new, changed = inject(text, block(rel_root(path, base)))
            if not changed:
                counts["noop"] += 1
                continue
            counts["changed"] += 1
            if args.write:
                path.write_text(new, encoding="utf-8")
    print(f"  changed: {counts['changed']}   noop: {counts['noop']}   skipped: {counts['skip']}")
    if not args.write and counts["changed"]:
        print("  (dry run — pass --write to apply)")


if __name__ == "__main__":
    main()
