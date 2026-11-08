#!/usr/bin/env python3
"""bandanix-giris: the Bandanix look for Linux Mint's login screen (Slick Greeter).

  bandanix-giris              current login screen settings
  bandanix-giris guncelle     rebuild the background from the current wallpaper (asks for the password)
  bandanix-giris dene         show the login screen in a window, without logging out

The login screen runs as the system's own user and cannot read the home folder, so the
background, theme, icons and cursor are copied to system folders (each with a marker file,
so uninstalling removes only what Bandanix put there).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse

HOME = Path.home()
ROOT = Path(os.environ.get("BANDANIX_GIRIS_KOK", "/"))          # tests point this elsewhere
CONF = ROOT / "etc/lightdm/slick-greeter.conf"
BACKUP = ROOT / "etc/lightdm/slick-greeter.conf.bandanix-yedek"
NO_CONF = ROOT / "etc/lightdm/.slick-greeter.conf.bandanix-yoktu"
BG_DIR = ROOT / "usr/share/backgrounds/bandanix"
BG = BG_DIR / "giris.png"
MARK = ".bandanix"
SUDO = os.environ.get("BANDANIX_GIRIS_SUDO", "sudo").split()

DATA = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local" / "share")
# (user copy, system copy, greeter key)
PARTS = [
    (HOME / ".themes" / "Bandanix", ROOT / "usr/share/themes/Bandanix", "theme-name"),
    (DATA / "icons" / "Bandanix", ROOT / "usr/share/icons/Bandanix", "icon-theme-name"),
    (HOME / ".icons" / "Bandanix-Imlec", ROOT / "usr/share/icons/Bandanix-Imlec", "cursor-theme-name"),
]
FIXED = {"background": str(Path("/usr/share/backgrounds/bandanix/giris.png")),
         "draw-user-backgrounds": "false", "draw-grid": "false", "clock-format": "%H:%M"}
OUR_KEYS = list(FIXED) + [key for *_, key in PARTS]
WALL_RE = re.compile(r"^(bandanix-[a-z]+)-(sabah|ogle|aksam|gece)\.png$")

USAGE = """Kullanım:
  bandanix-giris              giriş ekranının şu anki ayarları
  bandanix-giris guncelle     arka planı şu anki duvar kağıdından yeniden üret (şifre ister)
  bandanix-giris dene         giriş ekranını oturumu kapatmadan bir pencerede göster"""


def say(msg: str) -> None:
    print(f"• {msg}")


def sudo(*cmd: str) -> None:
    subprocess.run([*SUDO, *cmd], check=True)


# ---- the background ---------------------------------------------------------------------
def current_wallpaper() -> Path | None:
    """The desktop's wallpaper; for a Bandanix one, its night tone."""
    try:
        uri = subprocess.run(["dconf", "read", "/org/cinnamon/desktop/background/picture-uri"],
                             capture_output=True, text=True).stdout.strip().strip("'")
    except OSError:
        uri = ""
    path = Path(unquote(urlparse(uri).path)) if uri.startswith("file://") else None
    if path is None or not path.is_file():
        return None
    m = WALL_RE.match(path.name)
    if m and (path.parent / f"{m.group(1)}-gece.png").is_file():
        return path.parent / f"{m.group(1)}-gece.png"
    return path


