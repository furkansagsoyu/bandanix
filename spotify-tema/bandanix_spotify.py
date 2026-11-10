#!/usr/bin/env python3
"""bandanix-spotify: the Bandanix colours in Spotify, through Spicetify.

  bandanix-spotify            how Spotify is installed, is the theme on
  bandanix-spotify uygula     put the theme on (again); asks for the password if Spotify's folder needs it
  bandanix-spotify geri       give Spotify its own look back

At login "_oturum" checks Spotify's version once: after an update Spotify has thrown the theme
away, so it is applied again (or, if the update took the write permission too, a notification
says what to run).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
ROOT = Path(os.environ.get("BANDANIX_KOK", "/"))                  # tests point this elsewhere
DATA = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local/share")
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config")
APP = DATA / "bandanix" / "spotify-tema"
STATE = APP / "durum.json"
THEME_SRC = APP / "Bandanix"
SPICE_CONFIG = CONFIG / "spicetify"
FLATPAK_SUB = "app/com.spotify.Client/x86_64/stable/active/files/extra/share/spotify"
THEME = "Bandanix"

USAGE = """Kullanım:
  bandanix-spotify            Spotify nasıl kurulu, tema açık mı
  bandanix-spotify uygula     temayı (yeniden) uygula
  bandanix-spotify geri       Spotify'ın kendi görünümüne dön"""


def say(msg: str) -> None:
    print(f"• {msg}")


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, **kw)
    except OSError as e:
        return subprocess.CompletedProcess(cmd, 127, "", str(e))


# ---- where is Spotify ---------------------------------------------------------------------
def detect() -> dict:
    """{tur: deb|flatpak|snap|yok, yol, prefs, surum}"""
    if (ROOT / "snap/bin/spotify").exists() or (ROOT / "snap/spotify").is_dir():
        return {"tur": "snap", "yol": "", "prefs": "", "surum": ""}
    for folder in ("usr/share/spotify", "opt/spotify"):
        path = ROOT / folder
        if (path / "Apps").is_dir():
            version = run(["dpkg-query", "-W", "-f=${Version}", "spotify-client"]).stdout.strip()
            return {"tur": "deb", "yol": str(path), "prefs": str(CONFIG / "spotify" / "prefs"),
                    "surum": version or f"mtime:{int((path / 'Apps').stat().st_mtime)}"}
    for base in (ROOT / "var/lib/flatpak", DATA / "flatpak"):
        path = base / FLATPAK_SUB
        if (path / "Apps").is_dir():
            commit = run(["flatpak", "info", "--show-commit", "com.spotify.Client"]).stdout.strip()
            prefs = HOME / ".var/app/com.spotify.Client/config/spotify/prefs"
            if not prefs.is_file() and (CONFIG / "spotify" / "prefs").is_file():
                prefs = CONFIG / "spotify" / "prefs"
            return {"tur": "flatpak", "yol": str(path), "prefs": str(prefs),
                    "surum": commit or f"mtime:{int((path / 'Apps').stat().st_mtime)}"}
    return {"tur": "yok", "yol": "", "prefs": "", "surum": ""}


def spicetify() -> str | None:
    own = HOME / ".spicetify" / "spicetify"
    if own.is_file() and os.access(own, os.X_OK):
        return str(own)
    return shutil.which("spicetify")


def writable(path: str) -> bool:
    apps = Path(path) / "Apps"
    if not (os.access(path, os.W_OK) and os.access(apps, os.W_OK)):
        return False
    return all(os.access(p, os.W_OK) for p in apps.iterdir())


def load_state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def notify(text: str) -> None:
    run(["notify-send", "-a", "Bandanix", "-i", "spotify-client", "Spotify teması", text])


# ---- applying -----------------------------------------------------------------------------
def install_theme_files() -> None:
    target = SPICE_CONFIG / "Themes" / THEME
    target.mkdir(parents=True, exist_ok=True)
    for f in THEME_SRC.iterdir():
        shutil.copyfile(f, target / f.name)


def configure(sp: str, info: dict) -> bool:
    run([sp, "-q", "config"])                      # first run writes config-xpui.ini
    r = run([sp, "-q", "config",
             "spotify_path", info["yol"], "prefs_path", info["prefs"],
             "current_theme", THEME, "color_scheme", THEME,
             "inject_css", "1", "replace_colors", "1", "overwrite_assets", "0", "inject_theme_js", "0"])
    if r.returncode != 0:
        print((r.stdout + r.stderr).strip(), file=sys.stderr)
    return r.returncode == 0


def spice_apply(sp: str, restart: bool, same_spotify: bool) -> tuple[bool, str]:
    """Same Spotify as last time: a plain apply. Otherwise backup + apply; if that fails the CLI may
    be too old for this Spotify (upgrade), then restore backup apply (Spicetify's own advice)."""
    extra = [] if restart else ["--no-restart"]
    log = ""
    attempts = [["backup", "apply"], ["upgrade"], ["restore", "backup", "apply"]]
    if same_spotify:
        attempts.insert(0, ["apply"])
    for attempt in attempts:
        r = run([sp, "-q", *extra, *attempt], timeout=300)
        log += (r.stdout + r.stderr)
        if attempt[0] == "upgrade":
            continue
        if r.returncode == 0 and "error" not in (r.stdout + r.stderr).lower():
            return True, log
    return False, log


