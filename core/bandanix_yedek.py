#!/usr/bin/python3
"""bandanix-yedek: snapshots of the Cinnamon desktop, so Bandanix changes can always be undone.

Only the Python standard library is used, so it runs on the system Python with no setup.
User-facing messages are Turkish; command names avoid Turkish characters on purpose.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

VERSION = "0.3.0"
HOME = Path.home()
DATA = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local/share") / "bandanix"
BACKUPS = DATA / "yedekler"
CHANGES = DATA / "degisiklikler"

# dconf trees saved in every backup (file name -> dconf path)
DCONF_TREES = {
    "cinnamon": "/org/cinnamon/",
    "gnome-desktop": "/org/gnome/desktop/",
    "gnome-terminal": "/org/gnome/terminal/",
    "nemo": "/org/nemo/",
    "mint-apps": "/org/x/",
}

# files and folders (relative to $HOME) saved in every backup
FILES = [
    ".bashrc",
    ".config/gtk-3.0/settings.ini",
    ".config/gtk-3.0/gtk.css",
    ".config/gtk-4.0/settings.ini",
    ".config/gtk-4.0/gtk.css",
    ".config/cinnamon",
    ".cinnamon/configs",
    ".config/autostart",
]

KEEP = {"otomatik": 5, "geri-yukleme": 3}      # other types are never pruned
TYPE_LABEL = {"orijinal": "★ orijinal", "otomatik": "otomatik", "elle": "elle",
              "geri-yukleme": "geri-yukleme", "ice-aktarilan": "ice-aktarilan"}

LABELS = {
    "/org/cinnamon/desktop/interface/gtk-theme": "GTK teması",
    "/org/cinnamon/desktop/interface/icon-theme": "İkon teması",
    "/org/cinnamon/desktop/interface/cursor-theme": "İmleç teması",
    "/org/cinnamon/desktop/interface/font-name": "Yazı tipi",
    "/org/cinnamon/theme/name": "Cinnamon teması",
    "/org/cinnamon/desktop/background/picture-uri": "Duvar kağıdı",
    "/org/cinnamon/panels-height": "Panel yüksekliği",
    "/org/cinnamon/panels-enabled": "Paneller",
    "/org/cinnamon/enabled-applets": "Panel uygulamacıkları",
    "/org/gnome/desktop/interface/gtk-theme": "GTK teması (GNOME)",
    "/org/gnome/desktop/interface/icon-theme": "İkon teması (GNOME)",
    "/org/gnome/desktop/interface/cursor-theme": "İmleç teması (GNOME)",
    "/org/gnome/desktop/interface/font-name": "Yazı tipi (GNOME)",
    "/org/gnome/desktop/interface/monospace-font-name": "Sabit genişlikli yazı tipi",
    "/org/gnome/terminal/legacy/profiles:/default": "Varsayılan terminal profili",
}

# ---- output -------------------------------------------------------------------
TTY = sys.stdout.isatty()
RED = "\033[38;2;200;16;46m" if TTY else ""
DIM = "\033[2m" if TTY else ""
BOLD = "\033[1m" if TTY else ""
RESET = "\033[0m" if TTY else ""


def say(msg: str) -> None:
    print(f"{RED}•{RESET} {msg}")


def fail(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    print(f"{RED}✗{RESET} {msg}", file=sys.stderr)
    sys.exit(1)


def ask(question: str) -> bool:
    if not sys.stdin.isatty():
        return True
    reply = input(f"{question} [E/h] ").strip().lower()
    return not reply.startswith(("h", "n"))


# ---- dconf ----------------------------------------------------------------------
def dconf(*args: str, stdin: str | None = None) -> str:
    try:
        result = subprocess.run(["dconf", *args], input=stdin, text=True,
                                capture_output=True, check=True)
    except FileNotFoundError:
        fail("dconf bulunamadı (sudo apt install dconf-cli)")
    except subprocess.CalledProcessError as exc:
        fail(f"dconf {' '.join(args)} başarısız: {exc.stderr.strip()}")
    return result.stdout


def parse_dump(text: str, prefix: str) -> dict[str, str]:
    """`dconf dump` text -> {full key path: value}."""
    keys: dict[str, str] = {}
    section = "/"
    for line in text.splitlines():
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
        elif "=" in line:
            key, value = line.split("=", 1)
            base = prefix if section == "/" else f"{prefix}{section}/"
            keys[base + key] = value
    return keys


# ---- backup records ----------------------------------------------------------
class Backup:
    def __init__(self, path: Path):
        self.path = path
        self.info = json.loads((path / "bilgi.json").read_text(encoding="utf-8"))

    @property
    def no(self) -> int:
        return int(self.info["no"])

    @property
    def kind(self) -> str:
        return self.info["tur"]

    @property
    def when(self) -> dt.datetime:
        return dt.datetime.fromisoformat(self.info["tarih"])


def all_backups() -> list[Backup]:
    if not BACKUPS.is_dir():
        return []
    found = []
    for path in BACKUPS.iterdir():
        if (path / "bilgi.json").is_file():
            try:
                found.append(Backup(path))
            except (ValueError, KeyError, OSError):
                continue
    return sorted(found, key=lambda b: b.no)


def find(ref: str) -> Backup:
    backups = all_backups()
    if not backups:
        fail("Hiç yedek yok. Almak için: bandanix-yedek al")
    if ref == "orijinal":
        for b in backups:
            if b.kind == "orijinal":
                return b
        fail("Orijinal yedek bulunamadı.")
    if ref == "son":
        return backups[-1]
    try:
        wanted = int(ref)
    except ValueError:
        fail(f"Geçersiz yedek numarası: {ref} (bir sayı, 'orijinal' ya da 'son' yaz)")
    for b in backups:
        if b.no == wanted:
            return b
    fail(f"{wanted} numaralı yedek yok. Liste için: bandanix-yedek liste")


def os_name() -> str:
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if line.startswith("PRETTY_NAME="):
                return line.split("=", 1)[1].strip('"')
    except OSError:
        pass
    return "Linux"


def take(kind: str, note: str = "", quiet: bool = False) -> Backup:
    backups = all_backups()
    no = (backups[-1].no + 1) if backups else 1
    now = dt.datetime.now().replace(microsecond=0)
    folder = BACKUPS / f"{no:03d}-{now:%Y%m%d-%H%M%S}-{kind}"
    (folder / "dconf").mkdir(parents=True)

    for name, tree in DCONF_TREES.items():
        (folder / "dconf" / f"{name}.ini").write_text(dconf("dump", tree), encoding="utf-8")

    files: dict[str, str] = {}
    for rel in FILES:
        src = HOME / rel
        dst = folder / "dosyalar" / rel
        if src.is_dir():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst, symlinks=True)
            files[rel] = "klasor"
        elif src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            files[rel] = "dosya"
        else:
            files[rel] = "yok"

    info = {
        "bicim": 1, "no": no, "tarih": now.isoformat(), "tur": kind, "not": note,
        "ev": str(HOME), "sistem": os_name(), "bandanix": VERSION,
        "dconf": DCONF_TREES, "dosyalar": files,
    }
    (folder / "bilgi.json").write_text(json.dumps(info, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    prune()
    backup = Backup(folder)
    if not quiet:
        say(f"Yedek alındı: {BOLD}{no}{RESET} ({TYPE_LABEL[kind]}){f' · {note}' if note else ''}")
    return backup


def prune() -> None:
    for kind, keep in KEEP.items():
        same = [b for b in all_backups() if b.kind == kind]
        for old in same[:-keep] if len(same) > keep else []:
            shutil.rmtree(old.path, ignore_errors=True)


# ---- comparing ----------------------------------------------------------------
def backup_keys(b: Backup) -> dict[str, str]:
    keys: dict[str, str] = {}
    for name, tree in b.info["dconf"].items():
        path = b.path / "dconf" / f"{name}.ini"
        if path.is_file():
            keys.update(parse_dump(path.read_text(encoding="utf-8"), tree))
    return keys


def current_keys(trees: dict[str, str]) -> dict[str, str]:
    keys: dict[str, str] = {}
    for tree in trees.values():
        keys.update(parse_dump(dconf("dump", tree), tree))
    return keys


def digest(path: Path) -> str:
    if path.is_dir():
        h = hashlib.sha256()
        for p in sorted(path.rglob("*")):
            if p.is_file():
                h.update(str(p.relative_to(path)).encode())
                h.update(p.read_bytes())
        return h.hexdigest()
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "-"


def short(value: str | None) -> str:
    if value is None:
        return "(yok)"
    value = value.strip("'")
    return value if len(value) <= 40 else value[:39] + "…"


def changes_since(b: Backup) -> tuple[list[str], list[str]]:
    old, now = backup_keys(b), current_keys(b.info["dconf"])
    settings = []
    for key in sorted(set(old) | set(now)):
        if old.get(key) != now.get(key):
            label = LABELS.get(key, key)
            settings.append(f"{label}: {short(now.get(key))} → {short(old.get(key))}")
    files = []
    for rel, kind in b.info["dosyalar"].items():
        saved = b.path / "dosyalar" / rel
        then = digest(saved) if kind != "yok" else "-"
        if then != digest(HOME / rel):
            files.append(f"~/{rel}")
    return settings, files


# ---- restoring ------------------------------------------------------------------
def restore(b: Backup) -> None:
    for name, tree in b.info["dconf"].items():
        path = b.path / "dconf" / f"{name}.ini"
        if not path.is_file():
            continue
        dconf("reset", "-f", tree)
        dconf("load", tree, stdin=path.read_text(encoding="utf-8"))
    for rel, kind in b.info["dosyalar"].items():
        target = HOME / rel
        saved = b.path / "dosyalar" / rel
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        elif target.exists() or target.is_symlink():
            target.unlink()
        if kind == "klasor":
            shutil.copytree(saved, target, symlinks=True)
        elif kind == "dosya":
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(saved, target)


def offer_cinnamon_restart() -> None:
    if "Cinnamon" not in os.environ.get("XDG_CURRENT_DESKTOP", ""):
        return
    if ask("Cinnamon yeniden başlatılsın mı? (pencerelerin kapanmaz)"):
        subprocess.Popen(["cinnamon", "--replace"], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
        say("Cinnamon yeniden başlatılıyor.")


# ---- commands -------------------------------------------------------------------
def cmd_al(args) -> None:
    take("elle", " ".join(args.not_) if args.not_ else "")


def cmd_otomatik(args) -> None:
    """Used by the Bandanix installer: the very first backup becomes 'orijinal'."""
    if not any(b.kind == "orijinal" for b in all_backups()):
        take("orijinal", "Bandanix öncesi masaüstü")
    else:
        take("otomatik", " ".join(args.not_) if args.not_ else "kurulum öncesi")


def cmd_liste(_args) -> None:
    backups = all_backups()
    if not backups:
        say("Henüz yedek yok. Almak için: bandanix-yedek al")
        return
    print(f"{BOLD} No  Tarih              Tür               Not{RESET}")
    for b in backups:
        kind = TYPE_LABEL.get(b.kind, b.kind)
        colour = RED if b.kind == "orijinal" else ""
        print(f" {b.no:>2}  {b.when:%d.%m.%Y %H:%M}   {colour}{kind:<16}{RESET}  {b.info.get('not', '')}")


def cmd_fark(args) -> None:
    b = find(args.no)
    settings, files = changes_since(b)
    if not settings and not files:
        say(f"{b.no} numaralı yedekten bu yana hiçbir şey değişmemiş.")
        return
    print(f"{BOLD}{b.no} numaraya dönersen değişecekler (şimdiki → yedekteki):{RESET}")
    for line in settings[:30]:
        print(f"  {line}")
    if len(settings) > 30:
        print(f"  {DIM}… ve {len(settings) - 30} ayar daha{RESET}")
    for f in files:
        print(f"  Dosya: {f}")


def cmd_geri_yukle(args) -> None:
    b = find(args.no)
    settings, files = changes_since(b)
    if not settings and not files:
        say("Masaüstün zaten bu yedekle aynı, yapılacak bir şey yok.")
        return
    print(f"{b.no} numaralı yedeğe dönülecek ({b.when:%d.%m.%Y %H:%M}, "
          f"{TYPE_LABEL.get(b.kind, b.kind)}): {len(settings)} ayar, {len(files)} dosya değişecek.")
    if not ask("Devam edilsin mi?"):
        say("Vazgeçildi.")
        return
    take("geri-yukleme", f"{b.no} numaraya dönmeden önce")
    restore(b)
    say(f"Masaüstü {b.no} numaralı yedeğe döndürüldü.")
    offer_cinnamon_restart()


def cmd_sil(args) -> None:
    b = find(args.no)
    if b.kind == "orijinal" and not args.zorla:
        fail("Orijinal yedek korunuyor. Yine de silmek için: bandanix-yedek sil orijinal --zorla")
    if not ask(f"{b.no} numaralı yedek silinsin mi?"):
        say("Vazgeçildi.")
        return
    shutil.rmtree(b.path)
    say(f"{b.no} numaralı yedek silindi.")


def cmd_disa_aktar(args) -> None:
    b = find(args.no)
    out = Path(args.dosya) if args.dosya else Path.cwd() / f"bandanix-yedek-{b.no}-{b.when:%Y%m%d}.tar.gz"
    with tarfile.open(out, "w:gz") as tar:
        tar.add(b.path, arcname="yedek")
    say(f"Dışa aktarıldı: {out}")


def rewrite_home(folder: Path, old_home: str) -> None:
    """Point paths like /home/olduser/... at this computer's home folder."""
    new_home = str(HOME)
    if not old_home or old_home == new_home:
        return
    for path in folder.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue                       # binary files stay as they are
        if old_home in text:
            path.write_text(text.replace(old_home, new_home), encoding="utf-8")


