#!/usr/bin/env python3
"""
build_carousel.py

Regenerate the homepage "All travel prep guides" carousel (site/index.html,
section id="guides") from the SLIDES registry below, and mirror the result
to docs/index.html. Also refreshes the hero "N travel guides" counter so it
always matches the number of slides.

The slide block is wrapped in BEGIN/END markers, so re-running is
idempotent (same pattern as add_internal_links.py). Publishing a new
article means adding one SLIDES entry (or, for the rare non-guide page,
one SKIP entry) — the script exits non-zero whenever an article in
site/articles/ is in neither list, so the carousel can't silently go
stale again.

Usage:
  python build_carousel.py            # dry run + staleness check
  python build_carousel.py --write    # apply to site/index.html + docs/index.html
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
SITE = REPO / "site"
DOCS = REPO / "docs"
INDEX = "index.html"

MARK_BEGIN = "<!-- BEGIN guides-carousel (managed by build_carousel.py) -->"
MARK_END = "<!-- END guides-carousel -->"
INDENT = " " * 12  # matches the <li> indentation inside .carousel-track

# Articles that are published but deliberately NOT in the guides carousel.
SKIP = {
    "south-korea-country-profile.html",  # featured in the homepage countries list
}

# Display order = slide order. img is the base name under images/pinterest/
# (both .webp and .png must exist). alt defaults to title.
SLIDES: list[dict[str, str]] = [
    {"href": "articles/airport-security-liquids.html", "tag": "Carry-on Prep",
     "title": "Airport Security Liquids Checklist", "img": "airport-liquids-photo"},
    {"href": "articles/airport-security-packing-moments.html", "tag": "Carry-on Prep",
     "title": "Carry-On Packing for Airport Security", "img": "carry-on-photo"},
    {"href": "articles/esim-activation-and-preparation.html", "tag": "Connectivity",
     "title": "eSIM Setup for International Travel", "img": "esim-photo"},
    {"href": "articles/everyday-carry-essentials-for-travel.html", "tag": "Everyday Carry",
     "title": "Travel EDC Checklist", "img": "travel-edc-photo"},
    {"href": "articles/beach-trip-packing-checklist.html", "tag": "Sun & Beach",
     "title": "Beach Trip Packing Checklist", "img": "beach-photo"},
    {"href": "articles/hotel-booking-sites-comparison.html", "tag": "Hotel Stay Comfort",
     "title": "Hotel Booking Sites Compared", "img": "hotels-photo"},
    {"href": "articles/what-counts-as-rude.html", "tag": "Cross-Cultural Etiquette",
     "title": "What Counts as Rude in 12 Cultures", "img": "etiquette-photo"},
    {"href": "articles/untranslatable-words.html", "tag": "Language & Culture",
     "title": "Untranslatable Words: 14 Concepts in 12 Languages", "img": "untranslatable-photo",
     "alt": "Untranslatable Words"},
    {"href": "articles/charter-a-boat-for-a-day.html", "tag": "Coastal Travel",
     "title": "Charter a Boat for a Day (No License Required)", "img": "boat-day-photo",
     "alt": "Charter a Boat for a Day"},
    {"href": "articles/travel-insurance-compared.html", "tag": "Travel Safety",
     "title": "Travel Insurance Compared: SafetyWing vs World Nomads vs Genki", "img": "insurance-photo",
     "alt": "Travel Insurance Compared"},
    {"href": "articles/airport-security-bag-rules.html", "tag": "Carry-on Prep",
     "title": "Airport Security Bags: Carry-On and Personal Item Rules", "img": "airport-bags-photo"},
    {"href": "articles/capsule-wardrobe-2-week-trips.html", "tag": "Packing",
     "title": "Capsule Wardrobe for 2-Week Trips", "img": "capsule-photo"},
    # — connectivity comparisons —
    {"href": "articles/airalo-vs-holafly-vs-saily.html", "tag": "Connectivity",
     "title": "Airalo vs Holafly vs Saily", "img": "esim-3way-photo"},
    {"href": "articles/best-esim-japan-korea-vietnam.html", "tag": "Connectivity",
     "title": "Best eSIM for Japan, Korea & Vietnam", "img": "asia-esim-photo"},
    {"href": "articles/best-esim-europe-2026.html", "tag": "Connectivity",
     "title": "Best eSIM for Europe (2026)", "img": "europe-esim"},
    {"href": "articles/best-esim-thailand-2026.html", "tag": "Connectivity",
     "title": "Best eSIM for Thailand (2026)", "img": "thailand-esim"},
    {"href": "articles/pocket-wifi-vs-esim.html", "tag": "Connectivity",
     "title": "Pocket WiFi vs eSIM", "img": "wifi-vs-esim-photo"},
    # — insurance —
    {"href": "articles/safetywing-vs-world-nomads.html", "tag": "Travel Safety",
     "title": "SafetyWing vs World Nomads", "img": "safetywing-vs-world-nomads-photo"},
    {"href": "articles/best-travel-insurance-digital-nomads-2026.html", "tag": "Travel Safety",
     "title": "Best Travel Insurance for Digital Nomads (2026)", "img": "nomad-insurance-photo"},
    # — Japan on the ground —
    {"href": "articles/three-slow-days-in-kyoto.html", "tag": "Itineraries",
     "title": "Three Slow Days in Kyoto", "img": "kyoto-slow-photo"},
    {"href": "articles/luggage-storage-tokyo.html", "tag": "City Logistics",
     "title": "Where to Store Luggage in Tokyo", "img": "tokyo-luggage"},
    {"href": "articles/carry-on-packing-list-10-day-japan.html", "tag": "Packing",
     "title": "Carry-On Packing List for 10 Days in Japan", "img": "japan-carry-on"},
    # — tours & final prep —
    {"href": "articles/klook-vs-viator-vs-getyourguide.html", "tag": "Tours & Activities",
     "title": "Klook vs Viator vs GetYourGuide", "img": "tours-3way-photo"},
    {"href": "articles/airport-security-checklist.html", "tag": "Carry-on Prep",
     "title": "Airport Security Checklist: 12 Points Before You Fly", "img": "airport-security-checklist-photo"},
]


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def render_slide(s: dict[str, str]) -> str:
    img = s["img"]
    alt = esc(s.get("alt", s["title"]))
    return (
        f'{INDENT}<li class="carousel-slide">\n'
        f'{INDENT}  <a href="{s["href"]}">\n'
        f'{INDENT}    <picture><source srcset="images/pinterest/{img}.webp" type="image/webp">'
        f'<img src="images/pinterest/{img}.png" alt="{alt}" loading="lazy" decoding="async" /></picture>\n'
        f'{INDENT}    <div class="carousel-caption">\n'
        f'{INDENT}      <span class="carousel-tag">{esc(s["tag"])}</span>\n'
        f'{INDENT}      <h3>{esc(s["title"])}</h3>\n'
        f'{INDENT}    </div>\n'
        f'{INDENT}  </a>\n'
        f'{INDENT}</li>'
    )


def check_images() -> list[str]:
    missing = []
    for s in SLIDES:
        for ext in ("webp", "png"):
            p = SITE / "images" / "pinterest" / f'{s["img"]}.{ext}'
            if not p.exists():
                missing.append(str(p.relative_to(REPO)))
    return missing


def check_unregistered() -> list[str]:
    registered = {Path(s["href"]).name for s in SLIDES}
    published = {p.name for p in (SITE / "articles").glob("*.html")}
    return sorted(published - registered - SKIP)


def update_hero_stat(page: str, count: int) -> tuple[str, bool]:
    pattern = r'(<span data-count-to=")\d+(">)\d+(</span>travel guides)'
    new, n = re.subn(pattern, rf"\g<1>{count}\g<2>{count}\g<3>", page, count=1)
    return new, n == 1


def rebuild(page: str) -> str:
    b = page.find(MARK_BEGIN)
    e = page.find(MARK_END, b)
    if b == -1 or e == -1:
        sys.exit(f"  ✗ {MARK_BEGIN} / {MARK_END} markers not found in site/{INDEX}")
    slides = "\n".join(render_slide(s) for s in SLIDES)
    inner = f"{MARK_BEGIN}\n{slides}\n{INDENT}{MARK_END}"
    page = page[:b] + inner + page[e + len(MARK_END):]
    page, ok = update_hero_stat(page, len(SLIDES))
    if not ok:
        print("  ⚠ hero 'N travel guides' stat not found — left unchanged")
    return page


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="apply (otherwise dry run)")
    args = parser.parse_args()

    missing = check_images()
    if missing:
        for m in missing:
            print(f"  ✗ missing image: {m}")
        sys.exit(1)

    src = SITE / INDEX
    old = src.read_text(encoding="utf-8")
    new = rebuild(old)

    if new == old:
        print(f"  ✓ carousel up to date ({len(SLIDES)} slides)")
    elif args.write:
        src.write_text(new, encoding="utf-8")
        (DOCS / INDEX).write_text(new, encoding="utf-8")
        print(f"  ✓ wrote {len(SLIDES)} slides to site/{INDEX} + docs/{INDEX}")
    else:
        print(f"  → would rewrite carousel with {len(SLIDES)} slides (dry run — pass --write)")

    unregistered = check_unregistered()
    if unregistered:
        print()
        for name in unregistered:
            print(f"  ⚠ articles/{name} is not in the carousel registry")
        print("  add it to SLIDES (or SKIP) in build_carousel.py, then re-run with --write")
        sys.exit(1)


if __name__ == "__main__":
    main()
