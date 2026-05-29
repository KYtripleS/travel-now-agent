#!/usr/bin/env python3
"""
generate_draft.py

Generates long-form Markdown drafts from content_log.csv article candidates.
Saves drafts to content_drafts/{date}-{slug}.md

Each draft includes:
  - platform_suggestion (note / Medium / Substack / site)
  - title, intro, checklist body
  - CTA to the Travel Now Checklist Generator
  - suggested tags

Usage:
  python generate_draft.py              # list candidates (dry run)
  python generate_draft.py --write      # write all candidate drafts
  python generate_draft.py --slug esim  # match a single slug
  python generate_draft.py --force      # overwrite existing drafts
  python generate_draft.py --platform substack  # override platform for all
"""

import argparse
import csv
import re
from datetime import date
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────

CONTENT_LOG   = Path("data/content_log.csv")
DRAFTS_DIR    = Path("content_drafts")
CHECKLIST_URL = "https://kytriples.github.io/travel-now-agent/checklist-generator.html"
SITE_URL      = "https://kytriples.github.io/travel-now-agent/"

# ── Product catalog (mirrors products.csv) ─────────────────────────────────────

PRODUCTS: dict[str, list[tuple[str, str, str]]] = {
    "esim": [
        ("Travel SIM card",        "https://www.amazon.com/s?k=travel+sim+card+international&tag=packlightpick-20",  "Useful backup for staying connected abroad"),
        ("Portable Wi-Fi hotspot", "https://www.amazon.com/s?k=portable+wifi+hotspot+travel&tag=packlightpick-20",  "Useful when travelling with multiple devices or companions"),
    ],
    "packing": [
        ("Travel toiletry bag",    "https://www.amazon.com/s?k=travel+toiletry+bag&tag=packlightpick-20",           "Useful for keeping liquids and bathroom items easy to find"),
        ("Packing cubes",          "https://www.amazon.com/s?k=packing+cubes+travel&tag=packlightpick-20",          "Useful for separating clothes and organising your carry-on"),
        ("Cable organiser pouch",  "https://www.amazon.com/s?k=cable+organizer+pouch+travel&tag=packlightpick-20",  "Helps keep chargers and small tech accessories together"),
    ],
    "flight": [
        ("Travel pillow",          "https://www.amazon.com/s?k=travel+pillow+airplane&tag=packlightpick-20",        "May help make long flights more comfortable"),
        ("Eye mask and earplugs",  "https://www.amazon.com/s?k=travel+eye+mask+earplugs&tag=packlightpick-20",      "Simple tools for rest on overnight and long-haul flights"),
        ("Collapsible water bottle","https://www.amazon.com/s?k=collapsible+travel+water+bottle&tag=packlightpick-20","Useful after airport security and during long travel days"),
    ],
    "power": [
        ("Compact power bank",     "https://www.amazon.com/s?k=compact+power+bank+travel&tag=packlightpick-20",     "Useful for keeping devices charged on long travel days"),
        ("Universal travel adapter","https://www.amazon.com/s?k=universal+travel+adapter&tag=packlightpick-20",     "Helpful in countries with different plug types"),
        ("USB-C charging cable",   "https://www.amazon.com/s?k=usb+c+charging+cable+travel&tag=packlightpick-20",  "Keep a spare cable in your carry-on or personal item"),
    ],
    "safety": [
        ("Passport holder",        "https://www.amazon.com/s?k=passport+holder+travel&tag=packlightpick-20",        "Useful for keeping passport and boarding passes together"),
        ("RFID travel wallet",     "https://www.amazon.com/s?k=rfid+travel+wallet&tag=packlightpick-20",            "A simple way to organise cards, cash, and documents"),
        ("Luggage tag",            "https://www.amazon.com/s?k=luggage+tag+travel&tag=packlightpick-20",            "Helpful for identifying bags and adding contact information"),
    ],
}

# ── Platform defaults by category ──────────────────────────────────────────────

PLATFORM_BY_CATEGORY: dict[str, str] = {
    "eSIM":           "Substack",
    "EDC":            "note",
    "Carry-on":       "Medium",
    "Flight Comfort": "Medium",
    "Power":          "note",
    "Travel Safety":  "Substack",
    "Camera":         "Medium",
    "Brand":          "note",
}

