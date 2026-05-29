#!/usr/bin/env python3
"""
generate_note_draft.py

Generates two Japanese Markdown drafts per run for the note series:
  「会社員、AIでメディアを作る。」
  「1日40分で、英語サイト・X・note・アフィリエイト導線を育てる実験記」

Drafts are saved to note_drafts/ for MANUAL posting to note ONLY.
This script does NOT post to note, use unofficial APIs,
log in to note, or run any browser automation.

Two drafts per run:
  1. Free article  — story-driven, relatable, does not reveal all implementation details
  2. Paid article  — practical, detailed, includes frameworks / workflows / checklists

Usage:
  python generate_note_draft.py                        # dry run (shows config, no API call)
  python generate_note_draft.py --write                # generate and save drafts
  python generate_note_draft.py --write --mode build_log
  python generate_note_draft.py --write --topic-free "..."  --topic-paid "..."
  python generate_note_draft.py --write --force        # overwrite today's files
  python generate_note_draft.py --list-modes           # show available modes
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

# ── Series constants ───────────────────────────────────────────────────────────

SERIES_NAME  = "会社員、AIでメディアを作る。"
SUBTITLE     = "1日40分で、英語サイト・X・note・アフィリエイト導線を育てる実験記"
SITE_URL     = "https://kytriples.github.io/travel-now-agent/"
DRAFTS_DIR   = Path("note_drafts")

# ── Topic modes ────────────────────────────────────────────────────────────────

MODES: dict[str, dict] = {
    "ai_side_hustle": {
        "label":       "AIで副業",
        "description": "AIを使った副業・メディア構築の体験談とノウハウ",
        "free_hint":   "AIで何かを始めた体験・失敗・気づきをストーリーで語る",
        "paid_hint":   "AIツールの使い方・ワークフロー・実際の手順を詳細に解説する",
        "free_default":  "AIで副業を始めて最初の1ヶ月でわかったこと",
        "paid_default":  "【実践編】AIで副業メディアを立ち上げる具体的な手順",
    },
    "travel_prep": {
        "label":       "旅行メディア",
        "description": "旅行準備メディアの構造・設計・アフィリエイト実装",
        "free_hint":   "旅行メディアを副業で作る面白さや可能性をストーリーで伝える",
        "paid_hint":   "旅行メディアの設計・収益化・コンテンツ実装を実践レベルで解説する",
        "free_default":  "旅行メディアを副業で作れるって知ってた？",
        "paid_default":  "【実践編】英語旅行メディアの設計とアフィリエイト実装全公開",
    },
    "english_global": {
        "label":       "英語メディア",
        "description": "英語サイト・グローバル発信・英語コンテンツの実践",
        "free_hint":   "英語で発信することの面白さと心理的ハードルを語る",
        "paid_hint":   "英語コンテンツの制作フロー・AIの活用・品質管理を実践的に解説する",
        "free_default":  "英語が得意じゃない僕がAIで英語サイトを作った話",
        "paid_default":  "【実践編】AIで英語コンテンツを量産する実際のフロー",
    },
    "build_log": {
        "label":       "制作ログ",
        "description": "進捗報告・作業ログ・週次振り返り",
        "free_hint":   "今週やったこと・感じたこと・失敗と回復をリアルに語る",
        "paid_hint":   "具体的な作業手順・使ったプロンプト・ツール設定・改善結果を全公開する",
        "free_default":  "今週の制作ログ：うまくいったこと・失敗したこと",
        "paid_default":  "【実践編】今週の制作ログ全公開：プロンプト・設定・数値",
    },
    "template_pack": {
        "label":       "テンプレート",
        "description": "すぐに使えるテンプレート・チェックリスト・フレームワーク配布",
        "free_hint":   "テンプレートを使うとどう変わるか・作った背景を話す",
        "paid_hint":   "実際に使えるテンプレート・チェックリスト・スクリプトを全公開する",
        "free_default":  "副業メディア制作で使い続けているテンプレートの話",
        "paid_default":  "【実践編】副業メディア制作テンプレート全部入りパック",
    },
}

# Weekday-based auto mode (Mon=0 … Sun=6)
_WEEKDAY_MODES = [
    "build_log",       # Mon
    "ai_side_hustle",  # Tue
    "travel_prep",     # Wed
    "english_global",  # Thu
    "template_pack",   # Fri
    "ai_side_hustle",  # Sat
    "build_log",       # Sun
]


def auto_mode() -> str:
    return _WEEKDAY_MODES[date.today().weekday()]


# ── Gemini client ──────────────────────────────────────────────────────────────

def get_client() -> genai.Client:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing. Check your .env file.")
    return genai.Client(api_key=api_key)


# ── Prompt ─────────────────────────────────────────────────────────────────────

def build_prompt(mode: str, free_topic: str, paid_topic: str) -> str:
    m         = MODES.get(mode, MODES["ai_side_hustle"])
    today_str = date.today().strftime("%Y年%m月%d日")

    return f"""あなたは日本のnote専用記事ライターです。以下の設定に従い、2本の記事を含む有効なJSONを生成してください。

