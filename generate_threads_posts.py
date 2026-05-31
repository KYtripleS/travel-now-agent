#!/usr/bin/env python3
"""
generate_threads_posts.py

Generates Threads-ready post drafts from existing note drafts, Travel Now
updates, and monetization logs. Supports two modes:

  japanese_ai_media — Japanese posts for 「会社員、AIでメディアを作る。」
  travel_now        — English posts promoting Travel Now checklists

Output is saved to threads_drafts/YYYY-MM-DD-{mode}.md for MANUAL posting.

Usage:
  python generate_threads_posts.py                         # dry run (no API call)
  python generate_threads_posts.py --write                 # generate and save
  python generate_threads_posts.py --write --mode travel_now
  python generate_threads_posts.py --write --mode japanese_ai_media
  python generate_threads_posts.py --write --all           # both modes
  python generate_threads_posts.py --write --force         # overwrite today's files

Constraints (never change):
  - Does NOT post to Threads automatically.
  - Does NOT use the Meta API or Threads API.
  - Does NOT log in. Does NOT use browser automation.
  - All output is for MANUAL posting only.
"""

import argparse
import csv
import json
import os
import re
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

# ── Constants ─────────────────────────────────────────────────────────────────

DRAFTS_DIR    = Path("threads_drafts")
NOTE_DIR      = Path("note_drafts")
MONO_LOG      = Path("data/monetization_log.csv")
TOP_POSTS_CSV = Path("top_posts.csv")

CHECKLIST_URL = "https://kytriples.github.io/travel-now-agent/checklist-generator.html"
SERIES_NAME   = "会社員、AIでメディアを作る。"

_SKIP_NOTE = {"README.md", "TODAY_POSTING_GUIDE.md"}

# Gemini model fallback chain (same as other generators)
_GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
]


# ── Gemini client ─────────────────────────────────────────────────────────────

def get_client():
    """Lazily import google.genai and return an authenticated client."""
    try:
        from google import genai  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "google-genai is not installed. Run: pip install google-genai"
        ) from exc
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing. Check your .env file.")
    return genai.Client(api_key=api_key)


def call_gemini(client, prompt: str) -> str:
    """Call Gemini with the fallback model chain; return response text."""
    last_err = None
    for model in _GEMINI_MODELS:
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            return response.text.strip()
        except Exception as e:
            print(f"    Model {model} failed: {e}")
            last_err = e
    raise RuntimeError(f"All Gemini models failed. Last error: {last_err}") from last_err


# ── Context helpers ───────────────────────────────────────────────────────────

def _parse_note_frontmatter(path: Path) -> dict:
    """Extract <!-- key: value --> frontmatter and the first # heading."""
    text = path.read_text(encoding="utf-8")
    meta: dict = {}
    m = re.search(r"<!--(.*?)-->", text, re.DOTALL)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()
    for line in text.splitlines():
        if line.strip().startswith("# "):
            meta["_title"] = line.strip()[2:].strip()
            break
    return meta


def gather_note_context() -> dict:
    """Return the 3 most recent free and paid note drafts for prompt context."""
    if not NOTE_DIR.exists():
        return {"free": [], "paid": []}

    free_notes: list = []
    paid_notes: list = []

    for p in sorted(NOTE_DIR.glob("*.md"), reverse=True):
        if p.name in _SKIP_NOTE:
            continue
        meta  = _parse_note_frontmatter(p)
        ntype = meta.get("type", "").lower()
        title = meta.get("_title", p.stem)
        d     = re.match(r"(\d{4}-\d{2}-\d{2})", p.name)
        item  = {"title": title, "date": d.group(1) if d else ""}
        if ntype == "free":
            free_notes.append(item)
        elif ntype == "paid":
            paid_notes.append(item)

    return {"free": free_notes[:3], "paid": paid_notes[:3]}


def gather_travel_now_context() -> dict:
    """Return today's X post topics for thematic alignment."""
    if not TOP_POSTS_CSV.exists():
        return {"posts": []}

    with TOP_POSTS_CSV.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    posts = [
        {
            "slot":  r.get("slot", ""),
            "type":  r.get("type", ""),
            "topic": r.get("topic", ""),
            "text":  r.get("post_text", "")[:140],
        }
        for r in rows
    ]
    return {"posts": posts}


