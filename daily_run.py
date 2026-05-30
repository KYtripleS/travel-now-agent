import csv
import re
import subprocess
from datetime import date
from pathlib import Path

# ── Money-path constants ───────────────────────────────────────────────────

CHECKLIST_URL = "https://kytriples.github.io/travel-now-agent/checklist-generator.html"
SITE_BASE_URL = "https://kytriples.github.io/travel-now-agent"

# Affiliate categories in monetization priority order
_PRIORITY_CATS = [
    "Packing Essentials",
    "eSIM & Connectivity",
    "Flight Comfort",
    "Power & Charging",
    "Travel Safety",
    "Camera Travel Gear",
]

# Map top-post category/topic keywords → affiliate category
_TOPIC_TO_CAT = {
    "carry-on": "Packing Essentials",
    "packing":  "Packing Essentials",
    "liquids":  "Packing Essentials",
    "edc":      "Packing Essentials",
    "everyday": "Packing Essentials",
    "esim":     "eSIM & Connectivity",
    "sim":      "eSIM & Connectivity",
    "data":     "eSIM & Connectivity",
    "wifi":     "eSIM & Connectivity",
    "flight":   "Flight Comfort",
    "comfort":  "Flight Comfort",
    "power":    "Power & Charging",
    "charging": "Power & Charging",
    "battery":  "Power & Charging",
    "safety":   "Travel Safety",
    "camera":   "Camera Travel Gear",
    "photo":    "Camera Travel Gear",
}

# Affiliate category → best existing article slug (for URL)
_CAT_TO_ARTICLE = {
    "Packing Essentials":  "airport-security-liquids",
    "eSIM & Connectivity": "esim-activation-and-preparation",
    "Flight Comfort":      "airport-security-packing-moments",
    "Travel Safety":       "everyday-carry-essentials-for-travel",
    "Power & Charging":    "everyday-carry-essentials-for-travel",
    "Camera Travel Gear":  "everyday-carry-essentials-for-travel",
}


def run(command):
    print(f"\n> {command}")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        raise SystemExit(f"Command failed: {command}")


def show_file(path):
    file_path = Path(path)
    if file_path.exists():
        print(f"\n--- {path} ---")
        print(file_path.read_text(encoding="utf-8"))
    else:
        print(f"\n{path} not found.")


def show_recent_content_log(path="data/content_log.csv", limit=5):
    log_path = Path(path)

    if not log_path.exists():
        print("\nNo content_log.csv found yet.")
        print("Tip: create data/content_log.csv to track posted content and avoid repeating topics.")
        return

    with log_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("\ncontent_log.csv exists, but it is empty.")
        return

    recent_rows = rows[-limit:]

    print("\n=== RECENT POSTED CONTENT ===")
    for row in recent_rows:
        date = row.get("date", "")
        platform = row.get("platform", "")
        category = row.get("category", "")
        topic = row.get("topic", "")
        status = row.get("status", "")
        article_candidate = row.get("article_candidate", "")

        print(f"- {date} | {platform} | {category} | {topic} | {status} | article: {article_candidate}")
    print("=============================")


def show_today_candidate(path="top_posts.csv"):
    top_posts = Path(path)

    if not top_posts.exists():
        print(f"\n{path} not found. Skipping today's candidate display.")
        return

    with top_posts.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print(f"\n{path} is empty.")
        return

    best = rows[0]

    print("\n=== TODAY'S POST CANDIDATE ===")
    print(f"Category: {best.get('category', '')}")
    print(f"Topic: {best.get('topic', '')}")
    print("\nPost:")
    print(best.get("post_text", ""))

    cta = best.get("cta", "")
    if cta:
        print("\nCTA:")
        print(cta)

    print("==============================")


