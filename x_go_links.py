#!/usr/bin/env python3
"""
x_go_links.py — the short links used in X posts: gentlyyonder.com/go/<key>.

The X queue must stay within 275 raw characters (the n8n node slices there), and
a 55-65 character article URL rarely fits, so posts link to a ~25 character
redirect page instead. Each page meta-refreshes to its guide.

X builds a link card from the page it fetches, and its crawler does not follow a
meta refresh, so every redirect page also carries the target guide's card: its
title, description and image (og: and twitter: tags). Without them the posts
went out with no card at all.

This script owns site/go/ and docs/go/: it renders every page in REDIRECTS from
the target's own meta tags. Add a key here, run it, then link the key in
site/data/x_queue.json and run x_queue_check.py. Idempotent.

    python x_go_links.py            # dry run
    python x_go_links.py --write
"""
from __future__ import annotations

import argparse
import hashlib
import html
from pathlib import Path

from bs4 import BeautifulSoup

REPO = Path(__file__).resolve().parent
DOMAIN = "gentlyyonder.com"
X_HANDLE = "@GentlyYonder"

# short key -> target page (relative to the site root)
REDIRECTS: dict[str, str] = {
    "arr":         "articles/first-day-in-tokyo-arrival-plan.html",
    "au":          "articles/best-esim-australia-2026.html",
    "boat":        "articles/charter-a-boat-for-a-day.html",
    "cash":        "articles/how-much-cash-japan.html",
    "dtax":        "articles/is-accommodation-tax-double-taxation.html",
    "foodtour":    "articles/where-to-book-tokyo-food-tour.html",
    "ft":          "articles/first-international-trip-checklist.html",
    "gion":        "articles/gion-kyoto-neighbourhood-guide.html",
    "ins":         "articles/travel-insurance-compared.html",
    "jc":          "articles/how-much-does-japan-cost.html",
    "jr":          "articles/jr-pass-worth-it-2026.html",
    "jw":          "articles/best-time-to-visit-japan-2026.html",
    "keta":        "articles/do-you-need-keta-south-korea.html",
    "kissaten":    "articles/tokyo-kissaten-guide.html",
    "lug":         "articles/luggage-storage-tokyo.html",
    "mel":         "articles/getting-around-melbourne.html",
    "pb":          "articles/best-power-bank-travel-2026.html",
    "pf":          "articles/pre-flight-checklist-48-hours.html",
    "sec":         "articles/airport-security-checklist.html",
    "stay-kyoto":  "articles/where-to-stay-in-kyoto.html",
    "stay-mel":    "articles/where-to-stay-in-melbourne.html",
    "stay-osaka":  "articles/where-to-stay-in-osaka.html",
    "stay-sydney": "articles/where-to-stay-in-sydney.html",
    "stay-tokyo":  "articles/where-to-stay-in-tokyo.html",
    "tax":         "articles/japan-tax-free-shopping-2026-changes.html",
    "tokyo-kyoto": "articles/tokyo-to-kyoto-shinkansen-vs-flight-vs-bus.html",
    "vn":          "articles/best-esim-vietnam-2026.html",
}

# the card tags copied from the target page, in this order
CARD = [
    ("property", "og:type"), ("property", "og:title"), ("property", "og:description"),
    ("property", "og:image"), ("property", "og:image:width"), ("property", "og:image:height"),
    ("property", "og:image:alt"), ("name", "twitter:card"), ("name", "twitter:title"),
    ("name", "twitter:description"), ("name", "twitter:image"), ("name", "twitter:image:alt"),
]


def short_url(key: str) -> str:
    return f"{DOMAIN}/go/{key}"


def _css_stamp() -> str:
    """The same ?v= stamp bust_assets.py gives style-v2.css, so neither rewrites the other."""
    return hashlib.sha1((REPO / "site" / "style-v2.css").read_bytes()).hexdigest()[:8]


def render(target: str, stamp: str) -> str:
    soup = BeautifulSoup((REPO / "site" / target).read_text(encoding="utf-8"), "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else "Gently Yonder"
    url = f"https://{DOMAIN}/{target}"
    esc = lambda s: html.escape(s, quote=True)  # noqa: E731

    meta = []
    for attr, key in CARD:
        tag = soup.find("meta", attrs={attr: key})
        if tag and tag.get("content"):
            meta.append(f'<meta {attr}="{key}" content="{esc(tag["content"])}"/>')
    meta.append(f'<meta property="og:url" content="{url}"/>')
    meta.append('<meta property="og:site_name" content="Gently Yonder"/>')
    meta.append(f'<meta name="twitter:site" content="{X_HANDLE}"/>')

    return "\n".join([
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8"/>',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0"/>',
        f"<title>{esc(title)}</title>",
        f'<link rel="canonical" href="{url}"/>',
        '<meta name="robots" content="noindex, follow"/>',
        *meta,
        f'<meta http-equiv="refresh" content="0; url=/{target}"/>',
        f'<link rel="stylesheet" href="/style-v2.css?v={stamp}"/>',
        f'<script>location.replace("/{target}");</script>',
        "</head>",
        "<body>",
        f'<p>Redirecting to <a href="/{target}">{esc(title)}</a>…</p>',
        "</body>",
        "</html>",
        "",
    ])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    stamp = _css_stamp()
    changed = 0
    for key, target in sorted(REDIRECTS.items()):
        if not (REPO / "site" / target).exists():
            raise SystemExit(f"target missing for /go/{key}: site/{target}")
        page = render(target, stamp)
        for base in ("site", "docs"):
            out = REPO / base / "go" / f"{key}.html"
            if out.exists() and out.read_text(encoding="utf-8") == page:
                continue
            changed += 1
            print(f"  {'write' if args.write else 'would write'} {base}/go/{key}.html -> {target}")
            if args.write:
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(page, encoding="utf-8")

    print(f"\n{len(REDIRECTS)} short links · {changed} file(s) {'written' if args.write else 'to write'}")
    if not args.write and changed:
        print("(dry run — pass --write)")


if __name__ == "__main__":
    main()
