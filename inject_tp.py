#!/usr/bin/env python3
"""
inject_tp.py — place Travelpayouts affiliate CTAs / widgets into the right pages.

Deliberate, per-page REGISTRY (not a spray). Idempotent: re-running replaces the
block between the tp-inject markers. Inserts right before each page's <footer>,
which sits after the article body — a natural, constitution-safe CTA spot on
pages that already carry affiliate links.

Light text CTAs (tpx.lu deep-links) are the default — calm and fast. The heavier
WeGoTrip tours iframe is reserved for a couple of destination hubs.

    python inject_tp.py            # inject + mirror site -> docs
"""

from __future__ import annotations

from pathlib import Path

from tp_widgets import wegotrip_tours  # verified-rendering tours widget

REPO = Path(__file__).resolve().parent
BEGIN = "<!-- BEGIN tp-inject (managed by inject_tp.py) -->"
END = "<!-- END tp-inject -->"
REL = 'rel="nofollow sponsored noopener" target="_blank"'

# --- affiliate deep-links (tpx.lu) + default anchor labels -------------------
TPX = {
    "aviasales":      "https://aviasales.tpx.lu/dESAKheX",
    "tiqets":         "https://tiqets.tpx.lu/7rZHQkfx",
    "radicalstorage": "https://radicalstorage.tpx.lu/WpAnAq1c",
    "klook":          "https://klook.tpx.lu/TgR5Suzs",
    "welcomepickups": "https://tpx.lu/YtuAbaB1",
    "saily":          "https://saily.tpx.lu/hk5XU6Sm",
    "ekta":           "https://ektatraveling.tpx.lu/LXmPxVUQ",
    "kkday":          "https://kkday.tpx.lu/99SKEU6d",
}
LABEL = {
    "aviasales":      "Compare current flight fares on Aviasales &rarr;",
    "tiqets":         "Skip-the-line attraction tickets via Tiqets &rarr;",
    "radicalstorage": "Book day-luggage storage with Radical Storage &rarr;",
    "klook":          "Tours, rail passes &amp; transfers on Klook &rarr;",
    "welcomepickups": "Arrange a private airport pickup (Welcome Pickups) &rarr;",
    "saily":          "Set up a travel eSIM with Saily &rarr;",
    "ekta":           "Compare travel insurance with EKTA &rarr;",
    "kkday":          "Book local experiences on KKday &rarr;",
}
NOTE = ("Affiliate links &mdash; Gently Yonder may earn a commission at no extra "
        "cost to you. See our full disclosure below.")


def _links_html(brands: list[str]) -> str:
    return "\n".join(
        f'    <li><a class="gy-cta-link" href="{TPX[b]}" {REL}>{LABEL[b]}</a></li>'
        for b in brands)


def cta(heading: str, brands: list[str]) -> str:
    return (f'<aside class="gy-cta">\n'
            f'  <p class="gy-cta-h">{heading}</p>\n'
            f'  <ul class="gy-cta-list">\n{_links_html(brands)}\n  </ul>\n'
            f'  <p class="gy-cta-note">{NOTE}</p>\n'
            f'</aside>')


def hub(heading: str, blurb: str, city_id: str, brands: list[str]) -> str:
    """Destination-hub block: WeGoTrip tours iframe + a few text CTAs."""
    return (f'<aside class="gy-widget">\n'
            f'  <h4 class="gy-widget-h">{heading}</h4>\n'
            f'  <p class="gy-widget-blurb">{blurb}</p>\n'
            f'  <div class="gy-widget-frame">\n{wegotrip_tours(city_id)}\n  </div>\n'
            f'  <ul class="gy-cta-list">\n{_links_html(brands)}\n  </ul>\n'
            f'  <p class="gy-widget-note">{NOTE}</p>\n'
            f'</aside>')


