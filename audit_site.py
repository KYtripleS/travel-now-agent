#!/usr/bin/env python3
"""
audit_site.py

Pre-deployment audit for the Travel Now site.
Prints PASS / WARN / FAIL for each check, then exits with code 1 if any FAILs.

Usage:
  python audit_site.py
"""

import csv
import hashlib
import re
import sys
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────

SITE_DIR     = Path("site")
DOCS_DIR     = Path("docs")
PRODUCTS_CSV = Path("site/products.csv")
CONTENT_LOG  = Path("data/content_log.csv")

AFFILIATE_TAG       = "tag=packlightpick-20"
REQUIRED_STYLESHEET = "style-v2.css"

REQUIRED_PRODUCTS_COLS = {
    "category", "item", "description", "url",
    "priority", "buyer_intent", "monetization", "article_slug",
}
REQUIRED_LOG_COLS = {
    "date", "platform", "category", "topic",
    "post_text", "cta", "status", "article_candidate", "notes",
}

# Files intentionally absent from site/ or docs/ — excluded from sync check
SYNC_ONLY_IN_DOCS = {".nojekyll"}
SYNC_IGNORE       = {".deploy-check.txt", "style.backup.css"}

# ── Result tracking ────────────────────────────────────────────────────────────

_results: list[tuple[str, str]] = []  # (status, label)


def result(label: str, status: str, detail: list[str] | None = None) -> None:
    """Print one check result and record it."""
    icons = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗"}
    print(f"  {status}  {icons[status]}  {label}")
    if detail:
        for line in detail:
            print(f"             {line}")
    _results.append((status, label))


# ── Helpers ────────────────────────────────────────────────────────────────────

def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def html_files(root: Path) -> list[Path]:
    """Return all HTML files under root, recursively, sorted."""
    return sorted(root.rglob("*.html"))


def parse_local_hrefs(text: str) -> list[str]:
    """
    Extract href values that are local file references.
    Skips: external URLs, bare anchors (#foo), mailto:.
    """
    all_hrefs = re.findall(r'href=["\']([^"\']+)["\']', text)
    local = []
    for h in all_hrefs:
        if not h:
            continue
        if h.startswith(("http://", "https://", "mailto:", "//")):
            continue
        if h.startswith("#"):
            continue
        local.append(h)
    return local


def resolve(href: str, from_file: Path) -> Path | None:
    """Resolve a local href relative to the HTML file containing it."""
    fragment_stripped = href.split("#")[0]
    if not fragment_stripped:
        return None
    return (from_file.parent / fragment_stripped).resolve()


def csv_columns(path: Path, encoding: str = "utf-8") -> set[str]:
    with path.open(newline="", encoding=encoding) as f:
        reader = csv.DictReader(f)
        row = next(reader, None)
        return set(row.keys()) if row else set()


# ── Individual checks ──────────────────────────────────────────────────────────

def check_docs_index() -> None:
    target = DOCS_DIR / "index.html"
    if target.exists():
        result("docs/index.html exists", "PASS")
    else:
        result("docs/index.html exists", "FAIL",
               ["Run build_site.py to regenerate docs/index.html"])


def check_nojekyll() -> None:
    target = DOCS_DIR / ".nojekyll"
    if target.exists():
        result("docs/.nojekyll exists", "PASS")
    else:
        result("docs/.nojekyll exists", "FAIL",
               ["Create an empty docs/.nojekyll to disable Jekyll processing on GitHub Pages"])


def check_products_csv_columns() -> None:
    if not PRODUCTS_CSV.exists():
        result("products.csv has required columns", "FAIL",
               [f"{PRODUCTS_CSV} not found"])
        return
    cols    = csv_columns(PRODUCTS_CSV)
    missing = REQUIRED_PRODUCTS_COLS - cols
    if not missing:
        result("products.csv has required columns", "PASS")
    else:
        result("products.csv has required columns", "FAIL",
               [f"Missing column(s): {', '.join(sorted(missing))}"])


def check_content_log_columns() -> None:
    if not CONTENT_LOG.exists():
        result("content_log.csv has required columns", "WARN",
               [f"{CONTENT_LOG} not found — create it to track posts"])
        return
    cols    = csv_columns(CONTENT_LOG)
    missing = REQUIRED_LOG_COLS - cols
    if not missing:
        result("content_log.csv has required columns", "PASS")
    else:
        result("content_log.csv has required columns", "FAIL",
               [f"Missing column(s): {', '.join(sorted(missing))}"])


