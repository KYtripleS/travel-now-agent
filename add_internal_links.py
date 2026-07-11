#!/usr/bin/env python3
"""
add_internal_links.py

Inject a "Keep reading on Gently Yonder" section into every public article,
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
    # ---- city first-timer guides (SE/E-Asia expansion) ----
    "articles/singapore-first-timers-guide.html": (
        "Singapore: A First-Timer's Guide",
        "Marina Bay, the hawker centres, Sentosa and the MRT — a calm first orientation to Singapore.",
    ),
    "articles/bangkok-first-timers-guide.html": (
        "Bangkok: A First-Timer's Guide",
        "The Grand Palace and Wat Arun, the markets, street food and the river — how to take on Bangkok.",
    ),
    "articles/bali-first-timers-guide.html": (
        "Bali: A First-Timer's Guide",
        "Ubud's rice terraces, clifftop temples, beaches and warungs — a gentle first orientation to Bali.",
    ),
    "articles/hanoi-first-timers-guide.html": (
        "Hanoi: A First-Timer's Guide",
        "The Old Quarter, Hoan Kiem Lake, egg coffee and pho, and Ha Long day trips.",
    ),
    "articles/ho-chi-minh-city-first-timers-guide.html": (
        "Ho Chi Minh City: A First-Timer's Guide",
        "Ben Thanh Market, the War Remnants Museum, coffee culture, and the Cu Chi Tunnels.",
    ),
    "articles/hoi-an-first-timers-guide.html": (
        "Hoi An: A First-Timer's Guide",
        "The lantern-lit Old Town, the Japanese Bridge, tailors and An Bang Beach.",
    ),
    "articles/kuala-lumpur-first-timers-guide.html": (
        "Kuala Lumpur: A First-Timer's Guide",
        "The Petronas Towers, Batu Caves, street food and easy day trips.",
    ),
    "articles/manila-first-timers-guide.html": (
        "Manila: A First-Timer's Guide",
        "Intramuros, Binondo Chinatown, the Manila Bay sunset, and getting around the traffic.",
    ),
    "articles/cebu-first-timers-guide.html": (
        "Cebu: A First-Timer's Guide",
        "Magellan's Cross, whale sharks (honestly), Kawasan Falls, and island hopping.",
    ),
    "articles/chiang-mai-first-timers-guide.html": (
        "Chiang Mai: A First-Timer's Guide",
        "Old City temples, Doi Suthep, ethical elephant sanctuaries, and khao soi.",
    ),
    "articles/phuket-first-timers-guide.html": (
        "Phuket: A First-Timer's Guide",
        "Choosing your beach, the Sino-Portuguese Old Town, and island-hopping to Phi Phi.",
    ),
    "articles/hong-kong-first-timers-guide.html": (
        "Hong Kong: A First-Timer's Guide",
        "Victoria Peak, the Star Ferry, Lantau's Big Buddha, and dim sum.",
    ),
    "articles/seoul-first-timers-guide.html": (
        "Seoul: A First-Timer's Guide",
        "The royal palaces, Bukchon Hanok Village, Gwangjang Market, and a DMZ day trip.",
    ),
    "articles/osaka-first-timers-guide.html": (
        "Osaka: A First-Timer's Guide",
        "Osaka Castle, Dotonbori, the street food, and an easy day trip to Nara.",
    ),
    "articles/penang-first-timers-guide.html": (
        "Penang: A First-Timer's Guide",
        "George Town's murals and clan jetties, Kek Lok Si, Penang Hill, and hawker food.",
    ),
    "articles/yogyakarta-first-timers-guide.html": (
        "Yogyakarta: A First-Timer's Guide",
        "Borobudur at sunrise, Prambanan, the Kraton, and a Mount Merapi jeep tour.",
    ),
    # ---- 'The places worth your time' city guides (Pinterest-format) ----
    "articles/things-to-do-in-tokyo.html": (
        "Tokyo: The Places Worth Your Time",
        "The best of Tokyo — Senso-ji, Shibuya, Harajuku, Shinjuku, teamLab, and easy day trips.",
    ),
    "articles/things-to-do-in-kyoto.html": (
        "Kyoto: The Places Worth Your Time",
        "Fushimi Inari, Arashiyama, Kiyomizu-dera, the Golden Pavilion, Gion, and a Nara day trip.",
    ),
    "articles/things-to-do-in-bangkok.html": (
        "Bangkok: The Places Worth Your Time",
        "The Grand Palace, Wat Pho and Wat Arun, the river and canals, markets, and Ayutthaya.",
    ),
    "articles/things-to-do-in-seoul.html": (
        "Seoul: The Places Worth Your Time",
        "Gyeongbokgung, Bukchon, N Seoul Tower, Myeongdong, Gwangjang Market, and a DMZ day trip.",
    ),
    "articles/things-to-do-in-osaka.html": (
        "Osaka: The Places Worth Your Time",
        "Osaka Castle, Dotonbori, Shinsekai's kushikatsu, Universal Studios, and a Nara day trip.",
    ),
    "articles/things-to-do-in-singapore.html": (
        "Singapore: The Places Worth Your Time",
        "Marina Bay, Gardens by the Bay, the cultural quarters, the hawker centres, and Sentosa.",
    ),
    "articles/things-to-do-in-bali.html": (
        "Bali: The Places Worth Your Time",
        "Ubud and the rice terraces, the great temples, the surf south, Nusa Penida, and Mount Batur.",
    ),
    "articles/things-to-do-in-hong-kong.html": (
        "Hong Kong: The Places Worth Your Time",
        "Victoria Peak, the Star Ferry, Kowloon's markets, the Big Buddha, and dim sum.",
    ),
    "articles/things-to-do-in-hanoi.html": (
        "Hanoi: The Places Worth Your Time",
        "The Old Quarter and Hoan Kiem Lake, the Temple of Literature, Train Street, egg coffee, and Ha Long Bay.",
    ),
    "articles/things-to-do-in-ho-chi-minh-city.html": (
        "Ho Chi Minh City: The Places Worth Your Time",
        "The War Remnants Museum, the colonial core, Ben Thanh, Landmark 81, and the Mekong Delta.",
    ),
    "articles/things-to-do-in-kuala-lumpur.html": (
        "Kuala Lumpur: The Places Worth Your Time",
        "The Petronas Towers, Batu Caves, the colonial core, the Islamic Arts Museum, and Jalan Alor.",
    ),
    "articles/things-to-do-in-manila.html": (
        "Manila: The Places Worth Your Time",
        "Intramuros, Rizal Park and the National Museum, Binondo, the Manila Bay sunset, and Corregidor.",
    ),
    "articles/things-to-do-in-chiang-mai.html": (
        "Chiang Mai: The Places Worth Your Time",
        "The Old City temples, Doi Suthep, ethical elephants, the markets, khao soi, and Doi Inthanon.",
    ),
    "articles/things-to-do-in-phuket.html": (
        "Phuket: The Places Worth Your Time",
        "Choosing your beach, the Old Town, the Big Buddha, and island-hopping to Phi Phi and Phang Nga.",
    ),
    "articles/airport-security-bag-rules.html": (
        "Airport Security Bag Rules",
        "What gets flagged at the X-ray belt and how to repack to avoid the bin.",
    ),
    "articles/airport-security-checklist.html": (
        "Airport Security Checklist (12-Point Pre-Flight)",
        "A 12-point pre-flight verification covering documents, liquids, electronics, and prohibited items.",
    ),
    "articles/safetywing-vs-world-nomads.html": (
        "SafetyWing vs World Nomads",
        "A head-to-head insurance comparison — coverage, pricing, claims, and who each suits best.",
    ),
    "articles/airalo-vs-holafly-vs-saily.html": (
        "Airalo vs Holafly vs Saily",
        "The three big travel eSIM providers compared — coverage, pricing, and who each suits.",
    ),
    "articles/best-esim-japan-2026.html": (
        "Best eSIM for Japan (2026)",
        "How to choose a Japan travel eSIM — coverage, data plans, and the pick for most trips.",
    ),
    "articles/best-esim-japan-korea-vietnam.html": (
        "Best eSIM for Japan, Korea & Vietnam",
        "Destination-by-destination eSIM picks for three popular Asian countries.",
    ),
    "articles/pocket-wifi-vs-esim.html": (
        "Pocket WiFi vs eSIM",
        "Which connectivity option wins — solo vs group, cost, battery, and setup compared.",
    ),
    "articles/klook-vs-viator-vs-getyourguide.html": (
        "Klook vs Viator vs GetYourGuide",
        "Which tours-and-activities platform to use where — Asia, Europe, and global.",
    ),
    "articles/best-travel-insurance-digital-nomads-2026.html": (
        "Best Travel Insurance for Digital Nomads",
        "A 2026 buyer's guide — what nomad cover needs, by traveler archetype.",
    ),
    "articles/carry-on-packing-list-10-day-japan.html": (
        "Carry-On Packing List for a 10-Day Japan Trip",
        "A 10-item capsule sized for Japan — plugs, cash, IC cards, and the right shoes.",
    ),
    "articles/luggage-storage-tokyo.html": (
        "Where to Store Luggage in Tokyo",
        "Coin lockers, cloakrooms, storage apps, and hotel holds — which to use where.",
    ),
    "articles/best-esim-europe-2026.html": (
        "Best eSIM for Europe (2026)",
        "Why a regional Europe plan usually beats country-by-country, and how much data to get.",
    ),
    "articles/best-esim-thailand-2026.html": (
        "Best eSIM for Thailand (2026)",
        "Coverage across Bangkok, Chiang Mai, and the islands, and how much data you'll need.",
    ),
    "articles/three-slow-days-in-kyoto.html": (
        "Three Slow Days in Kyoto",
        "A gentle, unhurried first-timer's itinerary — Fushimi Inari at dawn to Arashiyama's bamboo.",
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
    # ---- city guides -> harvest targets (etiquette + eSIM + boat) + tours/insurance + sibling cities ----
    "articles/singapore-first-timers-guide.html": [
        "articles/what-counts-as-rude.html",
        "articles/airalo-vs-holafly-vs-saily.html",
        "articles/klook-vs-viator-vs-getyourguide.html",
        "articles/kuala-lumpur-first-timers-guide.html",
        "articles/bangkok-first-timers-guide.html",
    ],
    "articles/bangkok-first-timers-guide.html": [
        "articles/things-to-do-in-bangkok.html",
        "articles/what-counts-as-rude.html",
        "articles/best-esim-thailand-2026.html",
        "articles/klook-vs-viator-vs-getyourguide.html",
        "articles/chiang-mai-first-timers-guide.html",
    ],
    "articles/bali-first-timers-guide.html": [
        "articles/untranslatable-words.html",
        "articles/airalo-vs-holafly-vs-saily.html",
        "articles/travel-insurance-compared.html",
        "articles/yogyakarta-first-timers-guide.html",
        "articles/bangkok-first-timers-guide.html",
    ],
    "articles/hanoi-first-timers-guide.html": [
        "articles/what-counts-as-rude.html",
        "articles/best-esim-japan-korea-vietnam.html",
        "articles/klook-vs-viator-vs-getyourguide.html",
        "articles/ho-chi-minh-city-first-timers-guide.html",
        "articles/hoi-an-first-timers-guide.html",
    ],
    "articles/ho-chi-minh-city-first-timers-guide.html": [
        "articles/what-counts-as-rude.html",
        "articles/best-esim-japan-korea-vietnam.html",
        "articles/klook-vs-viator-vs-getyourguide.html",
        "articles/hanoi-first-timers-guide.html",
        "articles/hoi-an-first-timers-guide.html",
    ],
    "articles/hoi-an-first-timers-guide.html": [
        "articles/untranslatable-words.html",
        "articles/best-esim-japan-korea-vietnam.html",
        "articles/charter-a-boat-for-a-day.html",
        "articles/hanoi-first-timers-guide.html",
        "articles/ho-chi-minh-city-first-timers-guide.html",
    ],
    "articles/kuala-lumpur-first-timers-guide.html": [
        "articles/what-counts-as-rude.html",
        "articles/airalo-vs-holafly-vs-saily.html",
        "articles/klook-vs-viator-vs-getyourguide.html",
        "articles/penang-first-timers-guide.html",
        "articles/singapore-first-timers-guide.html",
    ],
    "articles/manila-first-timers-guide.html": [
        "articles/what-counts-as-rude.html",
        "articles/airalo-vs-holafly-vs-saily.html",
        "articles/travel-insurance-compared.html",
        "articles/cebu-first-timers-guide.html",
        "articles/kuala-lumpur-first-timers-guide.html",
    ],
    "articles/cebu-first-timers-guide.html": [
        "articles/untranslatable-words.html",
        "articles/airalo-vs-holafly-vs-saily.html",
        "articles/charter-a-boat-for-a-day.html",
        "articles/manila-first-timers-guide.html",
        "articles/phuket-first-timers-guide.html",
    ],
    "articles/chiang-mai-first-timers-guide.html": [
        "articles/what-counts-as-rude.html",
        "articles/best-esim-thailand-2026.html",
        "articles/klook-vs-viator-vs-getyourguide.html",
        "articles/bangkok-first-timers-guide.html",
        "articles/phuket-first-timers-guide.html",
    ],
    "articles/phuket-first-timers-guide.html": [
        "articles/untranslatable-words.html",
        "articles/best-esim-thailand-2026.html",
        "articles/charter-a-boat-for-a-day.html",
        "articles/bangkok-first-timers-guide.html",
        "articles/chiang-mai-first-timers-guide.html",
    ],
    "articles/hong-kong-first-timers-guide.html": [
        "articles/what-counts-as-rude.html",
        "articles/airalo-vs-holafly-vs-saily.html",
        "articles/klook-vs-viator-vs-getyourguide.html",
        "articles/osaka-first-timers-guide.html",
        "articles/seoul-first-timers-guide.html",
    ],
    "articles/seoul-first-timers-guide.html": [
        "articles/what-counts-as-rude.html",
        "articles/best-esim-japan-korea-vietnam.html",
        "articles/south-korea-country-profile.html",
        "articles/osaka-first-timers-guide.html",
        "articles/hong-kong-first-timers-guide.html",
    ],
    "articles/osaka-first-timers-guide.html": [
        "articles/untranslatable-words.html",
        "articles/best-esim-japan-2026.html",
        "articles/luggage-storage-tokyo.html",
        "articles/carry-on-packing-list-10-day-japan.html",
        "articles/seoul-first-timers-guide.html",
    ],
    "articles/penang-first-timers-guide.html": [
        "articles/what-counts-as-rude.html",
        "articles/airalo-vs-holafly-vs-saily.html",
        "articles/klook-vs-viator-vs-getyourguide.html",
        "articles/kuala-lumpur-first-timers-guide.html",
        "articles/singapore-first-timers-guide.html",
    ],
    "articles/yogyakarta-first-timers-guide.html": [
        "articles/untranslatable-words.html",
        "articles/airalo-vs-holafly-vs-saily.html",
        "articles/klook-vs-viator-vs-getyourguide.html",
        "articles/bali-first-timers-guide.html",
        "articles/singapore-first-timers-guide.html",
    ],
    "articles/things-to-do-in-tokyo.html": [
        "articles/best-esim-japan-2026.html",
        "cities/tokyo/index.html",
        "articles/luggage-storage-tokyo.html",
        "articles/things-to-do-in-kyoto.html",
        "articles/carry-on-packing-list-10-day-japan.html",
    ],
    "articles/things-to-do-in-kyoto.html": [
        "articles/best-esim-japan-2026.html",
        "articles/three-slow-days-in-kyoto.html",
        "articles/things-to-do-in-tokyo.html",
        "countries/japan/index.html",
        "articles/untranslatable-words.html",
    ],
    "articles/things-to-do-in-bangkok.html": [
        "articles/bangkok-first-timers-guide.html",
        "articles/best-esim-thailand-2026.html",
        "articles/what-counts-as-rude.html",
        "articles/chiang-mai-first-timers-guide.html",
        "articles/klook-vs-viator-vs-getyourguide.html",
    ],
    "articles/things-to-do-in-seoul.html": [
        "articles/seoul-first-timers-guide.html",
        "articles/best-esim-japan-korea-vietnam.html",
        "articles/what-counts-as-rude.html",
        "articles/things-to-do-in-osaka.html",
        "articles/klook-vs-viator-vs-getyourguide.html",
    ],
    "articles/things-to-do-in-osaka.html": [
        "articles/osaka-first-timers-guide.html",
        "articles/best-esim-japan-2026.html",
        "articles/things-to-do-in-kyoto.html",
        "articles/luggage-storage-tokyo.html",
        "articles/things-to-do-in-seoul.html",
    ],
    "articles/things-to-do-in-singapore.html": [
        "articles/singapore-first-timers-guide.html",
        "articles/airalo-vs-holafly-vs-saily.html",
        "articles/what-counts-as-rude.html",
        "articles/things-to-do-in-bangkok.html",
        "articles/klook-vs-viator-vs-getyourguide.html",
    ],
    "articles/things-to-do-in-bali.html": [
        "articles/bali-first-timers-guide.html",
        "articles/airalo-vs-holafly-vs-saily.html",
        "articles/things-to-do-in-singapore.html",
        "articles/travel-insurance-compared.html",
        "articles/what-counts-as-rude.html",
    ],
    "articles/things-to-do-in-hong-kong.html": [
        "articles/hong-kong-first-timers-guide.html",
        "articles/airalo-vs-holafly-vs-saily.html",
        "articles/what-counts-as-rude.html",
        "articles/things-to-do-in-osaka.html",
        "articles/klook-vs-viator-vs-getyourguide.html",
    ],
    "articles/things-to-do-in-hanoi.html": [
        "articles/hanoi-first-timers-guide.html",
        "articles/best-esim-japan-korea-vietnam.html",
        "articles/things-to-do-in-ho-chi-minh-city.html",
        "articles/what-counts-as-rude.html",
        "articles/klook-vs-viator-vs-getyourguide.html",
    ],
    "articles/things-to-do-in-ho-chi-minh-city.html": [
        "articles/ho-chi-minh-city-first-timers-guide.html",
        "articles/best-esim-japan-korea-vietnam.html",
        "articles/things-to-do-in-hanoi.html",
        "articles/what-counts-as-rude.html",
        "articles/klook-vs-viator-vs-getyourguide.html",
    ],
    "articles/things-to-do-in-kuala-lumpur.html": [
        "articles/kuala-lumpur-first-timers-guide.html",
        "articles/airalo-vs-holafly-vs-saily.html",
        "articles/things-to-do-in-singapore.html",
        "articles/what-counts-as-rude.html",
        "articles/klook-vs-viator-vs-getyourguide.html",
    ],
    "articles/things-to-do-in-manila.html": [
        "articles/manila-first-timers-guide.html",
        "articles/airalo-vs-holafly-vs-saily.html",
        "articles/things-to-do-in-hong-kong.html",
        "articles/travel-insurance-compared.html",
        "articles/what-counts-as-rude.html",
    ],
    "articles/things-to-do-in-chiang-mai.html": [
        "articles/chiang-mai-first-timers-guide.html",
        "articles/best-esim-thailand-2026.html",
        "articles/things-to-do-in-bangkok.html",
        "articles/what-counts-as-rude.html",
        "articles/klook-vs-viator-vs-getyourguide.html",
    ],
    "articles/things-to-do-in-phuket.html": [
        "articles/phuket-first-timers-guide.html",
        "articles/best-esim-thailand-2026.html",
        "articles/things-to-do-in-bangkok.html",
        "articles/charter-a-boat-for-a-day.html",
        "articles/what-counts-as-rude.html",
    ],
    "articles/airport-security-bag-rules.html": [
        "articles/airport-security-checklist.html",
        "articles/airport-security-liquids.html",
        "articles/airport-security-packing-moments.html",
        "articles/everyday-carry-essentials-for-travel.html",
        "articles/capsule-wardrobe-2-week-trips.html",
        "articles/esim-activation-and-preparation.html",
    ],
    "articles/airport-security-checklist.html": [
        "articles/airport-security-bag-rules.html",
        "articles/airport-security-liquids.html",
        "articles/airport-security-packing-moments.html",
        "articles/everyday-carry-essentials-for-travel.html",
        "articles/capsule-wardrobe-2-week-trips.html",
        "articles/travel-insurance-compared.html",
        "articles/esim-activation-and-preparation.html",
    ],
    "articles/airport-security-liquids.html": [
        "articles/airport-security-checklist.html",
        "articles/airport-security-bag-rules.html",
        "articles/airport-security-packing-moments.html",
        "articles/everyday-carry-essentials-for-travel.html",
        "articles/capsule-wardrobe-2-week-trips.html",
        "articles/esim-activation-and-preparation.html",
    ],
    "articles/airport-security-packing-moments.html": [
        "articles/airport-security-checklist.html",
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
        "articles/carry-on-packing-list-10-day-japan.html",
        "articles/beach-trip-packing-checklist.html",
        "articles/everyday-carry-essentials-for-travel.html",
        "articles/airport-security-bag-rules.html",
        "countries/japan/index.html",
        "countries/vietnam/index.html",
    ],
    "articles/charter-a-boat-for-a-day.html": [
        "articles/travel-insurance-compared.html",
        "articles/everyday-carry-essentials-for-travel.html",
        "articles/hotel-booking-sites-comparison.html",
        "articles/untranslatable-words.html",
    ],
    "articles/esim-activation-and-preparation.html": [
        "articles/best-esim-japan-2026.html",
        "articles/airalo-vs-holafly-vs-saily.html",
        "articles/best-esim-japan-korea-vietnam.html",
        "articles/pocket-wifi-vs-esim.html",
        "articles/hotel-booking-sites-comparison.html",
        "articles/travel-insurance-compared.html",
        "countries/japan/index.html",
    ],
    "articles/everyday-carry-essentials-for-travel.html": [
        "articles/airport-security-checklist.html",
        "articles/airport-security-bag-rules.html",
        "articles/capsule-wardrobe-2-week-trips.html",
        "articles/beach-trip-packing-checklist.html",
        "articles/esim-activation-and-preparation.html",
        "articles/travel-insurance-compared.html",
    ],
    "articles/hotel-booking-sites-comparison.html": [
        "articles/klook-vs-viator-vs-getyourguide.html",
        "articles/airalo-vs-holafly-vs-saily.html",
        "articles/travel-insurance-compared.html",
        "countries/japan/index.html",
        "cities/tokyo/index.html",
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
        "articles/safetywing-vs-world-nomads.html",
        "articles/best-travel-insurance-digital-nomads-2026.html",
        "articles/esim-activation-and-preparation.html",
        "articles/hotel-booking-sites-comparison.html",
        "articles/charter-a-boat-for-a-day.html",
        "countries/japan/index.html",
    ],
    "articles/safetywing-vs-world-nomads.html": [
        "articles/best-travel-insurance-digital-nomads-2026.html",
        "articles/travel-insurance-compared.html",
        "articles/esim-activation-and-preparation.html",
        "articles/everyday-carry-essentials-for-travel.html",
        "countries/japan/index.html",
        "countries/vietnam/index.html",
        "countries/australia/index.html",
    ],
    "articles/airalo-vs-holafly-vs-saily.html": [
        "articles/best-esim-japan-2026.html",
        "articles/best-esim-japan-korea-vietnam.html",
        "articles/best-esim-europe-2026.html",
        "articles/best-esim-thailand-2026.html",
        "articles/pocket-wifi-vs-esim.html",
        "articles/esim-activation-and-preparation.html",
        "articles/travel-insurance-compared.html",
    ],
    "articles/best-esim-japan-2026.html": [
        "articles/best-esim-japan-korea-vietnam.html",
        "articles/airalo-vs-holafly-vs-saily.html",
        "articles/pocket-wifi-vs-esim.html",
        "articles/esim-activation-and-preparation.html",
        "articles/travel-insurance-compared.html",
    ],
    "articles/best-esim-japan-korea-vietnam.html": [
        "articles/best-esim-japan-2026.html",
        "articles/best-esim-thailand-2026.html",
        "articles/airalo-vs-holafly-vs-saily.html",
        "articles/pocket-wifi-vs-esim.html",
        "articles/esim-activation-and-preparation.html",
        "countries/japan/index.html",
    ],
    "articles/best-esim-europe-2026.html": [
        "articles/best-esim-japan-korea-vietnam.html",
        "articles/best-esim-thailand-2026.html",
        "articles/airalo-vs-holafly-vs-saily.html",
        "articles/pocket-wifi-vs-esim.html",
        "articles/esim-activation-and-preparation.html",
        "articles/travel-insurance-compared.html",
    ],
    "articles/best-esim-thailand-2026.html": [
        "articles/best-esim-japan-korea-vietnam.html",
        "articles/best-esim-europe-2026.html",
        "articles/airalo-vs-holafly-vs-saily.html",
        "articles/pocket-wifi-vs-esim.html",
        "articles/esim-activation-and-preparation.html",
        "articles/carry-on-packing-list-10-day-japan.html",
    ],
    "articles/three-slow-days-in-kyoto.html": [
        "cities/tokyo/index.html",
        "cities/tokyo/asakusa.html",
        "countries/japan/index.html",
        "articles/carry-on-packing-list-10-day-japan.html",
        "articles/best-esim-japan-korea-vietnam.html",
        "articles/klook-vs-viator-vs-getyourguide.html",
    ],
    "articles/pocket-wifi-vs-esim.html": [
        "articles/best-esim-japan-2026.html",
        "articles/airalo-vs-holafly-vs-saily.html",
        "articles/best-esim-japan-korea-vietnam.html",
        "articles/esim-activation-and-preparation.html",
        "articles/everyday-carry-essentials-for-travel.html",
        "countries/japan/index.html",
    ],
    "articles/klook-vs-viator-vs-getyourguide.html": [
        "cities/tokyo/index.html",
        "cities/tokyo/asakusa.html",
        "countries/japan/index.html",
        "articles/south-korea-country-profile.html",
        "articles/esim-activation-and-preparation.html",
        "countries/vietnam/index.html",
    ],
    "articles/best-travel-insurance-digital-nomads-2026.html": [
        "articles/safetywing-vs-world-nomads.html",
        "articles/travel-insurance-compared.html",
        "articles/esim-activation-and-preparation.html",
        "articles/pocket-wifi-vs-esim.html",
        "articles/everyday-carry-essentials-for-travel.html",
        "countries/japan/index.html",
    ],
    "articles/carry-on-packing-list-10-day-japan.html": [
        "articles/capsule-wardrobe-2-week-trips.html",
        "articles/everyday-carry-essentials-for-travel.html",
        "articles/best-esim-japan-2026.html",
        "countries/japan/index.html",
        "cities/tokyo/index.html",
        "articles/luggage-storage-tokyo.html",
    ],
    "articles/luggage-storage-tokyo.html": [
        "cities/tokyo/index.html",
        "cities/tokyo/asakusa.html",
        "countries/japan/index.html",
        "articles/carry-on-packing-list-10-day-japan.html",
        "articles/best-esim-japan-korea-vietnam.html",
        "articles/klook-vs-viator-vs-getyourguide.html",
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
        "articles/three-slow-days-in-kyoto.html",
        "articles/klook-vs-viator-vs-getyourguide.html",
        "articles/best-esim-japan-korea-vietnam.html",
        "articles/carry-on-packing-list-10-day-japan.html",
        "articles/south-korea-country-profile.html",
    ],
    "cities/tokyo/index.html": [
        "countries/japan/index.html",
        "articles/three-slow-days-in-kyoto.html",
        "cities/tokyo/asakusa.html",
        "articles/luggage-storage-tokyo.html",
        "articles/carry-on-packing-list-10-day-japan.html",
        "articles/klook-vs-viator-vs-getyourguide.html",
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
        f'<h2>Keep reading on Gently Yonder</h2>\n'
        f'<ul>\n'
        f'{items_html}\n'
        f'</ul>\n'
        f'</section>\n'
        f'{MARK_END}'
    )


def inject(html: str, section: str) -> tuple[str, bool]:
    # If an existing block is present, replace it (so adding new articles to
    # the registry updates already-injected pages without manual cleanup).
    if MARK_BEGIN in html and MARK_END in html:
        b = html.find(MARK_BEGIN)
        e = html.find(MARK_END, b) + len(MARK_END)
        existing = html[b:e]
        if existing.strip() == section.strip():
            return html, False
        return html[:b] + section + html[e:], True
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