# ── Prompts ───────────────────────────────────────────────────────────────────

def build_japanese_prompt(context: dict) -> str:
    note_ctx  = context.get("notes", {})
    free_list = note_ctx.get("free", [])
    paid_list = note_ctx.get("paid", [])

    free_text = "\n".join(
        f"  - {n['date']} 「{n['title']}」" for n in free_list
    ) or "  (まだなし)"
    paid_text = "\n".join(
        f"  - {n['date']} 「{n['title']}」(¥300)" for n in paid_list
    ) or "  (まだなし)"

    today_str = date.today().strftime("%Y年%m月%d日")

    return f"""あなたはThreads（Meta）向けの日本語投稿を作成する専門ライターです。
以下の設定・制約・フォーマットを厳密に守り、有効なJSONのみを返してください。
マークダウンのコードブロック（```）・説明文・前置きは一切含めないこと。

■ ナレーター設定
- 20代後半の普通の会社員。手取りが「え、マジ？」ってレベルで少なめ。
- AIを使った副業メディア構築に挑戦中。シリーズ名: 「{SERIES_NAME}」
- キャラ: 夢追いチャレンジャー・頼もしいお兄さん・等身大の普通の人
- 口調: 関西弁を自然に・軽めに交える（使いすぎない。1〜2個/投稿が上限）
- トーン: 正直・温かみ・実用的・少しユーモラス・背中を押す
- 絶対NG: 偉そう / 詐欺っぽい / guru的 / 「月〇万稼げる」などの誇張 /
          確実な成果の約束 / 医療・法律・保険の保証

■ 既存コンテンツ（参照してトーンの一貫性を保つ）
無料note記事:
{free_text}

有料note記事 (¥300):
{paid_text}

■ Threads投稿ルール
- 1投稿 500文字以内（Threadsの上限）
- 親しみやすく自然な文体。スパムっぽくしない。
- 絵文字は控えめ（1投稿あたり1〜2個まで、なくてもよい）
- ハッシュタグは不要（Threadsでは効果が薄い）
- CTA候補: 無料note記事へ誘導 / 有料note記事へ誘導 / シリーズフォロー促進
- CTAはソフトに。「読んでみてください」「気になる方はぜひ」くらいの温度感。

■ 本日 {today_str}

■ 出力形式（有効なJSONのみ。コードブロック・説明文は不要）
{{
  "standalone": [
    {{
      "id": 1,
      "text": "（投稿本文。改行は \\n で表現。500文字以内）",
      "cta_type": "none|free_article|paid_article|follow",
      "char_count": 123,
      "notes": "（この投稿が効果的な理由を一言で）"
    }}
  ],
  "threads": [
    {{
      "id": 1,
      "topic": "（スレッドのテーマを短く）",
      "posts": [
        {{"order": 1, "text": "（改行は \\n で。500文字以内）", "char_count": 123}},
        {{"order": 2, "text": "（改行は \\n で。500文字以内）", "char_count": 123}},
        {{"order": 3, "text": "（改行は \\n で。500文字以内）", "char_count": 123}}
      ]
    }},
    {{
      "id": 2,
      "topic": "（別テーマ）",
      "posts": [
        {{"order": 1, "text": "（改行は \\n で。500文字以内）", "char_count": 123}},
        {{"order": 2, "text": "（改行は \\n で。500文字以内）", "char_count": 123}}
      ]
    }}
  ],
  "cta_variants": [
    {{
      "id": 1,
      "text": "（ソフトCTA含む投稿本文。改行は \\n で。500文字以内）",
      "cta_target": "free_note|paid_note|follow",
      "char_count": 123
    }}
  ]
}}

standaloneは5個、threadsは2個（各2〜3投稿）、cta_variantsは3個を必ず生成すること。
"""