def slugify(text):
    """Convert a topic string to a URL-friendly slug (mirrors generate_article.py)."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"-+", "-", text)
    return text


def show_revenue_actions(top_posts_path="top_posts.csv", content_log_path="data/content_log.csv"):
    """Show revenue-focused next actions at the end of the daily workflow."""

    print("\n" + "=" * 36)
    print("=== REVENUE ACTIONS             ===")
    print("=" * 36)

    # ── 1. Today's top post and whether it is an article candidate ────────────
    top_path = Path(top_posts_path)
    top_post = None

    if top_path.exists():
        with top_path.open(newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
            if rows:
                top_post = rows[0]

    if top_post:
        topic    = top_post.get("topic", "").strip()
        category = top_post.get("category", "").strip()
        score    = top_post.get("score", "?")
        print(f"\nToday's top post:   {topic}")
        print(f"Category / score:   {category}  |  score {score}")

        # Check if this topic is already in content_log as article_candidate
        log_path = Path(content_log_path)
        match_status = None  # None = not found, True = yes, False = no
        if log_path.exists():
            with log_path.open(newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row.get("topic", "").strip().lower() == topic.lower():
                        match_status = row.get("article_candidate", "").strip().lower() == "yes"
                        break

        if match_status is True:
            print("Article candidate:  YES — already marked in content_log.csv")
        elif match_status is False:
            print("Article candidate:  no — in content_log but not marked")
        else:
            print("Article candidate:  not in content_log.csv yet")
            print("                    → after posting, add a row and set article_candidate=yes if useful")
    else:
        print("\nNo top post data found — run main.py first.")

    # ── 2. All article candidates and which already have articles ─────────────
    log_path = Path(content_log_path)

    if not log_path.exists():
        print("\nNo content_log.csv found.")
        print("=" * 36)
        return

    with log_path.open(newline="", encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))

    # Deduplicate by slug, keeping the latest date (same logic as generate_article.py)
    by_slug: dict = {}
    for row in all_rows:
        if row.get("article_candidate", "").strip().lower() == "yes":
            slug = slugify(row["topic"])
            existing = by_slug.get(slug)
            if existing is None or row.get("date", "") >= existing.get("date", ""):
                by_slug[slug] = row

    print(f"\nArticle candidates in content_log.csv: {len(by_slug)}")

    if not by_slug:
        print("  (none — mark posts as article_candidate=yes to build this list)")
        print("=" * 36)
        return

    pending_slugs = []
    for slug, row in by_slug.items():
        exists = (Path("site/articles") / f"{slug}.html").exists()
        mark   = "✓" if exists else "○"
        label  = "article exists" if exists else "no article yet"
        print(f"  {mark}  {row['topic']:<42}  {label}")
        if not exists:
            pending_slugs.append(slug)

    # ── 3. Command suggestion ─────────────────────────────────────────────────
    print()
    if pending_slugs:
        print(f"  {len(pending_slugs)} candidate(s) still need articles.")
        print("\n  Next revenue action:")
        print("    python generate_article.py           # dry run — preview what would be created")
        print("    python generate_article.py --write   # generate the missing article drafts")
    else:
        print("  All article candidates have articles. ✓")
        print("\n  Next revenue action:")
        print("    Review and polish article drafts in site/articles/")
        print("    Then link them from your X posts and update content_log.csv")

    print("=" * 36)


def show_note_drafts():
    """Generate today's Japanese note drafts if none exist; otherwise show existing paths."""
    today      = date.today().isoformat()
    drafts_dir = Path("note_drafts")

    existing = sorted(drafts_dir.glob(f"{today}-*.md")) if drafts_dir.exists() else []
    # Exclude README.md from the listing
    existing = [p for p in existing if p.name != "README.md"]

    print("\n" + "=" * 36)
    print("=== NOTE DRAFTS (JP)             ===")
    print("=" * 36)

    if existing:
        print(f"\n  Today's note drafts ({len(existing)} file(s)):\n")
        for p in existing:
            label = "FREE" if "-free-" in p.name else "PAID" if "-paid-" in p.name else "    "
            print(f"    [{label}]  {p}")
        print()
        print("  To regenerate: python generate_note_draft.py --write --force")
        print("=" * 36)
        return

    if not Path("generate_note_draft.py").exists():
        print("\n  generate_note_draft.py not found. Skipping.")
        print("=" * 36)
        return

    print("\n  No note drafts found for today. Generating now…")
    print()
    result = subprocess.run("python generate_note_draft.py --write", shell=True)

    if result.returncode != 0:
        print("\n  Warning: note draft generation failed.")
        print("  Check GEMINI_API_KEY and try: python generate_note_draft.py --write")
        print("=" * 36)
        return

    created = sorted(p for p in drafts_dir.glob(f"{today}-*.md") if p.name != "README.md")
    if created:
        print(f"\n  Note drafts saved ({len(created)} file(s)):\n")
        for p in created:
            label = "FREE" if "-free-" in p.name else "PAID" if "-paid-" in p.name else "    "
            print(f"    [{label}]  {p}")
    print("=" * 36)


