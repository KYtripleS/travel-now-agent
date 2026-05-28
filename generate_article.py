#!/usr/bin/env python3
"""
generate_article.py

Turns rows in data/content_log.csv into draft article HTML files.

Usage:
  python generate_article.py              # dry run — shows what would happen
  python generate_article.py --write      # write new articles
  python generate_article.py --write --force  # also overwrite existing articles
"""

import argparse
import csv
import re
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────

CONTENT_LOG   = Path("data/content_log.csv")
PRODUCTS_CSV  = Path("site/products.csv")
SITE_ARTICLES = Path("site/articles")
DOCS_ARTICLES = Path("docs/articles")

# ── Category → product-category mapping ────────────────────────────────────────
# Keys match values in content_log.csv "category" column (case-sensitive).
# Values match "category" values in products.csv.

CATEGORY_PRODUCT_MAP = {
    "eSIM":           ["eSIM & Connectivity"],
    "EDC":            ["Power & Charging", "Travel Safety"],
    "Carry-on":       ["Packing Essentials"],
    "Packing":        ["Packing Essentials"],
    "Flight Comfort": ["Flight Comfort"],
    "Flight":         ["Flight Comfort"],
    "Power":          ["Power & Charging"],
    "Safety":         ["Travel Safety"],
    "Camera":         ["Camera Travel Gear"],
    "Hotels":         [],
    "Brand":          [],
    "VPN":            [],
    "Insurance":      [],
}

MAX_PRODUCTS = 3


# ── Slug helpers ───────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """Convert a topic string into a URL-friendly filename slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)   # drop special chars (keep hyphen)
    text = re.sub(r"\s+", "-", text.strip())  # spaces → hyphens
    text = re.sub(r"-+", "-", text)           # collapse double hyphens
    return text


# ── Data loading ───────────────────────────────────────────────────────────────

def load_candidates() -> list[dict]:
    """Return all content_log rows where article_candidate == 'yes'."""
    if not CONTENT_LOG.exists():
        raise FileNotFoundError(f"Content log not found: {CONTENT_LOG}")

    candidates = []
    with CONTENT_LOG.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("article_candidate", "").strip().lower() == "yes":
                candidates.append(row)
    return candidates


def deduplicate(candidates: list[dict]) -> dict[str, dict]:
    """
    Group candidates by slug. When the same topic appears more than once,
    keep the most recently dated row.
    """
    by_slug: dict[str, dict] = {}
    for row in candidates:
        slug = slugify(row["topic"])
        existing = by_slug.get(slug)
        if existing is None or row.get("date", "") >= existing.get("date", ""):
            by_slug[slug] = row
    return by_slug


def load_products() -> dict[str, list[dict]]:
    """Return products grouped by category, sorted by priority ascending."""
    if not PRODUCTS_CSV.exists():
        raise FileNotFoundError(f"Products CSV not found: {PRODUCTS_CSV}")

    by_cat: dict[str, list[dict]] = {}
    with PRODUCTS_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            by_cat.setdefault(row["category"], []).append(row)

    for cat in by_cat:
        by_cat[cat].sort(key=lambda r: int(r.get("priority", 99)))

    return by_cat


# ── Content parsing ────────────────────────────────────────────────────────────

def parse_hook(post_text: str) -> str:
    """Return the first non-empty line of post_text (the hook sentence)."""
    for line in post_text.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def parse_checklist(post_text: str) -> list[str]:
    """Extract numbered list items from post_text (lines like '1. text')."""
    items = []
    for line in post_text.splitlines():
        m = re.match(r"^\d+\.\s+(.+)$", line.strip())
        if m:
            items.append(m.group(1))
    return items


def display_title(topic: str) -> str:
    """
    Capitalise each word with three rules:
    - ALL-CAPS (VPN, EDC) → preserved as-is
    - mixed-case (eSIM, iPhone) → preserved as-is
    - fully lowercase (activation, and) → first letter uppercased
    """
    out = []
    for w in topic.split():
        if not w:
            out.append(w)
        elif w == w.upper() and len(w) > 1:
            out.append(w)                        # ALL-CAPS acronym
        elif w == w.lower():
            out.append(w[0].upper() + w[1:])     # plain word → capitalise
        else:
            out.append(w)                        # mixed-case → leave intact
    return " ".join(out)


# ── HTML building ──────────────────────────────────────────────────────────────

def build_product_cards(products: list[dict]) -> str:
    cards = []
    for p in products:
        cards.append(
            f'        <article class="product-card">\n'
            f'          <h4>{p["item"]}</h4>\n'
            f'          <p>{p["description"]}</p>\n'
            f'          <a href="{p["url"]}" class="product-link"'
            f' target="_blank" rel="nofollow sponsored noopener">View options</a>\n'
            f'        </article>'
        )
    return "\n".join(cards)


