#!/usr/bin/env python3
"""Per-page social cards: og:image and a large Twitter/X card.

Every article used to share one generic card (images/travel-now-og.png), so a
link to the DMZ guide looked exactly like a link to the packing guide when
shared on X, LINE or Facebook, and articles asked X for the small "summary"
card. Each article now uses its own first photograph:

  · Pexels photos: the same photo, cropped by Pexels to 1200x630
  · our own photos (images/photos/): cropped here to 1.91:1 from the full
    original embedded in the pin SVG, written to images/og/<name>.jpg

Pages without a photo keep the site card. Pages that had no Open Graph tags at
all (About, Tools, the plug pages...) get the basics from their <title>, meta
description and canonical link; tags a page already has are left as they are.

Idempotent, and it edits only these meta tags. The publisher calls apply()
through add_aeo.apply(); page builders call apply_text() on what they write.

    python add_social_meta.py            # dry run
    python add_social_meta.py --write
"""
from __future__ import annotations

import argparse
import base64
import io
import re
from pathlib import Path

from bs4 import BeautifulSoup
from PIL import Image

REPO = Path(__file__).resolve().parent
BASE = "https://gentlyyonder.com"
DEFAULT = (f"{BASE}/images/travel-now-og.png", 1200, 630)
OG_DIR = "images/og"
RATIO = 1200 / 630
VERTICAL_BIAS = 0.42          # same as extract_photo.py: skylines sit high
SITE_SUFFIX = re.compile(r"\s*[|—–-]\s*Gently Yonder\s*$")


def _og_from_pin(name: str) -> tuple[str, int, int] | None:
    """Crop the full-size original out of site/images/pinterest/<name>.svg."""
    out_rel = f"{OG_DIR}/{name}.jpg"
    if all((REPO / base / out_rel).exists() for base in ("site", "docs")):
        w, h = Image.open(REPO / "site" / out_rel).size
        return f"{BASE}/{out_rel}", w, h
    svg = REPO / "site" / "images" / "pinterest" / f"{name}.svg"
    if not svg.exists():
        return None
    m = re.search(r'xlink:href="data:image/\w+;base64,([^"]+)"', svg.read_text(encoding="utf-8"))
    if not m:
        return None
    im = Image.open(io.BytesIO(base64.b64decode(m.group(1)))).convert("RGB")
    w, h = im.size
    ch = min(h, int(w / RATIO))
    top = int((h - ch) * VERTICAL_BIAS)
    im = im.crop((0, top, w, top + ch))
    if im.width > 1200:
        im = im.resize((1200, round(1200 / RATIO)), Image.LANCZOS)
    for base in ("site", "docs"):
        (REPO / base / OG_DIR).mkdir(parents=True, exist_ok=True)
        im.save(REPO / base / out_rel, "JPEG", quality=84, optimize=True, progressive=True)
    return f"{BASE}/{out_rel}", im.width, im.height


def image_for(soup: BeautifulSoup) -> tuple[str, int, int]:
    img = soup.select_one("section.article figure img, main figure img")
    src = (img.get("src") or "") if img else ""
    if "images.pexels.com" in src:
        return src.split("?")[0] + "?auto=compress&cs=tinysrgb&w=1200&h=630&fit=crop", 1200, 630
    m = re.search(r"images/photos/([a-z0-9-]+)\.webp", src)
    if m:
        got = _og_from_pin(m.group(1))
        if got:
            return got
    return DEFAULT


def _find(soup: BeautifulSoup, attr: str, key: str):
    return soup.find("meta", attrs={attr: key})


def _basics(soup: BeautifulSoup) -> tuple[str | None, str | None, str | None]:
    title = soup.title.get_text(strip=True) if soup.title else None
    if title:
        title = SITE_SUFFIX.sub("", title)
    desc_tag = _find(soup, "name", "description")
    desc = desc_tag.get("content") if desc_tag else None
    canon = soup.find("link", rel="canonical")
    url = canon.get("href") if canon else None
    return title, desc, url


