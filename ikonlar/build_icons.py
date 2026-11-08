#!/usr/bin/python3
"""Builds the Bandanix icon theme (from Mint-Y-Red) and cursor theme (from Bibata-Modern-Classic).

Icons: only the reds change (folders, places); greys stay, they give icons their depth.
Cursor: the black body stays, the white outline becomes the accent colour. Coloured parts
(e.g. the green "+" of the copy cursor) are left untouched.
"""

from __future__ import annotations

import argparse
import os
import shutil
import struct
import subprocess
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
from bandanix_renk import (hex_to_rgb, is_accent, read_accent,  # noqa: E402
                           rgb_to_hex, shift_accent)

try:
    from PIL import Image, ImageChops, ImageDraw
except ImportError:      # icons need Pillow; the cursor works without it
    Image = ImageChops = ImageDraw = None

ICON_NAME = "Bandanix"
CURSOR_DIR = "Bandanix-Imlec"
XCURSOR_IMAGE = 0xFFFD0002
GREY_TOLERANCE = 6       # channel spread up to this counts as grey (anti-aliasing noise)


# ---- icons --------------------------------------------------------------------------
def pixels(img):
    flat = getattr(img, "get_flattened_data", None) or img.getdata
    return list(flat())


def detect_icon_accent(source: Path) -> tuple[int, int, int]:
    """The red used most across the folder icons."""
    counts: Counter = Counter()
    for path in sorted(source.glob("places/48/folder*.png")) or sorted(source.rglob("*.png"))[:40]:
        if path.is_symlink():
            continue
        with Image.open(path) as img:
            for p in pixels(img.convert("RGBA")):
                if p[3] > 200 and is_accent(p[:3]):
                    counts[p[:3]] += 1
    if not counts:
        sys.exit("İkon temasında kırmızı vurgu bulunamadı.")
    return counts.most_common(1)[0][0]


def build_icons(source: Path, target: Path, accent: str) -> dict:
    if Image is None:
        sys.exit("İkonları boyamak için Pillow gerekli: sudo apt install python3-pil")
    if not (source / "index.theme").is_file():
        sys.exit(f"İkon teması bulunamadı: {source}")
    src_accent = detect_icon_accent(source)
    dst = hex_to_rgb(accent)
    cache: dict = {}

    def recolour(rgb):
        if rgb not in cache:
            cache[rgb] = shift_accent(rgb, src_accent, dst) if is_accent(rgb) else rgb
        return cache[rgb]

    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, symlinks=True)       # keep Mint's alias symlinks
    (target / "icon-theme.cache").unlink(missing_ok=True)  # stale; rebuilt below

    changed = 0
    for path in target.rglob("*.png"):
        if path.is_symlink():
            continue
        with Image.open(path) as img:
            img = img.convert("RGBA")
            old = pixels(img)
            new = [(*recolour(p[:3]), p[3]) if p[3] else p for p in old]
            if new != old:
                img.putdata(new)
                img.save(path)
                changed += 1

    index = target / "index.theme"
    text = index.read_text(encoding="utf-8").splitlines()
    out = []
    for line in text:
        if line.startswith("Name="):
            line = f"Name={ICON_NAME}"
        elif line.startswith("Comment="):
            line = "Comment=Bandanix: Mint-Y tabanlı, bandana kırmızısı klasörler"
        out.append(line)
    index.write_text("\n".join(out) + "\n", encoding="utf-8")

    if shutil.which("gtk-update-icon-cache"):
        subprocess.run(["gtk-update-icon-cache", "-q", "-f", "-t", str(target)], check=False)
    return {"source_accent": rgb_to_hex(src_accent), "png": changed}


