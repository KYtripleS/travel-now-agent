#!/usr/bin/env python3
"""Add meta description to every article that lacks one, derived from its title and first paragraph."""
import re
from pathlib import Path

ARTICLES = Path("site/articles")

def strip_tags(html: str) -> str:
    """Remove HTML tags for plain-text extraction."""
    return re.sub(r"<[^>]+>", " ", html)

def extract_title(content: str) -> str:
    m = re.search(r"<title>(.+?)</title>", content, re.S)
    return m.group(1).strip() if m else ""

def extract_first_para(content: str) -> str:
    """First <p> after the hero header, or first <p> in the article."""
    m = re.search(r"<main[^>]*>.*?<p[^>]*>(.+?)</p>", content, re.S)
    if not m:
        m = re.search(r"<p[^>]*>(.+?)</p>", content, re.S)
    return strip_tags(m.group(1)).strip() if m else ""

def build_description(title: str, first_para: str) -> str:
    """Compose a 150-155 char meta description."""
    # Prefer the title (it already contains the key phrase) + a short tail
    base = title.replace(" | Gently Yonder", "").strip()
    if len(base) <= 120:
        tail = first_para[:80].strip()
        desc = f"{base}. {tail}"
    else:
        desc = base[:150]
    # Hard cap at 155
    if len(desc) > 155:
        desc = desc[:152] + "..."
    return desc

def main():
    fixed = 0
    for f in sorted(ARTICLES.glob("*.html")):
        content = f.read_text(encoding="utf-8")
        # Skip any page that already has a description, whatever the attribute order:
        # the publisher writes <meta content=".." name="description"/>, and missing it
        # here once gave 177 pages a second, truncated description.
        if re.search(r'<meta\b(?=[^>]*\bname=["\']description["\'])', content):
            continue
        title = extract_title(content)
        if not title:
            print(f"SKIP (no title): {f.name}")
            continue
        para = extract_first_para(content)
        desc = build_description(title, para)
        # Insert after <title> block, before <link rel="stylesheet"
        pattern = r'(<title>.+?</title>\s*)'
        replacement = r'\1<meta name="description" content="' + desc.replace('"', '&quot;') + '" />\n'
        new_content = re.sub(pattern, replacement, content, count=1)
        if new_content == content:
            print(f"FAIL (no insertion point): {f.name}")
            continue
        f.write_text(new_content, encoding="utf-8")
        # Mirror to docs/
        docs_path = Path("docs/articles") / f.name
        docs_path.write_text(new_content, encoding="utf-8")
        fixed += 1
        print(f"OK {f.name}  ({len(desc)} chars)")

    print(f"\nAdded meta description to {fixed} articles.")

if __name__ == "__main__":
    main()
