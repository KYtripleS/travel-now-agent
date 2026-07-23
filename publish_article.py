#!/usr/bin/env python3
"""
publish_article.py

Convert a Gently Yonder article from content_drafts/{slug}.final.md and
{slug}.meta.json into a publish-ready HTML page in site/articles/
and docs/articles/, append the URL to sitemap.xml (both copies), and
run audit_site.py.

Does NOT commit. The caller (or AI) reviews, then runs git commands.

Usage:
  python publish_article.py --slug south-korea-country-profile
  python publish_article.py --slug X --category-label "Country profile"
  python publish_article.py --slug X --no-audit
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import markdown
from bs4 import BeautifulSoup

REPO_ROOT     = Path(__file__).resolve().parent
DRAFTS_DIR    = REPO_ROOT / "content_drafts"
SITE_DIR      = REPO_ROOT / "site"
DOCS_DIR      = REPO_ROOT / "docs"
SITEMAP_SITE  = SITE_DIR / "sitemap.xml"
SITEMAP_DOCS  = DOCS_DIR / "sitemap.xml"
TEMPLATE_PATH = SITE_DIR / "articles" / "esim-activation-and-preparation.html"
BASE_URL      = "https://gentlyyonder.com"


# ─────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────

def article_url(slug: str) -> str:
    return f"{BASE_URL}/articles/{slug}.html"


def today_iso() -> str:
    return date.today().isoformat()


def estimated_read_min(markdown_body: str) -> int:
    words = len(re.sub(r"<[^>]+>", " ", markdown_body).split())
    return max(2, round(words / 200))


def md_to_html(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["extra", "sane_lists", "smarty"],
        output_format="html5",
    )


def strip_outer_p(html: str) -> str:
    s = html.strip()
    if s.startswith("<p>") and s.endswith("</p>") and s.count("<p>") == 1:
        return s[3:-4]
    return s


# ─────────────────────────────────────────────────────────────────────
# Head metadata replacements (operate on a BeautifulSoup tree)
# ─────────────────────────────────────────────────────────────────────

def set_meta(soup: BeautifulSoup, *, attr: str, key: str, value: str) -> None:
    tag = soup.find("meta", attrs={attr: key})
    if tag is not None:
        tag["content"] = value


def set_jsonld_block(soup: BeautifulSoup, *, type_match: str, payload: dict) -> None:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        if data.get("@type") == type_match:
            script.string = json.dumps(payload, indent=2, ensure_ascii=False)
            return


def update_head(soup: BeautifulSoup, *, slug: str, meta: dict, label: str, body_md: str) -> None:
    title       = meta["title"]
    description = meta["description"]
    url         = article_url(slug)

    if soup.title is not None:
        soup.title.string = f"{title} | Gently Yonder"
    set_meta(soup, attr="name",     key="description", value=description)
    canonical = soup.find("link", attrs={"rel": "canonical"})
    if canonical is not None:
        canonical["href"] = url

    set_meta(soup, attr="property", key="og:title",       value=title)
    set_meta(soup, attr="property", key="og:description", value=description)
    set_meta(soup, attr="property", key="og:url",         value=url)

    set_meta(soup, attr="name",     key="twitter:title",       value=title)
    set_meta(soup, attr="name",     key="twitter:description", value=description)

    today_dt = f"{today_iso()}T09:00:00+09:00"
    set_meta(soup, attr="property", key="article:published_time", value=today_dt)
    set_meta(soup, attr="property", key="article:modified_time",  value=today_dt)

    set_jsonld_block(soup, type_match="Article", payload={
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "url": url,
        "datePublished": today_iso(),
        "dateModified": today_iso(),
        "author":    {"@type": "Organization", "name": "Gently Yonder", "url": f"{BASE_URL}/"},
        "publisher": {"@type": "Organization", "name": "Gently Yonder", "url": f"{BASE_URL}/"},
        "mainEntityOfPage": url,
        "articleSection": label,
        "inLanguage": "en",
    })

    faq = meta.get("faq") or []
    if faq:
        set_jsonld_block(soup, type_match="FAQPage", payload={
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": item["q"],
                 "acceptedAnswer": {"@type": "Answer", "text": item["a"]}}
                for item in faq
            ],
        })

    set_jsonld_block(soup, type_match="BreadcrumbList", payload={
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Gently Yonder", "item": f"{BASE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": "Guides",     "item": f"{BASE_URL}/#lists"},
            {"@type": "ListItem", "position": 3, "name": title},
        ],
    })


# ─────────────────────────────────────────────────────────────────────
# Body builders (breadcrumb, hero, main)
# ─────────────────────────────────────────────────────────────────────

def update_breadcrumb(soup: BeautifulSoup, *, title: str) -> None:
    ol = soup.select_one("nav.breadcrumb ol")
    if ol is None:
        return
    items = ol.find_all("li")
    if items:
        items[-1].clear()
        items[-1]["aria-current"] = "page"
        items[-1].append(title)


def update_hero(soup: BeautifulSoup, *, title: str, description: str, label: str, read_min: int) -> None:
    hero = soup.find("header", class_="hero article-hero")
    if hero is None:
        return
    for selector, value in (
        ("p.label", label),
        ("h1", title),
        ("p.subtitle", description),
        ("span.meta-date", f"Updated {today_iso()}"),
        ("span.meta-read", f"{read_min} min read"),
    ):
        tag = hero.select_one(selector)
        if tag is not None:
            tag.clear()
            tag.append(value)


def split_lede_and_body(body_md: str) -> tuple[str, str]:
    """Remove the leading H1 and split off the first paragraph for the lede."""
    body = re.sub(r"^#\s+.*?\n+", "", body_md.strip(), count=1)
    body = body.lstrip()
    para = re.match(r"(.*?)(?:\n\n|$)", body, re.DOTALL)
    if not para:
        return body, ""
    return para.group(1).strip(), body[para.end():].lstrip()


def build_main_inner(*, meta: dict, body_md: str) -> str:
    lede, rest = split_lede_and_body(body_md)
    lede_html = strip_outer_p(md_to_html(lede))
    body_html = md_to_html(rest)

    faq_blocks = []
    for item in meta.get("faq") or []:
        q = item["q"].replace("\n", " ")
        a = item["a"].replace("\n", " ")
        faq_blocks.append(
            f"        <details>\n          <summary>{q}</summary>\n          <p>{a}</p>\n        </details>"
        )
    faq_html = ""
    if faq_blocks:
        faq_html = (
            '\n      <h2 id="faq">Frequently asked questions</h2>\n'
            '      <div class="faq">\n'
            + "\n".join(faq_blocks)
            + "\n      </div>\n"
        )

    newsletter_html = (
        '\n      <section class="newsletter-cta" data-reveal>\n'
        '        <div class="newsletter-inner">\n'
        '          <span class="newsletter-label">The Weekly Travel Prep Brief</span>\n'
        '          <h2>Liked this guide? Get one like it, every week.</h2>\n'
        '          <p class="newsletter-desc">\n'
        '            Short, practical travel-prep emails. Country profiles, packing reminders, gear updates.\n'
        '            No spam, no influencer fluff. Subscribe and the printable Pre-Flight Checklist arrives as your welcome.\n'
        '          </p>\n'
        '          <button\n'
        '            data-tally-open="2EoDRA"\n'
        '            data-tally-emoji-text="✈️"\n'
        '            data-tally-emoji-animation="wave"\n'
        '            class="newsletter-btn">\n'
        '            Subscribe free →\n'
        '          </button>\n'
        '          <p class="newsletter-note">Free. The welcome checklist arrives instantly. Unsubscribe in one click, anytime.</p>\n'
        '        </div>\n'
        '      </section>\n'
    )

    back_link = '\n      <p class="back-link"><a href="../index.html">← Back to Gently Yonder</a></p>\n'

    return (
        f'\n      <p class="article-lede">{lede_html}</p>\n\n'
        f"      {body_html}\n"
        f"{faq_html}"
        f"{newsletter_html}"
        f"{back_link}"
    )


def update_main(soup: BeautifulSoup, *, meta: dict, body_md: str) -> None:
    section = soup.select_one("main section.article")
    if section is None:
        sys.exit("template has no <main><section class='article'> — abort")
    section.clear()
    inner = BeautifulSoup(build_main_inner(meta=meta, body_md=body_md), "html.parser")
    for child in list(inner.children):
        section.append(child)


# ─────────────────────────────────────────────────────────────────────
# Sitemap
# ─────────────────────────────────────────────────────────────────────

def update_sitemap(slug: str) -> None:
    url = article_url(slug)
    block = (
        f"  <url>\n"
        f"    <loc>{url}</loc>\n"
        f"    <changefreq>monthly</changefreq>\n"
        f"    <priority>0.7</priority>\n"
        f"  </url>"
    )
    for sitemap in (SITEMAP_SITE, SITEMAP_DOCS):
        text = sitemap.read_text(encoding="utf-8")
        if url in text:
            continue
        text = text.replace("</urlset>", f"{block}\n</urlset>")
        sitemap.write_text(text, encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────
# Audit
# ─────────────────────────────────────────────────────────────────────

def run_audit() -> int:
    print("\n— running audit_site.py —")
    res = subprocess.run(
        [sys.executable, "audit_site.py"],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
    )
    sys.stdout.write(res.stdout)
    sys.stderr.write(res.stderr)
    return res.returncode


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Publish a Gently Yonder article from content_drafts/.")
    p.add_argument("--slug", required=True)
    p.add_argument("--category-label", help="override hero <p class='label'>")
    p.add_argument("--no-sitemap", action="store_true")
    p.add_argument("--no-audit", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    md_path = DRAFTS_DIR / f"{args.slug}.final.md"
    meta_path = DRAFTS_DIR / f"{args.slug}.meta.json"
    if not md_path.exists() or not meta_path.exists():
        sys.exit(f"missing draft for {args.slug}: need {md_path} and {meta_path}")

    body_md = md_path.read_text(encoding="utf-8")
    meta    = json.loads(meta_path.read_text(encoding="utf-8"))
    label   = args.category_label or meta.get("category", "Travel")
    title   = meta["title"]
    desc    = meta["description"]

    template_html = TEMPLATE_PATH.read_text(encoding="utf-8")
    soup = BeautifulSoup(template_html, "html.parser")

    update_head(soup, slug=args.slug, meta=meta, label=label, body_md=body_md)
    update_breadcrumb(soup, title=title)
    update_hero(soup, title=title, description=desc, label=label,
                read_min=estimated_read_min(body_md))
    update_main(soup, meta=meta, body_md=body_md)

    html_out = str(soup)
    site_out = SITE_DIR / "articles" / f"{args.slug}.html"
    docs_out = DOCS_DIR / "articles" / f"{args.slug}.html"
    site_out.parent.mkdir(parents=True, exist_ok=True)
    docs_out.parent.mkdir(parents=True, exist_ok=True)
    site_out.write_text(html_out, encoding="utf-8")
    shutil.copy2(site_out, docs_out)
    print(f"wrote {site_out.relative_to(REPO_ROOT)}")
    print(f"wrote {docs_out.relative_to(REPO_ROOT)}")

    if not args.no_sitemap:
        update_sitemap(args.slug)
        print(f"sitemap.xml updated with {article_url(args.slug)}")

    # Self-updating homepage hero counts (travel guides / destinations / tools).
    try:
        import build_library
        c = build_library.inventory()
        build_library.update_hero(c)
        print(f"hero counts refreshed — {c['guides']} guides, "
              f"{c['destinations']} destinations, {c['tools']} tools")
    except Exception as exc:  # never block a publish on the counter
        print(f"  (hero count refresh skipped: {exc})")

    # Every practical article auto-gets an affiliate CTA (registry entry or default);
    # trust/cultural essays are safelisted out. Standing rule: monetise every guide.
    try:
        import inject_tp
        blk = inject_tp.block_for(args.slug)
        if blk:
            inject_tp.inject(f"articles/{args.slug}.html", blk)
            print("affiliate CTA injected")
        else:
            print("  (affiliate CTA skipped — trust/cultural article)")
    except Exception as exc:
        print(f"  (affiliate inject skipped: {exc})")

    if not args.no_audit:
        rc = run_audit()
        if rc != 0:
            sys.exit(f"audit_site.py exited {rc} — review before committing")


if __name__ == "__main__":
    main()
