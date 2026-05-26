import csv
import subprocess
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

    with top_posts.open(newline="", encoding="utf-8") as f:
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


def main():
    print("Starting Travel Now daily workflow...")

    # 1. Show recent posted content first to avoid repeating topics
    show_recent_content_log()

    # 2. Generate X post candidates
    if Path("main.py").exists():
        run("python main.py")
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

    print("\nDaily workflow complete.")
    print("Next: choose one non-repeated post, publish or save it, update content_log.csv, then commit changes if needed.")


if __name__ == "__main__":
    main()
