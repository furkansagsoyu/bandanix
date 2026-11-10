#!/usr/bin/env python3
"""Draw the theme's pictures (run on a developer machine; the PNGs are kept in the repo).

  cizim.py            redraw plymouth/*.png and grub/*.png
  cizim.py onizleme   also draw ../docs/acilis-ekrani.jpg (boot, shutdown, password, GRUB)

Plymouth pictures are drawn for a 1080p screen at 2x; the script scales them to the screen.
GRUB pictures are drawn at their real size (GRUB does not scale).
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
INTER = Path("/usr/share/fonts/opentype/inter")
RED = (200, 16, 46)
WHITE = (242, 242, 245)
LABEL = (138, 138, 149)
TRACK = (38, 38, 43)
BOX_BG = (23, 23, 26)
BOX_LINE = (58, 58, 64)
SEL_BG = (30, 30, 34)


def font(weight: str, px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(INTER / f"Inter-{weight}.otf"), px)


def wordmark(height: int, colour=WHITE) -> Image.Image:
    """BANDANIX with wide letter spacing, cropped to the letters, transparent background."""
    f = font("SemiBold", height)
    gap = int(height * 0.38)
    widths = [f.getlength(ch) for ch in "BANDANIX"]
    w = int(sum(widths) + gap * 7) + 4
    img = Image.new("RGBA", (w, height * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 2
    for ch, cw in zip("BANDANIX", widths):
        d.text((x, height // 2), ch, font=f, fill=colour)
        x += cw + gap
    return img.crop(img.getbbox())


def text(s: str, px: int, colour, weight="Regular") -> Image.Image:
    f = font(weight, px)
    l, t, r, b = f.getbbox(s)
    img = Image.new("RGBA", (r - l + 4, int(px * 1.4)), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((2 - l, int(px * 0.15)), s, font=f, fill=colour)
    return img


def rounded(w: int, h: int, r: int, fill, outline=None, width=0, ss=4) -> Image.Image:
    big = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    ImageDraw.Draw(big).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), r * ss, fill=fill,
                                          outline=outline, width=width * ss)
    return big.resize((w, h), Image.LANCZOS)


def dot(d: int) -> Image.Image:
    big = Image.new("RGBA", (d * 4, d * 4), (0, 0, 0, 0))
    ImageDraw.Draw(big).ellipse((0, 0, d * 4 - 1, d * 4 - 1), fill=WHITE)
    return big.resize((d, d), Image.LANCZOS)


def plymouth_assets() -> dict[str, Image.Image]:
    return {
        "wordmark.png": wordmark(76),                 # ~ 360 px wide on a 1080p screen
        "cizgi.png": Image.new("RGBA", (4, 4), RED + (255,)),
        "iz.png": Image.new("RGBA", (4, 4), TRACK + (255,)),
        "kapaniyor.png": text("Kapanıyor", 36, LABEL),
        "yeniden.png": text("Yeniden başlatılıyor", 36, LABEL),
        "kutu.png": rounded(760, 96, 16, BOX_BG, BOX_LINE, 2),
        "nokta.png": dot(20),
    }


def grub_assets() -> dict[str, Image.Image]:
    out = {"wordmark.png": wordmark(30)}
    sel = rounded(48, 48, 8, SEL_BG, RED, 2)       # cut into a 9-slice frame for the selected item
    c = 12
    boxes = {"nw": (0, 0, c, c), "n": (c, 0, 48 - c, c), "ne": (48 - c, 0, 48, c),
             "w": (0, c, c, 48 - c), "c": (c, c, 48 - c, 48 - c), "e": (48 - c, c, 48, 48 - c),
             "sw": (0, 48 - c, c, 48), "s": (c, 48 - c, 48 - c, 48), "se": (48 - c, 48 - c, 48, 48)}
    for name, box in boxes.items():
        out[f"select_{name}.png"] = sel.crop(box)
    return out


def save_all() -> None:
    for folder, assets in (("plymouth", plymouth_assets()), ("grub", grub_assets())):
        for name, img in assets.items():
            img.save(HERE / folder / name, optimize=True)


# ---- previews (what the screens should look like on a 1920x1080 laptop) --------------------
W, H = 1920, 1080


def paste_center(canvas: Image.Image, img: Image.Image, cy: int) -> tuple[int, int]:
    x, y = (canvas.width - img.width) // 2, cy - img.height // 2
    canvas.alpha_composite(img, (x, y))
    return x, y


def half(img: Image.Image) -> Image.Image:
    return img.resize((max(1, img.width // 2), max(1, img.height // 2)), Image.LANCZOS)


def plymouth_screen(kind: str) -> Image.Image:
    a = {k: half(v) for k, v in plymouth_assets().items()}
    s = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    mx, my = paste_center(s, a["wordmark.png"], int(H * 0.45))
    bar_w, bar_h = 260, 3
    bx, by = (W - bar_w) // 2, my + a["wordmark.png"].height + 36
    d = ImageDraw.Draw(s)
    if kind == "sifre":
        box = a["kutu.png"]
        bxx, byy = (W - box.width) // 2, by + 40
        s.alpha_composite(box, (bxx, byy))
        prompt = text("Please unlock disk nvme0n1p3_crypt:", 26, (161, 161, 171))
        s.alpha_composite(half(prompt), ((W - prompt.width // 2) // 2, byy - prompt.height // 2 - 12))
        n, step = 9, a["nokta.png"].width + 8
        start = (W - (n * step - 8)) // 2
        for i in range(n):
            s.alpha_composite(a["nokta.png"], (start + i * step, byy + (box.height - a["nokta.png"].height) // 2))
        return s
    d.rectangle((bx, by, bx + bar_w - 1, by + bar_h - 1), fill=TRACK)
    if kind == "acilis":
        d.rectangle((bx, by, bx + int(bar_w * 0.62) - 1, by + bar_h - 1), fill=RED)
        msg = half(text("/dev/nvme0n1p2: clean, 412398/30515200 files", 22, (115, 115, 128)))
        s.alpha_composite(msg, ((W - msg.width) // 2, H - msg.height - 40))
    else:
        d.rectangle((bx, by, bx + bar_w - 1, by + bar_h - 1), fill=tuple(int(c * 0.8) for c in RED))
        label = a["kapaniyor.png"]
        s.alpha_composite(label, ((W - label.width) // 2, by + bar_h + 22))
    return s


def grub_screen() -> Image.Image:
    g = grub_assets()
    s = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    s.alpha_composite(g["wordmark.png"], ((W - g["wordmark.png"].width) // 2, int(H * 0.18)))
    item = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    d = ImageDraw.Draw(s)
    left, top, width, ih, sp = W // 2 - 320, int(H * 0.30), 640, 44, 8
    entries = ["Linux Mint 22 Cinnamon", "Advanced options for Linux Mint 22 Cinnamon", "UEFI Firmware Settings"]
    for i, name in enumerate(entries):
        y = top + i * (ih + sp)
        if i == 0:
            frame = Image.new("RGBA", (width, ih))
            c = 12
            frame.paste(g["select_c.png"].resize((width - 2 * c, ih - 2 * c)), (c, c))
            frame.paste(g["select_n.png"].resize((width - 2 * c, c)), (c, 0))
            frame.paste(g["select_s.png"].resize((width - 2 * c, c)), (c, ih - c))
            frame.paste(g["select_w.png"].resize((c, ih - 2 * c)), (0, c))
            frame.paste(g["select_e.png"].resize((c, ih - 2 * c)), (width - c, c))
            for k, pos in (("nw", (0, 0)), ("ne", (width - c, 0)), ("sw", (0, ih - c)), ("se", (width - c, ih - c))):
                frame.paste(g[f"select_{k}.png"], pos)
            s.alpha_composite(frame, (left, y))
        d.text((left + 14, y + ih // 2), name, font=item, fill=(255, 255, 255) if i == 0 else (160, 160, 171), anchor="lm")
    d.text((W // 2, H - 50), "↑ ↓ seç   ·   Enter başlat   ·   e düzenle   ·   c komut satırı",
           font=small, fill=(115, 115, 128), anchor="mm")
    return s


def preview_sheet() -> None:
    shots = [("Açılış", plymouth_screen("acilis")), ("Kapanış", plymouth_screen("kapanis")),
             ("Disk şifresi", plymouth_screen("sifre")), ("GRUB menüsü (Shift / Esc)", grub_screen())]
    tw, th, gap, cap = 960, 540, 24, 44
    sheet = Image.new("RGB", (tw * 2 + gap * 3, (th + cap) * 2 + gap * 3), (18, 18, 20))
    d = ImageDraw.Draw(sheet)
    for i, (title, shot) in enumerate(shots):
        x = gap + (i % 2) * (tw + gap)
        y = gap + (i // 2) * (th + cap + gap)
        d.text((x, y + 8), title, font=font("Medium", 22), fill=(216, 216, 222))
        thumb = shot.convert("RGB").resize((tw, th), Image.LANCZOS)
        sheet.paste(thumb, (x, y + cap))
        d.rectangle((x - 1, y + cap - 1, x + tw, y + cap + th), outline=(48, 48, 54))
    sheet.save(HERE.parent / "docs" / "acilis-ekrani.jpg", quality=90)


if __name__ == "__main__":
    save_all()
    if sys.argv[1:] == ["onizleme"]:
        preview_sheet()
