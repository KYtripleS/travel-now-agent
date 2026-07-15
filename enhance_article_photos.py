#!/usr/bin/env python3
"""
enhance_article_photos.py

Inserts Pexels photos into articles that don't already have inline
<figure> blocks. Uses a curated per-article query list so each photo
matches the section's actual subject rather than a generic match.

Usage:
  python enhance_article_photos.py --slug airport-security-liquids
  python enhance_article_photos.py --all
  python enhance_article_photos.py --slug japan-country-profile --dry-run
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent
SITE_DIR  = REPO_ROOT / "site"
DOCS_DIR  = REPO_ROOT / "docs"
PEXELS_URL = "https://api.pexels.com/v1/search"


# Curated Pexels queries per article. Order matters: the i-th query maps
# to the i-th eligible H2 in the article body.
QUERIES: dict[str, list[str]] = {
    "airport-security-liquids": [
        "airport security tray laptop carry on",
        "travel size toiletry bottles flat lay",
        "clear plastic ziplock bag travel",
        "airport security checkpoint queue",
    ],
    "airport-security-packing-moments": [
        "carry on backpack travel airport",
        "airport security tray belongings",
        "passport boarding pass smartphone hand",
        "phone charger airplane cabin window",
    ],
    "beach-trip-packing-checklist": [
        "beach suitcase packing summer hat",
        "reef safe sunscreen bottle sand",
        "wide brim sun hat tropical",
        "quick dry beach towel folded",
        "tropical resort palm trees turquoise water",
    ],
    "esim-activation-and-preparation": [
        "smartphone airplane window travel",
        "phone settings cellular data screen",
        "international airport terminal passenger",
        "person using smartphone abroad",
    ],
    "everyday-carry-essentials-for-travel": [
        "travel essentials flat lay backpack",
        "power bank phone charging cable travel",
        "reusable water bottle commute",
        "small pouch travel pocket essentials",
    ],
    "hotel-booking-sites-comparison": [
        "hotel lobby modern interior architecture",
        "laptop hotel booking website desk",
        "smartphone hotel reservation app",
        "hotel room king bed window city view",
    ],
    "untranslatable-words": [
        "open old book library window light",
        "person reading journal cafe",
        "vintage notebook pen handwriting",
        "library bookshelves philosophy books",
    ],
    "what-counts-as-rude": [
        "Tokyo street pedestrians commute morning",
        "people dining chopsticks Asian restaurant table",
        "office handshake meeting business",
        "public transit subway commuters polite",
    ],
    "charter-a-boat-for-a-day": [
        "Mediterranean sailing boat coast turquoise water",
        "marina yacht harbor European coast",
        "sailboat sunset coastline Italy",
        "boat captain helm coastal sailing",
    ],
    "japan-country-profile": [
        "Mount Fuji Japan cherry blossom",
        "Kyoto temple stone path autumn",
        "Tokyo Shibuya crossing neon night",
        "Japanese countryside village rice paddy",
        "Hiroshima peace memorial",
    ],
    "asakusa": [
        "Asakusa Sensoji temple lantern Tokyo",
        "Nakamise shopping street Asakusa",
        "traditional Japanese kimono street",
        "Tokyo Skytree from Asakusa river",
    ],
    "where-to-stay-in-tokyo": [
        "Shinjuku skyscrapers night Tokyo",
        "Shibuya crossing Tokyo neon",
        "Tokyo Station Marunouchi building",
        "Ginza Tokyo shopping avenue",
        "Asakusa Sensoji temple lantern Tokyo",
    ],
    "how-much-does-japan-cost": [
        "airplane wing sky travel window",
        "Japanese yen coins and notes",
        "Japan convenience store konbini night",
        "shinkansen train platform Japan",
    ],
    "shinjuku-neighbourhood-guide": [
        "Shinjuku station crowd Tokyo",
        "Tokyo Metropolitan Government Building skyscrapers Shinjuku",
        "Golden Gai Shinjuku alley bars night",
        "Shinjuku Gyoen garden Tokyo",
    ],
    "gion-kyoto-neighbourhood-guide": [
        "Gion Kyoto traditional street dusk",
        "Hanamikoji Gion Kyoto machiya houses",
        "Shirakawa canal Kyoto willow bridge",
        "Yasaka Shrine Kyoto lanterns night",
    ],
    # ---- Taiwan ----
    "taipei-first-timers-guide": [
        "Taipei 101 skyline cityscape Taiwan",
        "Taipei MRT metro station interior",
        "Taipei night market street food stall",
        "Beitou hot spring Taipei steam",
        "Jiufen old street red lanterns Taiwan",
    ],
    "getting-around-taiwan": [
        "Taipei metro turnstile commuters",
        "Taipei MRT train carriage interior",
        "Taiwan high speed rail bullet train",
        "Taiwan railway coast scenic train",
    ],
    "things-to-do-in-taipei": [
        "Taipei 101 tower observation view",
        "Taipei skyline from Elephant Mountain dusk",
        "Longshan Temple Taipei incense",
        "Jiufen teahouse lanterns Taiwan night",
    ],
    # ---- Sydney (guide already has photos) ----
    "getting-around-sydney": [
        "Sydney train double decker platform",
        "Sydney ferry Circular Quay harbour",
        "Sydney bus street city",
        "Sydney airport terminal train",
    ],
    "things-to-do-in-sydney": [
        "Sydney Opera House harbour bridge",
        "The Rocks Sydney historic laneway",
        "Bondi Beach coastal walk Sydney",
        "Manly ferry Sydney harbour view",
    ],
    # ---- Melbourne ----
    "melbourne-first-timers-guide": [
        "Melbourne city skyline Yarra river",
        "Melbourne tram Flinders Street",
        "Melbourne cafe laneway coffee",
        "Melbourne Fitzroy street cafe",
    ],
    "getting-around-melbourne": [
        "Melbourne tram city street",
        "Melbourne Flinders Street Station",
        "Melbourne train platform commuters",
        "Melbourne city trams intersection",
    ],
    "things-to-do-in-melbourne": [
        "Melbourne laneway street art Hosier",
        "Federation Square Melbourne",
        "Queen Victoria Market Melbourne",
        "Great Ocean Road Twelve Apostles",
    ],
    # ---- Perth ----
    "perth-first-timers-guide": [
        "Perth city skyline Swan River",
        "Kings Park Perth view city",
        "Cottesloe Beach Perth sunset",
        "Fremantle Western Australia harbour",
    ],
    "getting-around-perth": [
        "Perth city bus street",
        "Perth train station platform",
        "Perth Swan River ferry",
        "Rottnest Island ferry beach Perth",
    ],
    "things-to-do-in-perth": [
        "Kings Park Perth botanic garden view",
        "Elizabeth Quay Perth waterfront",
        "Fremantle markets Western Australia",
        "Rottnest Island quokka beach Perth",
    ],
    "manila-first-timers-guide": [
        "Intramuros Manila Fort Santiago",
        "Rizal Park Manila monument",
        "Binondo Manila Chinatown street food",
        "Manila Bay sunset skyline",
    ],
    "cebu-first-timers-guide": [
        "Cebu City Basilica Santo Nino",
        "Kawasan Falls Cebu turquoise",
        "Moalboal Cebu diving reef",
        "Cebu island hopping beach boat",
    ],
    "chiang-mai-first-timers-guide": [
        "Chiang Mai temple Wat old city",
        "Doi Suthep temple Chiang Mai golden",
        "Chiang Mai night market lanterns",
        "Chiang Mai elephant sanctuary jungle",
    ],
    "phuket-first-timers-guide": [
        "Phuket beach turquoise Thailand",
        "Phi Phi islands longtail boat",
        "Old Phuket Town Sino-Portuguese street",
        "Big Buddha Phuket viewpoint",
    ],
    "hong-kong-first-timers-guide": [
        "Hong Kong Victoria Harbour skyline night",
        "Hong Kong Peak Tram Victoria Peak view",
        "Hong Kong Temple Street night market neon",
        "Tian Tan Big Buddha Lantau Hong Kong",
    ],
    "seoul-first-timers-guide": [
        "Gyeongbokgung Palace Seoul guards",
        "Bukchon Hanok Village Seoul traditional houses",
        "Myeongdong Seoul street food night",
        "N Seoul Tower Namsan skyline",
    ],
    "osaka-first-timers-guide": [
        "Osaka Castle cherry blossom Japan",
        "Dotonbori Osaka Glico neon night",
        "Osaka takoyaki street food",
        "Umeda Sky Building Osaka skyline",
    ],
    "penang-first-timers-guide": [
        "George Town Penang street art mural",
        "Kek Lok Si temple Penang",
        "Penang char kway teow hawker food",
        "Penang Hill funicular railway view",
    ],
    "yogyakarta-first-timers-guide": [
        "Borobudur temple sunrise Java Indonesia",
        "Prambanan Hindu temple Yogyakarta",
        "Malioboro street Yogyakarta Indonesia",
        "Yogyakarta batik craft Indonesia",
    ],
    "things-to-do-in-tokyo": [
        "Senso-ji temple Asakusa Tokyo",
        "Shibuya crossing Tokyo night",
        "Meiji shrine torii Tokyo",
        "Tokyo skyline Mount Fuji",
    ],
    "things-to-do-in-kyoto": [
        "Fushimi Inari torii gates Kyoto",
        "Arashiyama bamboo grove Kyoto",
        "Kinkaku-ji golden pavilion Kyoto",
        "Kiyomizu-dera temple Kyoto autumn",
    ],
    "things-to-do-in-bangkok": [
        "Grand Palace Bangkok Thailand",
        "Wat Arun temple Bangkok river sunset",
        "Bangkok Chinatown street food night",
        "Bangkok floating market boats",
    ],
    "things-to-do-in-seoul": [
        "Gyeongbokgung Palace Seoul guard",
        "Bukchon Hanok Village Seoul",
        "N Seoul Tower Namsan night",
        "Gwangjang Market Seoul food",
    ],
    "things-to-do-in-osaka": [
        "Osaka Castle Japan",
        "Dotonbori Osaka Glico neon",
        "Shinsekai Tsutenkaku Osaka",
        "Osaka takoyaki street food",
    ],
    "things-to-do-in-singapore": [
        "Marina Bay Sands Singapore skyline",
        "Gardens by the Bay Supertree Singapore",
        "Singapore hawker centre food",
        "Sentosa Singapore beach",
    ],
    "things-to-do-in-bali": [
        "Tegallalang rice terrace Ubud Bali",
        "Uluwatu temple Bali cliff sunset",
        "Kelingking Beach Nusa Penida Bali",
        "Bali beach surf Seminyak",
    ],
    "things-to-do-in-hong-kong": [
        "Victoria Peak Hong Kong skyline",
        "Star Ferry Victoria Harbour Hong Kong",
        "Tian Tan Big Buddha Lantau Hong Kong",
        "Temple Street night market Hong Kong",
    ],
    "things-to-do-in-hanoi": [
        "Hanoi Old Quarter street Vietnam",
        "Hoan Kiem Lake Huc Bridge Hanoi",
        "Temple of Literature Hanoi",
        "Ha Long Bay Vietnam karst",
    ],
    "things-to-do-in-ho-chi-minh-city": [
        "Ho Chi Minh City Saigon skyline night",
        "Notre Dame Cathedral Saigon Vietnam",
        "Ben Thanh Market Saigon",
        "Mekong Delta boat Vietnam",
    ],
    "things-to-do-in-kuala-lumpur": [
        "Petronas Towers Kuala Lumpur night",
        "Batu Caves Kuala Lumpur stairs",
        "Kuala Lumpur Chinatown street",
        "Jalan Alor food street KL",
    ],
    "things-to-do-in-manila": [
        "Intramuros Manila Fort Santiago",
        "San Agustin Church Manila",
        "Manila Bay sunset skyline",
        "Binondo Manila Chinatown",
    ],
    "things-to-do-in-chiang-mai": [
        "Wat Phra Singh temple Chiang Mai",
        "Doi Suthep temple Chiang Mai golden",
        "Chiang Mai night market lanterns",
        "Chiang Mai elephant sanctuary jungle",
    ],
    "things-to-do-in-phuket": [
        "Phuket beach island Thailand aerial",
        "Big Buddha Phuket viewpoint",
        "Old Phuket Town Sino-Portuguese street",
        "Phi Phi islands longtail boat Phuket",
    ],
    "japan-7-day-itinerary": [
        "Tokyo Shibuya crossing night",
        "Mount Fuji Hakone lake",
        "Kyoto Fushimi Inari torii",
        "Osaka Dotonbori night",
    ],
    "thailand-10-day-itinerary": [
        "Bangkok Wat Arun temple river",
        "Chiang Mai temple Thailand mountain",
        "Thailand island longtail boat beach",
        "Phi Phi islands Thailand aerial",
    ],
    "bali-7-day-itinerary": [
        "Bali Tegallalang rice terrace Ubud",
        "Uluwatu temple Bali cliff sunset",
        "Nusa Penida Kelingking Beach Bali",
        "Bali beach Seminyak surf",
    ],
    "what-to-pack-for-southeast-asia": [
        "travel backpack packing flat lay",
        "Southeast Asia temple traveller",
        "tropical island beach Thailand",
        "travel gear adapter power bank",
    ],
    "klook-vs-kkday": [
        "traveler booking phone app asia",
        "taipei night market street",
        "temple day tour asia tourists",
    ],
    "what-to-pack-for-japan": [
        "Japan travel suitcase train station",
        "Kyoto street kimono autumn",
        "Tokyo train Shinkansen platform",
        "Japan winter snow street",
    ],
}


# slug → path under site/
SLUG_TO_PATH: dict[str, Path] = {
    "airport-security-liquids":             Path("articles/airport-security-liquids.html"),
    "airport-security-packing-moments":     Path("articles/airport-security-packing-moments.html"),
    "beach-trip-packing-checklist":         Path("articles/beach-trip-packing-checklist.html"),
    "esim-activation-and-preparation":      Path("articles/esim-activation-and-preparation.html"),
    "everyday-carry-essentials-for-travel": Path("articles/everyday-carry-essentials-for-travel.html"),
    "hotel-booking-sites-comparison":       Path("articles/hotel-booking-sites-comparison.html"),
    "untranslatable-words":                 Path("articles/untranslatable-words.html"),
    "what-counts-as-rude":                  Path("articles/what-counts-as-rude.html"),
    "charter-a-boat-for-a-day":             Path("articles/charter-a-boat-for-a-day.html"),
    "japan-country-profile":                Path("countries/japan/index.html"),
    "asakusa":                              Path("cities/tokyo/asakusa.html"),
    "where-to-stay-in-tokyo":               Path("articles/where-to-stay-in-tokyo.html"),
    "how-much-does-japan-cost":             Path("articles/how-much-does-japan-cost.html"),
    "shinjuku-neighbourhood-guide":         Path("articles/shinjuku-neighbourhood-guide.html"),
    "gion-kyoto-neighbourhood-guide":       Path("articles/gion-kyoto-neighbourhood-guide.html"),
    "taipei-first-timers-guide":            Path("articles/taipei-first-timers-guide.html"),
    "getting-around-taiwan":                Path("articles/getting-around-taiwan.html"),
    "things-to-do-in-taipei":               Path("articles/things-to-do-in-taipei.html"),
    "getting-around-sydney":                Path("articles/getting-around-sydney.html"),
    "things-to-do-in-sydney":               Path("articles/things-to-do-in-sydney.html"),
    "melbourne-first-timers-guide":         Path("articles/melbourne-first-timers-guide.html"),
    "getting-around-melbourne":             Path("articles/getting-around-melbourne.html"),
    "things-to-do-in-melbourne":            Path("articles/things-to-do-in-melbourne.html"),
    "perth-first-timers-guide":             Path("articles/perth-first-timers-guide.html"),
    "getting-around-perth":                 Path("articles/getting-around-perth.html"),
    "things-to-do-in-perth":                Path("articles/things-to-do-in-perth.html"),
    "manila-first-timers-guide":            Path("articles/manila-first-timers-guide.html"),
    "cebu-first-timers-guide":              Path("articles/cebu-first-timers-guide.html"),
    "chiang-mai-first-timers-guide":        Path("articles/chiang-mai-first-timers-guide.html"),
    "phuket-first-timers-guide":            Path("articles/phuket-first-timers-guide.html"),
    "hong-kong-first-timers-guide":         Path("articles/hong-kong-first-timers-guide.html"),
    "seoul-first-timers-guide":             Path("articles/seoul-first-timers-guide.html"),
    "osaka-first-timers-guide":             Path("articles/osaka-first-timers-guide.html"),
    "penang-first-timers-guide":            Path("articles/penang-first-timers-guide.html"),
    "yogyakarta-first-timers-guide":        Path("articles/yogyakarta-first-timers-guide.html"),
    "things-to-do-in-tokyo":                Path("articles/things-to-do-in-tokyo.html"),
    "things-to-do-in-kyoto":                Path("articles/things-to-do-in-kyoto.html"),
    "things-to-do-in-bangkok":              Path("articles/things-to-do-in-bangkok.html"),
    "things-to-do-in-seoul":                Path("articles/things-to-do-in-seoul.html"),
    "things-to-do-in-osaka":                Path("articles/things-to-do-in-osaka.html"),
    "things-to-do-in-singapore":            Path("articles/things-to-do-in-singapore.html"),
    "things-to-do-in-bali":                 Path("articles/things-to-do-in-bali.html"),
    "things-to-do-in-hong-kong":            Path("articles/things-to-do-in-hong-kong.html"),
    "things-to-do-in-hanoi":                Path("articles/things-to-do-in-hanoi.html"),
    "things-to-do-in-ho-chi-minh-city":     Path("articles/things-to-do-in-ho-chi-minh-city.html"),
    "things-to-do-in-kuala-lumpur":         Path("articles/things-to-do-in-kuala-lumpur.html"),
    "things-to-do-in-manila":               Path("articles/things-to-do-in-manila.html"),
    "things-to-do-in-chiang-mai":           Path("articles/things-to-do-in-chiang-mai.html"),
    "things-to-do-in-phuket":               Path("articles/things-to-do-in-phuket.html"),
    "japan-7-day-itinerary":                Path("articles/japan-7-day-itinerary.html"),
    "thailand-10-day-itinerary":            Path("articles/thailand-10-day-itinerary.html"),
    "bali-7-day-itinerary":                 Path("articles/bali-7-day-itinerary.html"),
    "what-to-pack-for-southeast-asia":      Path("articles/what-to-pack-for-southeast-asia.html"),
    "klook-vs-kkday":                        Path("articles/klook-vs-kkday.html"),
    "what-to-pack-for-japan":               Path("articles/what-to-pack-for-japan.html"),
}


# H2 text fragments to skip (lowercased contains check)
SKIP_HEADINGS = (
    "faq",
    "frequently asked",
    "sources",
    "references",
    "bottom line",
    "related",
    "what this means",
    "further reading",
    "tip",
    "newsletter",
)


def pexels_photo(query: str) -> dict | None:
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        sys.exit("PEXELS_API_KEY missing in .env")
    r = requests.get(
        PEXELS_URL,
        headers={"Authorization": api_key},
        params={"query": query, "orientation": "landscape", "per_page": 5, "size": "large"},
        timeout=30,
    )
    if r.status_code != 200:
        return None
    photos = (r.json() or {}).get("photos") or []
    if not photos:
        return None
    p = photos[0]
    src = p.get("src") or {}
    return {
        "url": src.get("large2x") or src.get("large") or src.get("original"),
        "photographer": p.get("photographer", "Unknown"),
        "photographer_url": p.get("photographer_url", "https://www.pexels.com/"),
        "pexels_url": p.get("url", "https://www.pexels.com/"),
    }


def make_figure(soup: BeautifulSoup, photo: dict, alt: str) -> "BeautifulSoup":
    fig = soup.new_tag("figure", **{"class": "article-figure"})
    img = soup.new_tag("img")
    img["src"] = photo["url"]
    img["alt"] = alt
    img["loading"] = "lazy"
    fig.append(img)

    cap = soup.new_tag("figcaption")
    cap.append("Photo by ")
    a1 = soup.new_tag("a", href=photo["photographer_url"], rel="noopener nofollow")
    a1.string = photo["photographer"]
    cap.append(a1)
    cap.append(" on ")
    a2 = soup.new_tag("a", href=photo["pexels_url"], rel="noopener nofollow")
    a2.string = "Pexels"
    cap.append(a2)
    fig.append(cap)
    return fig


def should_skip_h2(h2) -> bool:
    text = h2.get_text(strip=True).lower()
    return any(kw in text for kw in SKIP_HEADINGS)


def article_body(soup: BeautifulSoup):
    # Prefer the canonical article container. Fall back to <main> as a whole
    # (NOT "main section" — that only grabs the first section).
    for sel in ("main section.article", "main", "article"):
        el = soup.select_one(sel)
        if el is not None:
            return el
    return soup.body


def enhance(slug: str, *, dry_run: bool = False) -> int:
    rel = SLUG_TO_PATH[slug]
    queries = QUERIES.get(slug, [])
    site_path = SITE_DIR / rel
    docs_path = DOCS_DIR / rel
    if not site_path.exists():
        print(f"  ! file missing: {site_path}")
        return 0
    if not queries:
        print(f"  ! no queries for slug {slug}")
        return 0

    soup = BeautifulSoup(site_path.read_text(encoding="utf-8"), "html.parser")

    body = article_body(soup)
    if body is None:
        print(f"  ! no article body — skip")
        return 0

    h2s = [h for h in body.find_all("h2") if not should_skip_h2(h)]
    if not h2s:
        print(f"  ! no eligible H2 sections — skip")
        return 0

    # Pair queries[i] with h2s[i] by original index. If an H2 already has a
    # figure, just skip that pair (keep the existing photo); don't shift the
    # query mapping for later H2s.
    def has_following_figure(h2) -> bool:
        sib = h2.find_next_sibling()
        return sib is not None and sib.name == "figure" and "article-figure" in (sib.get("class") or [])

    inserted = 0
    target = min(len(queries), len(h2s))
    for i in range(target):
        h2 = h2s[i]
        if has_following_figure(h2):
            print(f"  [{i + 1}] (already has figure — skip)")
            continue
        query = queries[i]
        photo = pexels_photo(query)
        if not photo:
            print(f"  [{i + 1}] {query!r} — no photo")
            continue
        fig = make_figure(soup, photo, alt=h2.get_text(strip=True))
        h2.insert_after(fig)
        inserted += 1
        print(f"  [{i + 1}] {query!r} → {photo['photographer']}")

    if not dry_run and inserted > 0:
        site_path.write_text(str(soup), encoding="utf-8")
        docs_path.parent.mkdir(parents=True, exist_ok=True)
        docs_path.write_text(site_path.read_text(encoding="utf-8"), encoding="utf-8")
    return inserted


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    p = argparse.ArgumentParser()
    p.add_argument("--slug", help="single slug")
    p.add_argument("--all", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.all:
        slugs = list(SLUG_TO_PATH.keys())
    elif args.slug:
        if args.slug not in SLUG_TO_PATH:
            sys.exit(f"unknown slug. Known: {', '.join(SLUG_TO_PATH)}")
        slugs = [args.slug]
    else:
        sys.exit("pass --slug NAME or --all")

    total = 0
    for slug in slugs:
        print(f"\n[{slug}]")
        n = enhance(slug, dry_run=args.dry_run)
        total += n
    print(f"\n— total photos inserted: {total} —")


if __name__ == "__main__":
    main()
