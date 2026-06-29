#!/usr/bin/env python3
"""
add_email_popup.py

Injects the email-capture popup loader (js/email-popup.js) before </body>
on every public HTML page. The script path is computed relative to each
page's depth, so it works at any nesting level and survives a domain move
(relative paths don't change when the base URL does).

Idempotent — running twice does not duplicate. Mirrors site/ -> docs/ by
operating on both trees.

Usage:
  python add_email_popup.py            # dry run
  python add_email_popup.py --write
"""

from __future__ import annotations

import argparse
from pathlib import Path

REPO = Path(__file__).resolve().parent
SKIP_NAMES = {"googlee46af4b13b14f75e.html"}
MARK_BEGIN = "<!-- BEGIN email-popup (managed by add_email_popup.py) -->"
MARK_END = "<!-- END email-popup -->"


def rel_prefix(path: Path, base: Path) -> str:
    # depth = number of directories between the file and the base root
    depth = len(path.relative_to(base).parts) - 1
    return "../" * depth


def block(path: Path, base: Path) -> str:
    rel = rel_prefix(path, base)
    src = rel + "js/email-popup.js"
    return (f'{MARK_BEGIN}\n<script src="{src}" data-root="{rel}" defer></script>\n'
            f'{MARK_END}\n')


def inject(html: str, snippet: str) -> tuple[str, bool]:
    # Replace an existing block if present (so attribute/path changes propagate),
    # otherwise insert before </body>.
    if MARK_BEGIN in html and MARK_END in html:
        b = html.find(MARK_BEGIN)
        e = html.find(MARK_END, b) + len(MARK_END)
        existing = html[b:e]
        new_inner = snippet.rstrip("\n")
        if existing == new_inner:
            return html, False
        return html[:b] + new_inner + html[e:], True
    idx = html.rfind("</body>")
    if idx == -1:
        return html, False
    return html[:idx] + snippet + html[idx:], True


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
            if path.name in SKIP_NAMES:
                counts["skip"] += 1
                continue
            text = path.read_text(encoding="utf-8")
            new, changed = inject(text, block(path, base))
            if not changed:
                counts["noop"] += 1
                continue
            counts["changed"] += 1
            if args.write:
                path.write_text(new, encoding="utf-8")

    print(f"  changed: {counts['changed']}   already had it: {counts['noop']}   skipped: {counts['skip']}")
    if not args.write and counts["changed"]:
        print("  (dry run — pass --write to apply)")


if __name__ == "__main__":
    main()
