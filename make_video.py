#!/usr/bin/env python3
"""
make_video.py — Generate a vertical MP4 video for Travel Now short-form content.

Creates a silent 1080×1920 MP4 from the "Before You Fly: 5 Things to Check"
script package using only local libraries (Pillow, imageio, imageio-ffmpeg).

No paid APIs. No auto-posting. No copyrighted assets.
Output is a local MP4 file for manual upload.

Install once:
  pip install Pillow imageio imageio-ffmpeg

Usage:
  python make_video.py                   # generate to rendered_videos/
  python make_video.py --fps 30
  python make_video.py --output path/to/output.mp4
  python make_video.py --no-transitions  # skip cross-dissolves (faster)
  python make_video.py --preview-frame 3 # save one slide as PNG and exit

Source: video_scripts/2026-05-30-before-you-fly-5-things-to-check/
"""

import argparse
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ── Output paths ───────────────────────────────────────────────────────────────

OUTPUT_DIR = Path("rendered_videos")

# ── Video geometry ─────────────────────────────────────────────────────────────

W, H   = 1080, 1920   # 9:16 vertical — YouTube Shorts / Reels / TikTok
FPS    = 30
TRANS  = 9            # cross-dissolve frames (0.3 s)
MARGIN = 90           # horizontal safe margin
SAFE_W = W - 2 * MARGIN

# ── Travel Now brand colours (from style-v2.css) ───────────────────────────────

BG      = (247, 244, 239)   # --bg:   #F7F4EF  warm off-white
NAVY    = ( 27,  42,  74)   # --navy: #1B2A4A  dark navy
GOLD    = (201, 168,  76)   # --gold: #C9A84C  brand gold
WHITE   = (255, 255, 255)
MUTED   = (120, 130, 155)   # secondary/muted text
GOLD_LT = (242, 234, 203)   # very light gold tint

# ── Font paths (Mac first, Linux fallback) ─────────────────────────────────────

_FONT_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",       # macOS — has bold at index 2
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
_BOLD_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _find(paths: list) -> Optional[str]:
    for p in paths:
        if os.path.exists(p):
            return p
    return None


_REG_PATH  = _find(_FONT_CANDIDATES)
_BOLD_PATH = _find(_BOLD_CANDIDATES)
_IS_TTC    = _REG_PATH and _REG_PATH.endswith(".ttc")


def fnt(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Return a PIL font at the requested size and weight."""
    try:
        if bold:
            if _IS_TTC:
                return ImageFont.truetype(_REG_PATH, size, index=2)   # Helvetica Bold
            if _BOLD_PATH:
                return ImageFont.truetype(_BOLD_PATH, size)
        if _REG_PATH:
            return ImageFont.truetype(_REG_PATH, size, index=0)
    except (OSError, AttributeError):
        pass
    return ImageFont.load_default()


# ── Script slides ──────────────────────────────────────────────────────────────

@dataclass
class Slide:
    kind:     str           # hook | check | closer | cta | endcard
    secs:     float         # display duration (seconds, before transitions)
    number:   int   = 0     # for check slides: 1–5
    lines:    list  = field(default_factory=list)


SLIDES = [
    Slide("hook",    2.5, lines=[
        "Airport panic?",
        "Five checks.",
        "Under five minutes.",
    ]),
    Slide("check",   4.0, number=1, lines=[
        "Boarding pass ready,",
        "passport valid.",
    ]),
    Slide("check",   4.0, number=2, lines=[
        "100ml, one clear bag,",
        "right at the top of",
        "your carry-on.",
    ]),
    Slide("check",   4.0, number=3, lines=[
        "Devices charged.",
        "Power bank in carry-on.",
        "Check battery rules.",
    ]),
    Slide("check",   4.0, number=4, lines=[
        "eSIM or roaming active.",
        "Offline maps downloaded.",
    ]),
    Slide("check",   4.0, number=5, lines=[
        "Meds and essentials",
        "in your carry-on.",
        "Checked bags can be delayed.",
    ]),
    Slide("closer",  2.5, lines=[
        "Five checks.",
        "Five minutes.",
        "Every time.",
    ]),
    Slide("cta",     2.5, lines=[
        "Build your full trip checklist",
        "→  link in bio",
    ]),
    Slide("endcard", 3.5),
]

TOTAL_SECS = sum(s.secs for s in SLIDES)

# ── Drawing helpers ────────────────────────────────────────────────────────────

def _tw(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]


def _th(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[3] - bb[1]


def _center_x(draw, text, font):
    return (W - _tw(draw, text, font)) // 2


def _draw_centered(draw: ImageDraw.ImageDraw, text: str, y: int,
                   font: ImageFont.FreeTypeFont, color: tuple) -> int:
    """Draw text centred horizontally at y. Returns bottom y."""
    x  = _center_x(draw, text, font)
    draw.text((x, y), text, font=font, fill=color)
    bb = draw.textbbox((x, y), text, font=font)
    return bb[3]


def _draw_lines(draw: ImageDraw.ImageDraw, lines: list, y: int,
                font: ImageFont.FreeTypeFont, color: tuple,
                gap: int = 14) -> int:
    """Draw multiple centred lines. Returns bottom y."""
    for line in lines:
        y = _draw_centered(draw, line, y, font, color) + gap
    return y


def _wrap(draw: ImageDraw.ImageDraw, text: str,
          font: ImageFont.FreeTypeFont, max_w: int) -> list:
    """Word-wrap text to fit max_w. Returns list of line strings."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if _tw(draw, test, font) <= max_w:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def _gold_bar(draw: ImageDraw.ImageDraw, y: int,
              width: int = 100, height: int = 7, cx: int = W // 2):
    x = cx - width // 2
    draw.rectangle([(x, y), (x + width, y + height)], fill=GOLD)


def _badge(draw: ImageDraw.ImageDraw, n: int, cx: int, cy: int, r: int):
    """Gold filled circle with white number."""
    draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=GOLD)
    f    = fnt(r - 4, bold=True)
    lab  = str(n)
    bb   = draw.textbbox((0, 0), lab, font=f)
    lw   = bb[2] - bb[0]
    lh   = bb[3] - bb[1]
    tx   = cx - lw // 2 - bb[0]
    ty   = cy - lh // 2 - bb[1]
    draw.text((tx, ty), lab, font=f, fill=WHITE)


