"""One label per article, one archive section per label.

Article eyebrow labels had drifted into 44 variants — "City Guide" and "City
guide", "Travel Safety" and "Travel safety", five names for eSIM articles, and
catch-alls like "Honest guide" that said nothing about the subject. This is the
single vocabulary: the article hero label, the JSON-LD articleSection, the
archive grouping and the homepage cards all read from here.
"""
from __future__ import annotations

# canonical label -> archive section
SECTION = {
    "Itinerary": "Destinations & itineraries",
    "City guide": "Destinations & itineraries",
    "Getting around": "Destinations & itineraries",
    "When to go": "Destinations & itineraries",
    "Country profile": "Destinations & itineraries",
    "Stay": "Where to stay",
    "Cafés": "Food & drink",
    "Food": "Food & drink",
    "Booking & tours": "Booking, rail & flights",
    "Flights & hotels": "Booking, rail & flights",
    "Rail": "Booking, rail & flights",
    "Connectivity": "Connectivity",
    "Insurance": "Insurance",
    "Packing": "Packing, gear & airports",
    "Gear": "Packing, gear & airports",
    "Airport": "Packing, gear & airports",
    "Entry & arrival": "Entry, money & rules",
    "Money & costs": "Entry, money & rules",
    "Culture": "Culture & trip planning",
    "Trip planning": "Culture & trip planning",
}
SECTION_ORDER = [
    "Destinations & itineraries", "Where to stay", "Food & drink", "Booking, rail & flights", "Connectivity",
    "Insurance", "Packing, gear & airports", "Entry, money & rules",
    "Culture & trip planning",
]

# old label -> canonical label, where the old label was specific enough
FROM_OLD = {
    "Itinerary": "Itinerary", "Itineraries": "Itinerary",
    "City Guide": "City guide", "City guide": "City guide",
    "City Logistics": "Getting around", "Tokyo": "Getting around",
    "Seasonal guide": "When to go", "Seasonal": "When to go",
    "Country profile": "Country profile", "Country Profile": "Country profile",
    "Booking platforms": "Booking & tours", "Activities comparison": "Booking & tours",
    "Tours & Activities": "Booking & tours", "Booking guide": "Booking & tours",
    "Coastal Travel": "Booking & tours",
    "Flights": "Flights & hotels",
    "Rail & transport": "Rail", "Japan Rail": "Rail",
    "eSIM guide": "Connectivity", "Connectivity": "Connectivity", "eSIM": "Connectivity",
    "eSIM comparison": "Connectivity", "Connectivity comparison": "Connectivity",
    "eSIM & Connectivity": "Connectivity",
    "Travel insurance": "Insurance", "Travel Safety": "Insurance",
    "Travel safety": "Insurance", "Insurance": "Insurance", "Safety": "Insurance",
    "Packing": "Packing", "Carry-on Prep": "Packing", "Packing guide": "Packing", "Carry-on": "Packing",
    "Sun & Beach": "Packing", "Everyday Carry": "Packing",
    "Airport prep": "Airport",
    "Power": "Gear",
    "Flight": "Trip planning",
    "Travel economics": "Money & costs", "Travel money": "Money & costs",
    "Cross-Cultural Etiquette": "Culture", "Language & Culture": "Culture",
    "Where to stay": "Stay", "Hotels": "Stay", "Accommodation": "Stay",
    "Café": "Cafés", "Cafe": "Cafés", "Coffee": "Cafés",
    "Food & drink": "Food", "Food tours": "Food",
}

