import csv
from pathlib import Path
from collections import defaultdict

PRODUCTS_CSV = Path("site/products.csv")
DOCS_INDEX = Path("docs/index.html")
SITE_INDEX = Path("site/index.html")

CATEGORY_IDS = {
    "eSIM & Connectivity": "esim",
    "Packing Essentials": "packing",
    "Flight Comfort": "flight",
    "Power & Charging": "power",
    "Travel Safety": "safety",
    "Camera Travel Gear": "camera",
    "Sun & Beach": "sunbeach",
    "Hotel Stay Comfort": "hotel",
}

CATEGORY_ICONS = {
    "eSIM & Connectivity": "📶",
    "Packing Essentials": "🎒",
    "Flight Comfort": "✈️",
    "Power & Charging": "🔋",
    "Travel Safety": "🛡️",
    "Camera Travel Gear": "📷",
    "Sun & Beach": "🌞",
    "Hotel Stay Comfort": "🏨",
}

CHECKLISTS = {
    "eSIM & Connectivity": [
        "Check if your phone supports eSIM",
        "Choose a data plan before departure",
        "Save setup instructions offline",
        "Keep your hotel address available without mobile data",
    ],
    "Packing Essentials": [
        "Use packing cubes to separate clothes",
        "Keep cables and chargers in one pouch",
        "Pack one change of clothes in your carry-on",
        "Keep passport, cards, and cash easy to reach",
    ],
    "Flight Comfort": [
        "Neck pillow or compact travel pillow",
        "Eye mask and earplugs",
        "Refillable water bottle after security",
        "Downloaded music, podcasts, or maps",
    ],
    "Power & Charging": [
        "Bring a compact power bank",
        "Pack the right plug adapter for your destination",
        "Keep one charging cable in your personal item",
        "Charge your phone before leaving the airport",
    ],
    "Travel Safety": [
        "Save digital copies of your passport and bookings",
        "Keep emergency cash separate from your wallet",
        "Write down your hotel address offline",
        "Check local emergency numbers before departure",
    ],
    "Camera Travel Gear": [
        "Pack one spare battery if you shoot often",
        "Use a small pouch for SD cards and cables",
        "Bring a lightweight strap for walking days",
        "Clean your lens before important photos",
    ],
    "Sun & Beach": [
        "Pack reef-safe sunscreen in travel-size bottles",
        "Bring a packable sun hat and polarized sunglasses",
        "Use a quick-dry microfiber towel for beach days",
        "Keep after-sun gel in your carry-on for evening relief",
    ],
    "Hotel Stay Comfort": [
        "Pack foldable slippers for the room",
        "Use a mesh laundry bag to separate dirty clothes",
        "Bring a universal sink stopper for hand-washing",
        "Add a portable door alarm for extra peace of mind",
    ],
}

INTRO_TEXT = {
    "eSIM & Connectivity": "Before you fly, consider preparing these:",
    "Packing Essentials": "A simple carry-on prep checklist:",
    "Flight Comfort": "Small items that may make long flights easier:",
    "Power & Charging": "Before your trip, check your charging setup:",
    "Travel Safety": "Simple prep that may reduce avoidable stress:",
    "Camera Travel Gear": "Useful ideas for lightweight travel shooting:",
    "Sun & Beach": "Small items that can make sunny destinations smoother:",
    "Hotel Stay Comfort": "Little extras that improve hotel stays:",
}


def read_products():
    products_by_category = defaultdict(list)

    with PRODUCTS_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            products_by_category[row["category"]].append(row)

    return products_by_category


def build_product_cards(products):
    cards = []

    for product in products:
        cards.append(f"""
        <article class="product-card">
          <h4>{product["item"]}</h4>
          <p>{product["description"]}</p>
          <a href="{product["url"]}" class="product-link" target="_blank" rel="nofollow sponsored noopener">View options</a>
        </article>""")

    return "\n".join(cards)


def build_section(category, products):
    icon = CATEGORY_ICONS[category]
    section_id = CATEGORY_IDS[category]
    checklist_items = "\n".join([f"        <li>{item}</li>" for item in CHECKLISTS[category]])
    product_cards = build_product_cards(products)

    return f"""
    <section class="list" id="{section_id}">
      <h2>{icon} {category}</h2>
      <p>{INTRO_TEXT[category]}</p>
      <ul>
{checklist_items}
      </ul>

      <h3>Starter picks to consider</h3>
      <div class="product-grid">
{product_cards}
      </div>
    </section>
"""


def replace_sections(html, generated_sections):
    start_marker = "    <!-- AUTO-GENERATED-SECTIONS-START -->"
    end_marker = "    <!-- AUTO-GENERATED-SECTIONS-END -->"

    start = html.find(start_marker)
    end = html.find(end_marker)

    if start == -1 or end == -1:
        raise ValueError("Auto-generation markers not found in index.html")

    before = html[: start + len(start_marker)]
    after = html[end:]

    return before + "\n" + generated_sections + "\n" + after


def main():
    products_by_category = read_products()

    generated_sections = "\n".join(
        build_section(category, products_by_category[category])
        for category in CATEGORY_IDS.keys()
    )

    html = SITE_INDEX.read_text(encoding="utf-8")
    updated_html = replace_sections(html, generated_sections)

    SITE_INDEX.write_text(updated_html, encoding="utf-8")
    DOCS_INDEX.write_text(updated_html, encoding="utf-8")

    print("Built site/index.html and docs/index.html from site/products.csv")


if __name__ == "__main__":
    main()
