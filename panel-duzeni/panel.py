#!/usr/bin/python3
"""Bandanix panel layout: floating islands on a clear panel (centred like Windows 11, or three).

  panel.py uygula <tema-css>    move applets into islands, set height, add the island CSS
  panel.py kaldir <tema-css>    remove the island CSS (settings come back via bandanix-yedek)
  panel.py css <tema-css>       only (re)write the island CSS into a theme file

Standard library only; settings are changed with the `dconf` command.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
from bandanix_renk import hex_to_rgb, read_accent  # noqa: E402

APPLETS = "/org/cinnamon/enabled-applets"
HEIGHTS = "/org/cinnamon/panels-height"
THEME_KEY = "/org/cinnamon/theme/name"
PANEL_HEIGHT = 54   # default; theme.toml [panel] yukseklik overrides (40-64)
START, END = "/* >>> bandanix panel-duzeni >>> */", "/* <<< bandanix panel-duzeni <<< */"


# ---- applets -------------------------------------------------------------------------
def parse_list(value: str) -> list[str]:
    """dconf array text like ['a', 'b'] (or '@as []' / empty) -> list."""
    value = value.strip()
    if not value or value.startswith("@as"):
        return []
    return list(ast.literal_eval(value))


def to_gvariant(items: list[str]) -> str:
    return "[" + ", ".join("'" + i.replace("\\", "\\\\").replace("'", "\\'") + "'" for i in items) + "]"


LAYOUTS = ("orta", "uc-ada")   # orta: Windows 11 style (menu + windows centred) · uc-ada: three islands


def island_applets(applets: list[str], panel: str = "panel1", layout: str = "orta") -> list[str]:
    """Window list -> centre; menu -> centre in front of it ("orta") or left ("uc-ada");
    the separator next to them goes; the rest keep their zone. Applet instance ids stay the
    same, so no applet loses its settings."""
    others, ours = [], []
    for entry in applets:
        parts = entry.split(":")
        if len(parts) < 5 or parts[0] != panel:
            others.append(entry)
            continue
        ours.append(parts)

    zones: dict[str, list[list[str]]] = {"left": [], "center": [], "right": []}
    for parts in sorted(ours, key=lambda p: ({"left": 0, "center": 1, "right": 2}.get(p[1], 3), int(p[2]))):
        uuid = parts[3]
        if uuid.startswith("separator@") and parts[1] == "left":
            continue                                      # islands are already apart
        if uuid.startswith("menu@"):
            zone = "center" if layout == "orta" else "left"
        elif uuid.startswith(("grouped-window-list@", "window-list@")):
            zone = "center"
        else:
            zone = parts[1] if parts[1] in zones else "right"
        zones[zone].append(parts)

    result = []
    for zone in ("left", "center", "right"):
        for order, parts in enumerate(zones[zone]):
            result.append(":".join([parts[0], zone, str(order)] + parts[3:]))
    return result + others


ICON_SIZES = "/org/cinnamon/panel-zone-icon-sizes"
ISLAND_ICON = 32     # px setting; drawn ~26px, a bit over half the 41px island, with room around it


def panel_setting(key: str):
    path = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "bandanix" / "theme.toml"
    try:
        import tomllib
        return tomllib.loads(path.read_text(encoding="utf-8")).get("panel", {}).get(key)
    except (ImportError, OSError, ValueError):
        return None


def icon_size() -> int:
    """[panel] ikon_boyutu from theme.toml (16-48), else ISLAND_ICON."""
    value = panel_setting("ikon_boyutu")
    return value if isinstance(value, int) and 16 <= value <= 48 else ISLAND_ICON


def panel_height() -> int:
    """[panel] yukseklik from theme.toml (40-64 px), else PANEL_HEIGHT. The island is this
    minus a 6px gap above and below; its pictures are redrawn for the height."""
    value = panel_setting("yukseklik")
    return value if isinstance(value, int) and 40 <= value <= 64 else PANEL_HEIGHT


def layout() -> str:
    """[panel] duzen from theme.toml: "orta" (default) or "uc-ada"."""
    value = panel_setting("duzen")
    return value if value in LAYOUTS else "orta"


def new_icon_sizes(value: str, panel_id: int = 1, size: int | None = None) -> str:
    """Fixed colour icon size in the left/centre zones. Cinnamon's default there is 0
    ("scale with the panel"), which grows the icons past the islands on a 48px panel."""
    size = size or icon_size()
    raw = value.strip()
    try:
        text = ast.literal_eval(raw) if raw else ""
        zones = json.loads(text) if text else []
    except (ValueError, SyntaxError):
        zones = []
    if not isinstance(zones, list):
        zones = []
    for zone in zones:
        if isinstance(zone, dict) and zone.get("panelId") == panel_id:
            zone.update(left=size, center=size)
            break
    else:
        zones.append({"panelId": panel_id, "left": size, "center": size, "right": 24})
    return "'" + json.dumps(zones) + "'"


def new_heights(heights: list[str], panel_id: str = "1") -> list[str]:
    out, found = [], False
    for item in heights:
        pid, _, _ = item.partition(":")
        if pid == panel_id:
            item, found = f"{pid}:{panel_height()}", True
        out.append(item)
    if not found:
        out.append(f"{panel_id}:{panel_height()}")
    return out


# ---- CSS -----------------------------------------------------------------------------
ISLAND_SVG = "bandanix-ada.svg"
GAP = 6              # transparent space above and below each island, in px


def radius() -> int:
    """Half the island height, so its ends are always full half-circles (a true pill)."""
    return (panel_height() - 2 * GAP) // 2


def island_svg(accent: str) -> str:
    """One panel-height tall picture of an island: transparent rows on top and bottom,
    a rounded #121214 pill in between with a faint accent outline. Cinnamon stretches its
    middle sideways (9-slice border-image), so corners never distort."""
    r, g, b = hex_to_rgb(accent)
    h = panel_height()
    rad = radius()
    w = 2 * rad + 12
    pill_h = h - 2 * GAP - 1
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<rect x="0.5" y="{GAP + 0.5}" width="{w - 1}" height="{pill_h}" rx="{rad - 0.5}" '
            f'fill="#121214" fill-opacity="0.92" stroke="rgb({r},{g},{b})" stroke-opacity="0.35" '
            f'stroke-width="1"/></svg>\n')


HOVER_SVG = "bandanix-ada-uzerinde.svg"
RUNNING_SVG = "bandanix-ada-calisiyor.svg"
ACTIVE_SVG = "bandanix-ada-aktif.svg"
BUTTON_SLICE = 15    # px kept fixed on each side; the window-list buttons are all the same width


def button_svg(accent: str, highlight: bool, line: bool) -> str:
    """Window-list button states drawn inside the island: a soft rounded highlight and/or a
    short accent line just under the icon, near the island's bottom edge (not the panel's)."""
    r, g, b = hex_to_rgb(accent)
    h, w = panel_height(), 2 * BUTTON_SLICE + 2
    top, bottom = GAP + 3, h - GAP - 3
    parts = []
    if highlight:
        parts.append(f'<rect x="1" y="{top}" width="{w - 2}" height="{bottom - top}" rx="9" '
                     f'fill="#ffffff" fill-opacity="0.08"/>')
    if line:   # middle part stretches, so the line is (button width - 2*(slice-4)) wide
        parts.append(f'<rect x="{BUTTON_SLICE - 4}" y="{bottom - 4}" width="{w - 2 * (BUTTON_SLICE - 4)}" '
                     f'height="3" rx="1.5" fill="rgb({r},{g},{b})"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            + "".join(parts) + "</svg>\n")


def island_css(accent: str, layout: str = "orta") -> str:
    zones = []
    for z in (("Center", "Right") if layout == "orta" else ("Left", "Center", "Right")):
        for base in (f"#panel{z}", f".panel{z}"):
            zones += [f".panel-bottom {base}", f".panel-bottom {base}:ltr", f".panel-bottom {base}:rtl"]
    left = ", ".join(s for s in zones if "Left" in s) or ".panel-bottom #panelLeft"
    right = ", ".join(s for s in zones if "Right" in s)
    every = ",\n".join(zones)
    half = panel_height() // 2
    rad = radius()
    return f"""{START}
