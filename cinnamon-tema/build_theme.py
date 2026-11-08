#!/usr/bin/python3
"""Builds the Bandanix GTK/Cinnamon theme from the Mint-Y-Dark-Red theme installed on the system.

Nothing is drawn from scratch: the Mint theme is copied and its colours are moved to the
Bandanix palette (darker, slightly cool greys and the bandana-red accent). Standard library
only; if Pillow is available the PNG assets (checkboxes, radios...) are recoloured too.
"""

from __future__ import annotations

import argparse
import colorsys
import os
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

try:
    from PIL import Image
except ImportError:  # Pillow is optional
    Image = None

DEFAULT_ACCENT = "#C8102E"
TARGET_WINDOW_BG = 0.096          # lightness of #17171A, the Bandanix window background
DARK_LIMIT = 0.55                 # greys darker than this are moved to the Bandanix scale
COOL_HUE = 240 / 360              # Bandanix greys lean very slightly blue
COOL_SAT = 0.07
TEXT_SUFFIXES = {".css", ".svg", ".rc", ".xml", ".theme", ".json", ".scss"}
TEXT_NAMES = {"gtkrc", "themerc", "metacity-theme-1.xml", "metacity-theme-2.xml", "metacity-theme-3.xml"}

HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")  # 8 = with alpha
RGB_RE = re.compile(r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(,\s*[\d.]+\s*)?\)")


