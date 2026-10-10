import os

files_to_complete = [
    "site/articles/where-to-stay-in-amsterdam.html",
    "site/articles/where-to-stay-in-barcelona.html",
    "site/articles/where-to-stay-in-berlin.html",
    "site/articles/where-to-stay-in-florence.html",
    "site/articles/where-to-stay-in-madrid.html",
    "site/articles/where-to-stay-in-prague.html",
    "site/articles/where-to-stay-in-rome.html",
    "site/articles/where-to-stay-in-venice.html",
    "site/articles/where-to-stay-in-vienna.html",
]

closing_tags = '''<!-- BEGIN gy-reveal (managed by add_reveal_script.py) -->
<script defer="" src="../js/gy-reveal.js?v=626be154"></script>
<!-- END gy-reveal -->
</body>
</html>
'''

for file_path in files_to_complete:
    try:
        with open(file_path, "r") as f:
            content = f.read()

        if not content.strip().endswith("</body>\n</html>"):
            # Ensure we only add if it's not already there or partially there
            if not "</body>" in content and not "</html>" in content:
                content += closing_tags
            elif "</body>" in content and not "</html>" in content:
                content += "</html>\n"
            elif not "</body>" in content and "</html>" in content:
                content += "</body>\n"

            with open(file_path, "w") as f:
                f.write(content)
            print(f"Completed: {file_path}")

            # Also copy to docs/
            docs_path = file_path.replace("site/", "docs/")
            os.makedirs(os.path.dirname(docs_path), exist_ok=True)
            with open(docs_path, "w") as f_docs:
                f_docs.write(content)
            print(f"Copied to: {docs_path}")
        else:
            print(f"Already complete: {file_path}")
            # Ensure docs/ is also in sync even if site/ is complete
            docs_path = file_path.replace("site/", "docs/")
            os.makedirs(os.path.dirname(docs_path), exist_ok=True)
            with open(file_path, "r") as f_site:
                site_content = f_site.read()
            with open(docs_path, "w") as f_docs:
                f_docs.write(site_content)
            print(f"Ensured docs sync for: {file_path}")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
