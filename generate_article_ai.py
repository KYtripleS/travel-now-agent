#!/usr/bin/env python3
"""
generate_article_ai.py

Drafts a Travel Now article through four Gemini passes:

  1. Writer pass    — produces <METADATA> JSON + <ARTICLE> Markdown
  2. Image curator  — Pexels search for each [PHOTO: ...] placeholder,
                      replaces it with a credited <figure> block
  3. Critic pass    — reviews the draft against editorial rules
  4. Final pass     — integrates the critic's top fixes

Outputs land in content_drafts/ (gitignored):

  content_drafts/<slug>.final.md     ready-to-review Markdown
  content_drafts/<slug>.meta.json    title, description, FAQ, photo credits
  content_drafts/<slug>.review.md    full critic notes (transparency)

Usage:

  python generate_article_ai.py \\
    --slug south-korea-country-profile \\
    --title "South Korea: A Layered Country Profile for Thoughtful Travelers" \\
    --brief "Country profile — history, geography, politics, economy, society, travel prep." \\
    --category "Country profile"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from google import genai

REPO_ROOT   = Path(__file__).resolve().parent
PROMPTS_DIR = REPO_ROOT / "prompts"
DRAFTS_DIR  = REPO_ROOT / "content_drafts"
PEXELS_URL  = "https://api.pexels.com/v1/search"
DEFAULT_MODEL = "gemini-2.5-flash"

# Transient error tokens we treat as retryable
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


# ──────────────────────────────────────────────────────────────────────
# Gemini wrapper (with exponential backoff)
# ──────────────────────────────────────────────────────────────────────

def gemini_call(prompt: str, *, model: str, max_attempts: int = 4) -> str:
    """Call Gemini with retry on transient errors (429/5xx)."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY missing from .env")
    client = genai.Client(api_key=api_key)

    from google.genai import types
    config = types.GenerateContentConfig(max_output_tokens=32768)

    delays = [5, 15, 45]  # seconds between attempts 1→2, 2→3, 3→4
    last_err: Exception | None = None
    for attempt in range(max_attempts):
        try:
            response = client.models.generate_content(model=model, contents=prompt, config=config)
            return response.text or ""
        except Exception as e:
            last_err = e
            status = getattr(e, "code", None) or getattr(e, "status_code", None)
            if status not in RETRYABLE_STATUS or attempt == max_attempts - 1:
                raise
            delay = delays[min(attempt, len(delays) - 1)]
            print(f"      retry {attempt + 1}/{max_attempts - 1} after {delay}s (status {status})",
                  file=sys.stderr, flush=True)
            time.sleep(delay)
    # unreachable; the loop either returns or raises
    raise last_err if last_err else RuntimeError("gemini_call failed without an exception")


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def render(template: str, **subs: str) -> str:
    out = template
    for key, value in subs.items():
        out = out.replace(f"[[{key}]]", value)
    return out


# ──────────────────────────────────────────────────────────────────────
# Pass 1: writer
# ──────────────────────────────────────────────────────────────────────

META_RE    = re.compile(r"<METADATA>\s*(.*?)\s*</METADATA>", re.DOTALL)
# Article body runs from <ARTICLE> to </ARTICLE> OR end of text (handles
# Gemini truncating before the closing tag).
ARTICLE_RE = re.compile(r"<ARTICLE>\s*(.*?)(?:\s*</ARTICLE>|\Z)", re.DOTALL)


def strip_code_fence(text: str) -> str:
    """Drop a leading/trailing ``` fence if Gemini wrapped the whole reply."""
    t = text.strip()
    if t.startswith("```"):
        # remove first line up to and including newline
        t = t.split("\n", 1)[1] if "\n" in t else t[3:]
    if t.endswith("```"):
        t = t.rsplit("\n", 1)[0] if "\n" in t else t[:-3]
    return t.strip()


def writer_pass(*, slug: str, title: str, brief: str, category: str, model: str) -> tuple[dict, str]:
    prompt = render(
        load_prompt("article_writer.md"),
        TITLE=title, BRIEF=brief, CATEGORY=category, SLUG_HINT=slug,
    )
    text = strip_code_fence(gemini_call(prompt, model=model))

    meta_m = META_RE.search(text)
    if not meta_m:
        Path("/tmp/article_writer_raw.txt").write_text(text, encoding="utf-8")
        sys.exit("Writer output missing <METADATA> block; raw saved to /tmp/article_writer_raw.txt")
    art_m = ARTICLE_RE.search(text)
    if not art_m or not art_m.group(1).strip():
        Path("/tmp/article_writer_raw.txt").write_text(text, encoding="utf-8")
        sys.exit("Writer output missing <ARTICLE> body; raw saved to /tmp/article_writer_raw.txt")

    try:
        metadata = json.loads(meta_m.group(1))
    except json.JSONDecodeError as e:
        sys.exit(f"Writer metadata is not valid JSON: {e}")
    metadata.setdefault("slug", slug)
    return metadata, art_m.group(1).strip()


# ──────────────────────────────────────────────────────────────────────
# Pass 2: image curator (Pexels)
# ──────────────────────────────────────────────────────────────────────

