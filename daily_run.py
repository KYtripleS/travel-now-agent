import csv
import re
import subprocess
from datetime import date
from pathlib import Path


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

    # 8. Japanese note drafts — generate today's pair if not yet created
    show_note_drafts()

    print("\nDaily workflow complete.")
    print("Next: choose a post → publish → update content_log.csv → commit.")


if __name__ == "__main__":
    main()
