#!/usr/bin/env python3
"""bandanix-widget: weather for the Bandanix desktop clock.

  bandanix-widget                 city and the last weather reading
  bandanix-widget sehir Ankara    change the city (asks when the name is ambiguous)
  bandanix-widget guncelle        fetch the weather now (the timer does this every 30 min)

Weather comes from Open-Meteo (free, no account). The desklet only reads the JSON file
this program writes, so Cinnamon itself never waits on the network.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
import bandanix_tema  # noqa: E402  (shared theme.toml writer)

HOME = Path.home()
THEME = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config") / "bandanix" / "theme.toml"
CACHE = Path(os.environ.get("XDG_CACHE_HOME") or HOME / ".cache") / "bandanix" / "hava.json"
GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
UUID = "bandanix-saat@furkansagsoyu"
DESKLET_WIDTH = 1000
AGENT = "Bandanix-widget/1.0 (+https://github.com/furkansagsoyu/bandanix)"

USAGE = """Kullanım:
  bandanix-widget                 şehir ve son hava durumu
  bandanix-widget sehir Ankara    şehri değiştir
  bandanix-widget guncelle        hava durumunu hemen yenile
  bandanix-widget ortala          saati ekranın ortasındaki varsayılan yerine al"""

DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

# WMO weather codes -> (Turkish text, day icon, night icon)
FEW = ("weather-few-clouds-symbolic", "weather-few-clouds-night-symbolic")
CODES = {
    0: ("Açık", "weather-clear-symbolic", "weather-clear-night-symbolic"),
    1: ("Çoğunlukla açık", *FEW),
    2: ("Parçalı bulutlu", *FEW),
    3: ("Kapalı", "weather-overcast-symbolic", "weather-overcast-symbolic"),
    45: ("Sisli", "weather-fog-symbolic", "weather-fog-symbolic"),
    48: ("Kırağılı sis", "weather-fog-symbolic", "weather-fog-symbolic"),
    51: ("Hafif çisenti", "weather-showers-scattered-symbolic", "weather-showers-scattered-symbolic"),
    53: ("Çisenti", "weather-showers-scattered-symbolic", "weather-showers-scattered-symbolic"),
    55: ("Yoğun çisenti", "weather-showers-scattered-symbolic", "weather-showers-scattered-symbolic"),
    56: ("Dondurucu çisenti", "weather-showers-scattered-symbolic", "weather-showers-scattered-symbolic"),
    57: ("Dondurucu çisenti", "weather-showers-scattered-symbolic", "weather-showers-scattered-symbolic"),
    61: ("Hafif yağmurlu", "weather-showers-scattered-symbolic", "weather-showers-scattered-symbolic"),
    63: ("Yağmurlu", "weather-showers-symbolic", "weather-showers-symbolic"),
    65: ("Şiddetli yağmur", "weather-showers-symbolic", "weather-showers-symbolic"),
    66: ("Dondurucu yağmur", "weather-showers-symbolic", "weather-showers-symbolic"),
    67: ("Dondurucu yağmur", "weather-showers-symbolic", "weather-showers-symbolic"),
    71: ("Hafif kar", "weather-snow-symbolic", "weather-snow-symbolic"),
    73: ("Karlı", "weather-snow-symbolic", "weather-snow-symbolic"),
    75: ("Yoğun kar", "weather-snow-symbolic", "weather-snow-symbolic"),
    77: ("Kar taneleri", "weather-snow-symbolic", "weather-snow-symbolic"),
    80: ("Hafif sağanak", "weather-showers-scattered-symbolic", "weather-showers-scattered-symbolic"),
    81: ("Sağanak", "weather-showers-symbolic", "weather-showers-symbolic"),
    82: ("Şiddetli sağanak", "weather-showers-symbolic", "weather-showers-symbolic"),
    85: ("Kar sağanağı", "weather-snow-symbolic", "weather-snow-symbolic"),
    86: ("Yoğun kar sağanağı", "weather-snow-symbolic", "weather-snow-symbolic"),
    95: ("Gök gürültülü fırtına", "weather-storm-symbolic", "weather-storm-symbolic"),
    96: ("Dolulu fırtına", "weather-storm-symbolic", "weather-storm-symbolic"),
    99: ("Dolulu fırtına", "weather-storm-symbolic", "weather-storm-symbolic"),
}


def describe(code, is_day: bool = True) -> tuple[str, str]:
    text, day, night = CODES.get(code if isinstance(code, int) else -1,
                                 ("Bilinmiyor", "weather-severe-alert-symbolic", "weather-severe-alert-symbolic"))
    return text, day if is_day else night


# ---- theme.toml [widget] ----------------------------------------------------------------
SECTION = "[widget]"


def read_section(name: str) -> dict:
    out, current = {}, ""
    try:
        lines = THEME.read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for line in lines:
        s = line.strip()
        if s.startswith("["):
            current = s
        elif current == name:
            m = re.match(r'^([a-z_]+)\s*=\s*("([^"]*)"|-?\d+(\.\d+)?)', s)
            if m:
                out[m.group(1)] = m.group(3) if m.group(3) is not None else float(m.group(2))
    return out


def write_section(values: dict) -> None:
    bandanix_tema.set_values("widget", values, THEME)


# ---- network ----------------------------------------------------------------------------
def get_json(url: str, params: dict) -> dict:
    req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}",
                                 headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def search_city(name: str) -> list[dict]:
    data = get_json(GEO_URL, {"name": name, "count": 6, "language": "tr", "format": "json"})
    results = data.get("results") or []
    return [r for r in results if isinstance(r, dict) and "latitude" in r and "longitude" in r]


def place_label(r: dict) -> str:
    parts = [r.get("name", "")]
    for key in ("admin1", "country"):
        if r.get(key) and r.get(key) not in parts:
            parts.append(r[key])
    return ", ".join(p for p in parts if p)


def build_weather(data: dict, city: str, now: float) -> dict:
    cur = data.get("current") or {}
    daily = data.get("daily") or {}
    text, icon = describe(cur.get("weather_code"), bool(cur.get("is_day", 1)))
    today = (cur.get("time") or "")[:10]
    days = []
    for i, day in enumerate(daily.get("time") or []):
        if day <= today:
            continue                                  # forecast starts tomorrow
        try:
            hi, lo = daily["temperature_2m_max"][i], daily["temperature_2m_min"][i]
            code = daily["weather_code"][i]
            weekday = DAYS[dt.date.fromisoformat(day).weekday()]
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        dtext, dicon = describe(code, True)
        days.append({"tarih": day, "gun": weekday, "yazi": dtext, "ikon": dicon,
                     "en_yuksek": round(hi), "en_dusuk": round(lo)})
        if len(days) == 3:
            break
    temp = cur.get("temperature_2m")
    return {
        "guncellendi": now,
        "son_deneme": now,
        "sehir": city,
        "simdi": {"sicaklik": None if temp is None else round(temp), "yazi": text, "ikon": icon},
        "gunler": days,
    }


def write_cache(data: dict) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, CACHE)


def read_cache() -> dict:
    try:
        data = json.loads(CACHE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


# ---- commands ---------------------------------------------------------------------------
def cmd_update(quiet: bool = False) -> int:
    cfg = read_section(SECTION)
    lat, lon = cfg.get("enlem"), cfg.get("boylam")
    if not isinstance(lat, float) or not isinstance(lon, float):
        if not quiet:
            print("• Şehir ayarlı değil. Ayarlamak için: bandanix-widget sehir <şehir adı>")
        return 1
    now = time.time()
    try:
        data = get_json(FORECAST_URL, {
            "latitude": f"{lat:.4f}", "longitude": f"{lon:.4f}",
            "current": "temperature_2m,weather_code,is_day",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "timezone": "auto", "forecast_days": 5,
        })
        write_cache(build_weather(data, str(cfg.get("sehir", "")), now))
    except (OSError, ValueError) as err:
        old = read_cache()
        old["son_deneme"] = now
        old["hata"] = "güncellenemedi"
        write_cache(old)
        if not quiet:
            print(f"• Hava durumu alınamadı ({err.__class__.__name__}). Son bilgi gösterilmeye devam ediyor.")
        return 1
    if not quiet:
        show()
    return 0


def choose(results: list[dict]) -> dict | None:
    if len(results) == 1 or not sys.stdin.isatty():
        return results[0]
    print("Birden fazla yer bulundu:")
    for i, r in enumerate(results, 1):
        print(f"  {i}) {place_label(r)}")
    while True:
        answer = input(f"Hangisi? [1-{len(results)}, Enter = 1] ").strip()
        if not answer:
            return results[0]
        if answer.isdigit() and 1 <= int(answer) <= len(results):
            return results[int(answer) - 1]


def cmd_city(name: str) -> int:
    name = name.strip()
    if not name:
        print("• Şehir adı boş olamaz.")
        return 2
    try:
        results = search_city(name)
    except (OSError, ValueError):
        print("• Konum aranamadı (internet bağlantısı var mı?). Sonra tekrar dene: bandanix-widget sehir <şehir>")
        return 1
    if not results:
        print(f"• \"{name}\" bulunamadı. Yazımı kontrol edip tekrar dene.")
        return 1
    place = choose(results)
    write_section({"sehir": place.get("name", name), "enlem": float(place["latitude"]),
                   "boylam": float(place["longitude"])})
    print(f"• Şehir: {place_label(place)}")
    return cmd_update()


def show() -> int:
    cfg = read_section(SECTION)
    data = read_cache()
    if not cfg.get("sehir"):
        print("• Şehir ayarlı değil. Ayarlamak için: bandanix-widget sehir <şehir adı>")
        return 0
    print(f"Şehir       {cfg['sehir']}")
    now = data.get("simdi") or {}
    if now.get("sicaklik") is not None:
        print(f"Şimdi       {now['sicaklik']}°C  {now.get('yazi', '')}")
    for d in data.get("gunler") or []:
        print(f"{d['gun']:<12}{d['en_yuksek']}° / {d['en_dusuk']}°  {d['yazi']}")
    if data.get("guncellendi"):
        when = dt.datetime.fromtimestamp(data["guncellendi"]).strftime("%d.%m %H:%M")
        note = "  (son deneme başarısız)" if data.get("hata") else ""
        print(f"Güncellendi {when}{note}")
    return 0


# ---- used by install.sh ----------------------------------------------------------------
def screen_box() -> tuple[int, int, int, int]:
    try:
        out = subprocess.run(["xrandr", "--current"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        out = ""
    lines = [l for l in out.splitlines() if " connected" in l]
    for line in sorted(lines, key=lambda l: " primary " not in l):
        m = re.search(r"(\d+)x(\d+)\+(\d+)\+(\d+)", line)
        if m:
            w, h, x, y = map(int, m.groups())
            return x, y, w, h
    return 0, 0, 1920, 1080


def theme_look() -> tuple[str, str]:
    """(accent, font) from theme.toml."""
    try:
        import tomllib
        data = tomllib.loads(THEME.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    colors = data.get("colors") if isinstance(data.get("colors"), dict) else {}
    fonts = data.get("fonts") if isinstance(data.get("fonts"), dict) else {}
    accent, font = colors.get("accent"), fonts.get("ui")
    return (accent if isinstance(accent, str) else "#C8102E",
            font.strip() if isinstance(font, str) else "")


def cmd_install_desklet(src: str, dst: str) -> int:
    """Copy the desklet, filling in the accent colour and font."""
    accent, font = theme_look()
    src_dir, dst_dir = Path(src), Path(dst)
    dst_dir.mkdir(parents=True, exist_ok=True)
    hexes = r"#([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})"
    m = re.fullmatch(hexes, accent) or re.fullmatch(hexes, "#C8102E")
    rgb = ", ".join(str(int(g, 16)) for g in m.groups())
    family = f'font-family: "{font}";' if font and '"' not in font and ";" not in font else ""
    for f in src_dir.iterdir():
        text = f.read_text(encoding="utf-8")
        if f.name == "stylesheet.css":
            text = text.replace("__ACCENT_RGB__", rgb).replace("/*__FONT__*/", family)
        (dst_dir / f.name).write_text(text, encoding="utf-8")
    return 0


def parse_list(value: str) -> list[str]:
    return re.findall(r"'([^']*)'", value)


def gv_list(items: list[str]) -> str:
    return "[" + ", ".join("'" + i.replace("'", "") + "'" for i in items) + "]" if items else "@as []"


def dconf(*args: str) -> str:
    return subprocess.run(["dconf", *args], capture_output=True, text=True).stdout.strip()


THEME_PADDING = 15      # Cinnamon themes pad desklets; without this the clock sits right of centre


def default_position() -> tuple[int, int]:
    """Centred, low enough that Sound Island's open player does not cover the clock."""
    sx, sy, sw, sh = screen_box()
    return sx + max(0, (sw - DESKLET_WIDTH) // 2 - THEME_PADDING), sy + round(sh * 0.255)


def cmd_center() -> int:
    key = "/org/cinnamon/enabled-desklets"
    items = parse_list(dconf("read", key))
    x, y = default_position()
    moved = [f"{UUID}:{i.split(':')[1]}:{x}:{y}" if i.split(":")[0] == UUID else i for i in items]
    if moved == items and not any(i.split(":")[0] == UUID for i in items):
        print("• Saat masaüstünde değil. Eklemek için: ./install.sh widget")
        return 1
    dconf("write", key, gv_list([i for i in items if i.split(":")[0] != UUID]))
    dconf("write", key, gv_list(moved))
    print("• Saat ekranın ortasına alındı.")
    return 0


def cmd_enable_desklet() -> int:
    """Add the desklet (centred, a fifth from the top) or re-add it so Cinnamon reloads it."""
    key = "/org/cinnamon/enabled-desklets"
    items = parse_list(dconf("read", key))
    ours = [i for i in items if i.split(":")[0] == UUID]
    others = [i for i in items if i.split(":")[0] != UUID]
    if ours:
        entry = ours[0]
        dconf("write", key, gv_list(others))           # take it out and put it back:
    else:                                              # Cinnamon reloads the new code
        raw = dconf("read", "/org/cinnamon/next-desklet-id")
        next_id = int(raw) if raw.lstrip("-").isdigit() else 0
        used = {int(i.split(":")[1]) for i in items if i.count(":") >= 3 and i.split(":")[1].isdigit()}
        while next_id in used:
            next_id += 1
        dconf("write", "/org/cinnamon/next-desklet-id", str(next_id + 1))
        x, y = default_position()
        entry = f"{UUID}:{next_id}:{x}:{y}"
    dconf("write", key, gv_list(others + [entry]))
    return 0


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else ""
    if not argv:
        return show()
    if cmd == "sehir":
        if len(argv) < 2:
            if not sys.stdin.isatty():
                return 2
            argv = argv + [input("Hava durumu için şehrin: ")]
        return cmd_city(" ".join(argv[1:]))
    if cmd == "ortala" and len(argv) == 1:
        return cmd_center()
    if cmd == "guncelle" and len(argv) == 1:
        return cmd_update()
    if cmd == "_zamanlayici":
        return cmd_update(quiet=True)
    if cmd == "_sehir-var":
        return 0 if isinstance(read_section(SECTION).get("enlem"), float) else 1
    if cmd == "_desklet-kopyala" and len(argv) == 3:
        return cmd_install_desklet(*argv[1:])
    if cmd == "_ara" and len(argv) >= 2:          # for Bandanix Ayarlar: matches as JSON
        try:
            found = search_city(" ".join(argv[1:]))
        except (OSError, ValueError):
            print("null")
            return 1
        print(json.dumps([{"ad": place_label(r), "sehir": r.get("name", ""),
                           "enlem": r["latitude"], "boylam": r["longitude"]} for r in found],
                         ensure_ascii=False))
        return 0
    if cmd == "_sec" and len(argv) == 4:          # for Bandanix Ayarlar: name lat lon
        try:
            lat, lon = float(argv[2]), float(argv[3])
        except ValueError:
            return 2
        write_section({"sehir": argv[1], "enlem": lat, "boylam": lon})
        return cmd_update(quiet=True)
    if cmd == "_desklet-ac":
        return cmd_enable_desklet()
    helped = cmd in ("-h", "--help", "yardim")
    print(USAGE, file=sys.stdout if helped else sys.stderr)
    return 0 if helped else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
