#!/usr/bin/env python3
"""
generate_video_scripts.py — Short-form video script generator for Travel Now.

Turns existing Markdown drafts from content_drafts/ or note_drafts/ into
platform-specific short-form video scripts for YouTube Shorts, Instagram Reels,
and TikTok.

IMPORTANT:
  - This script generates text scripts ONLY.
  - It never posts automatically.
  - It does not use YouTube, TikTok, Instagram, or Meta APIs.
  - It does not use video generation APIs.
  - All scripts require human review before use.

Outputs per run (saved to video_scripts/YYYY-MM-DD-{slug}/):
  scripts.md          — YouTube Shorts, Instagram Reels, TikTok scripts
  production_notes.md — Voiceover script, on-screen text, shot list
  posting_kit.md      — Caption, hashtags, CTA
  video_gen_prompt.md — Prompt for a future AI video generation tool

Usage:
  python generate_video_scripts.py --list-drafts
  python generate_video_scripts.py --input content_drafts/2026-05-29-airport-security-liquids.md
  python generate_video_scripts.py --input content_drafts/... --mode travel_now --write
  python generate_video_scripts.py --input note_drafts/... --mode japanese_ai_media --write
  python generate_video_scripts.py --input ... --mode travel_now --write --force
"""

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from google import genai

# ── Constants ──────────────────────────────────────────────────────────────────

OUTPUT_DIR         = Path("video_scripts")
CONTENT_DRAFTS_DIR = Path("content_drafts")
NOTE_DRAFTS_DIR    = Path("note_drafts")

CHECKLIST_URL  = "https://kytriples.github.io/travel-now-agent/checklist-generator.html"
TRAVEL_NOW_URL = "https://kytriples.github.io/travel-now-agent/"

NOTE_SKIP_FILES = {"README.md", "TODAY_POSTING_GUIDE.md"}

MODES: dict[str, dict] = {
    "travel_now": {
        "label":             "Travel Now (English)",
        "language":          "English",
        "description":       "Travel preparation tips for international travellers",
        "voice":             (
            "Practical, helpful, friendly — like a well-travelled friend giving genuine advice. "
            "Not salesy. Not spammy. No exaggerated claims. "
            "Use soft wording for anything safety/legal/medical: 'may help', 'consider', "
            "'check your airline's current policy'. Focus on real value every sentence."
        ),
        "cta_url":           CHECKLIST_URL,
        "cta_text":          f"Build your full packing checklist → {CHECKLIST_URL}",
        "output_language":   "English",
    },
    "japanese_ai_media": {
        "label":             "Japanese AI Media (日本語)",
        "language":          "Japanese",
        "description":       "AI-assisted media building and side-hustle journey",
        "voice":             (
            "20代後半の普通の会社員。手取りは少なめ。AIで副業メディアを作っている。"
            "関西弁を自然に・軽く交える（絶対に使いすぎない）。"
            "トーン: 頼もしいお兄さん的。正直・温かみ・実用的・少しユーモラス。"
            "絶対にNG: 偉そう・詐欺っぽい・guru的・「月100万稼げる」などの誇張・確実な成果の約束。"
        ),
        "cta_url":           "https://note.com/",
        "cta_text":          "noteのシリーズをフォローしてもらえると更新が届きます。無料記事・有料記事はプロフィールから。",
        "output_language":   "Japanese",
    },
}


# ── Gemini client ──────────────────────────────────────────────────────────────

def get_client() -> genai.Client:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing from .env")
    return genai.Client(api_key=api_key)


# ── Draft parsing ──────────────────────────────────────────────────────────────

