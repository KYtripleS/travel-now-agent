#!/usr/bin/env python3
"""
resolve_affiliate_placeholders.py

Replace [AFFILIATE: ...] markers left by the Gemini writer with real,
FTC-compliant Travelpayouts affiliate links. The URL is chosen by
matching a brand keyword inside the marker text. If no known brand is
named, the marker is unwrapped to plain text (no dead link, no fake
link) — we never invent an affiliate relationship we don't have.

All injected anchors carry rel="nofollow sponsored noopener" and
target="_blank", per the project's affiliate rules.

Usage:
  python resolve_affiliate_placeholders.py content_drafts/<slug>.final.md
  python resolve_affiliate_placeholders.py content_drafts/<slug>.final.md --check
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Brand keyword -> Travelpayouts tpx.lu link (the live set we hold)
AFFILIATE_LINKS = {
    "airalo": "https://airalo.tpx.lu/ctddHmQY",
    "saily": "https://saily.tpx.lu/1RHGIfQA",
    "klook": "https://klook.tpx.lu/wgsZkatL",
    "kkday": "https://kkday.tpx.lu/3364ws9s",
    "ekta": "https://ektatraveling.tpx.lu/nDrStdXW",
    "searadar": "https://searadar.tpx.lu/YiWnGz1v",
}

# Optionally consume backticks the writer sometimes wraps the marker in,
# so the resolved <a> tag renders as a link, not inline code.
MARKER = re.compile(r"`?\[AFFILIATE:\s*([^\]]+)\]`?")


def resolve(text: str) -> tuple[str, list[str]]:
    actions: list[str] = []

    def repl(m: re.Match) -> str:
        label = m.group(1).strip()
        low = label.lower()
        for brand, url in AFFILIATE_LINKS.items():
            if brand in low:
                actions.append(f"{label!r} -> {brand}")
                return (f'<a href="{url}" rel="nofollow sponsored noopener" '
                        f'target="_blank">{label}</a>')
        # no known brand: unwrap to plain text
        actions.append(f"{label!r} -> plain text (no affiliate match)")
        return label

    return MARKER.sub(repl, text), actions


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("path", help="content_drafts/<slug>.final.md")
    p.add_argument("--check", action="store_true", help="report only, don't write")
    args = p.parse_args()

    path = Path(args.path)
    if not path.exists():
        sys.exit(f"not found: {path}")
    text = path.read_text(encoding="utf-8")
    new, actions = resolve(text)

    if not actions:
        print("  no [AFFILIATE: ...] markers found")
        return
    for a in actions:
        print(f"  · {a}")
    if args.check:
        print("  (--check: not written)")
        return
    path.write_text(new, encoding="utf-8")
    print(f"  resolved {len(actions)} marker(s) in {path.name}")


if __name__ == "__main__":
    main()
