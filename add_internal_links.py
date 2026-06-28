#!/usr/bin/env python3
"""
add_internal_links.py

Inject a "Keep reading on Travel Now" section into every public article,
linking to 4-6 topically related siblings with a short hook each. The
goal is to push link equity around the 18-article corpus so each piece
benefits from the others' rankings, and to give readers an obvious next
step (which also lifts session depth metrics Google notices).

Each insertion is wrapped in an HTML comment marker so re-running is a
no-op. The script computes relative paths so it works for nested files
(articles/, countries/x/, cities/tokyo/asakusa.html, etc.).

Usage:
  python add_internal_links.py            # dry run
  python add_internal_links.py --write    # apply
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

REPO = Path(__file__).resolve().parent
SITE = REPO / "site"
DOCS = REPO / "docs"

MARK_BEGIN = "<!-- BEGIN internal-links (managed by add_internal_links.py) -->"
MARK_END = "<!-- END internal-links -->"

# title + hook (one-sentence "why this is worth reading next")
ARTICLES: dict[str, tuple[str, str]] = {
    "articles/airport-security-bag-rules.html": (
        "Airport Security Bag Rules",
        "What gets flagged at the X-ray belt and how to repack to avoid the bin.",
    ),
    "articles/airport-security-liquids.html": (
        "Airport Security Liquids Checklist",
        "The 100ml rule made simple — containers, the clear bag, common rejections.",
    ),
    "articles/airport-security-packing-moments.html": (
        "Carry-On Packing Order",
        "Pack in the order security expects — liquids on top, laptop accessible.",
    ),
    "articles/beach-trip-packing-checklist.html": (
        "Beach Trip Packing Checklist",
        "Reef-safe sunscreen, packable hats, quick-dry towels — pack lighter for the tropics.",
    ),
    "articles/capsule-wardrobe-2-week-trips.html": (
        "Capsule Wardrobe for 2-Week Trips",
        "Ten items, three climates — fabrics, layering, and laundry on the road.",
    ),
    "articles/charter-a-boat-for-a-day.html": (
        "Charter a Boat for a Day",
        "Which licences you actually need country by country, and where to find boats.",
    ),
    "articles/esim-activation-and-preparation.html": (
        "eSIM Setup for International Travel",
        "Phone compatibility, plan choice, and the activation order that avoids the airport scramble.",
    ),
    "articles/everyday-carry-essentials-for-travel.html": (
        "Travel EDC Checklist",
        "Power bank, water bottle, sanitiser — the pocket setup that keeps your day moving.",
    ),
    "articles/hotel-booking-sites-comparison.html": (
        "Hotel Booking Sites Compared",
        "Hotels.com, Booking.com, Trip.com, Agoda — what each is genuinely good for.",
    ),
    "articles/south-korea-country-profile.html": (
        "South Korea Country Profile",
        "Layered history and society, plus practical preparation for Seoul-bound travellers.",
    ),
    "articles/travel-insurance-compared.html": (
        "Travel Insurance Compared",
        "SafetyWing vs World Nomads vs Genki — coverage, exclusions, and how to choose.",
    ),
    "articles/untranslatable-words.html": (
        "14 Untranslatable Words",
        "Saudade, komorebi, sisu — words that resist English and what they teach travellers.",
    ),
    "articles/what-counts-as-rude.html": (
        "What Counts as Rude in 12 Cultures",
        "Goffman, Hofstede, and twelve country case studies for international travellers.",
    ),
    "countries/japan/index.html": (
        "Japan Country Profile",
        "Eight-section country deep-dive: history, geography, society, and travel prep.",
    ),
    "countries/vietnam/index.html": (
        "Vietnam Country Profile",
        "Layered country profile from Đông Sơn drums to Đổi Mới reforms, with prep.",
    ),
    "countries/australia/index.html": (
        "Australia Country Profile",
        "Indigenous continuity to modern federation, with layered travel preparation.",
    ),
    "cities/tokyo/index.html": (
        "Tokyo City Guide",
        "First-time visitor's layered introduction — neighbourhoods, food, and prep.",
    ),
    "cities/tokyo/asakusa.html": (
        "Asakusa, Tokyo",
        "Sensoji and Edo streets, with practical visit tips and nearby districts to combine.",
    ),
}

# each article → list of related-article paths (4-6 each)
LINKS: dict[str, list[str]] = {
    "articles/airport-security-bag-rules.html": [
        "articles/airport-security-liquids.html",
        "articles/airport-security-packing-moments.html",
        "articles/everyday-carry-essentials-for-travel.html",
        "articles/capsule-wardrobe-2-week-trips.html",
        "articles/beach-trip-packing-checklist.html",
        "articles/esim-activation-and-preparation.html",
    ],
    "articles/airport-security-liquids.html": [
        "articles/airport-security-bag-rules.html",
        "articles/airport-security-packing-moments.html",
        "articles/everyday-carry-essentials-for-travel.html",
        "articles/capsule-wardrobe-2-week-trips.html",
        "articles/esim-activation-and-preparation.html",
    ],
    "articles/airport-security-packing-moments.html": [
        "articles/airport-security-liquids.html",
        "articles/airport-security-bag-rules.html",
        "articles/everyday-carry-essentials-for-travel.html",
        "articles/esim-activation-and-preparation.html",
        "articles/capsule-wardrobe-2-week-trips.html",
    ],
    "articles/beach-trip-packing-checklist.html": [
        "articles/capsule-wardrobe-2-week-trips.html",
        "articles/everyday-carry-essentials-for-travel.html",
        "articles/travel-insurance-compared.html",
        "countries/vietnam/index.html",
        "countries/australia/index.html",
    ],
    "articles/capsule-wardrobe-2-week-trips.html": [
        "articles/beach-trip-packing-checklist.html",
        "articles/everyday-carry-essentials-for-travel.html",
        "articles/airport-security-bag-rules.html",
        "countries/japan/index.html",
        "countries/vietnam/index.html",
        "countries/australia/index.html",
    ],
    "articles/charter-a-boat-for-a-day.html": [
        "articles/travel-insurance-compared.html",
        "articles/everyday-carry-essentials-for-travel.html",
        "articles/hotel-booking-sites-comparison.html",
        "articles/untranslatable-words.html",
    ],
    "articles/esim-activation-and-preparation.html": [
        "articles/hotel-booking-sites-comparison.html",
        "articles/travel-insurance-compared.html",
        "articles/airport-security-packing-moments.html",
        "countries/japan/index.html",
        "cities/tokyo/index.html",
        "countries/vietnam/index.html",
    ],
    "articles/everyday-carry-essentials-for-travel.html": [
        "articles/airport-security-bag-rules.html",
        "articles/capsule-wardrobe-2-week-trips.html",
        "articles/beach-trip-packing-checklist.html",
        "articles/esim-activation-and-preparation.html",
        "articles/travel-insurance-compared.html",
    ],
    "articles/hotel-booking-sites-comparison.html": [
        "articles/esim-activation-and-preparation.html",
        "articles/travel-insurance-compared.html",
        "countries/japan/index.html",
        "cities/tokyo/index.html",
        "countries/vietnam/index.html",
        "articles/south-korea-country-profile.html",
    ],
    "articles/south-korea-country-profile.html": [
        "cities/tokyo/index.html",
        "countries/japan/index.html",
        "countries/vietnam/index.html",
        "articles/esim-activation-and-preparation.html",
        "articles/hotel-booking-sites-comparison.html",
        "articles/what-counts-as-rude.html",
    ],
    "articles/travel-insurance-compared.html": [
        "articles/esim-activation-and-preparation.html",
        "articles/hotel-booking-sites-comparison.html",
        "articles/charter-a-boat-for-a-day.html",
        "articles/everyday-carry-essentials-for-travel.html",
        "countries/japan/index.html",
    ],
    "articles/untranslatable-words.html": [
        "articles/what-counts-as-rude.html",
        "countries/japan/index.html",
        "countries/vietnam/index.html",
        "articles/south-korea-country-profile.html",
    ],
    "articles/what-counts-as-rude.html": [
        "articles/untranslatable-words.html",
        "countries/japan/index.html",
        "countries/vietnam/index.html",
        "articles/south-korea-country-profile.html",
        "cities/tokyo/index.html",
    ],
    "countries/japan/index.html": [
        "cities/tokyo/index.html",
        "cities/tokyo/asakusa.html",
        "articles/south-korea-country-profile.html",
        "countries/vietnam/index.html",
        "articles/esim-activation-and-preparation.html",
        "articles/hotel-booking-sites-comparison.html",
        "articles/what-counts-as-rude.html",
    ],
    "cities/tokyo/index.html": [
        "countries/japan/index.html",
        "cities/tokyo/asakusa.html",
        "articles/esim-activation-and-preparation.html",
        "articles/hotel-booking-sites-comparison.html",
        "articles/what-counts-as-rude.html",
        "articles/airport-security-packing-moments.html",
    ],
    "cities/tokyo/asakusa.html": [
        "cities/tokyo/index.html",
        "countries/japan/index.html",
        "articles/esim-activation-and-preparation.html",
        "articles/what-counts-as-rude.html",
        "articles/untranslatable-words.html",
    ],
    "countries/vietnam/index.html": [
        "countries/japan/index.html",
        "articles/south-korea-country-profile.html",
        "cities/tokyo/index.html",
        "articles/esim-activation-and-preparation.html",
        "articles/hotel-booking-sites-comparison.html",
        "articles/beach-trip-packing-checklist.html",
    ],
    "countries/australia/index.html": [
        "countries/japan/index.html",
        "articles/esim-activation-and-preparation.html",
        "articles/travel-insurance-compared.html",
        "articles/capsule-wardrobe-2-week-trips.html",
        "articles/beach-trip-packing-checklist.html",
        "articles/everyday-carry-essentials-for-travel.html",
    ],
}


def rel_link(from_file: str, to_file: str) -> str:
    from_dir = os.path.dirname(from_file)
    return os.path.relpath(to_file, from_dir).replace(os.sep, "/")


def render_section(from_file: str) -> str:
    targets = LINKS[from_file]
    items: list[str] = []
    for t in targets:
        title, hook = ARTICLES[t]
        href = rel_link(from_file, t)
        items.append(f'<li><a href="{href}">{title}</a> — {hook}</li>')
    items_html = "\n".join(items)
    return (
        f'{MARK_BEGIN}\n'
        f'<section class="keep-reading" style="margin: 36px 0;">\n'
        f'<h2>Keep reading on Travel Now</h2>\n'
        f'<ul>\n'
        f'{items_html}\n'
        f'</ul>\n'
        f'</section>\n'
        f'{MARK_END}'
    )


def inject(html: str, section: str) -> tuple[str, bool]:
    if MARK_BEGIN in html:
        return html, False
    anchor = "</main>"
    idx = html.rfind(anchor)
    if idx == -1:
        return html, False
    return html[:idx] + section + "\n" + html[idx:], True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="apply (otherwise dry run)")
    args = parser.parse_args()

    changed = 0
    for rel in ARTICLES:
        if rel not in LINKS:
            print(f"  ⚠ no link plan for {rel}")
            continue
        src = SITE / rel
        if not src.exists():
            print(f"  ⚠ missing source: {rel}")
            continue
        html = src.read_text(encoding="utf-8")
        section = render_section(rel)
        new, ok = inject(html, section)
        if not ok:
            print(f"  ⏭  {rel}: no-op (marker present or no </main>)")
            continue
        changed += 1
        n = len(LINKS[rel])
        print(f"  ✓  {rel}  ({n} links)")
        if args.write:
            src.write_text(new, encoding="utf-8")
            dst = DOCS / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(new, encoding="utf-8")

    print()
    print(f"  changed: {changed} / {len(ARTICLES)}")
    if not args.write and changed:
        print("  (dry run — pass --write to apply and mirror to docs/)")


if __name__ == "__main__":
    main()
