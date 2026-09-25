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

Only brands we have an affiliate relationship with are ever linked. Viator,
GetYourGuide, Holafly, SafetyWing and the rest stay plain text.

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
}
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
}

# --- verdicts -----------------------------------------------------------------
# slug -> text, cta, and optionally which legacy summary box it replaces.
# cta: (brand key, label) | ("amazon", asin, label) | None. None where the pick
# is not a partner of ours — a link to a different brand under a verdict that
# names someone else would be a bait-and-switch.
LEGACY_BOX = "aside.verdict"
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
        cta=None),
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
    "where-to-stay-in-tokyo": dict(
        text="Choose the station first, then the hotel (Klook lists several of the hotels below if you want "
             "to compare prices). For a first trip, stay on the south or west side of Shinjuku, or in Shibuya; "
             "for the Shinkansen or quiet evenings, the Marunouchi side of Tokyo Station; for old-Tokyo "
             "character and better value, Asakusa or Ueno. Then book within five minutes of the exit you will use.",
        cta=("klook", "Compare Tokyo hotels on Klook")),
    "where-to-stay-in-sydney": dict(
        text="For a first trip, stay in the city centre by Hyde Park; our pick there is the Sheraton Grand "
             "Sydney Hyde Park, where one of us stayed in September 2026 (Klook lists it if you want to "
             "compare prices). Choose Circular Quay and The Rocks for the harbour, Surry Hills for food, and "
             "Bondi or Manly for the beach.",
        cta=("klook", "Compare Sydney hotels on Klook")),
    "where-to-stay-in-melbourne": dict(
        text="Stay in the CBD, inside the Free Tram Zone, for a first trip; the SkyBus from the airport, "
             "bookable on Klook, stops at Southern Cross on its edge. Choose Southbank for the river, Fitzroy "
             "for bars and vintage shops, St Kilda for the bay and South Yarra for Chapel Street.",
        cta=("klook", "Book the SkyBus on Klook")),
    "where-to-stay-in-kyoto": dict(
        text="Stay downtown near a subway station for the best all-round base, or by Kyoto Station if you "
             "are arriving by Shinkansen or from Kansai Airport (Klook lists some of the station hotels if "
             "you want to compare prices). Choose Gion and Higashiyama for the old city at dawn and dusk, "
             "and budget for the accommodation tax that rose on 1 March 2026.",
        cta=("klook", "Compare Kyoto hotels on Klook")),
    "where-to-stay-in-osaka": dict(
        text="Stay in Namba or Shinsaibashi for food and nightlife, or around Umeda and Osaka Station for "
             "trains to Kyoto, Kobe and Kansai Airport (the Haruka stops there, and Klook sells tickets). "
             "Tennoji and Shinsekai are the value pick, and the bay only makes sense if Universal Studios "
             "Japan is the point of the trip.",
        cta=("klook", "Book the Haruka on Klook")),
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
    "tokyo-to-kyoto-shinkansen-vs-flight-vs-bus": "2026-09-24",  # no-airport answer, table, verified fares
    "charter-a-boat-for-a-day": "2026-09-23",                    # Spain 1 Oct 2026, Greece, Croatia
    "where-to-stay-in-tokyo": "2026-09-25",                      # rewrite: 17 verified hotels, tax, tables
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
def _page_href(soup: BeautifulSoup, key: str) -> str:
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


def link_brands(soup: BeautifulSoup) -> int:
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
            a = _anchor(soup, _page_href(soup, key))
            target.wrap(a)
            done.add(key)
            added += 1

    # 2. paragraphs that open with a bold partner name — the top of that
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
        first.wrap(_anchor(soup, _page_href(soup, key)))
        seen.add(key)
        added += 1

    # 3. headings that name exactly one partner ("1. Airalo — Best Overall …")
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
        a = _anchor(soup, _page_href(soup, key), managed=False)
        a.string = f"{SECTION_LABEL[key]} →"
        p.append(a)
        h.insert_after(p)
        added += 1
    return added


# --- verdict ------------------------------------------------------------------
def render_verdict(soup: BeautifulSoup, spec: dict) -> Tag:
    box = soup.new_tag("aside", attrs={"class": "gy-verdict", "data-aeo": "1"})
    p = soup.new_tag("p", attrs={"class": "gy-verdict-text"})
    label = soup.new_tag("strong", attrs={"class": "gy-verdict-label"})
    label.string = BRAND_LABEL
    p.append(label)
    cta = spec.get("cta")
    href = None
    if cta and cta[0] == "amazon":
        href, text = _amazon_href(soup, cta[1]), cta[2]
    elif cta:
        href, text = _page_href(soup, cta[0]), cta[1]
    # Link the partner where the verdict first names it, not only in the line
    # after the text: on a phone a long verdict pushed that last line below the
    # first screen on every decision article (the link must show unscrolled).
    names = [n for n, k in BRANDS.items() if cta and k == cta[0]]
    m = None
    if href and names:
        m = re.search(r"\b(" + "|".join(re.escape(n) for n in names) + r")\b", spec["text"])
    if m:
        p.append(" " + spec["text"][:m.start()])
        inline = _anchor(soup, href, managed=False)
        inline.string = m.group(0)
        p.append(inline)
        p.append(spec["text"][m.end():])
    else:
        p.append(" " + spec["text"])
    box.append(p)
    if href:
        c = soup.new_tag("p", attrs={"class": "gy-verdict-cta"})
        a = _anchor(soup, href, managed=False)
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
    out = {"verdict": False, "links": 0, "toc": 0}
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
        box = render_verdict(soup, spec)
        if first is not None:
            first.insert_before(box)
        else:
            article.append(box)
        out["verdict"] = True
        out["links"] = link_brands(soup)
    if article is not None:
        out["toc"] = add_toc(soup, article)
    add_social_meta.apply(soup)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    changed = verdicts = links = tocs = 0
    for src in sorted((SITE / "articles").glob("*.html")):
        rel = f"articles/{src.name}"
        html = src.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")
        res = apply(soup, rel)
        new = str(soup)
        verdicts += res["verdict"]
        links += res["links"]
        tocs += bool(res["toc"])
        if new != html:
            changed += 1
            if args.write:
                src.write_text(new, encoding="utf-8")
                (DOCS / rel).write_text(new, encoding="utf-8")
    missing = sorted(s for s in V if not (SITE / "articles" / f"{s}.html").exists())
    print(f"pages changed: {changed}   verdicts: {verdicts}   partner links placed: {links}   contents lists: {tocs}")
    if missing:
        print("  registry slugs with no page:", ", ".join(missing))
    if not args.write:
        print("  (dry run — pass --write to apply)")


if __name__ == "__main__":
    main()
