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
import re
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
    "klook": ["https://klook.tpx.lu/TgR5Suzs", "https://klook.tpx.lu/wgsZkatL"],
    "welcomepickups": ["https://tpx.lu/YtuAbaB1"],
    "kkday": ["https://kkday.tpx.lu/99SKEU6d", "https://kkday.tpx.lu/3364ws9s"],
}
# Each brand's page for the city a page is about: data/<brand>_cities.json, {"cities": {City: url}}
CITY_PAGES = {b: json.loads(p.read_text())["cities"]
              for b in ("klook", "welcomepickups", "kkday")
              if (p := REPO / "data" / f"{b}_cities.json").exists()}


def _city_key(name: str) -> str:
    import unicodedata
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().replace(",", "")
    return {"Sydney NSW": "Sydney"}.get(plain, plain)
ESIM = {  # page slug suffix: (Airalo slug, Saily slug)
    "japan": ("japan", "japan"), "south-korea": ("south-korea", "south-korea"), "taiwan": ("taiwan", "taiwan"),
    "thailand": ("thailand", "thailand"), "vietnam": ("vietnam", "vietnam"), "usa": ("united-states", "united-states"),
    "australia": ("australia", "australia"), "europe": ("europe", "europe"),
}
# Price-table cells that open the exact product: {page: {row header: (column, merchant URL)}}.
# Column counts the <td>s after the row header from 0 (the Klook column of the same-ticket
# table is 1). Each URL was matched to the price in its cell (Klook listings, 2026-10-21/25).
CELLS = {
    "klook-vs-viator-vs-getyourguide": {
        "teamLab Planets TOKYO": (1, "https://www.klook.com/en-US/activity/25300-teamlab-planets-toyosu-tokyo-ticket/"),
        "Warner Bros. Studio Tour Tokyo": (1, "https://www.klook.com/en-US/activity/84374-warner-bros-studio-tour-tokyo-making-harry-potter/"),
        "Universal Studios Singapore, one day": (1, "https://www.klook.com/en-US/activity/56114-universal-studios-singapore/"),
        "Burj Khalifa At the Top, levels 124–125": (1, "https://www.klook.com/en-US/activity/2228-burj-khalifa-observation-deck-dubai/"),
        "Empire State Building, 86th floor": (1, "https://www.klook.com/en-US/activity/2956-empire-state-building-new-york/"),
        "Sagrada Família, basic ticket": (1, "https://www.klook.com/en-US/activity/20380-sagrada-familia-ticket-barcelona/"),
    },
}
REL = 'rel="nofollow sponsored noopener" target="_blank"'

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


def _esim_page_for(slug: str) -> str | None:
    """The country eSIM guide whose deep links a page borrows: itself, or the country its
    destination is in (add_aeo.page_dest), so a Bangkok guide's Airalo link opens Thailand's plans."""
    if slug in DEEP:
        return slug
    sys.path.insert(0, str(REPO))
    import add_aeo
    dest = add_aeo.page_dest(slug)
    page = f"best-esim-{dest[4]}-2026" if dest and dest[4] else None
    return page if page in DEEP else None


def _page_city(slug: str) -> str | None:
    sys.path.insert(0, str(REPO))
    import add_aeo
    dest = add_aeo.page_dest(slug)
    return _city_key(dest[0]) if dest else None


def deep_for(slug: str, cache: dict) -> dict[str, str]:
    """{homepage short link: deep short link} for one page, from the cache only."""
    swaps = {}
    city = _page_city(slug)
    for brand, pages in CITY_PAGES.items():
        url = pages.get(city) if city else None
        if url in cache:
            for home in HOME[brand]:
                swaps[home] = cache[url]
    for brand, url in DEEP.get(_esim_page_for(slug) or "", {}).items():
        if url in cache:
            for home in HOME[brand]:
                swaps[home] = cache[url]
    return swaps


def link_cells(html: str, slug: str, cache: dict) -> str:
    """Wrap each listed price cell in a link to its product (once; a linked cell is left alone)."""
    for row, (col, url) in CELLS.get(slug, {}).items():
        if url not in cache:
            continue
        m = re.search(r'<tr><th scope="row">' + re.escape(row) + r'</th>((?:<td>.*?</td>){%d})<td>(.*?)</td>' % col, html)
        if not m or "<a " in m.group(2):
            continue
        cell = f'<a href="{cache[url]}" {REL}>{m.group(2)}</a>'
        html = html[:m.start(2)] + cell + html[m.end(2):]
    return html


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    wanted = ({u for m in DEEP.values() for u in m.values()} | {u for m in CELLS.values() for _, u in m.values()}
              | {u for m in CITY_PAGES.values() for u in m.values()})
    missing = sorted(wanted - cache.keys())
    if missing:
        if not args.write:
            print(f"{len(missing)} deep links to create (run with --write)")
        else:
            cache.update(create(missing))
            CACHE.write_text(json.dumps(dict(sorted(cache.items())), indent=1) + "\n")
            print(f"created {len(missing)} deep links")
    changed = 0
    slugs = {p.stem for p in (REPO / "site" / "articles").glob("*.html")}
    for slug in sorted(slugs):
        swaps = deep_for(slug, cache)
        for root in ("site", "docs"):
            p = REPO / root / "articles" / f"{slug}.html"
            if not p.exists():
                continue
            html = p.read_text(encoding="utf-8")
            new = html
            for home, deep in swaps.items():
                new = new.replace(f'href="{home}"', f'href="{deep}"')
            new = link_cells(new, slug, cache)
            if new != html:
                changed += 1
                if args.write:
                    p.write_text(new, encoding="utf-8")
    print(f"{changed} page files {'rewritten' if args.write else 'would change'}")


if __name__ == "__main__":
    main()
