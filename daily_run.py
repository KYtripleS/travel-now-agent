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


def main():
    print("Starting Travel Now daily workflow...")

    # 1. Generate X post candidates
    if Path("main.py").exists():
        run("python main.py")
    else:
        print("main.py not found. Skipping post generation.")

    # 2. Rebuild site from product data
    if Path("build_site.py").exists():
        run("python build_site.py")
    else:
        print("build_site.py not found. Skipping site build.")

    # 3. Show top posts
    show_file("top_posts.csv")

    # 4. Show git status
    run("git status")

    print("\nDaily workflow complete.")
    print("Next: choose one post, publish or save it, then commit any site changes if needed.")


if __name__ == "__main__":
    main()
