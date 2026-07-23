#!/usr/bin/env python3
"""
inject_newsletter_brief.py — elevate the article newsletter CTA into a named
core product: "The Weekly Travel Prep Brief", with the Pre-Flight Checklist
repositioned as the subscribe welcome gift and a clearer subscribe verb.

Rationale (CEO dashboard, recurring problem): 0 subscribers / 0 newsletter
clicks. The newsletter is the owned-audience hedge against Google's whims, so
it should read as a product people choose — not a footer afterthought.

This patches the ~109 article pages that share the publish_article.py template
block (label "Gently Yonder Weekly"). It does four exact, unique substring
replacements, so it is safe and idempotent (a second run is a no-op) and does
NOT touch the homepage or the country/city hub variants, which are handled
separately. Mirrors every change from site/ to docs/.

Usage:
  python inject_newsletter_brief.py            # dry run (counts only)
  python inject_newsletter_brief.py --write     # apply + mirror to docs/
"""
from __future__ import annotations

import argparse
from pathlib import Path

REPO = Path(__file__).resolve().parent

# (old, new) — each old string is unique within the article newsletter block
# and stable across all ~109 pages (and the publish_article.py template).
REPLACEMENTS: list[tuple[str, str]] = [
    (
        '<span class="newsletter-label">Gently Yonder Weekly</span>',
        '<span class="newsletter-label">The Weekly Travel Prep Brief</span>',
    ),
    (
        "No spam. No influencer fluff.",
        "No spam, no influencer fluff. Subscribe and the printable "
        "Pre-Flight Checklist arrives as your welcome.",
    ),
    (
        "Get Travel Tips →",
        "Subscribe free →",
    ),
    (
        "Free. Unsubscribe in one click, anytime.",
        "Free. The welcome checklist arrives instantly. "
        "Unsubscribe in one click, anytime.",
    ),
]


def patch(text: str) -> tuple[str, int]:
    n = 0
    for old, new in REPLACEMENTS:
        if old in text:
            text = text.replace(old, new)
            n += 1
    return text, n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="apply (else dry run)")
    args = ap.parse_args()

    site = REPO / "site"
    changed = 0
    for src in sorted(site.rglob("*.html")):
        text = src.read_text(encoding="utf-8")
        new, n = patch(text)
        if n == 0:
            continue
        changed += 1
        rel = src.relative_to(site)
        print(f"  ✓ {rel}  ({n}/4 replacements)")
        if args.write:
            src.write_text(new, encoding="utf-8")
            dst = REPO / "docs" / rel
            if dst.exists():
                d = dst.read_text(encoding="utf-8")
                d2, _ = patch(d)
                dst.write_text(d2, encoding="utf-8")

    print(f"\n  files changed: {changed}")
    if not args.write and changed:
        print("  (dry run — pass --write to apply and mirror to docs/)")


if __name__ == "__main__":
    main()
