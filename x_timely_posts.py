#!/usr/bin/env python3
"""
x_timely_posts.py — append timely, current-info ("what's changed now") X posts,
each with a short /go redirect link. One-off style, but idempotent: skips a post
whose exact first line already exists in the queue.

Facts here are web-verified (2026-09-09) against official / law-firm sources —
do not edit figures or dates without re-verifying. See memory
timely-current-info-content.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent
DOMAIN = "gentlyyonder.com"
MAX_LEN = 278

NEW_REDIRECTS = {
    "tax":  "articles/japan-tax-free-shopping-2026-changes.html",
    "keta": "articles/do-you-need-keta-south-korea.html",
    "jc":   "articles/how-much-does-japan-cost.html",
}

# (body, short key, lead-in)
NEW_POSTS = [
    (
        "Big change for shoppers in Japan from 1 November 2026:\n\n"
        "The 10% tax no longer comes off at the register. You pay full price, "
        "then claim the refund at the airport before you fly.\n\n"
        "Same ¥5,000 minimum. Budget for the 10% up front.",
        "tax", "What changes →",
    ),
    (
        "Flying to South Korea soon?\n\n"
        "Right now most tourists don't need a K-ETA — it's waived for 22 countries "
        "(US, UK, Canada, Australia, Japan…) through 31 December 2026.\n\n"
        "But skip it and you must file the arrival card. It's not a visa.",
        "keta", "The 2026 rule →",
    ),
    (
        "Japan has rarely been this affordable for foreign visitors — the weak yen "
        "stretches every budget.\n\n"
        "Where it shows up most: food, trains, mid-range hotels.\n\n"
        "Here's a realistic 2026 Japan budget, line by line.",
        "jc", "The numbers →",
    ),
]

REDIRECT_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Redirecting… | Gently Yonder</title>
<link rel="canonical" href="https://{d}/{t}"/>
<meta name="robots" content="noindex, follow"/>
<meta http-equiv="refresh" content="0; url=/{t}"/>
<link rel="stylesheet" href="/style-v2.css"/>
<script>location.replace("/{t}");</script>
</head>
<body><p>Redirecting to <a href="/{t}">this guide</a>…</p></body>
</html>
"""


def main() -> None:
    # sanity: targets exist
    for k, t in NEW_REDIRECTS.items():
        assert (REPO / "site" / t).exists(), f"missing target for /go/{k}: {t}"
        html = REDIRECT_HTML.format(d=DOMAIN, t=t)
        for base in ("site", "docs"):
            (REPO / base / "go" / f"{k}.html").write_text(html, encoding="utf-8")

    src = REPO / "site" / "data" / "x_queue.json"
    data = json.loads(src.read_text(encoding="utf-8"))
    posts = data["posts"]
    first_lines = {p["text"].split("\n")[0] for p in posts}
    next_id = max(p["id"] for p in posts) + 1

    added = 0
    for body, key, lead in NEW_POSTS:
        if body.split("\n")[0] in first_lines:
            print(f"skip (exists): {body[:40]}")
            continue
        url = f"{DOMAIN}/go/{key}"
        text = f"{body}\n\n{lead} {url}"
        assert len(text) <= MAX_LEN, f"post too long ({len(text)}): {body[:40]}"
        posts.append({"id": next_id, "text": text})
        print(f"  #{next_id} [{len(text)}] -> {url}")
        next_id += 1
        added += 1

    out = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    src.write_text(out, encoding="utf-8")
    (REPO / "docs" / "data" / "x_queue.json").write_text(out, encoding="utf-8")
    print(f"\n✓ redirects: {len(NEW_REDIRECTS)} · posts added: {added} · queue now {len(posts)}")


if __name__ == "__main__":
    main()
