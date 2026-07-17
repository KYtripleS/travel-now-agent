#!/usr/bin/env python3
"""
add_favicon.py — inject (or refresh) the GY favicon block in every HTML head.

Idempotent: replaces an existing managed block, otherwise inserts before
</head>. Paths are absolute because the site lives at the domain root.
Run after publishing new pages:  python3 add_favicon.py
Check coverage:                  python3 add_favicon.py --check
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
START = "<!-- BEGIN favicon (managed by add_favicon.py) -->"
END = "<!-- END favicon -->"
BLOCK = f"""{START}
<link rel="icon" href="/favicon.svg" type="image/svg+xml"/>
<link rel="icon" href="/favicon-48.png" type="image/png" sizes="48x48"/>
<link rel="icon" href="/favicon-192.png" type="image/png" sizes="192x192"/>
<link rel="apple-touch-icon" href="/apple-touch-icon.png"/>
{END}
"""


def html_files():
    for base in ("site", "docs"):
        yield from sorted((ROOT / base).rglob("*.html"))


def main() -> None:
    check = "--check" in sys.argv
    have = miss = added = 0
    for p in html_files():
        text = p.read_text(encoding="utf-8")
        if check:
            if START in text:
                have += 1
            else:
                miss += 1
                print(f"  missing: {p.relative_to(ROOT)}")
            continue
        if START in text:
            new = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?",
                         BLOCK, text, flags=re.S)
            if new != text:
                p.write_text(new, encoding="utf-8")
                added += 1
            have += 1
        elif "</head>" in text:
            p.write_text(text.replace("</head>", BLOCK + "</head>", 1),
                         encoding="utf-8")
            added += 1
        else:
            miss += 1
            print(f"  no </head>: {p.relative_to(ROOT)}")
    if check:
        print(f"\nTotal: {have} with favicon, {miss} without")
    else:
        print(f"favicon block ensured — {added} file(s) written, "
              f"{miss} skipped (no head)")


if __name__ == "__main__":
    main()
