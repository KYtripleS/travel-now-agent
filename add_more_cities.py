#!/usr/bin/env python3
"""Add 10 new major world city Where to Stay guides to content_log.csv."""
import csv
from datetime import date

NEW_CITIES = [
    ("Where to Stay in Lisbon (2026): Four Areas and 10 Hotels, Compared", "Hotels", "Lisbon's historic neighborhoods offer distinct atmospheres: Baixa for central walkability, Alfama for medieval charm, and Bairro Alto for nightlife."),
    ("Where to Stay in Lisbon (2026)", "Lisbon is a city of hills and viewpoints. Baixa and Chiado put you in the vibrant center, Alfama offers cobbled historic lanes, and Estrela provides a quieter local residential feel."),
    ("Where to Stay in Lisbon (2026): Four Areas and 10 Hotels, Compared", "Lisbon's historic neighborhoods offer distinct atmospheres: Baixa for central walkability, Alfama for medieval charm, and Bairro Alto for nightlife."),
]

# Let's write a robust script that generates full, rich hotel guides for 10 new global cities:
# 1. Lisbon
# 2. Kyoto (already have some, let's do Zurich)
# 3. Zurich
# 4. Edinburgh
# 5. Dublin
# 6. Vancouver
# 7. Toronto
# 8. Montreal
# 9. Singapore (already have, let's do Kyoto expansion / New York)
# Let's pick 10 major global cities with NO cannibalization:
# - lisbon
# - zurich
# - edinburgh
# - dublin
# - vancouver
# - montreal
# - copenhagen
# - stockholm
# - vienna (already added in CSV, let's check if file exists)
# - prague (already added in CSV)

# Let's check what CSV rows we need to add:
CITIES_DATA = [
    ("where-to-stay-in-lisbon", "Lisbon's historic neighborhoods offer distinct atmospheres: Baixa for central walkability, Alfama for medieval charm, and Bairro Alto for nightlife."),
    ("where-to-stay-in-zurich", "Zurich combines lakeside beauty with financial district efficiency: Altstadt for historic winding streets, Enge for lakeside calm, and Zurich West for modern design."),
    ("where-to-stay-in-edinburgh", "Edinburgh splits into the medieval Old Town and the Georgian New Town, each offering striking architecture, dramatic castle views, and distinct boutique stays."),
    ("where-to-stay-in-dublin", "Dublin's compact center makes exploring easy: Temple Bar for lively pubs and culture, St. Stephen's Green for Georgian elegance, and Docklands for modern waterfront hotels."),
    ("where-to-stay-in-vancouver", "Vancouver's neighborhoods balance ocean and mountain views: Downtown for central convenience, Yaletown for upscale dining, and West End for proximity to Stanley Park."),
    ("where-to-stay-in-montreal", "Montreal's cultural districts offer unique character: Old Montreal for historic stone facades, Downtown for museums and shopping, and Plateau Mont-Royal for bohemian cafes."),
    ("where-to-stay-in-copenhagen", "Copenhagen's design-forward districts shine: Indre By for historic central sights, Vesterbro for trendy food halls, and Nørrebro for multicultural indie cafes."),
    ("where-to-stay-in-stockholm", "Stockholm's islands create distinct neighborhood feels: Gamla Stan for medieval alleyways, Norrmalm for shopping convenience, and Södermalm for creative indie culture."),
    ("where-to-stay-in-new-york", "New York's boroughs and neighborhoods demand careful planning: Midtown for first-timers near Broadway, SoHo for boutique style, and Williamsburg for creative culture."),
    ("where-to-stay-in-reykjavik", "Reykjavik's compact downtown is ultra-walkable: Laugavegur for shopping and dining, Old Harbour for whale watching tours, and Hallgrímskirkja area for quiet residential stays."),
]

print("City data prepared.")
