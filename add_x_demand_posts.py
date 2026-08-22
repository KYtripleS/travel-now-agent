#!/usr/bin/env python3
"""
add_x_demand_posts.py — append demand-matched X posts to the queue.

Topics chosen from the 2026-08-22 data: the pages actually pulling sessions
(non-search / Pinterest) — capsule wardrobe, Australia, Thailand, Bali,
Singapore — none of which had a dedicated post yet. Each post gets a
contextual link ONLY if the complete URL fits within 278 raw chars (the
pipeline truncates on raw length — see add_x_queue_links.py), else it stays
link-free. Idempotent: skips if a post with the same id already exists.

Usage:
  python add_x_demand_posts.py            # dry run
  python add_x_demand_posts.py --write
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent
BASE = "https://gentlyyonder.com/"
MAX_LEN = 278

# (body, link_path). Voice matches the existing queue: specific, calm, no hype.
NEW_POSTS: list[tuple[str, str]] = [
    (
        "Australia isn't one season — it's a continent.\n\n"
        "December–February is beach summer down south, but the tropical north "
        "is deep in the wet.\n\n"
        "Pick the region first, then the month. Not the other way round.",
        "articles/best-time-to-visit-australia.html",
    ),
    (
        "A two-week trip needs about ten clothing items. Not thirty.\n\n"
        "The trick isn't packing less — it's one colour palette where every "
        "piece combines with every other.\n\n"
        "You re-wear. You don't repeat.",
        "articles/capsule-wardrobe-2-week-trips.html",
    ),
    (
        "Thailand in ten days, the honest split:\n\n"
        "3 in Bangkok, 3 in Chiang Mai, 4 on the islands.\n\n"
        "The internal flights are cheap and save you a 12-hour night bus — "
        "book them the week you land on the dates.",
        "articles/thailand-10-day-itinerary.html",
    ),
    (
        "Bali rewards picking a base over chasing the whole island.\n\n"
        "Ubud for the hills and temples. The south for surf and sunsets. "
        "Nusa Penida for the day-trip boat.\n\n"
        "Three of those in three days is the classic mistake.",
        "articles/things-to-do-in-bali.html",
    ),
    (
        "Singapore is expensive to sleep in and cheap to eat in.\n\n"
        "The hawker centres have Michelin-listed stalls for a few dollars.\n\n"
        "Spend on a central hotel; win it all back at Maxwell and Lau Pa Sat.",
        "articles/things-to-do-in-singapore.html",
    ),
]


def linked(body: str, path: str) -> str:
    url = f"{BASE}{path}"
    full = f"{body}\n\n{url}"
    return full if len(full) <= MAX_LEN else body  # link only if it fits


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    src = REPO / "site" / "data" / "x_queue.json"
    data = json.loads(src.read_text(encoding="utf-8"))
    posts = data["posts"]
    next_id = max(p["id"] for p in posts) + 1

    existing_bodies = {p["text"].split("\n\n")[0] for p in posts}
    added = []
    for body, path in NEW_POSTS:
        if body.split("\n\n")[0] in existing_bodies:
            continue
        text = linked(body, path)
        added.append({"id": next_id, "text": text})
        has = "link" if BASE in text else "NO link (too long)"
        print(f'  #{next_id} [{len(text)}] {has} — {body.split(chr(10))[0][:50]}')
        next_id += 1

    over = [p for p in added if len(p["text"]) > 280]
    assert not over, f"raw length over 280: {[p['id'] for p in over]}"

    if not args.write:
        print(f"\n(dry run — would add {len(added)} posts; total would be {len(posts)+len(added)})")
        return

    data["posts"] = posts + added
    out = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    src.write_text(out, encoding="utf-8")
    (REPO / "docs" / "data" / "x_queue.json").write_text(out, encoding="utf-8")
    print(f"\n✓ added {len(added)} posts · queue now {len(data['posts'])} · wrote site/ + docs/")


if __name__ == "__main__":
    main()