# --- per-page registry -------------------------------------------------------
# path (under site/ and docs/) -> block HTML
REGISTRY: dict[str, str] = {
    # ---- destination hubs (tours iframe + links) ----
    "cities/tokyo/index.html": hub(
        "Getting to Tokyo &amp; things to do",
        "Self-guided tours you can start the moment you land, plus fares, tickets, "
        "and an airport pickup for a smooth arrival.",
        "1850147", ["aviasales", "tiqets", "welcomepickups"]),
    "countries/australia/index.html": hub(
        "Getting to Australia &amp; things to do",
        "Sydney-based self-guided tours, plus current fares and local experiences "
        "for the wider trip.",
        "2147714", ["aviasales", "klook", "welcomepickups"]),

    # ---- country / city guides (tours + CTAs) ----
    "countries/vietnam/index.html": hub(
        "Tours &amp; getting to Vietnam",
        "Self-guided Hanoi tours, plus current fares, local experiences, and an "
        "airport pickup for a smooth arrival.",
        "1581130", ["aviasales", "klook", "welcomepickups"]),
    "articles/south-korea-country-profile.html": hub(
        "Tours &amp; getting to Seoul",
        "Self-guided Seoul tours, plus current fares, local experiences, and an "
        "airport pickup for a smooth arrival.",
        "1835848", ["aviasales", "klook", "welcomepickups"]),

    # ---- itineraries & seasonal (high booking intent) ----
    "articles/tokyo-itinerary-5-days.html": cta(
        "Ready to book this Tokyo trip?",
        ["aviasales", "tiqets", "welcomepickups"]),
    "articles/osaka-3-day-guide.html": hub(
        "Tours &amp; getting to Osaka",
        "Self-guided Osaka tours you can start the moment you land, plus fares, "
        "tickets, and local experiences.",
        "1853909", ["aviasales", "tiqets", "kkday"]),
    "articles/three-slow-days-in-kyoto.html": hub(
        "Tours &amp; getting to Kyoto",
        "Self-guided Kyoto walks you can start on arrival, plus fares, tickets, and a "
        "smooth airport pickup.",
        "1857910", ["aviasales", "tiqets", "kkday"]),
    "articles/kyoto-autumn-2026.html": hub(
        "Tours &amp; getting to Kyoto",
        "Self-guided Kyoto walks you can start on arrival, plus current fares and "
        "skip-the-line tickets.",
        "1857910", ["aviasales", "tiqets"]),
    "articles/seoul-itinerary-3-days.html": hub(
        "Tours &amp; getting to Seoul",
        "Self-guided Seoul tours you can start on arrival, plus fares, tickets, and "
        "local experiences.",
        "1835848", ["aviasales", "tiqets", "klook"]),
    "articles/japan-autumn-2026.html": cta(
        "Planning your Japan autumn trip",
        ["aviasales", "tiqets"]),
    "articles/best-time-to-visit-japan-2026.html": cta(
        "When you're ready to book Japan",
        ["aviasales", "tiqets"]),
    "articles/best-time-to-visit-vietnam.html": cta(
        "When you're ready to book Vietnam",
        ["aviasales", "klook"]),
    "articles/best-time-to-visit-australia.html": cta(
        "When you're ready to book Australia",
        ["aviasales", "klook"]),
    "articles/japan-book-in-advance-2026.html": cta(
        "Book the big-ticket items early",
        ["aviasales", "tiqets", "klook"]),

    # ---- exact-fit logistics ----
    "articles/luggage-storage-tokyo.html": cta(
        "Sorting your Tokyo logistics",
        ["radicalstorage", "welcomepickups", "tiqets"]),

    # ---- second wave: rail / tours / first-trip ----
    "articles/jr-pass-worth-it-2026.html": cta(
        "Booking Japan rail &amp; flights",
        ["klook", "aviasales"]),
    "articles/klook-vs-viator-vs-getyourguide.html": cta(
        "Book tours &amp; activities",
        ["klook", "kkday"]),
    "cities/tokyo/asakusa.html": cta(
        "Planning your Tokyo visit",
        ["aviasales", "tiqets", "welcomepickups"]),
    "articles/carry-on-packing-list-10-day-japan.html": cta(
        "Booking your Japan trip",
        ["aviasales", "tiqets"]),
    "articles/first-international-trip-checklist.html": cta(
        "Booking your first trip",
        ["aviasales", "welcomepickups"]),

    # ---- gap-fill: practical pages that had no CTA block (non-history, non-reflective) ----
    "articles/airalo-vs-holafly-vs-saily.html": cta("Ready to get connected?", ["saily", "aviasales"]),
    "articles/best-esim-japan-2026.html": cta("Get connected before you fly", ["saily", "aviasales"]),
    "articles/best-esim-europe-2026.html": cta("Get connected before you fly", ["saily", "aviasales"]),
    "articles/best-esim-usa-2026.html": cta("Get connected before you fly", ["saily", "aviasales"]),
    "articles/best-esim-south-korea-2026.html": cta("Get connected before you fly", ["saily", "aviasales"]),
    "articles/best-esim-thailand-2026.html": cta("Get connected before you fly", ["saily", "aviasales"]),
    "articles/best-esim-japan-korea-vietnam.html": cta("Get connected before you fly", ["saily", "aviasales"]),
    "articles/best-travel-esim-2026.html": cta("Get connected before you fly", ["saily", "aviasales"]),
    "articles/pocket-wifi-vs-esim.html": cta("Get connected before you fly", ["saily", "aviasales"]),
    "articles/best-travel-insurance-2026.html": cta("Sort your cover before you go", ["ekta", "aviasales"]),
    "articles/best-travel-insurance-digital-nomads-2026.html": cta("Sort your cover before you go", ["ekta", "aviasales"]),
    "articles/is-travel-insurance-worth-it.html": cta("Sort your cover before you go", ["ekta", "aviasales"]),
    "articles/travel-insurance-japan.html": cta("Sort your cover before you go", ["ekta", "aviasales"]),
    "articles/airport-security-checklist.html": cta("Before you fly", ["aviasales", "saily"]),

    # ---- newly published 2026-07-09 (transit / itinerary / passes) ----
    "articles/narita-haneda-to-central-tokyo.html": cta(
        "Sorting your Tokyo arrival", ["welcomepickups", "klook", "aviasales"]),
    "articles/tokyo-to-kyoto-shinkansen-vs-flight-vs-bus.html": cta(
        "Booking Tokyo to Kyoto", ["aviasales", "klook"]),
    "articles/osaka-or-kyoto-where-to-base.html": cta(
        "Planning Osaka or Kyoto", ["aviasales", "tiqets", "kkday"]),
    "articles/japan-city-sightseeing-passes-worth-it.html": cta(
        "Compare passes &amp; tickets", ["tiqets", "klook", "kkday"]),
    "articles/first-day-in-tokyo-arrival-plan.html": cta(
        "Your arrival toolkit", ["saily", "welcomepickups", "radicalstorage"]),

    # ---- batch 2026-07-09b (suica + hand-written five) ----
    "articles/suica-pasmo-ic-cards-guide.html": cta(
        "Sorting Japan transit & tickets", ["klook", "welcomepickups", "aviasales"]),
    "articles/where-to-stay-in-tokyo.html": cta(
        "Booking your Tokyo stay", ["welcomepickups", "klook", "tiqets", "aviasales"]),
    "articles/how-much-does-japan-cost.html": cta(
        "Building your Japan budget", ["aviasales", "saily", "ekta", "klook"]),
    "articles/shinjuku-neighbourhood-guide.html": cta(
        "Planning your Shinjuku visit", ["tiqets", "klook", "welcomepickups", "aviasales"]),
    "articles/gion-kyoto-neighbourhood-guide.html": cta(
        "Experiencing Gion respectfully", ["tiqets", "kkday", "klook", "aviasales"]),

    # ---- Taiwan (2026-07-10) — Taipei city_id 1668341 ----
    "articles/taipei-first-timers-guide.html": hub(
        "Tours &amp; tickets in Taipei",
        "Self-guided Taipei tours you can start on arrival, plus tickets, an eSIM, and a smooth airport pickup.",
        "1668341", ["klook", "kkday", "saily", "welcomepickups"]),
    "articles/getting-around-taiwan.html": hub(
        "Tours &amp; tickets in Taiwan",
        "Book the high-speed rail, day tours, and skip-the-line tickets in English before you go.",
        "1668341", ["klook", "kkday", "saily", "welcomepickups"]),
    "articles/things-to-do-in-taipei.html": hub(
        "Tours &amp; tickets in Taipei",
        "Self-guided Taipei tours and skip-the-line tickets for Taipei 101, the temples, and the markets.",
        "1668341", ["klook", "kkday", "tiqets", "aviasales"]),

    # ---- Australia — Sydney (2026-07-10) — city_id 2147714 ----
    "articles/sydney-first-timers-guide.html": hub(
        "Tours &amp; tickets in Sydney",
        "Self-guided Sydney tours you can start on arrival, plus current fares, tickets, and an airport pickup.",
        "2147714", ["aviasales", "klook", "saily", "welcomepickups"]),
    "articles/getting-around-sydney.html": hub(
        "Tours &amp; getting around Sydney",
        "Book harbour experiences and skip-the-line tickets, plus an easy airport pickup for arrival.",
        "2147714", ["welcomepickups", "klook", "saily", "aviasales"]),
    "articles/things-to-do-in-sydney.html": hub(
        "Tours &amp; tickets in Sydney",
        "Self-guided Sydney tours and tickets for the Opera House, the harbour, and the coast.",
        "2147714", ["klook", "tiqets", "aviasales", "welcomepickups"]),

    # ---- Australia — Melbourne (2026-07-10) — city_id 2158177 ----
    "articles/melbourne-first-timers-guide.html": hub(
        "Tours &amp; tickets in Melbourne",
        "Self-guided Melbourne tours you can start on arrival, plus fares, tickets, and an airport pickup.",
        "2158177", ["aviasales", "klook", "saily", "welcomepickups"]),
    "articles/getting-around-melbourne.html": hub(
        "Tours &amp; getting around Melbourne",
        "Book day trips and skip-the-line tickets, plus an easy airport transfer for arrival.",
        "2158177", ["welcomepickups", "klook", "saily", "aviasales"]),
    "articles/things-to-do-in-melbourne.html": hub(
        "Tours &amp; tickets in Melbourne",
        "Self-guided Melbourne tours, gallery tickets, and Great Ocean Road day tours.",
        "2158177", ["klook", "tiqets", "kkday", "aviasales"]),

    # ---- Australia — Perth (2026-07-10) — city_id 2063523 ----
    "articles/perth-first-timers-guide.html": hub(
        "Tours &amp; tickets in Perth",
        "Self-guided Perth tours you can start on arrival, plus fares, tickets, and an airport pickup.",
        "2063523", ["aviasales", "klook", "saily", "welcomepickups"]),
    "articles/getting-around-perth.html": hub(
        "Tours &amp; getting around Perth",
        "Book the Rottnest ferry, day tours, and tickets, plus an easy airport transfer for arrival.",
        "2063523", ["welcomepickups", "klook", "saily", "aviasales"]),
    "articles/things-to-do-in-perth.html": hub(
        "Tours &amp; tickets in Perth",
        "Self-guided Perth tours and tickets, plus Rottnest Island ferry-and-tour packages.",
        "2063523", ["klook", "tiqets", "kkday", "aviasales"]),

    # ---- SE Asia (2026-07-11) ----
    "articles/singapore-first-timers-guide.html": hub(
        "Tours &amp; tickets in Singapore",
        "Self-guided Singapore tours you can start on arrival, plus fares, tickets, and an airport pickup.",
        "1880252", ["klook", "kkday", "saily", "welcomepickups"]),
    "articles/bangkok-first-timers-guide.html": hub(
        "Tours &amp; tickets in Bangkok",
        "Self-guided Bangkok tours, temple and market tickets, an eSIM, and an airport pickup.",
        "1609350", ["klook", "kkday", "saily", "welcomepickups"]),
    "articles/bali-first-timers-guide.html": hub(
        "Tours &amp; tickets in Bali",
        "Self-guided Bali tours, temple tickets, an eSIM, and an airport transfer for arrival.",
        "1645528", ["klook", "kkday", "saily", "welcomepickups"]),

    # ---- Vietnam expansion (2026-07-11) ----
    "articles/hanoi-first-timers-guide.html": hub(
        "Tours &amp; tickets in Hanoi",
        "Self-guided Hanoi tours, plus Ha Long Bay and Ninh Binh day trips, an eSIM, and an airport pickup.",
        "1581130", ["klook", "kkday", "saily", "welcomepickups"]),
    "articles/ho-chi-minh-city-first-timers-guide.html": hub(
        "Tours &amp; tickets in Ho Chi Minh City",
        "Self-guided Saigon tours, plus Cu Chi Tunnels and Mekong Delta day trips, an eSIM, and an airport pickup.",
        "1566083", ["klook", "kkday", "saily", "welcomepickups"]),
    "articles/hoi-an-first-timers-guide.html": hub(
        "Tours &amp; tickets in Hoi An",
        "Self-guided Hoi An tours, a My Son day trip, an eSIM, and an airport transfer from Da Nang.",
        "1580240", ["klook", "kkday", "saily", "welcomepickups"]),

    # ---- Broad expansion (2026-07-11) ----
    "articles/kuala-lumpur-first-timers-guide.html": hub(
        "Tours &amp; tickets in Kuala Lumpur",
        "Self-guided KL tours, Batu Caves and Genting day trips, an eSIM, and an airport transfer.",
        "1735161", ["klook", "kkday", "saily", "welcomepickups"]),
    "articles/manila-first-timers-guide.html": hub(
        "Tours &amp; tickets in Manila",
        "Self-guided Manila tours, Corregidor and Tagaytay day trips, an eSIM, and an airport pickup.",
        "1701668", ["klook", "kkday", "saily", "welcomepickups"]),
    "articles/cebu-first-timers-guide.html": hub(
        "Tours &amp; tickets in Cebu",
        "Island-hopping, canyoneering and city tours in Cebu, plus an eSIM and an airport pickup.",
        "1717512", ["klook", "kkday", "saily", "welcomepickups"]),
    "articles/chiang-mai-first-timers-guide.html": hub(
        "Tours &amp; tickets in Chiang Mai",
        "Self-guided Chiang Mai tours, ethical elephant sanctuaries, a Doi Inthanon day trip, and an eSIM.",
        "1153671", ["klook", "kkday", "saily", "welcomepickups"]),
    "articles/phuket-first-timers-guide.html": hub(
        "Tours &amp; tickets in Phuket",
        "Phi Phi and Phang Nga boat trips, island tours, an eSIM, and an airport transfer in Phuket.",
        "1151254", ["klook", "kkday", "saily", "welcomepickups"]),
    "articles/hong-kong-first-timers-guide.html": hub(
        "Tours &amp; tickets in Hong Kong",
        "The Peak Tram, Ngong Ping 360 and Big Buddha, self-guided city walks, an eSIM, and an airport transfer.",
        "1819729", ["klook", "kkday", "saily", "welcomepickups"]),
    "articles/seoul-first-timers-guide.html": hub(
        "Tours &amp; tickets in Seoul",
        "Palace and Gangnam audio walks, a DMZ day trip, T-money-friendly attractions, an eSIM, and an airport pickup.",
        "1835848", ["klook", "kkday", "saily", "welcomepickups"]),
    "articles/osaka-first-timers-guide.html": hub(
        "Tours &amp; tickets in Osaka",
        "Self-guided Osaka walks, Universal Studios and Kaiyukan tickets, a Nara day trip, an eSIM, and an airport transfer.",
        "1853909", ["klook", "kkday", "saily", "welcomepickups"]),
    "articles/penang-first-timers-guide.html": hub(
        "Tours &amp; tickets in Penang",
        "George Town heritage walks, Penang Hill and Kek Lok Si, a street-food crawl, an eSIM, and an airport pickup.",
        "1735106", ["klook", "kkday", "saily", "welcomepickups"]),
    "articles/yogyakarta-first-timers-guide.html": hub(
        "Tours &amp; tickets in Yogyakarta",
        "Borobudur sunrise and Prambanan tours, a Merapi jeep trip, batik workshops, an eSIM, and an airport pickup.",
        "1621177", ["klook", "kkday", "saily", "welcomepickups"]),
    "articles/things-to-do-in-tokyo.html": hub(
        "Tours &amp; tickets in Tokyo",
        "teamLab and Skytree tickets, self-guided city walks, Kamakura and Mt Fuji day trips, an eSIM, and an airport transfer.",
        "1850147", ["klook", "kkday", "saily", "welcomepickups"]),
    "articles/things-to-do-in-kyoto.html": hub(
        "Tours &amp; tickets in Kyoto",
        "Fushimi Inari and Arashiyama tours, tea ceremonies, kimono rental, a Nara day trip, an eSIM, and an airport transfer.",
        "1857910", ["klook", "kkday", "saily", "welcomepickups"]),
    "articles/things-to-do-in-bangkok.html": hub(
        "Tours &amp; tickets in Bangkok",
        "Grand Palace and temple tours, canal longtail trips, floating-market and Ayutthaya day tours, an eSIM, and an airport transfer.",
        "1609350", ["klook", "kkday", "saily", "welcomepickups"]),
}


