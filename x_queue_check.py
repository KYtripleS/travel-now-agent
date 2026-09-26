#!/usr/bin/env python3
"""
x_queue_check.py — validate site/data/x_queue.json before it ships.

The n8n workflow reads https://gentlyyonder.com/data/x_queue.json and sends one
post per run to X through Buffer. Three things went wrong with the first queue,
and each is now a hard check here:

  1. Links were cut mid-URL. The deployed n8n code slices every post at 275
     characters (JavaScript length), so a post of 276-278 lost the end of its
     link. Raw length must be <= 275, and X's own weighted count (URLs = 23,
     most symbols such as the arrow = 2) must be <= 280.
  2. The same 49 posts went out again and again. X runs a duplicate-text job
     (botmaker rule BBQDuplicateTextProd) that labels repeated text
     COPYPASTA_SPAM. Every post must be new: no match, exact or near, with
     data/x_posted_archive.json or with another post in the queue.
  3. Short links to gentlyyonder.com/go/<key> must point at a redirect page that
     exists, and every other gentlyyonder.com link at a real page.

Also: ids are unique and increasing (the n8n cursor remembers the last id sent),
no emoji (the brand writes without them), none of the banned phrases, and the
site/ and docs/ copies are identical.

    python x_queue_check.py          # exits 1 if anything fails
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
QUEUE = REPO / "site" / "data" / "x_queue.json"
MIRROR = REPO / "docs" / "data" / "x_queue.json"
ARCHIVE = REPO / "data" / "x_posted_archive.json"

RAW_MAX = 275        # the deployed n8n node does String(text).slice(0, 275)
X_MAX = 280          # X's weighted limit
URL_WEIGHT = 23      # every URL counts as a t.co link

# twitter-text v3: these code point ranges weigh 1, everything else weighs 2
LIGHT = [(0, 4351), (8192, 8205), (8208, 8223), (8242, 8247)]
URL_RE = re.compile(r"(?:https?://)?(?:[a-z0-9-]+\.)+(?:com|net|org|io|co|jp|au)(?:/[^\s]*)?", re.I)
SITE_RE = re.compile(r"(?:https?://)?gentlyyonder\.com(/[^\s]*)?", re.I)
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF☀-➿️]")

BANNED = [
    "hidden gem", "magical", "must-see", "must see", "bucket list", "secret spot",
    "off the beaten path", "instagram-worthy", "you need this",
    "this changes everything", "the best", "ultimate", "life-changing",
    "guarantees entry", "you won't be denied",
]


def js_len(text: str) -> int:
    """Length as JavaScript counts it (UTF-16 code units)."""
    return len(text.encode("utf-16-le")) // 2


def x_weight(text: str) -> int:
    """X's weighted length: URLs count 23, light code points 1, others 2."""
    total, last = 0, 0
    for m in URL_RE.finditer(text):
        total += _chars(text[last:m.start()]) + URL_WEIGHT
        last = m.end()
    return total + _chars(text[last:])


def _chars(s: str) -> int:
    return sum(1 if any(a <= ord(c) <= b for a, b in LIGHT) else 2 for c in s)


def _words(text: str) -> set[str]:
    text = SITE_RE.sub(" ", text.lower())
    return set(re.findall(r"[a-z0-9¥,]+", text))


def _similar(a: str, b: str) -> float:
    wa, wb = _words(a), _words(b)
    return len(wa & wb) / len(wa | wb) if wa and wb else 0.0


def _target_ok(path: str) -> bool:
    path = path.split("?")[0].split("#")[0].rstrip(".,)")
    if path in ("", "/"):
        return True
    m = re.fullmatch(r"/go/([a-z0-9-]+)", path)
    if m:
        return (REPO / "site" / "go" / f"{m.group(1)}.html").exists()
    p = REPO / "site" / path.lstrip("/")
    return p.exists() or (p / "index.html").exists()


def main() -> int:
    errors: list[str] = []
    data = json.loads(QUEUE.read_text(encoding="utf-8"))
    posts = data.get("posts", [])
    archive = json.loads(ARCHIVE.read_text(encoding="utf-8"))["posts"] if ARCHIVE.exists() else []
    archived_max = max((p["id"] for p in archive), default=0)

    if MIRROR.read_text(encoding="utf-8") != QUEUE.read_text(encoding="utf-8"):
        errors.append("docs/data/x_queue.json differs from site/data/x_queue.json")

    ids = [p.get("id") for p in posts]
    if len(set(ids)) != len(ids):
        errors.append("duplicate ids")
    if ids != sorted(ids):
        errors.append("ids are not in increasing order")
    if ids and min(ids) <= archived_max:
        errors.append(f"ids must be above the archive's highest id ({archived_max})")

    for i, p in enumerate(posts):
        pid, text = p.get("id"), p.get("text", "")
        tag = f"#{pid}"
        if not isinstance(pid, int) or not text.strip():
            errors.append(f"{tag}: needs an integer id and text")
            continue
        if js_len(text) > RAW_MAX:
            errors.append(f"{tag}: {js_len(text)} raw chars (max {RAW_MAX}; n8n cuts the rest)")
        if x_weight(text) > X_MAX:
            errors.append(f"{tag}: X weighted length {x_weight(text)} (max {X_MAX})")
        if EMOJI_RE.search(text):
            errors.append(f"{tag}: contains emoji")
        low = text.lower()
        for phrase in BANNED:
            if re.search(rf"\b{re.escape(phrase)}\b", low):
                errors.append(f"{tag}: banned phrase '{phrase}'")
        for m in SITE_RE.finditer(text):
            if not _target_ok(m.group(1) or "/"):
                errors.append(f"{tag}: link target missing: {m.group(0)}")
        if "image" in p and not str(p["image"]).startswith("https://gentlyyonder.com/"):
            errors.append(f"{tag}: image must be an https://gentlyyonder.com/ URL")
        for old in archive:
            if _similar(text, old["text"]) >= 0.6:
                errors.append(f"{tag}: too close to archived post #{old['id']}")
        for other in posts[:i]:
            if _similar(text, other.get("text", "")) >= 0.6:
                errors.append(f"{tag}: too close to queued post #{other.get('id')}")

    linked = sum(1 for p in posts if "gentlyyonder.com" in p.get("text", ""))
    print(f"{len(posts)} posts · {linked} with a link · "
          f"longest raw {max((js_len(p['text']) for p in posts), default=0)} · "
          f"heaviest X count {max((x_weight(p['text']) for p in posts), default=0)} · "
          f"archive {len(archive)}")
    if errors:
        print("\n".join(f"  FAIL {e}" for e in errors))
        return 1
    print("  ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
