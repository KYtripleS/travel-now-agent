"""Refresh the eSIM plan prices behind the "plans for your trip" table on the country eSIM guides.

Airalo is read from its own country pages (USD, the plan list in the page's Nuxt payload).
Saily's pages refuse scripted requests, so its plans are typed into data/esim_plans.json by hand
from saily.com in a browser, with the date checked; this script only warns when they are old.

usage: .venv/bin/python ops/esim_prices.py            # refresh Airalo, report Saily's age
       .venv/bin/python ops/esim_prices.py --check    # report only, change nothing
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data" / "esim_plans.json"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0)", "Cookie": "currency=USD"}
STALE_DAYS = 35


def airalo_plans(slug: str) -> list[dict]:
    """Fixed-data plans on airalo.com/<slug>-esim, in US dollars (unlimited plans left out)."""
    url = f"https://www.airalo.com/{slug}-esim?currency=USD"
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    m = re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
    if not m:
        raise RuntimeError(f"{url}: no plan payload (page layout changed?)")
    arr = json.loads(m.group(1))

    def val(i, depth=0):
        v = arr[i] if isinstance(i, int) else i
        if depth > 6:
            return v
        if isinstance(v, dict):
            return {k: val(x, depth + 1) for k, x in v.items()}
        if isinstance(v, list):
            if v and isinstance(v[0], str) and v[0] in ("Reactive", "ShallowReactive", "Ref", "ShallowRef"):
                return val(v[1], depth + 1)
            return [val(x, depth + 1) for x in v]
        return v

    plans, seen = [], set()
    for i, v in enumerate(arr):
        if not (isinstance(v, dict) and {"validity", "price", "data", "slug"} <= v.keys()):
            continue
        p = val(i)
        price = p["price"] if isinstance(p["price"], dict) else {}
        if p["slug"] in seen or p.get("is_unlimited") or price.get("currency", {}).get("code") != "USD":
            continue
        gb = re.match(r"([\d.]+)\s*GB", str(p["data"]))
        days = re.match(r"(\d+)", str(p["validity"]))
        if not (gb and days):
            continue
        seen.add(p["slug"])
        plans.append({"gb": float(gb.group(1)), "days": int(days.group(1)), "usd": float(price["amount"])})
    if not plans:
        raise RuntimeError(f"{url}: no USD plans found")
    return sorted(plans, key=lambda x: (x["gb"], x["days"], x["usd"]))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    data = json.loads(DATA.read_text())
    today = date.today()
    for key, c in data["countries"].items():
        if not args.check:
            c["airalo"] = {"checked": today.isoformat(), "url": f"https://www.airalo.com/{c['airalo_slug']}-esim",
                           "plans": airalo_plans(c["airalo_slug"])}
        for brand in ("airalo", "saily"):
            age = (today - date.fromisoformat(c[brand]["checked"])).days
            flag = "  STALE: recheck" if age > STALE_DAYS else ""
            print(f"{key:13} {brand:6} checked {c[brand]['checked']} ({age} d){flag}")
    if not args.check:
        DATA.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
        print(f"wrote {DATA.relative_to(REPO)}")


if __name__ == "__main__":
    sys.exit(main())