def fix_permissions(path: str) -> bool:
    say("Spotify'ın klasörüne yazabilmek için bir kez şifren sorulacak (Spicetify'ın önerdiği izin).")
    apps = str(Path(path) / "Apps")
    first = subprocess.run(["sudo", "chmod", "a+wr", path])
    second = subprocess.run(["sudo", "chmod", "-R", "a+wr", apps]) if first.returncode == 0 else first
    return second.returncode == 0


def cmd_apply(restart: bool = True, interactive: bool = True) -> int:
    info = detect()
    if info["tur"] == "snap":
        say("Spotify Snap ile kurulu; Snap uygulamaları değiştirilemediği için tema uygulanamıyor.")
        say("Spotify'ı deb sürümüne geçirmek için: bandanix klasöründe spotify-tema/README.md → \"Snap'ten geçiş\".")
        return 1
    if info["tur"] == "yok":
        say("Spotify bulunamadı. Kurduktan sonra: ./install.sh spotify-tema")
        return 1
    if not Path(info["prefs"]).is_file():
        say("Spotify hiç açılmamış görünüyor. Spotify'ı aç, giriş yap, 1 dakika bekle, kapat; sonra: bandanix-spotify uygula")
        return 1
    sp = spicetify()
    if sp is None:
        say("Spicetify bulunamadı. Bandanix klasöründe: ./install.sh spotify-tema")
        return 1
    if not writable(info["yol"]):
        if not interactive or not fix_permissions(info["yol"]):
            say("Spotify'ın klasörüne yazılamıyor.")
            return 1
    install_theme_files()
    if not configure(sp, info):
        say("Spicetify ayarı yazılamadı.")
        return 1
    ok, log = spice_apply(sp, restart, load_state().get("surum") == info["surum"])
    if not ok:
        print(log.strip()[-1500:], file=sys.stderr)
        say("Tema uygulanamadı. Spotify yeni güncellendiyse Spicetify henüz uyumlu olmayabilir; birkaç gün sonra yeniden dene.")
        return 1
    save_state({"surum": info["surum"], "tur": info["tur"]})
    say("Spotify teması: Bandanix" + ("" if restart else " (Spotify'ı yeniden başlatınca görünür)"))
    return 0


def cmd_login() -> int:
    """At login: re-apply only when Spotify's version changed since the last time."""
    state, info = load_state(), detect()
    if not state or info["tur"] not in ("deb", "flatpak") or info["surum"] == state.get("surum"):
        return 0
    if not writable(info["yol"]):
        notify("Spotify güncellendi ve tema kalktı. Geri getirmek için terminalde: bandanix-spotify uygula")
        return 0
    running = run(["pgrep", "-x", "spotify"]).returncode == 0
    if cmd_apply(restart=False, interactive=False) == 0:
        if running:
            notify("Spotify güncellendi; Bandanix teması yeniden uygulandı. Spotify'ı yeniden başlatınca görünür.")
        return 0
    notify("Spotify güncellendi ama tema yeniden uygulanamadı. Terminalde: bandanix-spotify uygula")
    return 1


def cmd_restore() -> int:
    sp = spicetify()
    if sp is None:
        say("Spicetify bulunamadı; Spotify zaten kendi görünümünde.")
        return 0
    r = run([sp, "-q", "restore"], timeout=300)
    if r.returncode != 0:
        print((r.stdout + r.stderr).strip(), file=sys.stderr)
        say("Spotify eski hâline döndürülemedi.")
        return 1
    try:
        STATE.unlink()
    except OSError:
        pass
    say("Spotify kendi görünümüne döndü.")
    return 0


def cmd_show() -> int:
    info, state, sp = detect(), load_state(), spicetify()
    kinds = {"deb": "deb paketi", "flatpak": "Flatpak", "snap": "Snap (desteklenmiyor)", "yok": "bulunamadı"}
    print(f"Spotify      {kinds[info['tur']]}" + (f"  {info['yol']}" if info["yol"] else ""))
    version = run([sp, "-v"]).stdout.strip() if sp else ""
    print(f"Spicetify    {version or ('kurulu' if sp else 'kurulu değil')}")
    if not state:
        print("Tema         uygulanmadı (bandanix-spotify uygula)")
    elif state.get("surum") != info["surum"]:
        print("Tema         Spotify güncellenmiş, tema kalkmış olabilir (bandanix-spotify uygula)")
    else:
        print("Tema         Bandanix")
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        return cmd_show()
    cmd = argv[0]
    if len(argv) == 1 and cmd == "uygula":
        return cmd_apply()
    if len(argv) == 1 and cmd == "geri":
        return cmd_restore()
    if len(argv) == 1 and cmd == "_oturum":
        return cmd_login()
    if len(argv) == 1 and cmd == "_json":              # for Bandanix Ayarlar
        info, state, sp = detect(), load_state(), spicetify()
        theme = "yok" if not state else ("kalkmis" if state.get("surum") != info["surum"] else "acik")
        print(json.dumps({"tur": info["tur"], "spicetify": bool(sp), "tema": theme}))
        return 0
    if len(argv) == 1 and cmd == "_tur":
        print(detect()["tur"])
        return 0
    helped = cmd in ("-h", "--help", "yardim")
    print(USAGE, file=sys.stdout if helped else sys.stderr)
    return 0 if helped else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