■ シリーズ情報
シリーズ名: 「{SERIES_NAME}」
サブタイトル: 「{SUBTITLE}」
公開日: {today_str}
公開サイト（Travel Now）: {SITE_URL}

■ ナレーターの人物像・口調
- 20代後半の会社員。手取りは少なめ。副業でAIを使って英語メディアを構築中。
- 夢を追う挑戦者。普通の人の道案内役・ヒーローになりたいという思いがある。
- 口調: 頼もしいお兄さん的。関西弁を自然に・軽く交える（絶対に使いすぎない）。
- 以前はよく失敗していたが、今は少しずつうまくいき始めている段階。
- トーン: 正直・温かみ・実用的・少しユーモラス・背中を押す。
- 絶対にNGなこと: 偉そう・詐欺っぽい・guru的・「月100万稼げる」などの誇張・確実な成果の約束。

■ 今日のモード
{m["label"]}: {m["description"]}

■ 無料記事の要件
トピック: {free_topic}
方針: {m["free_hint"]}
- ストーリー性あり・共感できる・読んで面白い
- 全実装詳細は明かさない（有料記事へ自然に誘導する）
- intro: 200〜300文字
- body: 800〜1200文字（markdown見出し・箇条書き含む）
- takeaways: まとめ・気づきを箇条書き3〜5個

■ 有料記事の要件
トピック: {paid_topic}
方針: {m["paid_hint"]}
- 実践的・詳細。フレームワーク・ワークフロー・チェックリスト・テンプレートを必ず含む。
- 本文の中で「実際の公開サイト（Travel Now: {SITE_URL}）のURLと設計ロジックをこの記事の中で紹介している」と自然に言及すること。
- APIキー・.envの中身・プライベートな認証情報・機密実装詳細は含めない。
- 誇張した収益主張（月〇万円など）・確実な成果の約束はしない。
- intro: 200〜300文字
- body: 1500〜2500文字（フレームワーク・チェックリスト・テンプレート含む）
- takeaways: 実践チェックリストを箇条書き5〜8個

