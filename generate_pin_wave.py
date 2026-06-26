#!/usr/bin/env python3
"""
generate_pin_wave.py

Batch-generates a new wave of Pinterest pins for the existing article
catalogue. Each wave uses a different Pexels photo and a different tagline
angle so Pinterest treats them as fresh content, while the brand template
(navy + gold + Georgia serif) stays consistent.

Usage:
  python generate_pin_wave.py 2          # generate wave 2 (17 pins)
  python generate_pin_wave.py 3          # generate wave 3 (17 pins)
  python generate_pin_wave.py 2 --csv    # also append rows to pins.csv

Each call POSTs to the local pin_server (must already be running on
127.0.0.1:8765). Outputs land in site/images/pinterest/{slug}-w{n}.png and
are mirrored to docs/ automatically by generate_pin.py.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from urllib import request, error

REPO_ROOT = Path(__file__).resolve().parent
PIN_SERVER = "http://127.0.0.1:8765/generate-pin"
PINS_CSV = REPO_ROOT / "marketing" / "pinterest_kit" / "pins.csv"

# Wave-2 specs — quick-start / curiosity angle.
# Each entry produces a pin with the original on-image title (recognisable
# brand) but a fresh Pexels photo + a wave-2 tagline. The Pinterest post
# title/description (when uploaded) uses the wave-2 phrasing from
# variant_patterns.md.
WAVE_2 = [
    dict(base="japan-photo",       title="JAPAN",     tagline="What to know before you book", pexelsQuery="Japan torii gate Mount Fuji winter"),
    dict(base="vietnam-photo",     title="VIETNAM",   tagline="Start here for your trip",     pexelsQuery="Vietnam street food market Hanoi"),
    dict(base="australia-photo",   title="AUSTRALIA", tagline="A layered guide for first-timers", pexelsQuery="Australia Uluru sunset outback"),
    dict(base="tokyo-photo",       title="TOKYO",     tagline="A layered city guide",          pexelsQuery="Tokyo skyline Tokyo Tower dusk"),
    dict(base="asakusa-photo",     title="ASAKUSA",   tagline="A half-day walking guide",      pexelsQuery="Asakusa Sensoji night lanterns"),
    dict(base="airport-liquids-photo", title="100 ML", tagline="Cheat sheet for carry-on liquids", pexelsQuery="TSA liquids 100ml bottles flat lay"),
    dict(base="carry-on-photo",    title="CARRY-ON",  tagline="The 4-step order security wants", pexelsQuery="carry on suitcase open packing cubes"),
    dict(base="beach-photo",       title="BEACH",     tagline="What to actually pack",          pexelsQuery="beach travel essentials sand straw bag"),
    dict(base="boat-day-photo",    title="BOAT DAY",  tagline="Europe rentals, no licence",     pexelsQuery="Croatia coast turquoise sailboat"),
    dict(base="esim-photo",        title="eSIM",      tagline="A simple activation guide",      pexelsQuery="international travel phone roaming map"),
    dict(base="travel-edc-photo",  title="TRAVEL EDC", tagline="Pocket essentials, no fluff",   pexelsQuery="minimalist travel essentials neutral flat lay"),
    dict(base="hotels-photo",      title="HOTELS",    tagline="How to decide quickly",          pexelsQuery="boutique hotel exterior facade Europe"),
    dict(base="untranslatable-photo", title="14 WORDS", tagline="What travellers take home",    pexelsQuery="vintage atlas globe library"),
    dict(base="etiquette-photo",   title="ETIQUETTE", tagline="12 cultures, 12 rules",          pexelsQuery="international travellers cafe table"),
    dict(base="south-korea-photo", title="SOUTH KOREA", tagline="Seoul and beyond",             pexelsQuery="Seoul Bukchon hanok village rooftops"),
    dict(base="insurance-photo",   title="INSURANCE", tagline="Which one covers you",           pexelsQuery="passport travel insurance document hand"),
    dict(base="capsule-photo",     title="CAPSULE",   tagline="10 items for 14 days",           pexelsQuery="minimalist clothes packed neutral tones"),
]

# Wave-3 specs — number-led / list angle.
WAVE_3 = [
    dict(base="japan-photo",       title="JAPAN",     tagline="8 sections, 1 layered guide",    pexelsQuery="Kyoto bamboo grove morning path"),
    dict(base="vietnam-photo",     title="VIETNAM",   tagline="8 things to know first",          pexelsQuery="Ho Chi Minh City motorbikes street"),
    dict(base="australia-photo",   title="AUSTRALIA", tagline="8 layers of a country profile",   pexelsQuery="Great Ocean Road coast Australia"),
    dict(base="tokyo-photo",       title="TOKYO",     tagline="6 districts, 1 city guide",       pexelsQuery="Shinjuku night neon lights crowd"),
    dict(base="asakusa-photo",     title="ASAKUSA",   tagline="4 stops for a half-day walk",     pexelsQuery="Nakamise Street paper lanterns Asakusa"),
    dict(base="airport-liquids-photo", title="100 ML", tagline="6 common rejections to avoid",   pexelsQuery="airport security tray phone laptop"),
    dict(base="carry-on-photo",    title="CARRY-ON",  tagline="5 mistakes that slow you down",   pexelsQuery="carry on bag overhead bin plane"),
    dict(base="beach-photo",       title="BEACH",     tagline="10 items most travellers forget", pexelsQuery="beach umbrella sunset palm tropical"),
    dict(base="boat-day-photo",    title="BOAT DAY",  tagline="6 countries, no licence required", pexelsQuery="yacht charter Mediterranean sunset"),
    dict(base="esim-photo",        title="eSIM",      tagline="4 steps, 10 minutes, done",       pexelsQuery="phone settings cellular eSIM activation"),
    dict(base="travel-edc-photo",  title="TRAVEL EDC", tagline="6 items earning pocket space",   pexelsQuery="everyday carry pocket items flat lay"),
    dict(base="hotels-photo",      title="HOTELS",    tagline="5 booking mistakes that cost",    pexelsQuery="hotel reception lobby check in"),
    dict(base="untranslatable-photo", title="14 WORDS", tagline="And why they resist English",   pexelsQuery="old library books reading lamp"),
    dict(base="etiquette-photo",   title="ETIQUETTE", tagline="12 countries compared",            pexelsQuery="diverse travellers cafe meeting"),
    dict(base="south-korea-photo", title="SOUTH KOREA", tagline="8 layers before your first trip", pexelsQuery="Korean street food Myeongdong night"),
    dict(base="insurance-photo",   title="INSURANCE", tagline="How to pick in 5 minutes",        pexelsQuery="travel medical insurance hospital abroad"),
    dict(base="capsule-photo",     title="CAPSULE",   tagline="10 items, 3 climates, 14 days",   pexelsQuery="wardrobe rack neutral colors minimalist"),
]

# Pin slug → article URL + bullets/cta + urlHint (shared across waves)
SHARED: dict[str, dict] = {
    "japan-photo":          dict(bullets=["History & geography", "Politics & economy", "Society & culture", "Travel prep checklist"], cta="Read the full profile →", urlHint="travelnow • countries/japan", articleUrl="https://kytriples.github.io/travel-now-agent/countries/japan/"),
    "vietnam-photo":        dict(bullets=["Geography & climate", "Modern economy", "Food & street culture", "Travel prep checklist"], cta="Read the full profile →", urlHint="travelnow • countries/vietnam", articleUrl="https://kytriples.github.io/travel-now-agent/countries/vietnam/"),
    "australia-photo":      dict(bullets=["History & geography", "Politics & economy", "Society & culture", "Travel prep checklist"], cta="Read the full profile →", urlHint="travelnow • countries/australia", articleUrl="https://kytriples.github.io/travel-now-agent/countries/australia/"),
    "tokyo-photo":          dict(bullets=["History & neighborhoods", "Modern districts", "Food & culture", "Practical prep"], cta="Read the full guide →", urlHint="travelnow • cities/tokyo", articleUrl="https://kytriples.github.io/travel-now-agent/cities/tokyo/"),
    "asakusa-photo":        dict(bullets=["Sensoji temple history", "Edo-era streets", "Practical visit tips", "Nearby districts"], cta="Read the neighborhood guide →", urlHint="travelnow • cities/tokyo/asakusa", articleUrl="https://kytriples.github.io/travel-now-agent/cities/tokyo/asakusa.html"),
    "airport-liquids-photo": dict(bullets=["100ml rule basics", "Clear plastic bag tips", "Common rejections", "Quick FAQ"], cta="Read the checklist →", urlHint="travelnow • airport-security-liquids", articleUrl="https://kytriples.github.io/travel-now-agent/articles/airport-security-liquids.html"),
    "carry-on-photo":       dict(bullets=["Liquids on top", "Laptop accessible", "Passport in pocket", "Charger logic"], cta="Read the prep guide →", urlHint="travelnow • airport-security-packing", articleUrl="https://kytriples.github.io/travel-now-agent/articles/airport-security-packing-moments.html"),
    "beach-photo":          dict(bullets=["Reef-safe sunscreen", "Packable sun hats", "Quick-dry towels", "Forgotten essentials"], cta="Read the checklist →", urlHint="travelnow • beach-trip-packing", articleUrl="https://kytriples.github.io/travel-now-agent/articles/beach-trip-packing-checklist.html"),
    "boat-day-photo":       dict(bullets=["UK, Italy, France rules", "Spain, Croatia, Greece", "Platforms & costs", "What to bring"], cta="Read the full guide →", urlHint="travelnow • charter-a-boat-for-a-day", articleUrl="https://kytriples.github.io/travel-now-agent/articles/charter-a-boat-for-a-day.html"),
    "esim-photo":           dict(bullets=["Phone compatibility", "Choosing a data plan", "Offline backup tips", "Pre-flight checklist"], cta="Read the setup guide →", urlHint="travelnow • esim-activation", articleUrl="https://kytriples.github.io/travel-now-agent/articles/esim-activation-and-preparation.html"),
    "travel-edc-photo":     dict(bullets=["Power bank", "Water bottle", "Hand sanitizer", "Small cash"], cta="Read the checklist →", urlHint="travelnow • everyday-carry-essentials", articleUrl="https://kytriples.github.io/travel-now-agent/articles/everyday-carry-essentials-for-travel.html"),
    "hotels-photo":         dict(bullets=["Hotels.com vs Booking", "Trip.com & Agoda", "HotelsCombined logic", "Common booking mistakes"], cta="Read the comparison →", urlHint="travelnow • hotel-booking-sites", articleUrl="https://kytriples.github.io/travel-now-agent/articles/hotel-booking-sites-comparison.html"),
    "untranslatable-photo": dict(bullets=["Saudade, Hygge, Wabi-sabi", "Why they resist English", "What linguists say", "What travelers take home"], cta="Read the full essay →", urlHint="travelnow • untranslatable-words", articleUrl="https://kytriples.github.io/travel-now-agent/articles/untranslatable-words.html"),
    "etiquette-photo":      dict(bullets=["Face & politeness theory", "Greeting conventions", "Dining manners", "Public space norms"], cta="Read the cultural guide →", urlHint="travelnow • what-counts-as-rude", articleUrl="https://kytriples.github.io/travel-now-agent/articles/what-counts-as-rude.html"),
    "south-korea-photo":    dict(bullets=["History & geography", "Politics & economy", "Society & culture", "Travel prep checklist"], cta="Read the full profile →", urlHint="travelnow • south-korea-country-profile", articleUrl="https://kytriples.github.io/travel-now-agent/articles/south-korea-country-profile.html"),
    "insurance-photo":      dict(bullets=["Provider archetypes", "Coverage & exclusions", "Claims process", "Decision framework"], cta="Read the comparison →", urlHint="travelnow • travel-insurance-compared", articleUrl="https://kytriples.github.io/travel-now-agent/articles/travel-insurance-compared.html"),
    "capsule-photo":        dict(bullets=["Core 10 pieces", "Fabric choices", "Layering logic", "Laundry strategy"], cta="Read the packing guide →", urlHint="travelnow • capsule-wardrobe", articleUrl="https://kytriples.github.io/travel-now-agent/articles/capsule-wardrobe-2-week-trips.html"),
}


def post_to_server(payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(PIN_SERVER, data=body, headers={"Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as e:
        return {"exitCode": e.code, "stderr": e.read().decode("utf-8")}
    except Exception as e:
        return {"exitCode": -1, "stderr": repr(e)}


def run_wave(wave: int, *, append_csv: bool) -> None:
    specs = {2: WAVE_2, 3: WAVE_3}.get(wave)
    if specs is None:
        sys.exit(f"unknown wave: {wave} (supported: 2, 3)")

    rows_for_csv: list[list[str]] = []
    ok = 0
    fail = 0
    for spec in specs:
        shared = SHARED[spec["base"]]
        slug = spec["base"] + f"-w{wave}"
        payload = {
            "slug": slug,
            "title": spec["title"],
            "tagline": spec["tagline"],
            "bullet1": shared["bullets"][0],
            "bullet2": shared["bullets"][1],
            "bullet3": shared["bullets"][2],
            "bullet4": shared["bullets"][3],
            "cta": shared["cta"],
            "urlHint": shared["urlHint"],
            "pexelsQuery": spec["pexelsQuery"],
        }
        print(f"  generating {slug}…", flush=True)
        result = post_to_server(payload)
        if result.get("exitCode") == 0:
            ok += 1
            print(f"    ✓ {result.get('stdout', '').splitlines()[0] if result.get('stdout') else 'ok'}")
        else:
            fail += 1
            print(f"    ✗ {result.get('stderr', 'unknown')[:160]}")
        # Append CSV row even on failure so user has full record
        rows_for_csv.append([
            "",                                              # post_day (assign manually)
            slug,
            f"site/images/pinterest/{slug}.png",
            shared["articleUrl"],
            spec["title"],                                   # simple title for now
            spec["tagline"],                                 # simple description for now
            "",                                              # board_primary (copy from wave 1)
            "",                                              # board_secondary
            "2",                                             # priority
        ])
        time.sleep(0.4)

    if append_csv and rows_for_csv:
        with PINS_CSV.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in rows_for_csv:
                writer.writerow(row)
        print(f"\nappended {len(rows_for_csv)} rows to {PINS_CSV.relative_to(REPO_ROOT)}")
    print(f"\n— wave {wave}: {ok} ok, {fail} failed —")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("wave", type=int, help="2 or 3")
    p.add_argument("--csv", action="store_true", help="append generated rows to pins.csv")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_wave(args.wave, append_csv=args.csv)
