#!/usr/bin/env python3
"""
affiliate_tools.py — Affiliate link management utilities for Travel Now.

IMPORTANT: This tool only reads and reports. It never fetches from Amazon,
scrapes product data, or modifies any existing links.

Usage:
  python affiliate_tools.py list                        # list active links
  python affiliate_tools.py list --all                  # include inactive links
  python affiliate_tools.py category "Packing Essentials"
  python affiliate_tools.py check-disclosures           # check HTML files for disclosure notice
  python affiliate_tools.py check-placeholders          # check products.csv for missing/untagged links
  python affiliate_tools.py weekly-summary              # last 7 days from click log
  python affiliate_tools.py weekly-summary --weeks 4    # last 4 weeks
"""

import argparse
import csv
from datetime import date, timedelta
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────

AFFILIATE_LINKS_CSV  = Path("affiliate_links.csv")
CLICK_LOG_CSV        = Path("affiliate_click_log.csv")
PRODUCTS_CSV_PATHS   = [Path("site/products.csv"), Path("docs/products.csv")]
HTML_DIRS            = [Path("site"), Path("docs")]
AFFILIATE_TAG        = "packlightpick-20"
REQUIRED_TAG_PARAM   = f"tag={AFFILIATE_TAG}"

# Keywords that satisfy an affiliate disclosure check
DISCLOSURE_KEYWORDS  = [
    "affiliate",
    "commission",
    "sponsored",
    "disclosure",
    "associate",
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_links(active_only: bool = True) -> list[dict]:
    if not AFFILIATE_LINKS_CSV.exists():
        return []
    with AFFILIATE_LINKS_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if active_only:
        rows = [r for r in rows if r.get("status", "active").strip().lower() == "active"]
    return rows


def _tag_ok(url: str) -> bool:
    return REQUIRED_TAG_PARAM in url


# ── Commands ───────────────────────────────────────────────────────────────────

def list_links(active_only: bool = True) -> None:
    """Print all affiliate links grouped by category."""
    rows = _load_links(active_only)
    label = "ACTIVE ONLY" if active_only else "ALL"
    print(f"\n=== AFFILIATE LINKS ({label}) ===")

    if not rows:
        print(f"  No links found in {AFFILIATE_LINKS_CSV}.")
        return

    # Group by category
    by_cat: dict[str, list] = {}
    for r in rows:
        cat = r.get("category", "Uncategorized")
        by_cat.setdefault(cat, []).append(r)

    total = 0
    missing_tag = 0
    for cat, items in by_cat.items():
        print(f"\n  {cat}  ({len(items)} link(s))")
        for r in items:
            name   = r.get("product_name", "")
            url    = r.get("amazon_url", "")
            status = r.get("status", "active")
            ok     = _tag_ok(url)
            mark   = "✓" if ok else "✗ MISSING TAG"
            status_label = "" if status == "active" else f"  [{status}]"
            print(f"    {mark}  {name}{status_label}")
            print(f"           {url}")
            if not ok:
                missing_tag += 1
        total += len(items)

    print(f"\n  Total: {total} link(s)")
    if missing_tag:
        print(f"  WARNING: {missing_tag} link(s) missing affiliate tag '{REQUIRED_TAG_PARAM}'")
    else:
        print(f"  All links tagged with '{REQUIRED_TAG_PARAM}'. ✓")
    print("=" * 44)


def show_by_category(category: str) -> None:
    """Print all links for a given category (case-insensitive, partial match)."""
    rows = _load_links(active_only=False)
    term = category.strip().lower()

    matches = [r for r in rows if r.get("category", "").strip().lower() == term]
    if not matches:
        # Try partial match
        matches = [r for r in rows if term in r.get("category", "").strip().lower()]

    print(f"\n=== CATEGORY: {category} ===")
    if not matches:
        print(f"  No links found for '{category}'.")
        available = sorted({r.get("category", "") for r in rows if r.get("category")})
        if available:
            print("  Available categories:")
            for c in available:
                print(f"    - {c}")
        return

    for r in matches:
        name      = r.get("product_name", "")
        url       = r.get("amazon_url", "")
        placement = r.get("placement", "")
        status    = r.get("status", "active")
        notes     = r.get("notes", "")
        mark      = "✓" if _tag_ok(url) else "✗ MISSING TAG"

        print(f"\n  {mark}  [{status}] {name}")
        print(f"    URL:       {url}")
        if placement:
            for loc in placement.split("|"):
                print(f"    Placement: {loc.strip()}")
        if notes:
            print(f"    Notes:     {notes}")

    print(f"\n  {len(matches)} link(s) in this category.")
    print("=" * 44)


def check_disclosures() -> list[str]:
    """
    Check HTML files that contain Amazon links for an affiliate disclosure notice.
    Returns a list of file paths that are missing a disclosure.
    """
    print("\n=== DISCLOSURE CHECK ===")

    issues: list[str] = []
    checked = 0

    checked_paths: set[str] = set()

    for html_dir in HTML_DIRS:
        if not html_dir.exists():
            continue
        html_files = sorted(html_dir.glob("*.html")) + sorted(html_dir.glob("articles/*.html"))
        for html_file in html_files:
            rel = str(html_file)
            # Skip duplicates (site/ and docs/ often mirror each other)
            name_key = html_file.name + str(html_file.parent.name)
            if name_key in checked_paths:
                continue
            checked_paths.add(name_key)

            content = html_file.read_text(encoding="utf-8").lower()

            # Only audit files that actually contain Amazon affiliate links
            if "amazon.com" not in content:
                continue

            checked += 1
            has_disclosure = any(kw in content for kw in DISCLOSURE_KEYWORDS)
            mark = "✓" if has_disclosure else "✗"
            print(f"  {mark}  {rel}")
            if not has_disclosure:
                issues.append(rel)

    print(f"\n  Checked: {checked} HTML file(s) with Amazon links")

    if issues:
        print(f"  Missing disclosure: {len(issues)} file(s)")
        print()
        print("  Suggested fix — add this inside the <article> or before the first product link:")
        print()
        print('    <p class="disclosure">This page contains affiliate links.')
        print('    If you purchase through these links, we may earn a small commission')
        print('    at no extra cost to you.</p>')
    else:
        print("  All checked files have a disclosure. ✓")

    print("=" * 44)
    return issues


def check_placeholders() -> int:
    """
    Check products.csv files for rows that are missing the affiliate tag
    or using obvious placeholder URLs.
    Returns total number of issues found.
    """
    print("\n=== PLACEHOLDER / TAG CHECK ===")

    total_issues = 0
    found_any    = False

    for csv_path in PRODUCTS_CSV_PATHS:
        if not csv_path.exists():
            print(f"  {csv_path}: not found, skipping.")
            continue

        found_any = True
        with csv_path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        issues: list[tuple[str, str]] = []
        for row in rows:
            url  = row.get("url", "").strip()
            name = row.get("item", row.get("product_name", "(unknown)"))

            if not url:
                issues.append((name, "MISSING URL"))
            elif REQUIRED_TAG_PARAM not in url:
                issues.append((name, f"MISSING TAG — {url}"))
            elif "example.com" in url or "placeholder" in url.lower():
                issues.append((name, f"PLACEHOLDER URL — {url}"))

        print(f"\n  {csv_path}  ({len(rows)} products)")
        if issues:
            for name, msg in issues:
                print(f"    ✗  {name}: {msg}")
            total_issues += len(issues)
        else:
            print(f"    ✓  All {len(rows)} links tagged with '{REQUIRED_TAG_PARAM}'")

    if not found_any:
        print("  No products.csv files found.")

    print()
    if total_issues:
        print(f"  Total issues: {total_issues}")
        print(f"  Fix: add &tag={AFFILIATE_TAG} to each flagged URL.")
    else:
        print("  No issues found. ✓")

    print("=" * 44)
    return total_issues


def weekly_summary(weeks: int = 1) -> None:
    """
    Generate a revenue summary from affiliate_click_log.csv for the last N weeks.
    The log is manually maintained — this tool only reads it, never writes to it.
    """
    print(f"\n=== WEEKLY SUMMARY (last {weeks} week(s)) ===")

    if not CLICK_LOG_CSV.exists():
        print(f"  {CLICK_LOG_CSV} not found.")
        print("  Create the file with the required headers to start tracking.")
        _print_log_headers()
        return

    with CLICK_LOG_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("  Click log is empty — no data to summarise yet.")
        print(f"  Add rows to {CLICK_LOG_CSV} after each content piece is published.")
        _print_log_headers()
        return

    cutoff = date.today() - timedelta(weeks=weeks)

    def _parse_date(s: str):
        try:
            return date.fromisoformat(s.strip())
        except (ValueError, AttributeError):
            return None

    period_rows = [
        r for r in rows
        if (d := _parse_date(r.get("date", ""))) and d >= cutoff
    ]

    if not period_rows:
        print(f"  No entries in the last {weeks} week(s).")
        print(f"  (cutoff: {cutoff.isoformat()}, total log rows: {len(rows)})")
        return

    # Aggregate totals
    total_clicks  = 0
    total_orders  = 0
    total_revenue = 0.0
    by_category: dict[str, dict] = {}
    by_platform:  dict[str, dict] = {}

    for r in period_rows:
        try:
            clicks  = int(r.get("clicks", 0) or 0)
            orders  = int(r.get("orders", 0) or 0)
            revenue = float(r.get("revenue_yen", 0) or 0)
        except ValueError:
            clicks = orders = 0
            revenue = 0.0

        total_clicks  += clicks
        total_orders  += orders
        total_revenue += revenue

        cat = r.get("product_category", "Unknown")
        if cat not in by_category:
            by_category[cat] = {"clicks": 0, "orders": 0, "revenue": 0.0}
        by_category[cat]["clicks"]  += clicks
        by_category[cat]["orders"]  += orders
        by_category[cat]["revenue"] += revenue

        plat = r.get("platform", "Unknown")
        if plat not in by_platform:
            by_platform[plat] = {"clicks": 0, "orders": 0}
        by_platform[plat]["clicks"] += clicks
        by_platform[plat]["orders"] += orders

    # Print summary
    print(f"\n  Period:  {cutoff.isoformat()} → {date.today().isoformat()}")
    print(f"  Entries: {len(period_rows)}")
    print()
    print(f"  Total clicks:    {total_clicks}")
    print(f"  Total orders:    {total_orders}")
    print(f"  Total revenue:   ¥{total_revenue:,.0f}")
    if total_clicks > 0:
        conv = (total_orders / total_clicks) * 100
        print(f"  Conversion rate: {conv:.1f}%")

    if by_category:
        print("\n  By category:")
        for cat, data in sorted(by_category.items(), key=lambda x: -x[1]["revenue"]):
            print(
                f"    {cat:<32}  "
                f"clicks: {data['clicks']:3d}  "
                f"orders: {data['orders']:2d}  "
                f"revenue: ¥{data['revenue']:,.0f}"
            )

    if by_platform:
        print("\n  By platform:")
        for plat, data in sorted(by_platform.items(), key=lambda x: -x[1]["clicks"]):
            print(
                f"    {plat:<22}  "
                f"clicks: {data['clicks']:3d}  "
                f"orders: {data['orders']:2d}"
            )

    print("=" * 44)


def _print_log_headers() -> None:
    print()
    print("  Required CSV headers:")
    print("  date, platform, source_content, destination_page,")
    print("  product_category, link_url, clicks, orders, revenue_yen, notes")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Travel Now affiliate link management tools.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = sub.add_parser("list", help="List affiliate links (active only by default)")
    p_list.add_argument(
        "--all", dest="show_all", action="store_true",
        help="Include inactive links"
    )

    # category
    p_cat = sub.add_parser("category", help="Show links for one category")
    p_cat.add_argument("name", help="Category name (partial match supported)")

    # check-disclosures
    sub.add_parser(
        "check-disclosures",
        help="Check HTML files with Amazon links for an affiliate disclosure notice"
    )

    # check-placeholders
    sub.add_parser(
        "check-placeholders",
        help="Check products.csv files for links missing the affiliate tag"
    )

    # weekly-summary
    p_ws = sub.add_parser(
        "weekly-summary",
        help="Generate a revenue summary from affiliate_click_log.csv"
    )
    p_ws.add_argument(
        "--weeks", type=int, default=1,
        help="Number of weeks to look back (default: 1)"
    )

    args = parser.parse_args()

    if args.command == "list":
        list_links(active_only=not args.show_all)
    elif args.command == "category":
        show_by_category(args.name)
    elif args.command == "check-disclosures":
        check_disclosures()
    elif args.command == "check-placeholders":
        check_placeholders()
    elif args.command == "weekly-summary":
        weekly_summary(weeks=args.weeks)


if __name__ == "__main__":
    main()
