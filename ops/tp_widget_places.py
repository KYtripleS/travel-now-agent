"""Look up the place ids Travelpayouts' widgets need for each city the site writes about.

Writes data/tp_widget_places.json: {city: {country, viator, gyg_iata, twelvego, omio, vio, agoda, klook, tm_country}}.
Uses the same public suggestion endpoints as the widget builder in the Travelpayouts dashboard.
Only exact title matches are kept; a city whose name is shared by several places is listed under
"check" for a hand decision (put the answer in OVERRIDES).
Run: .venv/bin/python ops/tp_widget_places.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
OUT = REPO / "data" / "tp_widget_places.json"
S = "https://suggest.travelpayouts.com"

# Ticketmaster's widget lists these countries only
TM = {"Australia": "AU", "Austria": "AT", "Belgium": "BE", "France": "FR", "Finland": "FI", "Czech Republic": "CZ",
      "Denmark": "DK", "Germany": "DE", "United Kingdom": "GB", "Italy": "IT", "Netherlands": "NL", "Norway": "NO",
      "Poland": "PL", "Spain": "ES", "Sweden": "SE", "Switzerland": "CH", "Ireland": "IE", "USA": "US",
      "United States": "US", "Canada": "CA", "New Zealand": "NZ", "Mexico": "MX", "Portugal": "PT"}
# 12Go sells the overland legs of South and South-East Asia (and Japan/Korea less well)
ASIA_12GO = {"Thailand", "Vietnam", "Cambodia", "Laos", "Malaysia", "Singapore", "Indonesia", "Philippines",
             "Myanmar", "India", "Sri Lanka", "Nepal"}
EUROPE = {"Italy", "Spain", "France", "United Kingdom", "Finland", "Croatia", "Poland", "Portugal", "Greece",
          "Hungary", "Denmark", "Sweden", "Ireland", "Austria", "Germany", "Czech Republic", "Netherlands",
          "Belgium", "Switzerland", "Norway", "Iceland", "Slovenia", "Estonia", "Latvia", "Lithuania", "Scotland",
          "England", "Monaco", "Malta", "Turkey"}
# hand-checked (2026-11-10): same-name places, local spellings, regions
CN_ALIAS = {"USA": ["United States"], "United States": ["United States"], "Czech Republic": ["Czechia", "Czech Republic"],
            "Turkey": ["Türkiye", "Turkey"], "Hong Kong": ["Hong Kong"], "South Korea": ["South Korea", "Korea"],
            "United Kingdom": ["United Kingdom"], "United Arab Emirates": ["United Arab Emirates"]}


def base(t: str | None) -> str:
    """'New York (and vicinity)' / 'Las Vegas (NV)' / 'Zürich' / 'Hong Kong SAR' -> comparable name."""
    import re
    import unicodedata
    t = re.sub(r"\s*\(.*?\)", "", t or "").replace(" SAR", "").replace("İ", "I")
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return t.strip().lower().replace(", dc", "").replace(",", "")


OVERRIDES: dict[str, dict] = {
    "London": {"viator": 737}, "Naples": {"viator": 508}, "Sydney": {"viator": 357},
    "New York": {"viator": 687}, "Kraków": {"viator": 529}, "Bali": {"viator": 98, "gyg_iata": "DPS"},
    "Cancún": {"viator": 631}, "Tromsø": {"viator": 4362}, "Washington, DC": {"viator": 657},
    "Okinawa": {"viator": 5614}, "Amalfi Coast": {"viator": 946}, "Hokkaido": {"viator": 5558},
    "Hong Kong": {"viator": 35959}, "Coachella": {"viator": 648},
    "Seville": {"gyg_iata": "SVQ"}, "Santorini": {"gyg_iata": "JTR"}, "Mykonos": {"gyg_iata": "JMK"},
    "Cebu": {"gyg_iata": "CEB"},
    # Klook (2026-11-12): its suggestions carry no country, so prefectures/regions and spellings by hand
    "Fukuoka": {"klook": "5209"}, "Hiroshima": {"klook": "5122"}, "Okinawa": {"viator": 5614, "klook": "6484"},
    "Maui": {"klook": "365001"}, "Chamonix": {"klook": "700232"}, "Marrakech": {"klook": "289"},
    "Tromsø": {"viator": 4362, "klook": "172"}, "Perth": {"klook": "88"},
}


def kslug(t: str) -> str:
    """'Washington, DC' -> 'washington-dc', 'Kraków' -> 'krakow' (Klook's suggestion titles)."""
    import re
    import unicodedata
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def get(path: str):
    with urllib.request.urlopen(S + path, timeout=20) as r:
        return json.loads(r.read())


def q(s: str) -> str:
    return urllib.parse.quote(s)


def cities() -> dict[str, str]:
    import add_aeo
    out = {}
    for p in sorted((REPO / "site").rglob("*.html")):
        d = add_aeo.page_dest(p.stem)
        if d and d[0] != "Europe":
            city = d[0].replace(" NSW", "")
            guide = d[3]
            country = (add_aeo.stay22.PAGES[guide]["address"].split(",")[-1].strip() if guide in add_aeo.stay22.PAGES
                       else {"japan": "Japan", "south-korea": "South Korea", "taiwan": "Taiwan", "thailand": "Thailand",
                             "vietnam": "Vietnam", "australia": "Australia"}.get(d[4] or "", ""))
            out.setdefault(city, country)
    return out


def main() -> None:
    res, check = {}, {}
    for city, country in sorted(cities().items()):
        row = {"country": country}
        v = [x for x in get(f"/search?service=viator_places&term={q(city)}") if x.get("title") == city and x.get("type") == "city"]
        if len(v) == 1:
            row["viator"] = v[0]["value"]
        elif v:
            check[city] = f"viator: {len(v)} places named {city}"
        a = [x for x in get(f"/uaca/v1/search_terms_forward?term={q(city)}&locale=en&service=aviasales")
             if x.get("title") == city and len(x.get("slug", "")) == 3]
        a_c = [x for x in a if x.get("subtitle") == country] or ([a[0]] if len(a) == 1 else [])
        if a_c:
            row["gyg_iata"] = a_c[0]["slug"]
        if country in ASIA_12GO:
            t = [x for x in get(f"/widgets/v1/onetwogo/autocomplete?term={q(city)}") if x.get("title") == city]
            if t:
                row["twelvego"] = city
        if country in EUROPE:
            o = [x for x in get(f"/uaca/v1/get_data_forward?service=omio_data&title={q(city)}")
                 if x.get("title") == city and (x.get("slug") == country or country in ("United Kingdom", "Scotland", "England"))]
            if o:
                row["omio"] = o[0]["value"]
        names = CN_ALIAS.get(country, [country]) if country else []
        inc = lambda txt: not names or any(n in (txt or "") for n in names)
        vio = [x for x in get(f"/uaca/v1/search_terms_forward?service=vio_suggest&term={q(city)}&locale=en")
               if x.get("slug") in ("city", "country") and base(x.get("title")) == base(city) and inc(x.get("subtitle"))]
        if vio:
            row["vio"] = vio[0]["title"]
        ag = [x for x in get(f"/uaca/v1/search_terms_forward?service=agoda&term={q(city)}&locale=en")
              if x.get("subtitle") == "City" and base(x.get("title", "").split(",")[0]) == base(city) and inc(x.get("title"))]
        if ag:
            row["agoda"] = ag[0]["title"]
        k = [x for x in get(f"/uaca/v1/search_terms_forward?service=klook&term={q(city)}&locale=en")
             if kslug(x.get("title", "")) == kslug(city)]
        if len(k) == 1:
            row["klook"] = k[0]["value"]
        elif k:
            check[city] = f"klook: {len(k)} places named {city}"
        if country in TM:
            row["tm_country"] = TM[country]
        row.update(OVERRIDES.get(city, {}))
        res[city] = row
        time.sleep(0.15)
    OUT.write_text(json.dumps({"cities": res, "check": check}, indent=1, ensure_ascii=False) + "\n")
    print(len(res), "cities;", sum("viator" in r for r in res.values()), "viator;",
          sum("gyg_iata" in r for r in res.values()), "gyg;", sum("twelvego" in r for r in res.values()), "12go;",
          sum("omio" in r for r in res.values()), "omio;", sum("vio" in r for r in res.values()), "vio;",
          sum("agoda" in r for r in res.values()), "agoda;", sum("tm_country" in r for r in res.values()), "ticketmaster;",
          sum("klook" in r for r in res.values()), "klook")
    for c, why in check.items():
        print("check:", c, "-", why)


if __name__ == "__main__":
    main()