def show_money_path():
    """Print TODAY'S MONEY PATH — what to publish, where to send traffic,
    which affiliate category to promote, and a manual action checklist."""

    today_str = date.today().isoformat()
    divider   = "=" * 64

    print(f"\n{divider}")
    print("=== TODAY'S MONEY PATH                                      ===")
    print(divider)

    # ── Read top post ──────────────────────────────────────────────────────
    top_post: dict = {}
    top_path = Path("top_posts.csv")
    if top_path.exists():
        with top_path.open(newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
            if rows:
                top_post = rows[0]

    top_topic    = top_post.get("topic",    "").strip()
    top_category = top_post.get("category", "").strip()
    top_score    = top_post.get("score",    "?")
    top_text     = top_post.get("post_text","").strip()
    top_cta      = top_post.get("cta",      "").strip()

    # ── Pick affiliate category ────────────────────────────────────────────
    aff_cat = None
    needle  = (top_topic + " " + top_category).lower()
    for kw, cat in _TOPIC_TO_CAT.items():
        if kw in needle:
            aff_cat = cat
            break
    if aff_cat is None:
        # Rotate by weekday so each category gets a day
        aff_cat = _PRIORITY_CATS[date.today().weekday() % len(_PRIORITY_CATS)]

    # Count active links in chosen category
    aff_links: list = []
    aff_path = Path("affiliate_links.csv")
    if aff_path.exists():
        with aff_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("category", "") == aff_cat and row.get("status", "") == "active":
                    aff_links.append(row)

    article_slug = _CAT_TO_ARTICLE.get(aff_cat, "")
    article_url  = f"{SITE_BASE_URL}/articles/{article_slug}.html" if article_slug else ""

    # ── Scan note drafts ───────────────────────────────────────────────────
    note_dir = Path("note_drafts")
    note_free: Path | None = None
    note_paid: Path | None = None
    note_free_title = ""
    note_paid_title = ""

    if note_dir.exists():
        _skip = {"README.md", "TODAY_POSTING_GUIDE.md"}
        # Prefer today's drafts; fall back to most recent
        for pattern in (f"{today_str}-*.md", "*.md"):
            candidates = sorted(
                (p for p in note_dir.glob(pattern) if p.name not in _skip),
                reverse=True,
            )
            for p in candidates:
                text = p.read_text(encoding="utf-8")
                m    = re.search(r"<!--(.*?)-->", text, re.DOTALL)
                ntype = ""
                if m:
                    for line in m.group(1).splitlines():
                        if line.strip().startswith("type:"):
                            ntype = line.split(":", 1)[1].strip().lower()
                            break
                title_line = next(
                    (l[2:].strip() for l in text.splitlines() if l.strip().startswith("# ")),
                    p.stem,
                )
                if ntype == "free"  and note_free is None:
                    note_free, note_free_title = p, title_line
                if ntype == "paid"  and note_paid is None:
                    note_paid, note_paid_title = p, title_line
            if note_free or note_paid:
                break

    # ── Scan rendered videos ───────────────────────────────────────────────
    video_dir   = Path("rendered_videos")
    latest_mp4: Path | None = None
    posting_kit: Path | None = None

    if video_dir.exists():
        mp4s = sorted(video_dir.glob("*.mp4"), reverse=True)
        if mp4s:
            latest_mp4 = mp4s[0]
            slug = re.sub(r"\.mp4$", "", latest_mp4.name)
            slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", slug)
            kits = sorted(Path("video_scripts").glob(f"*{slug}*/posting_kit.md"))
            if kits:
                posting_kit = kits[0]

    # ── Section 1 : Primary destination ───────────────────────────────────
    print("\n📍  PRIMARY DESTINATION")
    print(f"    Checklist Generator  →  {CHECKLIST_URL}")
    if article_url:
        print(f"    Best article today   →  {article_url}")

    # ── Section 2 : Traffic actions ───────────────────────────────────────
    print("\n📣  TRAFFIC ACTIONS")

    # X post
    print("\n  [X / Twitter]")
    if top_post:
        print(f"    Topic:    {top_topic}  |  Category: {top_category}  |  Score: {top_score}")
        # Show first 3 non-empty lines of post
        lines = [l for l in top_text.splitlines() if l.strip()][:3]
        for line in lines:
            print(f"    {line}")
        if top_cta and top_cta.lower() != "no cta":
            print(f"    CTA:  {top_cta}")
        print(f"    → Add: Build your free trip checklist → {CHECKLIST_URL}")
    else:
        print("    No top post found — run python main.py first.")

    # note drafts
    print("\n  [note（日本語）]")
    if note_free:
        print(f"    FREE  →  {note_free}")
        print(f"             {note_free_title}")
    if note_paid:
        print(f"    PAID  →  {note_paid}  (¥300)")
        print(f"             {note_paid_title}")
    if not note_free and not note_paid:
        print("    No note drafts found — run python generate_note_draft.py --write")
    print(f"    CTA: noteの本文末に → チェックリストURL を入れる")
    print(f"         {CHECKLIST_URL}")

    # Video
    print("\n  [Short video]")
    if latest_mp4:
        ready = "✓ READY" if latest_mp4.exists() else "—"
        print(f"    {ready}  →  {latest_mp4}")
        if posting_kit:
            print(f"    Posting kit  →  {posting_kit}")
        print(f"    Upload to: YouTube Shorts · Instagram Reels · TikTok")
        print(f"    CTA: \"Build My Full Checklist → link in bio\"")
        print(f"         {CHECKLIST_URL}")
    else:
        print("    No rendered video found.")
        print("    → Run: python make_video.py")

    # ── Section 3 : Monetization route ────────────────────────────────────
    print("\n💰  MONETIZATION ROUTE")
    print(f"    Category today:   {aff_cat}  ({len(aff_links)} active link(s))")
    if aff_links:
        for lnk in aff_links[:2]:
            print(f"    Product:          {lnk['product_name']}")
            print(f"                      {lnk['amazon_url']}")
    if note_paid:
        print(f"    Paid note (¥300): {note_paid.name}")
        print( "    Strategy: post free note first → add paid CTA at the end")
    print( "    Disclosure:       Required on all posts with Amazon links.")
    print( "                      \"As an Amazon Associate I earn from qualifying purchases.\"")

    # ── Section 4 : Suggested CTAs ────────────────────────────────────────
    print("\n💬  SUGGESTED CTAs")
    print(f"    X:      \"Build a free personalised trip checklist →\"")
    print(f"            {CHECKLIST_URL}")
    print( "    note:   「旅行の準備チェックリストを無料で作れます →」")
    print(f"            {CHECKLIST_URL}")
    print( "    video:  \"Build My Full Checklist → link in bio\"")
    print(f"            {CHECKLIST_URL}")

    # ── Section 5 : Manual checklist ──────────────────────────────────────
    print("\n✅  MANUAL CHECKLIST — " + today_str)
    print("    [ ]  Post X thread (copy from top_posts.csv)")
    if note_free:
        print(f"    [ ]  Post free note article to note.com")
    if note_paid:
        print(f"    [ ]  Post / promote paid note article (¥300)")
    if latest_mp4:
        print(f"    [ ]  Upload Short: {latest_mp4.name}")
        print( "         → YouTube Shorts: youtube.com/upload")
        print( "         → Instagram Reels: instagram.com → + → Reel")
        print( "         → TikTok: tiktok.com/upload")
    print( "    [ ]  Log clicks/orders manually → affiliate_click_log.csv")
    print( "    [ ]  python update_content_log.py --write")

    print(f"\n{divider}")


def main():
    print("Starting Travel Now daily workflow...")

    # 1. Show recent posted content first to avoid repeating topics
    show_recent_content_log()

    # 2. Generate X post candidates (soft failure — workflow continues on error)
    if Path("main.py").exists():
        print("\n> python main.py")
        result = subprocess.run("python main.py", shell=True)
        if result.returncode != 0:
            print("  Warning: post generation failed. Check your GEMINI_API_KEY and dependencies.")
            print("  Continuing with existing top_posts.csv if available.")
    else:
        print("main.py not found. Skipping post generation.")

    # 3. Rebuild site from product data
    if Path("build_site.py").exists():
        run("python build_site.py")
    else:
        print("build_site.py not found. Skipping site build.")

    # 4. Show raw top posts
    show_file("top_posts.csv")

    # 5. Show today's recommended post in a clean format
    show_today_candidate()

    # 6. Show git status
    run("git status")

    # 7. Revenue actions — article pipeline status and next step suggestion
    show_revenue_actions()

    # 8. TODAY'S MONEY PATH — what to publish, where to send traffic, what to earn
    show_money_path()

    # 9. Japanese note drafts — generate today's pair if not yet created
    show_note_drafts()

    print("\nDaily workflow complete.")
    print("Next: choose a post → publish → update monetization_log.csv → commit.")


if __name__ == "__main__":
    main()