def plan(soup: BeautifulSoup) -> tuple[list[tuple[str, str, str, bool]], list[str]]:
    """What the page's head should carry: (attr, key, value, overwrite) tags,
    and og: keys to drop. overwrite=False only fills a tag that is missing."""
    title, desc, url = _basics(soup)
    is_article = soup.select_one("section.article") is not None
    img, w, h = image_for(soup)
    h1 = soup.find("h1")
    alt = " ".join(h1.get_text(" ", strip=True).split()) if h1 else (title or "Gently Yonder")
    tags = [
        ("property", "og:type", "article" if is_article else "website", False),
        ("property", "og:title", title, False),
        ("property", "og:description", desc, False),
        ("property", "og:url", url, False),
        ("property", "og:site_name", "Gently Yonder", False),
        ("name", "twitter:title", title, False),
        ("name", "twitter:description", desc, False),
        ("name", "twitter:site", "@TripWorldAdvice", False),
        ("property", "og:image", img, True),
        ("property", "og:image:width", str(w), True),
        ("property", "og:image:height", str(h), True),
        ("property", "og:image:alt", alt, True),
        ("name", "twitter:card", "summary_large_image", True),
        ("name", "twitter:image", img, True),
        ("name", "twitter:image:alt", alt, True),
    ]
    # the homepage declares the PNG's type and https URL; only true for the PNG
    drop = [] if img == DEFAULT[0] else ["og:image:type", "og:image:secure_url"]
    return [t for t in tags if t[2]], drop


def apply(soup: BeautifulSoup) -> None:
    """Apply to a parsed page (the publisher's path, via add_aeo.apply)."""
    if soup.head is None:
        return
    tags, drop = plan(soup)
    for attr, key, value, overwrite in tags:
        tag = _find(soup, attr, key)
        if tag is None:
            tag = soup.new_tag("meta", attrs={attr: key})
            soup.head.append(tag)
        elif not overwrite:
            continue
        tag["content"] = value
    for key in drop:
        tag = _find(soup, "property", key)
        if tag is not None:
            tag.decompose()


def _meta_re(attr: str, key: str) -> re.Pattern:
    return re.compile(rf'<meta\b(?=[^>]*\b{attr}="{re.escape(key)}")[^>]*>\n?', re.I)


def _tag_html(attr: str, key: str, value: str) -> str:
    # parser-canonical, like every other managed block on the site
    return str(BeautifulSoup("", "html.parser").new_tag("meta", attrs={"content": value, attr: key}))


def apply_text(html: str) -> str:
    """Apply to page text, editing only these meta tags. Page builders
    (build_library, build_gear_page) call this on what they write, so the
    rest of the page keeps its own formatting and nothing ping-pongs."""
    soup = BeautifulSoup(html, "html.parser")
    if soup.head is None or "</head>" not in html:
        return html
    tags, drop = plan(soup)
    missing = []
    for attr, key, value, overwrite in tags:
        m = _meta_re(attr, key).search(html)
        if m is None:
            missing.append(_tag_html(attr, key, value))
            continue
        current = BeautifulSoup(m.group(0), "html.parser").meta.get("content")
        if overwrite and current != value:
            html = html[:m.start()] + _tag_html(attr, key, value) + ("\n" if m.group(0).endswith("\n") else "") + html[m.end():]
    for key in drop:
        html = _meta_re("property", key).sub("", html)
    if missing:
        at = html.index("</head>")
        html = html[:at] + "".join(missing) + html[at:]
    return html


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    changed = own = total = 0
    for src in sorted((REPO / "site").rglob("*.html")):
        rel = src.relative_to(REPO / "site")
        if rel.parts[0] == "go" or src.name.startswith("googlee"):
            continue
        html = src.read_text(encoding="utf-8")
        if "</head>" not in html:
            continue
        new = apply_text(html)
        total += 1
        if f'content="{DEFAULT[0]}" property="og:image"' not in new:
            own += 1
        if new != html:
            changed += 1
            if args.write:
                src.write_text(new, encoding="utf-8")
                (REPO / "docs" / rel).write_text(new, encoding="utf-8")
    print(f"pages: {total}   changed: {changed}   with their own photo card: {own}"
          + ("" if args.write else "   (dry run)"))


if __name__ == "__main__":
    main()
