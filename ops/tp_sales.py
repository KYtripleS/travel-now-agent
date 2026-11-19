"""Travelpayouts sales, read-only: every action with a value (bookings), by brand, page and placement.

The sub_id on each action is set at click time by js/gy-reveal.js as <page>__<placement>, so a sale
names the page and the block that earned it. Reads the statistics API with TRAVELPAYOUTS_API_TOKEN.

usage: .venv/bin/python ops/tp_sales.py [--since 2026-06-01]
"""
import argparse
import os
import sys
from collections import Counter
from pathlib import Path

import requests
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
load_dotenv(REPO / ".env")
API = "https://api.travelpayouts.com/statistics/v1/execute_query"
BRANDS = {89: "Tiqets", 108: "GetYourGuide", 47: "Viator", 104: "Agoda", 100: "Aviasales", 91: "Omio",
          121: "Kiwi.com", 638: "Trip.com", 183: "Airalo"}   # ids seen in our actions; unknown ids print as numbers


def actions(since: str) -> list[dict]:
    h = {"X-Access-Token": os.getenv("TRAVELPAYOUTS_API_TOKEN", "")}
    out, off = [], 0
    while True:
        body = {"fields": ["action_id", "campaign_id", "sub_id", "price_usd", "paid_profit_usd", "state", "created_at"],
                "filters": [{"field": "created_at", "op": "ge", "value": f"{since} 00:00:00"}],
                "sort": [{"field": "created_at", "order": "desc"}], "offset": off, "limit": 1000}
        r = requests.post(API, headers=h, json=body, timeout=60)
        r.raise_for_status()
        res = r.json()["results"]
        out += res
        off += len(res)
        if len(res) < 1000:
            return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-06-01")
    a = ap.parse_args()
    rows = actions(a.since)
    sales = [x for x in rows if x["state"] or float(x["price_usd"] or 0) > 0]
    print(f"actions since {a.since}: {len(rows)}; with a booking: {len(sales)}")
    total = 0.0
    for x in sales:
        brand = BRANDS.get(x["campaign_id"], x["campaign_id"])
        total += float(x["paid_profit_usd"] or 0)
        print(f"  {x['created_at'][:10]}  {brand:<12} ${float(x['price_usd']):>8.2f} -> ${float(x['paid_profit_usd']):.2f} "
              f"[{x['state'] or 'pending'}]  {x['sub_id']}")
    print(f"commission: ${total:.2f}")
    by = Counter(x["sub_id"].rsplit("_", 1)[0] for x in rows if x["sub_id"])
    print("most actions by page (clicks and bookings):", ", ".join(f"{k} {n}" for k, n in by.most_common(5)))


if __name__ == "__main__":
    sys.exit(main())