def cmd_ice_aktar(args) -> None:
    source = Path(args.dosya)
    if not source.is_file():
        fail(f"Dosya bulunamadı: {source}")
    with tempfile.TemporaryDirectory() as tmp:
        try:
            with tarfile.open(source, "r:gz") as tar:
                for member in tar.getmembers():
                    name = Path(member.name)
                    if name.is_absolute() or ".." in name.parts or member.isdev():
                        fail("Bu dosya güvenli bir Bandanix yedeği değil.")
                if hasattr(tarfile, "data_filter"):
                    tar.extractall(tmp, filter="data")
                else:
                    tar.extractall(tmp)
        except tarfile.TarError:
            fail("Dosya okunamadı, geçerli bir .tar.gz değil.")
        folder = Path(tmp) / "yedek"
        info_path = folder / "bilgi.json"
        if not info_path.is_file():
            fail("Bu dosya bir Bandanix yedeği değil (bilgi.json yok).")
        info = json.loads(info_path.read_text(encoding="utf-8"))
        rewrite_home(folder, info.get("ev", ""))

        backups = all_backups()
        no = (backups[-1].no + 1) if backups else 1
        info.update(no=no, tur="ice-aktarilan", ev=str(HOME),
                    **{"not": f"{info.get('sistem', '?')} · {info.get('tarih', '')[:10]} tarihli yedek"})
        info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        BACKUPS.mkdir(parents=True, exist_ok=True)
        target = BACKUPS / f"{no:03d}-{dt.datetime.now():%Y%m%d-%H%M%S}-ice-aktarilan"
        shutil.move(str(folder), target)
    say(f"İçe aktarıldı: {BOLD}{no}{RESET}. Uygulamak için: bandanix-yedek geri-yukle {no}")


