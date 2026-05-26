import os
import json
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from google import genai

print("1. Starting Travel Now Agent with Gemini...")

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is missing. Check your .env file.")

client = genai.Client(api_key=api_key)


def load_recent_posts(path="data/content_log.csv", limit=10):
    log_path = Path(path)

    if not log_path.exists():
        return []

    df = pd.read_csv(log_path)

    if df.empty:
        return []

    recent = df.tail(limit)

    recent_items = []
    for _, row in recent.iterrows():
        date = row.get("date", "")
        category = row.get("category", "")
        topic = row.get("topic", "")
        status = row.get("status", "")
        post_text = str(row.get("post_text", "")).replace("\n", " ")

        recent_items.append(
            f"- {date} | {category} | {topic} | {status} | {post_text[:140]}"
        )

    return recent_items


recent_posts = load_recent_posts()

recent_posts_text = "No previous posts found."

if recent_posts:
    recent_posts_text = "\n".join(recent_posts)

prompt = f"""
Create 30 high-quality X/Twitter posts for an English travel affiliate account called Travel Now.

Brand:
Travel Now helps travelers prepare smoother trips with practical travel preparation checklists, travel gear, EDC picks, eSIMs, packing tools, flight comfort items, travel insurance, VPNs, hotel tools, tours, and camera gear.

Positioning:
Travel Now is not luxury travel, not backpacking, and not influencer travel.
It is a practical travel preparation media brand for normal people who want smoother trips, fewer mistakes, and less stress before and after flights.

Main content style:
- Checklist-led
- Before-you-fly preparation
- Mistake avoidance
- Simple travel systems
- Practical, saveable posts

Recently posted content to avoid repeating:
{recent_posts_text}

Important anti-repetition rule:
Do NOT create posts that are too similar to the recently posted content above.
Avoid repeating the same topic, same angle, same checklist, or same opening hook.
You may use the same broad category only if the angle is clearly different.

Better examples of different angles:
- If eSIM was already posted, do not write another basic eSIM activation checklist.
  Instead, you may write about saving hotel addresses offline, screenshotting QR codes, or checking roaming settings.
- If EDC was already posted, do not write another generic everyday carry checklist.
  Instead, you may write about airport-day pocket setup, day-trip bag setup, or small cash preparation.

Goal:
Attract English-speaking travelers and build trust first. A future travel setup checklist page may be used later, but most posts should be useful without asking for clicks.

Return only valid JSON. No markdown. No explanation.

JSON format:
[
  {{
    "topic": "...",
    "category": "...",
    "hook": "...",
    "post_text": "A complete X post with line breaks, ready to copy and paste. Do not include CTA here.",
    "cta": "no CTA",
    "score": 8,
    "status": "draft"
  }}
]

Very important:
- post_text must be a complete X/Twitter post.
- post_text must include line breaks.
- post_text should NOT sound like a product description.
- Do NOT write article-style titles.
- Do NOT include actual affiliate links.
- Do NOT pretend personal experience.
- Keep each post under 280 characters.
- Do NOT include CTA inside post_text.
- Keep CTA in the cta field only.
- Use "no CTA" in the cta field if the post does not need one.
- Only about 20% of posts should include a CTA.
- Do NOT use strong claims such as "protect your data", "travel insurance covers", "prevents DVT", "essential", "lifesaver", "guaranteed", or "non-negotiable".
- Use soft wording: "may help", "consider", "check your policy", "can make it easier".
- For medical, insurance, finance, VPN, and safety topics, avoid guarantees.
- For VPN topics, focus on privacy habits and safer browsing, not bypassing restrictions.
- Avoid generic marketing phrases like "unlock better deals", "your best companion", "travel smarter".
- Make the post useful even without clicking a link.
- Use practical, sharp, simple English.
- Prefer checklist-style, mistake-avoidance, and before-your-trip formats.
- Make it sound like a helpful person on X, not a travel safety brochure.
- Use varied categories: eSIM, packing, carry-on, flight comfort, power, safety, insurance, hotels, tours, VPN, camera gear.
- Score each post from 1 to 10.
- Do not give every post the same score.

Preferred post_text format:

Hook sentence.

Short setup.

1. item
2. item
3. item
4. item

Soft closing sentence.

Example post_text:

Landing abroad with no data is stressful.

Before you fly:

1. Check if your phone supports eSIM
2. Pick a local data plan
3. Save setup instructions offline
4. Keep your hotel address saved

Small prep. Smoother arrival.

CTA examples:
- no CTA
- Building a simple travel setup checklist.
- Full setup checklist coming soon.
"""

print("2. Recent posts loaded:")
print(recent_posts_text)

print("3. Sending request to Gemini...")

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
)

print("4. Response received.")

text = response.text.strip()

if text.startswith("```json"):
    text = text.replace("```json", "").replace("```", "").strip()
elif text.startswith("```"):
    text = text.replace("```", "").strip()

try:
    posts = json.loads(text)
except json.JSONDecodeError:
    print("JSON parsing failed. Raw output:")
    print(text)
    raise

df = pd.DataFrame(posts)

if "score" in df.columns:
    df = df.sort_values(by="score", ascending=False)

df.to_csv("posts.csv", index=False, encoding="utf-8-sig")

top_df = df.head(3)
top_df.to_csv("top_posts.csv", index=False, encoding="utf-8-sig")

print("5. Done.")
print("Generated posts.csv and top_posts.csv")
print(top_df[["topic", "category", "score", "status", "cta"]])
