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
    "japan-tourist-taxes-2026": "2026-10-04",                    # corrected: summary still said ¥1,000 departure tax
    "hong-kong-first-timers-guide": "2026-10-04",                # corrected: tram fare HK$3.30, not HK$3
}

STOP_HEADINGS = re.compile(r"frequently asked|^sources|references|liked this guide|keep reading|related reading",
                           re.I)
SKIP_SELECTOR = ".gy-verdict, .gy-widget, .gy-cta, .gy-section-link, figure, .faq, .newsletter, script, style"


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
            c in ("gy-verdict", "gy-widget", "gy-cta", "gy-section-link", "faq", "newsletter")
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
        box.extend([h, b, frame])
        last.insert_after(box)
    return placed, unknown


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
        a.string = "Check rates →"
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


# --- hotels by city (the booking-site comparison) ---------------------------------
# Readers reach the comparison from ChatGPT with a trip in mind; most never scroll.
# Under the verdict, one line per city: hotels around a central spot (Stay22 picks
# the booking site) and, where we have one, our guide to the city's areas.
# (city, stay22.PAGES slug or None, area label, address when there is no guide)
CITY_RATES = {
    "hotel-booking-sites-comparison": [
        ("Tokyo", "where-to-stay-in-tokyo", None, None),
        ("Kyoto", "where-to-stay-in-kyoto", None, None),
        ("Osaka", "where-to-stay-in-osaka", None, None),
        ("Hakone", "where-to-stay-in-hakone", None, None),
        ("Seoul", "where-to-stay-in-seoul", None, None),
        ("Bangkok", "where-to-stay-in-bangkok", None, None),
        ("Hong Kong", "where-to-stay-in-hong-kong", None, None),
        ("Taipei", "where-to-stay-in-taipei", None, None),
        ("Singapore", "where-to-stay-in-singapore", None, None),
        ("Kuala Lumpur", "where-to-stay-in-kuala-lumpur", None, None),
        ("Sydney", "where-to-stay-in-sydney", None, None),
        ("Melbourne", "where-to-stay-in-melbourne", None, None),
    ],
}
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
    for city, guide, area, address in CITY_RATES[slug]:
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
    for sel in ("details.gy-toc", "p.gy-promise", "aside.gy-verdict"):
        anchor = article.select_one(sel)
        if anchor is not None and anchor.parent is article:
            anchor.insert_after(box)
            return len(CITY_RATES[slug])
    return 0


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
        'compares six areas, from Shinjuku to Asakusa, and names 17 hotels; in cherry season, <a '
        f'href="{_TS}">our cherry-blossom guide</a> matches five areas to the parks and rivers.'),
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
        'dates and the areas by blossom.'),
    "japan-autumn-2026": ("Flights and Stays",
        f'For where to sleep, <a href="{_JP}">where to stay in Japan on a first trip</a> splits the nights between '
        f'cities, and our guides to {_JP3} name the hotels.'),
    "japan-book-in-advance-2026": ("Authentic Stays",
        f'For named ryokan in Kyoto, including Tawaraya and Hiiragiya, see <a href="{_K}">Where to stay in '
        'Kyoto</a>.'),
    "japan-tourist-taxes-2026": ("Kyoto’s new lodging tax",
        f'Choosing where to stay in Kyoto? <a href="{_K}">Our Kyoto guide</a> compares five areas and names '
        '14 hotels and ryokan.'),
    # the three Japan city guides, back to the trip-level question
    "where-to-stay-in-tokyo": ("intro",
        f'Splitting the trip between cities? <a href="{_JP}">Where to stay in Japan on a first trip</a> covers '
        'how many nights to give Tokyo, Kyoto and Osaka, and moving day in between. Coming for the cherry '
        f'blossom? <a href="{_TS}">Our cherry-blossom guide</a> has the dates and the tax change on 1 April 2027.'),
    "where-to-stay-in-kyoto": ("intro",
        f'Coming from Tokyo? <a href="{_JP}">Where to stay in Japan on a first trip</a> covers how many nights to '
        'give each city, and how to move your bags between them.'),
    "where-to-stay-in-osaka": ("intro",
        f'Kyoto, Osaka, or both? <a href="{_JP}">Where to stay in Japan on a first trip</a> covers how many '
        'nights to give each, and moving day from Tokyo.'),
    # Kyoto
    "gion-kyoto-neighbourhood-guide": ("Getting there, and fitting it in",
        f'Staying close by? <a href="{_K}#gion-and-higashiyama-the-old-city-early-and-late">Where to stay in '
        'Gion and Higashiyama</a> names three hotels in this part of Kyoto.'),
    "three-slow-days-in-kyoto": ("Moving Gently",
        f'Where to base yourself for these three days: <a href="{_K}">Where to stay in Kyoto</a> compares '
        'downtown, Kyoto Station, Gion, Arashiyama and the northern hills.'),
    "kyoto-autumn-2026": ("Accommodation and Mobility",
        f'<a href="{_K}">Where to stay in Kyoto</a> compares five areas and names 14 hotels and ryokan.'),
    "tokyo-to-kyoto-shinkansen-vs-flight-vs-bus": ("What This Means",
        f'Arriving by Shinkansen? <a href="{_K}#kyoto-station-the-transport-base">Where to stay in Kyoto</a> '
        'explains when a hotel at the station beats one downtown.'),
    "things-to-do-in-kyoto": ("intro",
        f'Where you stay decides which of these you can walk to early, before the crowds. <a href="{_K}">Where '
        'to stay in Kyoto</a> compares five areas, from downtown to Arashiyama, and <a '
        'href="where-to-stay-in-kyoto-cherry-blossom.html">our cherry-blossom guide</a> matches them to the '
        'blossom walks.'),
    # Osaka
    "osaka-first-timers-guide": ("intro",
        f'Minami or Kita? <a href="{_O}">Where to stay in Osaka</a> compares Namba and Umeda with three other '
        'areas and names 10 hotels.'),
    "osaka-3-day-guide": ("intro",
        f'Choosing a base for these three days? <a href="{_O}">Where to stay in Osaka</a> compares Namba, '
        'Umeda, Nakanoshima, Tennoji and the bay, and names 10 hotels.'),
    "things-to-do-in-osaka": ("intro",
        f'<a href="{_O}">Where to stay in Osaka</a> compares five areas, from Namba’s food streets to the bay '
        'by Universal Studios Japan, and names 10 hotels.'),
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
    "seoul-itinerary-3-days": ("The practical spine",
        f'For a base that suits these three days, <a href="{_SE}">where to stay in Seoul</a> compares five areas and '
        'names 12 hotels.'),
    "how-much-does-south-korea-cost": ("Accommodation",
        f'Pricing the beds in Seoul? <a href="{_SE}">Where to stay in Seoul</a> names 12 hotels by area, from a '
        'mid-range base in Myeongdong to Signiel on the 76th floor and up.'),
    "korail-pass-worth-it-2026": ("How to decide",
        f'Catching an early KTX? <a href="{_SE}#seoul-station-and-itaewon-trains-then-dinner">Where to stay in '
        'Seoul</a> names a hotel linked to Seoul Station by an underground passage.'),
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
        'Manly, and names 13 hotels.'),
    "sydney-harbour-cruises-guide": ("Practical notes",
        f'Staying near a departure point? <a href="{_S}">Where to stay in Sydney</a> compares Circular Quay '
        'and Darling Harbour as bases.'),
    # both
    "best-time-to-visit-australia": ("The south: Sydney",
        f'Once you have dates: <a href="{_S}">where to stay in Sydney</a> and <a href="{_M}">in Melbourne</a>, '
        'area by area.'),
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
    if article is not None:
        out["toc"] = add_toc(soup, article)
        add_promise(soup, article)
        if slug in stay22.PAGES:
            move_map_up(article)
        if slug in QUICK_PICKS:
            out["quick_picks"] = add_quick_picks(soup, slug, article)
        if slug in CITY_RATES:
            out["city_rates"] = add_city_rates(soup, slug, article)
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
