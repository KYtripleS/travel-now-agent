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
    {"href": "articles/best-esim-australia-2026.html", "tag": "Connectivity",
     "title": "Best eSIM for Australia (2026)", "img": "australia-esim-photo"},
    {"href": "articles/melbourne-airport-to-city.html", "tag": "City Logistics",
     "title": "Melbourne Airport to the City: SkyBus, Taxi, or the Cheap Way", "img": "melbourne-photo"},
    {"href": "articles/best-travel-insurance-australia-2026.html", "tag": "Travel Safety",
     "title": "Travel Insurance for Australia: What Actually Matters", "img": "australia-photo"},
    {"href": "articles/japan-7-day-itinerary.html", "tag": "Itinerary",
     "title": "Japan: A 7-Day First-Timer's Itinerary", "img": "japan-itin-photo"},
    {"href": "articles/thailand-10-day-itinerary.html", "tag": "Itinerary",
     "title": "Thailand: A 10-Day Itinerary", "img": "thailand-itin-photo"},
    {"href": "articles/bali-7-day-itinerary.html", "tag": "Itinerary",
     "title": "Bali: A 7-Day Itinerary", "img": "bali-itin-photo"},
    {"href": "articles/what-to-pack-for-southeast-asia.html", "tag": "Packing",
     "title": "What to Pack for Southeast Asia", "img": "pack-sea-photo"},
    {"href": "articles/what-to-pack-for-japan.html", "tag": "Packing",
     "title": "What to Pack for Japan", "img": "pack-japan-photo"},
    {"href": "articles/things-to-do-in-tokyo.html", "tag": "City Guide",
     "title": "Tokyo: The Places Worth Your Time", "img": "things-tokyo-photo"},
    {"href": "articles/things-to-do-in-kyoto.html", "tag": "City Guide",
     "title": "Kyoto: The Places Worth Your Time", "img": "things-kyoto-photo"},
    {"href": "articles/things-to-do-in-bangkok.html", "tag": "City Guide",
     "title": "Bangkok: The Places Worth Your Time", "img": "things-bangkok-photo"},
    {"href": "articles/things-to-do-in-seoul.html", "tag": "City Guide",
     "title": "Seoul: The Places Worth Your Time", "img": "things-seoul-photo"},
    {"href": "articles/things-to-do-in-osaka.html", "tag": "City Guide",
     "title": "Osaka: The Places Worth Your Time", "img": "things-osaka-photo"},
    {"href": "articles/things-to-do-in-singapore.html", "tag": "City Guide",
     "title": "Singapore: The Places Worth Your Time", "img": "things-singapore-photo"},
    {"href": "articles/things-to-do-in-bali.html", "tag": "City Guide",
     "title": "Bali: The Places Worth Your Time", "img": "things-bali-photo"},
    {"href": "articles/things-to-do-in-hong-kong.html", "tag": "City Guide",
     "title": "Hong Kong: The Places Worth Your Time", "img": "things-hongkong-photo"},
    {"href": "articles/things-to-do-in-hanoi.html", "tag": "City Guide",
     "title": "Hanoi: The Places Worth Your Time", "img": "things-hanoi-photo"},
    {"href": "articles/things-to-do-in-ho-chi-minh-city.html", "tag": "City Guide",
     "title": "Ho Chi Minh City: The Places Worth Your Time", "img": "things-hcmc-photo"},
    {"href": "articles/things-to-do-in-kuala-lumpur.html", "tag": "City Guide",
     "title": "Kuala Lumpur: The Places Worth Your Time", "img": "things-kl-photo"},
    {"href": "articles/things-to-do-in-manila.html", "tag": "City Guide",
     "title": "Manila: The Places Worth Your Time", "img": "things-manila-photo"},
    {"href": "articles/things-to-do-in-chiang-mai.html", "tag": "City Guide",
     "title": "Chiang Mai: The Places Worth Your Time", "img": "things-chiangmai-photo"},
    {"href": "articles/things-to-do-in-phuket.html", "tag": "City Guide",
     "title": "Phuket: The Places Worth Your Time", "img": "things-phuket-photo"},
    {"href": "articles/hong-kong-first-timers-guide.html", "tag": "Itinerary",
     "title": "Hong Kong: A First-Timer's Guide", "img": "hong-kong-photo"},
    {"href": "articles/seoul-first-timers-guide.html", "tag": "Itinerary",
     "title": "Seoul: A First-Timer's Guide", "img": "seoul-photo"},
    {"href": "articles/osaka-first-timers-guide.html", "tag": "Itinerary",
     "title": "Osaka: A First-Timer's Guide", "img": "osaka-photo"},
    {"href": "articles/penang-first-timers-guide.html", "tag": "Itinerary",
     "title": "Penang: A First-Timer's Guide", "img": "penang-photo"},
    {"href": "articles/yogyakarta-first-timers-guide.html", "tag": "Itinerary",
     "title": "Yogyakarta: A First-Timer's Guide", "img": "yogyakarta-photo"},
    {"href": "articles/kuala-lumpur-first-timers-guide.html", "tag": "Itinerary",
     "title": "Kuala Lumpur: A First-Timer's Guide", "img": "kl-photo"},
    {"href": "articles/manila-first-timers-guide.html", "tag": "Itinerary",
     "title": "Manila: A First-Timer's Guide", "img": "manila-photo"},
    {"href": "articles/cebu-first-timers-guide.html", "tag": "Itinerary",
     "title": "Cebu: A First-Timer's Guide", "img": "cebu-photo"},
    {"href": "articles/chiang-mai-first-timers-guide.html", "tag": "Itinerary",
     "title": "Chiang Mai: A First-Timer's Guide", "img": "chiang-mai-photo"},
    {"href": "articles/phuket-first-timers-guide.html", "tag": "Itinerary",
     "title": "Phuket: A First-Timer's Guide", "img": "phuket-photo"},
    {"href": "articles/hanoi-first-timers-guide.html", "tag": "Itinerary",
     "title": "Hanoi: A First-Timer's Guide", "img": "hanoi-photo"},
    {"href": "articles/ho-chi-minh-city-first-timers-guide.html", "tag": "Itinerary",
     "title": "Ho Chi Minh City: A First-Timer's Guide", "img": "hcmc-photo"},
    {"href": "articles/hoi-an-first-timers-guide.html", "tag": "Itinerary",
     "title": "Hoi An: A First-Timer's Guide", "img": "hoi-an-photo"},
    {"href": "articles/singapore-first-timers-guide.html", "tag": "Itinerary",
     "title": "Singapore: A First-Timer's Guide", "img": "singapore-photo"},
    {"href": "articles/bangkok-first-timers-guide.html", "tag": "Itinerary",
     "title": "Bangkok: A First-Timer's Guide", "img": "bangkok-photo"},
    {"href": "articles/bali-first-timers-guide.html", "tag": "Itinerary",
     "title": "Bali: A First-Timer's Guide", "img": "bali-photo"},
    {"href": "articles/taipei-first-timers-guide.html", "tag": "Itinerary",
     "title": "Taipei: A First-Timer's Guide", "img": "taipei-photo"},
    {"href": "articles/getting-around-taiwan.html", "tag": "City Logistics",
     "title": "Getting Around Taiwan: EasyCard, MRT & High-Speed Rail", "img": "taipei-photo"},
    {"href": "articles/things-to-do-in-taipei.html", "tag": "City Guide",
     "title": "Taipei: The Places Worth Your Time", "img": "taipei-photo"},
    {"href": "articles/sydney-first-timers-guide.html", "tag": "Itinerary",
     "title": "Sydney: A First-Timer's Guide", "img": "sydney-photo"},
    {"href": "articles/getting-around-sydney.html", "tag": "City Logistics",
     "title": "Getting Around Sydney: Opal, Trains & Ferries", "img": "sydney-photo"},
    {"href": "articles/things-to-do-in-sydney.html", "tag": "City Guide",
     "title": "Sydney: The Places Worth Your Time", "img": "sydney-photo"},
    {"href": "articles/melbourne-first-timers-guide.html", "tag": "Itinerary",
     "title": "Melbourne: A First-Timer's Guide", "img": "melbourne-photo"},
    {"href": "articles/getting-around-melbourne.html", "tag": "City Logistics",
     "title": "Getting Around Melbourne: Trams, Myki & Free Zone", "img": "melbourne-photo"},
    {"href": "articles/things-to-do-in-melbourne.html", "tag": "City Guide",
     "title": "Melbourne: The Places Worth Your Time", "img": "melbourne-photo"},
    {"href": "articles/perth-first-timers-guide.html", "tag": "Itinerary",
     "title": "Perth: A First-Timer's Guide", "img": "perth-photo"},
    {"href": "articles/getting-around-perth.html", "tag": "City Logistics",
     "title": "Getting Around Perth: Transperth & Free CAT Buses", "img": "perth-photo"},
    {"href": "articles/things-to-do-in-perth.html", "tag": "City Guide",
     "title": "Perth: The Places Worth Your Time", "img": "perth-photo"},
    {"href": "articles/suica-pasmo-ic-cards-guide.html", "tag": "City Logistics",
     "title": "Suica, Pasmo & IC Cards: The Complete 2026 Guide", "img": "japan-photo"},
    {"href": "articles/where-to-stay-in-tokyo.html", "tag": "Itinerary",
     "title": "Where to Stay in Tokyo: Neighbourhoods Compared", "img": "japan-photo-w2"},
    {"href": "articles/how-much-does-japan-cost.html", "tag": "Itinerary",
     "title": "How Much Does a Trip to Japan Cost in 2026?", "img": "japan-photo-w3"},
    {"href": "articles/shinjuku-neighbourhood-guide.html", "tag": "City Guide",
     "title": "Shinjuku, Tokyo: A Neighbourhood Guide", "img": "japan-arrival-photo"},
    {"href": "articles/gion-kyoto-neighbourhood-guide.html", "tag": "City Guide",
     "title": "Gion, Kyoto: A Neighbourhood Guide", "img": "japan-autumn-photo"},
    {"href": "articles/narita-haneda-to-central-tokyo.html", "tag": "City Logistics",
     "title": "Narita & Haneda to Central Tokyo", "img": "japan-arrival-photo"},
    {"href": "articles/tokyo-to-kyoto-shinkansen-vs-flight-vs-bus.html", "tag": "City Logistics",
     "title": "Tokyo to Kyoto: Shinkansen, Flight, or Night Bus?", "img": "japan-photo"},
    {"href": "articles/osaka-or-kyoto-where-to-base.html", "tag": "Itinerary",
     "title": "Osaka or Kyoto: Which to Base Your Trip In", "img": "japan-photo-w2"},
    {"href": "articles/japan-city-sightseeing-passes-worth-it.html", "tag": "Tours & Activities",
     "title": "Are Japan's City Sightseeing Passes Worth It?", "img": "japan-photo-w3"},
    {"href": "articles/first-day-in-tokyo-arrival-plan.html", "tag": "Itinerary",
     "title": "Your First Day in Tokyo: A Calm Arrival Plan", "img": "japan-arrival-photo"},
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
    {"href": "articles/best-esim-japan-2026.html", "tag": "Connectivity",
     "title": "Best eSIM for Japan (2026)", "img": "japan-esim-photo"},
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
    {"href": "articles/best-travel-esim-2026.html", "tag": "Connectivity",
     "title": "Best Travel eSIM 2026: Ranked, Honestly", "img": "asia-esim-photo"},
    {"href": "articles/best-travel-insurance-2026.html", "tag": "Travel Safety",
     "title": "Best Travel Insurance 2026: Ranked by Traveler Type", "img": "insurance-3way-photo"},
    {"href": "articles/best-esim-usa-2026.html", "tag": "Connectivity",
     "title": "Best eSIM for the USA (2026): How I'd Choose", "img": "japan-arrival-photo"},
    {"href": "articles/is-travel-insurance-worth-it.html", "tag": "Travel Safety",
     "title": "Is Travel Insurance Actually Worth It?", "img": "insurance-claims-photo"},
    {"href": "articles/japan-autumn-2026.html", "tag": "Seasonal",
     "title": "Japan in Autumn 2026: Foliage, Crowds & Planning", "img": "kyoto-slow-photo"},
    {"href": "articles/japan-book-in-advance-2026.html", "tag": "Tours & Activities",
     "title": "Japan Tickets That Sell Out: Book Before You Fly", "img": "japan-photo-w2"},
    {"href": "articles/travel-insurance-japan.html", "tag": "Travel Safety",
     "title": "Do You Need Travel Insurance for Japan?", "img": "japan-arrival-photo"},
    {"href": "articles/best-esim-south-korea-2026.html", "tag": "Connectivity",
     "title": "Best eSIM for South Korea (2026): How I'd Choose", "img": "asia-esim-photo"},
    {"href": "articles/jr-pass-worth-it-2026.html", "tag": "Japan Rail",
     "title": "Is the JR Pass Worth It in 2026? The Honest Math", "img": "japan-data-photo"},
    {"href": "articles/best-time-to-visit-vietnam.html", "tag": "Seasonal",
     "title": "Best Time to Visit Vietnam (2026): Region by Region", "img": "vnjp-esim-photo"},
    {"href": "articles/first-international-trip-checklist.html", "tag": "Travel Prep",
     "title": "Your First International Trip: A Calm Checklist", "img": "best-esim-ranking-photo"},
    {"href": "articles/best-time-to-visit-japan-2026.html", "tag": "Seasonal",
     "title": "Best Time to Visit Japan (2026): A Season-Honest Guide", "img": "japan-autumn-photo"},
    {"href": "articles/seoul-itinerary-3-days.html", "tag": "Itinerary",
     "title": "Seoul in 3 Days: A First-Timer's Unhurried Itinerary", "img": "asia-esim-photo"},
    {"href": "articles/jet-lag-what-actually-works.html", "tag": "Flight Comfort",
     "title": "Jet Lag, Honestly: What Helps, What's Myth", "img": "japan-esim-choice-photo"},
    {"href": "articles/best-time-to-visit-australia.html", "tag": "Seasonal",
     "title": "Best Time to Visit Australia (2026): Region by Region", "img": "australia-photo"},
    {"href": "articles/tokyo-itinerary-5-days.html", "tag": "Itinerary",
     "title": "Tokyo in 5 Days: A First-Timer's Unhurried Itinerary", "img": "tokyo-photo"},
    {"href": "articles/kyoto-autumn-2026.html", "tag": "Seasonal",
     "title": "Kyoto in Autumn 2026: Where the Colors Peak, and When", "img": "japan-tickets-photo"},
    {"href": "articles/osaka-3-day-guide.html", "tag": "Itinerary",
     "title": "Osaka in 3 Days: Food, Neighborhoods, and Day-One Energy", "img": "japan-photo-w3"},
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
        import build_library; build_library.main()
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
