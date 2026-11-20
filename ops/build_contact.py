"""Contact page (2026-11-20: a reader should be able to see who runs the
site and how to reach it). Writes contact.html to site/ and docs/ and adds it to the sitemap.

Every channel listed must really work: an email address appears only when data/contact.json has
one that the operator has set up and tested. Ownership is described as it is: independently owned,
written under pen names, no outside funder.

usage: .venv/bin/python ops/build_contact.py
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import build_library as L  # noqa: E402

CONF = json.loads((REPO / "data" / "contact.json").read_text())
URL = "https://gentlyyonder.com/contact.html"


def channels() -> str:
    rows = []
    if CONF.get("email"):
        e = html.escape(CONF["email"])
        rows.append(f'<li><strong>Email:</strong> <a href="mailto:{e}">{e}</a>. Corrections, questions, '
                    f'partnership enquiries and requests about your data.</li>')
    rows.append('<li><strong>X:</strong> <a href="https://x.com/GentlyYonder" rel="noopener" target="_blank">'
                '@GentlyYonder</a>. Send a direct message or mention us.</li>')
    return "\n".join(rows)


def render() -> str:
    ld = json.dumps({"@context": "https://schema.org", "@type": "ContactPage", "url": URL,
                     "name": "Contact Gently Yonder",
                     "about": {"@type": "Organization", "name": "Gently Yonder", "url": "https://gentlyyonder.com/",
                               "sameAs": ["https://x.com/GentlyYonder"],
                               **({"email": CONF["email"]} if CONF.get("email") else {})}})
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Contact Gently Yonder | Gently Yonder</title>
<meta name="description" content="How to reach Gently Yonder: corrections, questions, partnership enquiries and data requests, and who runs the site." />
<link rel="canonical" href="{URL}" />
<meta name="robots" content="index, follow" />
<link rel="stylesheet" href="style-v2.css" />
<script type="application/ld+json">{ld}</script>
{L.GA4}
<!-- BEGIN favicon (managed by add_favicon.py) -->
<link href="/favicon.svg" rel="icon" type="image/svg+xml"/>
<link href="/favicon-48.png" rel="icon" sizes="48x48" type="image/png"/>
<link href="/favicon-192.png" rel="icon" sizes="192x192" type="image/png"/>
<link href="/apple-touch-icon.png" rel="apple-touch-icon"/>
<!-- END favicon -->
</head>
<body>
{L._nav_block("")}
<header class="hero article-hero">
<p class="label">About</p>
<h1>Contact us</h1>
</header>
<main id="main">
<section class="article">
<p class="article-lede">Found an error, have a question about a guide, or want us to delete your newsletter
address? Tell us. We read every message.</p>
<h2>How to reach us</h2>
<ul>
{channels()}
</ul>
<p>Every correction we make is listed on our public <a href="corrections.html">corrections page</a>, with the
date and what changed.</p>
<h2>Who runs Gently Yonder</h2>
<p>Gently Yonder is an independent publication, started in 2026. It is privately owned, and no media
company, airline, hotel group or travel platform owns or funds it. We earn money from affiliate links,
and <a href="promise.html">our promise</a> sets out what that does and does not change.</p>
<p>Our writers publish under pen names, as <a href="editors.html">our editors page</a> says. That is a choice
to keep our private lives apart from the work, not a way to avoid answering for it: every guide lists
its sources, shows when it was last checked, and can be corrected through this page.</p>
<h2>Your data</h2>
<p>To have your newsletter address deleted, or to ask what we hold about you, contact us here.
<a href="privacy.html">Our privacy policy</a> explains what we collect.</p>
<p class="back-link"><a href="about.html">&larr; About Gently Yonder</a></p>
</section>
</main>
{L._footer_block("")}
<script defer src="js/gy-reveal.js"></script>
</body>
</html>
"""


def main() -> None:
    page = render()
    for root in (REPO / "site", REPO / "docs"):
        (root / "contact.html").write_text(page, encoding="utf-8")
        sm = root / "sitemap.xml"
        s = sm.read_text(encoding="utf-8")
        if f"<loc>{URL}</loc>" not in s:
            s = s.replace("</urlset>", f"  <url>\n    <loc>{URL}</loc>\n    <changefreq>monthly</changefreq>\n"
                                       f"    <priority>0.4</priority>\n  </url>\n</urlset>")
            sm.write_text(s, encoding="utf-8")
    print("contact page:", "email listed" if CONF.get("email") else "no email yet (X only)")


if __name__ == "__main__":
    main()
