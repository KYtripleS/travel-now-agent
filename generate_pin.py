#!/usr/bin/env python3
"""
Generate a Travel Now Pinterest pin (1000x1500 PNG) with a photo background.

Two photo sources:
  1. --photo /path/to/local.jpg    (no API needed; great for testing)
  2. --pexels-query "Kyoto temple" (requires PEXELS_API_KEY in .env)

Output: writes SVG + PNG to both site/images/pinterest/ and docs/images/pinterest/.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

import requests
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent
TEMPLATE = REPO_ROOT / "site" / "images" / "pinterest" / "_template-photo.svg"
SITE_DIR = REPO_ROOT / "site" / "images" / "pinterest"
DOCS_DIR = REPO_ROOT / "docs" / "images" / "pinterest"

PEXELS_SEARCH = "https://api.pexels.com/v1/search"


def fit_title_size(title: str) -> int:
    n = len(title)
    if n <= 5:
        return 200
    if n <= 7:
        return 170
    if n <= 9:
        return 140
    if n <= 12:
        return 115
    return 95


def pexels_search(query: str, api_key: str) -> str:
    """Search Pexels and return the URL of the best portrait photo."""
    r = requests.get(
        PEXELS_SEARCH,
        headers={"Authorization": api_key},
        params={"query": query, "orientation": "portrait", "per_page": 15, "size": "large"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    photos = data.get("photos") or []
    if not photos:
        raise RuntimeError(f"Pexels returned no photos for query: {query!r}")
    # Prefer "large2x" (~1880px tall) for crisp 1500-tall downscale.
    src = photos[0]["src"]
    return src.get("large2x") or src.get("large") or src.get("original")


def download_photo(url: str, dest: Path) -> None:
    r = requests.get(url, timeout=60, stream=True)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)


def encode_data_uri(jpg_path: Path) -> str:
    mime = "image/jpeg"
    if jpg_path.suffix.lower() == ".png":
        mime = "image/png"
    b64 = base64.b64encode(jpg_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def fill_template(
    *,
    photo_href: str,
    title: str,
    tagline: str,
    bullets: list[str],
    cta: str,
    url_hint: str,
) -> str:
    if len(bullets) != 4:
        raise ValueError("exactly 4 bullets required")
    svg = TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "{{PHOTO_HREF}}": photo_href,
        "{{TITLE_SIZE}}": str(fit_title_size(title)),
        "{{TITLE}}": xml_escape(title),
        "{{TAGLINE}}": xml_escape(tagline),
        "{{BULLET1}}": xml_escape(bullets[0]),
        "{{BULLET2}}": xml_escape(bullets[1]),
        "{{BULLET3}}": xml_escape(bullets[2]),
        "{{BULLET4}}": xml_escape(bullets[3]),
        "{{CTA}}": xml_escape(cta),
        "{{URL_HINT}}": xml_escape(url_hint),
    }
    for k, v in replacements.items():
        svg = svg.replace(k, v)
    return svg


def render_png(svg_path: Path, png_path: Path) -> None:
    subprocess.run(
        ["rsvg-convert", "-w", "1000", "-h", "1500", str(svg_path), "-o", str(png_path)],
        check=True,
    )


def resolve_photo_href(args, work_dir: Path) -> str:
    if args.photo:
        local = Path(args.photo).expanduser().resolve()
        if not local.exists():
            sys.exit(f"--photo file not found: {local}")
        return encode_data_uri(local)

    if args.pexels_query:
        load_dotenv(REPO_ROOT / ".env")
        api_key = os.getenv("PEXELS_API_KEY")
        if not api_key:
            sys.exit(
                "PEXELS_API_KEY missing from .env. Register at https://www.pexels.com/api/ "
                "(free) and add: PEXELS_API_KEY=your_key"
            )
        url = pexels_search(args.pexels_query, api_key)
        tmp_jpg = work_dir / "pexels.jpg"
        download_photo(url, tmp_jpg)
        return encode_data_uri(tmp_jpg)

    sys.exit("must pass either --photo /path/to.jpg or --pexels-query 'search terms'")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate a Travel Now Pinterest pin.")
    p.add_argument("--slug", required=True, help="filename slug, e.g. 'japan-photo'")
    p.add_argument("--title", required=True, help="big title, e.g. 'JAPAN'")
    p.add_argument("--tagline", required=True, help="italic subtitle")
    p.add_argument("--bullet1", required=True)
    p.add_argument("--bullet2", required=True)
    p.add_argument("--bullet3", required=True)
    p.add_argument("--bullet4", required=True)
    p.add_argument("--cta", default="Read the full profile →")
    p.add_argument("--url-hint", required=True, help="e.g. 'travelnow • countries/japan'")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--photo", help="local image path (skip Pexels)")
    src.add_argument("--pexels-query", help="Pexels search query (uses PEXELS_API_KEY)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        work_dir = Path(td)
        photo_href = resolve_photo_href(args, work_dir)

        svg = fill_template(
            photo_href=photo_href,
            title=args.title,
            tagline=args.tagline,
            bullets=[args.bullet1, args.bullet2, args.bullet3, args.bullet4],
            cta=args.cta,
            url_hint=args.url_hint,
        )

        svg_path = SITE_DIR / f"{args.slug}.svg"
        png_path = SITE_DIR / f"{args.slug}.png"
        svg_path.write_text(svg, encoding="utf-8")
        render_png(svg_path, png_path)

        shutil.copy2(svg_path, DOCS_DIR / svg_path.name)
        shutil.copy2(png_path, DOCS_DIR / png_path.name)

    print(f"wrote {svg_path.relative_to(REPO_ROOT)}")
    print(f"wrote {png_path.relative_to(REPO_ROOT)}")
    print(f"mirrored to {DOCS_DIR.relative_to(REPO_ROOT)}/")


if __name__ == "__main__":
    main()
