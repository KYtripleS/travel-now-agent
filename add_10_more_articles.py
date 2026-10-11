#!/usr/bin/env python3
"""Add 10 distinct, high-demand travel preparation articles with ZERO keyword cannibalization."""
import csv
from pathlib import Path

# 10 completely fresh, highly searched topics filling distinct preparation gaps
NEW_10_TOPICS = [
    {
        "topic": "Solo Travel Safety Rules: 10 Practical Habits for Safer Trips",
        "category": "Safety",
        "notes": "Essential safety habits for solo travelers covering emergency communication, situational awareness, and scam prevention."
    },
    {
        "topic": "How to Pack Fragile Souvenirs and Liquids in Checked Bags",
        "category": "Packing",
        "notes": "Step-by-step method to pack wine bottles, ceramics, and glassware safely in checked luggage without breakage."
    },
    {
        "topic": "Digital Nomad Tax & Visa Basics: 90-Day Schengen and Nomad Permits",
        "category": "Entry & arrival",
        "notes": "Clear breakdown of tourist visa limits, 90/180 Schengen rolling rules, and legal digital nomad visa requirements."
    },
    {
        "topic": "Train vs Flight in Europe: When Rail Beats Flying on Time and Price",
        "category": "Rail",
        "notes": "Detailed comparison of high-speed rail vs budget airlines in Europe considering security time, luggage fees, and city-center access."
    },
    {
        "topic": "How to Keep Valuables Safe in Hostels and Dorm Rooms",
        "category": "Stay",
        "notes": "Locker protocols, padlock choices, daypack habits, and digital backup techniques for budget backpackers in dorms."
    },
    {
        "topic": "Travel Medical Kit Essentials: What Actually Belongs in Your Pouch",
        "category": "Safety",
        "notes": "Compact, effective travel first-aid and medication checklist covering gastro, blisters, pain relief, and altitude sickness."
    },
    {
        "topic": "How to Choose the Right Travel Shoes: Walking 20,000 Steps Daily",
        "category": "Gear",
        "notes": "Footwear selection guide for cobblestones, rain, and all-day walking without blisters or sore arches."
    },
    {
        "topic": "Airport Layover Survival Guide: Making Long Transit Hours Bearable",
        "category": "Trip planning",
        "notes": "Maximizing 4-to-12 hour layovers with lounge day passes, airport showers, luggage storage, and sleep pods."
    },
    {
        "topic": "Smart Luggage Tracking: AirTags vs Tile vs Smart Bag Rules",
        "category": "Gear",
        "notes": "How to set up Bluetooth bag trackers for air travel, airline battery compliance, and locating delayed baggage."
    },
    {
        "topic": "How to Order Food Abroad with Dietary Restrictions & Allergies",
        "category": "Food",
        "notes": "Practical strategies for navigating gluten-free, vegan, nut allergies, and language barriers in foreign restaurants."
    }
]

log_path = Path("data/content_log.csv")
today = "2026-10-19"
existing = log_path.read_text(encoding="utf-8")

added = 0
with log_path.open("a", newline="", encoding="utf-8") as f:
    for art in NEW_10_TOPICS:
        topic = art["topic"]
        if topic in existing:
            print(f"Skipping (already exists): {topic}")
            continue
        row = f'{today},X,{art["category"]},"{topic}","Practical guide for {topic.lower()}. Before you travel: 1. Review the rules. 2. Compare options. 3. Prepare offline copies. 4. Know your rights.",no CTA,draft,yes,"{art["notes"]}"\n'
        f.write(row)
        added += 1
        print(f"Added: {topic}")

print(f"\nSuccessfully added {added} new articles to content_log.csv")
