#!/usr/bin/env python3
"""
migrate_domain.py

One-shot migration of the site's absolute base URL when moving from the
GitHub Pages project subpath (kytriples.github.io/travel-now-agent) to a
custom apex domain (e.g. tripprep.com).

It rewrites every hard-coded absolute URL — canonicals, sitemap entries,
Open Graph tags, JSON-LD `url`/`@id` fields, and the BASE_URL constants in
the Python tooling — so nothing keeps pointing at the old address.

IMPORTANT ordering (see migration guide):
  1. Buy the domain and configure DNS first.
  2. Run this with --write.
  3. Add docs/CNAME LAST (this script can do it with --cname), then push.
Adding the CNAME before DNS resolves takes the live site down.

Usage:
  python migrate_domain.py --domain tripprep.com                 # dry run
  python migrate_domain.py --domain tripprep.com --write         # rewrite URLs
  python migrate_domain.py --domain tripprep.com --write --cname # + write docs/CNAME
"""

from __future__ import annotations

import argparse
from pathlib import Path

REPO = Path(__file__).resolve().parent
OLD_BASE = "https://kytriples.github.io/travel-now-agent"

# Where to look. We rewrite HTML/XML/TXT content and the Python BASE_URL consts.
SCAN_DIRS = ["site", "docs"]
SCAN_SUFFIXES = {".html", ".xml", ".txt"}
PY_FILES = ["publish_article.py", "build_country_power_pages.py"]


def new_base(domain: str) -> str:
    return f"https://{domain}"


def migrate(domain: str, write: bool) -> dict:
    counts = {"files_changed": 0, "occurrences": 0}
    targets: list[Path] = []
    for d in SCAN_DIRS:
        root = REPO / d
        if root.exists():
            targets += [p for p in root.rglob("*") if p.suffix in SCAN_SUFFIXES]
    targets += [REPO / f for f in PY_FILES if (REPO / f).exists()]

    nb = new_base(domain)
    for p in targets:
        text = p.read_text(encoding="utf-8")
        n = text.count(OLD_BASE)
        if not n:
            continue
        counts["files_changed"] += 1
        counts["occurrences"] += n
        if write:
            p.write_text(text.replace(OLD_BASE, nb), encoding="utf-8")
    return counts


def write_cname(domain: str) -> None:
    for d in SCAN_DIRS:
        root = REPO / d
        if root.exists():
            (root / "CNAME").write_text(domain + "\n", encoding="utf-8")
            print(f"  wrote {d}/CNAME -> {domain}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True, help="new apex domain, e.g. tripprep.com")
    ap.add_argument("--write", action="store_true", help="apply URL rewrite")
    ap.add_argument("--cname", action="store_true",
                    help="also write site/CNAME and docs/CNAME (do this LAST, after DNS)")
    args = ap.parse_args()

    print(f"  old base : {OLD_BASE}")
    print(f"  new base : {new_base(args.domain)}")
    counts = migrate(args.domain, args.write)
    print(f"  files w/ base URL : {counts['files_changed']}")
    print(f"  occurrences       : {counts['occurrences']}")
    if args.write and args.cname:
        write_cname(args.domain)
    if not args.write:
        print("  (dry run — add --write to apply)")
    else:
        print("  done. Re-run audit_site.py, then commit + push.")
        if not args.cname:
            print("  NOTE: add the CNAME only after DNS resolves: --write --cname")


if __name__ == "__main__":
    main()
