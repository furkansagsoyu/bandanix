"""bandanix-sistem: command line for the system island.

  bandanix-sistem          current values and limits
  bandanix-sistem dene     show the island for 20 seconds with a made-up warning
  bandanix-sistem ac       start watching (now and at every login)
  bandanix-sistem kapat    stop watching
"""
from __future__ import annotations

import fcntl
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

USAGE = """Kullanım:
  bandanix-sistem          şu anki değerler ve sınırlar
  bandanix-sistem dene     adayı 20 saniyeliğine örnek bir uyarıyla göster
  bandanix-sistem ac       izlemeyi aç (şimdi ve her oturum açılışında)
  bandanix-sistem kapat    izlemeyi kapat"""

HOME = Path.home()
AUTOSTART = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config") / "autostart" / "bandanix-sistem.desktop"
BIN = HOME / ".local" / "bin" / "bandanix-sistem"


def watcher_running() -> bool:
    from .bekci import LOCK
    try:
        with open(LOCK, "a") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fh, fcntl.LOCK_UN)
        return False
    except OSError as err:
        return isinstance(err, BlockingIOError) or err.errno in (11, 13)


def durum() -> int:
    from . import olcum
    from .bekci import limits
    lim = limits()
    a = olcum.cpu_times()
    time.sleep(0.5)
    b = olcum.cpu_times()
    cpu = (b[0] - a[0]) / (b[1] - a[1]) * 100 if a and b and b[1] > a[1] else None
    temp, mem = olcum.temperature(), olcum.memory()

    def row(label, value, extra=""):
        print(f"{label:<12}{value:<8}{extra}")

    row("İşlemci", "-" if cpu is None else f"%{cpu:.0f}", f"(sınır: 1 dakika boyunca %{lim['islemci']})")
    row("Sıcaklık", "-" if temp is None else f"{temp:.0f}°C", f"(sınır: {lim['sicaklik']}°C)")
    if mem:
        row("RAM", f"%{mem[0] / mem[1] * 100:.0f}",
            f"{olcum.human(mem[0])} / {olcum.human(mem[1])}  (sınır: %{lim['ram']})")
    for d in olcum.disks():
        row(f"Disk {d.path if d.path == '/' else '~'}", f"%{d.percent:.0f}",
            f"boş {olcum.human(d.free)}  (sınır: %{lim['disk']})")
    print()
    if watcher_running():
        print("• İzleme açık. Bir sınır aşılınca ada ekranın üstünde belirir.")
    else:
        print("• İzleme kapalı. Açmak için: bandanix-sistem ac")
    return 0


def dene() -> int:
    from .bekci import LAUNCHER
    env = dict(os.environ, BANDANIX_SISTEM_DENE="1")
    try:
        subprocess.Popen([str(LAUNCHER)], env=env, stdin=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        print("• Ada başlatılamadı. Parçayı yeniden kur: ./install.sh sistem-adasi")
        return 1
    print("• Ada 20 saniyeliğine örnek bir sıcaklık uyarısıyla açılıyor. Üzerine gelip dene.")
    return 0


def ac() -> int:
    AUTOSTART.parent.mkdir(parents=True, exist_ok=True)
    AUTOSTART.write_text(
        "[Desktop Entry]\nType=Application\nName=Bandanix Sistem adası\n"
        "Comment=İşlemci, sıcaklık, RAM ve disk uyarıları\n"
        f"Exec={BIN} _bekci\nTerminal=false\nNoDisplay=true\nX-GNOME-Autostart-enabled=true\n",
        encoding="utf-8")
    if not watcher_running():
        subprocess.Popen([str(BIN), "_bekci"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    print("• İzleme açık; her oturum açılışında kendiliğinden başlar.")
    return 0


def kapat() -> int:
    AUTOSTART.unlink(missing_ok=True)
    from .bekci import LOCK
    try:
        pid = int(LOCK.read_text().strip() or 0)
    except (OSError, ValueError):
        pid = 0
    if pid and watcher_running():
        try:
            cmd = Path(f"/proc/{pid}/cmdline").read_bytes()
            if b"_bekci" in cmd:
                os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    subprocess.run(["pkill", "-f", "bandanix_sistem _ada"], check=False)
    print("• İzleme kapalı. Tekrar açmak için: bandanix-sistem ac")
    return 0


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "durum"
    if len(argv) > 1:
        print(USAGE, file=sys.stderr)
        return 2
    if cmd == "durum":
        return durum()
    if cmd == "dene":
        return dene()
    if cmd == "ac":
        return ac()
    if cmd == "kapat":
        return kapat()
    if cmd == "_bekci":
        from .bekci import run
        return run()
    if cmd == "_ada":
        from .ada import main as island
        return island()
    helped = cmd in ("-h", "--help", "yardim")
    print(USAGE, file=sys.stdout if helped else sys.stderr)
    return 0 if helped else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