def build_travel_now_prompt(context: dict) -> str:
    posts_ctx  = context.get("x_posts", {}).get("posts", [])
    today_topics = "\n".join(
        f"  - [{p['slot']}] {p['topic']}" for p in posts_ctx
    ) or "  (no X posts loaded)"

    return f"""You are writing Threads (Meta) post drafts for the Travel Now account.
Travel Now is a practical travel-prep brand for normal people who want smoother trips.
It is NOT luxury travel, NOT backpacker content, NOT influencer travel.

Voice:
- Useful, concise, practical — like a well-prepared travel friend sharing real tips
- Conversational but not casual to the point of being sloppy
- Not salesy, not spammy, not hypey
- Soft wording only: "may help", "consider", "worth checking", "can make it easier"
- No guarantees on safety, medical, legal, or insurance topics
- No strong claims: never "protect your data", "essential", "lifesaver", "non-negotiable"
- No fake personal experiences

Platform (Threads):
- Max 500 characters per post
- Natural, friendly tone — not X-optimized (no aggressive hooks required)
- Hashtags optional — use 0–1 per post at most
- No affiliate links inside posts

CTA (soft):
- Invite readers to try the Travel Now Checklist Generator
- URL: {CHECKLIST_URL}
- CTA posts only — never force CTA into standalone posts that don't need it

Today's X themes (use for consistency — different angle, same topic area is fine):
{today_topics}

Generate:
- 5 standalone posts: self-contained practical tips, most with no CTA
- 2 thread sequences: 2–3 connected posts on one topic per sequence
- 3 soft CTA variants: posts that naturally invite trying the checklist generator

Each post must be genuinely useful — not just a teaser or pure promotion.
All posts must be under 500 characters.

Return ONLY valid JSON. No markdown fences, no explanation.

JSON format (follow exactly):
{{
  "standalone": [
    {{
      "id": 1,
      "text": "post text (use \\n for line breaks)",
      "cta_type": "none|checklist",
      "char_count": 123,
      "notes": "one-line reason this post works"
    }}
  ],
  "threads": [
    {{
      "id": 1,
      "topic": "thread topic label",
      "posts": [
        {{"order": 1, "text": "text (\\n for newlines)", "char_count": 123}},
        {{"order": 2, "text": "text (\\n for newlines)", "char_count": 123}}
      ]
    }},
    {{
      "id": 2,
      "topic": "second thread topic",
      "posts": [
        {{"order": 1, "text": "text (\\n for newlines)", "char_count": 123}},
        {{"order": 2, "text": "text (\\n for newlines)", "char_count": 123}},
        {{"order": 3, "text": "text (\\n for newlines)", "char_count": 123}}
      ]
    }}
  ],
  "cta_variants": [
    {{
      "id": 1,
      "text": "post text with soft CTA (\\n for newlines)",
      "cta_target": "checklist_generator",
      "char_count": 123
    }}
  ]
}}

Generate exactly: 5 standalone posts, 2 thread sequences, 3 CTA variants.
"""


# ── Markdown renderers ────────────────────────────────────────────────────────