/* The panel itself is invisible; each zone is a floating, rounded island.
   The window list makes its buttons exactly as tall as the panel and starts them at the
   top of the zone's content, so padding, borders or margins would push its icons down.
   The island is therefore only painted: a 9-slice border-image ({ISLAND_SVG}) with
   transparent rows above and below, while the zone keeps the full panel height and the
   icons stay on the island's centre line. */
.panel-bottom {{
  background-color: transparent;
  background-gradient-direction: none;
  box-shadow: none;
  border: none;
  padding: 0;
}}
{every} {{
  background-color: transparent;
  border: none;
  border-image: url("{ISLAND_SVG}") {half} {rad} {half} {rad};
  padding-left: 16px;
  padding-right: 16px;
  spacing: 6px;
}}
{left} {{ margin-left: 8px; }}
{right} {{ margin-right: 8px; }}
/* window-list buttons are panel-tall too: keep their highlight and the focus line inside
   the island instead of Mint-Y's full-height box and bottom border */
.panel-bottom .grouped-window-list-item-box,
.panel-bottom .grouped-window-list-item-box.bottom {{
  border: none;
  border-bottom-width: 0;
  background-color: transparent;
  border-image: none;
  padding-left: 10px;
  padding-right: 10px;
}}
.panel-bottom .grouped-window-list-item-box:hover,
.panel-bottom .grouped-window-list-item-box:focus {{
  background-color: transparent;
  border-image: url("{HOVER_SVG}") {half} {BUTTON_SLICE} {half} {BUTTON_SLICE};
}}
/* has open windows: a short accent line under the icon */
.panel-bottom .grouped-window-list-item-box:active {{
  background-color: transparent;
  border-image: url("{RUNNING_SVG}") {half} {BUTTON_SLICE} {half} {BUTTON_SLICE};
}}
/* the focused window: soft highlight + line */
.panel-bottom .grouped-window-list-item-box:checked {{
  background-color: transparent;
  border-image: url("{ACTIVE_SVG}") {half} {BUTTON_SLICE} {half} {BUTTON_SLICE};
}}
{END}
"""


def strip_block(text: str) -> str:
    return re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", text, flags=re.S)


def write_css(theme_css: Path, accent: str, layout: str = "orta") -> None:
    (theme_css.parent / ISLAND_SVG).write_text(island_svg(accent), encoding="utf-8")
    (theme_css.parent / HOVER_SVG).write_text(button_svg(accent, True, False), encoding="utf-8")
    (theme_css.parent / RUNNING_SVG).write_text(button_svg(accent, False, True), encoding="utf-8")
    (theme_css.parent / ACTIVE_SVG).write_text(button_svg(accent, True, True), encoding="utf-8")
    text = strip_block(theme_css.read_text(encoding="utf-8"))
    theme_css.write_text(text.rstrip("\n") + "\n\n" + island_css(accent, layout), encoding="utf-8")


def remove_css(theme_css: Path) -> None:
    for name in (ISLAND_SVG, HOVER_SVG, RUNNING_SVG, ACTIVE_SVG):
        (theme_css.parent / name).unlink(missing_ok=True)
    if theme_css.is_file():
        theme_css.write_text(strip_block(theme_css.read_text(encoding="utf-8")), encoding="utf-8")


# ---- menu icon: the red bandana instead of the Mint logo ---------------------------------
DATA = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "bandanix" / "panel-duzeni"
MENU_ICON = DATA / "bandana-menu.svg"
YEDEK = Path.home() / ".local/bin/bandanix-yedek"


def bandana_svg(accent: str) -> str:
    """The Bandanix mark: a folded bandana triangle with dots."""
    r, g, b = hex_to_rgb(accent)
    dots = []
    for y, xs in ((24, (16, 24, 32, 40, 48)), (34, (24, 32, 40)), (44, (32,))):
        dots += [f'<circle cx="{x}" cy="{y}" r="2.6" fill="#121214"/>' for x in xs]
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">'
            f'<path d="M4 14 H60 L32 56 Z" fill="rgb({r},{g},{b})" stroke-linejoin="round"/>'
            '<rect x="4" y="14" width="56" height="2.5" fill="#121214" fill-opacity="0.35"/>'
            + "".join(dots) + "</svg>\n")


def menu_config_files(applets: list[str]) -> list[Path]:
    """Settings files of the menu applet(s) on panel 1 (new and old Cinnamon locations)."""
    files = []
    for entry in applets:
        parts = entry.split(":")
        if len(parts) >= 5 and parts[0] == "panel1" and parts[3].startswith("menu@"):
            for base in (Path.home() / ".config/cinnamon/spices", Path.home() / ".cinnamon/configs"):
                path = base / parts[3] / f"{parts[4]}.json"
                if path.is_file():
                    files.append(path)
                    break
    return files


def set_menu_icon(path: Path, icon: Path) -> bool:
    """Point the menu applet at a custom icon (no label). Unknown file layouts are left alone."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(data.get("menu-icon"), dict):
        return False
    data["menu-icon"]["value"] = str(icon)
    for key, value in (("menu-custom", True), ("menu-label", "")):
        if isinstance(data.get(key), dict):
            data[key]["value"] = value
    path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
    return True