# ---- cursor ---------------------------------------------------------------------------
def recolour_image(data: bytearray, start: int, w: int, h: int, accent) -> bool:
    """Xcursor pixels are premultiplied ARGB, little-endian: bytes B, G, R, A.

    A grey pixel's premultiplied value v = lightness * alpha, so scaling each channel by
    the accent gives exactly "accent * lightness" with the same alpha: white -> accent,
    black stays black, anti-aliased steps in between.
    """
    end = start + w * h * 4
    ar, ag, ab = accent
    tables = [bytes(round(v * c / 255) for v in range(256)) for c in (ab, ag, ar)]  # B, G, R
    b, g, r = bytes(data[start:end:4]), bytes(data[start + 1:end:4]), bytes(data[start + 2:end:4])

    if b == g == r:                                   # fully grey image: fast path
        for offset, table, chan in ((0, tables[0], b), (1, tables[1], g), (2, tables[2], r)):
            data[start + offset:end:4] = chan.translate(table)
        return True
    if Image is None:                                 # coloured image without Pillow: leave it
        return False

    img = Image.frombuffer("RGBA", (w, h), bytes(data[start:end]), "raw", "BGRA", 0, 1)
    R, G, B, A = img.split()
    spread = ImageChops.add(ImageChops.difference(R, G), ImageChops.difference(G, B))
    grey = spread.point(lambda x: 255 if x <= GREY_TOLERANCE else 0)
    transparent = A.point(lambda x: 255 if x == 0 else 0)
    # Only greys reachable from outside the cursor (through transparent or grey pixels) are
    # its outline/body. White details inside coloured shapes (the "+" of the copy cursor,
    # the inside of the "no" sign) can't be reached and keep their colour.
    passable = ImageChops.lighter(grey, transparent)
    region = Image.new("L", (w + 2, h + 2), 255)      # 1px open frame: one fill reaches every edge
    region.paste(passable, (1, 1))
    ImageDraw.floodfill(region, (0, 0), 128)
    outside = region.crop((1, 1, w + 1, h + 1)).point(lambda x: 255 if x == 128 else 0)
    grey_mask = ImageChops.multiply(grey, outside)
    recoloured = Image.merge("RGBA", (R.point(list(tables[2])), G.point(list(tables[1])),
                                      B.point(list(tables[0])), A))
    result = Image.composite(recoloured, img, grey_mask)
    data[start:end] = result.tobytes("raw", "BGRA")
    return True


def recolour_xcursor(path: Path, accent) -> int:
    data = bytearray(path.read_bytes())
    if data[:4] != b"Xcur":
        return 0
    ntoc = struct.unpack_from("<I", data, 12)[0]
    images = 0
    for i in range(ntoc):
        kind, _subtype, pos = struct.unpack_from("<III", data, 16 + 12 * i)
        if kind != XCURSOR_IMAGE:
            continue
        header, _, _, _, w, h = struct.unpack_from("<IIIIII", data, pos)
        images += recolour_image(data, pos + header, w, h, accent)
    path.write_bytes(bytes(data))
    return images


def build_cursor(source: Path, target: Path, accent: str) -> dict:
    if not (source / "cursors").is_dir():
        sys.exit(f"İmleç teması bulunamadı: {source}")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, symlinks=True)
    rgb = hex_to_rgb(accent)
    paths = [p for p in (target / "cursors").iterdir() if p.is_file() and not p.is_symlink()]
    # one cursor file per CPU core: the build runs once at install, this keeps it short
    with ProcessPoolExecutor(max_workers=os.cpu_count() or 2) as pool:
        counts = list(pool.map(recolour_xcursor, paths, [rgb] * len(paths)))
    files = sum(1 for n in counts if n)
    images = sum(counts)
    (target / "index.theme").write_text(
        "[Icon Theme]\nName=Bandanix İmleç\n"
        "Comment=Bibata-Modern-Classic: siyah gövde, bandana kırmızısı kenar\n", encoding="utf-8")
    (target / "cursor.theme").write_text(
        f"[Icon Theme]\nName=Bandanix İmleç\nInherits={target.name}\n", encoding="utf-8")
    return {"files": files, "images": images}


def main() -> int:
    home = Path.home()
    parser = argparse.ArgumentParser(description="Bandanix ikon ve imleç temalarını üretir.")
    parser.add_argument("--ikon-kaynak", default="/usr/share/icons/Mint-Y-Red")
    parser.add_argument("--imlec-kaynak", default="/usr/share/icons/Bibata-Modern-Classic")
    parser.add_argument("--hedef-klasor", default=str(home / ".local/share/icons"),
                        help="ikon teması buraya kurulur")
    parser.add_argument("--imlec-klasor", default=str(home / ".icons"),
                        help="imleç buraya kurulur (X11 imleç kütüphanesinin her sistemde baktığı yer)")
    parser.add_argument("--accent", default=None, help="#RRGGBB (varsayılan: theme.toml)")
    args = parser.parse_args()

    accent = args.accent or read_accent()
    root = Path(args.hedef_klasor)
    root.mkdir(parents=True, exist_ok=True)

    icons = build_icons(Path(args.ikon_kaynak), root / ICON_NAME, accent)
    print(f"• İkonlar üretildi: {root / ICON_NAME}")
    print(f"  Kaynak kırmızı {icons['source_accent']} → {accent}, {icons['png']} resim boyandı")

    cursor_root = Path(args.imlec_klasor)
    cursor_root.mkdir(parents=True, exist_ok=True)
    cursor = build_cursor(Path(args.imlec_kaynak), cursor_root / CURSOR_DIR, accent)
    print(f"• İmleç üretildi: {cursor_root / CURSOR_DIR}")
    print(f"  {cursor['files']} imleç dosyasında {cursor['images']} boyut boyandı")
    return 0


if __name__ == "__main__":
    sys.exit(main())