def _render_japanese(data: dict, today_str: str) -> str:
    _CTA_LABELS = {
        "free_article": "無料note記事へ誘導",
        "paid_article":  "有料note記事へ誘導 (¥300)",
        "follow":        "シリーズフォロー促進",
        "none":          "CTA なし",
    }
    _TARGET_LABELS = {
        "free_note":  "無料note記事",
        "paid_note":  "有料note記事 (¥300)",
        "follow":     "フォロー促進",
    }

    lines: list[str] = [
        f"# Threads下書き — {today_str} — japanese_ai_media",
        f"<!-- mode: japanese_ai_media -->",
        f"<!-- date: {today_str} -->",
        f"<!-- generated_by: generate_threads_posts.py -->",
        f"<!-- series: {SERIES_NAME} -->",
        "",
        "> **使い方:** 以下のテキストをコピーしてThreadsに手動投稿してください。",
        "> 自動投稿・Meta API・ブラウザ自動操作は使いません。",
        "",
        "---",
        "",
        "## 1. スタンドアロン投稿（単体完結）",
        "",
    ]

    for post in data.get("standalone", []):
        pid   = post.get("id", "?")
        text  = post.get("text",   "").replace("\\n", "\n")
        notes = post.get("notes",  "")
        chars = post.get("char_count", "?")
        cta   = post.get("cta_type", "none")

        lines += [
            f"### 投稿 {pid}",
            "",
            "```",
            text,
            "```",
            "",
        ]
        if notes:
            lines += [f"*{notes}*", ""]
        lines += [
            f"CTA: {_CTA_LABELS.get(cta, cta)}　｜　文字数: {chars}",
            "",
            "---",
            "",
        ]

    lines += [
        "",
        "## 2. スレッド形式（連投）",
        "",
    ]

    for seq in data.get("threads", []):
        sid   = seq.get("id", "?")
        topic = seq.get("topic", "")
        posts = seq.get("posts", [])
        n     = len(posts)

        lines += [f"### スレッド {sid} — {topic}", ""]
        for p in posts:
            order = p.get("order", "?")
            text  = p.get("text", "").replace("\\n", "\n")
            chars = p.get("char_count", "?")
            lines += [
                f"**[{order}/{n}]** （{chars}文字）",
                "",
                "```",
                text,
                "```",
                "",
            ]
        lines += ["---", ""]

    lines += [
        "",
        "## 3. ソフトCTAバリアント",
        "",
    ]

    for cta in data.get("cta_variants", []):
        cid    = cta.get("id", "?")
        text   = cta.get("text", "").replace("\\n", "\n")
        target = cta.get("cta_target", "")
        chars  = cta.get("char_count", "?")

        lines += [
            f"### CTA {cid} — {_TARGET_LABELS.get(target, target)}",
            "",
            "```",
            text,
            "```",
            "",
            f"文字数: {chars}",
            "",
            "---",
            "",
        ]

    return "\n".join(lines)


def _render_travel_now(data: dict, today_str: str) -> str:
    lines: list[str] = [
        f"# Threads Drafts — {today_str} — travel_now",
        f"<!-- mode: travel_now -->",
        f"<!-- date: {today_str} -->",
        f"<!-- generated_by: generate_threads_posts.py -->",
        f"<!-- checklist_url: {CHECKLIST_URL} -->",
        "",
        "> **Usage:** Copy text below and post manually to Threads.",
        "> No auto-posting. No Meta API. No browser automation.",
        "",
        "---",
        "",
        "## 1. Standalone Posts",
        "",
    ]

    for post in data.get("standalone", []):
        pid   = post.get("id", "?")
        text  = post.get("text",  "").replace("\\n", "\n")
        notes = post.get("notes", "")
        chars = post.get("char_count", "?")
        cta   = post.get("cta_type", "none")

        lines += [
            f"### Post {pid}",
            "",
            "```",
            text,
            "```",
            "",
        ]
        if notes:
            lines += [f"*{notes}*", ""]
        cta_label = "Checklist generator" if cta == "checklist" else "None"
        lines += [
            f"CTA: {cta_label}　|　Chars: {chars}",
            "",
            "---",
            "",
        ]

    lines += [
        "",
        "## 2. Thread Sequences",
        "",
    ]

    for seq in data.get("threads", []):
        sid   = seq.get("id", "?")
        topic = seq.get("topic", "")
        posts = seq.get("posts", [])
        n     = len(posts)

        lines += [f"### Sequence {sid} — {topic}", ""]
        for p in posts:
            order = p.get("order", "?")
            text  = p.get("text", "").replace("\\n", "\n")
            chars = p.get("char_count", "?")
            lines += [
                f"**[{order}/{n}]** ({chars} chars)",
                "",
                "```",
                text,
                "```",
                "",
            ]
        lines += ["---", ""]

    lines += [
        "",
        "## 3. Soft CTA Variants",
        "",
    ]

    for cta in data.get("cta_variants", []):
        cid   = cta.get("id", "?")
        text  = cta.get("text", "").replace("\\n", "\n")
        chars = cta.get("char_count", "?")

        lines += [
            f"### CTA Variant {cid}",
            "",
            "```",
            text,
            "```",
            "",
            f"Chars: {chars}",
            f"CTA → {CHECKLIST_URL}",
            "",
            "---",
            "",
        ]

    return "\n".join(lines)