# Every practical article gets an affiliate CTA — registry-specific if defined,
# otherwise a sensible default. Trust/cultural essays are never monetised (constitution).
BLOCKLIST = {
    "untranslatable-words", "what-counts-as-rude", "jet-lag-what-actually-works",
    "about", "privacy", "methodology", "editors", "editorial-guidelines",
}
DEFAULT_CTA_BRANDS = ["aviasales", "saily", "welcomepickups"]


def block_for(slug: str) -> str | None:
    """CTA HTML for an article slug: its registry entry, else a default.
    Returns None for trust/cultural pages that must stay affiliate-free."""
    rel = f"articles/{slug}.html"
    if rel in REGISTRY:
        return REGISTRY[rel]
    if slug in BLOCKLIST:
        return None
    return cta("Planning your trip?", DEFAULT_CTA_BRANDS)


# Insert the CTA before the first anchor found — keep it INSIDE the article
# content (before the FAQ / back-link), never orphaned after </main>.
ANCHORS = ('<h2 id="faq"', '<p class="back-link"', '</main>', '<footer')


def inject(rel: str, block: str) -> str:
    wrapped = f"{BEGIN}\n{block}\n{END}"
    changed = []
    for base in ("site", "docs"):
        p = REPO / base / rel
        t = orig = p.read_text(encoding="utf-8")
        # 1) strip any existing managed block so it can be relocated
        if BEGIN in t and END in t:
            s = t.index(BEGIN); e = t.index(END) + len(END)
            if t[e:e + 1] == "\n":
                e += 1
            t = t[:s] + t[e:]
        # 2) insert before the best in-content anchor
        anchor = next((a for a in ANCHORS if a in t), None)
        if anchor is None:
            print(f"    !! no anchor in {base}/{rel} — skipped")
            continue
        i = t.index(anchor)
        t = t[:i] + wrapped + "\n" + t[i:]
        if t != orig:
            p.write_text(t, encoding="utf-8")
            changed.append(base)
    return ",".join(changed) or "no-change"


def main() -> None:
    for rel, block in REGISTRY.items():
        status = inject(rel, block)
        print(f"  {rel:52s} {status}")
    print(f"injected into {len(REGISTRY)} pages (site + docs)")


if __name__ == "__main__":
    main()
