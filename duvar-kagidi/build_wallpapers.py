#!/usr/bin/python3
"""Draws the Bandanix wallpapers with code (no downloaded images), at the screen's own size.

Styles: gece (dark, tone-on-tone paisley), bandana (classic red bandana), dalga (soft red
light waves), logo (bandana mark + BANDANIX). Each style can be drawn for four times of day.
Needs Pillow (python3-pil, installed on Linux Mint).
"""

from __future__ import annotations

import argparse
import math
import random
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
from bandanix_renk import hex_to_rgb, read_accent  # noqa: E402

STYLES = ("gece", "bandana", "dalga", "logo")
TIMES = ("sabah", "ogle", "aksam", "gece")
BG = (18, 18, 20)
SS = 2                       # supersampling for smooth curves

# How each time of day tints the picture: (brightness multiplier, warm tint)
TIME_LOOK = {"sabah": (1.25, (8, 4, 0)), "ogle": (1.35, (0, 0, 2)),
             "aksam": (1.1, (14, 4, -4)), "gece": (1.0, (0, 0, 0))}


# ---- paisley -----------------------------------------------------------------------
# The boteh (paisley): a teardrop whose tip is bent into a curl.
def paisley_points(cx, cy, size, angle, scale=1.0, shift=0.0, n=140, bend=1.9, slim=1.6):
    """Teardrop x=cos t, y=sin t*sin^m(t/2) (round end left, tip right), then the tip is
    curled by rotating each point more the closer it is to the tip."""
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = math.cos(t)
        y = math.sin(t) * abs(math.sin(t / 2)) ** slim * 0.75
        x, y = x * scale + shift, y * scale
        k = ((x + 1) / 2) ** 3 * bend                 # 0 at the round end, max at the tip
        x, y = x * math.cos(k) - y * math.sin(k), x * math.sin(k) + y * math.cos(k)
        pts.append((x, y))
    ca, sa = math.cos(angle), math.sin(angle)
    half = size / 2
    return [(cx + (x * ca - y * sa) * half, cy + (x * sa + y * ca) * half) for x, y in pts]


def draw_paisley(d, cx, cy, size, angle, fill, line, width, detail=True):
    d.polygon(paisley_points(cx, cy, size, angle), fill=fill, outline=line, width=width)
    if not detail:
        return
    inner = paisley_points(cx, cy, size, angle, scale=0.68, shift=-0.18)
    d.line(inner + inner[:1], fill=line, width=max(1, width), joint="curve")
    for x, y in inner[::7]:                           # dots along the inner outline
        r = size * 0.018
        d.ellipse((x - r, y - r, x + r, y + r), fill=line)
    fx, fy = paisley_points(cx, cy, size, angle, scale=0.0, shift=-0.45)[0]
    pr = size * 0.045                                 # small flower in the round body
    for k in range(5):
        a = angle + k * 2 * math.pi / 5
        px, py = fx + math.cos(a) * pr * 1.4, fy + math.sin(a) * pr * 1.4
        d.ellipse((px - pr, py - pr, px + pr, py + pr), fill=line)
    d.ellipse((fx - pr * 0.8, fy - pr * 0.8, fx + pr * 0.8, fy + pr * 0.8), fill=fill)


def bandana_mark(d, cx, cy, size, colour, dot):
    """The Bandanix mark: a folded bandana triangle with paisley dots."""
    h = size * 0.62
    tri = [(cx - size / 2, cy - h / 2), (cx + size / 2, cy - h / 2), (cx, cy + h / 2)]
    d.polygon(tri, fill=colour)
    d.line([(cx - size / 2, cy - h / 2), (cx + size / 2, cy - h / 2)], fill=dot, width=max(1, int(size * 0.03)))
    for row, n in enumerate((5, 3, 1)):
        y = cy - h / 2 + h * (0.22 + row * 0.24)
        span = size * (0.62 - row * 0.2)
        for k in range(n):
            x = cx - span / 2 + (span * k / (n - 1) if n > 1 else span / 2)
            r = size * 0.035
            d.ellipse((x - r, y - r, x + r, y + r), fill=dot)


# ---- helpers -----------------------------------------------------------------------
def mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def vignette(img, strength=0.55):
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse((-w * 0.25, -h * 0.35, w * 1.25, h * 1.35), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(min(w, h) * 0.25))
    dark = Image.new("RGB", img.size, (0, 0, 0))
    return Image.composite(img, Image.blend(img, dark, strength), mask)