def screen_size() -> tuple[int, int]:
    try:
        out = subprocess.run(["xrandr", "--current"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        out = ""
    lines = sorted((l for l in out.splitlines() if " connected" in l), key=lambda l: " primary " not in l)
    for line in lines:
        m = re.search(r"(\d+)x(\d+)\+\d+\+\d+", line)
        if m:
            return int(m.group(1)), int(m.group(2))
    return 1920, 1080


def make_background(source: Path | None, target: Path, size: tuple[int, int]) -> None:
    """Blurred and darkened copy of the wallpaper (plain dark if there is none)."""
    from PIL import Image, ImageEnhance, ImageFilter
    w, h = size
    if source is not None:
        img = Image.open(source).convert("RGB")
        scale = max(w / img.width, h / img.height)
        img = img.resize((max(w, round(img.width * scale)), max(h, round(img.height * scale))), Image.LANCZOS)
        left, top = (img.width - w) // 2, (img.height - h) // 2
        img = img.crop((left, top, left + w, top + h))
        img = img.filter(ImageFilter.GaussianBlur(radius=max(6, w // 110)))
        img = ImageEnhance.Brightness(img).enhance(0.85)
    else:
        img = Image.new("RGB", (w, h), (23, 23, 26))
    img.save(target, optimize=True)


# ---- slick-greeter.conf -----------------------------------------------------------------
def set_keys(text: str, values: dict[str, str | None]) -> str:
    """Set (or with None remove) keys in [Greeter], keeping every other line."""
    lines = text.splitlines()
    out, section, todo = [], "", dict(values)
    for line in lines:
        s = line.strip()
        if s.startswith("["):
            if section == "[Greeter]":
                while out and not out[-1].strip():
                    out.pop()
                out += [f"{k}={v}" for k, v in todo.items() if v is not None]
                todo.clear()
                out.append("")
            section = s
        elif section == "[Greeter]":
            key = s.split("=", 1)[0].strip() if "=" in s and not s.startswith("#") else ""
            if key in todo:
                value = todo.pop(key)
                if value is not None:
                    out.append(f"{key}={value}")
                continue
        out.append(line)
    if section == "[Greeter]":
        out += [f"{k}={v}" for k, v in todo.items() if v is not None]
    elif any(v is not None for v in todo.values()):
        if out and out[-1].strip():
            out.append("")
        out += ["[Greeter]"] + [f"{k}={v}" for k, v in todo.items() if v is not None]
    return "\n".join(out).strip("\n") + "\n"


def read_keys(text: str) -> dict[str, str]:
    out, section = {}, ""
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("["):
            section = s
        elif section == "[Greeter]" and "=" in s and not s.startswith("#"):
            k, v = s.split("=", 1)
            out[k.strip()] = v.strip()
    return out


# ---- commands ---------------------------------------------------------------------------
def copy_part(user: Path, system: Path) -> bool:
    if not user.is_dir():
        return False
    if system.exists() and not (system / MARK).exists():
        say(f"{system} zaten var ve Bandanix'e ait değil; dokunulmadı.")
        return False
    sudo("rm", "-rf", str(system))
    sudo("mkdir", "-p", str(system.parent))
    sudo("cp", "-a", "--no-preserve=ownership", str(user), str(system))
    sudo("touch", str(system / MARK))
    sudo("chmod", "-R", "a+rX", str(system))
    return True


def cmd_update() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        bg = Path(tmp) / "giris.png"
        source = current_wallpaper()
        make_background(source, bg, screen_size())
        say(f"Arka plan: {source.name if source else 'düz koyu renk'} (bulanık, koyulaştırılmış)")

        # back up the settings once, before Bandanix ever changes them
        if not BACKUP.exists() and not NO_CONF.exists():
            if CONF.exists():
                sudo("cp", "-a", str(CONF), str(BACKUP))
            else:
                sudo("touch", str(NO_CONF))

        sudo("install", "-D", "-m", "0644", str(bg), str(BG))
        sudo("touch", str(BG_DIR / MARK))
        values: dict[str, str | None] = dict(FIXED)
        for user, system, key in PARTS:
            if copy_part(user, system):          # a part that is not installed keeps Mint's value
                values[key] = system.name
        old = CONF.read_text(encoding="utf-8") if CONF.exists() else ""
        conf = Path(tmp) / "slick-greeter.conf"
        conf.write_text(set_keys(old, values), encoding="utf-8")
        sudo("install", "-D", "-m", "0644", str(conf), str(CONF))
    say("Giriş ekranı güncellendi. Oturumu kapatınca ya da yeniden başlatınca görünür.")
    say("Hemen bakmak için: bandanix-giris dene")
    return 0


def cmd_remove() -> int:
    if BACKUP.exists():
        sudo("mv", "-f", str(BACKUP), str(CONF))
    elif NO_CONF.exists():
        sudo("rm", "-f", str(CONF), str(NO_CONF))
    elif CONF.exists():                       # no backup: just take our keys out
        with tempfile.TemporaryDirectory() as tmp:
            conf = Path(tmp) / "slick-greeter.conf"
            conf.write_text(set_keys(CONF.read_text(encoding="utf-8"), {k: None for k in OUR_KEYS}),
                            encoding="utf-8")
            sudo("install", "-m", "0644", str(conf), str(CONF))
    for path in [BG_DIR] + [system for _, system, _ in PARTS]:
        if (path / MARK).exists():
            sudo("rm", "-rf", str(path))
    say("Giriş ekranı eski hâline döndü.")
    return 0


def cmd_show() -> int:
    keys = read_keys(CONF.read_text(encoding="utf-8")) if CONF.exists() else {}
    if keys.get("background") != FIXED["background"]:
        say("Giriş ekranında Bandanix ayarları yok. Kurmak için: ./install.sh giris-ekrani")
        return 0
    labels = {"background": "Arka plan", "theme-name": "Tema", "icon-theme-name": "İkonlar",
              "cursor-theme-name": "İmleç", "clock-format": "Saat"}
    for key, label in labels.items():
        print(f"{label:<11}{keys.get(key, 'Mint varsayılanı')}")
    return 0


def cmd_try() -> int:
    if not shutil.which("slick-greeter"):
        say("slick-greeter bulunamadı.")
        return 1
    say("Giriş ekranı bir pencerede açılıyor; Alt+F4 ile kapat (45 saniye sonra kendiliğinden kapanır).")
    subprocess.run(["timeout", "45", "slick-greeter", "--test-mode"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return 0


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else ""
    if not argv:
        return cmd_show()
    if len(argv) == 1 and cmd == "guncelle":
        return cmd_update()
    if len(argv) == 1 and cmd == "dene":
        return cmd_try()
    if len(argv) == 1 and cmd == "_kaldir":
        return cmd_remove()
    helped = cmd in ("-h", "--help", "yardim")
    print(USAGE, file=sys.stdout if helped else sys.stderr)
    return 0 if helped else 2


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except subprocess.CalledProcessError:
        say("Bir adım yönetici yetkisiyle yapılamadı (şifre yanlış ya da iptal edildi). Hiçbir şey yarım kalmadıysa tekrar dene.")
        sys.exit(1)