PHOTO_RE = re.compile(r"\[PHOTO:\s*(?P<query>.*?)\]")


def pexels_photo(query: str) -> dict | None:
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        return None
    r = requests.get(
        PEXELS_URL,
        headers={"Authorization": api_key},
        params={"query": query, "orientation": "landscape", "per_page": 5, "size": "large"},
        timeout=30,
    )
    if r.status_code != 200:
        return None
    photos = (r.json() or {}).get("photos") or []
    if not photos:
        return None
    p = photos[0]
    src = p.get("src") or {}
    return {
        "url": src.get("large2x") or src.get("large") or src.get("original"),
        "photographer": p.get("photographer", "Unknown"),
        "photographer_url": p.get("photographer_url", "https://www.pexels.com/"),
        "pexels_url": p.get("url", "https://www.pexels.com/"),
        "query": query,
    }


def insert_photos(article_md: str) -> tuple[str, list[dict]]:
    credits: list[dict] = []

    def replacer(match: re.Match) -> str:
        query = match.group("query").strip()
        photo = pexels_photo(query)
        if not photo:
            return f"<!-- PHOTO MISSING (no Pexels result) for query: {query} -->"
        credits.append(photo)
        return (
            f'\n<figure class="article-photo">\n'
            f'  <img src="{photo["url"]}" alt="{query}" loading="lazy" />\n'
            f'  <figcaption>Photo by '
            f'<a href="{photo["photographer_url"]}" rel="noopener nofollow">{photo["photographer"]}</a> '
            f'on <a href="{photo["pexels_url"]}" rel="noopener nofollow">Pexels</a>'
            f'</figcaption>\n'
            f'</figure>\n'
        )

    enriched = PHOTO_RE.sub(replacer, article_md)
    return enriched, credits


# ──────────────────────────────────────────────────────────────────────
# Pass 3: critic
# ──────────────────────────────────────────────────────────────────────

def critic_pass(article_md: str, *, model: str) -> str:
    prompt = render(load_prompt("article_critic.md"), DRAFT=article_md)
    return gemini_call(prompt, model=model)


# ──────────────────────────────────────────────────────────────────────
# Pass 4: final integration
# ──────────────────────────────────────────────────────────────────────

FINAL_PROMPT = """\
You are Travel Now's senior editor. Apply the critic's **Top 3 fixes** to
the draft below. Preserve all <figure>...</figure> blocks exactly as-is
(do not change image URLs, captions, or credits). Preserve all
[AFFILIATE: ...] placeholders. Do not introduce any banned phrases.

Output only the revised Markdown article — no commentary, no delimiters.

# Draft

[[DRAFT]]

# Critic notes

[[CRITIQUE]]
"""


def final_pass(article_md: str, critique: str, *, model: str) -> str:
    prompt = render(FINAL_PROMPT, DRAFT=article_md, CRITIQUE=critique)
    return gemini_call(prompt, model=model)


# ──────────────────────────────────────────────────────────────────────
# Output
# ──────────────────────────────────────────────────────────────────────

def save_outputs(*, slug: str, metadata: dict, article_md: str, critique: str, credits: list[dict]) -> None:
    DRAFTS_DIR.mkdir(exist_ok=True)
    metadata["photo_credits"] = credits
    (DRAFTS_DIR / f"{slug}.final.md").write_text(article_md, encoding="utf-8")
    (DRAFTS_DIR / f"{slug}.meta.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (DRAFTS_DIR / f"{slug}.review.md").write_text(critique, encoding="utf-8")


# ──────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Draft a Travel Now article via Gemini + Pexels.")
    p.add_argument("--slug", required=True, help="kebab-case slug (filename + URL)")
    p.add_argument("--title", required=True, help="article title (H1)")
    p.add_argument("--brief", required=True, help="1-3 sentences on what the article should cover")
    p.add_argument("--category", default="Other", help="content category, e.g. 'Country profile'")
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"Gemini model id (default: {DEFAULT_MODEL})")
    return p.parse_args()


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    args = parse_args()

    print(f"[1/4] Writer pass ({args.model})…", flush=True)
    metadata, article_md = writer_pass(
        slug=args.slug, title=args.title, brief=args.brief,
        category=args.category, model=args.model,
    )

    print(f"[2/4] Image curator (Pexels)…", flush=True)
    article_md, credits = insert_photos(article_md)
    print(f"      embedded {len(credits)} photo(s)", flush=True)

    print(f"[3/4] Critic pass ({args.model})…", flush=True)
    critique = critic_pass(article_md, model=args.model)

    print(f"[4/4] Final integration pass ({args.model})…", flush=True)
    final_md = final_pass(article_md, critique, model=args.model)

    save_outputs(slug=args.slug, metadata=metadata, article_md=final_md,
                 critique=critique, credits=credits)

    print()
    print(f"  Draft:    content_drafts/{args.slug}.final.md")
    print(f"  Metadata: content_drafts/{args.slug}.meta.json")
    print(f"  Critique: content_drafts/{args.slug}.review.md")
    print()
    print("Review the draft. The HTML publish step is the next iteration —")
    print("we'll add it once you've eyeballed a sample.")


if __name__ == "__main__":
    main()