def parse_draft(path: Path) -> dict:
    """
    Extract title, body, and metadata from a Markdown draft.
    Handles both content_drafts (English) and note_drafts (Japanese) frontmatter.
    """
    raw = path.read_text(encoding="utf-8")

    # HTML comment frontmatter (both draft types use <!-- key: value --> blocks)
    meta: dict[str, str] = {}
    comment = re.search(r"<!--(.*?)-->", raw, re.DOTALL)
    if comment:
        for line in comment.group(1).strip().splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                meta[key.strip()] = val.strip()

    # First H1 as title
    h1 = re.search(r"^# (.+)$", raw, re.MULTILINE)
    title = h1.group(1).strip() if h1 else path.stem

    # Strip comment block and normalize whitespace
    body = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL).strip()

    # Detect Japanese note draft
    is_japanese = meta.get("type") in ("free", "paid") or "series" in meta

    return {
        "title":       title,
        "body":        body,
        "meta":        meta,
        "is_japanese": is_japanese,
        "path":        str(path),
        "stem":        path.stem,
    }


# ── Slugging & path helpers ────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"-+", "-", text)
    return text[:60]


def _output_slug(draft: dict) -> str:
    """Strip leading YYYY-MM-DD- date and free-/paid- type prefix from stem."""
    stem = draft["stem"]
    stem = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", stem)   # remove date
    stem = re.sub(r"^(free|paid)-", "", stem)           # remove type prefix
    return stem[:60]


def _base_output_dir(draft: dict) -> Path:
    return OUTPUT_DIR / f"{date.today().isoformat()}-{_output_slug(draft)}"


def _resolve_output_dir(draft: dict, force: bool) -> Path:
    base = _base_output_dir(draft)
    if not base.exists() or force:
        return base
    i = 2
    while True:
        candidate = base.parent / f"{base.name}-v{i}"
        if not candidate.exists():
            return candidate
        i += 1


# ── Prompt builders ────────────────────────────────────────────────────────────

_JSON_SCHEMA_EN = """{
  "youtube_shorts": {
    "hook":               "(first 3 seconds — one punchy sentence that stops the scroll)",
    "script":             "(full spoken script, ~45-60 seconds read aloud; use [PAUSE] for natural beats)",
    "on_screen_cue":      "(brief visual direction for each section)",
    "estimated_duration": "~XX seconds"
  },
  "instagram_reels": {
    "hook":               "(first 2 seconds — visual-first or spoken)",
    "script":             "(full spoken script, ~30-45 seconds, punchy)",
    "on_screen_cue":      "(visual direction)",
    "estimated_duration": "~XX seconds"
  },
  "tiktok": {
    "hook":               "(first 2 seconds — most disruptive, curiosity-driven)",
    "script":             "(full spoken script, ~30-60 seconds, very conversational)",
    "on_screen_cue":      "(text overlay and visual direction)",
    "estimated_duration": "~XX seconds"
  },
  "voiceover_script":    "(clean platform-neutral spoken script, ~60 seconds, no cue markers)",
  "onscreen_text": [
    "(line 1 — hook stat or key claim)",
    "(line 2 — tip or step)",
    "(line 3 — tip or step)",
    "(line 4 — CTA)"
  ],
  "shot_list": [
    "(shot 1: what to film — e.g. 'overhead: toiletry bag being packed into clear ziplock')",
    "(shot 2: ...)",
    "(shot 3: ...)",
    "(shot 4: ...)",
    "(shot 5: CTA end card with URL)"
  ],
  "caption":              "(social media caption, 3-5 sentences, ends with a question or engagement hook)",
  "hashtags":             ["#travel", "#traveltips", "(8-12 relevant hashtags total)"],
  "cta":                  "(the exact CTA line for end of video, including URL)",
  "video_gen_prompt":     "(detailed prompt for a future AI video generation tool — scenes, mood, pacing, text overlays, music vibe; enough detail that someone who hasn't read the article can make the video)"
}"""

