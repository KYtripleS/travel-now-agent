"""Create the Travelpayouts short links the trip kit and the flights box use (add_aeo.trip_kit_links).

Merchant URLs come from the hand-checked city maps (data/viator_cities.json,
data/hostelworld_cities.json, data/discovercars_cities.json) plus a few fixed pages. Short links
are cached in data/tp_deeplinks.json with ops/tp_deeplinks.py's other links, so the Links API is
called only for URLs it has not seen.

usage: .venv/bin/python ops/trip_kit_links.py
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "ops"))
import tp_deeplinks  # noqa: E402

FIXED = {
    "tripcom_flights": "https://www.trip.com/flights/",
    "kiwi": "https://www.kiwi.com/en/",
    "rakuten": "https://travel.rakuten.com/",
    "kiwitaxi": "https://kiwitaxi.com/",
    "airhelp": "https://www.airhelp.com/en/",
    "compensair": "https://www.compensair.com/",
}


def merchant_urls() -> dict[str, dict[str, str]]:
    """{kind: {city or key: merchant URL}}"""
    load = lambda name: json.loads((REPO / "data" / name).read_text())["cities"]
    return {
        "viator": {c: "https://www.viator.com" + p for c, p in load("viator_cities.json").items()},
        "hostelworld": {c: f"https://www.hostelworld.com/hostels/{p}/" for c, p in load("hostelworld_cities.json").items()},
        "discovercars": {c: f"https://www.discovercars.com/{p}" for c, p in load("discovercars_cities.json").items()},
        "fixed": FIXED,
    }


def main() -> None:
    cache = json.loads(tp_deeplinks.CACHE.read_text()) if tp_deeplinks.CACHE.exists() else {}
    wanted = sorted({u for group in merchant_urls().values() for u in group.values()} - set(cache))
    if wanted:
        cache.update(tp_deeplinks.create(wanted))
        tp_deeplinks.CACHE.write_text(json.dumps(dict(sorted(cache.items())), indent=1) + "\n")
    missing = [u for g in merchant_urls().values() for u in g.values() if u not in cache]
    print(f"created {len(wanted) - len(missing)}, missing {len(missing)}")
    for u in missing:
        print("  !", u)


if __name__ == "__main__":
    main()
