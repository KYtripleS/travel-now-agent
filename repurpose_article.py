#!/usr/bin/env python3
"""
repurpose_article.py  —  Agent #3: article -> social/video repurposer

Reads a published Travel Now article and emits a ready-to-post bundle so
one piece of writing fuels Pinterest, X, short-form video, and YouTube
without rewriting anything by hand. No external API — it parses the HTML
we already publish.

Output: marketing/repurposed/<slug>.md  containing:
  * 3 fresh Pinterest pin descriptions (different angles) + board ideas
  * an X / Twitter thread (hook -> points -> CTA)
  * a 35-second short-video script (hook / beats / CTA, with on-screen text)
  * a YouTube / Shorts description + hashtags

Usage:
  python repurpose_article.py --slug airalo-vs-holafly-vs-saily
  python repurpose_article.py --path site/cities/tokyo/asakusa.html
  python repurpose_article.py --all          # every article in site/articles
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from bs4 import BeautifulSoup

REPO = Path(__file__).resolve().parent
SITE = REPO / "site"
OUT_DIR = REPO / "marketing" / "repurposed"

SKIP_HEADINGS = {
    "keep reading on travel now", "related", "related guides", "related reading",
    "related travel prep", "related articles", "references & sources",
    "references and sources", "sources & further reading", "where to go next on travel now",
    "liked this guide? get one like it, every week.", "get country profiles like this in your inbox.",
    "get city guides like this in your inbox.", "want guides like this in your inbox?",
}


def first_sentence(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    m = re.split(r"(?<=[.!?]) ", text)
    return m[0].strip() if m else text


def topic_of(title: str) -> str:
    """'How Much Cash Do You Need in Japan? A Guide for 2026' -> 'how much cash you need in japan'."""
    s = re.sub(r"\((\d{4})\)", "", title)
    s = re.split(r"[:?]", s)[0]
    s = re.sub(r"\bA Guide for \d{4}\b|\b\d{4}\b", "", s, flags=re.I)
    return re.sub(r"\s{2,}", " ", s).strip().rstrip(".").lower()


def best_sentence(text: str) -> str:
    """Prefer the sentence that carries a number/fact and fits a tweet."""
    text = clean_social(re.sub(r"\s+", " ", text).strip())
    sents = re.split(r"(?<=[.!?]) ", text)
    if not sents:
        return text
    def score(s):
        return (2 if re.search(r"[\d¥$%]", s) else 0) + (1 if len(s) <= 200 else -1)
    return max(sents, key=score).strip()


def clean_social(text: str) -> str:
    """Strip academic artifacts that read as noise on social: superscript
    footnote markers and parenthetical citations like (Wierzbicka, 1992)."""
    text = re.sub(r"[¹²³⁰⁴-⁹]+", "", text)
    text = re.sub(r"\s*\([A-Z][A-Za-zÀ-ſ]+(?:\s+(?:&|and|et al\.?)\s+[A-Z][A-Za-z]+)?,?\s+\d{4}[a-z]?(?:[;,]\s*[^)]*)?\)", "", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def extract(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.find("h1").get_text(strip=True) if soup.find("h1")
             else (soup.title.get_text(strip=True) if soup.title else "Travel Now guide"))
    canon = soup.find("link", rel="canonical")
    url = canon["href"] if canon and canon.has_attr("href") else ""
    desc_tag = soup.find("meta", attrs={"name": "description"})
    description = desc_tag["content"] if desc_tag and desc_tag.has_attr("content") else ""

    # sections: H2 -> first sentence of the following paragraph
    sections: list[tuple[str, str]] = []
    for h2 in soup.find_all("h2"):
        htext = h2.get_text(strip=True)
        if htext.lower() in SKIP_HEADINGS or not htext:
            continue
        paras = []
        sib = h2.find_next_sibling()
        while sib is not None and sib.name != "h2":
            if sib.name == "p":
                paras.append(sib.get_text(" ", strip=True))
            sib = sib.find_next_sibling()
        sections.append((htext, " ".join(paras)))

    # FAQ pairs
    faqs: list[tuple[str, str]] = []
    for det in soup.select("details"):
        s = det.find("summary")
        p = det.find("p")
        if s and p:
            faqs.append((s.get_text(strip=True), first_sentence(p.get_text(" ", strip=True))))

    lede = ""
    lede_tag = soup.find(class_="article-lede")
    if lede_tag:
        lede = first_sentence(lede_tag.get_text(" ", strip=True))

    return {"title": title, "url": url, "description": description,
            "sections": sections, "faqs": faqs, "lede": lede}


def hashtags(title: str) -> str:
    base = ["#TravelTips", "#TravelPrep", "#TravelHacks"]
    t = title.lower()
    if "esim" in t or "sim" in t or "wifi" in t:
        base += ["#eSIM", "#TravelTech"]
    if "insurance" in t:
        base += ["#TravelInsurance", "#DigitalNomad"]
    if "airport" in t or "security" in t or "carry" in t or "pack" in t:
        base += ["#PackingTips", "#CarryOn"]
    if "japan" in t or "tokyo" in t or "korea" in t or "vietnam" in t or "asia" in t:
        base += ["#Japan", "#AsiaTravel"]
    if "adapter" in t or "plug" in t or "power" in t:
        base += ["#TravelAdapter"]
    # de-dup, keep order, cap at 6
    seen, out = set(), []
    for h in base:
        if h.lower() not in seen:
            seen.add(h.lower()); out.append(h)
    return " ".join(out[:6])


def build_bundle(d: dict) -> str:
    title, url, desc = d["title"], d["url"], d["description"]
    secs = [s for s in d["sections"] if s[0]][:6]
    faqs = d["faqs"][:6]
    points = [h for h, _ in secs] or [q for q, _ in faqs]
    tags = hashtags(title)
    title_hook = re.sub(r"[.!?]+$", "", title).strip()
    L: list[str] = []

    L.append(f"# Repurpose bundle — {title}\n")
    L.append(f"Source: {url}\n")
    L.append("> Generated by `repurpose_article.py`. Copy-paste each block; tweak the voice "
             "to taste. Schedule, don't dump them all at once.\n")

    # ---- Pinterest ----
    L.append("\n## Pinterest — 3 fresh pin descriptions\n")
    angles = [
        ("Straight value", desc or (best_sentence(secs[0][1]) if secs else title)),
        ("Listicle hook", "Save this before your next trip — "
            + (", ".join(p.rstrip('.').lower() for p, _ in secs[:3]) if secs else "the essentials")
            + ". Full guide linked."),
        ("Question hook", f"{title_hook}? Here's the honest answer, "
            "with the details that actually change your decision. Read the full guide."),
    ]
    for i, (name, body) in enumerate(angles, 1):
        L.append(f"**Pin {i} — {name}**")
        L.append(f"- Title: {title}")
        L.append(f"- Description: {body}")
        L.append(f"- Link: {url}")
        L.append("")

    # ---- X thread (format researched 2026-07: links get a 30-50% reach penalty
    # so the URL goes in the FIRST REPLY; replies weigh 27-150x a like so the
    # closer is a question; each body tweet ends with a forward pull) ----
    L.append("\n## X / Twitter thread\n")
    body_pts = (secs or [(q, a) for q, a in faqs])[:6]
    n_pts = len(body_pts)
    num_match = re.search(r"(¥?[\d,]+(?:–|-)[\d,]+|\d+(?:\.\d+)?\s?(?:GB|ml|kg|%)|¥[\d,]+|\$\d+)", desc or "")
    L.append("**Pick ONE hook (delete the others):**")
    tpc = topic_of(title)
    L.append(f"- Number hook: {num_match.group(1) + ' — that number settles most of ' if num_match else str(n_pts) + ' things that decide '}"
             f"{tpc}. Thread: 🧵")
    L.append(f"- Contrarian hook: Most advice about {tpc} is either outdated or copied. "
             "Here's what actually holds up: 🧵")
    L.append(f"- Open-loop hook: I read every guide on {tpc} so you don't have to. "
             "The short version, in one thread: 🧵")
    L.append("")
    n = 2
    for i, (h, p) in enumerate(body_pts):
        point = best_sentence(p) if p else ""
        line = f"{h}" if not point else f"{h}: {point}"
        pull = ""
        if i < n_pts - 1:
            nxt = body_pts[i + 1][0]
            pull = f"\n(next: {clean_social(nxt).lower().rstrip('.')})"
        L.append(f"{n}/ {line}{pull}\n")
        n += 1
    L.append(f"{n}/ That's the short version. Bookmark it for your next trip — "
             "and tell me: what's the one thing you wish you'd known before yours?")
    L.append(f"\n**REPLY 1 (post immediately after the thread — the link lives HERE, "
             f"never in the thread):**\nFull guide, free, no signup: {url}\n{tags.split()[0] if tags else ''}")
    L.append("\n*Ops: post 8–10am or 7–9pm EST. Stay 30 min and reply to every comment — "
             "author replies are the single strongest ranking signal. Text only, no image needed.*")

    # ---- Short video ----
    L.append("\n## Short-form video script (~35s, Reels / TikTok / Shorts)\n")
    hook = title_hook
    L.append("| Time | On-screen text | Voiceover |")
    L.append("|---|---|---|")
    L.append(f"| 0–3s | {hook}? | \"If you're about to travel, save this.\" |")
    beats = (secs or [(q, a) for q, a in faqs])[:4]
    t0 = 3
    for h, p in beats:
        t1 = t0 + 7
        vo = best_sentence(p) if p else h
        L.append(f"| {t0}–{t1}s | {h} | \"{vo}\" |")
        t0 = t1
    L.append(f"| {t0}–{t0+4}s | Full guide → link in bio | \"The full guide's linked — it's free.\" |")
    L.append("\n*Shoot: text-on-screen over b-roll (airport, phone, packing). Caption the whole thing — most watch muted.*")

    # ---- YouTube ----
    L.append("\n## YouTube / Shorts description\n")
    L.append(f"{title}\n")
    L.append(f"{desc}\n")
    L.append(f"Full written guide: {url}\n")
    L.append(tags)

    return "\n".join(L) + "\n"


def repurpose_path(path: Path) -> Path:
    html = path.read_text(encoding="utf-8")
    d = extract(html)
    slug = path.stem if path.stem != "index" else path.parent.name
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{slug}.md"
    out.write_text(build_bundle(d), encoding="utf-8")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--slug", help="article slug in site/articles/")
    g.add_argument("--path", help="explicit path to an HTML file")
    g.add_argument("--all", action="store_true", help="every article in site/articles/")
    args = ap.parse_args()

    if args.all:
        paths = sorted((SITE / "articles").glob("*.html"))
    elif args.slug:
        paths = [SITE / "articles" / f"{args.slug}.html"]
    else:
        paths = [REPO / args.path]

    for p in paths:
        if not p.exists():
            print(f"  ⚠ missing: {p}")
            continue
        out = repurpose_path(p)
        print(f"  ✓ {p.name} -> {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