# ---- smart restore for components ------------------------------------------------
def change_file(component: str) -> Path:
    return CHANGES / f"{component}.json"


def cmd_isaretle(args) -> None:
    """Remember original values before a component changes them (first value wins)."""
    path = change_file(args.parca)
    state = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"dconf": {}, "dosya": {}}
    store = CHANGES / args.parca
    for item in args.ogeler:
        if item.startswith("dconf:"):
            key = item[6:]
            if key not in state["dconf"]:
                value = dconf("read", key).strip()
                state["dconf"][key] = value or None
        elif item.startswith("dosya:"):
            rel = item[6:].removeprefix("~/")
            if rel not in state["dosya"]:
                src = HOME / rel
                if src.is_file():
                    dst = store / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    state["dosya"][rel] = "dosya"
                else:
                    state["dosya"][rel] = "yok"
        else:
            fail(f"Bilinmeyen öğe: {item} (dconf:/yol/anahtar ya da dosya:~/yol bekleniyor)")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_geri_al(args) -> None:
    """Put back exactly the values a component changed, nothing else."""
    path = change_file(args.parca)
    if not path.is_file():
        return
    state = json.loads(path.read_text(encoding="utf-8"))
    for key, value in state["dconf"].items():
        if value is None:
            dconf("reset", key)
        else:
            dconf("write", key, value)
    store = CHANGES / args.parca
    for rel, kind in state["dosya"].items():
        target = HOME / rel
        if kind == "dosya":
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(store / rel, target)
        elif target.exists():
            target.unlink()
    path.unlink()
    shutil.rmtree(store, ignore_errors=True)
    say(f"{args.parca}: değiştirilen ayarlar eski hâline döndü.")