def check_stylesheet() -> None:
    """Every HTML file must link to style-v2.css only. Any .css href that
    is not style-v2.css is flagged."""
    bad: list[str] = []
    for f in html_files(SITE_DIR):
        text = f.read_text(encoding="utf-8")
        css_hrefs = re.findall(r'href=["\']([^"\']*\.css[^"\']*)["\']', text)
        for href in css_hrefs:
            if REQUIRED_STYLESHEET not in href:
                bad.append(f"{f.relative_to(Path('.'))}  →  {href}")
    if not bad:
        result(f"All HTML files use {REQUIRED_STYLESHEET}", "PASS")
    else:
        result(f"All HTML files use {REQUIRED_STYLESHEET}", "FAIL", bad)


def check_affiliate_tags() -> None:
    """Every amazon.com link must contain the affiliate tag."""
    missing: list[str] = []
    for f in html_files(SITE_DIR):
        text  = f.read_text(encoding="utf-8")
        links = re.findall(r'https?://[^\s"\'<>]*amazon\.com[^\s"\'<>]*', text)
        for link in links:
            if AFFILIATE_TAG not in link:
                # Shorten for display
                short = link.replace("https://www.amazon.com/", "").replace("http://www.amazon.com/", "")
                missing.append(f"{f.relative_to(Path('.'))}  →  {short}")
    if not missing:
        result(f"All Amazon links include {AFFILIATE_TAG}", "PASS")
    else:
        result(f"All Amazon links include {AFFILIATE_TAG}", "FAIL", missing)


def check_local_links() -> None:
    """Every local href in every HTML file must resolve to an existing file."""
    broken: list[str] = []
    for f in html_files(SITE_DIR):
        text = f.read_text(encoding="utf-8")
        for href in parse_local_hrefs(text):
            target = resolve(href, f)
            if target is None:
                continue
            if not target.exists():
                broken.append(f"{f.relative_to(Path('.'))}  →  {href}")
    if not broken:
        result("No broken local links", "PASS")
    else:
        result("No broken local links", "FAIL", broken)


def check_sync() -> None:
    """
    Every HTML, CSS, and CSV file in site/ must exist in docs/ with identical content.
    Files in SYNC_ONLY_IN_DOCS and SYNC_IGNORE are excluded from comparison.
    """
    suffixes = {".html", ".css", ".csv"}

    site_rel = {
        p.relative_to(SITE_DIR)
        for p in SITE_DIR.rglob("*")
        if p.is_file()
        and p.suffix in suffixes
        and p.name not in SYNC_IGNORE
    }

    docs_rel = {
        p.relative_to(DOCS_DIR)
        for p in DOCS_DIR.rglob("*")
        if p.is_file()
        and p.suffix in suffixes
        and p.name not in SYNC_IGNORE
        and p.name not in SYNC_ONLY_IN_DOCS
    }

    only_site = site_rel - docs_rel
    only_docs = docs_rel - site_rel
    issues: list[str] = []

    for rel in sorted(only_site):
        issues.append(f"Only in site/ (missing from docs/): {rel}")
    for rel in sorted(only_docs):
        issues.append(f"Only in docs/ (missing from site/): {rel}")
    for rel in sorted(site_rel & docs_rel):
        if md5(SITE_DIR / rel) != md5(DOCS_DIR / rel):
            issues.append(f"Content differs: {rel}")

    # Legacy CSS files (.backup, style.css) present in both → note as WARN, not FAIL
    legacy_both: list[str] = []
    for name in ("style.css", "style.backup.css"):
        if (SITE_DIR / name).exists() and (DOCS_DIR / name).exists():
            legacy_both.append(f"Legacy file present in both site/ and docs/: {name}")

    if not issues and not legacy_both:
        result("site/ and docs/ are in sync", "PASS")
    elif issues:
        result("site/ and docs/ are in sync", "FAIL", issues)
    else:
        result("site/ and docs/ are in sync", "WARN",
               legacy_both + ["These files are unused — safe to delete"])


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Travel Now — Site Audit")
    print("─" * 52)

    check_docs_index()
    check_nojekyll()
    check_products_csv_columns()
    check_content_log_columns()
    check_stylesheet()
    check_affiliate_tags()
    check_local_links()
    check_sync()

    print("─" * 52)

    passed  = sum(1 for s, _ in _results if s == "PASS")
    warned  = sum(1 for s, _ in _results if s == "WARN")
    failed  = sum(1 for s, _ in _results if s == "FAIL")
    total   = len(_results)

    print(f"  {passed}/{total} passed    {warned} warning(s)    {failed} failure(s)")

    if failed > 0:
        print("\n  Fix FAIL items before deploying.")
        sys.exit(1)
    elif warned > 0:
        print("\n  No failures. Review warnings before next deploy.")
    else:
        print("\n  All checks passed. Safe to deploy.")


if __name__ == "__main__":
    main()