def font(size, bold=False):
    names = (["Ubuntu-L.ttf", "Ubuntu-R.ttf"] if not bold else ["Ubuntu-B.ttf"]) + \
            ["DejaVuSans-ExtraLight.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
    for root in (Path("/usr/share/fonts"), Path.home() / ".local/share/fonts"):
        for name in names:
            hit = next(root.rglob(name), None) if root.is_dir() else None
            if hit:
                return ImageFont.truetype(str(hit), size)
    return ImageFont.load_default()


def corner_mark(img, accent, opacity=0.35):
    w, h = img.size
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    s = min(w, h) * 0.035
    bandana_mark(ImageDraw.Draw(layer), w - s * 1.6, h - s * 1.5, s, (*accent, int(255 * opacity)),
                 (*BG, int(255 * opacity)))
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def time_tint(img, when):
    gain, (tr, tg, tb) = TIME_LOOK[when]
    r, g, b = img.split()
    r = r.point(lambda v: max(0, min(255, int(v * gain + tr))))
    g = g.point(lambda v: max(0, min(255, int(v * gain + tg))))
    b = b.point(lambda v: max(0, min(255, int(v * gain + tb))))
    return Image.merge("RGB", (r, g, b))


# ---- styles --------------------------------------------------------------------------
def style_gece(W, H, accent, rng):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    for y in range(H):                                   # very soft top-to-bottom gradient
        d.line([(0, y), (W, y)], fill=mix((22, 22, 25), (14, 14, 16), y / H))
    size = min(W, H) * 0.16
    step = size * 1.35
    tone = mix(BG, accent, 0.07)
    line = mix(BG, (232, 230, 227), 0.05)
    row = 0
    y = -size
    while y < H + size:
        x = -size + (step / 2 if row % 2 else 0)
        while x < W + size:
            draw_paisley(d, x, y, size, rng.uniform(-0.6, 0.6) + (math.pi if (row + int(x / step)) % 2 else 0),
                         tone, line, max(1, int(size * 0.02)))
            x += step
        y += step * 0.8
        row += 1
    return vignette(img, 0.5)


def style_bandana(W, H, accent, rng):
    """A real bandana layout, muted: everything sits close to a dark red so nothing shouts."""
    field = mix(accent, BG, 0.62)                     # deep, dull red
    dark = mix(BG, field, 0.25)                       # "black" print
    light = mix((245, 243, 240), field, 0.72)         # "white" print, faded into the cloth
    img = Image.new("RGB", (W, H), field)
    d = ImageDraw.Draw(img)
    m = min(W, H)
    # border: two lines and a row of alternating dots, like a real bandana's edge
    b1, b2 = m * 0.035, m * 0.075
    for inset, wid in ((b1, int(m * 0.006)), (b2, int(m * 0.003))):
        d.rectangle((inset, inset, W - inset, H - inset), outline=dark, width=max(1, wid))
    dot = m * 0.006
    k = 0
    pos = b1 + (b2 - b1) / 2
    gap = int(m * 0.025)
    for x in range(int(b2), int(W - b2), gap):
        for yy in (pos, H - pos):
            d.ellipse((x - dot, yy - dot, x + dot, yy + dot), fill=light if k % 2 else dark)
            k += 1
    for y in range(int(b2), int(H - b2), gap):
        for xx in (pos, W - pos):
            d.ellipse((xx - dot, y - dot, xx + dot, y + dot), fill=light if k % 2 else dark)
            k += 1
    # paisleys in the field, alternating "black" and "white" print
    size = m * 0.2
    step = size * 1.25
    row = 0
    y = b2 + size * 0.7
    while y < H - b2 - size * 0.4:
        x = b2 + size * 0.7 + (step / 2 if row % 2 else 0)
        while x < W - b2 - size * 0.4:
            first = (row + int(x / step)) % 2 == 0
            draw_paisley(d, x, y, size, rng.uniform(-0.5, 0.5) + (0 if first else math.pi),
                         dark if first else light, light if first else dark,
                         max(1, int(size * 0.02)))
            x += step
        y += step * 0.78
        row += 1
    for _ in range(int(W * H / (m * m) * 120)):       # scattered small dots
        x, y = rng.uniform(b2, W - b2), rng.uniform(b2, H - b2)
        r = m * 0.004
        d.ellipse((x - r, y - r, x + r, y + r), fill=light)
    return vignette(img, 0.45)


def style_dalga(W, H, accent, rng):
    img = Image.new("RGB", (W, H), BG)
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(glow)
    for i in range(5):
        amp = H * rng.uniform(0.06, 0.14)
        base = H * (0.45 + i * 0.07)
        freq = rng.uniform(1.2, 2.2)
        phase = rng.uniform(0, math.tau)
        col = mix((0, 0, 0), accent, 0.55 - i * 0.08)
        pts = [(x, base + amp * math.sin(freq * math.tau * x / W + phase)) for x in range(0, W + 8, 8)]
        d.line(pts, fill=col, width=max(2, int(H * 0.012)))
    soft = glow.filter(ImageFilter.GaussianBlur(H * 0.035))
    sharp = glow.filter(ImageFilter.GaussianBlur(H * 0.004))
    img = ImageChops.add(img, soft)
    img = ImageChops.add(img, ImageChops.multiply(sharp, Image.new("RGB", (W, H), (150, 150, 150))))
    return vignette(img, 0.55)


def style_logo(W, H, accent, rng):
    img = Image.new("RGB", (W, H), BG)
    m = min(W, H)
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    r = m * 0.28
    gd.ellipse((W / 2 - r, H * 0.44 - r, W / 2 + r, H * 0.44 + r), fill=mix((0, 0, 0), accent, 0.22))
    img = ImageChops.add(img, glow.filter(ImageFilter.GaussianBlur(m * 0.12)))
    d = ImageDraw.Draw(img)
    bandana_mark(d, W / 2, H * 0.44, m * 0.16, accent, BG)
    f = font(int(m * 0.035))
    text = " ".join("BANDANIX")
    tw = d.textlength(text, font=f)
    d.text((W / 2 - tw / 2, H * 0.44 + m * 0.11), text, font=f, fill=(232, 230, 227))
    return vignette(img, 0.45)


DRAW = {"gece": style_gece, "bandana": style_bandana, "dalga": style_dalga, "logo": style_logo}


def render_base(style: str, width: int, height: int, accent: str, mark: bool = True,
                seed: int = 7) -> Image.Image:
    """The slow part (drawing), done once per style; time-of-day tints are applied after."""
    rgb = hex_to_rgb(accent)
    img = DRAW[style](width * SS, height * SS, rgb, random.Random(seed))
    img = img.resize((width, height), Image.LANCZOS)
    if mark and style != "logo":
        img = corner_mark(img, rgb, 0.35)
    return img


def render(style: str, width: int, height: int, accent: str, when: str = "gece",
           mark: bool = True, seed: int = 7) -> Image.Image:
    return time_tint(render_base(style, width, height, accent, mark, seed), when)


def screen_size() -> tuple[int, int]:
    """Largest connected monitor from xrandr; 1920x1080 if it can't be read."""
    try:
        out = subprocess.run(["xrandr", "--current"], capture_output=True, text=True,
                             timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        out = ""
    best = (1920, 1080)
    for m in re.finditer(r" connected (?:primary )?(\d+)x(\d+)\+", out):
        w, h = int(m.group(1)), int(m.group(2))
        if w * h > best[0] * best[1]:
            best = (w, h)
    return best


def file_name(style: str, when: str) -> str:
    return f"bandanix-{style}-{when}.png"


def main() -> int:
    parser = argparse.ArgumentParser(description="Bandanix duvar kağıtlarını üretir.")
    parser.add_argument("--hedef", required=True, help="çıktı klasörü")
    parser.add_argument("--boyut", default="otomatik", help="GENxYUK ya da 'otomatik' (ekrandan)")
    parser.add_argument("--stiller", default=",".join(STYLES))
    parser.add_argument("--zamanlar", default=",".join(TIMES), help="virgülle: sabah,ogle,aksam,gece")
    parser.add_argument("--isaretsiz", action="store_true", help="köşe işareti olmasın")
    parser.add_argument("--accent", default=None)
    args = parser.parse_args()

    if args.boyut == "otomatik":
        w, h = screen_size()
    else:
        w, h = (int(v) for v in args.boyut.lower().split("x"))
    accent = args.accent or read_accent()
    out = Path(args.hedef)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("bandanix-*.png"):              # no leftovers from an older size/colour
        old.unlink()
    count = 0
    for style in args.stiller.split(","):
        base = render_base(style, w, h, accent, not args.isaretsiz)
        for when in args.zamanlar.split(","):
            time_tint(base, when).save(out / file_name(style, when), optimize=True)
            count += 1
    print(f"• {count} duvar kağıdı üretildi ({w}×{h}): {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