# ---- colour helpers ---------------------------------------------------------------
def hex_to_rgb(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")[:6]
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def hls(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    return colorsys.rgb_to_hls(*(c / 255 for c in rgb))


def from_hls(h: float, l: float, s: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hls_to_rgb(h, max(0.0, min(1.0, l)), max(0.0, min(1.0, s)))
    return round(r * 255), round(g * 255), round(b * 255)


def is_accent(rgb: tuple[int, int, int]) -> bool:
    h, l, s = hls(rgb)
    # narrow red band: keeps orange warnings (#f27835, ~21°) out
    return s >= 0.35 and 0.12 <= l <= 0.88 and (h <= 0.035 or h >= 0.95)


def is_neutral(rgb: tuple[int, int, int]) -> bool:
    _, _, s = hls(rgb)
    return s < 0.15


# ---- the colour mapping -------------------------------------------------------------
class Recolour:
    def __init__(self, source_accent, source_bg, target_accent):
        self.src_accent = hls(source_accent)
        self.src_bg_l = hls(source_bg)[1]
        self.dst_accent = hls(target_accent)
        self.cache: dict[tuple[int, int, int], tuple[int, int, int]] = {}

    def dark_lightness(self, l: float) -> float:
        """Piecewise-linear: 0 stays 0, window bg -> Bandanix bg, DARK_LIMIT stays put."""
        a = self.src_bg_l
        if l <= a:
            return l * TARGET_WINDOW_BG / a if a else l
        return TARGET_WINDOW_BG + (l - a) * (DARK_LIMIT - TARGET_WINDOW_BG) / (DARK_LIMIT - a)

    def __call__(self, rgb: tuple[int, int, int]) -> tuple[int, int, int]:
        if rgb in self.cache:
            return self.cache[rgb]
        h, l, s = hls(rgb)
        out = rgb
        if is_accent(rgb):
            sh, sl, ss = self.src_accent
            dh, dl, ds = self.dst_accent
            out = from_hls(dh, dl + (l - sl), ds)   # keep hover/pressed steps, Bandanix saturation
        elif is_neutral(rgb) and l < DARK_LIMIT:
            new_l = self.dark_lightness(l)
            out = from_hls(COOL_HUE, new_l, COOL_SAT if new_l < 0.35 else s)
        self.cache[rgb] = out
        return out


# ---- reading the source theme ---------------------------------------------------------
def text_files(root: Path):
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink() and (
                path.suffix in TEXT_SUFFIXES or path.name in TEXT_NAMES):
            yield path


def colours_in(text: str) -> list[tuple[int, int, int]]:
    found = [hex_to_rgb(m.group(0)) for m in HEX_RE.finditer(text)]
    found += [(int(m.group(1)), int(m.group(2)), int(m.group(3))) for m in RGB_RE.finditer(text)]
    return found


def detect(source: Path) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """Most used red = the theme's accent; most used dark grey in GTK3 = window background."""
    accents, darks = Counter(), Counter()
    for path in text_files(source):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for rgb in colours_in(text):
            if is_accent(rgb):
                accents[rgb] += 1
            elif is_neutral(rgb) and 0.10 <= hls(rgb)[1] <= 0.35 and "gtk-3" in str(path):
                darks[rgb] += 1
    if not accents:
        sys.exit("Kaynak temada kırmızı vurgu rengi bulunamadı.")
    if not darks:
        sys.exit("Kaynak temada koyu zemin rengi bulunamadı.")
    return accents.most_common(1)[0][0], darks.most_common(1)[0][0]


# ---- rewriting --------------------------------------------------------------------
def rewrite_text(path: Path, recolour: Recolour) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return 0
    changes = 0

    def hex_sub(m):
        nonlocal changes
        old = hex_to_rgb(m.group(0))
        new = recolour(old)
        if new == old:
            return m.group(0)
        changes += 1
        alpha = m.group(0)[7:] if len(m.group(0)) == 9 else ""
        return rgb_to_hex(new) + alpha

    def rgb_sub(m):
        nonlocal changes
        old = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        new = recolour(old)
        if new == old:
            return m.group(0)
        changes += 1
        alpha = m.group(4)
        return f"rgba({new[0]}, {new[1]}, {new[2]}{alpha})" if alpha else f"rgb({new[0]}, {new[1]}, {new[2]})"

    text = HEX_RE.sub(hex_sub, text)
    text = RGB_RE.sub(rgb_sub, text)
    if changes:
        path.write_text(text, encoding="utf-8")
    return changes


def rewrite_png(path: Path, recolour: Recolour) -> bool:
    try:
        with Image.open(path) as img:
            img = img.convert("RGBA")
            flat = getattr(img, "get_flattened_data", None) or img.getdata
            pixels = list(flat())
            new = [(*recolour(p[:3]), p[3]) if p[3] else p for p in pixels]
            if new == pixels:
                return False
            img.putdata(new)
            img.save(path)
            return True
    except Exception:            # an odd file must never break the whole build
        return False


PANEL_OVERRIDE = """
/* ---- Bandanix: panel ---- */
.panel-top, .panel-bottom, .panel-left, .panel-right {
  background-color: rgba(18, 18, 20, 0.92);
}
"""


def read_accent() -> str:
    path = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "bandanix" / "theme.toml"
    if tomllib and path.is_file():
        try:
            accent = tomllib.loads(path.read_text(encoding="utf-8")).get("colors", {}).get("accent")
            if isinstance(accent, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", accent):
                return accent
        except (OSError, ValueError):
            pass
    return DEFAULT_ACCENT


def gtk4_css(accent: str) -> str:
    acc = hex_to_rgb(accent)
    h, l, s = hls(acc)
    hover = rgb_to_hex(from_hls(h, l + 0.08, s))
    return f"""/* >>> bandanix >>> (Bandanix cinnamon-tema tarafından yazıldı) */
@define-color accent_color {rgb_to_hex(from_hls(h, l + 0.12, s))};
@define-color accent_bg_color {accent};
@define-color accent_fg_color #F5F3F0;
@define-color window_bg_color #17171A;
@define-color window_fg_color #E8E6E3;
@define-color view_bg_color #121214;
@define-color view_fg_color #E8E6E3;
@define-color headerbar_bg_color #121214;
@define-color headerbar_fg_color #E8E6E3;
@define-color sidebar_bg_color #1C1C1F;
@define-color card_bg_color #1C1C1F;
@define-color popover_bg_color #1C1C1F;
@define-color dialog_bg_color #1C1C1F;
@define-color destructive_bg_color {hover};
/* <<< bandanix <<< */
"""


def build(source: Path, target: Path, accent: str, name: str = "Bandanix") -> dict:
    if not (source / "gtk-3.0").is_dir():
        sys.exit(f"Kaynak tema bulunamadı ya da eksik: {source}")
    src_accent, src_bg = detect(source)
    recolour = Recolour(src_accent, src_bg, hex_to_rgb(accent))

    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, symlinks=False)   # dereference shared Mint-Y assets

    stats = {"source_accent": rgb_to_hex(src_accent), "source_bg": rgb_to_hex(src_bg),
             "text_files": 0, "colour_changes": 0, "png": 0, "png_supported": Image is not None}
    for path in text_files(target):
        n = rewrite_text(path, recolour)
        if n:
            stats["text_files"] += 1
            stats["colour_changes"] += n
    if Image is not None:
        for path in target.rglob("*.png"):
            if path.name == "thumbnail.png":
                continue
            stats["png"] += rewrite_png(path, recolour)

    index = target / "index.theme"
    if index.is_file():
        text = index.read_text(encoding="utf-8")
        # MetacityTheme stays as is: Mint-Y variants share the "Mint-Y" window borders
        text = re.sub(r"(?m)^(Name|GtkTheme)=.*$", lambda m: f"{m.group(1)}={name}", text)
        text = re.sub(r"(?m)^Comment=.*$", "Comment=Bandanix: Mint-Y tabanlı koyu tema", text)
        index.write_text(text, encoding="utf-8")

    cinnamon_css = target / "cinnamon" / "cinnamon.css"
    if cinnamon_css.is_file():
        with cinnamon_css.open("a", encoding="utf-8") as fh:
            fh.write(PANEL_OVERRIDE)
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Bandanix temasını Mint-Y-Dark-Red'den üretir.")
    parser.add_argument("--kaynak", default="/usr/share/themes/Mint-Y-Dark-Red")
    parser.add_argument("--hedef", default=str(Path.home() / ".themes" / "Bandanix"))
    parser.add_argument("--accent", default=None, help="#RRGGBB (varsayılan: theme.toml)")
    parser.add_argument("--gtk4-css", metavar="DOSYA", help="GTK4/libadwaita renk dosyasını da yaz")
    args = parser.parse_args()

    accent = args.accent or read_accent()
    stats = build(Path(args.kaynak), Path(args.hedef), accent)
    if args.gtk4_css:
        out = Path(args.gtk4_css)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(gtk4_css(accent), encoding="utf-8")
    print(f"• Tema üretildi: {args.hedef}")
    print(f"  Kaynak vurgu {stats['source_accent']} → {accent}, kaynak zemin {stats['source_bg']} → #17171a")
    print(f"  {stats['text_files']} dosyada {stats['colour_changes']} renk değişti", end="")
    if stats["png_supported"]:
        print(f", {stats['png']} resim boyandı")
    else:
        print(" (resim kütüphanesi yok, resimli öğeler Mint kırmızısında kaldı)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
