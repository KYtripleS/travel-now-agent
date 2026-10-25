"""Stay22 bookings by page and placement, from the Stay22 Reporting API (read-only).

Stay22 campaigns are "<page>__<placement>" for links (set at click time by gy-reveal.js) and
"<page>_map" for the hotel-map iframes, so each booking says which page and which block earned it.
STAY22_API_TOKEN in .env; the token is never printed.

usage: .venv/bin/python ops/stay22_report.py [--days 90]
"""
import argparse
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent
API = "https://api.stay22.com/v1/reporting/transactions"


def token() -> str:
    for line in (REPO / ".env").read_text().splitlines():
        if line.startswith("STAY22_API_TOKEN="):
            return line.split("=", 1)[1].strip().strip("\"'")
    raise SystemExit("STAY22_API_TOKEN missing from .env")


def transactions(start: str, end: str) -> list[dict]:
    rows, page = [], 0
    while True:
        r = requests.get(API, headers={"X-API-KEY": token()}, timeout=60,
                         params={"format": "json", "startDate": start, "endDate": end,
                                 "dateFilter": "bookedDate", "page": page, "limit": 500})
        r.raise_for_status()
        data = r.json().get("data", [])
        rows += data
        if len(data) < 500:
            return rows
        page += 1


def split(campaign: str) -> tuple[str, str]:
    if "__" in campaign:
        page, placement = campaign.rsplit("__", 1)
    elif campaign.endswith("_map"):
        page, placement = campaign[:-4], "map"
    else:
        page, placement = campaign, "(load-time stamp)"
    return page, placement


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=90)
    args = ap.parse_args()
    end = date.today()
    rows = transactions((end - timedelta(days=args.days)).isoformat(), end.isoformat())
    print(f"Stay22 bookings, booked {end - timedelta(days=args.days)} → {end}: {len(rows)}")
    by = defaultdict(lambda: [0, 0.0])
    for t in rows:
        page, placement = split(t.get("campaignId") or "")
        key = (page, placement, t.get("bookingStatus", ""))
        by[key][0] += 1
        by[key][1] += float(t.get("commission") or 0)
    for (page, placement, status), (n, usd) in sorted(by.items(), key=lambda x: -x[1][1]):
        print(f"  {page:45} {placement:18} {status:10} {n:3}  US${usd:,.2f}")
    for t in rows:
        print(f"  - {t.get('bookedDate')} {t.get('destination')} {t.get('provider')} {t.get('device')} "
              f"{t.get('userCountry')} stay {t.get('startDate')}→{t.get('endDate')} {t.get('bookingStatus')} "
              f"US${t.get('commission')}")


if __name__ == "__main__":
    main()