def build_html(slug: str, row: dict, products: list[dict]) -> str:
    topic      = row["topic"]
    category   = row["category"]
    post_text  = row.get("post_text", "")
    notes      = row.get("notes", "")

    title       = display_title(topic)
    hook        = parse_hook(post_text)
    items       = parse_checklist(post_text)

    # Meta description: prefer notes, fall back to hook (capped at 155 chars)
    raw_desc = notes if notes else hook
    meta_desc = raw_desc[:155].replace('"', "&quot;")

    # Checklist block
    if items:
        li_html = "\n".join(f"        <li>{item}</li>" for item in items)
        checklist_block = (
            "      <h2>Before you go: checklist</h2>\n"
            "      <ol>\n"
            f"{li_html}\n"
            "      </ol>"
        )
    else:
        checklist_block = ""

    # Products block
    if products:
        cards_html = build_product_cards(products)
        products_block = (
            "\n      <h2>Useful prep items</h2>\n"
            "      <p>\n"
            "        A few items worth considering for this type of trip prep.\n"
            "      </p>\n\n"
            '      <div class="product-grid article-products">\n'
            f"{cards_html}\n"
            "      </div>\n"
        )
    else:
        products_block = ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title} | Travel Now</title>
  <meta name="description" content="{meta_desc}" />
  <link rel="stylesheet" href="../style-v2.css" />
</head>
<body>
  <header class="hero article-hero">
    <p class="label">Travel Now</p>
    <h1>{title}</h1>
    <p class="subtitle">
      A practical travel prep checklist from Travel Now.
    </p>

    <div class="buttons">
      <a href="../index.html" class="button secondary">Back to Travel Now</a>
    </div>
  </header>

  <main>
    <section class="article">
      <p class="label">{category}</p>

      <p>
        {hook}
      </p>

{checklist_block}

      <h2>Why this helps</h2>
      <p>
        Small preparation steps before a trip may reduce avoidable stress
        and make travel days feel smoother.
      </p>
{products_block}
      <div class="tip-box">
        <strong>Travel Now tip:</strong>
        Run through this checklist the day before you leave, not the morning of your flight.
      </div>

      <p class="back-link">
        <a href="../index.html">&#8592; Back to Travel Now</a>
      </p>
    </section>
  </main>

  <footer>
    <p>
      Disclosure: Some links on this page are affiliate links.
      As an Amazon Associate, Travel Now may earn from qualifying purchases
      at no extra cost to you.
    </p>
  </footer>
</body>
</html>
"""


# ── File writing ───────────────────────────────────────────────────────────────

def write_article(slug: str, html: str, *, force: bool, dry_run: bool) -> str:
    """
    Write to site/articles/ and docs/articles/.
    Returns a short status label.
    """
    site_path = SITE_ARTICLES / f"{slug}.html"
    docs_path = DOCS_ARTICLES / f"{slug}.html"
    exists    = site_path.exists() or docs_path.exists()

    if exists and not force:
        return "SKIPPED  (exists — use --force to overwrite)"

    action = "OVERWRITE" if exists else "CREATE"

    if dry_run:
        return f"{action}  (dry run)"

    SITE_ARTICLES.mkdir(parents=True, exist_ok=True)
    DOCS_ARTICLES.mkdir(parents=True, exist_ok=True)

    site_path.write_text(html, encoding="utf-8")
    docs_path.write_text(html, encoding="utf-8")

    return "OVERWRITTEN" if exists else "CREATED"


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate article HTML drafts from content_log.csv candidates."
    )
    parser.add_argument(
        "--write", action="store_true",
        help="Write files to disk. Without this flag the script is a dry run.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite existing articles. Requires --write.",
    )
    args = parser.parse_args()

    dry_run = not args.write
    force   = args.force

    if force and dry_run:
        print("Note: --force has no effect without --write.\n")

    if dry_run:
        print("DRY RUN — no files will be written. Pass --write to generate.\n")

    # ── Load ──────────────────────────────────────────────────────────────────
    try:
        all_candidates    = load_candidates()
        products_by_cat   = load_products()
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not all_candidates:
        print("No article candidates found in content_log.csv.")
        return

    candidates = deduplicate(all_candidates)

    print(
        f"Found {len(all_candidates)} candidate row(s) in content_log.csv "
        f"→ {len(candidates)} unique article(s) after deduplication.\n"
    )

    # ── Process ───────────────────────────────────────────────────────────────
    counts = {"created": 0, "skipped": 0, "overwritten": 0, "errors": 0}

    for slug, row in candidates.items():
        topic    = row["topic"]
        category = row["category"]

        try:
            prod_cats = CATEGORY_PRODUCT_MAP.get(category, [])
            products  = []
            for cat in prod_cats:
                products.extend(products_by_cat.get(cat, []))
            products = products[:MAX_PRODUCTS]

            html   = build_html(slug, row, products)
            status = write_article(slug, html, force=force, dry_run=dry_run)

        except Exception as exc:
            print(f"  ERROR    {slug}.html  —  {exc}")
            counts["errors"] += 1
            continue

        n_prods = len(products)
        unmapped = category not in CATEGORY_PRODUCT_MAP
        warn = "  ⚠ category not in map" if unmapped else ""

        print(f"  {status:<44}  {slug}.html  [{category}, {n_prods} product(s)]{warn}")

        if "SKIPPED" in status:
            counts["skipped"] += 1
        elif "OVERWRITE" in status:   # matches OVERWRITE (dry run) and OVERWRITTEN
            counts["overwritten"] += 1
        elif "CREATE" in status:      # matches CREATE (dry run) and CREATED
            counts["created"] += 1

    # ── Summary ───────────────────────────────────────────────────────────────
    verb = "would be created" if dry_run else "created"
    print(
        f"\nSummary: "
        f"{counts['created']} {verb}, "
        f"{counts['skipped']} skipped, "
        f"{counts['overwritten']} overwritten, "
        f"{counts['errors']} error(s)."
    )

    if dry_run and counts["created"] + counts["overwritten"] > 0:
        print("Run with --write to write files.")


if __name__ == "__main__":
    main()