# ---- entry ------------------------------------------------------------------------
class TurkishHelp(argparse.HelpFormatter):
    def add_usage(self, usage, actions, groups, prefix=None):
        super().add_usage(usage, actions, groups,
                          "kullanım: " if prefix is None else prefix)


def turkish_parser(make, *args, **kwargs) -> argparse.ArgumentParser:
    """Build a (sub)parser whose help texts and headings are Turkish."""
    p = make(*args, add_help=False, formatter_class=TurkishHelp, **kwargs)
    p._positionals.title = "argümanlar"
    p._optionals.title = "seçenekler"
    p.add_argument("-h", "--yardim", action="help", help="bu yardımı göster")

    def error(message: str) -> None:
        p.print_usage(sys.stderr)
        if "invalid choice" in message:
            fail("Bilinmeyen komut. Komutların listesi için: bandanix-yedek -h")
        fail(f"Eksik ya da hatalı kullanım. Yardım için: {p.prog} -h")

    p.error = error
    return p


def main(argv: list[str] | None = None) -> int:
    parser = turkish_parser(
        argparse.ArgumentParser, prog="bandanix-yedek",
        description="Bandanix masaüstü yedekleri: al, karşılaştır, geri yükle, taşı.",
        epilog="Yedek numarası yerine 'orijinal' ya da 'son' da yazabilirsin.")
    parser.add_argument("--surum", action="version", version=f"bandanix-yedek {VERSION}",
                        help="sürümü göster")
    sub = parser.add_subparsers(dest="komut", metavar="komut", title="komutlar")
    _add = sub.add_parser
    sub.add_parser = lambda *a, **k: turkish_parser(_add, *a, **k)

    p = sub.add_parser("al", help="elle yedek al")
    p.add_argument("not_", nargs="*", metavar="not", help="isteğe bağlı kısa not")
    p.set_defaults(func=cmd_al)

    sub.add_parser("liste", help="yedekleri göster").set_defaults(func=cmd_liste)

    for name, func, text in (("fark", cmd_fark, "yedekten bu yana neler değişmiş"),
                             ("geri-yukle", cmd_geri_yukle, "masaüstünü bir yedeğe döndür")):
        p = sub.add_parser(name, help=text)
        p.add_argument("no", help="yedek numarası, 'orijinal' ya da 'son'")
        p.set_defaults(func=func)

    p = sub.add_parser("sil", help="bir yedeği sil")
    p.add_argument("no")
    p.add_argument("--zorla", action="store_true", help="orijinal yedeği de silebilmek için")
    p.set_defaults(func=cmd_sil)

    p = sub.add_parser("disa-aktar", help="yedeği tek bir .tar.gz dosyası yap")
    p.add_argument("no")
    p.add_argument("dosya", nargs="?", help="çıktı dosyası (varsayılan: bulunduğun klasör)")
    p.set_defaults(func=cmd_disa_aktar)

    p = sub.add_parser("ice-aktar", help="başka bilgisayardan gelen yedeği ekle")
    p.add_argument("dosya")
    p.set_defaults(func=cmd_ice_aktar)

    # used by Bandanix components and the installer
    p = sub.add_parser("otomatik", help="(kurulum için) otomatik yedek; ilki 'orijinal' olur")
    p.add_argument("not_", nargs="*", metavar="not")
    p.set_defaults(func=cmd_otomatik)

    p = sub.add_parser("isaretle", help="(parçalar için) değiştirilecek ayarların eski değerini sakla")
    p.add_argument("parca")
    p.add_argument("ogeler", nargs="+", help="dconf:/yol/anahtar ya da dosya:~/yol")
    p.set_defaults(func=cmd_isaretle)

    p = sub.add_parser("geri-al", help="(parçalar için) bir parçanın değiştirdiklerini geri al")
    p.add_argument("parca")
    p.set_defaults(func=cmd_geri_al)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    try:
        args.func(args)
    except KeyboardInterrupt:
        print()
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
