#!/usr/bin/env python3
"""
tp_widgets.py — Travelpayouts embeddable widgets (tpemb.com/content).

Single source of truth for our Travelpayouts marker + the campaign→brand decode,
plus generators that emit a brand-wrapped widget box so the loud third-party UI
sits calmly inside Gently Yonder instead of reading like an ad.

Marker (public — safe in page source, NOT a secret like an API key):
    trs = 547982   shmarker = 743846

Campaign → brand decode (verified 2026-07-09 by fetching the tpemb loaders):
    campaign_id=100  Aviasales      flights (metasearch)         reward ~40% (Hot)
    campaign_id=89   Hotellook      hotels                       reward ~varies
    campaign_id=111  Kiwi.com       flights (virtual interlining) reward ~3%   <- redundant w/ Aviasales; usually skip
    campaign_id=627  Welcome Pickups airport transfers           reward ~8-9%
    campaign_id=150  WeGoTrip       self-guided audio tours       reward up to ~41.5%

Placement rules (same as every affiliate on this site — see CLAUDE.md / constitution):
  * practical / planning sections ONLY. Never in historical, cultural, or reflective
    content, About, or trust pages.
  * one flight partner per context — default Aviasales; do not stack Kiwi on top.
  * every page carrying a widget needs the FTC disclosure line in its footer.

Destination reference (IATA for flights, GeoNames city_id for WeGoTrip tours):
    Tokyo   TYO  1850147     Osaka  OSA  1857910
    Bangkok BKK  1609350     Sydney SYD  2147714
    (Hanoi HAN, Ho Chi Minh SGN, Seoul SEL, Kyoto — need city_id lookups before use.)
"""

from __future__ import annotations

TRS = "547982"
SHMARKER = "743846"

# Brand accent that blends with the Gently Yonder palette (navy, url-encoded #172033).
NAVY = "%23172033"

_BASE = f"https://tpemb.com/content?trs={TRS}&shmarker={SHMARKER}"


def _script(qs: str) -> str:
    return f'<script async src="{_BASE}&{qs}" charset="utf-8"></script>'


# --- individual widgets -----------------------------------------------------

def aviasales_flights_to(iata: str) -> str:
    """Aviasales 'best fares to <city>' cards (campaign 100, promo 4044)."""
    return _script(f"currency=usd&destination={iata}&target_host=www.aviasales.com%2Fsearch"
                   f"&locale=en&limit=6&powered_by=true&primary={NAVY}"
                   f"&promo_id=4044&campaign_id=100")


def aviasales_search() -> str:
    """Aviasales flight+hotel search form (campaign 100, promo 7879)."""
    return _script("currency=usd&show_hotels=true&powered_by=true&locale=en"
                   f"&searchUrl=www.aviasales.com%2Fsearch&primary_override={NAVY}"
                   f"&color_button={NAVY}&color_icons={NAVY}&dark=%23262626&light=%23FFFFFF"
                   "&secondary=%23FFFFFF&special=%23C4C4C4&border_radius=6&plain=false"
                   "&promo_id=7879&campaign_id=100")


def wegotrip_tours(city_id: str) -> str:
    """WeGoTrip self-guided tours for a city (campaign 150, promo 4489).

    tours=2 (not 3): the widget lays cards out in a 2-column grid, so an odd
    count leaves an orphan card in a second row that the iframe's fixed height
    clips. Two cards fill exactly one row — no clipping.
    """
    return _script(f"locale=en&city_id={city_id}&tours=2&powered_by=true"
                   "&campaign_id=150&promo_id=4489")


def welcome_pickups() -> str:
    """Welcome Pickups airport-transfer search (campaign 627, promo 8951).
    Auto-detects airport by the reader; no destination param needed."""
    return _script("locale=en&show_header=true&powered_by=true"
                   "&campaign_id=627&promo_id=8951")


# --- brand-safe wrapper -----------------------------------------------------

def box(heading: str, blurb: str, *widgets: str, note: str = "") -> str:
    """Wrap one or more widget scripts in a calm .gy-widget card with an FTC note."""
    note = note or ("Booking tools are affiliate-supported — Gently Yonder may earn a "
                    "commission at no extra cost to you.")
    inner = "\n".join(widgets)
    return (f'<aside class="gy-widget">\n'
            f'  <h4 class="gy-widget-h">{heading}</h4>\n'
            f'  <p class="gy-widget-blurb">{blurb}</p>\n'
            f'  <div class="gy-widget-frame">\n{inner}\n  </div>\n'
            f'  <p class="gy-widget-note">{note}</p>\n'
            f'</aside>')


# Convenience: the standard "flights + tours" block for a destination.
def destination_block(city: str, iata: str, city_id: str) -> str:
    return box(
        f"Getting to {city} &amp; things to do",
        f"Compare current fares to {city} and browse self-guided tours you can start "
        f"the moment you land.",
        aviasales_flights_to(iata),
        wegotrip_tours(city_id),
    )


if __name__ == "__main__":
    # Emit the Tokyo reference block (used for the Japan profile).
    print(destination_block("Tokyo", "TYO", "1850147"))
