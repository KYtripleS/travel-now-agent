#!/usr/bin/env python3
"""
inject_affiliates.py

One-shot, idempotent injection of Travelpayouts affiliate product cards
and Klook discovery widgets across 9 articles. Each insertion is wrapped
with HTML comment markers so re-running this script is a no-op.

Article → affiliate mapping:
  esim-activation-and-preparation.html  → Airalo + Saily cards
  travel-insurance-compared.html        → EKTA card (25% commission)
  charter-a-boat-for-a-day.html         → SEARADAR card
  countries/japan/index.html            → Klook + KKday cards
  cities/tokyo/index.html               → Klook + KKday cards + widget (city 28, cat 2)
  cities/tokyo/asakusa.html             → Klook + KKday cards + widget (city 28, cat 1)
  articles/south-korea-country-profile  → Klook card + widget (city 13, cat 2)
  countries/vietnam/index.html          → Klook card + widget (city 34, cat 2)
  countries/australia/index.html        → Klook card + widget (city 68, cat 2)

Usage:
  python inject_affiliates.py            # dry run
  python inject_affiliates.py --write    # apply
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent
SITE = REPO / "site"
DOCS = REPO / "docs"

MARK_BEGIN = "<!-- BEGIN affiliate-inject (managed by inject_affiliates.py) -->"
MARK_END = "<!-- END affiliate-inject -->"
WIDGET_BEGIN = "<!-- BEGIN klook-widget (managed by inject_affiliates.py) -->"
WIDGET_END = "<!-- END klook-widget -->"


# -------- Product card snippets --------

def card(brand: str, tagline: str, body: str, href: str, cta: str) -> str:
    return (
        '<article class="product-card">\n'
        f'<h4>{brand} — {tagline}</h4>\n'
        f'<p>{body}</p>\n'
        f'<a class="product-link" href="{href}" rel="nofollow sponsored noopener" target="_blank">{cta}</a>\n'
        '</article>'
    )


AIRALO_CARD = card(
    "Airalo",
    "eSIM in 200+ countries",
    "The most established travel eSIM marketplace. Country-specific or regional plans, instant QR delivery, top-up directly in the app. Strong support and a clear refund window if your phone turns out not to be eSIM-capable.",
    "https://airalo.tpx.lu/ctddHmQY",
    "Browse Airalo eSIM plans →",
)

SAILY_CARD = card(
    "Saily by NordVPN",
    "eSIM with privacy focus",
    "From the NordVPN team. Affordable plans with strong network coverage and built-in privacy features. Often undercuts other eSIM marketplaces on per-GB pricing, particularly in Europe and Asia.",
    "https://saily.tpx.lu/1RHGIfQA",
    "Browse Saily eSIM plans →",
)

EKTA_CARD = card(
    "EKTA",
    "transparent travel insurance quotes",
    "EKTA offers fast online quotes for short-term travel cover including medical, baggage, and trip-interruption layers. Useful as a reference quote alongside SafetyWing, World Nomads, and Genki — especially if you want a simpler single-trip policy rather than an ongoing subscription.",
    "https://ektatraveling.tpx.lu/nDrStdXW",
    "Get an EKTA quote →",
)

SEARADAR_CARD = card(
    "SEARADAR",
    "yacht charter across the Mediterranean",
    "Specialised yacht charter platform covering Greece, Croatia, Italy, Turkey, and the Balearics. Verified boats, transparent pricing, optional skipper or bareboat. Useful as a SamBoat alternative when you want curated yachts rather than peer-to-peer listings.",
    "https://searadar.tpx.lu/YiWnGz1v",
    "Browse SEARADAR yacht charters →",
)

KLOOK_CARD = card(
    "Klook",
    "tours, tickets, and transfers across Asia",
    "Strong coverage in Japan, Korea, Vietnam, Thailand, Hong Kong, Taiwan, and Singapore. Skip-the-line tickets, day tours, airport transfers, and pocket Wi-Fi. Often the cheapest reliable option for major attractions in Asian capitals.",
    "https://klook.tpx.lu/wgsZkatL",
    "Browse Klook tours & tickets →",
)

KKDAY_CARD = card(
    "KKday",
    "niche Japanese experiences",
    "Stronger than Klook for off-beat Japan-specific bookings: tea ceremonies, kimono rental, ninja workshops, small-group food tours. Smaller catalog overall, but often the only place these are bookable in English.",
    "https://kkday.tpx.lu/3364ws9s",
    "Browse KKday experiences →",
)


# -------- Widget snippet --------

def widget_block(city_id: int, category: int, place_name: str) -> str:
    """Klook tours-and-activities widget, wrapped in idempotency markers."""
    src = (
        f"https://tpemb.com/content?currency=USD&trs=543719&shmarker=743846"
        f"&locale=en&city_id={city_id}&category={category}&amount=3"
        f"&powered_by=true&campaign_id=137&promo_id=4497"
    )
    return (
        f'{WIDGET_BEGIN}\n'
        f'<section class="travel-experiences" style="margin: 36px 0;">\n'
        f'<h2>Experiences worth booking ahead in {place_name}</h2>\n'
        f'<p>Top-rated tours and activities — book skip-the-line where possible:</p>\n'
        f'<script async src="{src}" charset="utf-8"></script>\n'
        f'</section>\n'
        f'{WIDGET_END}'
    )


# -------- New affiliate section for files without an existing product-grid --------

def standalone_section(heading: str, intro: str, cards_html: list[str]) -> str:
    cards = "\n".join(cards_html)
    return (
        f'{MARK_BEGIN}\n'
        f'<section class="travel-affiliates" style="margin: 36px 0;">\n'
        f'<h2>{heading}</h2>\n'
        f'<p>{intro}</p>\n'
        f'<div class="product-grid article-products">\n'
        f'{cards}\n'
        f'</div>\n'
        f'<p style="font-size: 0.86rem; color: #647084; margin-top: 14px;">\n'
        f'  Disclosure: links in this section are affiliate links. Travel Now may earn '
        f'  a commission if you book through them, at no extra cost to you.\n'
        f'</p>\n'
        f'</section>\n'
        f'{MARK_END}'
    )


# -------- Insertion helpers --------

def insert_into_existing_grid(html: str, cards_html: list[str], grid_marker: str) -> tuple[str, bool]:
    """Insert cards inside an existing <div class="product-grid article-products"> block.
    Adds cards just BEFORE the closing </div> of that grid. Idempotent via markers."""
    if MARK_BEGIN in html:
        return html, False
    idx = html.find(grid_marker)
    if idx == -1:
        return html, False
    # find the closing </div> of this grid
    open_count = 1
    pos = idx + len(grid_marker)
    while open_count > 0 and pos < len(html):
        next_open = html.find("<div", pos)
        next_close = html.find("</div>", pos)
        if next_close == -1:
            return html, False
        if next_open != -1 and next_open < next_close:
            open_count += 1
            pos = next_open + 4
        else:
            open_count -= 1
            if open_count == 0:
                # insert before this </div>
                wrapped = f"{MARK_BEGIN}\n" + "\n".join(cards_html) + f"\n{MARK_END}\n"
                return html[:next_close] + wrapped + html[next_close:], True
            pos = next_close + 6
    return html, False


def insert_before(html: str, anchor: str, block: str) -> tuple[str, bool]:
    """Insert `block` immediately before `anchor` in html. Idempotent via marker."""
    # The block carries its own BEGIN marker; check that exact marker isn't already present.
    if MARK_BEGIN in block and MARK_BEGIN in html:
        return html, False
    if WIDGET_BEGIN in block and WIDGET_BEGIN in html:
        return html, False
    idx = html.find(anchor)
    if idx == -1:
        return html, False
    return html[:idx] + block + "\n" + html[idx:], True


# -------- Per-file plan --------

def process_file(rel_path: str, html: str) -> tuple[str, list[str]]:
    """Return (new_html, list_of_actions). Each file has bespoke handling."""
    actions: list[str] = []

    if rel_path == "articles/esim-activation-and-preparation.html":
        new, ok = insert_into_existing_grid(
            html, [AIRALO_CARD, SAILY_CARD],
            '<div class="product-grid article-products">'
        )
        if ok:
            actions.append("inserted Airalo + Saily into existing product-grid")
            html = new

    elif rel_path == "articles/travel-insurance-compared.html":
        section = standalone_section(
            "Get a quote",
            "Three providers compared above. For a fast online quote, EKTA delivers a transparent price in under a minute — useful as a fourth reference point.",
            [EKTA_CARD],
        )
        new, ok = insert_before(html, '<h2>Liked this guide?', section)
        if ok:
            actions.append("inserted EKTA card before newsletter CTA")
            html = new

    elif rel_path == "articles/charter-a-boat-for-a-day.html":
        # insert into existing product-grid in section 3 ("Where to find boats")
        new, ok = insert_into_existing_grid(
            html, [SEARADAR_CARD],
            '<div class="product-grid article-products">'
        )
        if ok:
            actions.append("inserted SEARADAR into existing product-grid")
            html = new

    elif rel_path == "countries/japan/index.html":
        new, ok = insert_into_existing_grid(
            html, [KLOOK_CARD, KKDAY_CARD],
            '<div class="product-grid article-products">'
        )
        if ok:
            actions.append("inserted Klook + KKday into Travel-prep grid")
            html = new

    elif rel_path == "cities/tokyo/index.html":
        # no existing grid → standalone section before "Where to start"
        section = standalone_section(
            "Tours, transfers, and tickets",
            "Tokyo rewards a bit of advance planning. A handful of bookings worth making before you fly:",
            [KLOOK_CARD, KKDAY_CARD],
        )
        new, ok = insert_before(html, '<h2>Where to start</h2>', section)
        if ok:
            actions.append("inserted Klook + KKday standalone section")
            html = new
        # widget — Tokyo, city 28, category 2
        widget = widget_block(28, 2, "Tokyo")
        new, ok = insert_before(html, '<section class="newsletter-cta"', widget)
        if ok:
            actions.append("inserted Tokyo widget (city 28, cat 2)")
            html = new

    elif rel_path == "cities/tokyo/asakusa.html":
        section = standalone_section(
            "Tours and tickets in Asakusa",
            "Asakusa is dense with bookable experiences. A few worth lining up before you visit:",
            [KLOOK_CARD, KKDAY_CARD],
        )
        new, ok = insert_before(html, '<h2>Related guides</h2>', section)
        if ok:
            actions.append("inserted Klook + KKday standalone section")
            html = new
        widget = widget_block(28, 1, "Asakusa")
        new, ok = insert_before(html, '<h2>Related guides</h2>', widget)
        if ok:
            actions.append("inserted Asakusa widget (city 28, cat 1)")
            html = new

    elif rel_path == "articles/south-korea-country-profile.html":
        section = standalone_section(
            "Tours, transfers, and tickets in Korea",
            "A few bookings worth making before you fly to Seoul:",
            [KLOOK_CARD],
        )
        new, ok = insert_before(html, '<h2>Liked this guide?', section)
        if ok:
            actions.append("inserted Klook standalone section")
            html = new
        widget = widget_block(13, 2, "Seoul")
        new, ok = insert_before(html, '<h2>Liked this guide?', widget)
        if ok:
            actions.append("inserted Seoul widget (city 13, cat 2)")
            html = new

    elif rel_path == "countries/vietnam/index.html":
        new, ok = insert_into_existing_grid(
            html, [KLOOK_CARD],
            '<div class="product-grid article-products">'
        )
        if ok:
            actions.append("inserted Klook into Travel-prep grid")
            html = new
        widget = widget_block(34, 2, "Hanoi & Ho Chi Minh City")
        new, ok = insert_before(html, '<h2>Where to go next on Travel Now</h2>', widget)
        if ok:
            actions.append("inserted Vietnam widget (city 34, cat 2)")
            html = new

    elif rel_path == "countries/australia/index.html":
        new, ok = insert_into_existing_grid(
            html, [KLOOK_CARD],
            '<div class="product-grid article-products">'
        )
        if ok:
            actions.append("inserted Klook into Travel-prep grid")
            html = new
        widget = widget_block(68, 2, "Sydney & Melbourne")
        new, ok = insert_before(html, '<h2>Where to go next on Travel Now</h2>', widget)
        if ok:
            actions.append("inserted Australia widget (city 68, cat 2)")
            html = new

    return html, actions


TARGETS = [
    "articles/esim-activation-and-preparation.html",
    "articles/travel-insurance-compared.html",
    "articles/charter-a-boat-for-a-day.html",
    "countries/japan/index.html",
    "cities/tokyo/index.html",
    "cities/tokyo/asakusa.html",
    "articles/south-korea-country-profile.html",
    "countries/vietnam/index.html",
    "countries/australia/index.html",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="apply changes (otherwise dry run)")
    args = parser.parse_args()

    total_changed = 0
    for rel in TARGETS:
        src = SITE / rel
        dst = DOCS / rel
        if not src.exists():
            print(f"  ⚠ missing: {rel}")
            continue
        html = src.read_text(encoding="utf-8")
        new_html, actions = process_file(rel, html)
        if not actions:
            print(f"  ⏭  {rel}: no-op (already injected or anchor not found)")
            continue
        total_changed += 1
        print(f"  ✓  {rel}")
        for a in actions:
            print(f"      · {a}")
        if args.write:
            src.write_text(new_html, encoding="utf-8")
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(new_html, encoding="utf-8")

    print()
    print(f"  changed: {total_changed} / {len(TARGETS)}")
    if not args.write and total_changed:
        print("  (dry run — pass --write to apply and mirror to docs/)")


if __name__ == "__main__":
    main()
