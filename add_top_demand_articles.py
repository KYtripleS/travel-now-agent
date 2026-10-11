#!/usr/bin/env python3
"""Add 5 high-demand travel preparation and comparison articles to content_log.csv and generate them."""
import csv
from datetime import date
from pathlib import Path

NEW_ARTICLES = [
    {
        "topic": "Best Travel Backpacks 2026: Carry-On Size Limits & Ergonomics Compared",
        "category": "Packing",
        "notes": "Comprehensive comparison of top travel backpacks under 40L for strict carry-on size limits, laptop protection, and harness comfort."
    },
    {
        "topic": "How to Avoid International Roaming Fees: eSIM vs Local SIM vs Pocket WiFi",
        "category": "Connectivity",
        "notes": "Definitive breakdown of how to eliminate carrier roaming charges when traveling abroad with cost, speed, and setup comparisons."
    },
    {
        "topic": "Credit Card Foreign Transaction Fees Explained: Best Cards for Travel",
        "category": "Money & costs",
        "notes": "Guide to avoiding 3% foreign transaction fees, understanding dynamic currency conversion (DCC) scams at ATMs, and top no-foreign-fee travel cards."
    },
    {
        "topic": "How to Recover Cancelled or Delayed Flights: Passenger Rights & Compensation",
        "category": "Flight",
        "notes": "Step-by-step guide to claiming compensation under EU261, US DOT rules, and travel insurance when flights are delayed or cancelled."
    },
    {
        "topic": "Jet Lag Protocol: Science-Backed Strategies for Fast Adjustment",
        "category": "Trip planning",
        "notes": "Circadian rhythm adjustment guide using melatonin timing, light exposure, caffeine management, and meal scheduling for long-haul travel."
    }
]

def update_content_log():
    log_path = Path("data/content_log.csv")
    today = "2026-10-19"
    
    existing = log_path.read_text(encoding="utf-8")
    
    added = 0
    with log_path.open("a", newline="", encoding="utf-8") as f:
        for art in NEW_ARTICLES:
            topic = art["topic"]
            slug = topic.lower().replace(":", "").replace("?", "").replace(",", "").replace(" ", "-").replace("--", "-")
            # check if topic already in log
            if topic in existing:
                print(f"Already in log: {topic}")
                continue
            # row: date,platform,category,topic,post_text,cta,status,article_candidate,notes
            row = f'{today},X,{art["category"]},"{topic}","Practical guide for {topic.lower()}. Before you travel: 1. Review the rules. 2. Compare options. 3. Prepare offline copies. 4. Know your rights.",no CTA,draft,yes,"{art["notes"]}"\n'
            f.write(row)
            added += 1
            print(f"Added to log: {topic}")
            
    print(f"Added {added} new article candidates to content_log.csv")

if __name__ == "__main__":
    update_content_log()