def apply_menu_icon(applets: list[str], accent: str) -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    MENU_ICON.write_text(bandana_svg(accent), encoding="utf-8")
    changed = 0
    for path in menu_config_files(applets):
        rel = path.relative_to(Path.home())
        if YEDEK.is_file():   # remember the original settings file before editing it
            subprocess.run([str(YEDEK), "isaretle", "panel-duzeni", f"dosya:~/{rel}"], check=False)
        changed += set_menu_icon(path, MENU_ICON)
    return changed


# ---- dconf / Cinnamon -------------------------------------------------------------------
def dconf_read(key: str) -> str:
    return subprocess.run(["dconf", "read", key], capture_output=True, text=True).stdout.strip()


def dconf_write(key: str, value: str) -> None:
    subprocess.run(["dconf", "write", key, value], check=True)


def reload_theme() -> None:
    """Cinnamon only re-reads CSS when the theme name changes: switch away and back."""
    current = dconf_read(THEME_KEY)
    if current.strip("'") != "Bandanix":
        return
    dconf_write(THEME_KEY, "'Mint-Y-Dark-Red'")
    time.sleep(1)
    dconf_write(THEME_KEY, current)


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in ("uygula", "kaldir", "css"):
        print(__doc__.strip())
        return 1
    cmd, css_path = argv[1], Path(argv[2])
    if cmd == "kaldir":
        remove_css(css_path)
        reload_theme()
        return 0
    write_css(css_path, read_accent(), layout())
    if cmd == "uygula":
        before = parse_list(dconf_read(APPLETS))
        after = island_applets(before, layout=layout())
        if after != before:
            dconf_write(APPLETS, to_gvariant(after))
        dconf_write(HEIGHTS, to_gvariant(new_heights(parse_list(dconf_read(HEIGHTS)))))
        dconf_write(ICON_SIZES, new_icon_sizes(dconf_read(ICON_SIZES)))
        if not apply_menu_icon(after, read_accent()):
            print("• Menü ikonu değiştirilemedi; menüye sağ tıklayıp Yapılandır'dan elle seçebilirsin:")
            print(f"  {MENU_ICON}")
    reload_theme()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