# per-article decisions where the old label was a catch-all
BY_SLUG = {
    "best-esim-japan-2026": "Connectivity",
    "best-esim-south-korea-2026": "Connectivity",
    "best-esim-usa-2026": "Connectivity",
    "best-travel-esim-2026": "Connectivity",
    "best-power-bank-travel-2026": "Gear",
    "best-travel-adapter-asia-2026": "Gear",
    "best-travel-insurance-2026": "Insurance",
    "is-travel-insurance-worth-it": "Insurance",
    "travel-insurance-japan": "Insurance",
    "day-trips-from-tokyo": "Itinerary",
    "klook-vs-kkday": "Booking & tours",
    # where-to-stay pillar (2026-09-24): hotel choice is its own decision
    "hotel-booking-sites-comparison": "Stay",
    "where-to-stay-in-tokyo": "Stay",
    "where-to-stay-in-london": "Stay",
    "osaka-or-kyoto-where-to-base": "Stay",
    "jr-pass-worth-it-2026": "Rail",
    "do-you-need-keta-south-korea": "Entry & arrival",
    "visit-japan-web-guide": "Entry & arrival",
    "how-much-cash-japan": "Money & costs",
    "how-much-does-south-korea-cost": "Money & costs",
    "japan-tax-free-shopping-2026-changes": "Money & costs",
    "japan-tourist-taxes-2026": "Money & costs",
    "is-travel-insurance-a-rip-off": "Insurance",
    "pre-flight-checklist-48-hours": "Airport",
    "first-international-trip-checklist": "Trip planning",
    "jet-lag-what-actually-works": "Trip planning",
    # "which cruise to book" guides: decisions about booking, not city guides
    "bangkok-river-cruises-guide": "Booking & tours",
    "sydney-harbour-cruises-guide": "Booking & tours",
    "hong-kong-harbour-cruises-guide": "Booking & tours",
    "halong-bay-cruises-from-hanoi": "Booking & tours",
    # 2026-10-10 demand articles
    "airport-security-liquids": "Packing",
    "airport-security-packing-moments": "Packing",
    "esim-activation-and-preparation": "Connectivity",
    "everyday-carry-essentials-for-travel": "Gear",
    "esim-vs-roaming-vs-physical-sim-when-each-wins": "Connectivity",
    "airport-security-liquid-rules-and-containers": "Packing",
    "power-bank-airplane-rules-and-limits": "Gear",
    "lost-luggage-recovery-strategy-first-48-hours": "Insurance",
    "hotel-room-physical-security-checklist": "Stay",
    "universal-travel-adapter-and-socket-guide": "Gear",
    "packing-cube-organization-system-guide": "Packing",
    "travel-insurance-selection-and-what-is-covered": "Insurance",
    "fatigue-management-on-long-haul-flights": "Trip planning",
    "luggage-weight-management-before-you-fly": "Packing",
    "direct-booking-vs-otas-hotel-guide": "Stay",
    # 2026-10-11 demand articles
    "where-to-stay-in-rome": "Stay",
    "where-to-stay-in-florence": "Stay",
    "where-to-stay-in-venice": "Stay",
    "where-to-stay-in-amsterdam": "Stay",
    "where-to-stay-in-barcelona": "Stay",
    "where-to-stay-in-madrid": "Stay",
    "where-to-stay-in-berlin": "Stay",
    "where-to-stay-in-vienna": "Stay",
    "where-to-stay-in-prague": "Stay",
    # 2026-10-12 city guides
    "where-to-stay-in-lisbon": "Stay",
    "where-to-stay-in-zurich": "Stay",
    "where-to-stay-in-edinburgh": "Stay",
    "where-to-stay-in-dublin": "Stay",
    "where-to-stay-in-vancouver": "Stay",
    "where-to-stay-in-montreal": "Stay",
    "where-to-stay-in-copenhagen": "Stay",
    "where-to-stay-in-stockholm": "Stay",
    "where-to-stay-in-new-york": "Stay",
    "where-to-stay-in-dubrovnik": "Stay",
    "where-to-stay-in-krakow": "Stay",
    "where-to-stay-in-nice": "Stay",
    "where-to-stay-in-mexico-city": "Stay",
    "where-to-stay-in-chiang-mai": "Stay",
    "where-to-stay-in-cancun": "Stay",
    "where-to-stay-in-da-nang": "Stay",
    "where-to-stay-in-phuket": "Stay",
    "where-to-stay-in-porto": "Stay",
    "where-to-stay-in-san-francisco": "Stay",
    "where-to-stay-in-las-vegas": "Stay",
    "where-to-stay-in-milan": "Stay",
    "where-to-stay-in-seville": "Stay",
    "where-to-stay-in-los-angeles": "Stay",
    "where-to-stay-in-athens": "Stay",
    "where-to-stay-in-honolulu": "Stay",
    "where-to-stay-in-budapest": "Stay",
    "where-to-stay-in-istanbul": "Stay",
    "where-to-stay-in-ho-chi-minh-city": "Stay",
    "where-to-stay-in-hanoi": "Stay",
    "where-to-stay-in-bali": "Stay",
    "where-to-stay-in-reykjavik": "Stay",
    # 2026-10-19 demand articles
    "best-travel-backpacks-2026-carry-on-size-limits-ergonomics-compared": "Gear",
    "how-to-avoid-international-roaming-fees-esim-vs-local-sim-vs-pocket-wifi": "Connectivity",
    "credit-card-foreign-transaction-fees-explained-best-cards-for-travel": "Money & costs",
    "how-to-recover-cancelled-or-delayed-flights-passenger-rights-compensation": "Flights & hotels",
    "jet-lag-protocol-science-backed-strategies-for-fast-adjustment": "Trip planning",
    # 2026-10-19 additional high-demand articles (anti-cannibalization)
    "solo-travel-safety-rules-10-practical-habits-for-safer-trips": "Insurance",
    "how-to-pack-fragile-souvenirs-and-liquids-in-checked-bags": "Packing",
    "digital-nomad-tax-visa-basics-90-day-schengen-and-nomad-permits": "Entry & arrival",
    "train-vs-flight-in-europe-when-rail-beats-flying-on-time-and-price": "Rail",
    "how-to-keep-valuables-safe-in-hostels-and-dorm-rooms": "Stay",
    "travel-medical-kit-essentials-what-actually-belongs-in-your-pouch": "Insurance",
    "how-to-choose-the-right-travel-shoes-walking-20000-steps-daily": "Gear",
    "airport-layover-survival-guide-making-long-transit-hours-bearable": "Airport",
    "smart-luggage-tracking-airtags-vs-tile-vs-smart-bag-rules": "Gear",
    "how-to-order-food-abroad-with-dietary-restrictions-allergies": "Food",
}

PAGE_LABEL = {                       # non-article pages that appear in the archive
    "countries/japan/index.html": "Country profile",
    "countries/vietnam/index.html": "Country profile",
    "countries/australia/index.html": "Country profile",
    "cities/tokyo/index.html": "City guide",
    "cities/tokyo/asakusa.html": "City guide",
}


def label_for(slug: str, old_label: str) -> str:
    """Canonical label for an article, from its slug and its current label."""
    if slug in BY_SLUG:
        return BY_SLUG[slug]
    old = old_label.split("·")[0].strip()
    if old in FROM_OLD:
        return FROM_OLD[old]
    if old in SECTION:
        return old
    raise KeyError(f"no canonical label for {slug!r} (was {old_label!r}) — add it to site_taxonomy")


def section_for(label: str) -> str:
    return SECTION[label]
