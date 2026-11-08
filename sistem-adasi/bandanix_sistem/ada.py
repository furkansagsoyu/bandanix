"""The system island: a small warning pill that grows into a panel on hover.

Opened by the watcher only while something is wrong; quits by itself when it is over.
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time

from PySide6.QtCore import QDir, QEasingCurve, QLockFile, QPointF, QRectF, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QCursor, QFont, QFontMetrics, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from bandanix_ada import dizilim, tema
from bandanix_ada.cizim import FG, MUTED, TOP_MARGIN, lerp, paint_shell

from . import olcum
from .bekci import STATE, mute, read_json
from .kurallar import Rules, limits_from

H = 42
EXPANDED_W = 360
PAD = 16
METRIC_ROW = 22
PROC_ROW = 28
QUIT_AFTER_OK = 10          # seconds without a problem before the island goes away
DENE = bool(os.environ.get("BANDANIX_SISTEM_DENE"))
DENE_SECONDS = 20
CONFIRM_MS = 4000
FORCE_AFTER = 3.0
DENE_PROBLEM = {"tur": "sicaklik", "deger": 94.0, "yazi": "94°C"}


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class SystemIsland(QWidget):
    def __init__(self, theme: dict):
        super().__init__(None, Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self.setWindowTitle("Bandanix Sistem adası")

        self.accent = QColor(tema.accent(theme))
        self.limits = limits_from(tema.section(theme, "sistem-adasi"))
        self.started = time.time()
        self.state: dict = {}
        self.shown: list[dict] = []
        self.ok_since: float | None = None
        self.t = 0.0
        self.hover = False
        self.mouse = QPointF(-1, -1)
        self.hit: dict[str, QRectF] = {}

        # process list (only sampled while the panel is open)
        self.snap: dict[str, olcum.Group] = {}
        self.snap_time = 0.0
        self.usage: dict[str, float] = {}
        self.confirm: str | None = None
        self.killing: dict[str, float] = {}
        self.note = ""

        # test mode measures by itself, without the watcher
        self.rules = Rules(self.limits) if DENE else None

        self.anim = QVariantAnimation(self)
        self.anim.setDuration(260)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.valueChanged.connect(self._apply_t)

        self.leave_timer = self._timer(450, self._maybe_collapse, single=True)
        self.confirm_timer = self._timer(CONFIRM_MS, self._clear_confirm, single=True)
        self.state_timer = self._timer(1000, self.reload)
        self.place_timer = self._timer(120, self.place)
        self.proc_timer = self._timer(1500, self.sample_processes)

        self.reload()
        self._apply_t(0.0)

    def _timer(self, ms: int, slot, single: bool = False) -> QTimer:
        timer = QTimer(self)
        timer.setInterval(ms)
        timer.setSingleShot(single)
        timer.timeout.connect(slot)
        if not single:
            timer.start()
        return timer

    # ---- data ----------------------------------------------------------------------------
    def reload(self) -> None:
        now = time.time()
        if DENE:
            self.state = self.rules.update(now, olcum.cpu_times(), olcum.temperature(),
                                           olcum.memory(), olcum.disks())
            self.state["olcum"]["sicaklik"] = DENE_PROBLEM["deger"]
            self.shown = [DENE_PROBLEM]
            if now - self.started > DENE_SECONDS and not self.hover:
                self.quit()
        else:
            state = read_json(STATE, {})
            if not state or now - float(state.get("zaman", 0)) > 20:
                self.quit()                          # the watcher is gone
                return
            self.state = state
            self.shown = [p for p in state.get("gosterilen", []) if isinstance(p, dict)]
            self.limits = state.get("sinirlar", self.limits)
            if self.shown:
                self.ok_since = None
            elif self.ok_since is None:
                self.ok_since = now
            elif now - self.ok_since > QUIT_AFTER_OK and not self.hover:
                self.quit()
        self._apply_t(self.t)

    def quit(self) -> None:
        # deferred, so it also works before the event loop has started
        QTimer.singleShot(0, QApplication.quit)

    def main_kind(self) -> str:
        return self.shown[0]["tur"] if self.shown else ""

    def sample_processes(self) -> None:
        if self.t <= 0 and not self.hover:
            return
        now = time.monotonic()
        snap = olcum.processes()
        if self.snap:
            self.usage = olcum.cpu_usage(self.snap, snap, now - self.snap_time, olcum.cpu_count())
        self.snap, self.snap_time = snap, now
        for key in list(self.killing):
            if key not in snap:
                del self.killing[key]
                self.note = "Kapatıldı"
        self.update()

    def top_groups(self) -> list[tuple[str, olcum.Group, str]]:
        """(key, group, value text) for the three heaviest groups."""
        if self.main_kind() == "ram":
            keys = sorted(self.snap, key=lambda k: self.snap[k].rss, reverse=True)
            return [(k, self.snap[k], olcum.human(self.snap[k].rss)) for k in keys[:3]]
        if not self.usage:
            return []
        keys = sorted(self.usage, key=self.usage.get, reverse=True)[:3]
        return [(k, self.snap[k], "%<1" if self.usage[k] < 1 else f"%{self.usage[k]:.0f}")
                for k in keys if k in self.snap]

    # ---- size and place ------------------------------------------------------------------
    def collapsed_width(self) -> int:
        if not self.shown:
            return 120
        width = QFontMetrics(self._font(13, QFont.Weight.DemiBold)).horizontalAdvance(self.shown[0]["yazi"])
        if len(self.shown) > 1:
            width += 8 + QFontMetrics(self._font(12)).horizontalAdvance(f"+{len(self.shown) - 1}")
        return max(96, PAD + 8 + 10 + width + PAD + 2)

    def metric_rows(self) -> list[tuple[str, float | None, str, bool]]:
        o = self.state.get("olcum", {}) if isinstance(self.state.get("olcum"), dict) else {}
        active = {p["tur"] for p in self.shown}
        cpu = o.get("islemci_anlik") if o.get("islemci_anlik") is not None else o.get("islemci")
        rows = [
            ("İşlemci", cpu, "-" if cpu is None else f"%{cpu:.0f}", "islemci" in active),
            ("Sıcaklık", o.get("sicaklik"),
             "-" if o.get("sicaklik") is None else f"{o['sicaklik']:.0f}°C", "sicaklik" in active),
            ("RAM", o.get("ram"), "-" if o.get("ram") is None else f"%{o['ram']:.0f}", "ram" in active),
        ]
        for d in o.get("diskler", []) or []:
            label = "Disk" if d.get("yol") == "/" else "Disk ~"
            rows.append((label, d.get("yuzde"), f"%{d.get('yuzde', 0):.0f}",
                         "disk" in active and d.get("yuzde", 0) >= self.limits.get("disk", 95) - 5))
        return rows

    def expanded_height(self) -> int:
        rows = len(self.metric_rows())
        if self.main_kind() == "disk":
            section = 20 + len(self.state.get("olcum", {}).get("diskler", []) or []) * 22 + 8 + 30
        else:
            section = 20 + 3 * PROC_ROW
        return PAD + 26 + rows * METRIC_ROW + 18 + section + PAD

    def _apply_t(self, t) -> None:
        self.t = float(t)
        self.place()

    def place(self) -> None:
        w = round(lerp(self.collapsed_width(), EXPANDED_W, self.t))
        h = round(lerp(H, self.expanded_height(), self.t))
        screen = self.screen() or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        x, y = dizilim.place_beside(dizilim.read("sound-island"), w, geo.x(), geo.width(),
                                    geo.y() + TOP_MARGIN)
        if (x, y, w, h) != (self.x(), self.y(), self.width(), self.height()):
            self.setGeometry(x, y, w, h)
        self.update()

    def _animate_to(self, target: float) -> None:
        if abs(self.t - target) < 1e-3 and self.anim.state() != QVariantAnimation.State.Running:
            return
        self.anim.stop()
        self.anim.setStartValue(self.t)
        self.anim.setEndValue(float(target))
        self.anim.start()

    def _maybe_collapse(self) -> None:
        if not self.hover:
            self._animate_to(0.0)
            self.confirm = None

    # ---- painting --------------------------------------------------------------------
    def _font(self, px: int, weight=QFont.Weight.Normal) -> QFont:
        f = QFont(self.font())
        f.setPixelSize(px)
        f.setWeight(weight)
        return f

    def _text(self, p: QPainter, rect: QRectF, text: str, font: QFont, color: QColor,
              align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter) -> None:
        p.setFont(font)
        p.setPen(color)
        elided = QFontMetrics(font).elidedText(text, Qt.TextElideMode.ElideRight, int(rect.width()))
        p.drawText(rect, int(align), elided)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        w, h, t = self.width(), self.height(), self.t
        paint_shell(p, w, h, lerp(h / 2, 22, t), self.accent, lerp(150, 110, t))
        self.hit = {}
        pill_alpha = max(0.0, 1 - t * 2.2)
        full_alpha = max(0.0, (t - 0.45) / 0.55)
        if pill_alpha > 0:
            p.setOpacity(pill_alpha)
            self._paint_pill(p)
        if full_alpha > 0:
            p.setOpacity(full_alpha)
            self._paint_panel(p, w)
        p.end()

    def _paint_pill(self, p: QPainter) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.accent)
        p.drawEllipse(QPointF(PAD + 4, H / 2), 4, 4)
        if not self.shown:
            self._text(p, QRectF(PAD + 18, 0, 200, H), "Düzeldi", self._font(13), MUTED)
            return
        main = self.shown[0]["yazi"]
        font = self._font(13, QFont.Weight.DemiBold)
        main_w = QFontMetrics(font).horizontalAdvance(main)
        self._text(p, QRectF(PAD + 18, 0, main_w + 2, H), main, font, FG)
        if len(self.shown) > 1:
            self._text(p, QRectF(PAD + 18 + main_w + 8, 0, 40, H), f"+{len(self.shown) - 1}",
                       self._font(12), MUTED)

    def _paint_panel(self, p: QPainter, w: int) -> None:
        right = w - PAD
        y = PAD
        self._text(p, QRectF(PAD, y, 160, 20), "Sistem", self._font(14, QFont.Weight.Bold), FG)
        if self.shown:
            self._text(p, QRectF(right - 160, y, 160, 20), self.shown[0]["yazi"],
                       self._font(13, QFont.Weight.DemiBold), self.accent,
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        y += 26

        # measurements with small bars
        bar_x0, bar_x1 = PAD + 74, right - 52
        for label, value, text, over in self.metric_rows():
            self._text(p, QRectF(PAD, y, 70, METRIC_ROW), label, self._font(12), MUTED)
            cy = y + METRIC_ROW / 2
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 30))
            p.drawRoundedRect(QRectF(bar_x0, cy - 3, bar_x1 - bar_x0, 6), 3, 3)
            if value is not None:
                frac = max(0.0, min(1.0, float(value) / 100))
                fill = QColor(self.accent) if over else QColor(245, 245, 247, 150)
                p.setBrush(fill)
                p.drawRoundedRect(QRectF(bar_x0, cy - 3, max(6.0, (bar_x1 - bar_x0) * frac), 6), 3, 3)
            self._text(p, QRectF(right - 48, y, 48, METRIC_ROW), text,
                       self._font(12, QFont.Weight.DemiBold), self.accent if over else FG,
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            y += METRIC_ROW

        y += 8
        p.setPen(QPen(QColor(255, 255, 255, 22), 1))
        p.drawLine(QPointF(PAD, y), QPointF(right, y))
        y += 10

        if self.main_kind() == "disk":
            self._paint_disk(p, y, right)
        else:
            self._paint_processes(p, y, right)

    def _paint_processes(self, p: QPainter, y: float, right: float) -> None:
        title = "En çok RAM kullananlar" if self.main_kind() == "ram" else "En çok işlemci kullananlar"
        if self.note:
            title += f"  ·  {self.note}"
        self._text(p, QRectF(PAD, y, right - PAD, 18), title, self._font(12), MUTED)
        y += 20
        rows = self.top_groups()
        if not rows:
            self._text(p, QRectF(PAD, y, right - PAD, PROC_ROW), "Ölçülüyor…", self._font(12), MUTED)
            return
        now = time.time()
        for key, group, value in rows:
            name = group.name + (f" ×{len(group.pids)}" if len(group.pids) > 1 else "")
            button = QRectF(right - 84, y + (PROC_ROW - 22) / 2, 84, 22)
            self._text(p, QRectF(PAD, y, button.left() - PAD - 64, PROC_ROW), name,
                       self._font(13), FG)
            self._text(p, QRectF(button.left() - 60, y, 52, PROC_ROW), value, self._font(12), MUTED,
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if group.mine and not group.protected:
                self._paint_button(p, key, button, now)
            y += PROC_ROW

    def _paint_button(self, p: QPainter, key: str, rect: QRectF, now: float) -> None:
        hovered = rect.contains(self.mouse)
        started = self.killing.get(key)
        if started is not None and now - started < FORCE_AFTER:
            self._text(p, rect, "Kapanıyor…", self._font(11), MUTED, Qt.AlignmentFlag.AlignCenter)
            return
        self.hit[f"kill:{key}"] = rect
        if started is not None:
            label, fill, border, color = "Zorla kapat", None, self.accent, self.accent
        elif self.confirm == key:
            label, fill, border, color = "Emin misin?", self.accent, self.accent, FG
        else:
            label, fill, border, color = "Kapat", None, QColor(255, 255, 255, 70), FG
        p.setPen(QPen(border, 1))
        if fill is not None:
            p.setBrush(fill)
        elif hovered:
            p.setBrush(QColor(255, 255, 255, 28))
        else:
            p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 11, 11)
        self._text(p, rect, label, self._font(11, QFont.Weight.DemiBold), color, Qt.AlignmentFlag.AlignCenter)

    def _paint_disk(self, p: QPainter, y: float, right: float) -> None:
        self._text(p, QRectF(PAD, y, right - PAD, 18), "Boş alan", self._font(12), MUTED)
        y += 20
        for d in self.state.get("olcum", {}).get("diskler", []) or []:
            where = "Sistem (/)" if d.get("yol") == "/" else "Ev klasörü"
            self._text(p, QRectF(PAD, y, right - PAD, 22),
                       f"{where}  ·  {olcum.human(d.get('bos', 0))} boş", self._font(13), FG)
            y += 22
        y += 8
        rect = QRectF(PAD, y, right - PAD, 28)
        self.hit["disk"] = rect
        p.setPen(QPen(QColor(255, 255, 255, 70), 1))
        p.setBrush(QColor(255, 255, 255, 28) if rect.contains(self.mouse) else Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 14, 14)
        self._text(p, rect, "Disk Kullanım Çözümleyicisi'ni aç", self._font(12, QFont.Weight.DemiBold),
                   FG, Qt.AlignmentFlag.AlignCenter)

    # ---- actions ---------------------------------------------------------------------
    def kill(self, key: str) -> None:
        group = self.snap.get(key)
        if group is None or not group.mine or group.protected:
            return
        force = key in self.killing
        if not force and self.confirm != key:
            self.confirm = key
            self.confirm_timer.start()
            return
        self.confirm = None
        sig = signal.SIGKILL if force else signal.SIGTERM
        for pid in group.pids:
            try:
                os.kill(pid, sig)
            except OSError:
                pass
        self.killing[key] = time.time()
        if all(not alive(pid) for pid in group.pids):
            self.note = "Kapatıldı"
        QTimer.singleShot(int(FORCE_AFTER * 1000) + 100, self.update)

    def _clear_confirm(self) -> None:
        self.confirm = None
        self.update()

    def open_disk_tool(self) -> None:
        tool = shutil.which("baobab")
        cmd = [tool] if tool else ["xdg-open", os.path.expanduser("~")]
        subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)

    # ---- mouse -----------------------------------------------------------------------
    def enterEvent(self, _event) -> None:
        self.hover = True
        self.leave_timer.stop()
        self.note = ""
        if not self.snap:
            self.sample_processes()
        self._animate_to(1.0)

    def leaveEvent(self, _event) -> None:
        self.hover = False
        self.mouse = QPointF(-1, -1)
        self.unsetCursor()
        self.leave_timer.start()
        self.update()

    def mouseMoveEvent(self, event) -> None:
        self.mouse = event.position()
        if self.t > 0.8 and any(r.contains(self.mouse) for r in self.hit.values()):
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        else:
            self.unsetCursor()
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self.t < 0.8:
            return
        pos = event.position()
        for name, rect in self.hit.items():
            if rect.contains(pos):
                if name == "disk":
                    self.open_disk_tool()
                elif name.startswith("kill:"):
                    self.kill(name[5:])
                break
        self.update()

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        kinds = [p["tur"] for p in self.shown]
        if DENE or not kinds:
            menu.addAction("Kapat", self.quit)
        else:
            menu.addAction("1 saat sustur", lambda: self._mute(kinds, 3600))
            menu.addAction("Düzelene kadar gizle", lambda: self._mute(kinds, None))
        menu.exec(event.globalPos())

    def _mute(self, kinds: list[str], seconds) -> None:
        mute(kinds, seconds)
        self.quit()


def main() -> int:
    lock = QLockFile(QDir.tempPath() + "/bandanix-sistem-adasi.lock")
    if not lock.tryLock(100):
        return 0
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Bandanix Sistem adası")
    theme = tema.load()
    if tema.font(theme):
        app.setFont(QFont(tema.font(theme)))
    island = SystemIsland(theme)
    island.show()
    code = app.exec()
    lock.unlock()
    return code
