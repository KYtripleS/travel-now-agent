# Variant pin patterns — waves 2 and 3

Each article should produce 3–5 pins over time (different photo, different
title angle, different keyword cluster). This file lists the next two
variants per article so we can generate them in batches.

Generation: I will create one variant pin per article when you say go, using
a different Pexels photo and a different title angle. We post wave 2 in week
3–4 (after the wave-1 pins from `pins.csv` are uploaded) and wave 3 in week
6–8.

---

## Why this works

- Pinterest's algorithm rewards "fresh content" — same article, different
  pin design counts as fresh.
- A single article can rank for 10–20 different search queries. Each variant
  targets a different one.
- Wave 1 (already produced) leads with the brand format. Waves 2 and 3 try
  different hooks to find the angle that converts.

---

## Variant angles (the three "hooks" we rotate)

| Wave | Hook | Example title pattern |
|------|------|----------------------|
| 1 (done) | Editorial / authoritative | "Japan Country Profile: History, Geography & Travel Prep" |
| 2 | Quick-start / curiosity | "Going to Japan? 8 Things Worth Knowing Before You Go" |
| 3 | List / number-led | "Japan in 8 Sections: A Layered Guide for Thoughtful Travelers" |

Pinterest searchers respond differently to each hook. Number-led titles
(wave 3) usually win on impressions; editorial titles (wave 1) win on
outbound clicks; curiosity titles (wave 2) win on saves.

---

## Wave 2 specs (ready to generate when you say go)

| slug | new pexels query | wave-2 title |
|------|-----------------|--------------|
| japan-photo | "Japan torii gate snow Mount Fuji" | Going to Japan? What to Know Before You Book |
| vietnam-photo | "Vietnam street food market Hanoi" | Planning a Vietnam Trip? Start Here |
| australia-photo | "Australia Uluru sunset outback" | Australia for First-Time Visitors: A Layered Guide |
| tokyo-photo | "Tokyo skyline Tokyo Tower dusk" | First Time in Tokyo? A Layered City Guide |
| asakusa-photo | "Asakusa Senso-ji night festival" | Asakusa Walking Guide: A Half-Day in Old Tokyo |
| airport-liquids-photo | "TSA liquids 100ml bottles flat lay" | 100ml Rule Cheat Sheet for Carry-On Liquids |
| carry-on-photo | "carry on suitcase open packing cubes" | The 4-Step Carry-On Order Airport Security Wants |
| beach-photo | "beach travel essentials sand straw bag" | What to Actually Pack for a Beach Trip |
| boat-day-photo | "Croatia coast turquoise water boat" | Renting a Boat for a Day in Europe (No License) |
| esim-photo | "international travel phone connectivity world map" | eSIM vs Roaming: A Simple Activation Guide |
| travel-edc-photo | "minimalist travel essentials flat lay neutral" | The Travel EDC That Actually Lives in Your Pocket |
| hotels-photo | "boutique hotel exterior facade Europe" | Booking.com vs Hotels.com vs Agoda: How to Decide |
| untranslatable-photo | "vintage map atlas languages globe" | Saudade, Komorebi, Hygge: What Travelers Take Home |
| etiquette-photo | "international travelers handshake greeting" | 12 Countries, 12 Etiquette Rules Worth Knowing |
| south-korea-photo | "Seoul Bukchon hanok village rooftops" | Seoul & Beyond: A Layered South Korea Guide |
| insurance-photo | "passport travel insurance document hand" | SafetyWing, World Nomads, Genki: Which Covers You |
| capsule-photo | "minimalist clothes packed neutral tones" | 10-Item Capsule for 2-Week International Trips |

---

## Wave 3 specs (after wave 2 lands)

| slug | new pexels query | wave-3 title |
|------|-----------------|--------------|
| japan-photo | "Kyoto bamboo grove path morning" | Japan in 8 Sections: History to Travel Prep |
| vietnam-photo | "Ho Chi Minh City motorbikes traffic" | Vietnam: 8 Things to Know Before You Visit |
| australia-photo | "Great Ocean Road coast Australia" | Australia: 8 Layers of a Country Profile |
| tokyo-photo | "Shinjuku night neon lights crowd" | Tokyo: 6 Districts, 1 First-Time Guide |
| asakusa-photo | "Nakamise Street paper lanterns Asakusa" | Asakusa: 4 Stops for a Half-Day Walk |
| airport-liquids-photo | "airport security tray phone laptop" | Airport Liquids: 6 Common Rejections to Avoid |
| carry-on-photo | "carry on bag overhead bin plane" | Carry-On Packing: 5 Mistakes That Slow You Down |
| beach-photo | "beach umbrella sunset palm tropical" | Beach Packing: 10 Items Most Travelers Forget |
| boat-day-photo | "yacht charter Mediterranean sunset" | 6 European Countries, 1 No-License Boat Day |
| esim-photo | "phone settings cellular eSIM activation" | eSIM Activation: 4 Steps, 10 Minutes, Done |
| travel-edc-photo | "everyday carry pocket items flat lay" | Travel EDC: 6 Items That Earn Their Pocket Space |
| hotels-photo | "hotel reception lobby check in" | Hotel Booking: 5 Mistakes That Cost You |
| untranslatable-photo | "old library books reading lamp" | 14 Words That Resist Translation — and Why |
| etiquette-photo | "diverse group of travelers cafe" | What Counts as Rude: 12 Countries Compared |
| south-korea-photo | "Korean street food Myeongdong night" | South Korea: 8 Layers Before Your First Trip |
| insurance-photo | "travel medical insurance hospital abroad" | Travel Insurance: How to Pick in 5 Minutes |
| capsule-photo | "wardrobe rack neutral colors minimalist" | Capsule Wardrobe: 10 Items, 3 Climates, 14 Days |

---

## How to generate a wave

```bash
# I will provide a small script that loops through the wave and runs
# generate_pin.py with each spec. For now, when you want wave 2 generated:
# 1. Tell me "generate wave 2"
# 2. I will run the script in this session, produce 17 new PNGs under
#    site/images/pinterest/{slug}-w2.png and update pins.csv with the new rows
# 3. Commit and push as normal
```