_JSON_SCHEMA_JP = """{
  "youtube_shorts": {
    "hook":               "（最初の3秒で視聴者を止める一言）",
    "script":             "（全体のセリフ、約45〜60秒で読めるもの；[間]で自然な間を入れる）",
    "on_screen_cue":      "（各セクションで映すべき映像の簡単なメモ）",
    "estimated_duration": "約XX秒"
  },
  "instagram_reels": {
    "hook":               "（最初の2秒、映像的または音声的なフック）",
    "script":             "（全体のセリフ、約30〜45秒、短くてインパクト）",
    "on_screen_cue":      "（映像メモ）",
    "estimated_duration": "約XX秒"
  },
  "tiktok": {
    "hook":               "（最初の2秒、最もキャッチーな導入）",
    "script":             "（全体のセリフ、約30〜60秒、会話的でトレンド感）",
    "on_screen_cue":      "（映像・テキストオーバーレイのメモ）",
    "estimated_duration": "約XX秒"
  },
  "voiceover_script":    "（全プラットフォーム共通ナレーション原稿、約60秒、自然で聞きやすい）",
  "onscreen_text": [
    "（テキスト行1 — フックや数字）",
    "（テキスト行2 — ヒントやステップ）",
    "（テキスト行3 — ヒントやステップ）",
    "（テキスト行4 — CTA）"
  ],
  "shot_list": [
    "（カット1: 何を撮るか）",
    "（カット2: ...）",
    "（カット3: ...）",
    "（カット4: ...）",
    "（カット5: CTA画面）"
  ],
  "caption":              "（SNS投稿用キャプション、3〜5文、最後に質問または行動喚起）",
  "hashtags":             ["#AI副業", "#会社員", "（関連ハッシュタグ8〜12個）"],
  "cta":                  "（動画の最後に使うCTA文、具体的に）",
  "video_gen_prompt":     "（将来のAI動画生成ツール向けの詳細なプロンプト。シーン・雰囲気・映像スタイル・テキストオーバーレイ・音楽の雰囲気を具体的に描写。元の記事を知らない人でもこのプロンプトだけで動画を作れるくらい詳細に。）"
}"""


def build_prompt(draft: dict, mode: str) -> str:
    m            = MODES[mode]
    today_str    = date.today().strftime("%Y-%m-%d")
    body_excerpt = draft["body"][:3500]
    if len(draft["body"]) > 3500:
        body_excerpt += "\n\n[...content continues — adapt scripts from this excerpt...]"

    if mode == "travel_now":
        return f"""You are a short-form video script writer for a travel preparation channel called "Travel Now".

Generate platform-specific scripts from the source article below.
Return ONLY valid JSON — no markdown code fences, no prose explanations outside the JSON.

SOURCE ARTICLE
Title: {draft["title"]}
Date: {today_str}

{body_excerpt}

VOICE & TONE
{m["voice"]}

CTA (use at the end of each script):
{m["cta_text"]}

HARD RULES
- No exaggerated claims
- No guaranteed results
- No "secret method" language
- Soft wording required for anything safety/legal/medical/insurance-related
- Every sentence must earn its place — cut filler aggressively
- Keep each platform script natural for spoken delivery

OUTPUT JSON SCHEMA (return this structure exactly):
{_JSON_SCHEMA_EN}"""

    else:  # japanese_ai_media
        return f"""あなたはショート動画スクリプトライターです。
以下の記事を元に、YouTube Shorts・Instagram Reels・TikTok向けのスクリプトを日本語で生成してください。

有効なJSONのみを返してください。マークダウンのコードブロックや説明文は含めないでください。

■ 元になる記事
タイトル: {draft["title"]}
日付: {today_str}

{body_excerpt}

■ キャラクター・口調
{m["voice"]}

■ CTA（動画の最後に使うもの）
{m["cta_text"]}

■ 絶対に守るべきルール
- 収益を誇張する表現は絶対に使わない（「月100万」「絶対稼げる」など）
- 確実な成果を約束しない
- 「秘密の方法」「限定情報」などの怪しい表現は使わない
- 全体のトーン: 正直・温かみ・実用的・背中を押す

■ 出力JSONスキーマ（この構造を厳密に守る）:
{_JSON_SCHEMA_JP}"""


# ── Gemini call ────────────────────────────────────────────────────────────────

# Try models in order; fall back if a model is unavailable (503/429)
_MODELS = [
    "gemini-2.5-flash",        # preferred — best quality
    "gemini-2.0-flash",        # strong fallback
    "gemini-2.5-flash-lite",   # lighter, usually available
    "gemini-2.0-flash-lite",   # lightest fallback
]


