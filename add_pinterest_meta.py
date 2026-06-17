#!/usr/bin/env python3
"""
add_pinterest_meta.py — Inject Pinterest Rich Pin meta tags into all article and
country/city pages. Idempotent — safe to re-run.

For each page it injects (right before </head>):
- <meta property="article:published_time" content="<datePublished from JSON-LD>" />
- <meta property="article:modified_time"  content="<dateModified from JSON-LD>" />
- <meta property="article:author"         content="Travel Now" />
- <meta property="og:image"               content="<fallback OG image>" /> (if missing)

These are the required fields for Pinterest "Article Rich Pins". Once the
domain is verified on Pinterest, every pin from this site that links to one of
these pages will automatically render as a Rich Pin (title + description +
author + bold typography) instead of a plain pin.

Usage:
    python add_pinterest_meta.py             # inject across site/ and docs/
    python add_pinterest_meta.py --check     # report which pages have which tags
"""

from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SCAN_DIRS = [ROOT / "site", ROOT / "docs"]

START = "<!-- BEGIN Pinterest Rich Pin meta (managed by add_pinterest_meta.py) -->"
END = "<!-- END Pinterest Rich Pin meta -->"
BLOCK_RE = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"\s*", re.DOTALL)

FALLBACK_OG_IMAGE = "https://kytriples.github.io/travel-now-agent/images/travel-now-og.png"

# Files we want Article Rich Pins on. Excludes index.html, about.html, etc.
def is_article_like(path: Path) -> bool:
    parts = path.parts
    name = path.name
    if "articles" in parts:
        return True
    if "countries" in parts and name == "index.html":
        return True
    if "cities" in parts:  # includes index.html and asakusa.html
        return True
    return False


def extract_dates(text: str) -> tuple[str | None, str | None]:
    pub = re.search(r'"datePublished"\s*:\s*"([0-9T:\-+Z.]+)"', text)
    mod = re.search(r'"dateModified"\s*:\s*"([0-9T:\-+Z.]+)"', text)
    return (pub.group(1) if pub else None, mod.group(1) if mod else None)


def has_og_image(text: str) -> bool:
    return bool(re.search(r'<meta\s+property=["\']og:image["\']', text))


def build_block(pub: str, mod: str, need_image: bool) -> str:
    lines = [START]
    lines.append(f'<meta property="article:published_time" content="{pub}" />')
    lines.append(f'<meta property="article:modified_time"  content="{mod}" />')
    lines.append('<meta property="article:author"         content="Travel Now" />')
    lines.append('<meta property="article:section"        content="Travel" />')
    if need_image:
        lines.append(f'<meta property="og:image"               content="{FALLBACK_OG_IMAGE}" />')
        lines.append('<meta property="og:image:width"         content="1200" />')
        lines.append('<meta property="og:image:height"        content="630" />')
    lines.append(END)
    return "\n".join(lines) + "\n"


def files_to_process():
    for d in SCAN_DIRS:
        if not d.exists():
            continue
        for p in d.rglob("*.html"):
            if is_article_like(p):
                yield p


def inject():
    added = updated = skipped = 0
    for p in files_to_process():
        text = p.read_text()
        pub, mod = extract_dates(text)
        if not pub:
            print(f"  ⚠️  {p.relative_to(ROOT)} — no datePublished, skipped")
            skipped += 1
            continue
        if not mod:
            mod = pub
        # normalize to YYYY-MM-DDT00:00:00+00:00 if just a date
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", pub):
            pub_iso = f"{pub}T09:00:00+09:00"
        else:
            pub_iso = pub
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", mod):
            mod_iso = f"{mod}T09:00:00+09:00"
        else:
            mod_iso = mod
        need_image = not has_og_image(text)
        block = build_block(pub_iso, mod_iso, need_image)
        if START in text:
            new_text = BLOCK_RE.sub(block, text)
            if new_text != text:
                p.write_text(new_text)
                updated += 1
                print(f"  🔁 {p.relative_to(ROOT)} (updated)")
        else:
            if "</head>" not in text:
                print(f"  ⚠️  {p.relative_to(ROOT)} — no </head>, skipped")
                skipped += 1
                continue
            new_text = text.replace("</head>", f"  {block}</head>", 1)
            p.write_text(new_text)
            added += 1
            print(f"  ✅ {p.relative_to(ROOT)} (added)")
    print(f"\n✅ Pinterest meta: {added} added, {updated} updated, {skipped} skipped")


def check():
    for p in files_to_process():
        text = p.read_text()
        has_pub = "article:published_time" in text
        has_img = has_og_image(text)
        mark = "✅" if has_pub and has_img else "❌"
        print(f"  {mark} {p.relative_to(ROOT)} — pub={has_pub} img={has_img}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        check()
    else:
        inject()


if __name__ == "__main__":
    main()
