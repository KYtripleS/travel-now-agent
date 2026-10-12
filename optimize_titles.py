#!/usr/bin/env python3
"""Optimize titles of top-impression, low-CTR articles for higher click-through rate."""
import re
from pathlib import Path

# Title rewrites optimized for search intent and CTR
REWRITES = {
    "klook-vs-viator-vs-getyourguide.html": (
        "Klook vs Viator vs GetYourGuide (2026): Which Is Cheaper & Better?",
        "Honest comparison of Klook, Viator, and GetYourGuide. Compare prices, cancellation policies, tour availability, and mobile app experience before booking."
    ),
    "travel-insurance-japan.html": (
        "Japan Travel Insurance (2026): Is It Worth It? (Costs & Coverage)",
        "Do you really need travel insurance for Japan? Real hospital costs, credit card coverage gaps, and recommended providers for medical and trip disruption."
    ),
    "carry-on-packing-list-10-day-japan.html": (
        "10-Day Japan Carry-On Packing List (2026): Capsule Wardrobe & Tech",
        "Pack 10 days in Japan into one carry-on: a capsule wardrobe by season, walking shoes, a Type A adapter and power bank, laundry and cabin bag limits."
    ),
    "airport-security-checklist.html": (
        "Airport Security Checklist 2026: 12 Pre-Flight Liquid & Tech Rules",
        "Get through airport security faster. Clear carry-on rules for liquids, power banks, laptops, shoes, and TSA/international screening guidelines."
    ),
    "suica-pasmo-ic-cards-guide.html": (
        "Suica vs Pasmo IC Cards Guide (2026): Apple Wallet & Welcome Suica",
        "Everything about Japan IC cards: Suica vs Pasmo, adding to iPhone Apple Wallet, Welcome Suica for tourists, and paying for trains, buses & konbini."
    ),
    "capsule-wardrobe-2-week-trips.html": (
        "2-Week Travel Capsule Wardrobe: 10 Essential Clothing Pieces (2026)",
        "Pack for a 2-week trip in one carry-on. Step-by-step capsule wardrobe template with 10 mix-and-match pieces for hot, cold, and variable climates."
    ),
    "where-to-stay-in-tokyo.html": (
        "Where to Stay in Tokyo (2026): Best Neighbourhoods & Hotel Picks",
        "Honest guide to Tokyo's 6 best areas to stay: Shinjuku, Shibuya, Ginza, Asakusa, Ueno, and Tokyo Station compared with budget, boutique & luxury hotels."
    ),
    "pocket-wifi-vs-esim.html": (
        "Pocket WiFi vs eSIM (2026): Speed, Cost & Data Compared",
        "Pocket WiFi or eSIM? Speed, data limits, battery life, sharing between devices and total cost compared, with simple rules for choosing on your trip."
    ),
    "japan-book-in-advance-2026.html": (
        "Japan Tickets to Book in Advance (2026): Timelines & Selling-Fast Sights",
        "Don't miss out in Japan: when to book the Ghibli Museum, teamLab, Shibuya Sky, popular parks, workshops, restaurants and ryokans, with a booking calendar."
    ),
    "what-counts-as-rude.html": (
        "Cultural Etiquette Guide: What Counts as Rude in 12 Destinations",
        "Avoid accidental offence abroad: tipping, shoes, gestures, noise and table manners in 12 countries, from Japan and Thailand to France, Brazil and the US."
    )
}

for filename, (new_title, new_desc) in REWRITES.items():
    site_f = Path("site/articles") / filename
    docs_f = Path("docs/articles") / filename
    if not site_f.exists():
        print(f"MISSING: {filename}")
        continue
    content = site_f.read_text(encoding="utf-8")
    
    # Replace <title>
    content = re.sub(r'<title>[^<]+</title>', f'<title>{new_title} | Gently Yonder</title>', content)
    
    # Replace or add <meta name="description">
    # A page may already carry its description in either attribute order
    # (<meta content=".." name="description"/> from the publisher); replace that one, never add a second.
    content = re.sub(r'<meta content="[^"]*" name="description"/>\n?', '', content)
    if '<meta name="description"' in content:
        content = re.sub(r'<meta name="description" content="[^"]*" />', f'<meta name="description" content="{new_desc}" />', content)
    else:
        content = re.sub(r'(<title>.+?</title>\s*)', r'\1<meta name="description" content="' + new_desc + '" />\n', content, count=1)
    
    site_f.write_text(content, encoding="utf-8")
    docs_f.write_text(content, encoding="utf-8")
    print(f"UPDATED: {filename}")

print("\nFinished title and description optimization for TOP 10 impression pages.")