def call_gemini(prompt: str) -> dict:
    client   = get_client()
    last_err: Exception | None = None

    for model in _MODELS:
        try:
            print(f"  → trying model: {model}")
            response = client.models.generate_content(
                model    = model,
                contents = prompt,
            )
            text = response.text.strip()

            # Strip markdown code fences that Gemini sometimes wraps around JSON
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                print("\nJSON parsing failed. Raw Gemini output (first 3000 chars):")
                print(text[:3000])
                raise RuntimeError("Gemini returned invalid JSON") from exc

        except RuntimeError:
            raise  # JSON parse errors propagate immediately
        except Exception as exc:
            last_err = exc
            msg = str(exc)
            if "503" in msg or "UNAVAILABLE" in msg or "429" in msg:
                print(f"  → {model} unavailable, trying next...")
                continue
            raise  # unexpected error — don't silently swallow

    raise RuntimeError(
        f"All Gemini models unavailable. Last error: {last_err}"
    )


# ── Rendering ─────────────────────────────────────────────────────────────────

def _md_bullets(items: list) -> str:
    if not items:
        return "_(none generated)_"
    return "\n".join(f"- {item}" for item in items)


def render_files(data: dict, draft: dict, mode: str) -> dict[str, str]:
    """
    Render the Gemini response into four output files.
    Returns { filename: content } dict.
    """
    m     = MODES[mode]
    title = draft["title"]
    today = date.today().isoformat()
    src   = draft["path"]

    header = f"> Source: `{src}`  \n> Mode: {m['label']}  \n> Generated: {today}  \n> ⚠️ Review before use. Do not post automatically."

    # ── scripts.md ──────────────────────────────────────────────────────────
    yt = data.get("youtube_shorts", {})
    ig = data.get("instagram_reels", {})
    tt = data.get("tiktok", {})

    scripts_md = f"""# Video Scripts — {title}

{header}

---

## YouTube Shorts

**Hook** *(first ~3 seconds)*
> {yt.get("hook", "_(missing)_")}

**Full Script** *({yt.get("estimated_duration", "~60 seconds")})*
{yt.get("script", "_(missing)_")}

**On-Screen Visual Cue**
{yt.get("on_screen_cue", "_(missing)_")}

---

## Instagram Reels

**Hook** *(first ~2 seconds)*
> {ig.get("hook", "_(missing)_")}

**Full Script** *({ig.get("estimated_duration", "~45 seconds")})*
{ig.get("script", "_(missing)_")}

**On-Screen Visual Cue**
{ig.get("on_screen_cue", "_(missing)_")}

---

## TikTok

**Hook** *(first ~2 seconds)*
> {tt.get("hook", "_(missing)_")}

**Full Script** *({tt.get("estimated_duration", "~45 seconds")})*
{tt.get("script", "_(missing)_")}

**On-Screen Visual Cue**
{tt.get("on_screen_cue", "_(missing)_")}
"""

    # ── production_notes.md ─────────────────────────────────────────────────
    onscreen = data.get("onscreen_text", [])
    shots    = data.get("shot_list", [])

    production_md = f"""# Production Notes — {title}

{header}

---

## Voiceover Script *(platform-neutral, ~60 seconds)*

{data.get("voiceover_script", "_(missing)_")}

---

## On-Screen Text *(overlay order)*

{_md_bullets(onscreen)}

---

## Shot List

{_md_bullets(shots)}
"""

    # ── posting_kit.md ──────────────────────────────────────────────────────
    hashtags    = data.get("hashtags", [])
    hashtag_str = "  ".join(hashtags) if hashtags else "_(none generated)_"

    posting_md = f"""# Posting Kit — {title}

{header}

---

## Caption

{data.get("caption", "_(missing)_")}

---

## Hashtags

{hashtag_str}

---

## CTA

{data.get("cta", "_(missing)_")}
"""

    # ── video_gen_prompt.md ─────────────────────────────────────────────────
    vgp_md = f"""# Video Generation Prompt — {title}

{header}

> NOTE: This prompt is for **future use** with AI video generation tools (e.g. Sora, Runway, Pika).
> It is a reference document — not an API call. No video is generated automatically.

---

{data.get("video_gen_prompt", "_(missing)_")}
"""

    return {
        "scripts.md":           scripts_md,
        "production_notes.md":  production_md,
        "posting_kit.md":       posting_md,
        "video_gen_prompt.md":  vgp_md,
    }


