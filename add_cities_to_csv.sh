#!/bin/bash
# Add new city where-to-stay entries to content_log.csv
# Format: date,platform,category,topic,post_text,cta,status,article_candidate,notes

# Use today's date (2026-10-12) as per system
DATE="2026-10-12"

# Array of entries: (slug, title, description)
CITIES=(
    "lisbon|Lisbon (2026): Four Areas and 10 Hotels, Compared|Lisbon's historic neighborhoods offer distinct atmospheres: Baixa for central walkability, Alfama for medieval charm, and Bairro Alto for nightlife."
    "zurich|Zurich (2026): Three Areas and 10 Hotels, Compared|Zurich combines lakeside beauty with financial district efficiency: Altstadt for historic winding streets, Enge for lakeside calm, and Zurich West for modern design."
    "edinburgh|Edinburgh (2026): Two Areas and 10 Hotels, Compared|Edinburgh splits into the medieval Old Town and the Georgian New Town, each offering striking architecture, dramatic castle views, and distinct boutique stays."
    "dublin|Dublin (2026): Three Areas and 10 Hotels, Compared|Dublin's compact center makes exploring easy: Temple Bar for lively pubs and culture, St. Stephen's Green for Georgian elegance, and Docklands for modern waterfront hotels."
    "vancouver|Vancouver (2026): Three Areas and 10 Hotels, Compared|Vancouver's neighborhoods balance ocean and mountain views: Downtown for central convenience, Yaletown for upscale dining, and West End for proximity to Stanley Park."
    "montreal|Montreal (2026): Three Areas and 10 Hotels, Compared|Montreal's cultural districts offer unique character: Old Montreal for historic stone facades, Downtown for museums and shopping, and Plateau Mont-Royal for bohemian cafes."
    "copenhagen|Copenhagen (2026): Three Areas and 10 Hotels, Compared|Copenhagen's design-forward districts shine: Indre By for historic central sights, Vesterbro for trendy food halls, and Nørrebro for multicultural indie cafes."
    "stockholm|Stockholm (2026): Three Areas and 10 Hotels, Compared|Stockholm's islands create distinct neighborhood feels: Gamla Stan for medieval alleyways, Norrmalm for shopping convenience, and Södermalm for creative indie culture."
    "new-york|New York (2026): Four Areas and 15 Hotels, Compared|New York's boroughs and neighborhoods demand careful planning: Midtown for first-timers near Broadway, SoHo for boutique style, and Williamsburg for creative culture."
    "reykjavik|Reykjavik (2026): Three Areas and 10 Hotels, Compared|Reykjavik's compact downtown is ultra-walkable: Laugavegur for shopping and dining, Old Harbour for whale watching tours, and Hallgrímskirkja area for quiet residential stays."
)

for entry in "${CITIES[@]}"; do
    IFS='|' read -r slug title desc <<< "$entry"
    echo "$DATE,X,Hotels,where-to-stay-in-$slug,$desc,no CTA,draft,yes,Good candidate for $title hotel guide" >> data/content_log.csv
done
