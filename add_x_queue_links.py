#!/usr/bin/env python3
"""
add_x_queue_links.py — append a contextual site link to the X (Twitter) queue
posts that map cleanly to a guide, driving referral traffic to the Japan
beachhead + money pages. Pure-engagement / musing posts (1, 32, 35, 36) stay
link-free to preserve reach.

Idempotent: skips any post whose text already contains gentlyyonder.com.
Writes both site/data/x_queue.json and docs/data/x_queue.json.

Usage:
  python add_x_queue_links.py            # dry run (prints before/after)
  python add_x_queue_links.py --write
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent
BASE = "https://gentlyyonder.com/"
MAX_LEN = 280  # standard X limit; a URL counts as 23 regardless of length


def weighted_len(text: str) -> int:
    return len(re.sub(r"https?://\S+", "x" * 23, text))

# id -> (path, lead-in). Omitted ids stay link-free on purpose.
LINKS: dict[int, tuple[str, str]] = {
    2:  ("articles/how-much-cash-japan.html", "How much to actually carry →"),
    3:  ("articles/best-power-bank-travel-2026.html", "The watt-hour rules, in full →"),
    4:  ("articles/jr-pass-worth-it-2026.html", "The full math →"),
    5:  ("articles/pre-flight-checklist-48-hours.html", "The 48-hour checklist →"),
    6:  ("articles/how-much-cash-japan.html", "Where cash still rules →"),
    7:  ("travel-power/", "Plugs by country →"),
    8:  ("articles/airport-security-checklist.html", "The full checklist →"),
    9:  ("articles/best-esim-vietnam-2026.html", "Vietnam eSIM, explained →"),
    10: ("articles/how-much-cash-japan.html", "Cash in Japan, 2026 →"),
    11: ("articles/jr-pass-worth-it-2026.html", "When it does pay off →"),
    12: ("tools/esim-finder.html", "Pick your data size →"),
    13: ("articles/esim-activation-and-preparation.html", "Set it up before you fly →"),
    14: ("articles/travel-insurance-compared.html", "What cards miss →"),
    15: ("articles/first-day-in-tokyo-arrival-plan.html", "Your calm first day →"),
    16: ("articles/what-to-pack-for-japan.html", "The Japan packing list →"),
    17: ("articles/best-esim-japan-korea-vietnam.html", "Regional vs per-country →"),
    18: ("articles/gion-kyoto-neighbourhood-guide.html", "Kyoto, block by block →"),
    19: ("articles/best-power-bank-travel-2026.html", "Which size to carry →"),
    20: ("articles/best-time-to-visit-japan-2026.html", "When to go, honestly →"),
    21: ("articles/luggage-storage-tokyo.html", "How it works →"),
    22: ("articles/tokyo-to-kyoto-shinkansen-vs-flight-vs-bus.html", "All three ways compared →"),
    23: ("articles/charter-a-boat-for-a-day.html", "Where a licence isn't needed →"),
    24: ("articles/klook-vs-kkday.html", "The honest comparison →"),
    25: ("articles/getting-around-melbourne.html", "Getting into the city →"),
    26: ("articles/first-international-trip-checklist.html", "Don't forget these →"),
    27: ("articles/first-day-in-tokyo-arrival-plan.html", "Your smooth arrival →"),
    28: ("articles/pre-flight-checklist-48-hours.html", "The pre-flight checklist →"),
    29: ("articles/best-esim-australia-2026.html", "Australia eSIM →"),
    30: ("articles/travel-insurance-compared.html", "Coverage compared →"),
    31: ("articles/first-international-trip-checklist.html", "The whole checklist →"),
    33: ("articles/first-international-trip-checklist.html", "First-trip checklist →"),
    34: ("articles/capsule-wardrobe-2-week-trips.html", "The capsule method →"),
}


def linked_text(body: str, path: str, lead: str) -> tuple[str, bool]:
    """Append the link, keeping the post within MAX_LEN. Falls back to a bare
    URL (no lead-in) when the lead-in would push the post over the limit."""
    url = f"{BASE}{path}"
    withlead = f"{body}\n\n{lead} {url}"
    if weighted_len(withlead) <= MAX_LEN:
        return withlead, True
    return f"{body}\n\n{url}", False


def apply(posts: list[dict], verbose: bool = False) -> int:
    n = 0
    for p in posts:
        m = LINKS.get(p["id"])
        if not m or "gentlyyonder.com" in p["text"]:
            continue
        path, lead = m
        new, kept = linked_text(p["text"], path, lead)
        if verbose and not kept:
            print(f'  #{p["id"]:>2} lead-in dropped (length) → bare URL')
        p["text"] = new
        n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    src = REPO / "site" / "data" / "x_queue.json"
    data = json.loads(src.read_text(encoding="utf-8"))
    posts = data["posts"]

    linked = [pid for pid in LINKS if any(p["id"] == pid for p in posts)]
    free = [p["id"] for p in posts if p["id"] not in LINKS]
    print(f"posts: {len(posts)} · will link: {len(linked)} · stay link-free: {free}")
    for p in posts:
        if p["id"] in LINKS and "gentlyyonder.com" not in p["text"]:
            path, lead = LINKS[p["id"]]
            print(f'  #{p["id"]:>2} += "{lead} {BASE}{path}"')

    if not args.write:
        print("\n(dry run — pass --write to apply to site/ + docs/)")
        return

    n = apply(posts, verbose=True)
    longest = max(weighted_len(p["text"]) for p in posts)
    over = [p["id"] for p in posts if weighted_len(p["text"]) > MAX_LEN]
    src.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    dst = REPO / "docs" / "data" / "x_queue.json"
    dst.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n✓ linked {n} posts · longest {longest} chars · over-limit {over or 'none'} · wrote site/ + docs/")


if __name__ == "__main__":
    main()