# ── Draft listing ──────────────────────────────────────────────────────────────

def list_drafts() -> None:
    print("\n=== AVAILABLE INPUT DRAFTS ===")

    print(f"\n  {CONTENT_DRAFTS_DIR}/  →  use --mode travel_now")
    found = False
    if CONTENT_DRAFTS_DIR.exists():
        for f in sorted(CONTENT_DRAFTS_DIR.glob("*.md")):
            print(f"    {f}")
            found = True
    if not found:
        print("    (none found)")

    print(f"\n  {NOTE_DRAFTS_DIR}/  →  use --mode japanese_ai_media")
    if NOTE_DRAFTS_DIR.exists():
        for f in sorted(NOTE_DRAFTS_DIR.glob("*.md")):
            if f.name not in NOTE_SKIP_FILES:
                print(f"    {f}")

    print()
    print("  Example:")
    print("    python generate_video_scripts.py \\")
    print("      --input content_drafts/2026-05-29-airport-security-liquids.md \\")
    print("      --mode travel_now --write")
    print()
    print("    python generate_video_scripts.py \\")
    print("      --input note_drafts/2026-05-29-paid-ai-travel-media-7days-workflow-practical.md \\")
    print("      --mode japanese_ai_media --write")
    print("=" * 44)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate short-form video scripts from Travel Now Markdown drafts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input",  "-i",  help="Path to input Markdown draft file")
    parser.add_argument(
        "--mode", choices=list(MODES.keys()), default="travel_now",
        help="Content mode — sets voice, language, and CTA (default: travel_now)",
    )
    parser.add_argument("--write",       action="store_true", help="Save output files to video_scripts/")
    parser.add_argument("--force",       action="store_true", help="Overwrite existing output folder")
    parser.add_argument("--list-drafts", action="store_true", help="List available input drafts and exit")

    args = parser.parse_args()

    if args.list_drafts:
        list_drafts()
        return

    if not args.input:
        print("Error: --input is required. Use --list-drafts to see available files.\n")
        parser.print_help()
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: file not found: {input_path}")
        sys.exit(1)

    draft   = parse_draft(input_path)
    mode    = args.mode
    m       = MODES[mode]
    out_dir = _resolve_output_dir(draft, args.force)

    print(f"\n=== VIDEO SCRIPT GENERATOR ===")
    print(f"  Input:    {input_path}")
    print(f"  Title:    {draft['title'][:72]}")
    print(f"  Mode:     {m['label']}")
    print(f"  Output:   {out_dir}/")
    print(f"  Write:    {'yes' if args.write else 'dry run (no API call, no files)'}")
    if args.force:
        print(f"  Force:    yes (will overwrite)")
    print()

    if not args.write:
        print("  Add --write to call Gemini and generate scripts.")
        print("=" * 36)
        return

    print("  Calling Gemini API (gemini-2.5-flash)...")
    prompt = build_prompt(draft, mode)
    data   = call_gemini(prompt)
    print("  Response received. Rendering...")

    files = render_files(data, draft, mode)

    out_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in files.items():
        fpath = out_dir / filename
        fpath.write_text(content, encoding="utf-8")
        lines = content.count("\n")
        print(f"    ✓  {fpath}  ({lines} lines)")

    print()
    print(f"  Done. Review all scripts before use:")
    print(f"  {out_dir}/")
    print()
    print(f"  Next steps:")
    print(f"    1. Read scripts.md — pick the best hook per platform")
    print(f"    2. Read production_notes.md — voiceover + shot list")
    print(f"    3. Read posting_kit.md — caption + hashtags + CTA")
    print(f"    4. Record, edit, and post manually")
    print(f"    5. Keep video_gen_prompt.md for future AI video tools")
    print("=" * 36)


if __name__ == "__main__":
    main()
