#!/usr/bin/env python3
import os
from pathlib import Path

cities = [
    ("lisbon", "Lisbon (2026): Four Areas and 10 Hotels, Compared", "Lisbon's historic neighborhoods offer distinct atmospheres: Baixa for central walkability, Alfama for medieval charm, and Bairro Alto for nightlife."),
    ("zurich", "Zurich (2026): Three Areas and 10 Hotels, Compared", "Zurich combines lakeside beauty with financial district efficiency: Altstadt for historic winding streets, Enge for lakeside calm, and Zurich West for modern design."),
    ("edinburgh", "Edinburgh (2026): Two Areas and 10 Hotels, Compared", "Edinburgh splits into the medieval Old Town and the Georgian New Town, each offering striking architecture, dramatic castle views, and distinct boutique stays."),
    ("dublin", "Dublin (2026): Three Areas and 10 Hotels, Compared", "Dublin's compact center makes exploring easy: Temple Bar for lively pubs and culture, St. Stephen's Green for Georgian elegance, and Docklands for modern waterfront hotels."),
    ("vancouver", "Vancouver (2026): Three Areas and 10 Hotels, Compared", "Vancouver's neighborhoods balance ocean and mountain views: Downtown for central convenience, Yaletown for upscale dining, and West End for proximity to Stanley Park."),
    ("montreal", "Montreal (2026): Three Areas and 10 Hotels, Compared", "Montreal's cultural districts offer unique character: Old Montreal for historic stone facades, Downtown for museums and shopping, and Plateau Mont-Royal for bohemian cafes."),
    ("copenhagen", "Copenhagen (2026): Three Areas and 10 Hotels, Compared", "Copenhagen's design-forward districts shine: Indre By for historic central sights, Vesterbro for trendy food halls, and Nørrebro for multicultural indie cafes."),
    ("stockholm", "Stockholm (2026): Three Areas and 10 Hotels, Compared", "Stockholm's islands create distinct neighborhood feels: Gamla Stan for medieval alleyways, Norrmalm for shopping convenience, and Södermalm for creative indie culture."),
    ("new-york", "New York (2026): Four Areas and 15 Hotels, Compared", "New York's boroughs and neighborhoods demand careful planning: Midtown for first-timers near Broadway, SoHo for boutique style, and Williamsburg for creative culture."),
    ("reykjavik", "Reykjavik (2026): Three Areas and 10 Hotels, Compared", "Reykjavik's compact downtown is ultra-walkable: Laugavegur for shopping and dining, Old Harbour for whale watching tours, and Hallgrímskirkja area for quiet residential stays.")
]

template = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>Where to Stay in {title} | Gently Yonder</title>
<meta content="{description}" name="description"/>
<link href="https://gentlyyonder.com/articles/where-to-stay-in-{slug}.html" rel="canonical"/>
<link href="../style-v2.css" rel="stylesheet"/>
</head>
<body>
<nav aria-label="Primary" class="gy-topnav" data-gy-root="../"><div class="gy-topnav-inner"><a class="gy-topnav-brand" href="../index.html">Gently Yonder</a></div></nav>
<main id="main">
<header class="hero article-hero">
<h1>Where to Stay in {title}</h1>
<p class="subtitle">{description}</p>
</header>
<section class="article">
<p>Choose the best area for your stay in {slug}. Complete guide coming soon with Stay22 maps and hotel recommendations.</p>
</section>
</main>
<footer><p>Disclosure: Gently Yonder may earn from affiliate links.</p></footer>
</body>
</html>
"""

for slug, title, desc in cities:
    path = Path(f"site/articles/where-to-stay-in-{slug}.html")
    with open(path, "w") as f:
        f.write(template.format(slug=slug, title=title, description=desc))
    print(f"Created {path}")

    # Copy to docs
    docs_path = Path(f"docs/articles/where-to-stay-in-{slug}.html")
    docs_path.parent.mkdir(parents=True, exist_ok=True)
    with open(docs_path, "w") as f:
        f.write(template.format(slug=slug, title=title, description=desc))
    print(f"Copied to {docs_path}")
