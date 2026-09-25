#!/usr/bin/env python3
"""One footer for every page.

The site had seven footer variants — some with Methodology, some without, one
with ten links in a row, and the homepage printing an Impact verification code
to every visitor (the meta tag in <head> already does that job). This writes the
same footer everywhere: brand line, three link columns, the affiliate
disclosure, and a copyright line. Paths are resolved per page depth.

Idempotent: the block is wrapped in markers and replaced on each run.

    python add_footer.py            # dry run
    python add_footer.py --write
"""
from __future__ import annotations

import argparse
from pathlib import Path

from bs4 import BeautifulSoup

from add_global_nav import rel_root

REPO = Path(__file__).resolve().parent
SKIP = {"googlee46af4b13b14f75e.html"}
SKIP_DIRS = {"go"}                      # short-link redirect stubs
MARK_BEGIN = "<!-- BEGIN site-footer (managed by add_footer.py) -->"
MARK_END = "<!-- END site-footer -->"

COLUMNS = [
    ("Guides", [
        ("all-guides.html", "All guides"),
        ("stay/index.html", "Where to stay"),
        ("food/index.html", "Food &amp; drink"),
        ("articles/klook-vs-viator-vs-getyourguide.html", "Booking tours"),
        ("articles/best-travel-esim-2026.html", "Travel eSIMs"),
        ("articles/best-travel-insurance-2026.html", "Travel insurance"),
        ("index.html#map", "Destinations"),
    ]),
    ("Tools", [
        ("tools/index.html", "All tools"),
        ("index.html#ready", "Ready Score"),
        ("checklist-generator.html", "Checklist generator"),
        ("tools/esim-finder.html", "eSIM finder"),
        ("gear.html", "Gear directory"),
    ]),
    ("About", [
        ("about.html", "About Gently Yonder"),
        ("editors.html", "Editors"),
        ("editorial.html", "Editorial guidelines"),
        ("methodology.html", "How we verify"),
        ("privacy.html", "Privacy"),
    ]),
]


def block(root: str) -> str:
    # Parser-canonical (attributes sorted, entities as characters), because every
    # other tool re-serialises pages through BeautifulSoup; a raw block made this
    # script "update" all 370 pages on every run.
    return str(BeautifulSoup(_raw_block(root), "html.parser"))


def _raw_block(root: str) -> str:
    cols = "".join(
        f'<div class="gy-footer-col"><h2>{title}</h2>'
        + "".join(f'<a href="{root}{href}">{label}</a>' for href, label in links)
        + "</div>"
        for title, links in COLUMNS)
    return (
        f"{MARK_BEGIN}\n"
        f'<footer class="gy-footer">\n'
        f'<div class="gy-footer-inner">\n'
        f'<div class="gy-footer-brand">'
        f'<a class="gy-footer-logo" href="{root}index.html">Gently Yonder</a>'
        f"<p>An independent travel-preparation publication. We check what we publish "
        f"against primary sources, and date every guide when it changes.</p></div>\n"
        f'<nav class="gy-footer-cols" aria-label="Footer">{cols}</nav>\n'
        f"</div>\n"
        f'<div class="gy-footer-legal">'
        f"<p>Disclosure: some links on this site are affiliate links. If you book or buy "
        f"through them we may earn a commission, at no extra cost to you; it never decides "
        f"what we recommend. As an Amazon Associate, Gently Yonder earns from qualifying "
        f"purchases.</p>"
        f'<p>&copy; 2026 Gently Yonder &middot; '
        f'<a href="https://x.com/TripWorldAdvice">@TripWorldAdvice</a></p>'
        f"</div>\n"
        f"</footer>\n"
        f"{MARK_END}"
    )


def apply(html: str, root: str) -> tuple[str, bool, str]:
    """Replace the page's body-level footer with the shared one."""
    snippet = block(root)
    if MARK_BEGIN in html and MARK_END in html:
        b = html.find(MARK_BEGIN)
        e = html.find(MARK_END, b) + len(MARK_END)
        if html[b:e] == snippet:
            return html, False, "noop"
        return html[:b] + snippet + html[e:], True, "updated"
    soup = BeautifulSoup(html, "html.parser")
    body_footers = [f for f in soup.find_all("footer") if f.parent is not None and f.parent.name == "body"]
    if not body_footers:
        return html, False, "no body-level footer"
    old = body_footers[-1]
    old.replace_with(BeautifulSoup(snippet, "html.parser"))
    return str(soup), True, "replaced"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    tally: dict[str, int] = {}
    skipped: list[str] = []
    for base_name in ("site", "docs"):
        base = REPO / base_name
        for path in sorted(base.rglob("*.html")):
            rel = path.relative_to(base)
            if path.name in SKIP or rel.parts[0] in SKIP_DIRS:
                continue
            html = path.read_text(encoding="utf-8")
            new, changed, why = apply(html, rel_root(path, base))
            tally[why] = tally.get(why, 0) + 1
            if why == "no body-level footer" and base_name == "site":
                skipped.append(str(rel))
            if changed and args.write:
                path.write_text(new, encoding="utf-8")
    print("  " + "   ".join(f"{k}: {v}" for k, v in sorted(tally.items())))
    if skipped:
        print("  pages without a body-level footer (left alone):", ", ".join(skipped))
    if not args.write:
        print("  (dry run — pass --write to apply)")


if __name__ == "__main__":
    main()
