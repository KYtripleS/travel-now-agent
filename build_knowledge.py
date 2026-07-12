#!/usr/bin/env python3
"""
build_knowledge.py — turn the article corpus into a structured knowledge graph.

Scans site/articles/*.html (plus the countries/ and cities/ hubs) and emits
data/knowledge.json: World -> Country -> City -> Guide, plus cross-destination
"prep" nodes (eSIM, insurance, packing, …) with tags. This is the data layer
the world-map navigation, country/city hubs, and the Ready Score all read from.

No backend: it's generated at build time and served as a static JSON file.

Usage:  python build_knowledge.py           # writes site/ + docs/ data/knowledge.json
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent
SITE = REPO / "site"
DOCS = REPO / "docs"

# ── City tokens (checked longest-first) → (City, Country) ────────────────────
CITY_TOKENS: list[tuple[str, str, str]] = [
    ("ho-chi-minh", "Ho Chi Minh City", "Vietnam"),
    ("kuala-lumpur", "Kuala Lumpur", "Malaysia"),
    ("chiang-mai", "Chiang Mai", "Thailand"),
    ("hong-kong", "Hong Kong", "Hong Kong"),
    ("yogyakarta", "Yogyakarta", "Indonesia"),
    ("narita-haneda", "Tokyo", "Japan"),
    ("shinjuku", "Tokyo", "Japan"),
    ("hoi-an", "Hoi An", "Vietnam"),
    ("gion", "Kyoto", "Japan"),
    ("tokyo", "Tokyo", "Japan"),
    ("kyoto", "Kyoto", "Japan"),
    ("osaka", "Osaka", "Japan"),
    ("seoul", "Seoul", "South Korea"),
    ("bangkok", "Bangkok", "Thailand"),
    ("phuket", "Phuket", "Thailand"),
    ("hanoi", "Hanoi", "Vietnam"),
    ("singapore", "Singapore", "Singapore"),
    ("bali", "Bali", "Indonesia"),
    ("penang", "Penang", "Malaysia"),
    ("manila", "Manila", "Philippines"),
    ("cebu", "Cebu", "Philippines"),
    ("taipei", "Taipei", "Taiwan"),
    ("sydney", "Sydney", "Australia"),
    ("melbourne", "Melbourne", "Australia"),
    ("perth", "Perth", "Australia"),
]

# Country tokens (only used when no city matched) → Country
COUNTRY_TOKENS: list[tuple[str, str]] = [
    ("south-korea", "South Korea"), ("korea", "South Korea"),
    ("japan", "Japan"), ("jr-pass", "Japan"), ("suica", "Japan"), ("shinkansen", "Japan"),
    ("thailand", "Thailand"), ("vietnam", "Vietnam"), ("taiwan", "Taiwan"),
    ("indonesia", "Indonesia"), ("malaysia", "Malaysia"), ("philippines", "Philippines"),
    ("australia", "Australia"), ("hong-kong", "Hong Kong"), ("singapore", "Singapore"),
]

REGION = {
    "Japan": "East Asia", "South Korea": "East Asia", "Hong Kong": "East Asia", "Taiwan": "East Asia",
    "Thailand": "Southeast Asia", "Vietnam": "Southeast Asia", "Singapore": "Southeast Asia",
    "Indonesia": "Southeast Asia", "Malaysia": "Southeast Asia", "Philippines": "Southeast Asia",
    "Australia": "Oceania",
}
COUNTRY_SLUG = {
    "Japan": "japan", "South Korea": "south-korea", "Hong Kong": "hong-kong", "Taiwan": "taiwan",
    "Thailand": "thailand", "Vietnam": "vietnam", "Singapore": "singapore", "Indonesia": "indonesia",
    "Malaysia": "malaysia", "Philippines": "philippines", "Australia": "australia",
}

# Cross-destination prep categories → tag (any token match adds the tag) ──────
PREP_TAGS: dict[str, list[str]] = {
    "eSIM": ["esim", "airalo", "holafly", "saily", "pocket-wifi"],
    "Insurance": ["insurance", "safetywing", "world-nomads", "nomads"],
    "Packing": ["packing", "capsule-wardrobe", "carry-on", "what-to-pack", "everyday-carry"],
    "Airport": ["airport"],
    "Money": ["cost", "budget", "how-much"],
    "Tours": ["klook", "viator", "getyourguide"],
    "Hotels": ["hotel", "where-to-stay"],
    "Culture": ["rude", "untranslatable"],
    "Jet lag": ["jet-lag"],
    "Transport": ["getting-around", "jr-pass", "shinkansen", "suica", "pasmo", "ic-cards",
                  "sightseeing-passes", "narita-haneda", "to-central-tokyo", "shinjuku-neighbourhood"],
    "Timing": ["best-time-to-visit", "autumn", "book-in-advance", "book-ahead"],
}
# categories that describe a whole prep topic (override country when no city)
CROSS_PREP = {"eSIM", "Insurance", "Packing", "Airport", "Tours", "Hotels", "Culture", "Jet lag"}


def title_of(html_path: Path) -> str:
    t = re.search(r"<title>(.*?)</title>", html_path.read_text(encoding="utf-8"), re.S)
    if not t:
        return html_path.stem.replace("-", " ").title()
    import html as _h
    return _h.unescape(re.split(r"\s*[|—–]\s*", t.group(1).strip())[0].strip())


def node_type(slug: str) -> str:
    if "things-to-do" in slug: return "places"
    if "itinerary" in slug or re.search(r"\d+-day|days-in|3-day|5-days", slug): return "itinerary"
    if "first-timers-guide" in slug: return "guide"
    if "neighbourhood" in slug: return "neighbourhood"
    if "where-to-stay" in slug: return "stay"
    if "first-day" in slug or "arrival" in slug: return "arrival"
    if "getting-around" in slug or "to-central" in slug or "narita" in slug: return "transport"
    return "guide"


def tags_for(slug: str) -> list[str]:
    return [cat for cat, toks in PREP_TAGS.items() if any(tok in slug for tok in toks)]


def main() -> None:
    articles = sorted((SITE / "articles").glob("*.html"))
    countries: dict[str, dict] = {}
    prep: dict[str, list] = {}

    def ensure_country(name: str) -> dict:
        if name not in countries:
            countries[name] = {"name": name, "slug": COUNTRY_SLUG.get(name, name.lower()),
                               "region": REGION.get(name, "Other"),
                               "hub": None, "cities": {}, "guides": []}
        return countries[name]

    for f in articles:
        slug = f.stem
        title = title_of(f)
        url = f"articles/{slug}.html"
        tags = tags_for(slug)
        rec = {"title": title, "url": url, "slug": slug, "type": node_type(slug), "tags": tags}

        # 1) city?
        city = country = None
        for tok, c, co in CITY_TOKENS:
            if tok in slug:
                city, country = c, co
                break
        if city:
            cy = ensure_country(country)
            cy["cities"].setdefault(city, {"name": city, "slug": city.lower().replace(" ", "-"),
                                           "hub": None, "guides": []})
            cy["cities"][city]["guides"].append(rec)
            continue
        # 2) cross-destination prep topic overrides country
        cross = [t for t in tags if t in CROSS_PREP]
        if cross:
            prep.setdefault(cross[0], []).append(rec)
            continue
        # 3) country-level?
        for tok, co in COUNTRY_TOKENS:
            if tok in slug:
                country = co
                break
        if country:
            ensure_country(country)["guides"].append(rec)
            continue
        # 4) other prep (transport/timing/money) or general
        if tags:
            prep.setdefault(tags[0], []).append(rec)
        else:
            prep.setdefault("General", []).append(rec)

    # attach existing hub pages
    for d in (SITE / "countries").glob("*/"):
        name = {v: k for k, v in COUNTRY_SLUG.items()}.get(d.name)
        if name and name in countries:
            countries[name]["hub"] = f"countries/{d.name}/"
    for d in (SITE / "cities").glob("*/"):
        for cy in countries.values():
            for cityname, city in cy["cities"].items():
                if city["slug"] == d.name:
                    city["hub"] = f"cities/{d.name}/"

    # finalize: counts + sort
    out_countries = []
    for name, cy in sorted(countries.items(), key=lambda kv: -sum(len(c["guides"]) for c in kv[1]["cities"].values()) - len(kv[1]["guides"])):
        city_list = sorted(cy["cities"].values(), key=lambda c: -len(c["guides"]))
        gc = sum(len(c["guides"]) for c in city_list) + len(cy["guides"])
        out_countries.append({**cy, "cities": city_list, "guideCount": gc})

    data = {
        "generated": date.today().isoformat(),
        "totals": {
            "countries": len(out_countries),
            "cities": sum(len(c["cities"]) for c in out_countries),
            "guides": sum(c["guideCount"] for c in out_countries) + sum(len(v) for v in prep.values()),
        },
        "countries": out_countries,
        "prep": [{"category": k, "guides": v} for k, v in sorted(prep.items(), key=lambda kv: -len(kv[1]))],
    }

    for base in (SITE, DOCS):
        p = base / "data" / "knowledge.json"
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"knowledge.json — {data['totals']['countries']} countries, "
          f"{data['totals']['cities']} cities, {data['totals']['guides']} guides")
    for c in out_countries:
        print(f"  {c['name']:14s} {c['guideCount']:2d} guides · {len(c['cities'])} cities"
              f" · hub={'yes' if c['hub'] else 'no'}")
    print("  prep:", ", ".join(f"{p['category']}({len(p['guides'])})" for p in data["prep"]))


if __name__ == "__main__":
    main()
