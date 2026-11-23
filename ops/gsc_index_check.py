"""Ask Search Console whether Google has indexed our pages (URL Inspection API, read-only, free).

Why: the weekly money-page report showed almost every page published since late October with 0 Google
impressions in 28 days. This tells us whether Google crawled them, skipped them, or indexed them.

  .venv/bin/python ops/gsc_index_check.py                 # pages with 0 impressions in the newest money-pages report
  .venv/bin/python ops/gsc_index_check.py slug-a slug-b   # named article slugs

Writes gsc_reports/index-<date>.md. Quota: 2,000 inspections a day; this sends one per page.
"""
from __future__ import annotations

import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import gsc_analyze as g  # noqa: E402

API = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"


def zero_impression_slugs() -> list[str]:
    reports = sorted((REPO / "ga4_reports").glob("money-pages-*.md"))
    if not reports:
        sys.exit("no money-pages report; run ops/money_pages_report.py first")
    slugs: list[str] = []
    for line in reports[-1].read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        # first table: Page | Published | Google impr | ...
        if len(cells) >= 4 and cells[2] == "0" and cells[1][:4] == "2026" and cells[0] not in slugs:
            slugs.append(cells[0])
    return slugs


def main() -> None:
    import requests
    g._load_env()
    sa = os.environ.get("GSC_SA_JSON") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    site = os.environ.get("GSC_SITE_URL", "https://gentlyyonder.com/")
    if not sa:
        sys.exit("GSC service-account path not set in .env (see gsc_analyze.py)")
    token = g._session_token(Path(sa))
    slugs = sys.argv[1:] or zero_impression_slugs()
    rows, states = [], Counter()
    for slug in slugs:
        url = f"https://gentlyyonder.com/articles/{slug}.html"
        r = requests.post(API, headers={"Authorization": f"Bearer {token}"},
                          json={"inspectionUrl": url, "siteUrl": site}, timeout=60)
        if r.status_code != 200:
            rows.append((slug, f"API {r.status_code}", "", ""))
            states[f"API {r.status_code}"] += 1
            continue
        idx = r.json().get("inspectionResult", {}).get("indexStatusResult", {})
        state = idx.get("coverageState", "?")
        states[state] += 1
        rows.append((slug, state, (idx.get("lastCrawlTime") or "never")[:10],
                     idx.get("googleCanonical", "")[-60:]))
        print(f"{state:45} {rows[-1][2]:10} {slug}")
    out = REPO / "gsc_reports" / f"index-{date.today()}.md"
    lines = [f"# Google index status, {date.today()} ({len(rows)} pages)", "",
             *[f"- {s}: {n}" for s, n in states.most_common()], "",
             "| Page | Coverage | Last crawl | Google canonical |", "|---|---|---|---|",
             *[f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]]
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(f"{s}: {n}" for s, n in states.most_common()))
    print(f"wrote {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
