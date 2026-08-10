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
# The posting pipeline (Buffer/n8n) truncates on RAW characters — it does NOT
# apply X's t.co URL weighting — so a long URL at the end gets cut mid-string.
# We therefore budget by RAW length and only link a post when the COMPLETE URL
# fits; otherwise the post stays link-free (a broken link is worse than none).
MAX_LEN = 278  # raw chars, with a small safety margin under X's 280

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


def linked_text(body: str, path: str, lead: str) -> tuple[str | None, str]:
    """Return (new_text, mode). Only appends a link when the COMPLETE URL fits
    within MAX_LEN raw chars — lead-in if it fits, else a bare URL. If even the
    bare URL does not fit, returns (None, 'skip') and the post stays link-free."""
    url = f"{BASE}{path}"
    withlead = f"{body}\n\n{lead} {url}"
    if len(withlead) <= MAX_LEN:
        return withlead, "lead"
    bare = f"{body}\n\n{url}"
    if len(bare) <= MAX_LEN:
        return bare, "bare"
    return None, "skip"


def apply(posts: list[dict], verbose: bool = False) -> tuple[int, list[int]]:
    n = 0
    skipped: list[int] = []
    for p in posts:
        m = LINKS.get(p["id"])
        if not m or "gentlyyonder.com" in p["text"]:
            continue
        path, lead = m
        new, mode = linked_text(p["text"], path, lead)
        if mode == "skip":
            skipped.append(p["id"])
            if verbose:
                print(f'  #{p["id"]:>2} SKIP (URL would not fit in {MAX_LEN} raw) → left link-free')
            continue
        if verbose and mode == "bare":
            print(f'  #{p["id"]:>2} bare URL (lead-in dropped for length)')
        p["text"] = new
        n += 1
    return n, skipped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    src = REPO / "site" / "data" / "x_queue.json"
    data = json.loads(src.read_text(encoding="utf-8"))
    posts = data["posts"]

    would_link, would_skip = 0, []
    for p in posts:
        if p["id"] not in LINKS or "gentlyyonder.com" in p["text"]:
            continue
        path, lead = LINKS[p["id"]]
        new, mode = linked_text(p["text"], path, lead)
        if mode == "skip":
            would_skip.append(p["id"])
            print(f'  #{p["id"]:>2} SKIP — full URL exceeds {MAX_LEN} raw, stays link-free')
        else:
            would_link += 1
            tail = new[len(p["text"]):].strip()
            print(f'  #{p["id"]:>2} [{len(new)}] += {tail}')
    print(f"\nwould link: {would_link} · would skip (link-free): {would_skip}")

    if not args.write:
        print("\n(dry run — pass --write to apply to site/ + docs/)")
        return

    n, skipped = apply(posts, verbose=True)
    longest = max(len(p["text"]) for p in posts)
    over = [p["id"] for p in posts if len(p["text"]) > 280]
    assert not over, f"RAW length still over 280 for {over} — refusing to write"
    src.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    dst = REPO / "docs" / "data" / "x_queue.json"
    dst.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n✓ linked {n} posts · left link-free (too long): {skipped or 'none'} · "
          f"longest raw {longest} · wrote site/ + docs/")


if __name__ == "__main__":
    main()
