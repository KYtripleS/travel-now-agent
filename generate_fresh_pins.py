#!/usr/bin/env python3
"""
generate_fresh_pins.py — fresh Pinterest pins and the queue n8n posts from.

Until September 2026 the Pinterest workflow cycled the same 145 pins, so every
~48 days Pinterest saw the same image with the same link again. Pinterest
rewards fresh pins (a new image, even for an old page) and repeated pins lose
reach. From now on:

  * every pin in site/data/pins.json is new (ids from 1001, increasing), made
    here from a photo Pinterest has not seen from us;
  * the n8n node (n8n/pinterest-pick-next.js) posts the next id and never
    wraps; when the queue is used up it posts nothing until the next batch;
  * the 145 pins already posted live in data/pins_posted_archive.json.

Photos come from Pexels at 1000x1500 and are checked by eye before they go in
SPECS (a pin never shows a place other than the one it names). Images are
written as JPEG to images/pinterest/fresh/ in site/ and docs/ (the old PNGs
are ~1.3 MB each; these are ~0.3 MB).

    python generate_fresh_pins.py            # check specs, render missing images, write the queue
    python generate_fresh_pins.py --check    # checks only, writes nothing
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from PIL import Image

import generate_pin
from generate_pin import encode_data_uri, fill_template

REPO = Path(__file__).resolve().parent
BASE = "https://gentlyyonder.com"
OUT_DIR = "images/pinterest/fresh"
QUEUE = REPO / "site" / "data" / "pins.json"
ARCHIVE = REPO / "data" / "pins_posted_archive.json"
UTM = "utm_source=pinterest&utm_medium=pin&utm_campaign=fresh"

# Board names exactly as on pinterest.com/gentlyyonder, with their ids (read
# from the public profile on 2026-09-27). Keep in sync with the n8n node.
BOARDS = {
    "Travel Packing Checklists": "609956411972752122",
    "Asia Travel": "609956411972753421",
    "Language & Culture or Travel Reflections": "609956411972753420",
    "Travel Tech: eSIM & Insurance": "609956411972757874",
    "Japan Travel Guides": "609956411972750832",
    "Australia Travel Guides": "609956411972751419",
    "Vietnam Travel Guides": "609956411972750987",
}
JP, AU, VN, ASIA, TECH, GEN = ("Japan Travel Guides", "Australia Travel Guides",
                              "Vietnam Travel Guides", "Asia Travel",
                              "Travel Tech: eSIM & Insurance", "Travel Packing Checklists")

BANNED = ["hidden gem", "magical", "must-see", "must see", "bucket list", "secret spot",
          "off the beaten path", "instagram-worthy", "you need this", "this changes everything",
          "ultimate", "life-changing", "guarantees entry"]

# id, slug, article, board, Pexels photo id, big title, tagline, 4 bullets, button,
# Pinterest title (<=100), description (<=500). Facts come from the article itself.
SPECS = [
    dict(id=1001, slug="tax-free-japan-f1", article="articles/japan-tax-free-shopping-2026-changes.html",
         board=JP, photo=31416386, title="TAX-FREE", tagline="Japan changes it on 1 November",
         bullets=["Pay full price at the till", "Claim the 10% at the airport",
                  "Same ¥5,000 minimum spend", "No more sealed bags"], cta="What changes →",
         pin_title="Japan Tax-Free Shopping Changes on 1 November 2026: How the New Refund Works",
         description="From 1 November 2026, tax-free shopping in Japan works differently: you pay the full "
                     "price, 10% tax included, then claim the tax back at the airport through a customs "
                     "terminal or Visit Japan Web before check-in. The ¥5,000 minimum stays, sealed bags for "
                     "cosmetics and snacks go, and you need to budget for the full amount up front."),
    dict(id=1002, slug="where-to-stay-tokyo-f1", article="articles/where-to-stay-in-tokyo.html",
         board=JP, photo=30933060, title="TOKYO STAYS", tagline="choose the station first",
         bullets=["First trip: Shinjuku, Shibuya", "Shinkansen days: Tokyo Station",
                  "Old Tokyo: Asakusa, Ueno", "17 hotels, checked Sept 2026"], cta="Where to stay in Tokyo →",
         pin_title="Where to Stay in Tokyo (2026): 6 Neighbourhoods and 17 Hotels Compared",
         description="Choose the station before the hotel. Shinjuku or Shibuya for a first trip, the "
                     "Marunouchi side of Tokyo Station for Shinkansen days and quiet evenings, Asakusa or "
                     "Ueno for old-Tokyo character and better value. Six Tokyo neighbourhoods and 17 named "
                     "hotels, each checked in September 2026."),
    dict(id=1003, slug="where-to-stay-sydney-f1", article="articles/where-to-stay-in-sydney.html",
         board=AU, photo=36877472, title="SYDNEY", tagline="where to stay, area by area",
         bullets=["First trip: by Hyde Park", "Harbour: Circular Quay", "Food: Surry Hills",
                  "Beach: Bondi or Manly"], cta="Where to stay in Sydney →",
         pin_title="Where to Stay in Sydney (2026): 6 Areas and 13 Hotels Compared",
         description="The city centre by Hyde Park is the easiest first base, Circular Quay and The Rocks put "
                     "the harbour at your door, Surry Hills is for food, and Bondi or Manly are for the "
                     "beach. Six Sydney areas and 13 hotels, including the Sheraton Grand Sydney Hyde Park, "
                     "where one of us stayed in September 2026."),
    dict(id=1004, slug="k-eta-korea-f1", article="articles/do-you-need-keta-south-korea.html",
         board=ASIA, photo=33019231, title="K-ETA", tagline="the waiver ends 31 Dec 2026",
         bullets=["22 countries exempt until then", "No extension announced yet",
                  "No K-ETA? Arrival card instead", "It is not a visa"], cta="The 2026 rule →",
         pin_title="Do You Need a K-ETA for South Korea? The 2026 Waiver Ends on 31 December",
         description="Travellers from 22 countries and regions, including the US, UK, Canada, Australia and "
                     "Japan, don't need a K-ETA for short trips to South Korea until 31 December 2026. What "
                     "the exemption covers, the arrival card you fill in instead, and what to check before a "
                     "trip in the new year. No extension has been announced yet."),
    dict(id=1005, slug="where-to-stay-kyoto-f1", article="articles/where-to-stay-in-kyoto.html",
         board=JP, photo=36667044, title="KYOTO STAYS", tagline="where to base yourself",
         bullets=["Downtown: best all-round base", "Kyoto Station: Shinkansen days",
                  "Gion: the old city at dawn", "The 2026 hotel tax, explained"], cta="Where to stay in Kyoto →",
         pin_title="Where to Stay in Kyoto (2026): 5 Areas and 14 Hotels and Ryokan Compared",
         description="Stay downtown, between Karasuma and Kawaramachi, for the best all-round base; by Kyoto "
                     "Station if you arrive by Shinkansen or from Kansai Airport; in Gion and Higashiyama for "
                     "the old city at dawn and dusk. Five Kyoto areas, 14 hotels and ryokan, and the "
                     "accommodation tax that rose on 1 March 2026."),
    dict(id=1006, slug="interrail-europe-f1", article="articles/europe-rail-pass-worth-it-2026.html",
         board=GEN, photo=12603512, title="INTERRAIL", tagline="Eurail's new name, Sept 2026",
         bullets=["One pass range for everyone", "Best for long, loose trips",
                  "Fast trains need seat bookings", "Fixed route? Buy tickets"], cta="Is a pass worth it? →",
         pin_title="Is a Europe Rail Pass Worth It in 2026? Eurail Is Now Interrail",
         description="Since 9 September 2026, Eurail and Interrail are one pass range, open to every "
                     "traveller. A pass wins for long distances across several countries, loose plans, "
                     "children aged 4–11 and travellers under 28. On a fixed route, advance tickets in France, "
                     "Spain, Italy and Germany are often cheaper than a pass day plus its seat reservation."),
    dict(id=1007, slug="tokyo-kissaten-f1", article="articles/tokyo-kissaten-guide.html",
         board=JP, photo=22674075, title="KISSATEN", tagline="Tokyo's old coffee houses",
         bullets=["Café Paulista, since 1911", "Siphon coffee, velvet chairs", "One order per person",
                  "Bring cash"], cta="Nine still open →",
         pin_title="Tokyo Kissaten Guide: 9 Old Coffee Houses Still Open, and How to Behave",
         description="Tokyo's kissaten keep their own time: siphon coffee, morning sets and velvet chairs. "
                     "Nine old coffee houses still open in September 2026, from Café Paulista in Ginza (1911) "
                     "to the book-lined streets of Jimbocho, plus the etiquette: one order per person, cash "
                     "in hand, and a quiet voice."),
    dict(id=1008, slug="japan-winter-f1", article="articles/best-time-to-visit-japan-2026.html",
         board=JP, photo=707677, title="JAPAN", tagline="in winter, the value season",
         bullets=["Dec to mid-March: cheapest", "Least crowded months", "May, Oct–Nov: best balance",
                  "Blossom weeks: peak prices"], cta="When to go →",
         pin_title="Best Time to Visit Japan (2026): Why December to March Is the Value Season",
         description="For a first trip with flexible dates, May and October to November balance weather, "
                     "colour and crowds best. Cherry-blossom and autumn-leaf weeks are glorious but "
                     "peak-priced, while December to mid-March is Japan at its cheapest and least crowded. "
                     "Season by season, with the 2026 dates to plan around."),
    dict(id=1009, slug="where-to-stay-osaka-f1", article="articles/where-to-stay-in-osaka.html",
         board=JP, photo=31184555, title="OSAKA STAYS", tagline="Namba or Umeda?",
         bullets=["Food and nightlife: Namba", "Trains and airport: Umeda", "Value: Tennoji, Shinsekai",
                  "USJ: stay by the park"], cta="Where to stay in Osaka →",
         pin_title="Where to Stay in Osaka (2026): Namba vs Umeda, 5 Areas and 10 Hotels",
         description="Namba and Shinsaibashi for food, nightlife and Nankai trains to the airport; Umeda for "
                     "JR to Kyoto and Kobe and the Haruka from Kansai Airport; Tennoji and Shinsekai for "
                     "value; and the bay only if Universal Studios Japan is the point. Five Osaka areas, 10 "
                     "hotels, and the accommodation tax."),
    dict(id=1010, slug="seoul-dmz-f1", article="articles/where-to-book-seoul-dmz-tour.html",
         board=ASIA, photo=5574884, title="SEOUL DMZ", tagline="read the tour title twice",
         bullets=["JSA closed to tours since 2023", "Book DMZ, not 'DMZ + JSA'", "Check for a shopping stop",
                  "KKday vs Klook vs Viator"], cta="Where to book →",
         pin_title="Seoul DMZ Tour (2026): Where to Book, and Why the JSA Is Closed",
         description="The JSA at Panmunjom has been closed to civilian tours since July 2023, so book a DMZ "
                     "tour, not a 'DMZ & JSA' promise. Which platform has the sharpest verified price, which "
                     "tours add a North Korean defector Q&A, and how to spot a shopping stop before you "
                     "compare prices."),
    dict(id=1011, slug="australia-when-f1", article="articles/best-time-to-visit-australia.html",
         board=AU, photo=6610368, title="AUSTRALIA", tagline="when to go, region by region",
         bullets=["Dec–Feb: summer, peak crowds", "Sep–Nov, Mar–May: best value", "Reef and south: May–Oct",
                  "Pick the region, then month"], cta="When to go →",
         pin_title="Best Time to Visit Australia: Sydney, Melbourne, the Reef and the North",
         description="Australia is a continent, not one season. For a first trip mixing Sydney or Melbourne "
                     "with the Reef or the north, go between May and October. For the southern cities alone, "
                     "September to November and March to May are milder and better value; December to "
                     "February is the classic summer and the peak crowd."),
    dict(id=1012, slug="tokyo-food-tour-f1", article="articles/where-to-book-tokyo-food-tour.html",
         board=JP, photo=16781771, title="TOKYO FOOD", tagline="which tour, which platform",
         bullets=["Shinjuku izakaya at night", "Tsukiji in the morning", "Asakusa for old-town snacks",
                  "Viator vs Klook vs KKday"], cta="Where to book →",
         pin_title="Where to Book a Tokyo Food Tour (2026): Viator vs Klook vs KKday",
         description="Choose the neighbourhood and the hour first: Shinjuku's izakaya alleys at night, Tsukiji "
                     "in the morning, Asakusa for old-town snacks. Then the platform: Viator has the most "
                     "Tokyo food tours and reviews, Klook is often cheaper in its sales for the same tour, "
                     "and KKday has few. Prices checked September 2026."),
    dict(id=1013, slug="hong-kong-f1", article="articles/hong-kong-first-timers-guide.html",
         board=ASIA, photo=20306805, title="HONG KONG", tagline="a calm first-timer's guide",
         bullets=["Buy an Octopus card first", "Star Ferry, after dark", "The Peak and the Big Buddha",
                  "Dim sum and cha chaan teng"], cta="The first-timer's guide →",
         pin_title="Hong Kong for First-Timers: Octopus Card, Star Ferry and Where to Start",
         description="A calm orientation to Hong Kong: the Island and Kowloon on either side of Victoria "
                     "Harbour, the Star Ferry (running since 1888) and the Peak Tram, Kowloon's markets and "
                     "temples, Lantau's Big Buddha, dim sum and cha chaan teng, and getting around on the "
                     "Octopus card."),
    dict(id=1014, slug="where-to-stay-melbourne-f1", article="articles/where-to-stay-in-melbourne.html",
         board=AU, photo=38418159, title="MELBOURNE", title_size=118, tagline="where to stay, area by area",
         bullets=["First trip: the CBD", "Free trams in the city centre", "SkyBus to Southern Cross",
                  "Fitzroy, St Kilda, South Yarra"], cta="Where to stay →",
         pin_title="Where to Stay in Melbourne (2026): 5 Areas and 12 Hotels Compared",
         description="Stay in the CBD, inside the Free Tram Zone, for a first trip; the SkyBus from the airport "
                     "stops at Southern Cross on its edge. Southbank for the river, Fitzroy for bars and "
                     "vintage shops, St Kilda for the bay, South Yarra for Chapel Street. Five Melbourne areas "
                     "and 12 hotels, checked September 2026."),
    dict(id=1015, slug="vietnam-when-f1", article="articles/best-time-to-visit-vietnam.html",
         board=VN, photo=34949999, title="VIETNAM", tagline="the best time, north to south",
         bullets=["Three regions, three climates", "Feb–Apr, Oct–Nov: best mix", "May–Sep: cheaper, greener",
                  "Autumn: rain on central coast"], cta="When to go →",
         pin_title="Best Time to Visit Vietnam (2026): North, Centre and South Compared",
         description="Vietnam has no single best month: the north, centre and south run on different weather. "
                     "For a first trip from north to south, late February to April and October to November "
                     "compromise least, with some autumn rain on the central coast. May to September is "
                     "cheaper and greener if you can live with afternoon rain."),
    dict(id=1016, slug="taiwan-hsr-f1", article="articles/taiwan-high-speed-rail-pass-worth-it.html",
         board=ASIA, photo=32434305, title="TAIWAN HSR", tagline="the 3-Day Pass often loses",
         bullets=["3-Day Pass: NT$2,200", "Standard return: NT$2,980", "Early Bird: about NT$1,938",
                  "Discounts don't stack"], cta="The honest math →",
         pin_title="Taiwan High Speed Rail Pass (2026): Is the 3-Day Pass Worth It?",
         description="Taipei–Kaohsiung and back costs NT$2,980 at the standard fare. The 3-Day Pass is "
                     "NT$2,200, but an Early Bird round trip is about NT$1,938 and a buy-one-get-one pair "
                     "works out near NT$1,266 each. The discounts don't stack, so the order you check them in "
                     "decides the price."),
    dict(id=1017, slug="europe-esim-f1", article="articles/best-esim-europe-2026.html",
         board=TECH, photo=5448160, title="EUROPE eSIM", tagline="one plan, many countries",
         bullets=["One regional plan", "Check Switzerland and the UK", "10–20 GB for 1–2 weeks",
                  "Install it before you fly"], cta="Compare Europe eSIMs →",
         pin_title="Best eSIM for Europe (2026): One Regional Plan for a Multi-Country Trip",
         description="For a trip across several European countries, a regional eSIM from Airalo or Saily is "
                     "the practical choice. Check that non-EU stops such as Switzerland, the UK or the "
                     "Balkans are included. Moderate use for one to two weeks typically needs 10–20 GB; "
                     "install the plan before you fly."),
    dict(id=1018, slug="tokyo-kyoto-f1", article="articles/tokyo-to-kyoto-shinkansen-vs-flight-vs-bus.html",
         board=JP, photo=33341980, title="TOKYO–KYOTO", tagline="train, plane or bus?",
         bullets=["Shinkansen: about 2h 15m", "Nozomi: about ¥14,170", "Flying: about twice as long",
                  "Night bus: the budget pick"], cta="All three compared →",
         pin_title="Tokyo to Kyoto (2026): Shinkansen vs Flight vs Bus, Times and Prices",
         description="Take the Shinkansen: about 2 hours 15 minutes and about ¥14,170 on the Nozomi, city "
                     "centre to city centre. Flying via Osaka takes about twice as long door to door, and "
                     "the overnight bus is the budget option. All three ways compared."),
    dict(id=1019, slug="bangkok-river-f1", article="articles/bangkok-river-cruises-guide.html",
         board=ASIA, photo=26847891, title="BANGKOK", tagline="the river, without the cruise",
         bullets=["Chao Phraya Express Boat", "Free ICONSIAM shuttle", "Tha Tien pier for Wat Pho",
                  "When a dinner cruise pays off"], cta="The river guide →",
         pin_title="Bangkok River Cruises: A Dinner Cruise or the Chao Phraya Express Boat?",
         description="You don't need a dinner cruise to see Bangkok from the river: the Chao Phraya Express "
                     "Boat runs the same water for a normal fare, and the ICONSIAM shuttle from Sathorn "
                     "crosses it free. Ride up to Tha Tien for Wat Pho and the Wat Arun crossing, and see "
                     "when a dinner cruise is worth paying for."),
    dict(id=1020, slug="halong-bay-f1", article="articles/halong-bay-cruises-from-hanoi.html",
         board=VN, photo=5531543, title="HA LONG BAY", tagline="day trip or overnight?",
         bullets=["About 200 km from Hanoi", "3+ hours each way by road", "Lan Ha Bay: often better",
                  "A night on board changes it"], cta="Day trip or overnight →",
         pin_title="Ha Long Bay From Hanoi: Day Trip or Overnight Cruise? An Honest Guide",
         description="A Ha Long Bay day trip is mostly a bus ride: the bay is about 200 km from Hanoi and the "
                     "road takes at least three hours each way. The real costs of a day trip versus one or "
                     "two nights, why Lan Ha Bay is often the better pick, what you actually do on board, "
                     "and when the bay closes."),
    dict(id=1021, slug="klook-vs-kkday-f1", article="articles/klook-vs-kkday.html",
         board=ASIA, photo=4549408, title="KLOOK v KKDAY", tagline="which to book with, honestly",
         bullets=["Klook: transport, rail passes", "KKday: Taiwan, Japan, locals",
                  "Prices vary listing by listing", "Compare the same activity"], cta="The honest comparison →",
         pin_title="Klook vs KKday (2026): Which to Book With in Japan, Taiwan and Asia",
         description="Use Klook as your broad default, especially for transport, rail passes, transfers and "
                     "multi-category trips, and check KKday whenever you're in Taiwan or Japan or want a "
                     "smaller local operator. Prices vary listing by listing, so compare the same activity "
                     "on both."),
    dict(id=1022, slug="esim-compare-f1", article="articles/airalo-vs-holafly-vs-saily.html",
         board=TECH, photo=27019193, title="WHICH eSIM?", tagline="Airalo, Holafly or Saily",
         bullets=["Airalo: the flexible default", "Saily: good-value data", "Holafly: only if unlimited",
                  "Read fair-use rules first"], cta="Compare the three →",
         pin_title="Airalo vs Holafly vs Saily (2026): Which Travel eSIM Should You Buy?",
         description="Airalo is the flexible default, with wide country coverage and plans you can size to your "
                     "trip; Saily is the one to price-check for simple, good-value data; and Holafly only "
                     "pays off if you'll genuinely use unlimited data, so read its fair-usage policy first."),
    dict(id=1023, slug="where-to-stay-tokyo-f2", article="articles/where-to-stay-in-tokyo.html",
         board=JP, photo=23340221, title="TOKYO", tagline="6 neighbourhoods, 17 hotels",
         bullets=["Shinjuku: the all-hours hub", "Shibuya: young, walkable", "Ginza: refined, pricier",
                  "Ueno: Skyliner from Narita"], cta="Find your area →",
         pin_title="Tokyo Neighbourhoods for a First Trip: Shinjuku, Shibuya, Ginza, Asakusa or Ueno?",
         description="Shinjuku is the all-hours hub, Shibuya is young and walkable, Ginza is refined and priced "
                     "accordingly, Asakusa keeps old Tokyo's low-rise feel, and Ueno has the Keisei Skyliner "
                     "from Narita next door. How to choose, with 17 hotels by area."),
    dict(id=1024, slug="tax-free-japan-f2", article="articles/japan-tax-free-shopping-2026-changes.html",
         board=JP, photo=31178674, title="NEW RULES", tagline="tax-free shopping in Japan",
         bullets=["From 1 November 2026", "Pay first, refund later", "Claim before airport check-in",
                  "Keep goods out of checked bags"], cta="How the refund works →",
         pin_title="Japan Tax-Free Shopping 2026: Pay First, Refund Later. What to Do at the Airport",
         description="Japan's tax-free system changes on 1 November 2026: shoppers pay the full price and "
                     "reclaim the 10% at departure. Before check-in, submit your application at a customs "
                     "terminal or through Visit Japan Web, keep purchases and receipts in your hand luggage, "
                     "and allow extra time at Narita, Haneda or Kansai."),
    dict(id=1025, slug="sydney-hyde-park-f2", article="articles/where-to-stay-in-sydney.html",
         board=AU, photo=38680739, title="HYDE PARK", tagline="our Sydney pick, first-hand",
         bullets=["Sheraton Grand Hyde Park", "Minutes from St James station", "Rooftop pool and spa",
                  "We stayed and paid our way"], cta="Where to stay in Sydney →",
         pin_title="Where to Stay in Sydney: Our Pick by Hyde Park (We Stayed There in 2026)",
         description="Our Sydney pick for a first trip is the Sheraton Grand Sydney Hyde Park: on the park, a "
                     "couple of minutes from St James and Museum stations, with a rooftop pool and spa. One "
                     "of us stayed there in September 2026, paying our own way. The full guide compares six "
                     "areas and 13 hotels."),
    dict(id=1026, slug="kyoto-ryokan-f2", article="articles/where-to-stay-in-kyoto.html",
         board=JP, photo=30491451, title="RYOKAN", tagline="a night in a Kyoto inn",
         bullets=["Tawaraya, since 1709", "Hiiragiya, since 1818", "Tatami, futons, kaiseki",
                  "Pair it with a hotel"], cta="Where to stay in Kyoto →",
         pin_title="Staying in a Kyoto Ryokan: Tawaraya, Hiiragiya and How to Plan One Night",
         description="Tawaraya (1709) and Hiiragiya (1818) face each other in Fuyacho and are among the most "
                     "celebrated ryokan in Japan. Expect tatami, futons, a kaiseki dinner and customs to "
                     "follow; many travellers pair one ryokan night with a hotel for the rest of the stay. "
                     "Part of our guide to where to stay in Kyoto."),
    dict(id=1027, slug="osaka-umeda-f2", article="articles/where-to-stay-in-osaka.html",
         board=JP, photo=31261279, title="OSAKA", tagline="5 areas, 10 hotels",
         bullets=["Haruka stops at Osaka Station", "Namba to Umeda: 10 minutes", "Tax: ¥200–500 a night",
                  "Shinsekai for value"], cta="Where to stay in Osaka →",
         pin_title="Where to Stay in Osaka: Umeda or Namba? Trains, Tax and 10 Hotels (2026)",
         description="Since March 2023 the Haruka from Kansai Airport stops at Osaka Station, about 47 minutes "
                     "out. The Midosuji line links Umeda and Namba in about ten minutes, and Osaka's hotel tax "
                     "is ¥200 to ¥500 per person per night on rooms from ¥5,000. Five areas and 10 hotels "
                     "compared."),
    dict(id=1028, slug="kissaten-morning-f2", article="articles/tokyo-kissaten-guide.html",
         board=JP, photo=31338857, title="MORNING SET", tagline="breakfast in an old coffee house",
         bullets=["Toast, egg and coffee", "For little more than coffee", "Until late morning",
                  "Many take cash only"], cta="Nine kissaten to try →",
         pin_title="Kissaten Morning Sets in Tokyo: Toast, Egg and Coffee in an Old Coffee House",
         description="In many of Tokyo's old kissaten, the morning set brings toast, an egg and coffee for "
                     "little more than the coffee alone, served until late morning. Bring cash, order one "
                     "item each, and keep your voice low. Nine kissaten still open in September 2026."),
    # batch 2 (2026-09-28): the trip-level stay guide, for readers still deciding where to base
    dict(id=1029, slug="where-to-stay-japan-f1", article="articles/where-to-stay-in-japan.html",
         board=JP, photo=34297452, title="JAPAN STAYS", tagline="two bases beat four",
         bullets=["7 days: Tokyo 4, Kyoto 3", "10 days: add Osaka 2", "One ryokan night, not three",
                  "Bags sent ahead: next day"], cta="Plan your nights →",
         pin_title="Where to Stay in Japan on a First Trip: How Many Nights in Tokyo, Kyoto and Osaka",
         description="Two bases beat four on a first trip to Japan. For seven or eight days, sleep four nights "
                     "in Tokyo and three in Kyoto, moving once by Shinkansen; with ten days, add two nights in "
                     "Osaka and fly home from Kansai Airport. Give one night, not three, to a ryokan, and send "
                     "the big suitcase ahead: Yamato delivers next day to almost anywhere in Japan."),
    dict(id=1030, slug="shinkansen-luggage-f1", article="articles/where-to-stay-in-japan.html",
         board=JP, photo=10475813, title="BIG BAGS", tagline="on the Shinkansen",
         bullets=["Over 160 cm: reserve a seat", "Up to 250 cm allowed", "The reservation is free",
                  "No booking: ¥1,000 fee"], cta="Moving day, planned →",
         pin_title="Shinkansen Luggage Rules: The 160 cm Limit, Free Seat Reservations and the ¥1,000 Fee",
         description="On the Tokaido Shinkansen, a bag whose length, width and height add up to more than 160 "
                     "cm, and no more than 250 cm, needs a seat with an oversized-baggage area. Reserving it costs "
                     "nothing; without a reservation you pay ¥1,000. Or skip the lifting: Yamato's TA-Q-BIN sends "
                     "a suitcase to your next hotel, next day. Part of our guide to where to stay in Japan."),
]


def check() -> list[str]:
    errors, seen_ids, seen_slugs, seen_photos = [], set(), set(), set()
    archived = {p["image"] for p in json.loads(ARCHIVE.read_text(encoding="utf-8"))["pins"]} \
        if ARCHIVE.exists() else set()
    prev = 1000
    for s in SPECS:
        tag = f"#{s['id']} {s['slug']}"
        if s["id"] <= prev:
            errors.append(f"{tag}: ids must increase")
        prev = s["id"]
        if s["slug"] in seen_slugs or s["photo"] in seen_photos:
            errors.append(f"{tag}: slug or photo used twice")
        seen_ids.add(s["id"]); seen_slugs.add(s["slug"]); seen_photos.add(s["photo"])
        if s["board"] not in BOARDS:
            errors.append(f"{tag}: unknown board {s['board']!r}")
        if not (REPO / "site" / s["article"]).exists():
            errors.append(f"{tag}: article missing: {s['article']}")
        if len(s["pin_title"]) > 100:
            errors.append(f"{tag}: Pinterest title {len(s['pin_title'])} chars (max 100)")
        if len(s["description"]) > 500:
            errors.append(f"{tag}: description {len(s['description'])} chars (max 500)")
        if len(s["title"]) > 13 or len(s["tagline"]) > 32 or len(s["cta"]) > 27:
            errors.append(f"{tag}: title, tagline or button too long for the template")
        if len(s["bullets"]) != 4 or any(len(b) > 30 for b in s["bullets"]):
            errors.append(f"{tag}: needs 4 bullets of at most 30 characters")
        if f"{BASE}/{OUT_DIR}/{s['slug']}.jpg" in archived:
            errors.append(f"{tag}: this image was already posted")
        text = " ".join([s["title"], s["tagline"], s["cta"], s["pin_title"], s["description"], *s["bullets"]]).lower()
        errors += [f"{tag}: banned phrase {b!r}" for b in BANNED if re.search(rf"\b{re.escape(b)}\b", text)]
    return errors


def _get(url: str, **kw) -> requests.Response:
    for attempt in range(4):
        r = requests.get(url, timeout=60, **kw)
        if r.status_code not in (429, 500, 502, 503, 504):
            break
        time.sleep(3 * (attempt + 1))
    r.raise_for_status()
    return r


def photo_url(photo_id: int) -> str:
    """Pexels file names vary, so ask the API for the photo's real address and
    let the CDN crop it to 1000x1500."""
    load_dotenv(REPO / ".env")
    meta = _get(f"https://api.pexels.com/v1/photos/{photo_id}",
                headers={"Authorization": os.environ["PEXELS_API_KEY"]}).json()
    return meta["src"]["original"].split("?")[0] + "?auto=compress&cs=tinysrgb&fit=crop&w=1000&h=1500"


def render(spec: dict, work: Path) -> bytes:
    photo = work / f"{spec['slug']}-photo.jpg"
    photo.write_bytes(_get(photo_url(spec["photo"])).content)
    # a wide word (MELBOURNE) can overrun the template's size-by-length rule
    fit = generate_pin.fit_title_size
    if spec.get("title_size"):
        generate_pin.fit_title_size = lambda _t: spec["title_size"]
    try:
        svg = fill_template(photo_href=encode_data_uri(photo), title=spec["title"], tagline=spec["tagline"],
                            bullets=spec["bullets"], cta=spec["cta"], url_hint="gentlyyonder.com")
    finally:
        generate_pin.fit_title_size = fit
    svg_path, png_path = work / f"{spec['slug']}.svg", work / f"{spec['slug']}.png"
    svg_path.write_text(svg, encoding="utf-8")
    subprocess.run(["rsvg-convert", "-w", "1000", "-h", "1500", str(svg_path), "-o", str(png_path)], check=True)
    buf = io.BytesIO()
    Image.open(png_path).convert("RGB").save(buf, "JPEG", quality=85, optimize=True, progressive=True)
    return buf.getvalue()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate only")
    args = ap.parse_args()

    errors = check()
    if errors:
        sys.exit("\n".join(f"FAIL {e}" for e in errors))
    print(f"{len(SPECS)} specs ok")
    if args.check:
        return

    # the first run moves the pins that were already posted into the archive
    if not ARCHIVE.exists():
        old = json.loads(QUEUE.read_text(encoding="utf-8"))
        ARCHIVE.write_text(json.dumps({
            "note": "Pins posted by the n8n -> Buffer workflow until 2026-09-27. It cycled them, so each "
                    "went out more than once. Never queue these images again.",
            "pins": old["pins"]}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"archived {len(old['pins'])} posted pins")

    made = 0
    with tempfile.TemporaryDirectory() as tmp:
        for s in SPECS:
            outs = [REPO / base / OUT_DIR / f"{s['slug']}.jpg" for base in ("site", "docs")]
            if all(o.exists() for o in outs):
                continue
            data = render(s, Path(tmp))
            for o in outs:
                o.parent.mkdir(parents=True, exist_ok=True)
                o.write_bytes(data)
            made += 1
            print(f"  rendered {s['slug']} ({len(data) // 1024} KB)")

    pins = [{
        "id": s["id"], "slug": s["slug"],
        "image": f"{BASE}/{OUT_DIR}/{s['slug']}.jpg",
        "link": f"{BASE}/{s['article']}?{UTM}",
        "title": s["pin_title"], "description": s["description"], "board": s["board"],
    } for s in SPECS]
    out = json.dumps({"count": len(pins), "pins": pins}, ensure_ascii=False, indent=1)
    for base in ("site", "docs"):
        (REPO / base / "data" / "pins.json").write_text(out, encoding="utf-8")
    print(f"{made} image(s) rendered · queue: {len(pins)} fresh pins (ids {pins[0]['id']}–{pins[-1]['id']})")


if __name__ == "__main__":
    main()
