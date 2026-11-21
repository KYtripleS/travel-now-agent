"""City finder on the platform comparison pages (2026-11-22).

ops/epc.py (90 days): the two most-read pages, klook-vs-viator-vs-getyourguide (284 views) and
hotel-booking-sites-comparison (270), earned nothing. Their partner links go to a platform's front page,
where a reader has nothing to book yet. Every booking we have came from a page about one product in one
city (Disneyland Paris tickets, a Florence stay map, a Seoul DMZ tour). So these pages now hand the reader
straight to our dated, product-level guides, right under the verdict (most readers leave within seconds).
On klook-vs-viator-vs-getyourguide it replaces add_aeo's shorter "For your trip" picker.

Every link points to a page the site has; a missing page stops the script. Pages are grouped by region,
one left edge, ruled (style-v2.css section 20).

usage: .venv/bin/python ops/add_finder.py
"""
from __future__ import annotations

import re
import sys
from html import escape
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BEGIN, END = "<!-- BEGIN finder (managed by ops/add_finder.py) -->", "<!-- END finder -->"

TOURS = ("Booking a ticket or tour in one city? We priced each one on every partner for the same date.", [
    ("Japan", [("where-to-buy-tokyo-disney-resort-tickets", "Tokyo Disney Resort"),
               ("where-to-buy-universal-studios-japan-tickets", "Universal Studios Japan"),
               ("where-to-buy-teamlab-planets-tickets", "teamLab Planets"),
               ("where-to-buy-shibuya-sky-tickets", "Shibuya Sky"),
               ("where-to-book-mount-fuji-day-tour", "Mount Fuji day tours"),
               ("where-to-book-tokyo-food-tour", "Tokyo food tours"),
               ("where-to-book-snow-monkey-tour", "Snow monkey tours")]),
    ("Asia and the Gulf", [("where-to-buy-hong-kong-disneyland-tickets", "Hong Kong Disneyland"),
                           ("where-to-buy-shanghai-disneyland-tickets", "Shanghai Disneyland"),
                           ("where-to-buy-lotte-world-tickets", "Lotte World, Seoul"),
                           ("where-to-book-seoul-dmz-tour", "Seoul DMZ tours"),
                           ("where-to-book-jeju-bus-tour", "Jeju bus tours"),
                           ("where-to-book-taipei-day-tour", "Taipei day tours"),
                           ("where-to-buy-universal-studios-singapore-tickets", "Universal Studios Singapore"),
                           ("where-to-buy-gardens-by-the-bay-tickets", "Gardens by the Bay"),
                           ("where-to-book-bangkok-dinner-cruise", "Bangkok dinner cruises"),
                           ("where-to-book-halong-bay-cruise", "Ha Long Bay cruises"),
                           ("where-to-buy-burj-khalifa-tickets", "Burj Khalifa"),
                           ("where-to-book-dubai-desert-safari", "Dubai desert safaris")]),
    ("Europe", [("where-to-buy-eiffel-tower-tickets", "Eiffel Tower"),
                ("where-to-buy-disneyland-paris-tickets", "Disneyland Paris"),
                ("where-to-buy-colosseum-tickets", "Colosseum"),
                ("where-to-buy-vatican-museums-tickets", "Vatican Museums"),
                ("where-to-buy-harry-potter-studio-tour-tickets", "Studio tour, London"),
                ("where-to-book-rovaniemi-northern-lights-tour", "Rovaniemi aurora tours"),
                ("where-to-book-tromso-northern-lights-tour", "Tromsø aurora tours")]),
    ("Americas and Australia", [("where-to-buy-empire-state-building-tickets", "Empire State Building"),
                                ("where-to-buy-universal-studios-hollywood-tickets", "Universal Studios Hollywood"),
                                ("where-to-buy-universal-orlando-tickets", "Universal Orlando"),
                                ("where-to-book-sydney-harbour-cruise", "Sydney Harbour cruises")]),
])

