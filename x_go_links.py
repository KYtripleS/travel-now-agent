#!/usr/bin/env python3
"""
x_go_links.py — give every demand-matched X post a link, even the ones too long
for a full URL.

The n8n/Buffer pipeline truncates on RAW characters, so a 55-63 char article URL
won't fit posts already near 280. Fix: short redirect pages at /go/<key> (~24
chars) that meta-refresh + canonical to the real article. This lets the
previously link-free posts carry a working link within 280 raw chars.

Generates site/go/<key>.html + docs/go/<key>.html (noindex, canonical to the
target, style-v2.css so audit passes) and appends short links to the link-free
posts in x_queue.json. Idempotent.

Usage:
  python x_go_links.py            # dry run
  python x_go_links.py --write
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent
DOMAIN = "gentlyyonder.com"
MAX_LEN = 278

# short key -> target article path (built once, reusable for future posts too)
REDIRECTS: dict[str, str] = {
    "pf":   "articles/pre-flight-checklist-48-hours.html",
    "cash": "articles/how-much-cash-japan.html",
    "sec":  "articles/airport-security-checklist.html",
    "vn":   "articles/best-esim-vietnam-2026.html",
    "jr":   "articles/jr-pass-worth-it-2026.html",
    "ins":  "articles/travel-insurance-compared.html",
    "gion": "articles/gion-kyoto-neighbourhood-guide.html",
    "pb":   "articles/best-power-bank-travel-2026.html",
    "jw":   "articles/best-time-to-visit-japan-2026.html",
    "lug":  "articles/luggage-storage-tokyo.html",
    "boat": "articles/charter-a-boat-for-a-day.html",
    "mel":  "articles/getting-around-melbourne.html",
    "ft":   "articles/first-international-trip-checklist.html",
    "arr":  "articles/first-day-in-tokyo-arrival-plan.html",
    "au":   "articles/best-esim-australia-2026.html",
}

# post id -> (short key, lead-in). Only the currently link-free, on-topic posts.
POST_LINKS: dict[int, tuple[str, str]] = {
    5:  ("pf",   "The 48-hour checklist →"),
    6:  ("cash", "Where cash still rules →"),
    8:  ("sec",  "The full checklist →"),
    9:  ("vn",   "Vietnam eSIM →"),
    10: ("cash", "Cash in Japan, 2026 →"),
    11: ("jr",   "When it does pay off →"),
    14: ("ins",  "What cards miss →"),
    18: ("gion", "Kyoto, block by block →"),
    19: ("pb",   "Which size to carry →"),
    20: ("jw",   "When to go, honestly →"),
    21: ("lug",  "How it works →"),
    23: ("boat", "Where no licence is needed →"),
    25: ("mel",  "Getting into the city →"),
    26: ("ft",   "Don't forget these →"),
    27: ("arr",  "Your smooth arrival →"),
    29: ("au",   "Australia eSIM →"),
    30: ("ins",  "Coverage compared →"),
    33: ("ft",   "First-trip checklist →"),
}

REDIRECT_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Redirecting… | Gently Yonder</title>
<link rel="canonical" href="https://{domain}/{target}"/>
<meta name="robots" content="noindex, follow"/>
<meta http-equiv="refresh" content="0; url=/{target}"/>
<link rel="stylesheet" href="/style-v2.css"/>
<script>location.replace("/{target}");</script>
</head>
<body>
<p>Redirecting to <a href="/{target}">this guide</a>…</p>
</body>
</html>
"""


def short_url(key: str) -> str:
    return f"{DOMAIN}/go/{key}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    # sanity: every target exists
    for key, target in REDIRECTS.items():
        if not (REPO / "site" / target).exists():
            raise SystemExit(f"target missing for /go/{key}: site/{target}")

    # 1) generate redirect pages
    made = 0
    for key, target in REDIRECTS.items():
        html = REDIRECT_HTML.format(domain=DOMAIN, target=target)
        for base in ("site", "go"), ("docs", "go"):
            d = REPO / base[0] / base[1]
            if args.write:
                d.mkdir(parents=True, exist_ok=True)
                (d / f"{key}.html").write_text(html, encoding="utf-8")
        made += 1

    # 2) append short links to the link-free posts
    src = REPO / "site" / "data" / "x_queue.json"
    data = json.loads(src.read_text(encoding="utf-8"))
    posts = {p["id"]: p for p in data["posts"]}
    linked = skipped = 0
    for pid, (key, lead) in POST_LINKS.items():
        p = posts.get(pid)
        if not p or DOMAIN in p["text"]:
            continue
        url = short_url(key)
        withlead = f'{p["text"]}\n\n{lead} {url}'
        bare = f'{p["text"]}\n\n{url}'
        new = withlead if len(withlead) <= MAX_LEN else bare
        if len(new) > MAX_LEN:
            skipped += 1
            print(f'  #{pid} STILL too long ({len(bare)}) — left as is')
            continue
        mode = "lead" if new == withlead else "bare"
        print(f'  #{pid} [{len(new)}] {mode} -> {url}')
        p["text"] = new
        linked += 1

    over = [pid for pid, p in posts.items() if len(p["text"]) > 280]
    assert not over, f"raw >280: {over}"

    print(f"\nredirect pages: {made} · posts linked: {linked} · skipped: {skipped}")
    if args.write:
        out = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        src.write_text(out, encoding="utf-8")
        (REPO / "docs" / "data" / "x_queue.json").write_text(out, encoding="utf-8")
        print("✓ wrote redirect pages + site/ & docs/ x_queue.json")
    else:
        print("(dry run — pass --write)")


if __name__ == "__main__":
    main()