■ 絶対に守るべき出力ルール
- 有効なJSONのみを返す。マークダウンのコードブロック（```）や説明文は一切含めない。
- JSONの文字列内の改行は必ず \\n で表現する（実際の改行文字を含めない）。
- slugフィールドは英数字・ハイフンのみ（日本語・スペース・記号は含めない）。
- titleは魅力的で、noteのタイムラインで目を引くものにする。

■ 出力するJSONの形式（この形式を厳密に守る）
{{
  "free": {{
    "title": "（note向けのタイトル、魅力的に）",
    "slug": "lowercase-english-hyphens-only",
    "intro": "（導入文 200〜300文字）",
    "body": "（本文 markdown形式 \\nで改行 800〜1200文字）",
    "takeaways": "（まとめ・気づき 箇条書き3〜5個 \\nで区切る）",
    "cta": "（ソフトなCTA文。有料記事への誘導またはnoteフォロー促進。1〜3文）",
    "tags": ["タグ1", "タグ2", "タグ3", "タグ4", "タグ5"]
  }},
  "paid": {{
    "title": "（有料記事のタイトル。【実践編】や【保存版】などを自然につける）",
    "slug": "lowercase-english-hyphens-only",
    "intro": "（導入文 200〜300文字）",
    "body": "（本文 markdown形式 \\nで改行 フレームワーク・チェックリスト・テンプレート含む 1500〜2500文字）",
    "takeaways": "（実践チェックリスト 箇条書き5〜8個 \\nで区切る）",
    "cta": "（ソフトなCTA文。シリーズの次回やフォローへの誘導。1〜3文）",
    "tags": ["タグ1", "タグ2", "タグ3", "タグ4", "タグ5"],
    "recommended_price": 300
  }}
}}"""


# ── API call ───────────────────────────────────────────────────────────────────

def call_gemini(prompt: str) -> dict:
    client   = get_client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    text = response.text.strip()

    # Strip markdown code fences if Gemini wrapped the JSON
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
        print("JSON parsing failed. Raw Gemini output:")
        print(text[:2000])
        raise RuntimeError("Gemini returned invalid JSON") from exc


# ── File naming ────────────────────────────────────────────────────────────────

def _today() -> str:
    return date.today().isoformat()


def next_path(stem: str, force: bool = False) -> Path:
    """
    Return DRAFTS_DIR/{stem}.md.
    If that already exists and force=False, try {stem}-2.md, {stem}-3.md, etc.
    If force=True, always return the base path (caller will overwrite).
    """
    base = DRAFTS_DIR / f"{stem}.md"
    if force or not base.exists():
        return base
    i = 2
    while True:
        candidate = DRAFTS_DIR / f"{stem}-{i}.md"
        if not candidate.exists():
            return candidate
        i += 1


def slugify_safe(text: str) -> str:
    """Ensure a Gemini-supplied slug is safe for filenames."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.ASCII)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-") or "draft"


# ── Markdown renderers ─────────────────────────────────────────────────────────

def render_free(data: dict, mode: str) -> str:
    today    = _today()
    title    = data.get("title", "（タイトル未設定）")
    slug     = slugify_safe(data.get("slug", "free-draft"))
    intro    = data.get("intro", "").strip()
    body     = data.get("body", "").strip()
    takes    = data.get("takeaways", "").strip()
    cta      = data.get("cta", "").strip()
    tags     = data.get("tags", [])
    tags_str = "　".join(f"#{t}" for t in tags)

    meta = (
        f"<!--\n"
        f"type: free\n"
        f"series: {SERIES_NAME}\n"
        f"topic_mode: {mode}\n"
        f"date: {today}\n"
        f"suggested_tags: {', '.join(tags)}\n"
        f"-->\n"
    )

    parts = [
        meta,
        f"# {title}\n",
        f"> **シリーズ:** {SERIES_NAME}｜無料記事\n",
        intro,
        "---",
        body,
        "---",
        f"## まとめ・気づき\n\n{takes}",
        "---",
        cta,
        "---",
        tags_str,
    ]
    return "\n\n".join(p.strip() for p in parts if p.strip()) + "\n"


def render_paid(data: dict, mode: str) -> str:
    today    = _today()
    title    = data.get("title", "（タイトル未設定）")
    slug     = slugify_safe(data.get("slug", "paid-draft"))
    intro    = data.get("intro", "").strip()
    body     = data.get("body", "").strip()
    takes    = data.get("takeaways", "").strip()
    cta      = data.get("cta", "").strip()
    tags     = data.get("tags", [])
    price    = data.get("recommended_price", 300)
    tags_str = "　".join(f"#{t}" for t in tags)

    meta = (
        f"<!--\n"
        f"type: paid\n"
        f"series: {SERIES_NAME}\n"
        f"topic_mode: {mode}\n"
        f"recommended_price: ¥{price}\n"
        f"date: {today}\n"
        f"suggested_tags: {', '.join(tags)}\n"
        f"-->\n"
    )

    parts = [
        meta,
        f"# {title}\n",
        f"> **シリーズ:** {SERIES_NAME}｜有料記事｜推奨価格: ¥{price}\n",
        intro,
        "---",
        body,
        "---",
        f"## 実践チェックリスト\n\n{takes}",
        "---",
        cta,
        "---",
        tags_str,
    ]
    return "\n\n".join(p.strip() for p in parts if p.strip()) + "\n"


# ── Write drafts ───────────────────────────────────────────────────────────────

def write_pair(
    result:    dict,
    mode:      str,
    force:     bool = False,
    dry_run:   bool = True,
) -> tuple[Path, Path]:
    today = _today()

    free_slug = slugify_safe(result["free"].get("slug", "free-draft"))
    paid_slug = slugify_safe(result["paid"].get("slug", "paid-draft"))

    free_stem = f"{today}-free-{free_slug}"
    paid_stem = f"{today}-paid-{paid_slug}"

    free_path = next_path(free_stem, force=force)
    paid_path = next_path(paid_stem, force=force)

    free_md = render_free(result["free"], mode)
    paid_md = render_paid(result["paid"], mode)

    if not dry_run:
        DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
        free_path.write_text(free_md, encoding="utf-8")
        paid_path.write_text(paid_md, encoding="utf-8")

    return free_path, paid_path


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate two Japanese note drafts (free + paid) using Gemini"
    )
    parser.add_argument("--write",       action="store_true", help="Call Gemini and save drafts (default: dry run)")
    parser.add_argument("--force",       action="store_true", help="Overwrite today's files instead of creating numbered versions")
    parser.add_argument("--mode",        default=None,        choices=list(MODES), help="Topic mode (auto-picked from weekday if omitted)")
    parser.add_argument("--topic-free",  default=None,        help="Override free article topic")
    parser.add_argument("--topic-paid",  default=None,        help="Override paid article topic")
    parser.add_argument("--list-modes",  action="store_true", help="List all available topic modes and exit")
    args = parser.parse_args()

    if args.list_modes:
        print("\nAvailable topic modes:\n")
        for key, m in MODES.items():
            weekday = "（平日: " + ["月","火","水","木","金","土","日"][_WEEKDAY_MODES.index(key) if key in _WEEKDAY_MODES else 0] + "）"
            print(f"  {key:<18}  {m['label']}  —  {m['description']}")
        print()
        return

    dry_run = not args.write

    mode       = args.mode or auto_mode()
    m          = MODES[mode]
    free_topic = args.topic_free or m["free_default"]
    paid_topic = args.topic_paid or m["paid_default"]
    today      = _today()

    print("Travel Now — Note Draft Generator")
    print("─" * 52)
    print(f"  Series    : {SERIES_NAME}")
    print(f"  Mode      : {mode}  ({m['label']})")
    print(f"  Free topic: {free_topic}")
    print(f"  Paid topic: {paid_topic}")
    print(f"  Date      : {today}")
    if dry_run:
        print("\n  Dry run — pass --write to call Gemini and save drafts.")
        print("─" * 52)
        print()
        print("Prompt that would be sent:\n")
        print(build_prompt(mode, free_topic, paid_topic))
        return

    print("\n  Calling Gemini (gemini-2.5-flash)…")

    try:
        prompt = build_prompt(mode, free_topic, paid_topic)
        result = call_gemini(prompt)
    except Exception as exc:
        print(f"\n  Error: {exc}")
        sys.exit(1)

    if "free" not in result or "paid" not in result:
        print("  Error: Gemini response missing 'free' or 'paid' keys.")
        print("  Raw keys:", list(result.keys()))
        sys.exit(1)

    free_path, paid_path = write_pair(result, mode, force=args.force, dry_run=False)

    print("  Done.\n")
    print("─" * 52)
    print(f"  FREE  →  {free_path}")
    print(f"  PAID  →  {paid_path}")
    print("─" * 52)
    print()
    print(f"  Free title : {result['free'].get('title', '')}")
    print(f"  Paid title : {result['paid'].get('title', '')}")
    price = result["paid"].get("recommended_price", 300)
    print(f"  Paid price : ¥{price}")
    tags_f = result["free"].get("tags", [])
    tags_p = result["paid"].get("tags", [])
    print(f"  Free tags  : {', '.join(tags_f)}")
    print(f"  Paid tags  : {', '.join(tags_p)}")
    print()
    print("  Next: review drafts → post manually to note → do NOT use automated posting.")


if __name__ == "__main__":
    main()