# Platform-specific writing hints shown in each draft
PLATFORM_HINTS: dict[str, str] = {
    "note":     "> **Platform:** note · Keep it short — lead with the hook, pick 2–3 checklist items, end with the CTA. Aim under 600 words.",
    "Medium":   "> **Platform:** Medium · Use all sections. Add a cover image and a subtitle. Front-load the value — the first 3 sentences show in preview.",
    "Substack": "> **Platform:** Substack · Open with a personal note or quick observation before the intro. Treat it like a letter to a subscriber.",
    "site":     "> **Platform:** Travel Now site · Convert to HTML via generate_article.py, or adapt the structure to match existing articles.",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


def csv_rows(path: Path, encoding: str = "utf-8-sig") -> list[dict]:
    with path.open(newline="", encoding=encoding) as f:
        return list(csv.DictReader(f))


def load_candidates() -> list[dict]:
    """Read content_log.csv, keep article_candidate=yes rows, deduplicate by slug."""
    if not CONTENT_LOG.exists():
        return []
    rows = csv_rows(CONTENT_LOG)
    candidates = [r for r in rows if r.get("article_candidate", "").strip().lower() == "yes"]
    by_slug: dict[str, dict] = {}
    for row in candidates:
        slug = slugify(row.get("topic", ""))
        if not slug:
            continue
        existing = by_slug.get(slug)
        if existing is None or row.get("date", "") >= existing.get("date", ""):
            by_slug[slug] = row
    return [{"slug": s, **r} for s, r in by_slug.items()]


def platform_for(category: str, override: str | None = None) -> str:
    if override:
        return override.capitalize()
    return PLATFORM_BY_CATEGORY.get(category, "Medium")


def tags_for(category: str, topic: str) -> list[str]:
    base = ["travel", "travel-prep"]
    cat_tags: dict[str, list[str]] = {
        "eSIM":           ["esim", "connectivity", "travel-tech", "digital-nomad"],
        "EDC":            ["everyday-carry", "edc", "travel-essentials", "minimalist-travel"],
        "Carry-on":       ["carry-on", "airport-security", "packing", "travel-tips"],
        "Flight Comfort": ["flight", "long-haul", "flight-comfort", "travel-tips"],
        "Power":          ["power-bank", "travel-tech", "charging", "travel-essentials"],
        "Travel Safety":  ["travel-safety", "passport", "travel-essentials"],
        "Camera":         ["travel-photography", "camera-gear", "travel-tech"],
    }
    topic_lower = topic.lower()
    extra: list[str] = []
    if "liquid" in topic_lower:
        extra = ["liquids", "tsa", "carry-on-liquids"]
    elif "packing moment" in topic_lower:
        extra = ["airport", "packing-system", "carry-on-tips"]
    return base + cat_tags.get(category, []) + extra


# ── Shared blocks ──────────────────────────────────────────────────────────────

def _products_block(keys: list[str]) -> str:
    lines = [
        "## Useful items to consider\n",
        "*These are optional ideas based on common travel needs — not requirements. "
        "Links are affiliate links. Travel Now may earn a small commission "
        "at no extra cost to you.*\n",
    ]
    for key in keys:
        for name, url, desc in PRODUCTS.get(key, []):
            lines.append(f"- **[{name}]({url})** — {desc}")
    return "\n".join(lines)


def _cta_block() -> str:
    return (
        "## Build your personalised trip checklist\n\n"
        "The steps above are a starting point. For a full checklist tailored to your destination, "
        "travel style, trip length, and flight time:\n\n"
        f"**[→ Travel Now Checklist Generator]({CHECKLIST_URL})**\n\n"
        "_Covers: before you fly, documents & money, packing, connectivity, "
        "flight comfort, and safer trip prep._"
    )


# ── Content builders ───────────────────────────────────────────────────────────

def _draft_esim(slug: str, row: dict) -> dict:
    title    = "How to Set Up Mobile Data Before You Land: An eSIM Prep Checklist"
    platform = platform_for("eSIM")
    tags     = tags_for("eSIM", row.get("topic", ""))

    intro = (
        "Landing abroad with no phone data used to mean queuing at airport phone shops, "
        "guessing which plan was worth it, and overpaying for convenience. eSIM has changed "
        "this significantly — but only if you do the prep before you board, not after you land.\n\n"
        "This is a straightforward pre-flight checklist for getting your phone data sorted. "
        "It covers what to check, what to choose, and what to save offline so the first few "
        "minutes after arrival are less stressful.\n\n"
        "No technical background needed. Just a bit of time before your trip."
    )

    body = """\
## Step 1 — Check if your phone supports eSIM

Not all phones support eSIM. Before planning anything else:

- Open your phone settings and search for "eSIM" or "Add mobile plan"
- On iPhone: **Settings → Cellular → Add eSIM**
- On Android: **Settings → Network → SIM → Add eSIM** (path varies by manufacturer)
- If you don't see an eSIM option, a physical SIM card is the alternative

Many phones sold through certain carriers are eSIM-locked. Confirm your phone is unlocked before purchasing a plan.

---

## Step 2 — Research options before departure

Data plan quality varies significantly by country and provider. A quick search of "[destination] eSIM" or "[destination] tourist SIM" shows the main options. Things to compare:

- Coverage in your specific destination — not just major cities
- Price per GB vs. daily plans — know which your usage pattern needs
- Validity window — some plans start from purchase, others from first activation
- Whether tethering (sharing data with other devices) is included

Popular travel eSIM services include Airalo, Holafly, and Nomad. Coverage and pricing vary by region — worth comparing a few options.

---

## Step 3 — Install and test before you board

Once you've purchased a plan:

- Install the eSIM while on Wi-Fi — most require a connection to download
- Set the eSIM as your data SIM; keep your home SIM for calls and SMS if needed
- **Disable automatic data roaming on your home SIM** to avoid unexpected charges
- Confirm the eSIM shows as active in your network settings
- Save the QR code or activation email accessible offline (or on another device) in case support is needed

---

## Step 4 — Save these offline before you board

Assume you'll have no data for the first 15–20 minutes after landing. Save before you board:

- Full address of your accommodation (street address, not just the hotel name)
- Airport transfer instructions or taxi booking confirmation
- Local emergency services number for your destination
- Any border or entry confirmation numbers
- Screenshot of your eSIM activation confirmation

---

## Step 5 — Physical SIM as a backup

If eSIM isn't available for your destination or your phone model:

- Buy a physical travel SIM before departure if a known provider covers your route
- Airport SIMs are convenient but usually more expensive than pre-purchased options
- Keep your original SIM somewhere safe — it's easy to misplace

---

## A note on speed and limitations

Travel data plans are suited to maps, messaging, and light browsing. They are generally not designed for large file transfers, video calls on poor connections, or streaming at full speed. Set realistic expectations for what you'll use data for, and choose a plan to match."""

    products = _products_block(["esim", "power"])
    return dict(title=title, platform=platform, tags=tags,
                intro=intro, body=body, products=products, slug=slug, row=row)


def _draft_edc(slug: str, row: dict) -> dict:
    title    = "The 6 Items Worth Carrying Every Travel Day Abroad"
    platform = platform_for("EDC")
    tags     = tags_for("EDC", row.get("topic", ""))

    intro = (
        "A well-thought-out everyday carry for travel days doesn't need to be heavy or "
        "complicated. Most common problems on days spent out of your accommodation — dead phone, "
        "lost card, nowhere to refill water — have simple solutions that weigh almost nothing.\n\n"
        "This is a short practical list for city days, transit days, and day trips. "
        "Not a full packing guide. Just the items that tend to be useful most often."
    )

    body = """\
## 1. Compact power bank

Your phone is your map, translator, boarding pass, and contact point. A small power bank "
(10,000 mAh covers most day trips) means a dead battery isn't a problem.

Charge it the night before. Carry the cable too. Keep both in the same pouch so you don't leave one behind.

---

## 2. A reusable or collapsible water bottle

Buying bottled water several times a day adds up and creates unnecessary waste. A collapsible bottle packs flat and is useful from the moment you clear airport security onwards.

Fill it at your accommodation each morning. In destinations where tap water is safe to drink, use that.

---

## 3. Local currency — a small working amount

Cards work in most destinations but not everywhere. Street food vendors, local markets, small transit options, and tip situations often require cash. Carrying a working amount of local currency covers these without needing to find an ATM mid-day.

Keep a small amount in a pocket, separate from your main wallet.

---

## 4. Your passport or required ID

In many countries, carrying identification is a legal requirement. Know your destination's rules before assuming a phone photo is sufficient.

A passport holder keeps it flat, accessible, and alongside a transit card or hotel key card.

---

## 5. A short cable and adapter

A short cable in your bag lets you charge from a cafe, airport, or transit hub USB port without hunting for a shop. A universal adapter means you're not stuck when your charger plug doesn't fit the local socket.

Both are small enough to forget until you need them.

---

## 6. A light layer for unexpected weather

A packable rain layer or small umbrella adds almost nothing to your carry weight and covers the most common unexpected situation: rain when you've dressed for sun.

Shoulder seasons especially have unpredictable weather. A compact layer is easier to carry than to find in a tourist area at short notice.

---

## What this isn't

This list covers the most common problems on travel days. It isn't a complete guide to medication, allergies, destination-specific requirements, or health-related items. Always check destination-specific official guidance and carry what your situation specifically requires."""

    products = _products_block(["power", "safety"])
    return dict(title=title, platform=platform, tags=tags,
                intro=intro, body=body, products=products, slug=slug, row=row)


def _draft_liquids(slug: str, row: dict) -> dict:
    title    = "The Carry-On Liquids System That Works at Security"
    platform = platform_for("Carry-on")
    tags     = tags_for("Carry-on", "airport security liquids")

    intro = (
        "Most airport security friction isn't caused by the liquid rules themselves — "
        "it's caused by not having a system for them. Liquids at the bottom of a bag. "
        "A full-size moisturiser packed at the last minute. A toiletry bag that takes three "
        "minutes to locate under the security lights.\n\n"
        "The rules are simple. The system that makes them easy to follow is what most "
        "advice skips. This is about that."
    )

    body = """\
## The rules, briefly

Security rules vary by country, airport, and airline route — and do change. The general framework in many countries:

- Liquids in containers of **100ml / 3.4 oz** or under
- All containers in a **single clear, resealable bag** (approximately 1 litre / 1 quart)
- **One bag per passenger**, removed from your carry-on at the checkpoint

Always check your specific airport's current rules before travelling. They are the authoritative source.

---

## The 4-step system

**Step 1 — Use travel-size containers for everything**

Decant what you need into travel-size bottles before you pack. Full-size products above the limit are confiscated regardless of how much is left in them.

**Step 2 — Pack everything in one clear bag**

One bag makes inspection fast. Spreading liquids across multiple pouches creates delays. This is the single most common mistake.

**Step 3 — Place the clear bag at the top of your carry-on**

At security, you'll remove it quickly. If it's at the bottom of a packed bag, you're repacking at the tray under pressure. Top of the bag, easy to reach.

**Step 4 — Know what counts as a liquid at your airport**

Items travellers often forget are classified as liquids: lip gloss, mascara, some deodorants, hair gel, certain food items like peanut butter and spreads. Check before packing anything borderline.

---

## What doesn't need to go in the liquids bag

Solid toiletries — shampoo bars, solid sunscreen, solid deodorant, bar soap — don't count as liquids in most checkpoints. This is worth knowing if your liquid allowance is tight. Solid alternatives are widely available and travel more easily.

---

## Pre-flight liquids check (5 minutes)

- [ ] All containers are 100ml / 3.4oz or under
- [ ] All containers fit in your clear bag, sealed
- [ ] Clear bag is at the very top of your carry-on
- [ ] Airport and airline rules confirmed for your specific route
- [ ] Full-size items left at home or moved to checked luggage

---

## The goal

You want to reach security, remove one bag in under 10 seconds, and move through without repacking or holding up the queue. That's achievable with 5 minutes of prep the night before you fly."""

    products = _products_block(["packing"])
    return dict(title=title, platform=platform, tags=tags,
                intro=intro, body=body, products=products, slug=slug, row=row)


def _draft_packing_moments(slug: str, row: dict) -> dict:
    title    = "Pack Your Carry-On By Airport Moment, Not By Category"
    platform = platform_for("Carry-on")
    tags     = tags_for("Carry-on", "airport security packing moments")

    intro = (
        "Most packing advice is organised by category: clothes here, tech there, toiletries "
        "somewhere else. That's a reasonable storage system. It's not always a useful system "
        "for travel days.\n\n"
        "A different approach: organise what you're packing by when you'll need it. "
        "Think through your airport journey in sequence — from leaving home to sitting in "
        "your seat — then pack backwards from that sequence.\n\n"
        "The result is a bag where the right thing is reachable at the right moment, "
        "without repacking under pressure."
    )

    body = """\
## The four airport moments

**Moment 1 — Getting to the airport**

What you need before you reach security:

- Passport or travel ID — outer pocket or top of bag, not buried
- Boarding pass — on your phone (charged) or printed and easy to reach
- Transport documents for getting to the airport
- Phone — accessible, battery above 50%, airline app open

These should be reachable without opening your main compartment.

---

**Moment 2 — Airport security**

What needs to come out at the checkpoint:

- Liquids bag — at the very top of your carry-on
- Laptop or tablet — in an accessible sleeve or top compartment if required at your airport
- Jacket, belt, and watch — not in your bag, but know where you'll put them in the tray

Packing tip: liquids bag at the top. Laptop in the section you can reach in one motion.

---

**Moment 3 — At the gate**

What you might want while waiting or immediately after boarding:

- Headphones or earbuds
- Snacks — particularly on early flights or long gate waits with limited food options nearby
- A light layer if the terminal is cold
- Refilled water bottle (filled after security)

These go in your **personal item** — the smaller bag that fits under the seat in front.

---

**Moment 4 — In the seat**

What you want without standing up:

- Charging cable (for the seat-back USB port or your power bank)
- Eye mask and earplugs on longer flights
- Lip balm and small moisturiser — cabin air is dry on any flight over 2 hours
- Neck pillow — attach to the outside of your bag rather than packing inside it

Everything else goes overhead.

---

## Why this works

Each item goes to the place that gets it to your hand at the right moment. What you need first should reach you first. What you need in the air can go to the bottom of the overhead bin.

This requires no special organiser or expensive gear. It's a packing sequence, not a product purchase.

---

## Common problems this prevents

- Unpacking half your carry-on at security to reach the liquids bag
- Headphones stuck in the overhead bin 10 minutes into the flight
- Boarding pass at the bottom of the bag at the gate scanner
- Water bottle inaccessible for the first hour of a long gate wait

---

## Pre-flight check

- [ ] Passport/ID reachable without opening the main compartment
- [ ] Boarding pass accessible on phone or in outer pocket
- [ ] Liquids bag at the top of the main compartment
- [ ] Laptop accessible for security if required at your airport
- [ ] In-flight essentials in your personal item or seat pocket
- [ ] Neck pillow clipped externally if you're bringing one"""

    products = _products_block(["packing", "flight"])
    return dict(title=title, platform=platform, tags=tags,
                intro=intro, body=body, products=products, slug=slug, row=row)


def _draft_generic(slug: str, row: dict) -> dict:
    """Fallback builder for categories without a dedicated template."""
    topic    = row.get("topic", "Travel preparation")
    category = row.get("category", "")
    title    = f"A Practical Checklist for {topic}"
    platform = platform_for(category)
    tags     = tags_for(category, topic)

    intro = (
        f"Good travel preparation for {topic.lower()} often comes down to a "
        "short checklist done a few days before departure — not a last-minute scramble "
        "at the airport. This guide covers the key steps to check off before you fly."
    )

    body = f"""\
## Before you leave home

- Check your passport validity and any visa requirements for your destination
- Confirm your airline's carry-on size and weight limits before packing
- Save booking confirmations and key addresses accessible offline
- Consider travel insurance that covers your trip type — read the policy details

---

## The prep checklist: {topic}

- [ ] Review any specific requirements for your destination
- [ ] Prepare or pack the items you'll need in advance
- [ ] Confirm transport, accommodation, and bookings before departure
- [ ] Let someone at home know your itinerary and how to reach you

---

## Quick reminder

Requirements and rules vary by destination, airline, and travel date. "
Always check official sources for visa rules, entry requirements, health guidance, "
and airline policies specific to your route before you travel."""

    product_key = {
        "eSIM": "esim", "EDC": "safety", "Carry-on": "packing",
        "Flight Comfort": "flight", "Power": "power", "Travel Safety": "safety",
    }.get(category, "packing")

    products = _products_block([product_key])
    return dict(title=title, platform=platform, tags=tags,
                intro=intro, body=body, products=products, slug=slug, row=row)


# ── Dispatcher ─────────────────────────────────────────────────────────────────

def build_draft(slug: str, row: dict, platform_override: str | None = None) -> dict:
    topic    = row.get("topic", "").lower()
    category = row.get("category", "")

    if "esim" in topic or category == "eSIM":
        data = _draft_esim(slug, row)
    elif "everyday carry" in topic or category == "EDC":
        data = _draft_edc(slug, row)
    elif "packing moment" in topic:
        data = _draft_packing_moments(slug, row)
    elif "liquid" in topic or ("security" in topic and "carry" in topic.replace("carry-on", "carry")):
        data = _draft_liquids(slug, row)
    else:
        data = _draft_generic(slug, row)

    if platform_override:
        data["platform"] = platform_override.capitalize()

    return data


# ── Markdown renderer ──────────────────────────────────────────────────────────

def render_markdown(data: dict) -> str:
    slug         = data["slug"]
    title        = data["title"]
    platform     = data["platform"]
    tags         = data["tags"]
    intro        = data["intro"]
    body         = data["body"]
    products     = data["products"]
    today        = date.today().isoformat()
    source_topic = data["row"].get("topic", slug)
    tags_str     = ", ".join(tags)

    meta = (
        f"<!--\n"
        f"platform_suggestion: {platform}\n"
        f"title: {title}\n"
        f"suggested_tags: {tags_str}\n"
        f"date: {today}\n"
        f"source_topic: {source_topic}\n"
        f"-->\n"
    )

    hint = PLATFORM_HINTS.get(platform, "")
    cta  = _cta_block()

    parts = [
        meta,
        f"# {title}\n",
        hint,
        intro,
        "---",
        body,
        "---",
        products,
        "---",
        cta,
        "---",
        f"*Tags: {tags_str}*",
    ]

    return "\n\n".join(p.strip() for p in parts if p.strip()) + "\n"


# ── File writer ────────────────────────────────────────────────────────────────

def write_draft(
    slug: str,
    markdown: str,
    force: bool = False,
    dry_run: bool = True,
) -> str:
    filename = f"{date.today().isoformat()}-{slug}.md"
    out_path = DRAFTS_DIR / filename
    existed  = out_path.exists()

    if existed and not force:
        return f"SKIPPED     {out_path}  (exists — use --force to overwrite)"

    if dry_run:
        action = "OVERWRITE" if existed else "CREATE"
        return f"{action}   (dry run)  {out_path}"

    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")
    action = "OVERWRITTEN" if existed else "CREATED"
    return f"{action}   {out_path}"


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate long-form Markdown drafts from content_log.csv article candidates"
    )
    parser.add_argument("--write",    action="store_true", help="Write draft files (default: dry run)")
    parser.add_argument("--force",    action="store_true", help="Overwrite existing drafts")
    parser.add_argument("--slug",     default=None,        help="Only generate the draft matching this slug substring")
    parser.add_argument("--platform", default=None,        help="Override platform suggestion (note/medium/substack/site)")
    args = parser.parse_args()

    dry_run = not args.write

    print("Travel Now — Draft Generator")
    print("─" * 52)

    if dry_run:
        print("  Dry run. Pass --write to save files.\n")

    candidates = load_candidates()
    if not candidates:
        print(f"  No article candidates found in {CONTENT_LOG}.")
        return

    if args.slug:
        candidates = [c for c in candidates if args.slug in c["slug"]]
        if not candidates:
            print(f"  No candidate matching slug fragment: {args.slug!r}")
            return

    created = skipped = overwritten = 0

    for candidate in candidates:
        slug = candidate["slug"]
        data = build_draft(slug, candidate, platform_override=args.platform)
        md   = render_markdown(data)

        status = write_draft(slug, md, force=args.force, dry_run=dry_run)

        if "SKIPPED" in status:
            skipped += 1
        elif "OVERWRITTEN" in status or "OVERWRITE" in status:
            overwritten += 1
        else:
            created += 1

        print(f"  {status}")
        print(f"    Topic    : {candidate.get('topic', '')}")
        print(f"    Platform : {data['platform']}")
        print(f"    Title    : {data['title']}")
        print(f"    Tags     : {', '.join(data['tags'][:5])}")
        print()

    print("─" * 52)

    if dry_run:
        total = created + skipped + overwritten
        print(f"  {total} candidate(s) found.")
        print(f"  {created} would be created, {overwritten} overwritten, {skipped} skipped.")
        print()
        print("  Write all drafts :")
        print("    python generate_draft.py --write")
        print()
        print("  Write a single draft:")
        print("    python generate_draft.py --write --slug esim")
        print()
        print("  Override platform:")
        print("    python generate_draft.py --write --platform medium")
    else:
        print(f"  {created} created, {overwritten} overwritten, {skipped} skipped.")
        if created or overwritten:
            print(f"  Saved to: {DRAFTS_DIR}/")


if __name__ == "__main__":
    main()