def _progress(draw: ImageDraw.ImageDraw, current: int, total: int = 5):
    """Five dots at the bottom; filled gold up to current, muted after."""
    r       = 13
    gap     = 52
    total_w = (total - 1) * gap
    sx      = (W - total_w) // 2
    y       = H - 185
    for i in range(1, total + 1):
        cx = sx + (i - 1) * gap
        if i <= current:
            draw.ellipse([(cx - r, y - r), (cx + r, y + r)], fill=GOLD)
        else:
            draw.ellipse([(cx - r, y - r), (cx + r, y + r)],
                         outline=MUTED, width=3, fill=BG)


def _brand_footer(draw: ImageDraw.ImageDraw):
    f = fnt(34)
    draw.text((_center_x(draw, "Travel Now", f), H - 95),
              "Travel Now", font=f, fill=MUTED)


# ── Slide renderers ────────────────────────────────────────────────────────────

def _hook(img: Image.Image, draw: ImageDraw.ImageDraw, slide: Slide):
    _gold_bar(draw, 310, width=130, height=9)

    # "Airport panic?" — large gold
    y = 360
    y = _draw_centered(draw, slide.lines[0], y, fnt(100, bold=True), GOLD) + 44

    # "Five checks." — very large navy
    y = _draw_centered(draw, slide.lines[1], y, fnt(130, bold=True), NAVY) + 38

    # "Under five minutes." — medium muted
    _draw_centered(draw, slide.lines[2], y, fnt(66), MUTED)

    _gold_bar(draw, H // 2 + 190, width=80, height=6)
    _brand_footer(draw)


def _check(img: Image.Image, draw: ImageDraw.ImageDraw, slide: Slide):
    n = slide.number

    # "CHECK" label above badge
    lf = fnt(46)
    draw.text((_center_x(draw, "CHECK", lf), 310), "CHECK", font=lf, fill=MUTED)

    # Gold badge with number
    _badge(draw, n, W // 2, 540, 115)

    # Gold divider
    draw.rectangle([(MARGIN, 710), (W - MARGIN, 716)], fill=GOLD)

    # Check text (centred, wrapped)
    y = 770
    f = fnt(66, bold=True)
    for raw_line in slide.lines:
        for wrapped in _wrap(draw, raw_line, f, SAFE_W):
            y = _draw_centered(draw, wrapped, y, f, NAVY) + 18

    # Progress dots
    _progress(draw, n)
    _brand_footer(draw)


def _closer(img: Image.Image, draw: ImageDraw.ImageDraw, slide: Slide):
    _gold_bar(draw, 400, width=120, height=9)

    y = 470
    y = _draw_centered(draw, slide.lines[0], y, fnt(100, bold=True), GOLD)  + 32
    y = _draw_centered(draw, slide.lines[1], y, fnt(100, bold=True), NAVY)  + 32
    _draw_centered(draw, slide.lines[2], y, fnt(84), MUTED)

    _gold_bar(draw, H // 2 + 220, width=80, height=6)
    _brand_footer(draw)


def _cta(img: Image.Image, draw: ImageDraw.ImageDraw, slide: Slide):
    _gold_bar(draw, 360, width=130, height=9)

    y = 440
    y = _draw_centered(draw, slide.lines[0], y, fnt(66, bold=True), NAVY) + 32
    y = _draw_centered(draw, slide.lines[1], y, fnt(88, bold=True), GOLD) + 80

    # URL hint (small)
    f_url  = fnt(42)
    parts  = ["kytriples.github.io/travel-now-agent/", "checklist-generator.html"]
    y = H - 370
    for part in parts:
        y = _draw_centered(draw, part, y, f_url, MUTED) + 10

    _brand_footer(draw)


def _endcard(img: Image.Image, draw: ImageDraw.ImageDraw, slide: Slide):
    # Top and bottom gold bars
    draw.rectangle([(0, 0),    (W, 20)],   fill=GOLD)
    draw.rectangle([(0, H-20), (W, H)],    fill=GOLD)

    # Large "Travel Now"
    f_main = fnt(136, bold=True)
    y = 560
    y = _draw_centered(draw, "Travel Now", y, f_main, NAVY) + 50

    _gold_bar(draw, y, width=220, height=9)
    y += 70

    # Tagline
    f_tag = fnt(58)
    y = _draw_centered(draw, "Smarter travel prep.", y, f_tag, MUTED) + 16
    y = _draw_centered(draw, "Smoother trips.",      y, f_tag, MUTED) + 80

    # URL
    draw.rectangle([(MARGIN, y), (W - MARGIN, y + 4)], fill=GOLD)
    y += 30
    f_url = fnt(44)
    y = _draw_centered(draw, "kytriples.github.io/travel-now-agent/", y, f_url, NAVY) + 8
    _draw_centered(draw, "checklist-generator.html", y, f_url, NAVY)


_RENDERERS = {
    "hook":    _hook,
    "check":   _check,
    "closer":  _closer,
    "cta":     _cta,
    "endcard": _endcard,
}


def render_slide(slide: Slide) -> Image.Image:
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    _RENDERERS[slide.kind](img, draw, slide)
    return img


# ── Frame assembly ─────────────────────────────────────────────────────────────

def _dissolve(a: Image.Image, b: Image.Image, t: float) -> Image.Image:
    """Linear cross-dissolve. t=0 → a, t=1 → b."""
    return Image.blend(a, b, t)


def build_frames(slides: list, fps: int, transitions: bool = True) -> list:
    print(f"\n  Rendering {len(slides)} slides...")
    rendered = []
    for i, s in enumerate(slides):
        img = render_slide(s)
        rendered.append(img)
        kind = f"{s.kind} {s.number}" if s.kind == "check" else s.kind
        print(f"    {i+1}/{len(slides)}  {kind}")

    frames = []
    tf = TRANS if transitions else 0

    for i, slide in enumerate(slides):
        total_f = max(1, round(slide.secs * fps))
        body_f  = max(1, total_f - tf) if (i < len(slides) - 1 and tf) else total_f

        for _ in range(body_f):
            frames.append(rendered[i].copy())

        if i < len(slides) - 1 and tf:
            for t in range(tf):
                alpha = (t + 1) / (tf + 1)
                frames.append(_dissolve(rendered[i], rendered[i + 1], alpha))

    return frames


# ── MP4 writing ────────────────────────────────────────────────────────────────

def write_mp4(frames: list, path: Path, fps: int) -> bool:
    arr = [np.array(f) for f in frames]

    # ── Backend 1: imageio with libx264 (needs imageio-ffmpeg) ────────────────
    try:
        import imageio
        with imageio.get_writer(
            str(path), fps=fps,
            codec="libx264",
            pixelformat="yuv420p",
            macro_block_size=1,   # keep exact 1080×1920 — no auto-resize
            quality=8,
        ) as w:
            for frame in arr:
                w.append_data(frame)
        print(f"    backend: imageio / libx264")
        return True
    except Exception as e:
        print(f"    imageio/libx264 failed: {e}")

    # ── Backend 2: imageio default codec ──────────────────────────────────────
    try:
        import imageio
        with imageio.get_writer(str(path), fps=fps) as w:
            for frame in arr:
                w.append_data(frame)
        print(f"    backend: imageio (default codec)")
        return True
    except Exception as e:
        print(f"    imageio default failed: {e}")

    # ── Backend 3: opencv ─────────────────────────────────────────────────────
    try:
        import cv2
        writer = cv2.VideoWriter(
            str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H)
        )
        for frame in arr:
            writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        writer.release()
        print(f"    backend: opencv")
        return True
    except Exception as e:
        print(f"    opencv failed: {e}")

    # ── Backend 4: system ffmpeg via temp PNG frames ──────────────────────────
    try:
        import shutil
        if not shutil.which("ffmpeg"):
            raise FileNotFoundError("ffmpeg not found in PATH")
        with tempfile.TemporaryDirectory() as tmp:
            print(f"    writing {len(frames)} PNG frames to temp dir...")
            for i, f in enumerate(frames):
                f.save(f"{tmp}/f{i:06d}.png")
            cmd = [
                "ffmpeg", "-y",
                "-framerate", str(fps),
                "-i", f"{tmp}/f%06d.png",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22",
                str(path),
            ]
            r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            print(f"    backend: system ffmpeg")
            return True
        print(f"    ffmpeg error: {r.stderr[-400:]}")
    except Exception as e:
        print(f"    system ffmpeg failed: {e}")

    return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate Travel Now vertical MP4 short-form video.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--output", "-o",
        help="Output MP4 path (default: rendered_videos/YYYY-MM-DD-before-you-fly.mp4)",
    )
    parser.add_argument(
        "--fps", type=int, default=FPS,
        help=f"Frames per second (default: {FPS})",
    )
    parser.add_argument(
        "--no-transitions", action="store_true",
        help="Skip cross-dissolve transitions (faster rendering, harder cuts)",
    )
    parser.add_argument(
        "--preview-frame", type=int, metavar="N",
        help="Render slide N as a PNG preview and exit (1-indexed)",
    )
    args = parser.parse_args()

    # ── Preview mode ──────────────────────────────────────────────────────────
    if args.preview_frame:
        idx = args.preview_frame - 1
        if idx < 0 or idx >= len(SLIDES):
            print(f"Error: slide index {args.preview_frame} out of range (1–{len(SLIDES)})")
            sys.exit(1)
        OUTPUT_DIR.mkdir(exist_ok=True)
        slide = SLIDES[idx]
        kind  = f"{slide.kind}-{slide.number}" if slide.kind == "check" else slide.kind
        out   = OUTPUT_DIR / f"preview-slide-{args.preview_frame:02d}-{kind}.png"
        img   = render_slide(slide)
        img.save(out)
        print(f"Preview saved: {out}")
        print(f"  open {out}")
        return

    # ── Full video ─────────────────────────────────────────────────────────────
    OUTPUT_DIR.mkdir(exist_ok=True)
    if args.output:
        out_path = Path(args.output)
    else:
        today    = date.today().isoformat()
        out_path = OUTPUT_DIR / f"{today}-before-you-fly.mp4"

    transitions = not args.no_transitions

    print(f"\n=== TRAVEL NOW VIDEO GENERATOR ===")
    print(f"  Output:      {out_path}")
    print(f"  Resolution:  {W}×{H}  (9:16 vertical)")
    print(f"  FPS:         {args.fps}")
    print(f"  Duration:    ~{TOTAL_SECS:.0f}s  ({len(SLIDES)} slides)")
    print(f"  Transitions: {'yes (0.3s cross-dissolve)' if transitions else 'no'}")
    print(f"  Font:        {_REG_PATH or 'PIL default'}")

    frames          = build_frames(SLIDES, args.fps, transitions)
    actual_duration = len(frames) / args.fps
    print(f"\n  Total frames: {len(frames)} ({actual_duration:.1f}s)")

    print(f"\n  Writing MP4...")
    ok = write_mp4(frames, out_path, args.fps)

    if ok:
        size_mb = out_path.stat().st_size / 1_048_576
        print(f"\n  ✓  {out_path}  ({size_mb:.1f} MB, {actual_duration:.1f}s)")
        print()
        print(f"  Open on Mac:        open {out_path}")
        print(f"  Open in QuickTime:  open -a QuickTime\\ Player {out_path}")
        print()
        print(f"  Manual upload:")
        print(f"    YouTube Shorts:    youtube.com/upload  →  set as Short  →  max 60s")
        print(f"    Instagram Reels:   instagram.com  →  +  →  Reel  →  select MP4")
        print(f"    TikTok:            tiktok.com/upload  →  select MP4")
        print()
        print(f"  Tip: add music + captions in YouTube Studio / CapCut / DaVinci Resolve")
    else:
        print(f"\n  ✗  All write backends failed.")
        print(f"  Try: pip install imageio imageio-ffmpeg")
        sys.exit(1)

    print("=" * 36)


if __name__ == "__main__":
    main()