STAYS = ("Choosing where to stay in one city? Each guide maps the best area for a first visit, with live rates.", [
    ("Japan", [("tokyo", "Tokyo"), ("kyoto", "Kyoto"), ("osaka", "Osaka"), ("sapporo-snow-festival", "Sapporo"),
               ("hakuba", "Hakuba"), ("fukuoka", "Fukuoka")]),
    ("Asia", [("seoul", "Seoul"), ("bangkok", "Bangkok"), ("hong-kong", "Hong Kong"), ("singapore", "Singapore"),
              ("taipei", "Taipei"), ("bali", "Bali"), ("phuket", "Phuket"), ("dubai", "Dubai")]),
    ("Europe", [("paris", "Paris"), ("london", "London"), ("rome", "Rome"), ("florence", "Florence"),
                ("barcelona", "Barcelona"), ("amsterdam", "Amsterdam"), ("lisbon", "Lisbon"), ("prague", "Prague"),
                ("vienna", "Vienna"), ("edinburgh", "Edinburgh"), ("reykjavik", "Reykjavik"),
                ("rovaniemi-christmas", "Rovaniemi")]),
    ("Americas and Australia", [("new-york", "New York"), ("los-angeles", "Los Angeles"), ("las-vegas", "Las Vegas"),
                                ("orlando", "Orlando"), ("honolulu", "Honolulu"), ("sydney", "Sydney"),
                                ("melbourne", "Melbourne")]),
])

PAGES = {
    "klook-vs-viator-vs-getyourguide": (TOURS, ""),
    "klook-vs-kkday": (TOURS, ""),
    "hotel-booking-sites-comparison": (STAYS, "where-to-stay-in-"),
}


def block(spec, prefix: str, root: Path) -> str:
    lead, groups = spec
    rows = []
    for region, items in groups:
        links = []
        for slug, label in items:
            page = f"{prefix}{slug}.html"
            if not (root / "articles" / page).exists():
                sys.exit(f"finder: missing page articles/{page}")
            links.append(f'<a href="{page}">{escape(label)}</a>')
        rows.append(f'<p class="gy-cityfind-row"><span class="gy-cityfind-region">{escape(region)}</span> '
                    + '<span class="gy-cityfind-sep">·</span> '.join(links) + "</p>")
    return (f'{BEGIN}\n<nav class="gy-cityfind" aria-label="Guides by city">\n'
            f'<p class="gy-cityfind-h">{escape(lead)}</p>\n' + "\n".join(rows) + f"\n</nav>\n{END}")


def main() -> None:
    for root in (REPO / "site", REPO / "docs"):
        for name, (spec, prefix) in PAGES.items():
            p = root / "articles" / f"{name}.html"
            s = p.read_text(encoding="utf-8")
            new = block(spec, prefix, root)
            # remove the old block piece by piece: add_aeo re-inserts the verdict at the top of the article,
            # which can land between our BEGIN comment and the nav
            s2 = re.sub(r'\n?<nav(?=[^>]*aria-label="Guides by city")[^>]*>.*?</nav>', "", s, flags=re.S)
            s2 = s2.replace(BEGIN + "\n", "").replace(BEGIN, "").replace(END + "\n", "").replace(END, "")
            # straight under the verdict and its promise line: GA4 shows most readers leave within seconds
            m = None
            for pat in (r'<p class="gy-picker".*?</p>', r'<p class="gy-promise".*?</p>', r'<aside class="gy-verdict".*?</aside>'):
                m = re.search(pat, s2, flags=re.S)
                if m:
                    break
            assert m, f"no verdict in {p}"
            s2 = s2[:m.end()] + "\n" + new + s2[m.end():]
            if s2 != s:
                p.write_text(s2, encoding="utf-8")
                print("finder:", p.relative_to(REPO))


if __name__ == "__main__":
    main()
