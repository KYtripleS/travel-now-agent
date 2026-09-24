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
SKIP_DIRS = {"go"}          # short-link stubs redirect at once; no nav there
MARK_BEGIN = "<!-- BEGIN global-nav (managed by add_global_nav.py) -->"
MARK_END = "<!-- END global-nav -->"

# (href relative to site root, label)
LINKS = [
    # Hub pages, not homepage anchors: "Destinations" used to land on the
    # homepage's most-read list, and eSIM/Insurance on single articles.
    ("all-guides.html", "Guides"),
    ("index.html#map", "Destinations"),
    ("articles/klook-vs-viator-vs-getyourguide.html", "Booking"),
    ("articles/best-travel-esim-2026.html", "eSIM"),
    ("articles/best-travel-insurance-2026.html", "Insurance"),
    ("tools/index.html", "Tools"),
    ("about.html", "About"),
]
BODY_RE = re.compile(r"<body[^>]*>", re.IGNORECASE)


# GitHub Pages serves 404.html at whatever address was missing
# (/articles/old/thing.html), so its links must not be relative.
ROOT_ABSOLUTE = {"404.html"}


def rel_root(path: Path, base: Path) -> str:
    rel = path.relative_to(base)
    if rel.as_posix() in ROOT_ABSOLUTE:
        return "/"
    return "../" * (len(rel.parts) - 1)


def block(root: str) -> str:
    # Parser-canonical, like add_footer.block: other tools re-serialise pages
    # through BeautifulSoup, which sorts attributes and converts entities.
    from bs4 import BeautifulSoup
    return str(BeautifulSoup(_raw_block(root), "html.parser"))


def _raw_block(root: str) -> str:
    links = "".join(f'<a href="{root}{href}">{label}</a>' for href, label in LINKS)
    # The form's action/name are real, so Enter still reaches search.html if the
    # script fails; gy-search.js upgrades it to an instant dropdown. data-gy-root
    # is how the script resolves the index and result links at any nesting depth.
    search = (
        f'<form class="gy-search-box" role="search" action="{root}search.html" method="get">'
        # Size/stroke are set as attributes, not only in CSS: if the stylesheet
        # is momentarily stale in a browser cache, an unstyled <svg><circle> is
        # a huge black disc. Attributes make it degrade to a small outline icon.
        f'<svg class="gy-search-icon" width="15" height="15" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'aria-hidden="true">'
        f'<circle cx="11" cy="11" r="7"></circle><path d="M20 20l-3.5-3.5"></path></svg>'
        f'<input type="search" name="q" placeholder="Search guides&hellip;" '
        f'aria-label="Search guides" autocomplete="off" />'
        f'<div class="gy-search-panel" role="listbox" hidden></div>'
        f'</form>'
    )
    return (
        f'{MARK_BEGIN}\n'
        # First focusable element: keyboard and screen-reader users can jump
        # past the navigation straight to the page's <main id="main">.
        f'<a class="gy-skip" href="#main">Skip to content</a>'
        f'<nav class="gy-topnav" aria-label="Primary" data-gy-root="{root}">'
        f'<div class="gy-topnav-inner">'
        f'<a class="gy-topnav-brand" href="{root}index.html">Gently Yonder</a>'
        f'<div class="gy-topnav-links">{links}</div>'
        f'{search}'
        f'</div></nav>\n'
        f'<script defer src="{root}js/gy-search.js"></script>\n{MARK_END}'
    )


MAIN_RE = re.compile(r"<main(\s[^>]*)?>", re.IGNORECASE)


FIRST_BLOCK_RE = re.compile(r"<(section|div|header|article)(\s[^>]*)?>", re.IGNORECASE)


def ensure_main_id(html: str) -> str:
    """The skip link's target: id="main" on the first <main>, or on a page
    without one (the Ready Score Pro sales page), on its first content block."""
    if re.search(r'\bid="main"', html):
        return html
    m = MAIN_RE.search(html)
    if m is None:
        end = html.find(MARK_END)
        if end == -1:
            return html
        m = FIRST_BLOCK_RE.search(html, end)
        if m is None:
            return html
    if re.search(r"\bid=", m.group(0)):
        return html
    tag = m.group(0)
    return html[:m.start()] + tag[:-1].rstrip() + ' id="main">' + html[m.end():]


def remove(html: str) -> tuple[str, bool]:
    if MARK_BEGIN not in html:
        return html, False
    b = html.find(MARK_BEGIN)
    e = html.find(MARK_END, b) + len(MARK_END)
    return html[:b] + html[e:].lstrip("\n"), True


def inject(html: str, snippet: str) -> tuple[str, bool]:
    if MARK_BEGIN in html and MARK_END in html:
        b = html.find(MARK_BEGIN)
        e = html.find(MARK_END, b) + len(MARK_END)
        # bust_assets.py stamps ?v=<hash> onto the script src after we write it;
        # a difference in that stamp alone is not a change.
        if re.sub(r"\?v=[0-9a-f]+", "", html[b:e]) == re.sub(r"\?v=[0-9a-f]+", "", snippet):
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
            if path.relative_to(base).parts[0] in SKIP_DIRS:
                new, changed = remove(text)
            else:
                new, changed = inject(text, block(rel_root(path, base)))
                with_id = ensure_main_id(new)
                changed = changed or with_id != new
                new = with_id
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
