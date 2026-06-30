#!/usr/bin/env python3
"""
rebrand.py

One-shot brand rename across the site: "Travel Now" -> a new brand name
(e.g. "Gently Yonder"). Case-sensitive on the exact brand string so it
won't touch lowercase prose like "if you travel now...". Covers the
wordmark, page titles, og:site_name, JSON-LD publisher/author org, the
editor bio, and footers.

This is the NAME change only. The URL/domain change is migrate_domain.py.
A full cutover is:
    python rebrand.py --brand "Gently Yonder" --write
    python migrate_domain.py --domain gentlyyonder.com --write --cname
    python audit_site.py && git commit ... && git push

Recommended: run the cutover only AFTER you own the domain and DNS
resolves, so the name and the URL flip together (no half-state where the
live site says the new name but still lives at the old address).

Usage:
  python rebrand.py --brand "Gently Yonder"            # dry run
  python rebrand.py --brand "Gently Yonder" --write
"""

from __future__ import annotations

import argparse
from pathlib import Path

REPO = Path(__file__).resolve().parent
OLD = "Travel Now"
SCAN_DIRS = ("site", "docs")
SUFFIXES = {".html", ".xml", ".webmanifest"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True, help='new brand name, e.g. "Gently Yonder"')
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    new = args.brand

    files = 0
    occ = 0
    for d in SCAN_DIRS:
        root = REPO / d
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.suffix not in SUFFIXES:
                continue
            text = p.read_text(encoding="utf-8")
            n = text.count(OLD)
            if not n:
                continue
            files += 1
            occ += n
            if args.write:
                p.write_text(text.replace(OLD, new), encoding="utf-8")

    print(f'  "{OLD}" -> "{new}"')
    print(f"  files: {files}   occurrences: {occ}")
    if not args.write:
        print("  (dry run — add --write to apply)")
    else:
        print("  done. Next: migrate_domain.py, then audit + commit + push.")
        print("  NOTE: the @TripWorldAdvice X handle and the logo image files are")
        print("        not text — rename those separately if you want them changed.")


if __name__ == "__main__":
    main()
