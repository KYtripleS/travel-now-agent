"""Travelpayouts deep links: send a page's partner links to the page the reader wants, not the
brand's homepage.

The site's default Travelpayouts links (inject_tp.TP_LINKS) open each brand's homepage, so a
reader who taps "See Airalo's Japan plans" had to search for Japan again. For each page listed in
DEEP below, every default link of that brand is swapped for a short link to the exact page.
Short links come from the Travelpayouts Links API (TRAVELPAYOUTS_API_TOKEN in .env) and are
cached in data/tp_deeplinks.json, so the API is called only for new URLs. sub_id is still added
at click time by gy-reveal.js.

usage: .venv/bin/python ops/tp_deeplinks.py            # dry run: what would change
       .venv/bin/python ops/tp_deeplinks.py --write    # create missing links, rewrite site/ + docs/
"""
import argparse
import json
import sys
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent
CACHE = REPO / "data" / "tp_deeplinks.json"
API = "https://api.travelpayouts.com/links/v1/create"
TRS, MARKER = 547982, 743846

# the homepage short links each brand uses across the site
HOME = {
    "airalo": ["https://airalo.tpx.lu/ctddHmQY"],
    "saily": ["https://saily.tpx.lu/hk5XU6Sm", "https://saily.tpx.lu/1RHGIfQA"],
}
ESIM = {  # page slug suffix: (Airalo slug, Saily slug)
    "japan": ("japan", "japan"), "south-korea": ("south-korea", "south-korea"), "taiwan": ("taiwan", "taiwan"),
    "thailand": ("thailand", "thailand"), "vietnam": ("vietnam", "vietnam"), "usa": ("united-states", "united-states"),
    "australia": ("australia", "australia"), "europe": ("europe", "europe"),
}
DEEP = {
    f"best-esim-{k}-2026": {"airalo": f"https://www.airalo.com/{a}-esim", "saily": f"https://saily.com/esim-{s}/"}
    for k, (a, s) in ESIM.items()
}


def token() -> str:
    for line in (REPO / ".env").read_text().splitlines():
        if line.startswith("TRAVELPAYOUTS_API_TOKEN="):
            return line.split("=", 1)[1].strip().strip("\"'")
    sys.exit("TRAVELPAYOUTS_API_TOKEN missing from .env")


def create(urls: list[str]) -> dict[str, str]:
    out = {}
    for i in range(0, len(urls), 10):
        r = requests.post(API, headers={"X-Access-Token": token()}, timeout=60,
                          json={"trs": TRS, "marker": MARKER, "shorten": True,
                                "links": [{"url": u} for u in urls[i:i + 10]]})
        r.raise_for_status()
        for link in r.json()["result"]["links"]:
            if link.get("code") != "success":
                print(f"  ! {link['url']}: {link.get('code')} {link.get('message', '')}")
                continue
            out[link["url"]] = link["partner_url"]
    return out


def deep_for(slug: str, cache: dict) -> dict[str, str]:
    """{homepage short link: deep short link} for one page, from the cache only."""
    swaps = {}
    for brand, url in DEEP.get(slug, {}).items():
        if url in cache:
            for home in HOME[brand]:
                swaps[home] = cache[url]
    return swaps


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    missing = sorted({u for m in DEEP.values() for u in m.values()} - cache.keys())
    if missing:
        if not args.write:
            print(f"{len(missing)} deep links to create (run with --write)")
        else:
            cache.update(create(missing))
            CACHE.write_text(json.dumps(dict(sorted(cache.items())), indent=1) + "\n")
            print(f"created {len(missing)} deep links")
    changed = 0
    for slug in DEEP:
        swaps = deep_for(slug, cache)
        for root in ("site", "docs"):
            p = REPO / root / "articles" / f"{slug}.html"
            if not p.exists():
                continue
            html = p.read_text(encoding="utf-8")
            new = html
            for home, deep in swaps.items():
                new = new.replace(f'href="{home}"', f'href="{deep}"')
            if new != html:
                changed += 1
                if args.write:
                    p.write_text(new, encoding="utf-8")
    print(f"{changed} page files {'rewritten' if args.write else 'would change'}")


if __name__ == "__main__":
    main()
