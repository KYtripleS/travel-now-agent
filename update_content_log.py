#!/usr/bin/env python3
"""
update_content_log.py

Scans note_drafts/, rendered_videos/, and video_scripts/ and safely
appends new rows to data/monetization_log.csv.

Deduplicates by (date, platform, file_path) — existing rows are never
overwritten. Revenue columns (clicks, likes, sales, revenue_yen) are left
at 0 and must be updated manually after each publish.

Usage:
  python update_content_log.py           # dry run — preview rows to add
  python update_content_log.py --write   # append new rows to CSV
"""

import csv
import re
import sys
from datetime import date
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────

MONO_LOG          = Path("data/monetization_log.csv")
NOTE_DRAFTS_DIR   = Path("note_drafts")
VIDEO_DIR         = Path("rendered_videos")
SCRIPTS_DIR       = Path("video_scripts")
THREADS_DRAFTS_DIR = Path("threads_drafts")

COLUMNS = [
    "date", "platform", "content_type", "title",
    "file_path", "url", "status", "price",
    "clicks", "likes", "sales", "revenue_yen", "notes",
]

_SKIP_FILES         = {"README.md", "TODAY_POSTING_GUIDE.md"}
_SKIP_THREADS_FILES = {"README.md"}


# ── Helpers ─────────────────────────────────────────────────────────────────

def _parse_frontmatter(path: Path) -> dict:
    """Extract key: value pairs from an HTML comment frontmatter block
    and the first # heading as '_title'."""
    text = path.read_text(encoding="utf-8")
    meta: dict = {}

    m = re.search(r"<!--(.*?)-->", text, re.DOTALL)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            meta["_title"] = line[2:].strip()
            break

    return meta


def _date_from_filename(name: str, fallback: str) -> str:
    m = re.match(r"(\d{4}-\d{2}-\d{2})", name)
    return m.group(1) if m else fallback


def _video_title(path: Path) -> str:
    stem = path.stem
    stem = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", stem)
    return stem.replace("-", " ").title()


# ── Scanners ────────────────────────────────────────────────────────────────

def scan_note_drafts() -> list:
    rows = []
    if not NOTE_DRAFTS_DIR.exists():
        return rows

    for p in sorted(NOTE_DRAFTS_DIR.glob("*.md")):
        if p.name in _SKIP_FILES:
            continue

        meta  = _parse_frontmatter(p)
        ntype = meta.get("type", "").lower()
        if ntype not in ("free", "paid"):
            continue

        content_type = "paid_article" if ntype == "paid" else "free_article"
        price_val    = "300"          if ntype == "paid" else "0"
        title        = meta.get("_title", p.stem)
        series       = meta.get("series", "").strip()
        row_date     = _date_from_filename(p.name, date.today().isoformat())

        rows.append({
            "date":         row_date,
            "platform":     "note",
            "content_type": content_type,
            "title":        title,
            "file_path":    str(p),
            "url":          "",
            "status":       "draft",
            "price":        price_val,
            "clicks":       "0",
            "likes":        "0",
            "sales":        "0",
            "revenue_yen":  "0",
            "notes":        series,
        })

    return rows


def scan_videos() -> list:
    rows = []
    if not VIDEO_DIR.exists():
        return rows

    for p in sorted(VIDEO_DIR.glob("*.mp4")):
        row_date = _date_from_filename(p.name, date.today().isoformat())

        # Find matching video_scripts posting_kit
        slug  = re.sub(r"\.mp4$", "", p.name)
        slug  = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", slug)
        kits  = sorted(SCRIPTS_DIR.glob(f"*{slug}*/posting_kit.md"))
        kit_note = f"posting_kit: {kits[0]}" if kits else ""

        rows.append({
            "date":         row_date,
            "platform":     "YouTube Shorts / Reels / TikTok",
            "content_type": "short_video",
            "title":        _video_title(p),
            "file_path":    str(p),
            "url":          "",
            "status":       "ready",
            "price":        "0",
            "clicks":       "0",
            "likes":        "0",
            "sales":        "0",
            "revenue_yen":  "0",
            "notes":        kit_note,
        })

    return rows


def scan_threads_drafts() -> list:
    """Scan threads_drafts/ and return one log row per .md file."""
    rows = []
    if not THREADS_DRAFTS_DIR.exists():
        return rows

    for p in sorted(THREADS_DRAFTS_DIR.glob("*.md")):
        if p.name in _SKIP_THREADS_FILES:
            continue

        row_date = _date_from_filename(p.name, date.today().isoformat())

        # Infer mode from filename: YYYY-MM-DD-{mode}.md
        stem_no_date = re.sub(r"^\d{4}-\d{2}-\d{2}-?", "", p.stem)
        mode         = stem_no_date.replace("-", "_") or "unknown"

        # Content type label
        if mode == "japanese_ai_media":
            content_label = "threads_jp"
            platform_note = "会社員、AIでメディアを作る。"
        elif mode == "travel_now":
            content_label = "threads_en"
            platform_note = "Travel Now"
        else:
            content_label = "threads_post"
            platform_note = mode

        rows.append({
            "date":         row_date,
            "platform":     "Threads",
            "content_type": content_label,
            "title":        f"Threads drafts — {mode} — {row_date}",
            "file_path":    str(p),
            "url":          "",
            "status":       "draft",
            "price":        "0",
            "clicks":       "0",
            "likes":        "0",
            "sales":        "0",
            "revenue_yen":  "0",
            "notes":        platform_note,
        })

    return rows


# ── Deduplication ────────────────────────────────────────────────────────────

def load_existing_keys() -> set:
    """Return a set of (date, platform, file_path) tuples for rows already in the log."""
    if not MONO_LOG.exists():
        return set()
    with MONO_LOG.open(newline="", encoding="utf-8") as f:
        return {
            (r.get("date", ""), r.get("platform", ""), r.get("file_path", ""))
            for r in csv.DictReader(f)
        }


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    write_mode = "--write" in sys.argv

    all_rows  = scan_note_drafts() + scan_videos() + scan_threads_drafts()
    existing  = load_existing_keys()
    to_add    = [
        r for r in all_rows
        if (r["date"], r["platform"], r["file_path"]) not in existing
    ]

    print("=" * 56)
    print("=== UPDATE MONETIZATION LOG                         ===")
    print("=" * 56)

    if not to_add:
        print("\n  data/monetization_log.csv — no new rows to add. ✓")
        print("=" * 56)
        return

    print(f"\n  {'Writing' if write_mode else 'Dry run'} — {len(to_add)} new row(s):\n")
    for r in to_add:
        label = f"[{r['content_type']:>14}]"
        price = f"  ¥{r['price']}" if r["price"] != "0" else ""
        print(f"  {label}  {r['date']}  {r['platform'][:30]:<30}  {r['title'][:48]}{price}")

    if not write_mode:
        print("\n  Run with --write to append these rows to data/monetization_log.csv")
        print("=" * 56)
        return

    needs_header = not MONO_LOG.exists() or MONO_LOG.stat().st_size == 0
    MONO_LOG.parent.mkdir(parents=True, exist_ok=True)

    with MONO_LOG.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        if needs_header:
            writer.writeheader()
        writer.writerows(to_add)

    print(f"\n  ✓  {len(to_add)} row(s) appended → {MONO_LOG}")
    print("=" * 56)


if __name__ == "__main__":
    main()