# ── Core generation ───────────────────────────────────────────────────────────

def generate_mode(
    client,
    mode:  str,
    write: bool,
    force: bool,
) -> Path | None:
    today_str = date.today().isoformat()
    out_path  = DRAFTS_DIR / f"{today_str}-{mode}.md"

    if out_path.exists() and not force:
        print(f"  [{mode}] {out_path} already exists — skipping. (use --force to overwrite)")
        return out_path

    print(f"  [{mode}] Gathering context…")

    if mode == "japanese_ai_media":
        context = {"notes": gather_note_context()}
        prompt  = build_japanese_prompt(context)
    else:
        context = {"x_posts": gather_travel_now_context()}
        prompt  = build_travel_now_prompt(context)

    if not write:
        print(f"  [{mode}] Dry run — prompt built ({len(prompt)} chars). Use --write to call Gemini.")
        return None

    print(f"  [{mode}] Calling Gemini…")
    raw = call_gemini(client, prompt)

    # Strip markdown fences if Gemini returns them anyway
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = raw.rstrip("`").strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  [{mode}] JSON parse error: {e}")
        print(f"  Raw output (first 600 chars):\n{raw[:600]}")
        return None

    content = (
        _render_japanese(data, today_str)
        if mode == "japanese_ai_media"
        else _render_travel_now(data, today_str)
    )

    DRAFTS_DIR.mkdir(exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    print(f"  [{mode}] ✓ Saved → {out_path}")
    return out_path


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Threads post drafts for manual posting.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_threads_posts.py                         dry run
  python generate_threads_posts.py --write                 japanese_ai_media
  python generate_threads_posts.py --write --mode travel_now
  python generate_threads_posts.py --write --all           both modes
  python generate_threads_posts.py --write --force         overwrite today
""",
    )
    parser.add_argument("--write",  action="store_true", help="Call Gemini and save drafts")
    parser.add_argument(
        "--mode",
        default="japanese_ai_media",
        choices=["japanese_ai_media", "travel_now"],
        help="Generation mode (default: japanese_ai_media)",
    )
    parser.add_argument("--all",   action="store_true", help="Generate both modes")
    parser.add_argument("--force", action="store_true", help="Overwrite today's files if they exist")
    args = parser.parse_args()

    divider = "=" * 56
    print(divider)
    print("=== GENERATE THREADS DRAFTS                         ===")
    print(divider)
    print()
    print("  Platform:      Threads (Meta)")
    print("  Auto-posting:  DISABLED")
    print("  Meta API:      NOT USED")
    print("  Login:         NOT PERFORMED")
    print()

    modes = ["japanese_ai_media", "travel_now"] if args.all else [args.mode]

    if not args.write:
        print(f"  Dry run — modes: {', '.join(modes)}")
        print(f"  Output dir: {DRAFTS_DIR}/")
        print()
        # Still gather context so the user can see what would be used
        for mode in modes:
            print(f"  [{mode}] Gathering context (dry run)…")
            if mode == "japanese_ai_media":
                ctx = {"notes": gather_note_context()}
                prompt = build_japanese_prompt(ctx)
            else:
                ctx = {"x_posts": gather_travel_now_context()}
                prompt = build_travel_now_prompt(ctx)
            print(f"  [{mode}] Prompt ready ({len(prompt)} chars).")
        print()
        print("  Run with --write to call Gemini and save drafts.")
        print(divider)
        return

    client = get_client()
    saved  = []

    for mode in modes:
        path = generate_mode(client, mode, write=True, force=args.force)
        if path:
            saved.append(path)

    print()
    if saved:
        print(f"  {len(saved)} draft(s) saved:")
        for p in saved:
            print(f"    {p}")
        print()
        print("  Review drafts, then copy and post manually to Threads.")
    else:
        print("  No drafts saved. Check errors above.")
    print(divider)


if __name__ == "__main__":
    main()
