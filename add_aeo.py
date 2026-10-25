#!/usr/bin/env python3
"""Answer-engine optimisation (AEO) layer for Gently Yonder articles.

About a third of real readers now arrive from AI assistants (ChatGPT,
Perplexity), and the assistants read the page rather than click it — Search
Console shows their queries ("my main motivations: … is viator cheaper than
klook") at position ~9 with no clicks at all. This module shapes articles for
that reader:

1. Dates. A machine-readable "Last updated <time>" line on every article, and
   datePublished restored to the first-publish date from git — publish_article.py
   used to reset it to the day of every republish, so a guide first published in
   June claimed September.
2. A branded verdict at the top of decision articles:
   "Gently Yonder's verdict: …". When an assistant quotes the sentence, the
   name travels with it. Each verdict restates what the article itself already
   concludes; it adds no new claims.
3. Partner links where the decision is read. AI-referred readers land already
   decided, often mid-page, so a link only in the closing paragraph is a link
   they never reach. Linked: partner names in comparison tables, paragraphs that
   open with a bold partner name, and a one-line link under a heading that names
   a single partner ("1. Airalo — …").
4. "In this guide": a contents list under the verdict on articles with five or
   more sections, with a stable id on every section heading. Readers who land
   mid-decision jump straight to prices or the FAQ, and the anchors give search
   and answer engines addressable sections to cite.
5. A social card from the article's own photo (add_social_meta.py).
6. Where-to-stay guides (stay22.PAGES): a "Check rates" link after every hotel
   Booking.com lists, one line saying how those links work, and a hotel map under
   the "at a glance" table.

Only brands we have an affiliate relationship with are ever linked; the hotel
sites and GetYourGuide come through Stay22 (stay22.py). Viator, Trip.com,
HotelsCombined, SafetyWing and the rest stay plain text.

Everything this module adds carries data-aeo, so a re-run strips and rebuilds it
(idempotent). publish_article.py calls apply() so new articles are born with it.

Usage:
    python add_aeo.py            # dry run: report what would change
    python add_aeo.py --write    # apply to site/ and docs/
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import unicodedata
from datetime import date
from functools import lru_cache
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

import add_social_meta
import stay22

REPO = Path(__file__).resolve().parent
SITE = REPO / "site"
DOCS = REPO / "docs"

REL = "nofollow sponsored noopener"
BRAND_LABEL = "Gently Yonder’s verdict:"

# --- partners -----------------------------------------------------------------
# display name -> key. Longest names first so "Go City" wins over a partial match.
BRANDS = {
    "Welcome Pickups": "welcomepickups",
    "Radical Storage": "radicalstorage",
    "GetYourGuide": "getyourguide",
    "Booking.com": "booking",
    "Hotels.com": "hotelscom",
    "Go City": "gocity",
    "WeGoTrip": "wegotrip",
    "Aviasales": "aviasales",
    "SamBoat": "samboat",
    "Airalo": "airalo",
    "Tiqets": "tiqets",
    "VELTRA": "veltra",
    "KKday": "kkday",
    "Klook": "klook",
    "Saily": "saily",
    "EKTA": "ekta",
    "Holafly": "holafly",
    "Expedia": "expedia",
    "Agoda": "agoda",
    "Vrbo": "vrbo",
}
# Stay22 partners. Only a bare link is ever reused from a page: a link to one hotel
# must not become the link for the whole brand.
_STAY22_KEYS = ("getyourguide", "booking", "hotelscom", "expedia", "agoda", "vrbo")
# how to recognise a partner's link already on the page (reused, so each page
# keeps the tracking link it was built with) …
HREF_MATCH = {
    "klook": r"klook\.tpx\.lu/",
    "kkday": r"kkday\.tpx\.lu/",
    "tiqets": r"tiqets\.tpx\.lu/",
    "wegotrip": r"wegotrip\.tpx\.lu/",
    "gocity": r"gocity\.tpx\.lu/",
    "saily": r"saily\.tpx\.lu/",
    "airalo": r"airalo\.tpx\.lu/",
    "ekta": r"ektatraveling\.tpx\.lu/",
    "welcomepickups": r"//tpx\.lu/YtuAbaB1",
    "aviasales": r"aviasales\.tpx\.lu/",
    "radicalstorage": r"radicalstorage\.tpx\.lu/",
    "veltra": r"awinmid=89081",
    "samboat": r"awinmid=(?:32677|32681)",
    "holafly": r"holafly\.sjv\.io/",
    **{k: rf"stay22\.com/allez/{k}\?aid={stay22.AID}$" for k in _STAY22_KEYS},
}
# … and the default when the page has none yet.
DEFAULT_HREF = {
    "klook": "https://klook.tpx.lu/TgR5Suzs",
    "kkday": "https://kkday.tpx.lu/99SKEU6d",
    "tiqets": "https://tiqets.tpx.lu/7rZHQkfx",
    "wegotrip": "https://wegotrip.tpx.lu/DCr0TOXx",
    "gocity": "https://gocity.tpx.lu/z5uRRfo8",
    "saily": "https://saily.tpx.lu/hk5XU6Sm",
    "airalo": "https://airalo.tpx.lu/ctddHmQY",
    "ekta": "https://ektatraveling.tpx.lu/LXmPxVUQ",
    "welcomepickups": "https://tpx.lu/YtuAbaB1",
    "aviasales": "https://aviasales.tpx.lu/dESAKheX",
    "radicalstorage": "https://radicalstorage.tpx.lu/WpAnAq1c",
    "veltra": "https://www.awin1.com/cread.php?awinmid=89081&awinaffid=2926361&ued=https%3A%2F%2Fwww.veltra.com%2Fen%2F",
    "samboat": "https://www.awin1.com/cread.php?awinmid=32677&awinaffid=2926361&ued=https%3A%2F%2Fwww.samboat.co.uk%2F",
    # Impact; the link applies our coupon YONDER by itself (approved 2026-09)
    "holafly": "https://holafly.sjv.io/c/7394095/3920147/24764",
    **{k: stay22.allez(k) for k in _STAY22_KEYS},
}
# A page's own destination where the partner can search by place: a reader comparing
# Sydney cruises should land on GetYourGuide's Sydney results, not its home page.
PAGE_HREF = {
    "where-to-book-sydney-harbour-cruise": {"getyourguide": stay22.allez("getyourguide", address="Sydney, Australia")},
    "where-to-book-jeju-bus-tour": {"getyourguide": stay22.allez("getyourguide", address="Jeju, South Korea")},
    "where-to-book-halong-bay-cruise": {"getyourguide": stay22.allez("getyourguide", address="Ha Long Bay, Vietnam")},
    "where-to-book-tokyo-food-tour": {"getyourguide": stay22.allez("getyourguide", address="Tokyo, Japan")},
}
SECTION_LABEL = {
    "klook": "Check current prices on Klook",
    "kkday": "Check current prices on KKday",
    "tiqets": "Check tickets on Tiqets",
    "wegotrip": "Browse WeGoTrip audio tours",
    "gocity": "Compare passes on Go City",
    "saily": "See Saily’s current plans",
    "airalo": "See Airalo’s current plans",
    "ekta": "Get a quote from EKTA",
    "welcomepickups": "Arrange a pickup with Welcome Pickups",
    "aviasales": "Compare fares on Aviasales",
    "radicalstorage": "Book luggage storage with Radical Storage",
    "veltra": "Browse VELTRA tours",
    "samboat": "Browse boats on SamBoat",
    "holafly": "See Holafly’s unlimited plans",
    "getyourguide": "Browse tours on GetYourGuide",
    "booking": "Search hotels on Booking.com",
    "hotelscom": "Search hotels on Hotels.com",
    "expedia": "Search hotels on Expedia",
    "agoda": "Search hotels on Agoda",
    "vrbo": "Search holiday rentals on Vrbo",
}
# A reader-facing note after the section link, said plainly. Holafly asks for the
# code to sit beside the link (it still applies if the reader buys later).
SECTION_NOTE = {
    "holafly": ("Code ", "YONDER", " takes 5% off, and we earn a commission if you use it."),
}

# --- verdicts -----------------------------------------------------------------
# slug -> text, cta, and optionally which legacy summary box it replaces.
# cta: (brand key, label) | ("amazon", asin, label) | ("href", label, url) | None.
# None where the pick is not a partner of ours — a link to a different brand under
# a verdict that names someone else would be a bait-and-switch.
# The verdict links the CTA where its text first names the partner, or at
# `link_text` when the words that should carry it are not a partner's name
# ("the CBD"); `also` links further partners at their first mention.
LEGACY_BOX = "aside.verdict"


# Under every hotel verdict: why to act now, in words that are true on any date.
# Prices can fall as well as rise, so it never says they will go up.
PRICE_NOTE = ("Hotel prices change daily with demand, and on busy dates they tend to climb as rooms fill. "
              "A rate with free cancellation, where the hotel offers one, locks in today’s price while you "
              "keep comparing.")


def _stay_cta(slug: str, label: str) -> tuple:
    """A where-to-stay verdict's call to action: hotels around the area it
    recommends, on whichever booking site Stay22 picks, since the text names none."""
    p = stay22.PAGES[slug]
    return ("href", label, stay22.area_rates(p["lat"], p["lng"]))


V = {
    # booking platforms --------------------------------------------------------
    "klook-vs-viator-vs-getyourguide": dict(
        text="Viator has by far the most activities — more than 400,000 worldwide — and GetYourGuide "
             "the most consistent 24-hour free cancellation; in Asia, Klook is usually the cheaper and "
             "deeper of the three, and it also sells the rail passes, transfers and eSIMs the others don’t. "
             "No platform is always cheapest: the same tour is priced by each operator’s deal with each "
             "site, so compare the exact listing.",
        cta=("klook", "Check the same tour on Klook")),
    "klook-vs-kkday": dict(
        text="Use Klook as your broad default — especially for transport, rail passes, transfers and "
             "multi-category trips — and check KKday whenever you’re in Taiwan or Japan or want a "
             "smaller local operator. Prices vary listing by listing, so compare the same activity on both.",
        cta=("klook", "Check current prices on Klook")),
    "hotel-booking-sites-comparison": dict(
        text="There is no single best hotel site: start with HotelsCombined or Booking.com for the broadest "
             "coverage, check Agoda or Trip.com for Asia, and verify the hotel’s own site if you have "
             "loyalty status.",
        cta=("booking", "Search hotels on Booking.com"), also=("agoda",)),
    "where-to-book-sydney-harbour-cruise": dict(
        text="Book whale-watching and sunset cruises on Klook, usually the cheapest for Sydney; dinner "
             "cruises on GetYourGuide, which lays out menu tiers clearly and applies free cancellation most "
             "consistently; and anything unusual — private charters, tall ships — on Viator.",
        cta=("klook", "Check Sydney harbour cruises on Klook")),
    "where-to-book-jeju-bus-tour": dict(
        text="Book on Klook for a small-group, English-only Jeju tour with hotel pickup and no shopping "
             "stops; on KKday for the widest choice of routes, including Udo island. Check for shopping "
             "stops before you compare prices.",
        cta=("klook", "Check Jeju day tours on Klook")),
    "where-to-book-taipei-day-tour": dict(
        text="KKday for anything distinctly Taiwanese — Taroko Gorge, Sun Moon Lake, Alishan, night-market "
             "tours; Klook for the Jiufen–Shifen–Yehliu north-coast loop, where its listings commonly "
             "include Yehliu entry. The price gap is usually under 5%, so compare what’s included.",
        cta=("kkday", "Browse Taiwan day tours on KKday")),
    "where-to-book-bangkok-dinner-cruise": dict(
        text="Book the ~17:00 sunset departure first — often the same boat and buffet for 30–50% less "
             "— then KKday for the cheapest entry points (from about ฿880) or Klook for the headline "
             "boats and clearer pier details.",
        cta=("kkday", "Check Chao Phraya cruises on KKday")),
    "where-to-book-seoul-dmz-tour": dict(
        text="The JSA has been closed to civilian tours since July 2023, so book a DMZ tour, not a “DMZ & "
             "JSA” promise. KKday has the sharpest verified price, Klook lists tours with a North Korean "
             "defector Q&A, and on any platform check for a shopping stop before you compare prices.",
        cta=("kkday", "Check DMZ tours on KKday")),
    "where-to-book-halong-bay-cruise": dict(
        text="Compare the same boat on a platform and on the operator’s own site — direct is often "
             "cheaper. Pay the platform premium when you want card protection and clear cancellation terms: "
             "Klook for day trips from Hanoi, Viator for the widest range of overnights.",
        cta=("klook", "Check Halong Bay cruises on Klook")),
    # where to stay: hotel links through Stay22 (stay22.py) --------------------
    "where-to-stay-in-tokyo": dict(
        text="Choose the station first, then the hotel: for a first trip, the south or west side of Shinjuku, "
             "or Shibuya; for the Shinkansen or quiet evenings, the Marunouchi side of Tokyo Station; for "
             "old-Tokyo character and better value, Asakusa or Ueno. Then book within five minutes of the "
             "exit you will use.",
        link_text="the south or west side of Shinjuku",
        cta=_stay_cta("where-to-stay-in-tokyo", "See hotels around Shinjuku Station")),
    "where-to-stay-in-sydney": dict(
        text="For a first trip, stay in the city centre by Hyde Park; our pick there is the Sheraton Grand "
             "Sydney Hyde Park, where one of us stayed in September 2026. Choose Circular Quay and The Rocks "
             "for the harbour, Surry Hills for food, and Bondi or Manly for the beach.",
        link_text="Sheraton Grand Sydney Hyde Park",
        cta=("href", "See the Sheraton Grand’s rates on Booking.com",
             stay22.hotel_rates(stay22.HOTELS["Sheraton Grand Sydney Hyde Park"]))),
    "where-to-stay-in-melbourne": dict(
        text="Stay in the CBD, inside the Free Tram Zone, for a first trip; the SkyBus from the airport, "
             "bookable on Klook, stops at Southern Cross on its edge. Choose Southbank for the river, Fitzroy "
             "for bars and vintage shops, St Kilda for the bay and South Yarra for Chapel Street.",
        link_text="the CBD", also=("klook",),
        cta=_stay_cta("where-to-stay-in-melbourne", "See hotels in the Melbourne CBD")),
    "where-to-stay-in-kyoto": dict(
        text="Stay downtown near a subway station for the best all-round base, or by Kyoto Station if you "
             "are arriving by Shinkansen or from Kansai Airport. Choose Gion and Higashiyama for the old city "
             "at dawn and dusk, and budget for the accommodation tax that rose on 1 March 2026.",
        link_text="downtown near a subway station",
        cta=_stay_cta("where-to-stay-in-kyoto", "See hotels in downtown Kyoto")),
    "where-to-stay-in-osaka": dict(
        text="Stay in Namba or Shinsaibashi for food and nightlife, or around Umeda and Osaka Station for "
             "trains to Kyoto, Kobe and Kansai Airport (the Haruka stops there, and Klook sells tickets). "
             "Tennoji and Shinsekai are the value pick, and the bay only makes sense if Universal Studios "
             "Japan is the point of the trip.",
        link_text="Namba or Shinsaibashi", also=("klook",),
        cta=_stay_cta("where-to-stay-in-osaka", "See hotels around Namba and Shinsaibashi")),
    "where-to-stay-in-japan": dict(
        text="For a first trip of seven to ten days, sleep in two places: Shinjuku or Shibuya in Tokyo, then "
             "Kyoto or Osaka, moving once by Shinkansen. Kyoto suits temples at dawn and dusk; Osaka suits food and "
             "a smaller lodging tax. Give each base at least two nights, and add a third only with ten days or more.",
        link_text="Shinjuku or Shibuya",
        cta=_stay_cta("where-to-stay-in-tokyo", "See hotels around Shinjuku Station")),
    "where-to-stay-in-hakone": dict(
        text="For one night on a first trip, stay in Gora, where the mountain railway meets the cable car, so "
             "the whole loop to Owakudani and Lake Ashi starts at your door; choose Hakone-Yumoto instead if you "
             "want to step off the Romancecar into your hotel. Miyanoshita has the Fujiya Hotel and ryokan over "
             "the gorge, Lake Ashi the water and, on clear days, Mount Fuji, and Sengokuhara the quiet.",
        link_text="stay in Gora",
        cta=_stay_cta("where-to-stay-in-hakone", "See ryokan and hotels around Gora")),
    "where-to-stay-in-seoul": dict(
        text="For a first trip, stay in Myeongdong or around City Hall: central, with the shopping streets and "
             "several subway lines on foot. Choose Jongno and Insadong for the palaces and Bukchon's hanok lanes, "
             "Hongdae for nightlife and the airport train, Seoul Station for the AREX and the KTX, and Gangnam only "
             "if your plans are south of the river.",
        link_text="Myeongdong or around City Hall",
        cta=_stay_cta("where-to-stay-in-seoul", "See hotels around Myeongdong")),
    "where-to-stay-in-bangkok": dict(
        text="For a first trip, stay on Sukhumvit between Nana and Phrom Phong, a few minutes' walk from a "
             "Skytrain station: the trains reach Siam and the river, the MRT meets them at Asok, and there is a "
             "wide choice of hotels and food. Choose Siam for shopping at the centre of the network, the Riverside "
             "for the grand hotels and the boats to the temples, Silom and Sathorn for Lumphini Park, and the Old "
             "Town for the Grand Palace on foot.",
        link_text="Sukhumvit between Nana and Phrom Phong",
        cta=_stay_cta("where-to-stay-in-bangkok", "See hotels around Asok")),
    "where-to-stay-in-hong-kong": dict(
        text="For a first trip, stay in Tsim Sha Tsui, near the Star Ferry: the harbour is at the end of the "
             "street, the MTR runs under Nathan Road, and the ferry crosses to Central. Choose Central and "
             "Admiralty for the Airport Express and the Peak Tram, Wan Chai and Causeway Bay for shopping and "
             "the trams, Sheung Wan for old streets and smaller hotels, and Jordan or Mong Kok for markets and "
             "lower prices.",
        link_text="Tsim Sha Tsui, near the Star Ferry",
        cta=_stay_cta("where-to-stay-in-hong-kong", "See hotels around Tsim Sha Tsui")),
    "where-to-stay-in-kyoto-cherry-blossom": dict(
        text="For cherry blossom, stay in Okazaki, near Nanzen-ji: the Philosopher's Path and the Keage Incline "
             "are on foot, and the subway takes you downtown in minutes. Choose Gion and Higashiyama for "
             "Maruyama Park at dawn, downtown for the Kamo River, Kyoto Station for the trains, and Arashiyama "
             "for the hills. Book a refundable rate now.",
        link_text="Okazaki, near Nanzen-ji",
        cta=_stay_cta("where-to-stay-in-kyoto-cherry-blossom", "See hotels around Okazaki")),
    "where-to-stay-in-singapore": dict(
        text="For a first trip, stay around Marina Bay and the Civic District: Gardens by the Bay, the museums and "
             "the Padang are on foot, and four MRT lines meet at City Hall and Bayfront. Choose the river for "
             "evenings by the water, Orchard Road for shopping, Chinatown for hawker food, and Sentosa for "
             "beaches and theme parks with children.",
        link_text="Marina Bay and the Civic District",
        cta=_stay_cta("where-to-stay-in-singapore", "See hotels around Marina Bay")),
    "where-to-stay-in-taipei": dict(
        text="For a first trip, stay around Taipei Main Station or Zhongshan, one stop north: the Airport MRT, the "
             "high-speed rail and the Red and Blue lines meet at Main Station, and Zhongshan has the department "
             "stores and cafés. Choose Ximending for food and value, Xinyi for Taipei 101, Da'an for quieter "
             "streets, and Beitou for a night in a hot-spring room.",
        link_text="Taipei Main Station or Zhongshan",
        cta=_stay_cta("where-to-stay-in-taipei", "See hotels around Taipei Main Station")),
    "where-to-stay-in-kuala-lumpur": dict(
        text="For a first trip, stay in KLCC: the Petronas Twin Towers, KLCC Park and the Suria KLCC mall are at "
             "your door, and a covered walkway runs to Bukit Bintang. Choose Bukit Bintang for food and shopping, "
             "the old city and Chinatown for history, and KL Sentral for the 28-minute train to the airport.",
        link_text="KLCC",
        cta=_stay_cta("where-to-stay-in-kuala-lumpur", "See hotels around KLCC")),
    "where-to-stay-in-tokyo-cherry-blossom": dict(
        text="For cherry blossom, stay in Asakusa or Ueno: Sumida Park's riverside cherries and Senso-ji are on "
             "foot from Asakusa, Ueno Park's 800 trees are three stops away on the Ginza line, and the Skyliner "
             "runs from Ueno to Narita. Choose Marunouchi for the Chidorigafuchi moat, Shibuya for the Meguro "
             "River and Shinjuku for Shinjuku Gyoen. Book a refundable rate now.",
        link_text="Asakusa or Ueno",
        cta=_stay_cta("where-to-stay-in-tokyo-cherry-blossom", "See hotels around Asakusa")),
    "where-to-stay-in-sydney-new-years-eve": dict(
        text="For the fireworks from your room, stay at Circular Quay or in The Rocks: harbour rooms at the "
             "Shangri-La, Four Seasons and Park Hyatt face the Bridge or the Opera House. For less, stay in the "
             "city and walk to the Botanic Garden's free lawns, or at Darling Harbour, which has its own "
             "fireworks at 9pm and midnight. Check the minimum stay first.",
        link_text="Circular Quay or in The Rocks",
        cta=_stay_cta("where-to-stay-in-sydney-new-years-eve", "See hotels around Circular Quay")),
    "where-to-stay-in-sapporo-snow-festival": dict(
        text="For the Snow Festival, stay at Odori: the sculptures run along Odori Park from West 1 to West 11, "
             "all three subway lines meet at Odori Station, and a walkway under the street leads to Sapporo "
             "Station. Choose Sapporo Station for the airport train, Susukino for the ice sculptures and late "
             "nights, and Nakajima Park for quiet. The dates are fixed: book now.",
        link_text="Odori",
        cta=_stay_cta("where-to-stay-in-sapporo-snow-festival", "See hotels around Odori Park")),
    "where-to-stay-in-niseko": dict(
        text="For a first ski trip, stay in Grand Hirafu, near the King and Ace gondolas: the village has the "
             "restaurants and bars, and a hotel close to the lifts saves waiting for winter taxis. Choose HANAZONO "
             "for ski-in, ski-out away from the crowds, Niseko Village for hot springs at the gondola, Annupuri "
             "for quiet and Kutchan town for price. Both towns now charge 3% tax.",
        link_text="Grand Hirafu",
        cta=_stay_cta("where-to-stay-in-niseko", "See hotels around Grand Hirafu")),
    "where-to-stay-in-fukuoka": dict(
        text="For a first trip, stay near Hakata Station: the subway reaches the airport in 5 minutes for ¥260, "
             "and the shinkansen and the bus terminal are at the door. Choose Nakasu for the yatai, Tenjin for "
             "shopping and Momochi for the sea. Staying by 15 December? Check the Kyushu discount first; it is "
             "not on Booking.com.",
        link_text="Hakata Station",
        cta=_stay_cta("where-to-stay-in-fukuoka", "See hotels around Hakata Station")),
    "where-to-stay-in-kyoto-autumn-leaves": dict(
        text="For the autumn leaves, stay in Okazaki, near Nanzen-ji: Eikan-do and the Philosopher's Path are on "
             "foot, and Eikan-do's light-up runs from 20 November to 6 December. Choose Higashiyama for Kodai-ji's "
             "night opening, Kyoto Station for Tofuku-ji, one stop away, and Arashiyama for the river. Aim for the "
             "last ten days of November, on a refundable rate.",
        link_text="Okazaki, near Nanzen-ji",
        cta=_stay_cta("where-to-stay-in-kyoto-autumn-leaves", "See hotels around Okazaki")),
    "where-to-stay-in-busan": dict(
        text="For a first trip, stay in Haeundae: the beach is at the door, the airport limousine runs along it, "
             "and subway line 2 runs west to Gwangalli and Seomyeon. Choose Gwangalli for Gwangan Bridge, the "
             "Saturday drone show and the fireworks on 7 November 2026, Seomyeon for the subway hub, and Busan "
             "Station for the KTX.",
        link_text="Haeundae",
        cta=_stay_cta("where-to-stay-in-busan", "See hotels around Haeundae")),
    "where-to-stay-in-tokyo-autumn-leaves": dict(
        text="For the autumn leaves, stay in Shinjuku: Shinjuku Gyoen is ten minutes from the South Exit, and the "
             "Jingu Gaien ginkgo avenue is a short ride. Choose Shibuya for the ginkgo avenue, Ueno for Rikugien's "
             "evening opening from 25 November, and Marunouchi for the ginkgo outside Tokyo Station. Aim for late "
             "November, on a refundable rate.",
        link_text="Shinjuku",
        cta=_stay_cta("where-to-stay-in-tokyo-autumn-leaves", "See hotels around Shinjuku Station")),
    "where-to-stay-for-universal-studios-japan": dict(
        text="If the park is the point, stay at Universal City: seven official hotels sit a few minutes' walk "
             "from the gates, and most sell countdown Party Passes to their guests. If you are seeing Osaka too, "
             "stay in Umeda, 11 minutes by JR, or at the RIHGA Royal or OMO7 Osaka, which run a free bus to the "
             "park.",
        link_text="stay at Universal City",
        cta=_stay_cta("where-to-stay-for-universal-studios-japan", "See hotels at Universal City")),
    "where-to-stay-in-hakuba": dict(
        text="For a first ski trip, stay in Happo: the hotels and lodges of Wadano are a short walk from the "
             "Happo-one gondola and the village. Choose Echoland for restaurants, Goryu for beginner slopes and "
             "night skiing from 21 November, and Norikura or Cortina for ski-in, ski-out. Hakuba Village now taxes "
             "stays, up to ¥1,900 a person a night.",
        link_text="Happo",
        cta=_stay_cta("where-to-stay-in-hakuba", "See hotels around Happo")),
    "where-to-stay-in-paris": dict(
        text="For a first trip, stay in Le Marais: Place des Vosges is there, Notre-Dame is a bridge away, and "
             "metro line 1 runs to the Louvre. Choose Saint-Germain for the Left Bank, the Latin Quarter for a "
             "little less, and the Eiffel Tower area for a room facing the tower. The 2026 hotel tax is €8.45 a "
             "person a night at a four-star.",
        link_text="Le Marais",
        cta=_stay_cta("where-to-stay-in-paris", "See hotels around Le Marais")),
    "where-to-stay-in-new-york": dict(
        text="For a first trip, stay in Midtown near Times Square: Broadway's theatres are at the door and many "
             "subway lines meet at Times Sq–42 St. Choose SoHo or the Village for walkable streets, the Upper West "
             "Side for Central Park, and Brooklyn for the skyline view. Every room adds 14.75% in tax plus $3.50 "
             "a night.",
        link_text="Midtown near Times Square",
        cta=_stay_cta("where-to-stay-in-new-york", "See hotels around Times Square")),
    "where-to-stay-in-rovaniemi-christmas": dict(
        text="For a first Christmas trip, stay in Rovaniemi city centre: the airport shuttle stops there and bus 8 reaches Santa Claus Village, 8 km north. Choose Arctic Light Hotel for character, Santa's Hotel Rudolf for a budget bed, Santa's Igloos for a glass roof. VAT on accommodation is 13.5%.",
        link_text="Rovaniemi city centre",
        cta=_stay_cta("where-to-stay-in-rovaniemi-christmas", "See hotels around Rovaniemi city centre")),
    "where-to-stay-in-new-york-new-years-eve": dict(
        text="To watch the Ball from a warm room, stay inside the Times Square closures: the Marriott Marquis sells a Ball Drop View Room, with a three-to-four-night minimum. Otherwise stay just outside them and walk in. The tax is 14.75% plus $3.50 a night, so $347.75 on a $300 room.",
        link_text="Times Square",
        cta=_stay_cta("where-to-stay-in-new-york-new-years-eve", "See hotels around Times Square")),
    "where-to-stay-in-cape-town": dict(
        text="For a first trip, stay at the V&A Waterfront: the harbour, the shops and MyCiTi buses are at the door. Choose Cape Grace for the quay, the Victoria & Alfred Hotel for a 1904 warehouse, the Greenhouse Guesthouse for value. The tax is 15% VAT, plus a 1% levy at some hotels.",
        link_text="V&A Waterfront",
        cta=_stay_cta("where-to-stay-in-cape-town", "See hotels around the V&A Waterfront")),
    "where-to-stay-in-queenstown": dict(
        text="For a first trip, stay in the town centre: the lakefront and restaurants on foot. Choose Fernhill for views over Lake Wakatipu, Frankton for the airport and kitchens, Arrowtown for a quiet village. GST adds 15%, and no visitor levy is charged.",
        link_text="town centre",
        cta=_stay_cta("where-to-stay-in-queenstown", "See hotels around the town centre")),
    "where-to-stay-in-chicago": dict(
        text="For a first trip, stay in the Loop: Millennium Park, Grant Park and the 'L' are close. Choose the Palmer House for history, HI Chicago for value, the Peninsula for a splurge up the Mile. The tax is 17.4%, or $52.20 on a $300 room.",
        link_text="the Loop",
        cta=_stay_cta("where-to-stay-in-chicago", "See hotels around the Loop")),
    "where-to-stay-in-boston": dict(
        text="For a first trip, stay in Back Bay: Copley Square and Newbury Street are close, and the Logan Express runs from here for $3. Choose The Lenox for a classic address, Newbury Guest House for value, the Fairmont Copley Plaza for the square. The tax is 14.95%, or $44.85 on a $300 room.",
        link_text="Back Bay",
        cta=_stay_cta("where-to-stay-in-boston", "See hotels around Back Bay")),
    "where-to-stay-in-tulum": dict(
        text="For a first trip, stay in Tulum Pueblo: the bus terminal and the town are at hand. Choose Aldea Zamá for apartments, the Hotel Zone for the beach and Akumal for an all-inclusive bay. A room carries 5% lodging tax plus 16% IVA, and foreign visitors pay the Visitax, about 285 pesos.",
        link_text="Tulum Pueblo",
        cta=_stay_cta("where-to-stay-in-tulum", "See hotels around Tulum Pueblo")),
    "where-to-stay-in-washington-dc": dict(
        text="For a first trip, stay in Downtown and Penn Quarter: the White House, Capital One Arena and the National Mall are close, and the Smithsonian charges no admission. Choose the Willard for history, Moxy for value, the Wharf for the water. The tax is 15.95%, or $47.85 on a $300 room.",
        link_text="Downtown and Penn Quarter",
        cta=_stay_cta("where-to-stay-in-washington-dc", "See hotels around Penn Quarter")),
    "where-to-stay-in-miami": dict(
        text="For a first trip, stay in South Beach: Ocean Drive, Lummus Park and the Art Deco district are on foot. Choose Faena for space, Brickell for the trains, Wynwood for murals. The tax is 14% on Miami Beach and 13% on the mainland, plus each hotel's daily fee.",
        link_text="South Beach",
        cta=_stay_cta("where-to-stay-in-miami", "See hotels around South Beach")),
    "where-to-stay-in-san-diego": dict(
        text="For a first trip, stay in the Gaslamp Quarter: restaurants, Petco Park and the Convention Center are close, and the Green Line stops there. Choose Pendry for a splurge, Hotel Republic for comfort, the HI hostel for budget. Hotel tax is 11.75% to 13.75% by zone, plus 2% at larger hotels.",
        link_text="Gaslamp Quarter",
        cta=_stay_cta("where-to-stay-in-san-diego", "See hotels around the Gaslamp Quarter")),
    "where-to-stay-in-dubai": dict(
        text="For a first trip, stay in Downtown Dubai: the Burj Khalifa, the Dubai Mall and a metro station are close. Choose old Dubai for the Creek, Marina and JBR for the beach, the Palm for a resort. The Tourism Dirham is AED 7 to 20 a room a night, plus fees.",
        link_text="Downtown Dubai",
        cta=_stay_cta("where-to-stay-in-dubai", "See hotels around Downtown Dubai")),
    "where-to-stay-in-orlando": dict(
        text="For a first trip built around Disney, stay in Walt Disney World and Lake Buena Vista: Disney's own hotels carry 30-minute early theme park entry. Choose Universal's hotels for Universal's parks, Gaylord Palms for a Kissimmee water-park resort. The tax is 12.5% in Orange County, 13.5% in Osceola.",
        link_text="Walt Disney World and Lake Buena Vista",
        cta=_stay_cta("where-to-stay-in-orlando", "See hotels around Lake Buena Vista")),
    "where-to-stay-in-hiroshima": dict(
        text="For a first trip, stay near the Peace Memorial Park: the park is a short walk and streetcars reach the station. Choose Hiroshima Station for the Shinkansen and Miyajima for a night on the island. The prefecture's ¥200 tax applies from rooms of ¥6,000 a night.",
        link_text="Peace Memorial Park",
        cta=_stay_cta("where-to-stay-in-hiroshima", "See hotels around the Peace Memorial Park")),
    "where-to-stay-in-kanazawa": dict(
        text="For a first trip, stay in Omicho: from The Hotel Sanraku Kanazawa the market is a minute on foot, the castle park three and Kenrokuen ten. Choose Kanazawa Station for the Shinkansen and Korinbo for dinners. The city tax is ¥200 or ¥500 per person per night.",
        link_text="Omicho",
        cta=_stay_cta("where-to-stay-in-kanazawa", "See hotels around Omicho")),
    "where-to-stay-in-jeju": dict(
        text="For a first trip, stay in Nohyeong and Yeon-dong: the airport is in Jeju City, 10 to 15 minutes from two hotels here. Choose Jungmun for resort pools, Seogwipo for the south-coast town, Aewol for the west-coast sea and Seongsan for sunrise. The VAT is 10%, and the 600 bus runs ₩1,300 to ₩5,500.",
        link_text="Nohyeong and Yeon-dong",
        cta=_stay_cta("where-to-stay-in-jeju", "See hotels around Nohyeong and Yeon-dong")),
    "where-to-stay-in-okinawa": dict(
        text="For a first trip without a car, stay in Naha near Kokusai-dori: the Yui Rail runs from the airport and the main street is on foot. Choose Chatan for the beach, Onna for resorts and Motobu for the aquarium. The 2% prefecture tax starts on 1 February 2027.",
        link_text="Kokusai-dori",
        cta=_stay_cta("where-to-stay-in-okinawa", "See hotels around Kokusai-dori")),
    "where-to-stay-in-marrakech": dict(
        text="For a first trip, stay in the Medina near Jemaa el-Fnaa: the square, the souks and the Koutoubia are on foot. Choose Mouassine for riad lanes, the Kasbah for palaces, Gueliz for cafés, Hivernage for pools. The law sets the tourist tax at MAD 2 to 30 a person a night, plus 10% VAT.",
        link_text="the Medina near Jemaa el-Fnaa",
        cta=_stay_cta("where-to-stay-in-marrakech", "See hotels around Jemaa el-Fnaa")),
    "where-to-stay-in-shanghai": dict(
        text="For a first trip, stay around People's Square: metro lines 1, 2 and 8 meet there, and Nanjing Road runs towards the Bund. Choose the Bund for the river, Jing'an for a park, Lujiazui for the skyline and Hongqiao for flights. VAT is 6%, and some hotels add a service charge.",
        link_text="People's Square",
        cta=_stay_cta("where-to-stay-in-shanghai", "See hotels around People's Square")),
    "where-to-stay-in-dubrovnik": dict(
        text="For a first trip, stay in the Old Town: the Stradun, the walls and the lanes are on foot. Choose Ploče for the sea, Pile for the city buses, Lapad for beaches and Babin Kuk for pools. The tourist tax is €2.65 a person a night from April to September, €1.85 otherwise.",
        link_text="the Old Town",
        cta=_stay_cta("where-to-stay-in-dubrovnik", "See hotels around the Old Town")),
    "where-to-stay-in-krakow": dict(
        text="For a first trip, stay in the Old Town: the Main Market Square, Floriańska Street and the Planty park are on foot, and Kraków Główny station is a short walk. Choose Kazimierz for tenement streets, Wawel for the castle and Podgórze for the river. Kraków charges no tourist tax in 2026.",
        link_text="the Old Town",
        cta=_stay_cta("where-to-stay-in-krakow", "See hotels around the Old Town")),
    "where-to-stay-in-nice": dict(
        text="For a first trip, stay in Vieux Nice: the lanes, the Cours Saleya market and the beach are on foot. Choose the Promenade for the sea, the Carré d'Or for shops, the station for trains and Port Lympia for the harbour. The tax is €1.07 to €6.43 a person a night, by stars.",
        link_text="Vieux Nice",
        cta=_stay_cta("where-to-stay-in-nice", "See hotels around Vieux Nice")),
    "where-to-stay-in-mexico-city": dict(
        text="For a first trip, stay in Roma Norte: cafés, galleries and mansions on foot. Choose Condesa for leafy streets, Polanco for Masaryk and the park, the Centro Histórico for the Zócalo. A hotel room carries 3.5% lodging tax plus 16% IVA, 19.5% in all.",
        link_text="Roma Norte",
        cta=_stay_cta("where-to-stay-in-mexico-city", "See hotels around Roma Norte")),
    "where-to-stay-in-chiang-mai": dict(
        text="For a first trip, stay in the Old City: temples are on foot, and Rachamankha, Tamarind Village and Stamps cover three budgets. Choose Nimman for cafés, the river for a historic house, Mae Rim for a resort. Prices marked ++ add 17.7%: a 10% service charge, then 7% VAT.",
        link_text="Old City",
        cta=_stay_cta("where-to-stay-in-chiang-mai", "See hotels around the Old City")),
    "where-to-stay-in-cancun": dict(
        text="For a first trip, stay in the Hotel Zone: the beach and the resorts are at your door. Choose Downtown for a lower bill, Isla Mujeres for the island and Playa del Carmen for a town base. A room carries 5% lodging tax plus 16% IVA, and foreign visitors pay the Visitax, about 285 pesos.",
        link_text="Hotel Zone",
        cta=_stay_cta("where-to-stay-in-cancun", "See hotels around the Hotel Zone")),
    "where-to-stay-in-da-nang": dict(
        text="For a first trip, stay in My Khe: beach hotels on Vo Nguyen Giap Street, with the airport 4 km away by Haian's count. Choose the Han River for the city, Hoi An for the Ancient Town and An Bang for a quieter beach. VAT is 8% until 31 December 2026, then 10% unless extended.",
        link_text="My Khe",
        cta=_stay_cta("where-to-stay-in-da-nang", "See hotels around My Khe")),
    "where-to-stay-in-phuket": dict(
        text="For a first trip, stay in Kata: a bay beach on the Smart Bus line, with Karon beside it. Choose Patong for nightlife, Kamala or Bang Tao for resorts, the Old Town for streets and food. Prices marked ++ add 17.7%: a 10% service charge, then 7% VAT.",
        link_text="Kata",
        cta=_stay_cta("where-to-stay-in-phuket", "See hotels around Kata Beach")),
    "where-to-stay-in-porto": dict(
        text="For a first trip, stay in Ribeira and the Historic Centre: the river quay, São Bento station and the Dom Luís I bridge are on foot. Choose Baixa for shops, Cedofeita for galleries, Gaia for the Port lodges and Foz for the sea. Porto's tax is €3 a person a night, up to seven nights.",
        link_text="Ribeira and the Historic Centre",
        cta=_stay_cta("where-to-stay-in-porto", "See hotels around Ribeira")),
    "where-to-stay-in-san-francisco": dict(
        text="For a first trip, stay in Union Square: the Powell Street BART and Muni station and the cable cars are close. Choose The Clift for an old-school hotel, Hotel Zeppelin for value, the Fairmont on Nob Hill for a splurge. Tax is 14% plus up to 3.5% in district assessments.",
        link_text="Union Square",
        cta=_stay_cta("where-to-stay-in-san-francisco", "See hotels around Union Square")),
    "where-to-stay-in-las-vegas": dict(
        text="For a first trip, stay on the Center Strip: Bellagio's fountains, the Venetian and the Cosmopolitan are along one stretch of Las Vegas Boulevard. Choose Wynn for the north end, SAHARA for the monorail, the Plaza for Fremont Street. Room tax is 13.38% near the Strip, plus each resort's fee.",
        link_text="Center Strip",
        cta=_stay_cta("where-to-stay-in-las-vegas", "See hotels around the Center Strip")),
    "where-to-stay-in-milan": dict(
        text="For a first trip, stay near the Duomo: the cathedral, the Galleria and La Scala are a walk away. Choose Navigli for the canal, Porta Nuova for the skyline and Centrale for trains. The tax is €3 to €12 a person a night by stars; under-18s pay nothing.",
        link_text="the Duomo",
        cta=_stay_cta("where-to-stay-in-milan", "See hotels around the Duomo")),
    "where-to-stay-in-seville": dict(
        text="For a first trip, stay in Santa Cruz: the old Jewish quarter beside the Cathedral and the Alcázar. Choose Triana for the river, the Alameda for bars and Santa Justa for early trains. Seville adds no tourist tax in October 2026, only 10% VAT; a tax is still a proposal.",
        link_text="Santa Cruz",
        cta=_stay_cta("where-to-stay-in-seville", "See hotels around Santa Cruz")),
    "where-to-stay-in-los-angeles": dict(
        text="For a first trip, stay in Santa Monica: the pier, Third Street Promenade and the beach are on foot, and Metro's E Line runs to Downtown. Choose Hollywood for the Walk of Fame, West Hollywood for nights out, Downtown for the trains. Hotel tax is 15% plus a district assessment.",
        link_text="Santa Monica",
        cta=_stay_cta("where-to-stay-in-los-angeles", "See hotels around Santa Monica")),
    "where-to-stay-in-athens": dict(
        text="For a first trip, stay in Plaka: the old streets under the Acropolis, between Acropolis and Monastiraki metro stations. Choose Syntagma for the airport bus, Koukaki for the Acropolis Museum and Piraeus for an early ferry. The climate resilience fee is €2 to €15 a room a night, April to October.",
        link_text="Plaka",
        cta=_stay_cta("where-to-stay-in-athens", "See hotels around Plaka")),
    "where-to-stay-in-honolulu": dict(
        text="For a first trip, stay in central Waikiki: Kalakaua Avenue's shops and the beach are on foot, and the airport bus stops there. Choose Diamond Head for a quieter end, Kalia Road for big resorts, Ala Moana for the mall. Taxes add up to 18.712%.",
        link_text="central Waikiki",
        cta=_stay_cta("where-to-stay-in-honolulu", "See hotels around central Waikiki")),
    "where-to-stay-in-budapest": dict(
        text="For a first trip, stay in Belváros-Lipótváros: central Pest on foot, with Deák Ferenc tér where the 100E airport bus ends. Choose the Jewish Quarter for nightlife, Terézváros for Andrássy Avenue and Castle Hill for the river view. The tourist tax is 4% of the room price.",
        link_text="Belváros-Lipótváros",
        cta=_stay_cta("where-to-stay-in-budapest", "See hotels around Belváros-Lipótváros")),
    "where-to-stay-in-istanbul": dict(
        text="For a first trip, stay in Sultanahmet: the Blue Mosque and Hagia Sophia are steps away. Choose Karaköy and Galata for the tower, Beyoğlu for İstiklal Avenue and Kadıköy for the Asian side. The accommodation tax is 1% until 31 December 2026, plus VAT.",
        link_text="Sultanahmet",
        cta=_stay_cta("where-to-stay-in-istanbul", "See hotels around Sultanahmet")),
    "where-to-stay-in-ho-chi-minh-city": dict(
        text="For a first trip, stay in Dong Khoi: the Opera House, Nguyen Hue and the river on foot, with Line 1's Opera House station nearby. Choose Ben Thanh for the market and metro, District 3 for quiet, Thao Dien for the river. Rates are often quoted \"++\": add service charge and tax.",
        link_text="Dong Khoi",
        cta=_stay_cta("where-to-stay-in-ho-chi-minh-city", "See hotels around Dong Khoi")),
    "where-to-stay-in-hanoi": dict(
        text="For a first trip, stay in the Old Quarter: narrow trading streets, with the lake a short walk away. Choose the French Quarter for grand hotels, Ba Dinh for the Mausoleum and West Lake for views. VAT is 8% until 31 December 2026, then 10% unless extended.",
        link_text="the Old Quarter",
        cta=_stay_cta("where-to-stay-in-hanoi", "See hotels around the Old Quarter")),
    "where-to-stay-in-vancouver": dict(
        text="For a first trip, stay Downtown or in Coal Harbour: the seawall, Gastown and the Canada Line to the airport on foot. Choose the West End for Stanley Park and English Bay, Yaletown or Granville Island for False Creek. Taxes add about 19.2% to the room rate.",
        link_text="Coal Harbour",
        cta=_stay_cta("where-to-stay-in-vancouver", "See hotels around Coal Harbour")),
    "where-to-stay-in-montreal": dict(
        text="For a first trip, stay in Old Montreal: Notre-Dame Basilica, Place Jacques-Cartier and the Old Port on foot. Choose downtown for shops and the airport bus, the Plateau for local streets, and Griffintown for the canal. The 3.5% lodging tax, then GST and QST, add about 19%.",
        link_text="Old Montreal",
        cta=_stay_cta("where-to-stay-in-montreal", "See hotels around Old Montreal")),
    "where-to-stay-in-zurich": dict(
        text="For a first trip, stay in the Old Town: the Limmat, the Niederdorf and the Bahnhofstrasse on foot. Choose Zürich HB for the trains, Seefeld for the lake, Enge for value and Langstrasse for nightlife. The City Tax is CHF 3.50 per guest per night.",
        link_text="the Old Town",
        cta=_stay_cta("where-to-stay-in-zurich", "See hotels around the Old Town")),
    "where-to-stay-in-reykjavik": dict(
        text="For a first trip, stay downtown around Laugavegur: the shopping street, Austurvöllur and the pond are all on foot. Choose Hallgrímskirkja's hill for quieter streets, the Old Harbour for Harpa. Iceland's accommodation tax is 800 ISK a room a night; the 11% VAT is in the price.",
        link_text="Laugavegur",
        cta=_stay_cta("where-to-stay-in-reykjavik", "See hotels around Laugavegur")),
    "where-to-stay-in-copenhagen": dict(
        text="For a first trip, stay in Indre By: Strøget, Kongens Nytorv and Nyhavn on foot, and the M2 metro to the airport. Choose Christianshavn for canals, Vesterbro for Kødbyen's nightlife, and Nørrebro or Østerbro for local streets by the Lakes. There is no tourist tax; the 25% VAT is already in the price.",
        link_text="Indre By",
        cta=_stay_cta("where-to-stay-in-copenhagen", "See hotels around Indre By")),
    "where-to-stay-in-stockholm": dict(
        text="For a first trip, stay in Gamla Stan: the Royal Palace, Stortorget and the old lanes on foot, with the metro on the island. Choose Södermalm for bars and SoFo's shops, Östermalm for Strandvägen. Stockholm has no tourist tax; the 12% VAT is already in the price.",
        link_text="Gamla Stan",
        cta=_stay_cta("where-to-stay-in-stockholm", "See hotels around Gamla Stan")),
    "where-to-stay-in-dublin": dict(
        text="For a first trip, stay in Temple Bar: Trinity College, Dublin Castle and Grafton Street on foot, and airport coaches to its quays. Choose St Stephen's Green for a quieter classic base, Smithfield for lower prices. Dublin has no tourist tax; rooms carry 13.5% VAT, normally included in the price.",
        link_text="Temple Bar",
        cta=_stay_cta("where-to-stay-in-dublin", "See hotels around Temple Bar")),
    "where-to-stay-in-edinburgh": dict(
        text="For a first trip, stay in the Old Town: the Royal Mile, the castle and Waverley station on foot. Choose the New Town for Georgian squares, Leith for the waterfront and the West End for the airport tram. Since 24 July 2026 rooms carry a 5% Visitor Levy for up to five nights.",
        link_text="the Old Town",
        cta=_stay_cta("where-to-stay-in-edinburgh", "See hotels around the Old Town")),
    "where-to-stay-in-vienna": dict(
        text="For a first trip, stay in the Innere Stadt: St Stephen's, the Opera and the Hofburg on foot. Choose Leopoldstadt for a calmer base across the canal, Landstraße for the Belvedere and the airport train, and Neubau for the museums and bars. The city tax is 5% of the room price.",
        link_text="the Innere Stadt",
        cta=_stay_cta("where-to-stay-in-vienna", "See hotels around the Innere Stadt")),
    "where-to-stay-in-berlin": dict(
        text="For a first trip, stay in Mitte: the Brandenburg Gate, Museum Island and Hackescher Markt on foot, and the FEX to the airport. Choose Prenzlauer Berg for cafés and quiet streets, Kreuzberg or Friedrichshain for nightlife, and Charlottenburg for the Ku'damm. The City Tax is 7.5% of the room price.",
        link_text="Mitte",
        cta=_stay_cta("where-to-stay-in-berlin", "See hotels around Mitte")),
    "where-to-stay-in-madrid": dict(
        text="For a first trip, stay around Sol and the Centro: the Puerta del Sol, the Plaza Mayor and Gran Vía on foot. Choose the Barrio de las Letras for tapas squares and the Paseo del Arte for the Prado and the Retiro. Madrid has no tourist tax; rooms carry 10% VAT.",
        link_text="Sol and the Centro",
        cta=_stay_cta("where-to-stay-in-madrid", "See hotels around Sol")),
    "where-to-stay-in-bali": dict(
        text="For a first trip, stay in Seminyak: the beach, sunsets and restaurants on foot, close to the airport. Choose Ubud for temples and rice terraces, Sanur for calm water, and Uluwatu for cliffs and surf. The tourist levy is IDR 150,000 a person, once a trip.",
        link_text="Seminyak",
        cta=_stay_cta("where-to-stay-in-bali", "See hotels around Seminyak")),
    "where-to-stay-in-london": dict(
        text="For a first trip, stay in Covent Garden: the theatres and the market on foot, and the Piccadilly line straight from Heathrow. Choose the South Bank for the river, South Kensington for the museums and King's Cross for the Eurostar. London has no city tax; rooms carry 20% VAT, normally included in the price.",
        link_text="Covent Garden",
        cta=_stay_cta("where-to-stay-in-london", "See hotels around Covent Garden")),
    "where-to-stay-in-prague": dict(
        text="For a first trip, stay in the Old Town: Old Town Square, the Jewish Quarter and Charles Bridge on foot. Choose Malá Strana for the castle side, the New Town for the metro and the airport bus, and Vinohrady for cafés and parks. The city fee is 50 CZK a person a night.",
        link_text="the Old Town",
        cta=_stay_cta("where-to-stay-in-prague", "See hotels around the Old Town")),
    "where-to-stay-in-venice": dict(
        text="For a first trip, stay in San Marco: St Mark's Square, the Doge's Palace and the Grand Canal water buses at the door. Choose Castello for the waterfront for less, Dorsoduro for the galleries, and Mestre for the lowest tax. The tourist tax is up to €5 a person a night, €4.50 at a four-star.",
        link_text="San Marco",
        cta=_stay_cta("where-to-stay-in-venice", "See hotels around San Marco")),
    "where-to-stay-in-florence": dict(
        text="For a first trip, stay around the Duomo: the cathedral, the Uffizi and the Ponte Vecchio, all on foot. Choose Santo Spirito for evenings out, San Lorenzo for the David and Santa Maria Novella for the trains. The city tax is €7 a person a night at a four-star, for up to seven nights.",
        link_text="the Duomo",
        cta=_stay_cta("where-to-stay-in-florence", "See hotels around the Duomo")),
    "where-to-stay-in-barcelona": dict(
        text="For a first trip, stay in the Eixample: Passeig de Gràcia, Gaudí's Casa Batlló and La Pedrera, and the airport bus at Plaça de Catalunya. Choose the Gothic Quarter for medieval streets and Barceloneta for the beach. The tax is €8.40 a person a night at a four-star and €12 at a five-star.",
        link_text="Eixample",
        cta=_stay_cta("where-to-stay-in-barcelona", "See hotels around the Eixample")),
    "where-to-stay-in-rome": dict(
        text="For a first trip, stay in the Centro Storico: the Pantheon, Piazza Navona and the Trevi Fountain, all on foot. Choose Monti for the Colosseum, Trastevere for evenings out and Prati for the Vatican. The city tax is €7.50 a person a night at a four-star, for up to 10 nights.",
        link_text="the Centro Storico",
        cta=_stay_cta("where-to-stay-in-rome", "See hotels around the Centro Storico")),
    "where-to-stay-in-amsterdam": dict(
        text="For a first trip, stay in the Canal Ring: the 17th-century canals, with most sights on foot. Choose the Jordaan for village streets and markets, the Museum Quarter for the Rijksmuseum and Van Gogh, and Centraal for the train. The tourist tax is 12.5% of the room price, on top of 21% VAT.",
        link_text="the Canal Ring",
        cta=_stay_cta("where-to-stay-in-amsterdam", "See hotels around the Canal Ring")),
    "where-to-book-tokyo-food-tour": dict(
        text="Choose the tour on Viator, which has the most Tokyo food tours (300+) and the most reviews, then "
             "check the same title on Klook: during its sales it is often cheaper for the same Shinjuku tour. "
             "Skip KKday for Tokyo food. Decide by neighbourhood and time first: Shinjuku izakaya at night, "
             "Tsukiji in the morning, Asakusa for old-town snacks.",
        cta=("klook", "Check Tokyo food tours on Klook")),
    "where-to-book-mount-fuji-day-tour": dict(
        text="Klook and KKday both list the standard tour at about ¥7,800, so choose the month and the "
             "earliest departure instead: the whole mountain is visible about 7% of the time in June and "
             "60–77% in December and January. Book with free cancellation and check the forecast the "
             "night before.",
        cta=("klook", "Check Mount Fuji day tours on Klook")),
    "sydney-harbour-cruises-guide": dict(
        text="Pick by what you want from the two hours: a whale cruise between May and November, a sunset "
             "sightseeing cruise for the classic view, a multi-course dinner cruise for an occasion, the "
             "Aboriginal cultural cruise if you’ve been before — or the Manly ferry at dusk if you’re "
             "watching money.",
        cta=("klook", "Check Sydney harbour cruises on Klook")),
    "day-trips-from-tokyo": dict(
        text="With one day, make it Nikko for culture or Hakone for scenery and onsen; with two, add Kamakura "
             "for the coast. Kawagoe and Yokohama make easy half-days, and for Nikko, Hakone and Fuji a guided "
             "tour takes the train changes off your hands.",
        cta=("klook", "Browse Tokyo day tours on Klook")),
    # rail ---------------------------------------------------------------------
    "jr-pass-worth-it-2026": dict(
        text="Since the 2023 price rise, the 7-day nationwide JR Pass costs ¥50,000 and needs more than a "
             "Tokyo–Kyoto round trip (about ¥28,000) to pay off. It still wins on a "
             "Tokyo–Kyoto–Hiroshima loop inside a week; if you’re basing in Kansai, a regional pass "
             "such as JR West’s costs a fraction of the price.",
        cta=("klook", "Check JR Pass prices on Klook")),
    "korail-pass-worth-it-2026": dict(
        text="For most trips, no: one Seoul–Busan round trip costs about ₩119,600 in tickets against "
             "₩131,000 for the cheapest 2-day pass, and the pass doesn’t cover SRT, the roughly 10% "
             "cheaper operator on the same line. It pays off only with three or more intercity journeys.",
        cta=("klook", "Check KORAIL Pass prices on Klook")),
    "taiwan-high-speed-rail-pass-worth-it": dict(
        text="The 3-Day Pass is the one most visitors buy and the one that most often loses: at NT$2,200 it "
             "beats the NT$2,980 standard round trip, but an Early Bird round trip is about NT$1,938 and a "
             "buy-one-get-one pair works out near NT$1,266 each. The discounts don’t stack, so the order "
             "you check them in decides the price.",
        cta=("klook", "Compare THSR tickets on Klook")),
    "europe-rail-pass-worth-it-2026": dict(
        text="A pass wins when you’ll cover long distances across several countries, keep your plans "
             "loose, travel with children aged 4–11 or are under 28. With a fixed route, advance "
             "point-to-point fares in France, Spain, Italy and Germany are often cheaper than a pass day plus "
             "its seat reservation. Eurail and Interrail merged into one range on 9 September 2026.",
        cta=("klook", "Check rail passes on Klook")),
    "tokyo-to-kyoto-shinkansen-vs-flight-vs-bus": dict(
        text="Take the Shinkansen: about 2 hours 15 minutes and about \u00a514,170 on the Nozomi, city "
             "centre to city centre. Flying via Osaka takes about twice as long door to door, and the "
             "overnight bus is the budget option.",
        cta=("klook", "Check Shinkansen tickets on Klook")),
    "japan-city-sightseeing-passes-worth-it": dict(
        text="A city pass pays off only if you’ll visit several of its included, higher-priced attractions "
             "within its validity — add up the individual entry fees for your actual plan before you buy. "
             "For unhurried trips with few paid sights, individual tickets are usually cheaper.",
        cta=("klook", "Compare Japan city passes on Klook")),
    # connectivity -------------------------------------------------------------
    "best-travel-esim-2026": dict(
        text="Airalo is the best all-rounder for coverage and simplicity; Saily usually wins on price per GB, "
             "especially for larger and longer plans; and Holafly is only worth it if you’ll genuinely use "
             "unlimited data. No single eSIM wins every trip, so match it to your destination and your data.",
        cta=("airalo", "Compare Airalo plans for your destination")),
    "airalo-vs-holafly-vs-saily": dict(
        text="Airalo is the flexible default, with wide country coverage and plans you can size to your trip; "
             "Saily is the one to price-check for simple, good-value data; and Holafly only pays off if "
             "you’ll genuinely use unlimited data — read its fair-usage policy first.",
        cta=("airalo", "Compare Airalo plans for your destination")),
    "best-esim-japan-2026": dict(
        text="For most Japan trips, Airalo is the default — the widest plan range, from about 1 GB for 7 "
             "days to 10 GB+ for 30, with easy top-ups. Saily is the sharp-priced alternative, and a pocket "
             "WiFi only makes sense for a group sharing one connection.",
        cta=("airalo", "See Airalo’s Japan plans")),
    "best-esim-south-korea-2026": dict(
        text="Reach for Airalo first — broad Korea plans and an app that makes activating and topping up "
             "simple — and use Saily as the value check on price per GB. Install it before you fly so "
             "it’s live when you land at Incheon or Gimpo.",
        cta=("airalo", "See Airalo’s South Korea plans")),
    "best-esim-japan-korea-vietnam": dict(
        text="Expect roughly ¥2,000–5,000 for a 7-day, ~10 GB plan in Japan, ₩15,000–30,000 in "
             "Korea, and about $4–10 for 5–10 GB in Vietnam. Separate country plans are usually cheaper "
             "per GB; a regional Asia plan buys convenience across borders, not a lower price.",
        cta=("airalo", "Compare Airalo plans for each country")),
    "best-esim-taiwan-2026": dict(
        text="A travel eSIM installed over Wi-Fi before you land covers most Taiwan trips: Airalo’s range "
             "of packages makes it easy to match a plan to your trip length, and Saily is the alternative to "
             "compare. Pick up an EasyCard for the MRT once you arrive.",
        cta=("airalo", "See Airalo’s Taiwan plans")),
    "best-esim-thailand-2026": dict(
        text="For most short trips, a travel eSIM from Airalo or Saily installed before you fly is the "
             "practical choice, and 5–10 GB covers typical use. Size up if you’ll stream or tether: "
             "video can use 1–3 GB an hour.",
        cta=("airalo", "See Airalo’s Thailand plans")),
    "best-esim-vietnam-2026": dict(
        text="For 15–30 days in Vietnam, a 5–10 GB plan is usually more than enough, and Airalo and Saily "
             "both sell plans in that range for roughly $4–10. Install it on Wi-Fi before you leave home.",
        cta=("airalo", "See Airalo’s Vietnam plans")),
    "best-esim-usa-2026": dict(
        text="For a two-to-three-week trip, a 10–20 GB plan from Airalo or Saily, installed at home over "
             "Wi-Fi, is the comfortable choice; a regional North America plan only makes sense if Canada or "
             "Mexico is on the route.",
        cta=("airalo", "See Airalo’s USA plans")),
    "best-esim-australia-2026": dict(
        text="For one to three weeks, Airalo is the straightforward pick and Saily the one to check for a "
             "larger bundle for less; a 5 GB plan covers most weeks. Staying four weeks or more, or on a "
             "working holiday, a local Telstra or Optus prepaid SIM usually works out cheaper.",
        cta=("airalo", "See Airalo’s Australia plans")),
    "best-esim-europe-2026": dict(
        text="For a multi-country trip, a regional Europe eSIM from Airalo or Saily is the practical choice "
             "— check that non-EU stops such as Switzerland, the UK or the Balkans are included. Moderate "
             "use for one to two weeks typically needs 10–20 GB.",
        cta=("airalo", "Compare Europe eSIM plans on Airalo")),
    "esim-vs-physical-sim-card": dict(
        text="For most short trips, an eSIM is the better buy: you set it up before you fly and keep your home "
             "number on the same phone, which usually outweighs a slightly higher price per GB. A local "
             "physical SIM can still win on price, especially for longer stays.",
        cta=("airalo", "Compare travel eSIM plans on Airalo")),
    "pocket-wifi-vs-esim": dict(
        text="For solo travellers and couples, an eSIM wins: no extra device to carry, charge or return, and it "
             "can be live before you land. Pocket WiFi is the better choice for families or groups of three "
             "or more sharing one connection, or for heavy multi-device use.",
        cta=("airalo", "Compare travel eSIM plans on Airalo")),
    "staying-connected-south-korea": dict(
        text="For most short trips to South Korea, a travel eSIM is the easiest option — installed before "
             "you fly and live the moment you land at Incheon or Gimpo. A local physical SIM can be cheaper "
             "for long stays, and pocket WiFi suits a group sharing one connection.",
        cta=("airalo", "Browse South Korea eSIM plans"), replace=LEGACY_BOX),
    # insurance ----------------------------------------------------------------
    "best-travel-insurance-2026": dict(
        text="There is no single best policy, so we rank by traveller type: SafetyWing for digital nomads and "
             "open-ended trips, World Nomads for adventure and activity-heavy trips, Genki for long stays and "
             "Europe-based travellers, and EKTA for straightforward short trips.",
        cta=("ekta", "Get a quote from EKTA")),
    "best-travel-insurance-australia-2026": dict(
        text="For most Australia itineraries, EKTA is our default pick: comprehensive medical, cancellation and "
             "baggage cover with straightforward online management. SafetyWing suits open-ended trips, and "
             "World Nomads anyone planning surfing, diving or other adventure activities.",
        cta=("ekta", "Get an Australia quote from EKTA")),
    "best-travel-insurance-digital-nomads-2026": dict(
        text="Nomads need a different policy from holidaymakers: prioritise high medical limits and emergency "
             "evacuation, choose between a rolling subscription and a fixed term, and check how the policy "
             "treats time back in your home country. Gear and adventure activities are the usual exclusions.",
        cta=("ekta", "Compare cover with EKTA")),
    "is-travel-insurance-a-rip-off": dict(
        text="As a bet, travel insurance always loses — premiums exceed average payouts by design. As a "
             "decision it is rational when it covers the rare, ruinous costs you couldn’t absorb: buy "
             "medical and evacuation cover, skip the padded extras, and check what your card already includes.",
        cta=("ekta", "Get a quick quote from EKTA")),
    "is-travel-insurance-worth-it": dict(
        text="For most trips, yes — when the downside is large and unlikely: a medical emergency abroad, an "
             "evacuation home, or a cancelled trip you’ve already paid for. It’s rarely worth it for small "
             "losses you could absorb, so insure what would genuinely hurt and skip what wouldn’t.",
        cta=("ekta", "Get a quick quote from EKTA"), replace=LEGACY_BOX),
    "safetywing-vs-world-nomads": dict(
        text="SafetyWing suits long-term travellers and digital nomads who want flexible, affordable emergency "
             "medical cover; World Nomads suits adventure-heavy or structured trips that need broader "
             "protection for activities and trip disruption.",
        cta=None),
    "travel-insurance-compared": dict(
        text="Match the insurer to how you travel: SafetyWing for long-term, location-independent workers who "
             "mainly need medical cover; World Nomads for structured, adventure-focused trips; and Genki for "
             "long stays with ongoing health needs.",
        cta=None),
    "travel-insurance-japan": dict(
        text="Japan doesn’t require tourists to hold travel insurance, but it’s strongly recommended: "
             "care is excellent, there’s no reciprocal public cover for most nationalities, and hospitals "
             "expect visitors to pay in full. Prioritise emergency medical, hospitalisation and evacuation.",
        cta=("ekta", "Get a Japan quote from EKTA"), replace=LEGACY_BOX),
    "travel-insurance-south-korea": dict(
        text="South Korea doesn’t require travel insurance to enter, but it’s strongly recommended: "
             "visitors pay for private medical care and most nationalities have no reciprocal cover. "
             "Emergency medical, hospitalisation and evacuation matter most.",
        cta=("ekta", "Get a South Korea quote from EKTA"), replace=LEGACY_BOX),
    # timing and places --------------------------------------------------------
    "best-time-to-visit-japan-2026": dict(
        text="For a first trip with flexible dates, go in May or October–November: they balance weather, "
             "colour and crowds best. Cherry-blossom and autumn-leaf weeks are glorious but peak-priced, and "
             "December to mid-March is Japan at its cheapest and least crowded.",
        cta=("klook", "Book Japan experiences ahead on Klook")),
    "best-time-to-visit-australia": dict(
        text="For a first trip mixing Sydney or Melbourne with the Reef or the north, go between May and "
             "October, when the southern winter-into-spring and the northern dry season overlap. For the "
             "southern cities alone, September–November and March–May are the milder, better-value windows.",
        cta=("klook", "Browse Australia tours on Klook")),
    "best-time-to-visit-vietnam": dict(
        text="For a first trip from north to south, late February to April and October to November compromise "
             "least: the north at its best and the south dry, with some rain risk on the central coast in "
             "autumn. May to September is noticeably cheaper and greener if you can live with afternoon rain.",
        cta=("klook", "Browse Vietnam experiences on Klook")),
    "charter-a-boat-for-a-day": dict(
        text="With no boating licence, the simple answer is a skippered charter; SamBoat lists both skippered "
             "and licence-free boats. You can still hire a small motorboat without a licence in Italy (up to "
             "40 HP, within 6 nautical miles), Greece (up to 30 HP, within 3), Croatia (up to 5 m and 5 kW, "
             "within 500 m of shore) and on UK canals — but not in Spain from 1 October 2026, when renters "
             "will need at least a one-day licence.",
        cta=("samboat", "Browse licence-free and skippered boats on SamBoat"),
        note_html='<strong>Who this guide is for:</strong> first-time charterers with no boating history, '
                  'planning a single day on the water. Ticking the day off a bigger trip? '
                  '<a href="../index.html#ready">Check your Ready Score</a>.'),
    # gear ---------------------------------------------------------------------
    "best-power-bank-travel-2026": dict(
        text="For most trips, carry a 10,000 mAh power bank such as the Anker PowerCore 10000: two phone "
             "charges at about 180 g, and at 37 Wh it sits well inside airlines’ 100 Wh carry-on limit. "
             "Power banks go in your hand luggage, never in checked bags.",
        cta=("amazon", "B01B12PTOM", "View the Anker PowerCore 10000 on Amazon")),
    "best-travel-adapter-asia-2026": dict(
        text="For a multi-country Asia trip, one universal adapter such as the EPICKA TA-105 — covering "
             "Type A, G and I plus USB-C and USB-A — beats a bag of single plugs. It adapts the plug, "
             "not the voltage.",
        cta=("amazon", "B078S3M2NX", "View the EPICKA TA-105 on Amazon")),
}

# Pages whose substance was revised on the date given (facts re-checked, not
# just re-laid-out). Only these get a fresh dateModified; a verdict box that
# restates an article's own conclusion is not a reason to claim it was updated.
REVISED = {
    "klook-vs-viator-vs-getyourguide": "2026-10-01",            # corrected: GetYourGuide links go through Stay22
    "where-to-book-halong-bay-cruise": "2026-10-01",            # corrected: same
    "where-to-book-jeju-bus-tour": "2026-10-01",                # corrected: same
    "where-to-book-sydney-harbour-cruise": "2026-10-01",        # corrected: same
    "where-to-book-tokyo-food-tour": "2026-10-01",              # corrected: same
    "where-to-book-bangkok-dinner-cruise": "2026-09-29",        # corrected: Wat Arun photo caption said "from the water"
    "where-to-stay-in-osaka": "2026-09-28",                     # corrected: not the only hotel on a direct airport line
    "hotel-booking-sites-comparison": "2026-09-28",             # corrected: Hotels.com One Key/Rewards, Genius levels
    "tokyo-to-kyoto-shinkansen-vs-flight-vs-bus": "2026-09-27",  # bus fares re-checked on Willer (from ¥2,100)
    "narita-haneda-to-central-tokyo": "2026-09-27",              # added Narita <-> Haneda, official fares
    "charter-a-boat-for-a-day": "2026-09-23",                    # Spain 1 Oct 2026, Greece, Croatia
    "where-to-stay-in-tokyo": "2026-09-25",                      # rewrite: 17 verified hotels, tax, tables
    "japan-tourist-taxes-2026": "2026-10-08",                    # corrected: Niseko tiered; Hokkaido/Sapporo; Fukuoka; Nagano's tax began 1 Jun 2026 (Hakuba)
    "hong-kong-first-timers-guide": "2026-10-04",                # corrected: tram fare HK$3.30, not HK$3
    "where-to-stay-in-sydney": "2026-10-05",                     # corrected: Great Southern works now run to 31 Jan 2027
    "is-the-weak-yen-a-bargain-or-trap": "2026-10-06",           # corrected: Himeji's ¥2,500 is for all non-residents; no Niseko foreigner price
}

STOP_HEADINGS = re.compile(r"frequently asked|^sources|references|liked this guide|keep reading|related reading",
                           re.I)
SKIP_SELECTOR = ".gy-verdict, .gy-promo, .gy-finder-pointer, .gy-widget, .gy-cta, .gy-section-link, figure, .faq, .newsletter, script, style"


# --- dates --------------------------------------------------------------------
@lru_cache(maxsize=None)
def first_publish_date(rel: str) -> str | None:
    """Date of the commit that first added site/<rel>, or None if uncommitted."""
    out = subprocess.run(
        ["git", "log", "--diff-filter=A", "--follow", "--format=%ad", "--date=short", "--", f"site/{rel}"],
        cwd=REPO, capture_output=True, text=True).stdout.split()
    return out[-1] if out else None


def human(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {d:%b %Y}"


def _article_ld(soup: BeautifulSoup):
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") in ("Article", "BlogPosting", "NewsArticle"):
            return script, data
    return None, None


def _set_meta_prop(soup: BeautifulSoup, prop: str, value: str) -> None:
    tag = soup.find("meta", attrs={"property": prop})
    if tag is not None:
        tag["content"] = value


def apply_dates(soup: BeautifulSoup, rel: str, *, modified: str | None = None) -> None:
    script, data = _article_ld(soup)
    if data is None:
        return
    published = data.get("datePublished") or date.today().isoformat()
    first = first_publish_date(rel)
    if first and first < published:
        published = first                       # only ever move it earlier
    mod = modified or data.get("dateModified") or published
    if mod < published:
        mod = published
    data["datePublished"], data["dateModified"] = published, mod
    script.string = json.dumps(data, indent=2, ensure_ascii=False)
    _set_meta_prop(soup, "article:published_time", f"{published}T09:00:00+09:00")
    _set_meta_prop(soup, "article:modified_time", f"{mod}T09:00:00+09:00")

    hero = soup.select_one("header.article-hero, header.hero")
    if hero is None:
        return
    span = hero.select_one(".article-meta .meta-date")
    if span is None:                            # the three hand-built pages have no meta row
        meta_p = soup.new_tag("p", attrs={"class": "article-meta"})
        span = soup.new_tag("span", attrs={"class": "meta-date"})
        meta_p.append(span)
        anchor = hero.select_one("p.subtitle") or hero.select_one("p.article-byline") or hero.select_one("h1")
        anchor.insert_after(meta_p)
    span.clear()
    span.append("Last updated ")
    t = soup.new_tag("time", attrs={"datetime": mod})
    t.string = human(mod)
    span.append(t)


# --- links --------------------------------------------------------------------
def _page_href(soup: BeautifulSoup, key: str, slug: str | None = None) -> str:
    if slug and key in PAGE_HREF.get(slug, {}):
        return PAGE_HREF[slug][key]
    pat = re.compile(HREF_MATCH[key])
    for a in soup.select(".article a[href]"):
        if pat.search(a["href"]) and not a.has_attr("data-aeo"):
            return a["href"]
    return DEFAULT_HREF[key]


def _amazon_href(soup: BeautifulSoup, asin: str) -> str | None:
    for a in soup.select(".article a[href]"):
        if "amazon." in a["href"] and asin in a["href"]:
            return a["href"]
    return None


def _anchor(soup: BeautifulSoup, href: str, *, managed: bool = True) -> Tag:
    attrs = {"href": href, "rel": REL, "target": "_blank"}
    if managed:
        attrs["data-aeo"] = "1"
    return soup.new_tag("a", attrs=attrs)


def _eligible(el: Tag, after_stop: set[int]) -> bool:
    if id(el) in after_stop:                    # FAQ, sources, related reading
        return False
    if el.find_parent("a") or el.find_parent("figure"):
        return False
    if el.find_parent(lambda t: isinstance(t, Tag) and t.get("class") and any(
            c in ("gy-verdict", "gy-promo", "gy-finder-pointer", "gy-widget", "gy-cta", "gy-section-link", "faq", "newsletter")
            for c in t.get("class"))):
        return False
    return True


def _stop_heading(article: Tag) -> Tag | None:
    for h in article.find_all("h2"):
        if STOP_HEADINGS.search(h.get_text(" ", strip=True)):
            return h
    return None


def _brand_of(text: str) -> str | None:
    return BRANDS.get(text.strip().rstrip("*").strip())


def link_brands(soup: BeautifulSoup, slug: str | None = None) -> int:
    article = soup.select_one("section.article")
    if article is None:
        return 0
    # everything from the FAQ heading on is answers and navigation, not the
    # decision itself — computed once, not per element (that was quadratic)
    stop = _stop_heading(article)
    after_stop = {id(stop)} | {id(x) for x in stop.find_all_next()} if stop else set()
    added = 0

    # 1. comparison tables: first mention of each partner per table
    for table in article.find_all("table"):
        if not _eligible(table, after_stop):
            continue
        done: set[str] = set()
        for cell in table.find_all(["th", "td"]):
            first = next((c for c in cell.children
                          if not (isinstance(c, NavigableString) and not c.strip())), None)
            if first is None or cell.find("a"):
                continue
            if isinstance(first, Tag) and first.name == "strong":
                key, target = _brand_of(first.get_text()), first
            elif isinstance(first, NavigableString) and len(list(cell.children)) == 1:
                key, target = _brand_of(str(first)), first
            else:
                continue
            if not key or key in done:
                continue
            a = _anchor(soup, _page_href(soup, key, slug))
            target.wrap(a)
            done.add(key)
            added += 1

    # 2. lists whose items open with a bold partner name ("Booking.com — largest
    #    inventory…"): the at-a-glance rundowns readers reach on the second screen.
    #    First mention of each partner per list, as with tables.
    for lst in article.find_all(["ul", "ol"]):
        if not _eligible(lst, after_stop):
            continue
        done: set[str] = set()
        for li in lst.find_all("li", recursive=False):
            first = next((c for c in li.children
                          if not (isinstance(c, NavigableString) and not c.strip())), None)
            if not (isinstance(first, Tag) and first.name == "strong") or first.find("a"):
                continue
            key = _brand_of(first.get_text())
            if not key or key in done:
                continue
            first.wrap(_anchor(soup, _page_href(soup, key, slug)))
            done.add(key)
            added += 1

    # 3. paragraphs that open with a bold partner name — the top of that
    #    platform's discussion; first per partner per article
    seen: set[str] = set()
    for p in article.find_all("p"):
        if not _eligible(p, after_stop) or p.find_parent(["td", "th", "li"]):
            continue
        first = next((c for c in p.children
                      if not (isinstance(c, NavigableString) and not c.strip())), None)
        if not (isinstance(first, Tag) and first.name == "strong"):
            continue
        key = _brand_of(first.get_text())
        if not key or key in seen:
            continue
        first.wrap(_anchor(soup, _page_href(soup, key, slug)))
        seen.add(key)
        added += 1

    # 4. headings that name exactly one partner ("1. Airalo — Best Overall …")
    head_re = re.compile(r"^\s*(?:\d+(?:\s*&\s*\d+)?\.\s*)?(" + "|".join(map(re.escape, BRANDS)) +
                         r")\s*(?:[—–:\-]|$)")
    for h in article.find_all(["h2", "h3"]):
        if not _eligible(h, after_stop) or h is stop:
            continue
        text = h.get_text(" ", strip=True)
        m = head_re.match(text)
        if not m:
            continue
        others = [b for b in BRANDS if b != m.group(1) and b in text]
        if others:
            continue
        key = BRANDS[m.group(1)]
        p = soup.new_tag("p", attrs={"class": "gy-section-link", "data-aeo": "1"})
        a = _anchor(soup, _page_href(soup, key, slug), managed=False)
        a.string = f"{SECTION_LABEL[key]} →"
        p.append(a)
        if key in SECTION_NOTE:
            before, code, after = SECTION_NOTE[key]
            p.append(" " + before)
            strong = soup.new_tag("strong")
            strong.string = code
            p.append(strong)
            p.append(after)
        h.insert_after(p)
        added += 1
    return added


# --- verdict ------------------------------------------------------------------
def _names_re(key: str) -> str | None:
    names = [n for n, k in BRANDS.items() if k == key]
    return r"\b(?:" + "|".join(re.escape(n) for n in names) + r")\b" if names else None


def render_verdict(soup: BeautifulSoup, spec: dict, slug: str | None = None) -> Tag:
    box = soup.new_tag("aside", attrs={"class": "gy-verdict", "data-aeo": "1"})
    p = soup.new_tag("p", attrs={"class": "gy-verdict-text"})
    label = soup.new_tag("strong", attrs={"class": "gy-verdict-label"})
    label.string = BRAND_LABEL
    p.append(label)
    cta = spec.get("cta")
    href = None
    if cta and cta[0] == "amazon":
        href, text = _amazon_href(soup, cta[1]), cta[2]
    elif cta and cta[0] == "href":
        href, text = cta[2], cta[1]
    elif cta:
        href, text = _page_href(soup, cta[0], slug), cta[1]
    # Link the partner where the verdict first names it, not only in the line
    # after the text: on a phone a long verdict pushed that last line below the
    # first screen on every decision article (the link must show unscrolled).
    wanted: list[tuple[str, str]] = []
    if href and spec.get("link_text"):
        wanted.append((re.escape(spec["link_text"]), href))
    elif href and cta[0] not in ("amazon", "href") and _names_re(cta[0]):
        wanted.append((_names_re(cta[0]), href))
    for key in spec.get("also", ()):
        if _names_re(key):
            wanted.append((_names_re(key), _page_href(soup, key, slug)))
    spans: list[tuple[int, int, str]] = []
    for pat, h in wanted:
        m = re.search(pat, spec["text"])
        if m and not any(m.start() < e and s < m.end() for s, e, _ in spans):
            spans.append((m.start(), m.end(), h))
    pos = 0
    for s, e, h in sorted(spans):
        p.append((" " if pos == 0 else "") + spec["text"][pos:s])
        inline = _anchor(soup, h, managed=False)
        inline.string = spec["text"][s:e]
        p.append(inline)
        pos = e
    p.append((" " if pos == 0 else "") + spec["text"][pos:])
    box.append(p)
    if href:
        c = soup.new_tag("p", attrs={"class": "gy-verdict-cta"})
        a = _anchor(soup, href, managed=False)
        a["class"] = "gy-verdict-btn"            # styled as the page's main button
        a.string = f"{text} →"
        c.append(a)
        box.append(c)
    if spec.get("note_html"):
        n = BeautifulSoup(f'<p class="gy-verdict-note">{spec["note_html"]}</p>', "html.parser").p
        box.append(n)
    if href and "stay22.com" in href:                # a hotel verdict
        n = soup.new_tag("p", attrs={"class": "gy-verdict-price"})
        n.string = PRICE_NOTE
        box.append(n)
    return box


# --- "In this guide" ---------------------------------------------------------
TOC_MIN = 5                      # content sections before a page gets a contents list
TOC_SKIP = re.compile(r"^sources|references|liked this guide|keep reading|related reading", re.I)
FAQ_HEADING = re.compile(r"frequently asked", re.I)


def _slug(text: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-")
    if len(s) > 60:
        s = s[:60].rsplit("-", 1)[0]
    return s or "section"


def add_toc(soup: BeautifulSoup, article: Tag) -> int:
    """Contents list for long articles; gives every listed heading an id."""
    heads = [h for h in article.find_all("h2")
             if (h.parent is article and not TOC_SKIP.search(h.get_text(" ", strip=True)))
             or FAQ_HEADING.search(h.get_text(" ", strip=True))]
    if sum(1 for h in heads if not FAQ_HEADING.search(h.get_text(" ", strip=True))) < TOC_MIN:
        return 0
    taken = {t["id"] for t in soup.find_all(id=True)}
    box = soup.new_tag("details", attrs={"class": "gy-toc", "data-aeo": "1"})
    summary = soup.new_tag("summary")
    summary.append("In this guide")
    count = soup.new_tag("span", attrs={"class": "gy-toc-count"})
    count.string = f"{len(heads)} sections"
    summary.append(count)
    box.append(summary)
    ol = soup.new_tag("ol")
    for h in heads:
        if not h.get("id"):
            base = _slug(h.get_text(" ", strip=True))
            cand, n = base, 2
            while cand in taken:
                cand, n = f"{base}-{n}", n + 1
            h["id"] = cand
            taken.add(cand)
        li = soup.new_tag("li")
        a = soup.new_tag("a", attrs={"class": "gy-toc-link", "href": f"#{h['id']}"})
        a.string = " ".join(h.get_text(" ", strip=True).split())
        li.append(a)
        ol.append(li)
    box.append(ol)
    # under the verdict; otherwise under the opening paragraph
    kids = [c for c in article.children if isinstance(c, Tag)]
    anchor = next((c for c in kids if "gy-verdict" in (c.get("class") or [])), None)
    if anchor is None and kids and "article-lede" in (kids[0].get("class") or []):
        anchor = kids[0]
    if anchor is not None:
        anchor.insert_after(box)
    elif kids:
        kids[0].insert_before(box)
    else:
        article.append(box)
    return len(heads)


# --- the promise, where the reader decides ---------------------------------------
# One line under the verdict (or the opening paragraph), linking the promise page.
# Both claims must stay literally true: no brand pays to be included or ranked, and
# the guides say so when a free or cheaper option beats a partner.
PROMISE_TEXT = "No one pays to be recommended here, and we say when a free or cheaper option wins. "
PROMISE_HREF = "/promise.html"


def add_promise(soup: BeautifulSoup, article: Tag) -> None:
    p = soup.new_tag("p", attrs={"class": "gy-promise", "data-aeo": "1"})
    p.append(PROMISE_TEXT)
    a = soup.new_tag("a", attrs={"href": PROMISE_HREF})
    a.string = "Our promise →"
    p.append(a)
    kids = [c for c in article.children if isinstance(c, Tag)]
    anchor = next((c for c in kids if "gy-verdict" in (c.get("class") or [])), None)
    if anchor is None and kids and "article-lede" in (kids[0].get("class") or []):
        anchor = kids[0]
    if anchor is not None:
        anchor.insert_after(p)          # after add_toc, so it lands above the contents list
    elif kids:
        kids[0].insert_before(p)
    else:
        article.append(p)


# --- where to stay: hotel rates and a hotel map (Stay22) --------------------------
def _hotel_items(article: Tag, after_stop: set[int]):
    """(li, name) for each list item that opens with a bold, linked hotel name:
    the guides' "Where to stay in …" lists, where the name links the hotel's site."""
    for li in article.find_all("li"):
        if id(li) in after_stop:
            continue
        first = next((c for c in li.children
                      if not (isinstance(c, NavigableString) and not c.strip())), None)
        if isinstance(first, Tag) and first.name == "strong" and first.find("a", href=True):
            yield li, first.find("a").get_text(" ", strip=True)


def add_stay_links(soup: BeautifulSoup, slug: str, article: Tag) -> tuple[int, list[str]]:
    """"Check rates on Booking.com" after each hotel Booking.com lists — never a near
    match, so stay22.HOTELS was checked by hand — one line before the first list
    saying how those links work, and a hotel map under the "at a glance" table.
    Returns (rates links placed, hotel names stay22.HOTELS doesn't know yet)."""
    page = stay22.PAGES.get(slug)
    if page is None:
        return 0, []
    stop = _stop_heading(article)
    after_stop = {id(stop)} | {id(x) for x in stop.find_all_next()} if stop else set()
    def rates(url: str) -> Tag:
        span = soup.new_tag("span", attrs={"class": "gy-rates", "data-aeo": "1"})
        span.append(" ")
        a = _anchor(soup, stay22.hotel_rates(url), managed=False)
        a.string = f"{stay22.RATES_LABEL} →"
        span.append(a)
        return span

    placed, unknown, first_list = 0, [], None
    for pick in article.select(".gy-pick"):      # "Our pick": <strong>name</strong>: why
        strong = pick.find("strong")
        url = stay22.HOTELS.get(strong.get_text(" ", strip=True)) if strong else None
        if url:
            strong.parent.append(rates(url))
            placed += 1
    for li, name in _hotel_items(article, after_stop):
        if name not in stay22.HOTELS:
            unknown.append(name)
            continue
        if stay22.HOTELS[name] is None:          # not on Booking.com: its own site it is
            continue
        li.append(rates(stay22.HOTELS[name]))
        placed += 1
        if first_list is None:
            first_list = li.parent
    if first_list is not None:
        note = soup.new_tag("p", attrs={"class": "gy-rates-note", "data-aeo": "1"})
        note.string = stay22.RATES_NOTE
        first_list.insert_before(note)

    glance = next((h for h in article.find_all("h2")
                   if "at a glance" in h.get_text(" ", strip=True).lower()), None)
    if glance is not None:
        last = glance                            # the end of that section
        for sib in glance.find_next_siblings():
            if sib.name == "h2" or sib.find("h2") is not None:
                break
            last = sib
        heading, blurb = stay22.map_copy(page["area"])
        box = soup.new_tag("aside", attrs={"class": "gy-widget gy-stay-map", "data-aeo": "1"})
        h = soup.new_tag("h4", attrs={"class": "gy-widget-h"})
        h.string = heading
        b = soup.new_tag("p", attrs={"class": "gy-widget-blurb"})
        b.string = blurb
        frame = soup.new_tag("div", attrs={"class": "gy-widget-frame"})
        frame.append(soup.new_tag("iframe", attrs={
            "loading": "lazy",
            "src": stay22.map_src(page["address"], page["zoom"], f"{slug}_map"),
            "title": f"Map of hotels around {page['area']} with prices, from Stay22"}))
        box.extend([h, b, map_dates_form(soup), frame])
        last.insert_after(box)
    return placed, unknown


def map_dates_form(soup: BeautifulSoup) -> Tag:
    """Dates for the hotel map. With check-in and check-out the map shows live prices
    and availability on its pins; without them it shows typical prices. The first
    booking (Florence, 2026-10-20) was made six days before the stay, so readers who
    know their dates are the ones booking. js/gy-reveal.js reveals the form, fills
    in dates the reader gave on another page, and reloads the map with them."""
    form = soup.new_tag("form", attrs={"class": "gy-map-dates", "hidden": ""})
    def field(label: str, el: Tag) -> Tag:
        lab = soup.new_tag("label")
        span = soup.new_tag("span")
        span.string = label
        lab.extend([span, el])
        return lab
    date_in = soup.new_tag("input", attrs={"type": "date", "name": "in", "required": ""})
    nights = soup.new_tag("select", attrs={"name": "n"})
    for n in range(1, 15):
        o = soup.new_tag("option", attrs={"value": str(n), **({"selected": ""} if n == 3 else {})})
        o.string = str(n)
        nights.append(o)
    guests = soup.new_tag("select", attrs={"name": "a"})
    for n in range(1, 7):
        o = soup.new_tag("option", attrs={"value": str(n), **({"selected": ""} if n == 2 else {})})
        o.string = str(n)
        guests.append(o)
    btn = soup.new_tag("button", attrs={"type": "submit"})
    btn.string = "Show prices for my dates"
    form.extend([field("Check-in", date_in), field("Nights", nights), field("Guests", guests), btn])
    return form


# City pages (first-timers guides, things to do, itineraries, getting around) get
# the same Stay22 hotel map as their city's stay guide. The first booking
# (Florence, 20 Oct 2026) came from a stay guide's map, not from a named hotel:
# readers browse the map and pick their own, so the map earns where hotels
# are on the reader's mind, not only on the stay guide itself.
CITY_MAP_PATTERNS = (r"^(.+)-first-timers-guide$", r"^things-to-do-in-(.+)$", r"^getting-around-(.+)$",
                     r"^(.+)-airport-to-city$", r"^(.+)-itinerary-\d+-days$", r"^(.+)-\d+-day-itinerary$",
                     r"^day-trips-from-(.+)$", r"^first-day-in-(.+)-arrival-plan$")
CITY_MAP_ALIASES = {"hoi-an": "da-nang"}


def city_map_guide(slug: str) -> str | None:
    """The stay guide whose map a city page borrows, or None."""
    for pat in CITY_MAP_PATTERNS:
        m = re.match(pat, slug)
        if m:
            guide = f"where-to-stay-in-{CITY_MAP_ALIASES.get(m.group(1), m.group(1))}"
            return guide if guide in stay22.PAGES and guide != slug else None
    return None


def add_city_map(soup: BeautifulSoup, slug: str, article: Tag, guide: str) -> bool:
    """The hotel map, with a line pointing to the city's stay guide, placed where
    the page talks about where to stay; failing that, at the end of its first
    section. Nothing is added to a page with no h2."""
    page = stay22.PAGES[guide]
    city = guide.removeprefix("where-to-stay-in-").replace("-", " ").title()
    heads = article.find_all("h2")
    if not heads:
        return False
    stay_h = next((h for h in heads if re.search(r"\b(stay|sleep|hotel|base)\b", h.get_text(" ", strip=True), re.I)), None)
    box = soup.new_tag("aside", attrs={"class": "gy-widget gy-stay-map gy-city-map", "data-aeo": "1"})
    h = soup.new_tag("h4", attrs={"class": "gy-widget-h"})
    h.string = f"Hotels around {page['area']}, with prices"
    b = soup.new_tag("p", attrs={"class": "gy-widget-blurb"})
    b.append(f"The map shows the hotels and apartments around {page['area']} that booking sites such as "
             f"Booking.com and Expedia list, with nightly prices. Our guide to ")
    a = soup.new_tag("a", attrs={"href": f"{guide}.html"})
    a.string = f"where to stay in {city}"
    b.append(a)
    b.append(" compares the areas and the hotels we checked. The map comes from our partner Stay22, "
             "which pays us a commission if you book through it.")
    frame = soup.new_tag("div", attrs={"class": "gy-widget-frame"})
    frame.append(soup.new_tag("iframe", attrs={
        "loading": "lazy",
        "src": stay22.map_src(page["address"], page["zoom"], f"{slug}_map"),
        "title": f"Map of hotels around {page['area']} with prices, from Stay22"}))
    box.extend([h, b, map_dates_form(soup), frame])
    if stay_h is not None:
        nxt = stay_h.find_next_sibling()
        (nxt if nxt is not None and nxt.name == "p" else stay_h).insert_after(box)
    elif len(heads) > 1:
        heads[1].insert_before(box)
    else:
        article.append(box)
    return True


def move_map_up(article: Tag) -> None:
    """Put the hotel map straight under the verdict (and its contents list).

    GA4, September 2026: readers of the money pages stayed 2–8 seconds and under
    one in eight reached the end, while the map sat 13–17 phone screens down,
    after the hotel list. Under the verdict it is the second thing they see."""
    box = article.select_one("aside.gy-stay-map")
    if box is None:
        return
    for sel in ("details.gy-toc", "p.gy-promise", "aside.gy-verdict"):
        anchor = article.select_one(sel)
        if anchor is not None and anchor.parent is article:
            anchor.insert_after(box.extract())
            return


# --- three picks under the verdict (stay guides) -----------------------------------
# GA4, Sep 2026: readers of the money pages left within seconds. Three named hotels
# inside the area the verdict recommends, one per budget where the guide has one.
# Every word shown comes from the guide's own at-a-glance table (tier, area, best
# for, and the catch), so the box claims nothing the guide does not.
QUICK_PICKS = {
    "where-to-stay-in-tokyo": ["Park Hyatt Tokyo", "JR Kyushu Hotel Blossom Shinjuku", "sequence MIYASHITA PARK"],
    "where-to-stay-in-kyoto": ["HOTEL THE MITSUI KYOTO", "Mitsui Garden Hotel Kyoto Sanjo PREMIER", "Len Kyoto Kawaramachi"],
    "where-to-stay-in-osaka": ["W Osaka", "Swissôtel Nankai Osaka", "Hotel Hankyu RESPIRE OSAKA"],
    "where-to-stay-in-sydney": ["Sheraton Grand Sydney Hyde Park", "Park Hyatt Sydney", "YHA Sydney Harbour"],
    "where-to-stay-in-melbourne": ["Park Hyatt Melbourne", "QT Melbourne", "The Victoria Hotel"],
    "where-to-stay-in-hakone": ["Gora Kadan", "Hotel Indigo Hakone Gora", "Hakone Tent"],
    "where-to-stay-in-seoul": ["The Westin Josun Seoul", "L7 Myeongdong by Lotte", "Four Points by Sheraton Josun, Seoul Station"],
    "where-to-stay-in-bangkok": ["Hyatt Regency Bangkok Sukhumvit", "Bangkok Marriott Marquis Queen’s Park",
                                 "Holiday Inn Express Bangkok Sukhumvit 11"],
    "where-to-stay-in-hong-kong": ["The Peninsula Hong Kong", "Hotel ICON", "The Salisbury – YMCA of Hong Kong"],
    "where-to-stay-in-kyoto-cherry-blossom": ["The Westin Miyako Kyoto", "Hotel Okura Kyoto Okazaki Bettei",
                                              "Cross Hotel Kyoto"],
    "where-to-stay-in-singapore": ["Marina Bay Sands", "Raffles Singapore", "Pan Pacific Singapore"],
    "where-to-stay-in-taipei": ["Regent Taipei", "Palais de Chine Hotel", "citizenM Taipei North Gate"],
    "where-to-stay-in-kuala-lumpur": ["Mandarin Oriental, Kuala Lumpur", "Traders Hotel, Kuala Lumpur",
                                      "Holiday Inn Express Kuala Lumpur City Centre"],
    "where-to-stay-in-tokyo-cherry-blossom": ["The Gate Hotel Kaminarimon by Hulic", "OMO3 Asakusa by Hoshino Resorts",
                                              "NOHGA HOTEL UENO TOKYO"],
    "where-to-stay-in-sydney-new-years-eve": ["Shangri-La Sydney", "Pullman Quay Grand Sydney Harbour",
                                              "Sheraton Grand Sydney Hyde Park"],
    "where-to-stay-in-sapporo-snow-festival": ["The Royal Park Canvas Sapporo Odori Park", "Sapporo Grand Hotel",
                                               "JR Inn Sapporo-eki Minamiguchi"],
    "where-to-stay-in-niseko": ["Skye Niseko", "Nikko Style Niseko HANAZONO", "Mercure Niseko Resort"],
    "where-to-stay-in-fukuoka": ["Miyako Hotel Hakata", "Hotel Nikko Fukuoka", "JR Kyushu Hotel Blossom Hakata Central"],
    "where-to-stay-in-kyoto-autumn-leaves": ["The Westin Miyako Kyoto", "Hotel Okura Kyoto Okazaki Bettei",
                                             "Cross Hotel Kyoto"],
    "where-to-stay-in-busan": ["Signiel Busan", "Grand Josun Busan", "Shilla Stay Haeundae"],
    "where-to-stay-in-tokyo-autumn-leaves": ["Park Hyatt Tokyo", "JR Kyushu Hotel Blossom Shinjuku",
                                             "Hotel Gracery Shinjuku"],
    "where-to-stay-for-universal-studios-japan": ["The Singulari Hotel & Skyspa at Universal Studios Japan",
                                                  "The Park Front Hotel at Universal Studios Japan",
                                                  "Hotel Universal Port"],
    "where-to-stay-in-hakuba": ["Hakuba Tokyu Hotel", "Hotel Stelle Belle", "Hotel Green Plaza Hakuba"],
    "where-to-stay-in-paris": ["Hôtel National des Arts et Métiers", "Hôtel des Grands Hommes",
                               "Pullman Paris Tour Eiffel"],
    "where-to-stay-in-new-york": ["Arlo Midtown", "Washington Square Hotel", "Ace Hotel Brooklyn"],
    "where-to-stay-in-rovaniemi-christmas": ["Arctic Light Hotel", "Santa's Hotel Rudolf", "Santa's Igloos Arctic Circle"],
    "where-to-stay-in-new-york-new-years-eve": ["New York Marriott Marquis", "The Knickerbocker", "Pod Times Square"],
    "where-to-stay-in-cape-town": ["Cape Grace, A Fairmont Managed Hotel", "Victoria & Alfred Hotel", "The Greenhouse Guesthouse"],
    "where-to-stay-in-queenstown": ["Eichardt's Private Hotel", "Rendezvous Heritage Hotel Queenstown", "Queenstown Park Boutique Hotel"],
    "where-to-stay-in-chicago": ["The Peninsula Chicago", "Palmer House, a Hilton Hotel", "HI Chicago"],
    "where-to-stay-in-boston": ["The Lenox Hotel", "Newbury Guest House", "Fairmont Copley Plaza"],
    "where-to-stay-in-tulum": ["Azulik", "Una Vida", "The Strabon Tulum"],
    "where-to-stay-in-washington-dc": ["Kimpton Hotel Monaco Washington DC", "Moxy Washington, DC Downtown", "Willard InterContinental Washington"],
    "where-to-stay-in-miami": ["The Betsy", "Catalina Hotel & Beach Club", "Faena Hotel Miami Beach"],
    "where-to-stay-in-san-diego": ["Pendry San Diego", "Hotel Republic San Diego, Autograph Collection", "HI San Diego Downtown Hostel"],
    "where-to-stay-in-dubai": ["Armani Hotel Dubai", "Vida Dubai Mall", "Rove Downtown"],
    "where-to-stay-in-orlando": ["Disney's Grand Floridian Resort & Spa", "Drury Plaza Hotel Orlando - Disney Springs Area", "Rosen Inn at Pointe Orlando"],
    "where-to-stay-in-hiroshima": ["Dormy Inn Hiroshima", "Nest Hotel Hiroshima Hatchobori", "Toyoko Inn Hiroshima-eki Shinkansen-guchi No.1"],
    "where-to-stay-in-kanazawa": ["The Hotel Sanraku Kanazawa", "Hotel Intergate Kanazawa", "Hotel Nikko Kanazawa"],
    "where-to-stay-in-jeju": ["Lotte City Hotel Jeju", "Shilla Stay Jeju", "The Shilla Jeju"],
    "where-to-stay-in-okinawa": ["Hotel JAL City Naha", "Hotel Torifito Naha Asahibashi", "The Kitchen Hostel Ao"],
    "where-to-stay-in-marrakech": ["El Fenn", "Les Jardins de la Koutoubia", "Equity Point Marrakech"],
    "where-to-stay-in-shanghai": ["Radisson Blu New World Hotel, Shanghai", "Holiday Inn Shanghai Nanjing Road", "Fairmont Peace Hotel"],
    "where-to-stay-in-dubrovnik": ["Hotel Stari Grad", "Prijeko Palace", "Hotel Lero"],
    "where-to-stay-in-krakow": ["Hotel Stary", "Hotel Pod Różą", "Hotel Europejski"],
    "where-to-stay-in-nice": ["Le Negresco", "Hôtel Palais Saleya", "Hôtel Villa Rivoli"],
    "where-to-stay-in-mexico-city": ["Brick Hotel", "INNSiDE Mexico Roma Norte", "Hotel Gillow"],
    "where-to-stay-in-chiang-mai": ["Rachamankha", "Tamarind Village", "Stamps Backpackers"],
    "where-to-stay-in-cancun": ["Kempinski Hotel Cancún", "Hyatt Ziva Cancun", "Hotel Plaza Caribe"],
    "where-to-stay-in-da-nang": ["HAIAN Beach Hotel & Spa", "Diamond Sea Hotel", "Furama Resort Danang"],
    "where-to-stay-in-phuket": ["Kata Rocks", "Katathani Phuket Beach Resort", "Lub d Phuket Patong"],
    "where-to-stay-in-porto": ["Pestana Vintage Porto", "Grande Hotel do Porto", "Infante Sagres"],
    "where-to-stay-in-san-francisco": ["Fairmont San Francisco", "The Clift Royal Sonesta San Francisco", "Hotel Zeppelin"],
    "where-to-stay-in-las-vegas": ["Bellagio", "The Cosmopolitan of Las Vegas", "SAHARA Las Vegas"],
    "where-to-stay-in-milan": ["Sina The Gray", "Hotel Spadari al Duomo", "Gran Duca di York"],
    "where-to-stay-in-seville": ["EME Catedral Mercer", "Hotel Inglaterra", "Hotel Murillo"],
    "where-to-stay-in-los-angeles": ["Hotel Casa del Mar", "Santa Monica Proper Hotel", "Sea Blue Hotel"],
    "where-to-stay-in-athens": ["Electra Palace Athens", "Hotel Acropolis House", "Marble House Pension"],
    "where-to-stay-in-honolulu": ["Halekulani", "Surfjack Hotel & Swim Club", "Ohia Waikiki Studio Suites"],
    "where-to-stay-in-budapest": ["Gerlóczy Boutique Hotel", "Four Seasons Hotel Gresham Palace Budapest", "Hotel Moments Budapest"],
    "where-to-stay-in-istanbul": ["Four Seasons Hotel Istanbul at Sultanahmet", "Sirkeci Mansion", "Cheers Hostel"],
    "where-to-stay-in-ho-chi-minh-city": ["Caravelle Saigon", "Silverland Ben Thanh Hotel", "Liberty Central Saigon Citypoint"],
    "where-to-stay-in-hanoi": ["La Siesta Classic Ma May", "Sofitel Legend Metropole Hanoi", "Hanoi Backpackers Hostel & Rooftop Bar"],
    "where-to-stay-in-vancouver": ["Fairmont Pacific Rim", "Blue Horizon Hotel", "The Burrard"],
    "where-to-stay-in-montreal": ["Hotel Saint-Sulpice", "Hotel William Gray", "M Montreal"],
    "where-to-stay-in-zurich": ["Hotel Adler Zürich", "Sorell Hotel Seefeld", "Storchen Zürich"],
    "where-to-stay-in-reykjavik": ["Sand Hotel", "Hotel Leifur Eiríksson", "Hotel Borg"],
    "where-to-stay-in-copenhagen": ["Ibsens Hotel", "Hotel Sanders", "Generator Copenhagen"],
    "where-to-stay-in-stockholm": ["Victory Hotel", "Lord Nelson Hotel", "Grand Hôtel Stockholm"],
    "where-to-stay-in-dublin": ["The Morgan Hotel", "Temple Bar Inn", "The Shelbourne"],
    "where-to-stay-in-edinburgh": ["Motel One Edinburgh-Royal", "Radisson Blu Hotel, Edinburgh City Centre", "The Balmoral"],
    "where-to-stay-in-vienna": ["Hotel Kärntnerhof", "Hotel Stefanie", "Hotel Sacher Vienna"],
    "where-to-stay-in-berlin": ["The Circus Hotel", "Hotel Adlon Kempinski Berlin", "Motel One Berlin-Hackescher Markt"],
    "where-to-stay-in-madrid": ["Pestana Collection Plaza Mayor", "Room Mate Alicia", "Four Seasons Hotel Madrid"],
    "where-to-stay-in-bali": ["Lloyd's Inn Bali", "Alaya Resort Ubud", "The Oberoi, Bali"],
    "where-to-stay-in-london": ["Radisson Blu Hotel, London Mercer Street", "hub by Premier Inn London Covent Garden", "The Savoy"],
    "where-to-stay-in-prague": ["Hotel Josef", "Four Seasons Hotel Prague", "Motel One Prague-Florentinum"],
    "where-to-stay-in-venice": ["Hotel Flora", "Londra Palace Venezia", "Hotel La Residenza"],
    "where-to-stay-in-florence": ["Hotel Brunelleschi", "Hotel Pendini", "Portrait Firenze"],
    "where-to-stay-in-barcelona": ["Majestic Hotel & Spa Barcelona", "Casa Bonay", "Hotel Praktik Bakery"],
    "where-to-stay-in-rome": ["Albergo del Senato", "Albergo Santa Chiara", "Hotel Raphaël"],
    "where-to-stay-in-amsterdam": ["Ambassade Hotel", "Pulitzer Amsterdam", "Mr. Jordaan"],
}
QUICK_PICKS_H = "Three to start with"
QUICK_PICKS_NOTE = ("Rates open on Booking.com through our partner Stay22, which pays us a commission "
                    "if you book, at no extra cost to you. The full list, with every area, is below.")


def add_quick_picks(soup: BeautifulSoup, slug: str, article: Tag) -> int:
    glance = next((h for h in article.find_all("h2")
                   if "at a glance" in h.get_text(" ", strip=True).lower()), None)
    table = glance.find_next("table") if glance is not None else None
    if table is None:
        return 0
    heads = [th.get_text(" ", strip=True).lower() for th in table.find_all("th")]
    col = {k: heads.index(k) for k in ("area", "tier", "best for", "watch out for") if k in heads}
    rows = {}
    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all(["td", "th"])
        if cells:
            rows[cells[0].get_text(" ", strip=True)] = [c.get_text(" ", strip=True) for c in cells]
    box = soup.new_tag("aside", attrs={"class": "gy-quick-picks", "data-aeo": "1"})
    h = soup.new_tag("p", attrs={"class": "gy-quick-picks-h"})
    h.string = QUICK_PICKS_H
    ol = soup.new_tag("ol")
    for name in QUICK_PICKS[slug]:
        url = stay22.HOTELS.get(name)
        cells = next((v for k, v in rows.items() if k.startswith(name)), None)
        if not url or cells is None:
            continue
        li = soup.new_tag("li")
        n = soup.new_tag("strong")
        n.string = name
        li.append(n)
        extra = cells[0][len(name):].strip(" ()")     # e.g. "our pick, stayed"
        if extra:
            tag = soup.new_tag("span", attrs={"class": "gy-qp-tag"})
            tag.string = extra
            li.extend([" ", tag])
        meta = soup.new_tag("span", attrs={"class": "gy-qp-meta"})
        meta.string = " · ".join(cells[col[k]] for k in ("tier", "area") if k in col)
        li.append(meta)
        if "best for" in col:
            why = soup.new_tag("span", attrs={"class": "gy-qp-why"})
            why.string = cells[col["best for"]]
            li.append(why)
        if "watch out for" in col:
            w = soup.new_tag("span", attrs={"class": "gy-qp-watch"})
            label = soup.new_tag("b")
            label.string = "Watch out for"
            w.extend([label, " " + cells[col["watch out for"]]])
            li.append(w)
        a = _anchor(soup, stay22.hotel_rates(url), managed=False)
        a["class"] = "gy-qp-rates"
        a.string = "Rates on Booking.com →"   # says where it goes, as the hotel rows do
        li.append(a)
        ol.append(li)
    if not ol.find("li"):
        return 0
    note = soup.new_tag("p", attrs={"class": "gy-quick-picks-note"})
    note.string = QUICK_PICKS_NOTE
    box.extend([h, ol, note])
    for sel in ("p.gy-promise", "aside.gy-verdict"):
        anchor = article.select_one(sel)
        if anchor is not None and anchor.parent is article:
            anchor.insert_after(box)
            return len(ol.find_all("li"))
    return 0


# --- eSIM plans for the trip (country eSIM guides) -------------------------------
# The stay guides' quick picks turn a verdict into three things to click; the eSIM guides
# had a verdict and then prose. Here: for three common trips, each provider's cheapest plan
# that covers it, from the providers' own sites (data/esim_plans.json, ops/esim_prices.py).
# Only the lower price in a row is emphasised. Both brands are partners; neither is favoured.
ESIM_PLANS_JSON = Path(__file__).resolve().parent / "data" / "esim_plans.json"
ESIM_TRIPS = [("A week", 5, 7), ("Two weeks", 10, 15), ("A month", 20, 30)]
ESIM_BRANDS = [("Airalo", "https://airalo.tpx.lu/ctddHmQY"), ("Saily", "https://saily.tpx.lu/hk5XU6Sm")]


@lru_cache(maxsize=1)
def _esim_data() -> dict:
    if not ESIM_PLANS_JSON.exists():
        return {}
    return {c["page"]: c for c in json.loads(ESIM_PLANS_JSON.read_text())["countries"].values()}


@lru_cache(maxsize=1)
def _esim_deep_pages() -> set[str]:
    import importlib.util
    spec = importlib.util.spec_from_file_location("tp_deeplinks", Path(__file__).resolve().parent / "ops" / "tp_deeplinks.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cache = json.loads(mod.CACHE.read_text()) if mod.CACHE.exists() else {}
    return {slug for slug in mod.DEEP if mod.deep_for(slug, cache)}


def _gb(x: float) -> str:
    return f"{x:g} GB"


def add_esim_plans(soup: BeautifulSoup, slug: str, article: Tag) -> int:
    c = _esim_data().get(slug)
    if not c:
        return 0
    box = soup.new_tag("aside", attrs={"class": "gy-esim-plans", "data-aeo": "1"})
    h = soup.new_tag("p", attrs={"class": "gy-esim-plans-h"})
    h.string = f"Plans for your trip to {c['name']}"
    box.append(h)
    wrap = soup.new_tag("div", attrs={"class": "table-scroll"})
    table = soup.new_tag("table")
    head = soup.new_tag("tr")
    for t in ["Your trip"] + [b for b, _ in ESIM_BRANDS]:
        th = soup.new_tag("th", attrs={"scope": "col"})
        th.string = t
        head.append(th)
    thead = soup.new_tag("thead")
    thead.append(head)
    tbody = soup.new_tag("tbody")
    rows = 0
    for label, gb, days in ESIM_TRIPS:
        picks = []
        for brand, _ in ESIM_BRANDS:
            fit = [p for p in c[brand.lower()]["plans"] if p["gb"] >= gb and p["days"] >= days]
            picks.append(min(fit, key=lambda p: (p["usd"], p["gb"])) if fit else None)
        if not any(picks):
            continue
        low = min(p["usd"] for p in picks if p)
        tied = sum(1 for p in picks if p and p["usd"] == low) > 1
        tr = soup.new_tag("tr")
        th = soup.new_tag("th", attrs={"scope": "row"})
        th.append(label)
        th.append(soup.new_tag("br"))
        sub = soup.new_tag("span", attrs={"class": "gy-esim-need"})
        sub.string = f"{_gb(gb)} or more"
        th.append(sub)
        tr.append(th)
        for (brand, href), pk in zip(ESIM_BRANDS, picks):
            td = soup.new_tag("td")
            if pk:
                a = _anchor(soup, href, managed=False)
                a["class"] = "gy-plan-link" + (" is-lower" if pk["usd"] == low and not tied else "")
                price = soup.new_tag("strong" if pk["usd"] == low and not tied else "span", attrs={"class": "gy-plan-price"})
                price.string = f"US${pk['usd']:.2f}"
                spec = soup.new_tag("span", attrs={"class": "gy-plan-spec"})
                spec.string = f"{_gb(pk['gb'])} · {pk['days']} days"
                a.extend([price, spec])
                td.append(a)
            else:
                td.string = "No plan this size"
            tr.append(td)
        tbody.append(tr)
        rows += 1
    if not rows:
        return 0
    table.extend([thead, tbody])
    wrap.append(table)
    box.append(wrap)
    # ops/tp_deeplinks.py later points these links at each provider's page for this country
    deep = slug in _esim_deep_pages()
    btns = soup.new_tag("p", attrs={"class": "gy-esim-plans-btns"})
    for brand, href in ESIM_BRANDS:
        a = _anchor(soup, href, managed=False)
        a["class"] = "gy-plan-btn"
        a.string = f"{brand}’s {c['name'].removeprefix('the ')} plans →" if deep else f"Go to {brand} →"
        btns.append(a)
    box.append(btns)
    entry = min((p for b, _ in ESIM_BRANDS for p in c[b.lower()]["plans"]), key=lambda p: p["usd"])
    entry_brand = next(b for b, _ in ESIM_BRANDS if entry in c[b.lower()]["plans"])
    checked = max(c[b.lower()]["checked"] for b, _ in ESIM_BRANDS)
    note = soup.new_tag("p", attrs={"class": "gy-esim-plans-note"})
    note.string = (f"Each provider’s cheapest plan that covers the trip, from airalo.com and saily.com on "
                   f"{date.fromisoformat(checked).strftime('%-d %b %Y')}, in US dollars; prices change. The smallest "
                   f"plan starts at US${entry['usd']:.2f} ({entry_brand}, {_gb(entry['gb'])} for {entry['days']} days). "
                   + ("The links open each provider’s plans for " + c["name"] + "." if deep else
                      f"The links open each provider’s site, where you pick {c['name']}.") + " Affiliate links: we may earn a "
                   f"commission at no extra cost to you.")
    box.append(note)
    for sel in ("p.gy-promise", "aside.gy-verdict"):
        anchor = article.select_one(sel)
        if anchor is not None and anchor.parent is article:
            anchor.insert_after(box)
            return rows
    return 0


# --- flight fares to the city (stay guides) --------------------------------------
# Aviasales' "prices on map" widget (Travelpayouts promo 4054) centred on the city, from a hub
# the reader picks; gy-reveal.js preselects the hub nearest the reader's time zone and loads
# the widget only when the box comes near the screen. Hidden without JavaScript.
FLIGHT_HUBS = [("LON", "London"), ("NYC", "New York"), ("LAX", "Los Angeles"), ("YTO", "Toronto"),
               ("SYD", "Sydney"), ("SIN", "Singapore"), ("DEL", "Delhi"), ("TYO", "Tokyo")]


def _stay_city(slug: str) -> str:
    for city, guide, _, _ in CITY_RATES.get("hotel-booking-sites-comparison", []):
        if guide == slug:
            return re.sub(r"\s*\(.*\)$", "", city)
    parts = [x.strip() for x in stay22.PAGES[slug]["address"].split(",")]
    return parts[-2] if len(parts) >= 2 else parts[0]


def add_flight_map(soup: BeautifulSoup, slug: str, article: Tag) -> int:
    page = stay22.PAGES.get(slug)
    if not page:
        return 0
    city = _stay_city(slug)
    box = soup.new_tag("aside", attrs={"class": "gy-flightmap", "data-aeo": "1", "hidden": "",
                                       "data-lat": str(page["lat"]), "data-lng": str(page["lng"]),
                                       "data-sub": re.sub(r"[^A-Za-z0-9]+", "_", slug)})
    h = soup.new_tag("p", attrs={"class": "gy-widget-h"})
    h.string = f"Flights to {city}: recent fares"
    blurb = soup.new_tag("p", attrs={"class": "gy-widget-blurb"})
    blurb.string = (f"Round-trip fares from your city to {city} and the places around it, from searches on "
                    "Aviasales. Fares change daily: tap a price for its dates, then check them on Aviasales.")
    hubs = soup.new_tag("div", attrs={"class": "gy-flightmap-from", "role": "group", "aria-label": "Flying from"})
    lab = soup.new_tag("span", attrs={"class": "gy-flightmap-label"})
    lab.string = "From"
    hubs.append(lab)
    for code, name in FLIGHT_HUBS:
        if name == city:
            continue
        b = soup.new_tag("button", attrs={"type": "button", "data-from": code, "aria-pressed": "false"})
        b.string = name
        hubs.append(b)
    frame = soup.new_tag("div", attrs={"class": "gy-flightmap-frame"})
    note = soup.new_tag("p", attrs={"class": "gy-widget-note"})
    note.string = "A partner widget from Aviasales: we may earn a commission if you book."
    box.extend([h, blurb, hubs, frame, note])
    anchor = next((c for c in article.find_all("aside", class_="gy-cta", recursive=False)), None)
    if anchor is None:
        anchor = next((h2 for h2 in article.find_all("h2", recursive=False)
                       if "frequently asked" in h2.get_text(" ", strip=True).lower()), None)
    if anchor is None:
        return 0
    anchor.insert_before(box)
    return 1


# --- hotels by city (the booking-site comparison) ---------------------------------
# Readers reach the comparison from ChatGPT with a trip in mind; most never scroll.
# Under the verdict, one line per city: hotels around a central spot (Stay22 picks
# the booking site) and, where we have one, our guide to the city's areas.
# (city, stay22.PAGES slug or None, area label, address when there is no guide)
CITY_RATES = {
    # Only the first CITY_RATES_FULL rows get a rates link; keep them to the cities most
    # readers plan for: our two most-landed stay guides (Tokyo, Bangkok; GA4 Jul-Oct 2026)
    # and the big cities for the US/UK/Australian/Indian readers ChatGPT sends us.
    # register_stay.py appends new cities at the end, so this order holds.
    "hotel-booking-sites-comparison": [
        ("Tokyo", "where-to-stay-in-tokyo", None, None),
        ("Paris", "where-to-stay-in-paris", None, None),
        ("London", "where-to-stay-in-london", None, None),
        ("New York", "where-to-stay-in-new-york", None, None),
        ("Bangkok", "where-to-stay-in-bangkok", None, None),
        ("Rome", "where-to-stay-in-rome", None, None),
        ("Barcelona", "where-to-stay-in-barcelona", None, None),
        ("Dubai", "where-to-stay-in-dubai", None, None),
        ("Rovaniemi (Christmas)", "where-to-stay-in-rovaniemi-christmas", None, None),
        ("New York (New Year’s Eve)", "where-to-stay-in-new-york-new-years-eve", None, None),
        ("Cape Town", "where-to-stay-in-cape-town", None, None),
        ("Queenstown", "where-to-stay-in-queenstown", None, None),
        ("Chicago", "where-to-stay-in-chicago", None, None),
        ("Boston", "where-to-stay-in-boston", None, None),
        ("Tulum", "where-to-stay-in-tulum", None, None),
        ("Washington, DC", "where-to-stay-in-washington-dc", None, None),
        ("Miami", "where-to-stay-in-miami", None, None),
        ("San Diego", "where-to-stay-in-san-diego", None, None),
        ("Orlando", "where-to-stay-in-orlando", None, None),
        ("Hiroshima", "where-to-stay-in-hiroshima", None, None),
        ("Kanazawa", "where-to-stay-in-kanazawa", None, None),
        ("Jeju", "where-to-stay-in-jeju", None, None),
        ("Okinawa", "where-to-stay-in-okinawa", None, None),
        ("Marrakech", "where-to-stay-in-marrakech", None, None),
        ("Shanghai", "where-to-stay-in-shanghai", None, None),
        ("Dubrovnik", "where-to-stay-in-dubrovnik", None, None),
        ("Kraków", "where-to-stay-in-krakow", None, None),
        ("Nice", "where-to-stay-in-nice", None, None),
        ("Mexico City", "where-to-stay-in-mexico-city", None, None),
        ("Chiang Mai", "where-to-stay-in-chiang-mai", None, None),
        ("Cancún", "where-to-stay-in-cancun", None, None),
        ("Da Nang", "where-to-stay-in-da-nang", None, None),
        ("Phuket", "where-to-stay-in-phuket", None, None),
        ("Porto", "where-to-stay-in-porto", None, None),
        ("San Francisco", "where-to-stay-in-san-francisco", None, None),
        ("Las Vegas", "where-to-stay-in-las-vegas", None, None),
        ("Milan", "where-to-stay-in-milan", None, None),
        ("Seville", "where-to-stay-in-seville", None, None),
        ("Los Angeles", "where-to-stay-in-los-angeles", None, None),
        ("Athens", "where-to-stay-in-athens", None, None),
        ("Honolulu", "where-to-stay-in-honolulu", None, None),
        ("Budapest", "where-to-stay-in-budapest", None, None),
        ("Istanbul", "where-to-stay-in-istanbul", None, None),
        ("Ho Chi Minh City", "where-to-stay-in-ho-chi-minh-city", None, None),
        ("Hanoi", "where-to-stay-in-hanoi", None, None),
        ("Vancouver", "where-to-stay-in-vancouver", None, None),
        ("Montreal", "where-to-stay-in-montreal", None, None),
        ("Zurich", "where-to-stay-in-zurich", None, None),
        ("Reykjavik", "where-to-stay-in-reykjavik", None, None),
        ("Copenhagen", "where-to-stay-in-copenhagen", None, None),
        ("Stockholm", "where-to-stay-in-stockholm", None, None),
        ("Dublin", "where-to-stay-in-dublin", None, None),
        ("Edinburgh", "where-to-stay-in-edinburgh", None, None),
        ("Vienna", "where-to-stay-in-vienna", None, None),
        ("Berlin", "where-to-stay-in-berlin", None, None),
        ("Madrid", "where-to-stay-in-madrid", None, None),
        ("Bali", "where-to-stay-in-bali", None, None),
        ("Prague", "where-to-stay-in-prague", None, None),
        ("Venice", "where-to-stay-in-venice", None, None),
        ("Florence", "where-to-stay-in-florence", None, None),
        ("Amsterdam", "where-to-stay-in-amsterdam", None, None),
        ("Seoul", "where-to-stay-in-seoul", None, None),
        ("Singapore", "where-to-stay-in-singapore", None, None),
        ("Hong Kong", "where-to-stay-in-hong-kong", None, None),
        ("Kyoto", "where-to-stay-in-kyoto", None, None),
        ("Osaka", "where-to-stay-in-osaka", None, None),
        ("Sydney", "where-to-stay-in-sydney", None, None),
        ("Taipei", "where-to-stay-in-taipei", None, None),
        ("Kuala Lumpur", "where-to-stay-in-kuala-lumpur", None, None),
        ("Melbourne", "where-to-stay-in-melbourne", None, None),
        ("Hakone", "where-to-stay-in-hakone", None, None),
        ("Fukuoka", "where-to-stay-in-fukuoka", None, None),
        ("Busan", "where-to-stay-in-busan", None, None),
    ],
}
CITY_RATES_FULL = 8          # cities with a rates line; the rest share one line of guide links
CITY_RATES_MORE = "More city guides:"
CITY_RATES_H = "Looking for a hotel now?"
CITY_RATES_BLURB = ("Pick the city. The first link opens the hotels around a central spot on a booking "
                    "site chosen by our partner Stay22, which pays us a commission if you book through "
                    "it. Where we have a guide to the city’s areas, the second link opens it.")


def add_city_rates(soup: BeautifulSoup, slug: str, article: Tag) -> int:
    box = soup.new_tag("aside", attrs={"class": "gy-city-rates", "data-aeo": "1"})
    h = soup.new_tag("h4", attrs={"class": "gy-widget-h"})
    h.string = CITY_RATES_H
    b = soup.new_tag("p", attrs={"class": "gy-city-rates-blurb"})
    b.string = CITY_RATES_BLURB
    ul = soup.new_tag("ul", attrs={"class": "gy-city-rates-list"})
    rows = CITY_RATES[slug]
    # On a phone each city takes two lines; past the first eight the list pushed the
    # article down by over a thousand pixels, so the rest share one line of guide links.
    for city, guide, area, address in rows[:CITY_RATES_FULL]:
        if guide:
            page = stay22.PAGES[guide]
            href, area = stay22.area_rates(page["lat"], page["lng"]), page["area"]
        else:
            href = stay22.allez("roam", address=address)
        li = soup.new_tag("li")
        name = soup.new_tag("strong")
        name.string = city
        a = _anchor(soup, href, managed=False)
        a.string = f"Hotels around {area} →"
        li.extend([name, " ", a])
        if guide:
            g = soup.new_tag("a", attrs={"href": f"{guide}.html"})
            g.string = "our area guide"
            li.extend([" · ", g])
        ul.append(li)
    box.extend([h, b, ul])
    more = [(city, guide) for city, guide, _, _ in rows[CITY_RATES_FULL:] if guide]
    if more:
        line = soup.new_tag("p", attrs={"class": "gy-city-rates-blurb"})
        line.append(CITY_RATES_MORE + " ")
        for i, (city, guide) in enumerate(more):
            if i:
                line.append(" · ")
            g = soup.new_tag("a", attrs={"href": f"{guide}.html"})
            g.string = city
            line.append(g)
        box.append(line)
    for sel in ("p.gy-promise", "aside.gy-verdict"):     # above the contents list: in the first screen
        anchor = article.select_one(sel)
        if anchor is not None and anchor.parent is article:
            anchor.insert_after(box)
            return len(rows)
    return 0


# --- "for your trip" pickers --------------------------------------------------------
# The broad comparisons ChatGPT sends readers to answer "which platform", not "for my
# trip", and those readers leave within seconds (GA4, Sep-Oct 2026: 6-15 s, almost no
# clicks). One line under the verdict sends each to the page for their own trip.
# slug -> (label, lead, [(link text, href)])
PICKERS = {
    "klook-vs-viator-vs-getyourguide": ("For your trip", "Booking one tour? We compared the platforms for each:", [
        ("Tokyo food tours", "where-to-book-tokyo-food-tour.html"),
        ("Mount Fuji day tours", "where-to-book-mount-fuji-day-tour.html"),
        ("Seoul DMZ tours", "where-to-book-seoul-dmz-tour.html"),
        ("Jeju bus tours", "where-to-book-jeju-bus-tour.html"),
        ("Taipei day tours", "where-to-book-taipei-day-tour.html"),
        ("Bangkok dinner cruises", "where-to-book-bangkok-dinner-cruise.html"),
        ("Halong Bay cruises", "where-to-book-halong-bay-cruise.html"),
        ("Sydney harbour cruises", "where-to-book-sydney-harbour-cruise.html"),
    ]),
    "best-travel-esim-2026": ("For your trip", "Going to one country? Our pick for each:", [
        ("Japan", "best-esim-japan-2026.html"),
        ("South Korea", "best-esim-south-korea-2026.html"),
        ("Taiwan", "best-esim-taiwan-2026.html"),
        ("Thailand", "best-esim-thailand-2026.html"),
        ("Vietnam", "best-esim-vietnam-2026.html"),
        ("Australia", "best-esim-australia-2026.html"),
        ("Europe", "best-esim-europe-2026.html"),
        ("the USA", "best-esim-usa-2026.html"),
    ]),
}


def add_picker(soup: BeautifulSoup, slug: str, article: Tag) -> bool:
    label, lead, links = PICKERS[slug]
    line = soup.new_tag("p", attrs={"class": "gy-picker", "data-aeo": "1", "data-label": label})
    line.append(lead + " ")
    for i, (text, href) in enumerate(links):
        if i:
            line.append(" · ")
        a = soup.new_tag("a", attrs={"href": href})
        a.string = text
        line.append(a)
    for sel in ("p.gy-promise", "aside.gy-verdict"):
        anchor = article.select_one(sel)
        if anchor is not None and anchor.parent is article:
            anchor.insert_after(line)
            return True
    return False


# --- "where to stay" pointers ------------------------------------------------------
# A reader on a related guide, sent to the part of a stay guide that answers their
# next question: the Shinjuku walk to where to sleep in Shinjuku, the SkyBus to why
# the CBD. slug -> (where, html). where is "intro" (after the opening matter) or a
# regex for the heading whose first paragraph the line follows. Every clause must
# be true of the guide it points to: only the Tokyo guide gives each hotel a catch.
_T, _K, _O = "where-to-stay-in-tokyo.html", "where-to-stay-in-kyoto.html", "where-to-stay-in-osaka.html"
_S, _M = "where-to-stay-in-sydney.html", "where-to-stay-in-melbourne.html"
_JP3 = (f'<a href="{_T}">Tokyo</a>, <a href="{_K}">Kyoto</a> and <a href="{_O}">Osaka</a>')
_JP = "where-to-stay-in-japan.html"
_H = "where-to-stay-in-hakone.html"
_SE = "where-to-stay-in-seoul.html"
_BK = "where-to-stay-in-bangkok.html"
_HK = "where-to-stay-in-hong-kong.html"
_SG = "where-to-stay-in-singapore.html"
_TP = "where-to-stay-in-taipei.html"
_KL = "where-to-stay-in-kuala-lumpur.html"
_TS = "where-to-stay-in-tokyo-cherry-blossom.html"
_NY = "where-to-stay-in-sydney-new-years-eve.html"
_SP = "where-to-stay-in-sapporo-snow-festival.html"
_NS = "where-to-stay-in-niseko.html"
_FK = "where-to-stay-in-fukuoka.html"
_KA = "where-to-stay-in-kyoto-autumn-leaves.html"
_BS = "where-to-stay-in-busan.html"
_TA = "where-to-stay-in-tokyo-autumn-leaves.html"
_US = "where-to-stay-for-universal-studios-japan.html"
_HB = "where-to-stay-in-hakuba.html"
_PA = "where-to-stay-in-paris.html"
_NYC = "where-to-stay-in-new-york.html"
STAY_POINTERS = {
    # Kuala Lumpur
    "kuala-lumpur-first-timers-guide": ("Getting Your Bearings",
        f'Choosing a base? <a href="{_KL}">Where to stay in Kuala Lumpur</a> compares four areas, from KLCC to '
        'KL Sentral, and names 12 hotels, with the catch for each.'),
    "things-to-do-in-kuala-lumpur": ("The Petronas Towers",
        f'To have the towers at your door, <a href="{_KL}#klcc-the-first-trip-base">stay in KLCC</a>: our guide '
        'names four hotels there, from the Mandarin Oriental beside the towers to Traders on KLCC Park.'),
    # Taipei
    "taipei-first-timers-guide": ("where to base yourself",
        f'For the hotels, <a href="{_TP}">where to stay in Taipei</a> compares five areas, from Taipei Main '
        'Station to the hot springs of Beitou, and names 12 hotels, with the catch for each.'),
    "things-to-do-in-taipei": ("Green edges",
        f'To sleep by the springs, <a href="{_TP}#beitou-a-night-in-the-hot-springs">stay a night in Beitou</a>: '
        'our guide names two hotels with a hot-spring bath in every room.'),
    "where-to-book-taipei-day-tour": ("intro",
        f'Still choosing a base? <a href="{_TP}">Where to stay in Taipei</a> compares five areas and names 12 '
        'hotels, from Taipei Main Station to Beitou.'),
    # Singapore
    "singapore-first-timers-guide": ("Thoughtful Stays",
        f'Choosing a base? <a href="{_SG}">Where to stay in Singapore</a> compares five areas, from Marina Bay '
        'to Sentosa, and names 12 hotels, with the catch for each.'),
    "things-to-do-in-singapore": ("Marina Bay and Gardens by the Bay",
        f'To have the Bay on foot, <a href="{_SG}#marina-bay-and-the-civic-district-the-first-trip-base">stay '
        'around Marina Bay and the Civic District</a>: our guide names three hotels there, from Raffles, open '
        'since 1887, to Pan Pacific Singapore at Marina Square.'),
    # Hong Kong
    "hong-kong-first-timers-guide": ("The lie of the land",
        f'Choosing a side? <a href="{_HK}">Where to stay in Hong Kong</a> compares five areas on both sides '
        'of the harbour and names 12 hotels, with the catch for each.'),
    "things-to-do-in-hong-kong": ("The harbour and the Star Ferry",
        f'To have the Star Ferry at the end of your street, <a href="{_HK}#tsim-sha-tsui-the-first-trip-base">'
        'stay in Tsim Sha Tsui</a>: our guide names three hotels there, from The Peninsula of 1928 to the '
        'YMCA’s Salisbury on the same road.'),
    "hong-kong-harbour-cruises-guide": ("Practical notes",
        f'Staying near the piers? <a href="{_HK}#tsim-sha-tsui-the-first-trip-base">Where to stay in Tsim Sha '
        'Tsui</a> names three hotels there, two of them on Salisbury Road, a short walk from the Star Ferry.'),
    # Bangkok
    "bangkok-first-timers-guide": ("Finding Your Pace",
        f'Choosing a base? <a href="{_BK}">Where to stay in Bangkok</a> compares five areas, from Sukhumvit to '
        'the Old Town, and names 12 hotels, with the catch for each.'),
    "things-to-do-in-bangkok": ("The Grand Palace and Wat Phra Kaew",
        f'To be at the gates when they open, <a href="{_BK}#the-old-town-the-grand-palace-on-foot">stay in the '
        'Old Town</a>: our guide names two hotels there, each within a short walk of Khao San Road.'),
    "bangkok-river-cruises-guide": ("Where you board",
        f'Staying by the river? <a href="{_BK}#the-riverside-grand-hotels-and-boats-to-the-temples">Where to stay '
        'on the Riverside</a> names three hotels there, two of them with their own boats to Sathorn Pier, beside '
        'Saphan Taksin station.'),
    "where-to-book-bangkok-dinner-cruise": ("intro",
        f'Still choosing where to sleep? <a href="{_BK}">Where to stay in Bangkok</a> compares five areas and '
        'names 12 hotels, from the Mandarin Oriental, which opened in 1876, to a small hotel on the Bang Lamphu '
        'canal.'),
    # Tokyo
    "shinjuku-neighbourhood-guide": ("The station at the centre",
        f'Sleeping in Shinjuku? <a href="{_T}#shinjuku-the-all-hours-hub">Where to stay in Shinjuku</a> '
        'compares the quieter south and west sides of the station with Kabukichō and names three hotels, '
        'with the catch for each.'),
    "first-day-in-tokyo-arrival-plan": ("Settling In",
        f'Still choosing where to sleep? <a href="{_T}">Where to stay in Tokyo</a> starts with the station, '
        'then names 17 hotels in six areas, from Park Hyatt Tokyo to a family-run ryokan.'),
    "narita-haneda-to-central-tokyo": ("Choosing Your Route",
        f'The station your hotel is on decides which airport route is easiest. <a href="{_T}">Where to stay '
        'in Tokyo</a> compares six areas by the stations they sit on and names 17 hotels.'),
    "day-trips-from-tokyo": ("Hakone",
        f'Staying the night instead? <a href="{_H}">Where to stay in Hakone</a> compares five areas and names '
        '12 ryokan and hotels, from a hostel by Gora Station to the Fujiya Hotel, with which have a private '
        'open-air bath.'),
    "things-to-do-in-tokyo": ("intro",
        f'Where you sleep shapes these days as much as what you book. <a href="{_T}">Where to stay in Tokyo</a> '
        f'compares six areas, from Shinjuku to Asakusa, and names 17 hotels; our guides to <a href="{_TS}">the '
        f'cherry blossom</a> and <a href="{_TA}">the autumn leaves</a> match the areas to the seasons.'),
    "tokyo-itinerary-5-days": ("Getting Settled",
        f'Choosing a base for these five days? <a href="{_T}">Where to stay in Tokyo</a> compares six areas, '
        'including Asakusa, Ueno and Shinjuku, and names 17 hotels.'),
    "luggage-storage-tokyo": ("Hotel Front Desks",
        f'Still choosing a hotel? <a href="{_T}">Where to stay in Tokyo</a> names 17 by area and price, with '
        'the catch for each.'),
    "how-much-does-japan-cost": ("Where money actually changes",
        f'Pricing the beds? <a href="{_T}#all-17-at-a-glance">Where to stay in Tokyo</a> ranks 17 hotels by '
        f'price tier, and <a href="{_K}">our Kyoto guide</a> includes the ryokan Tawaraya and Hiiragiya.'),
    # Japan, all three cities
    "japan-7-day-itinerary": ("Before you land",
        f'Where to sleep on this route: <a href="{_JP}">how to split the nights</a>, then our guides to {_JP3}, '
        'which compare the areas and name the hotels.'),
    "carry-on-packing-list-10-day-japan": ("The Carry-On and Personal Item",
        f'Carrying everything between cities? Our where-to-stay guides for {_JP3} start with the station, so '
        'the walk with your bag stays short.'),
    "best-time-to-visit-japan-2026": ("The dates to plan around",
        f'Travelling in a peak week? Book the room first: <a href="{_JP}">where to stay in Japan on a first trip</a> '
        f'splits the nights, our guides to {_JP3} name the hotels, and our cherry-blossom guides to <a '
        f'href="{_TS}">Tokyo</a> and <a href="where-to-stay-in-kyoto-cherry-blossom.html">Kyoto</a> have the '
        f'dates and the areas by blossom, as <a href="{_SP}">our Sapporo Snow Festival guide</a> does for February '
        f'and our guides to <a href="{_NS}">Niseko</a> and <a href="{_HB}">Hakuba</a> do for the ski season.'),
    "japan-autumn-2026": ("Flights and Stays",
        f'For where to sleep, <a href="{_JP}">where to stay in Japan on a first trip</a> splits the nights between '
        f'cities, and our guides to {_JP3} name the hotels. For late November, our autumn-leaves guides to <a '
        f'href="{_KA}">Kyoto</a> and <a href="{_TA}">Tokyo</a> have the 2026 openings and fees.'),
    "japan-book-in-advance-2026": ("Authentic Stays",
        f'For named ryokan in Kyoto, including Tawaraya and Hiiragiya, see <a href="{_K}">Where to stay in '
        'Kyoto</a>.'),
    "where-to-stay-in-kyoto-autumn-leaves": ("intro",
        f'Starting in Tokyo? <a href="{_TA}">Where to stay in Tokyo for the autumn leaves</a> matches four areas '
        "to the ginkgo avenue and the gardens, with Rikugien's 2026 evening opening."),
    "where-to-stay-in-seoul": ("intro",
        f'Going on to Busan? <a href="{_BS}">Where to stay in Busan</a> compares Haeundae, Gwangalli, Seomyeon '
        'and Busan Station, and names nine hotels.'),
    "where-to-stay-in-japan": ("When to book",
        f'Booking Fukuoka for a stay by 15 December? <a href="{_FK}#the-kyushu-recovery-discount-to-15-december-2026">'
        'Our Fukuoka guide</a> explains the Kyushu recovery discount, half off on the Japanese booking sites in '
        'the campaign, and names 11 hotels.'),
    "japan-tourist-taxes-2026": ("Kyoto’s new lodging tax",
        f'Choosing where to stay in Kyoto? <a href="{_K}">Our Kyoto guide</a> compares five areas and names '
        f'14 hotels and ryokan. Going to Sapporo? <a href="{_SP}">Our Snow Festival guide</a> covers its new tax.'),
    # the three Japan city guides, back to the trip-level question
    "where-to-stay-in-tokyo": ("intro",
        f'Splitting the trip between cities? <a href="{_JP}">Where to stay in Japan on a first trip</a> covers '
        'how many nights to give Tokyo, Kyoto and Osaka, and moving day in between. Coming for the cherry '
        f'blossom? <a href="{_TS}">Our cherry-blossom guide</a> has the dates and the tax change on 1 April 2027; '
        f'for late November, <a href="{_TA}">our autumn-leaves guide</a> has the 2026 garden openings.'),
    "where-to-stay-in-kyoto": ("intro",
        f'Coming from Tokyo? <a href="{_JP}">Where to stay in Japan on a first trip</a> covers how many nights to '
        'give each city, and how to move your bags between them. Here for the autumn leaves? <a '
        f'href="{_KA}">Our autumn-leaves guide</a> has the 2026 temple openings and the weeks to aim for.'),
    "where-to-stay-in-osaka": ("intro",
        f'Kyoto, Osaka, or both? <a href="{_JP}">Where to stay in Japan on a first trip</a> covers how many nights '
        f'to give each, and moving day from Tokyo. Here for Universal Studios Japan? <a href="{_US}">Our park '
        'guide</a> compares the seven official hotels with bases in town, and has the New Year countdown.'),
    # Kyoto
    "gion-kyoto-neighbourhood-guide": ("Getting there, and fitting it in",
        f'Staying close by? <a href="{_K}#gion-and-higashiyama-the-old-city-early-and-late">Where to stay in '
        'Gion and Higashiyama</a> names three hotels in this part of Kyoto.'),
    "three-slow-days-in-kyoto": ("Moving Gently",
        f'Where to base yourself for these three days: <a href="{_K}">Where to stay in Kyoto</a> compares '
        'downtown, Kyoto Station, Gion, Arashiyama and the northern hills.'),
    "kyoto-autumn-2026": ("Accommodation and Mobility",
        f'For the leaf season itself, <a href="{_KA}">where to stay in Kyoto for the autumn leaves</a> has the 2026 '
        f'openings and fees at Eikan-do, Tofuku-ji and Kodai-ji, and names 12 hotels by area; <a href="{_K}">where to '
        'stay in Kyoto</a> compares five areas the year round.'),
    "tokyo-to-kyoto-shinkansen-vs-flight-vs-bus": ("What This Means",
        f'Arriving by Shinkansen? <a href="{_K}#kyoto-station-the-transport-base">Where to stay in Kyoto</a> '
        'explains when a hotel at the station beats one downtown.'),
    "things-to-do-in-kyoto": ("intro",
        f'Where you stay decides which of these you can walk to early, before the crowds. <a href="{_K}">Where '
        'to stay in Kyoto</a> compares five areas, from downtown to Arashiyama, and our guides to <a '
        'href="where-to-stay-in-kyoto-cherry-blossom.html">the cherry blossom</a> and <a '
        f'href="{_KA}">the autumn leaves</a> match them to the seasons.'),
    # Osaka
    "osaka-first-timers-guide": ("intro",
        f'Minami or Kita? <a href="{_O}">Where to stay in Osaka</a> compares Namba and Umeda with three other '
        'areas and names 10 hotels.'),
    "osaka-3-day-guide": ("intro",
        f'Choosing a base for these three days? <a href="{_O}">Where to stay in Osaka</a> compares Namba, '
        'Umeda, Nakanoshima, Tennoji and the bay, and names 10 hotels.'),
    "things-to-do-in-osaka": ("intro",
        f'<a href="{_O}">Where to stay in Osaka</a> compares five areas, from Namba’s food streets to the bay by '
        f'Universal Studios Japan, and names 10 hotels; for the park itself, <a href="{_US}">where to stay for '
        'Universal Studios Japan</a> names the seven official hotels.'),
    "osaka-or-kyoto-where-to-base": ("Accommodation and Pace",
        f'Once you’ve chosen: <a href="{_O}">Where to stay in Osaka</a> and <a href="{_K}">Where to stay in '
        'Kyoto</a> compare the areas and name the hotels.'),
    # Seoul
    "seoul-first-timers-guide": ("Neighbourhoods, each with a mood",
        f'Choosing where to sleep? <a href="{_SE}">Where to stay in Seoul</a> compares five areas, from Myeongdong '
        'to Gangnam, and names 12 hotels.'),
    "things-to-do-in-seoul": ("Myeongdong, Insadong",
        f'Staying in one of these? <a href="{_SE}">Where to stay in Seoul</a> compares them as bases and names 12 '
        'hotels, including a hanok in Bukchon.'),
    "how-much-does-south-korea-cost": ("Accommodation",
        f'Pricing the beds in Seoul? <a href="{_SE}">Where to stay in Seoul</a> names 12 hotels by area, from a '
        'mid-range base in Myeongdong to Signiel on the 76th floor and up. For Busan, <a '
        f'href="{_BS}">where to stay in Busan</a> names nine, from Haeundae to Busan Station.'),
    "korail-pass-worth-it-2026": ("How to decide",
        f'Catching an early KTX? <a href="{_SE}#seoul-station-and-itaewon-trains-then-dinner">Where to stay in '
        'Seoul</a> names a hotel linked to Seoul Station by an underground passage. Arriving in Busan? <a '
        f'href="{_BS}#busan-station-the-ktx-and-the-old-port">Where to stay in Busan</a> names a hotel a minute from the KTX.'),
    # Melbourne
    "melbourne-airport-to-city": ("The SkyBus",
        f'Southern Cross sits on the edge of the CBD. <a href="{_M}#the-cbd-the-grid-the-'
        'laneways-and-free-trams">Where to stay in Melbourne</a> explains why the CBD, inside the Free Tram '
        'Zone, suits a first trip.'),
    "melbourne-first-timers-guide": ("The shape of the city",
        f'<a href="{_M}">Where to stay in Melbourne</a> compares the CBD, Southbank, Fitzroy, St Kilda and '
        'South Yarra and names 12 hotels.'),
    "getting-around-melbourne": ("The Free Tram Zone",
        f'<a href="{_M}">Where to stay in Melbourne</a> names hotels inside the Free Tram Zone and beyond it.'),
    "things-to-do-in-melbourne": ("intro",
        f'<a href="{_M}">Where to stay in Melbourne</a> compares five areas, from the CBD to St Kilda, and '
        'names 12 hotels.'),
    # Sydney
    "sydney-first-timers-guide": ("intro",
        f'<a href="{_S}">Where to stay in Sydney</a> compares six areas and names 13 hotels, including the '
        'Sheraton Grand Sydney Hyde Park, where one of us stayed in September 2026.'),
    "getting-around-sydney": ("A simple mental model",
        f'<a href="{_S}">Where to stay in Sydney</a> compares six areas, with how you get around from each.'),
    "things-to-do-in-sydney": ("intro",
        f'<a href="{_S}">Where to stay in Sydney</a> compares six areas, from Circular Quay to Bondi and '
        f'Manly, and names 13 hotels. Here for New Year\'s Eve? <a href="{_NY}">Our New Year\'s Eve guide</a> '
        'matches four areas to the fireworks.'),
    "where-to-stay-in-sapporo-snow-festival": ("intro",
        f'Skiing too? <a href="{_NS}">Where to stay in Niseko</a> compares the four resorts and Kutchan town, '
        f'with the 2026/27 season and lift prices; for Nagano, <a href="{_HB}">our Hakuba guide</a> does the same.'),
    "where-to-stay-in-niseko": ("intro",
        f'Skiing in Nagano instead? <a href="{_HB}">Where to stay in Hakuba</a> compares six areas, from Happo to '
        'Cortina, with the 2026/27 season, the lift pass and the hotel tax that began in June 2026.'),
    "best-esim-europe-2026": ("intro",
        f'Starting in Paris? <a href="{_PA}">Where to stay in Paris</a> compares seven areas, from the Marais to '
        'Montmartre, with the 2026 hotel tax and the airport train that opens in March 2027.'),
    # Pages Google already indexes and shows (GSC, Oct 2026) pointing to stay guides it has not indexed yet
    "travel-insurance-japan": ("intro",
        f'Planning where to sleep, too? <a href="{_JP}">Where to stay in Japan</a> splits a first trip of seven to '
        'ten days between Tokyo and Kyoto or Osaka, with the lodging tax each city adds and when to book.'),
    "carry-on-packing-list-10-day-japan": ("intro",
        f'Packing for ten days usually means two bases. <a href="{_JP}">Where to stay in Japan</a> splits the '
        'trip between Tokyo and Kyoto or Osaka, with the lodging tax each city adds and when to book.'),
    "best-esim-japan-2026": ("intro",
        f'Still choosing a base? <a href="{_T}">Where to stay in Tokyo</a> starts with the station, then compares '
        'six neighbourhoods, from Shinjuku to Asakusa, and 17 hotels.'),
    "suica-pasmo-ic-cards-guide": ("intro",
        f'Tapping in every day? <a href="{_T}">Where to stay in Tokyo</a> picks the station before the hotel, '
        'then compares six neighbourhoods, from Shinjuku to Ueno, and 17 hotels.'),
    "best-esim-south-korea-2026": ("intro",
        f'Choosing a base in Seoul? <a href="{_SE}">Where to stay in Seoul</a> compares five areas, from Myeongdong '
        'to Gangnam, and 12 hotels, with the airport train from Hongdae and Seoul Station.'),
    "best-esim-thailand-2026": ("intro",
        f'Landing in Bangkok? <a href="{_BK}">Where to stay in Bangkok</a> compares five areas, from Sukhumvit to '
        'the Riverside and the Old Town, and names 12 hotels.'),
    "best-esim-usa-2026": ("intro",
        f'Flying into New York? <a href="{_NYC}">Where to stay in New York</a> compares six areas, from Midtown '
        'to Brooklyn, with the 14.75% hotel tax and the free bus from LaGuardia.'),
    "europe-rail-pass-worth-it-2026": ("intro",
        f'Beginning or ending in Paris? <a href="{_PA}">Where to stay in Paris</a> compares seven areas and names '
        '15 hotels, from the Gare de l\'Est, where the CDG Express starts in March 2027, to the Latin Quarter.'),
    "where-to-stay-in-sydney": ("intro",
        f'Coming for New Year\'s Eve? <a href="{_NY}">Where to stay in Sydney for New Year\'s Eve</a> has the '
        'vantage points, their ticket dates and the hotels with harbour rooms.'),
    "where-to-book-sydney-harbour-cruise": ("intro",
        f'Here for New Year\'s Eve? <a href="{_NY}">Where to stay in Sydney for New Year\'s Eve</a> has the '
        'vantage points, their ticket dates and the hotels that face the Bridge.'),
    "sydney-harbour-cruises-guide": ("Practical notes",
        f'Staying near a departure point? <a href="{_S}">Where to stay in Sydney</a> compares Circular Quay '
        f'and Darling Harbour as bases, and <a href="{_NY}">our New Year\'s Eve guide</a> names the hotels '
        'with harbour rooms facing the Bridge.'),
    # both
    "best-time-to-visit-australia": ("The south: Sydney",
        f'Once you have dates: <a href="{_S}">where to stay in Sydney</a> and <a href="{_M}">in Melbourne</a>, '
        f'area by area, and <a href="{_NY}">Sydney on New Year\'s Eve</a>, with the minimum stays to watch for.'),
}


def add_stay_pointer(soup: BeautifulSoup, slug: str, article: Tag) -> bool:
    """Place the slug's one-line pointer. False when its anchor is missing, so a
    renamed heading shows up in the report instead of the line silently vanishing."""
    if slug not in STAY_POINTERS:
        return False
    where, body = STAY_POINTERS[slug]
    line = BeautifulSoup(f'<p class="gy-stay-pointer" data-aeo="1">{body}</p>', "html.parser").p
    if where == "intro":
        kids = [c for c in article.children if isinstance(c, Tag)]
        first = next((c for c in kids if c.name == "p" and not c.has_attr("data-aeo")
                      and len(c.get_text(strip=True)) > 60), None)
        if first is None:
            return False
        anchor = first
        for sib in first.find_next_siblings():      # past the promise line and contents list
            if not sib.has_attr("data-aeo"):
                break
            anchor = sib
    else:
        head = next((h for h in article.find_all(["h2", "h3"])
                     if re.search(where, h.get_text(" ", strip=True), re.I)), None)
        if head is None:
            return False
        anchor = head
        for sib in head.find_next_siblings():
            if sib.name in ("h2", "h3"):
                break
            if sib.name == "p" and not sib.has_attr("data-aeo") and len(sib.get_text(strip=True)) > 40:
                anchor = sib
                break
    anchor.insert_after(line)
    return True


def strip_managed(soup: BeautifulSoup) -> None:
    for el in soup.select("[data-aeo]"):
        if el.name == "a":
            el.unwrap()
        else:
            el.decompose()


def apply(soup: BeautifulSoup, rel: str, *, modified: str | None = None) -> dict:
    """Apply the whole AEO layer to one parsed article. Returns what it did."""
    slug = Path(rel).stem
    strip_managed(soup)
    apply_dates(soup, rel, modified=modified or REVISED.get(slug))
    out = {"verdict": False, "links": 0, "toc": 0, "rates": 0, "unknown_hotels": []}
    spec = V.get(slug)
    article = soup.select_one("section.article")
    if spec and article is not None:
        if spec.get("replace"):
            for old in article.select(spec["replace"]):
                nxt = old.next_sibling           # don't leave a blank line behind
                if isinstance(nxt, NavigableString) and not nxt.strip():
                    nxt.extract()
                old.decompose()
        first = next((c for c in article.children if isinstance(c, Tag)), None)
        box = render_verdict(soup, spec, slug)
        if first is not None:
            first.insert_before(box)
        else:
            article.append(box)
        out["verdict"] = True
        out["links"] = link_brands(soup, slug)
    if article is not None and slug in stay22.PAGES:
        out["rates"], out["unknown_hotels"] = add_stay_links(soup, slug, article)
    elif article is not None and city_map_guide(slug):
        out["city_map"] = add_city_map(soup, slug, article, city_map_guide(slug))
    if article is not None:
        out["toc"] = add_toc(soup, article)
        add_promise(soup, article)
        if slug in stay22.PAGES:
            move_map_up(article)
        if slug in QUICK_PICKS:
            out["quick_picks"] = add_quick_picks(soup, slug, article)
        if slug in CITY_RATES:
            out["city_rates"] = add_city_rates(soup, slug, article)
        out["esim_plans"] = add_esim_plans(soup, slug, article)
        out["flight_map"] = add_flight_map(soup, slug, article)
        if slug in PICKERS:
            out["picker"] = add_picker(soup, slug, article)
        if slug in STAY_POINTERS:
            out["pointer"] = add_stay_pointer(soup, slug, article)
    add_social_meta.apply(soup)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    changed = verdicts = links = tocs = rates = pointers = 0
    unknown: list[str] = []
    no_anchor: list[str] = []
    for src in sorted((SITE / "articles").glob("*.html")):
        rel = f"articles/{src.name}"
        html = src.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")
        res = apply(soup, rel)
        new = str(soup)
        verdicts += res["verdict"]
        links += res["links"]
        tocs += bool(res["toc"])
        rates += res["rates"]
        unknown += [f"{src.stem}: {n}" for n in res["unknown_hotels"]]
        if src.stem in STAY_POINTERS:
            if res.get("pointer"):
                pointers += 1
            else:
                no_anchor.append(src.stem)
        if new != html:
            changed += 1
            if args.write:
                src.write_text(new, encoding="utf-8")
                (DOCS / rel).write_text(new, encoding="utf-8")
    missing = sorted(s for s in V if not (SITE / "articles" / f"{s}.html").exists())
    print(f"pages changed: {changed}   verdicts: {verdicts}   partner links placed: {links}   "
          f"contents lists: {tocs}   hotel rates links: {rates}   stay pointers: {pointers}/{len(STAY_POINTERS)}")
    if missing:
        print("  registry slugs with no page:", ", ".join(missing))
    if no_anchor:                                # a heading was renamed, or the page is gone
        print("  stay pointers with no anchor:", ", ".join(no_anchor))
    if unknown:                                  # look each one up on Booking.com first
        print("  hotels missing from stay22.HOTELS (no rates link yet):")
        for u in unknown:
            print("   ", u)
    if not args.write:
        print("  (dry run — pass --write to apply)")


if __name__ == "__main__":
    main()
