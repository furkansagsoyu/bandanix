"""Saat, oynatıcı, ayarlar ve bildirimler için yüzen Bandanix adası."""

from __future__ import annotations

import math
import random

from PySide6.QtCore import (QDate, QDateTime, QEasingCurve, QEvent, QLocale, QMimeData, QPointF, QProcess,
                            QRectF, Qt, QTimer, QUrl, QVariantAnimation)
from PySide6.QtGui import (QColor, QCursor, QDesktopServices, QDrag, QFont, QFontMetrics, QGuiApplication,
                           QImage, QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QShortcut)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWidgets import QApplication, QFileDialog, QMenu, QWidget

from bandanix_ada import dizilim
from bandanix_ada.cizim import BG, FG, MUTED, lerp, paint_shell

from .audio import AudioBars
from .capture import ScreenCapture
from .config import Theme
from .desktop import Brightness, WeatherRefresh, active_window, command, weather, window_classes
from .focus import FocusTimer
from .gosterge import Levels
from .lyrics import LyricsFetcher
from .notifications import Notifications
from .parsing import Track, fmt_time, line_at
from .player import Player
from .shelf import FileShelf
from .tool_panels import ClipboardPanel, NotesPanel, load_backend

COLLAPSED = (132, 32)
EXPANDED = (440, 212)
TAB_HEIGHT = 40
TABS = ("Saat", "Müzik", "Ayarlar", "Bildirimler", "Pano", "Notlar", "Araçlar", "Dosyalar")
TOOL_TABS = {4: "pano", 5: "not"}
TOOLS_TAB, FILES_TAB = 6, 7
TOOL_EXTRA_HEIGHT = 66
TURKISH = QLocale("tr_TR")
BAR_COUNT = 5
OSD_MS = 1500                    # how long the volume / brightness indicator stays
ISLAND_NAME = "sound-island"     # other islands line up next to this one


def accent_from(image: QImage, fallback: QColor) -> QColor:
    """Pick a vivid colour from the album cover for the accent."""
    small = image.scaled(16, 16, Qt.AspectRatioMode.IgnoreAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
    best, best_score = None, -1.0
    for y in range(small.height()):
        for x in range(small.width()):
            c = QColor(small.pixel(x, y))
            v, s = c.valueF(), c.hsvSaturationF()
            if v < 0.35:
                continue
            score = s * 0.7 + v * 0.3
            if score > best_score:
                best, best_score = c, score
    if best is None or best.hsvSaturationF() < 0.2:
        return QColor(fallback)
    h, s, v, _ = best.getHsvF()
    return QColor.fromHsvF(max(h, 0.0), max(s, 0.55), max(v, 0.85))


class Island(QWidget):
    def __init__(self, player: Player, theme: Theme | None = None):
        super().__init__(None, Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setWindowTitle("Bandanix Adası")

        self.player = player
        self.theme = theme or Theme()
        self.base_accent = QColor(self.theme.accent)
        self.track: Track | None = None
        self.status = ""
        self.art: QPixmap | None = None
        self.accent = QColor(self.base_accent)
        self.lyrics: list = []
        self.lyric_times: list = []
        self.levels = [0.12] * BAR_COUNT
        self.targets = [0.12] * BAR_COUNT
        self.angle = 0.0
        self.t = 0.0                      # 0 = pill, 1 = full player
        self.hover = False
        self.mouse = QPointF(-1, -1)
        self.hit: dict[str, QRectF] = {}
        self.tab = 0
        self.wheel_delta = 0
        self.tool_panel: ClipboardPanel | NotesPanel | None = None
        self.tool_widgets: dict[str, ClipboardPanel | NotesPanel] = {}
        self.previous_window: str | None = None
        self.paste_process = QProcess(self)
        self.paste_process.setStandardErrorFile(QProcess.nullDevice())
        self.paste_timeout = self._single_shot(1500, self._stop_paste)
        self.escape = QShortcut(QKeySequence("Escape"), self)
        self.escape.setEnabled(False)
        self.escape.activated.connect(self._close_tool)
        self.brightness = Brightness(self)
        self.brightness.changed.connect(self.update)
        self.volume: tuple[int, bool] | None = None
        self.level_monitor = Levels(self)
        self.level_monitor.volume_changed.connect(self._set_volume)
        if self.theme.gosterge:
            self.level_monitor.changed.connect(self.show_level)
        self.capture = ScreenCapture(self)
        self.capture.changed.connect(self.update)
        self.focus = FocusTimer()
        self.shelf = FileShelf()
        self.shelf_page = 0
        self.shelf_message = ""
        self.shelf_press: tuple[int, QPointF] | None = None
        self.file_drag_active = False
        self.file_dialog: QFileDialog | None = None
        self.calendar_month: QDate | None = None
        self.last_minute = ""
        self.last_weather_minute = ""
        self.notifications = Notifications(self)
        self.notifications.changed.connect(self._notifications_changed)
        self.notification_index: int | None = None
        self.seen_notification: dict | None = None
        self.weather = weather()
        self.weather_refresh = WeatherRefresh(self)
        self.settings_commands = {
            "bandanix": command("bandanix"),
            "cinnamon": command("cinnamon-settings"),
        }

        self.nam = QNetworkAccessManager(self)
        self.lyrics_fetcher = LyricsFetcher(self.nam, self)
        self.lyrics_fetcher.ready.connect(self._on_lyrics)

        self.audio = None
        if self.theme.bars == "auto" and AudioBars.available():
            self.audio = AudioBars(BAR_COUNT, self)

        self.anim = QVariantAnimation(self)
        self.anim.setDuration(280)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.valueChanged.connect(self._apply_t)

        self.tool_height = QVariantAnimation(self)
        self.tool_height.setDuration(180)
        self.tool_height.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.tool_height.setStartValue(0.0)
        self.tool_height.setEndValue(0.0)
        self.tool_height.valueChanged.connect(lambda _value: self._apply_t(self.t))

        self.leave_timer = self._single_shot(450, self._maybe_collapse)
        self.recenters = 0
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            screen.availableGeometryChanged.connect(lambda *_: self._recenter())
        for ms in (3000, 10000):
            QTimer.singleShot(ms, self._recenter)
        self.osd: tuple[str, int, bool] | None = None    # (kind, percent, muted)
        self.osd_timer = self._single_shot(OSD_MS, self._end_osd)

        self.frame = QTimer(self)
        self.frame.setInterval(33)
        self.frame.timeout.connect(self._tick)

        self.clock = QTimer(self)
        self.clock.setInterval(1000)
        self.clock.timeout.connect(self._clock_tick)
        self.clock.start()

        player.trackChanged.connect(self._on_track)
        player.trackUpdated.connect(self._on_track_updated)
        player.statusChanged.connect(self._on_status)
        self._apply_t(0.0)

    def _single_shot(self, ms: int, slot) -> QTimer:
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(ms)
        timer.timeout.connect(slot)
        return timer

    # ---- size / animation -------------------------------------------------
    def _animate_to(self, target: float) -> None:
        if abs(self.t - target) < 1e-3 and self.anim.state() != QVariantAnimation.State.Running:
            return
        self.anim.stop()
        self.anim.setStartValue(self.t)
        self.anim.setEndValue(float(target))
        self.anim.start()

    def _maybe_collapse(self) -> None:
        if (not self.hover and not self.file_drag_active and self.tool_panel is None
                and self.file_dialog is None):
            self._animate_to(0.0)

    def _apply_t(self, t) -> None:
        self.t = float(t)
        w = round(lerp(COLLAPSED[0], EXPANDED[0], self.t))
        extra = float(self.tool_height.currentValue() or 0.0)
        h = round(lerp(COLLAPSED[1], EXPANDED[1] + extra, self.t))
        screen = self.screen() or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        x, y = geo.x() + (geo.width() - w) // 2, geo.y()
        self.wanted = (x, y)
        self.setGeometry(x, y, w, h)
        dizilim.publish(ISLAND_NAME, x, y, w, h, self.isVisible())
        self._layout_tool()
        self.update()

    def _recenter(self) -> None:
        self.recenters = 0
        self._apply_t(self.t)

    def moveEvent(self, event) -> None:
        # At login the window manager can start after the island and park it in a
        # corner; put it back (a few times at most, in case something insists).
        super().moveEvent(event)
        wanted = getattr(self, "wanted", None)
        if wanted and (self.x(), self.y()) != wanted and getattr(self, "recenters", 0) < 5:
            self.recenters = getattr(self, "recenters", 0) + 1
            QTimer.singleShot(0, lambda: self._apply_t(self.t))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        g = self.geometry()
        dizilim.publish(ISLAND_NAME, g.x(), g.y(), g.width(), g.height(), True)
        QTimer.singleShot(300, self._recenter)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        g = self.geometry()
        dizilim.publish(ISLAND_NAME, g.x(), g.y(), g.width(), g.height(), False)

    # ---- player events ----------------------------------------------------
    def _on_track(self, track: Track | None) -> None:
        self.track = track
        self.lyrics, self.lyric_times = [], []
        self.art, self.accent = None, QColor(self.base_accent)
        if track is not None:
            self._load_art(track)
            self.lyrics_fetcher.fetch(track)
        self.update()

    def _on_track_updated(self, track: Track) -> None:
        old_art = self.track.art_url if self.track else ""
        self.track = track
        if track.art_url != old_art:
            self._load_art(track)

    def _on_status(self, status: str) -> None:
        self.status = status
        if self.audio is not None:
            # cava only runs while music plays: zero cost when paused or idle
            if status == "Playing":
                self.audio.start()
            else:
                self.audio.stop()
        self.update()

    # ---- volume / brightness indicator ------------------------------------------------
    def _set_volume(self, value: int, muted: bool) -> None:
        self.volume = value, muted
        if self.tab == 2:
            self.update()

    def show_level(self, kind: str, value: int, muted: bool) -> None:
        if kind == "parlaklik":
            self.brightness.value = value
            self.update()
        if self.hover:
            return
        self.osd = (kind, value, muted)
        self.osd_timer.start()
        self.update()

    def _end_osd(self) -> None:
        self.osd = None
        self.update()

    def shutdown(self) -> None:
        self._leave_tool()
        self._stop_paste()
        self.capture.shutdown()
        self.level_monitor.stop()
        self.notifications.stop()
        self.weather_refresh.stop()
        dizilim.remove(ISLAND_NAME)
        if self.audio is not None:
            self.audio.stop()

    def _load_art(self, track: Track) -> None:
        url = track.art_url
        if url.startswith("file://"):
            self._set_art(QImage(QUrl(url).toLocalFile()))
        elif url.startswith("http"):
            reply = self.nam.get(QNetworkRequest(QUrl(url)))
            track_id = track.track_id

            def done():
                data = bytes(reply.readAll())
                reply.deleteLater()
                if self.track and self.track.track_id == track_id:
                    image = QImage()
                    image.loadFromData(data)
                    self._set_art(image)

            reply.finished.connect(done)

    def _set_art(self, image: QImage) -> None:
        if image.isNull():
            return
        self.art = QPixmap.fromImage(image.scaled(
            192, 192, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation))
        if self.theme.follow_cover:
            self.accent = accent_from(image, self.base_accent)
        self.update()

    def _on_lyrics(self, track_id: str, lines: list) -> None:
        if self.track and self.track.track_id == track_id:
            self.lyrics = lines
            self.lyric_times = [t for t, _ in lines]
            self.update()

    # ---- frame loop -------------------------------------------------------
    def _tick(self) -> None:
        playing = self.status == "Playing"
        real = playing and self.audio is not None and self.audio.live()
        moving = False
        for i in range(BAR_COUNT):
            if real:
                self.targets[i] = 0.12 + 0.88 * self.audio.levels[i]
            elif playing:
                if random.random() < 0.18:
                    self.targets[i] = random.uniform(0.25, 1.0)
            else:
                self.targets[i] = 0.12
            delta = self.targets[i] - self.levels[i]
            self.levels[i] += delta * (0.5 if real else 0.25)
            moving = moving or abs(delta) > 0.005
        if playing:
            self.angle = (self.angle + 0.8) % 360
        if not playing and not moving:
            self.frame.stop()
        if (playing or moving) and (self.t < 0.45 or self.tab == 1):
            self.update()

    # ---- painting ---------------------------------------------------------
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing
                         | QPainter.RenderHint.SmoothPixmapTransform
                         | QPainter.RenderHint.TextAntialiasing)
        w, h, t = self.width(), self.height(), self.t
        radius = lerp(COLLAPSED[1] / 2, 23, t)
        paint_shell(p, w, h, radius, self.accent, lerp(16, 55, t))

        self.hit = {}
        pill_alpha = max(0.0, 1 - t * 2.2)
        full_alpha = max(0.0, (t - 0.45) / 0.55)
        if pill_alpha > 0:
            p.setOpacity(pill_alpha)
            if self.osd is not None:
                self._paint_osd(p, w)
            else:
                self._paint_pill(p, w)
        if full_alpha > 0:
            p.setOpacity(full_alpha)
            self._paint_tabs(p, w)
            if self.tab == 0:
                self._paint_clock(p, w)
            elif self.tab == 1:
                p.save()
                p.translate(0, TAB_HEIGHT)
                self._paint_player(p, w)
                p.restore()
            elif self.tab == 2:
                self._paint_settings(p, w)
            elif self.tab == 3:
                self._paint_notifications(p, w)
            elif self.tab == TOOLS_TAB:
                self._paint_tools(p, w)
            elif self.tab == FILES_TAB:
                self._paint_shelf(p, w)
            elif self.tool_panel is None:
                component = "pano" if self.tab == 4 else "not-kutusu"
                self._text(p, QRectF(22, 64, w - 44, 100), f"{component} bileşenini kur",
                           self._font(15), MUTED, Qt.AlignmentFlag.AlignCenter)
        p.end()

    def _font(self, px: int, weight=QFont.Weight.Normal, italic=False) -> QFont:
        f = QFont(self.font())
        f.setPixelSize(px)
        f.setWeight(weight)
        f.setItalic(italic)
        return f

    def _text(self, p: QPainter, rect: QRectF, text: str, font: QFont, color: QColor,
              align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter) -> None:
        p.setFont(font)
        p.setPen(color)
        elided = QFontMetrics(font).elidedText(text, Qt.TextElideMode.ElideRight, int(rect.width()))
        p.drawText(rect, int(align), elided)

    def _paint_pill(self, p: QPainter, w: int) -> None:
        ch = COLLAPSED[1]
        if self.focus.deadline is not None and self.status != "Playing":
            self._text(p, QRectF(0, 0, w, ch), fmt_time(self.focus.remaining),
                       self._font(14, QFont.Weight.DemiBold), FG, Qt.AlignmentFlag.AlignCenter)
        elif self.track and self.status == "Playing":
            self._draw_art(p, QRectF(w / 2 - 34, 5, 22, 22), circle=True)
            self._draw_bars(p, QRectF(w / 2 + 7, 8, 27, 16), 3, 3)
        else:
            self._text(p, QRectF(0, 0, w, ch), QDateTime.currentDateTime().toString("HH:mm"),
                       self._font(14, QFont.Weight.DemiBold), FG, Qt.AlignmentFlag.AlignCenter)
        if self.capture.recording:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#ff536b"))
            p.drawEllipse(QPointF(12, ch / 2), 3.5, 3.5)
        if self._unread():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#ff7086"))
            p.drawEllipse(QPointF(w - 12, ch / 2), 3, 3)

    def _clock_tick(self) -> None:
        remaining = self.focus.remaining
        if self.focus.tick():
            self.notifications.add("Bandanix", "Odak süresi doldu", "Mola verebilirsin.")
            QApplication.beep()
        minute = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm")
        if self.tab == 0 and self.hover and minute != self.last_weather_minute:
            self.weather = weather()
            self.last_weather_minute = minute
        if minute != self.last_minute or remaining != self.focus.remaining:
            self.last_minute = minute
            if self.t < 0.45 or self.tab in (0, TOOLS_TAB):
                self.update()

    def _unread(self) -> bool:
        items = self.notifications.items
        return bool(items and self.seen_notification is not items[0])

    def _notifications_changed(self) -> None:
        if self.hover and self.tab == 3 and self.notifications.items:
            newest = self.notifications.items[0]
            if self.notification_index is not None and self.seen_notification is not newest:
                self.notification_index = min(self.notification_index + 1, len(self.notifications.items) - 1)
            self.seen_notification = newest
        self.update()

    def _set_tab(self, tab: int) -> None:
        if tab in TOOL_TABS and self.open_tool(TOOL_TABS[tab]):
            return
        self._leave_tool()
        self.tab = tab
        if tab == 0:
            self.weather = weather()
        elif tab == 2:
            self.brightness.request()
        elif tab == 3:
            self.notification_index = None
            self._notifications_changed()
        self.update()

    def _capture_target(self) -> None:
        if QGuiApplication.platformName() != "xcb":
            return
        window = active_window()
        if window and int(window, 16) != int(self.winId()):
            self.previous_window = window

    def open_tool(self, name: str, *, toggle: bool = False) -> bool:
        tab = next(i for i, tool in TOOL_TABS.items() if tool == name)
        if self.tab == tab and self.tool_panel is not None:
            if toggle:
                self._close_tool()
            return True
        widget = self.tool_widgets.get(name)
        if widget is None:
            backend = load_backend(name)
            if backend is None:
                return False
            if name == "pano":
                widget = ClipboardPanel(backend, self)
                widget.paste.connect(self._paste_clipboard)
            else:
                widget = NotesPanel(backend, self)
                widget.saved.connect(self._close_tool)
            widget.hide()
            self.tool_widgets[name] = widget

        if toggle or self.tool_panel is None:
            self._capture_target()
        self._leave_tool()
        self.tab = tab
        self.tool_panel = widget
        self.escape.setEnabled(True)
        self.leave_timer.stop()
        self.osd = None
        widget.prepare()
        self._animate_tool_height(TOOL_EXTRA_HEIGHT)
        self._animate_to(1.0)
        self._layout_tool()
        self.update()
        return True

    def _animate_tool_height(self, height: int) -> None:
        current = self.tool_height.currentValue() or 0.0
        self.tool_height.stop()
        self.tool_height.setStartValue(float(current))
        self.tool_height.setEndValue(float(height))
        self.tool_height.start()

    def _layout_tool(self) -> None:
        widget = self.tool_panel
        if widget is None or self.t < 0.9 or self.height() < EXPANDED[1] + 25:
            return
        widget.setGeometry(15, TAB_HEIGHT + 5, self.width() - 30, self.height() - TAB_HEIGHT - 19)
        if widget.isHidden():
            widget.show()
            self.activateWindow()
            widget.take_focus()

    def _leave_tool(self) -> None:
        if self.tool_panel is None:
            return
        if isinstance(self.tool_panel, NotesPanel):
            try:
                self.tool_panel.store_draft()
            except OSError:
                pass
        self.tool_panel.hide()
        self.tool_panel = None
        self.escape.setEnabled(False)
        self._animate_tool_height(0)

    def _close_tool(self, *, restore_focus: bool = True) -> None:
        target = self.previous_window
        was_active = self.isActiveWindow()
        self._set_tab(0)
        self._animate_to(0.0)
        if restore_focus and was_active and target and command("xdotool"):
            QProcess.startDetached("xdotool", ["windowactivate", target])

    def _paste_clipboard(self, text: str) -> None:
        panel = self.tool_panel
        if not isinstance(panel, ClipboardPanel):
            return
        QApplication.clipboard().setText(text)
        target = self.previous_window
        self._close_tool(restore_focus=False)
        if not target or not command("xdotool"):
            return
        classes = window_classes(target)
        keys = next((panel.backend.paste_keys(name) for name in classes
                     if name.lower() in panel.backend.TERMINALS), "ctrl+v")
        self._stop_paste()
        self.paste_process.start("xdotool", ["windowactivate", "--sync", target, "key",
                                             "--clearmodifiers", keys])
        self.paste_timeout.start()

    def _stop_paste(self) -> None:
        if self.paste_process.state() != QProcess.ProcessState.NotRunning:
            self.paste_process.kill()
            self.paste_process.waitForFinished(250)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if (event.type() == QEvent.Type.ActivationChange and self.tool_panel is not None
                and not self.isActiveWindow() and not QApplication.activePopupWidget()):
            self._close_tool(restore_focus=False)

    def _button(self, p: QPainter, name: str, rect: QRectF, label: str,
                selected: bool = False, enabled: bool = True) -> None:
        if enabled:
            self.hit[name] = rect
        hovered = enabled and rect.contains(self.mouse)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 29 if hovered or selected else 12))
        p.drawRoundedRect(rect, 8, 8)
        self._text(p, rect, label, self._font(12, QFont.Weight.DemiBold),
                   FG if selected or enabled else MUTED, Qt.AlignmentFlag.AlignCenter)

    def _paint_tabs(self, p: QPainter, w: int) -> None:
        metrics = QFontMetrics(self._font(12, QFont.Weight.DemiBold))
        labels = [label + " •" if i == 3 and self._unread() else label
                  for i, label in enumerate(TABS)]
        widths = [metrics.horizontalAdvance(label) for label in labels]
        padding = (w - 24 - 4 * (len(TABS) - 1) - sum(widths)) / len(TABS)
        x = 12
        for i, (label, width) in enumerate(zip(labels, widths)):
            width = max(18.0, width + padding)
            self._button(p, f"tab{i}", QRectF(x, 9, width, 25), label, selected=self.tab == i)
            x += width + 4

    def _card(self, p: QPainter, rect: QRectF, brush=None) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(brush if brush is not None else QColor("#1b1b21"))
        p.drawRoundedRect(rect, 13, 13)

    def _paint_clock(self, p: QPainter, w: int) -> None:
        now = QDateTime.currentDateTime()
        width = (w - 45) / 2
        right = 24 + width
        self._card(p, QRectF(15, 49, width, 145))
        self._card(p, QRectF(right, 49, width, 145))
        self._text(p, QRectF(28, 64, width - 26, 23), "Yerel saat", self._font(12), MUTED)
        self._text(p, QRectF(28, 91, width - 26, 59), now.toString("HH:mm"),
                   self._font(46, QFont.Weight.DemiBold), FG)
        self._button(p, "calendar", QRectF(28, 155, width - 26, 23),
                     TURKISH.toString(now.date(), "d MMMM dddd"), selected=self.calendar_month is not None)

        if self.calendar_month is not None:
            self._paint_calendar(p, QRectF(right + 7, 54, width - 14, 135), now.date())
            return

        x = right + 13
        current = self.weather.get("simdi")
        if isinstance(current, dict) and current.get("sicaklik") is not None:
            self._text(p, QRectF(x, 64, width - 26, 23), str(self.weather.get("sehir") or "Hava durumu"),
                       self._font(12), MUTED)
            self._text(p, QRectF(x, 91, width - 26, 59), f"{current['sicaklik']}°",
                       self._font(46, QFont.Weight.DemiBold), FG)
            self._text(p, QRectF(x, 155, width - 26, 23), str(current.get("yazi") or ""),
                       self._font(13), MUTED)
        else:
            self._text(p, QRectF(x, 68, width - 26, 25), "Hava durumu", self._font(14), FG)
            self._button(p, "bandanix", QRectF(x, 121, width - 26, 34), "Şehir ayarla",
                         enabled=bool(self.settings_commands["bandanix"]))

    def _paint_calendar(self, p: QPainter, rect: QRectF, today: QDate) -> None:
        month = self.calendar_month
        x, y, w = rect.x(), rect.y(), rect.width()
        center = Qt.AlignmentFlag.AlignCenter
        self._button(p, "calendar_prev", QRectF(x, y, 23, 20), "‹")
        self._button(p, "calendar_next", QRectF(x + w - 23, y, 23, 20), "›")
        self._text(p, QRectF(x + 25, y, w - 50, 20), TURKISH.toString(month, "MMMM yyyy"),
                   self._font(12, QFont.Weight.DemiBold), FG, center)
        cell = w / 7
        for col, day in enumerate(("Pt", "Sa", "Ça", "Pe", "Cu", "Ct", "Pa")):
            self._text(p, QRectF(x + cell * col, y + 22, cell, 16), day, self._font(10), MUTED, center)
        first = month.dayOfWeek() - 1
        for day in range(1, month.daysInMonth() + 1):
            row, col = divmod(first + day - 1, 7)
            box = QRectF(x + cell * col, y + 39 + 16 * row, cell, 16)
            if month.addDays(day - 1) == today:
                self._card(p, box.adjusted(3, 0, -3, 0), self.accent)
            self._text(p, box, str(day), self._font(10), FG, center)

    def _paint_settings(self, p: QPainter, w: int) -> None:
        width = (w - 45) / 2
        right = 24 + width
        level = self.brightness.value
        volume, muted = self.volume if self.volume is not None else (None, False)
        for x, label, value in ((15, "Parlaklık", level), (right, "Ses", volume)):
            self._card(p, QRectF(x, 49, width, 102))
            self._text(p, QRectF(x + 13, 55, width - 26, 23), label,
                       self._font(13, QFont.Weight.DemiBold), FG)
            text = "—" if value is None else f"%{value}"
            if label == "Ses" and muted:
                text = "Sessiz"
            self._text(p, QRectF(x + 13, 80, width - 26, 30), text,
                       self._font(21, QFont.Weight.DemiBold), FG)
        unit = (width - 38) / 3
        for i, (key, label) in enumerate((("volume_down", "−"), ("volume_mute", "Sessiz"), ("volume_up", "+"))):
            self._button(p, key, QRectF(right + 13 + i * (unit + 6), 114, unit, 26), label,
                         enabled=volume is not None)
        half = (width - 32) / 2
        for i, (key, label) in enumerate((("brightness_down", "−"), ("brightness_up", "+"))):
            self._button(p, key, QRectF(28 + i * (half + 6), 114, half, 26), label, enabled=level is not None)
        self._button(p, "bandanix", QRectF(15, 160, width, 34), "Bandanix Ayarları",
                     enabled=bool(self.settings_commands["bandanix"]))
        self._button(p, "cinnamon", QRectF(right, 160, width, 34), "Sistem Ayarları",
                     enabled=bool(self.settings_commands["cinnamon"]))

    def _paint_tools(self, p: QPainter, w: int) -> None:
        width = (w - 45) / 2
        right = 24 + width
        self._card(p, QRectF(15, 49, width, 145))
        self._text(p, QRectF(27, 57, width - 24, 24), "Odak sayacı", self._font(13), MUTED)
        self._text(p, QRectF(27, 81, width - 24, 42), fmt_time(self.focus.remaining),
                   self._font(31, QFont.Weight.DemiBold), FG)
        preset = (width - 38) / 4
        for i, minutes in enumerate(self.focus.PRESETS):
            self._button(p, f"focus_{minutes}", QRectF(27 + i * (preset + 4), 125, preset, 22),
                         str(minutes), selected=self.focus.minutes == minutes)
        half = (width - 32) / 2
        self._button(p, "focus_toggle", QRectF(27, 153, half, 29),
                     "Başlat" if self.focus.deadline is None else "Duraklat")
        self._button(p, "focus_reset", QRectF(33 + half, 153, half, 29), "Sıfırla")
        self._button(p, "screenshot", QRectF(right, 49, width, 37), "Ekran görüntüsü",
                     enabled=bool(self.capture.screenshot))
        self._button(p, "record", QRectF(right, 94, width, 37),
                     "Kaydı durdur" if self.capture.recording else "Ekranı kaydet",
                     enabled=bool(self.capture.program) and QGuiApplication.platformName() == "xcb"
                     and not self.capture.stopping)
        self._text(p, QRectF(right + 4, 139, width - 8, 49), self.capture.status or "Alan görüntüsü · sessiz video",
                   self._font(11), MUTED)

    def _paint_shelf(self, p: QPainter, w: int) -> None:
        first = self.shelf_page * 3
        for index, path in enumerate(self.shelf.paths[first:first + 3], first):
            y = 48 + (index - first) * 37
            rect = QRectF(16, y, w - 68, 32)
            self.hit[f"file_item_{index}"] = rect
            self._card(p, rect, QColor("#27272f") if rect.contains(self.mouse) else None)
            self._text(p, rect.adjusted(11, 0, -9, 0), path.name, self._font(13), FG)
            self._button(p, f"file_remove_{index}", QRectF(w - 46, y, 30, 32), "×")
        if not self.shelf.paths:
            self._text(p, QRectF(18, 54, w - 36, 92), "Dosyaları buraya sürükle",
                       self._font(15), MUTED, Qt.AlignmentFlag.AlignCenter)
        self._button(p, "file_add", QRectF(16, 166, 89, 28), "Dosya ekle")
        self._text(p, QRectF(115, 166, w - 218, 28), self.shelf_message,
                   self._font(11), MUTED)
        self._button(p, "file_prev", QRectF(w - 93, 166, 35, 28), "‹", enabled=first > 0)
        self._button(p, "file_next", QRectF(w - 51, 166, 35, 28), "›",
                     enabled=first + 3 < len(self.shelf.paths))

    def _add_files(self, urls: list[QUrl]) -> bool:
        paths = self.shelf.paths_from_urls(urls)
        if not paths:
            return False
        saved = self.shelf.add(paths)
        self.shelf_page = 0
        self.shelf_message = "" if saved else "Raf kaydedilemedi"
        self.update()
        return True

    def _open_file_dialog(self) -> None:
        if self.file_dialog is not None:
            self.file_dialog.raise_()
            return
        self.leave_timer.stop()
        dialog = QFileDialog(self)
        self.file_dialog = dialog
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
        dialog.setWindowTitle("Dosya rafına ekle")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        dialog.filesSelected.connect(self._add_selected_files)
        dialog.finished.connect(self._finish_file_dialog)
        dialog.open()

    def _add_selected_files(self, files: list[str]) -> None:
        self._add_files([QUrl.fromLocalFile(path) for path in files])

    def _finish_file_dialog(self, _result: int) -> None:
        dialog, self.file_dialog = self.file_dialog, None
        if dialog is not None:
            dialog.deleteLater()
        if not self.hover:
            self.leave_timer.start()

    def dragEnterEvent(self, event) -> None:
        if event.possibleActions() & Qt.DropAction.CopyAction and event.mimeData().hasUrls():
            self.file_drag_active = True
            self.leave_timer.stop()
            self.anim.stop()
            self.tool_height.stop()
            self._accept_file_copy(event)

    @staticmethod
    def _accept_file_copy(event) -> None:
        event.setDropAction(Qt.DropAction.CopyAction)
        event.accept()

    def dragMoveEvent(self, event) -> None:
        if self.file_drag_active and event.possibleActions() & Qt.DropAction.CopyAction:
            self._accept_file_copy(event)

    def _finish_file_drag(self, *, open_shelf: bool = False) -> None:
        self.file_drag_active = False
        self.hover = self.underMouse()
        self._animate_tool_height(TOOL_EXTRA_HEIGHT if self.tool_panel is not None else 0)
        if self.hover or open_shelf:
            self._animate_to(1.0)
        if not self.hover:
            self.leave_timer.start()

    def dragLeaveEvent(self, event) -> None:
        self._finish_file_drag()
        event.accept()

    def dropEvent(self, event) -> None:
        if not event.possibleActions() & Qt.DropAction.CopyAction:
            self._finish_file_drag()
            return
        # Veriyi Xdnd işlemi sürerken kopyala. Pencereyi ve rafı işlem
        # bittikten sonra güncelle.
        urls = event.mimeData().urls()
        if not any(url.isLocalFile() and not url.host() for url in urls):
            self._finish_file_drag()
            return
        self._accept_file_copy(event)
        QTimer.singleShot(0, lambda: self._show_dropped_files(urls))

    def _show_dropped_files(self, urls: list[QUrl]) -> None:
        added = self._add_files(urls)
        if added:
            self._set_tab(FILES_TAB)
        self._finish_file_drag(open_shelf=added)

    def _paint_notifications(self, p: QPainter, w: int) -> None:
        items = self.notifications.items
        if not items:
            label = "Bildirim yok" if self.notifications.ready else "Bildirim bağlantısı kullanılamıyor"
            self._text(p, QRectF(22, 60, w - 44, 112), label, self._font(15), MUTED,
                       Qt.AlignmentFlag.AlignCenter)
            return
        if self.notification_index is None:
            for i, item in enumerate(list(items)[:3]):
                y = 48 + 38 * i
                rect = QRectF(17, y, w - 34, 35)
                self.hit[f"notice_item{i}"] = rect
                self._card(p, rect, QColor("#27272f") if rect.contains(self.mouse) else None)
                self._text(p, QRectF(28, y + 2, 95, 31), item["app"] or "Bildirim", self._font(11), MUTED)
                self._text(p, QRectF(127, y + 2, w - 156, 31), item["summary"] or item["body"],
                           self._font(13, QFont.Weight.DemiBold), FG)
            self._text(p, QRectF(22, 166, 180, 26), f"{len(items)} bildirim", self._font(12), MUTED)
            self._button(p, "notice_clear", QRectF(w - 100, 166, 78, 26), "Temizle")
            return
        item = items[self.notification_index]
        self._text(p, QRectF(22, 48, w - 44, 20), item["app"], self._font(12), MUTED)
        self._text(p, QRectF(22, 69, w - 44, 26), item["summary"],
                   self._font(17, QFont.Weight.DemiBold), FG)
        body = QRectF(22, 99, w - 44, 60)
        p.save()
        p.setClipRect(body)
        p.setPen(FG)
        p.setFont(self._font(13))
        p.drawText(body, int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignTop), item["body"])
        p.restore()
        self._button(p, "notice_newer", QRectF(22, 166, 58, 26), "Yeni", enabled=self.notification_index > 0)
        self._button(p, "notice_older", QRectF(86, 166, 58, 26), "Eski",
                     enabled=self.notification_index + 1 < len(items))
        self._text(p, QRectF(154, 166, 80, 26), f"{self.notification_index + 1} / {len(items)}",
                   self._font(12), MUTED)
        self._button(p, "notice_list", QRectF(w - 100, 166, 78, 26), "Listeye dön")

    def _paint_osd(self, p: QPainter, w: int) -> None:
        kind, value, muted = self.osd
        ch = COLLAPSED[1]
        icon = QRectF(10, (ch - 17) / 2, 17, 17)
        self._level_icon(p, kind, muted, icon)
        text = "Sessiz" if muted else f"%{value}"
        font = self._font(11, QFont.Weight.DemiBold)
        text_w = 36
        bar = QRectF(icon.right() + 6, ch / 2 - 2, w - icon.right() - text_w - 16, 4)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 40))
        p.drawRoundedRect(bar, 3, 3)
        fill = QColor(self.accent)
        if muted:
            fill.setAlpha(70)
        frac = max(0.0, min(1.0, value / 100))
        if frac > 0:
            p.setBrush(fill)
            p.drawRoundedRect(QRectF(bar.left(), bar.top(), max(6.0, bar.width() * frac), bar.height()), 3, 3)
        self._text(p, QRectF(w - 8 - text_w, 0, text_w, ch), text, font, MUTED if muted else FG,
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def _level_icon(self, p: QPainter, kind: str, muted: bool, rect: QRectF) -> None:
        p.save()
        c = rect.center()
        cx, cy, s = c.x(), c.y(), rect.width() / 2
        if kind == "parlaklik":
            p.setPen(QPen(FG, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for k in range(8):
                a = k * math.pi / 4
                p.drawLine(QPointF(cx + math.cos(a) * s * 0.62, cy + math.sin(a) * s * 0.62),
                           QPointF(cx + math.cos(a) * s * 0.92, cy + math.sin(a) * s * 0.92))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(FG)
            p.drawEllipse(c, s * 0.38, s * 0.38)
        else:
            body = QPainterPath(QPointF(cx - s * 0.85, cy - s * 0.3))
            body.lineTo(cx - s * 0.45, cy - s * 0.3)
            body.lineTo(cx, cy - s * 0.75)
            body.lineTo(cx, cy + s * 0.75)
            body.lineTo(cx - s * 0.45, cy + s * 0.3)
            body.lineTo(cx - s * 0.85, cy + s * 0.3)
            body.closeSubpath()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(MUTED if muted else FG)
            p.drawPath(body)
            p.setBrush(Qt.BrushStyle.NoBrush)
            if muted:
                p.setPen(QPen(MUTED, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawLine(QPointF(cx + s * 0.3, cy - s * 0.35), QPointF(cx + s * 0.95, cy + s * 0.35))
                p.drawLine(QPointF(cx + s * 0.3, cy + s * 0.35), QPointF(cx + s * 0.95, cy - s * 0.35))
            else:
                p.setPen(QPen(FG, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                waves = 1 if self.osd[1] < 34 else 2 if self.osd[1] < 67 else 3
                for i in range(waves):
                    r = s * (0.35 + 0.28 * i)
                    p.drawArc(QRectF(cx - r + s * 0.1, cy - r, 2 * r, 2 * r), -45 * 16, 90 * 16)
        p.restore()

    def _paint_player(self, p: QPainter, w: int) -> None:
        pad = 16
        if self.track:
            color = QColor(self.accent)
            color.setAlpha(48)
            backdrop = QLinearGradient(0, 0, w, 112)
            backdrop.setColorAt(0, color)
            backdrop.setColorAt(1, QColor("#1b1b21"))
            self._card(p, QRectF(12, 6, w - 24, 112), backdrop)
        art = QRectF(pad, pad, 96, 96)
        self._draw_art(p, art, circle=False)
        x, right = art.right() + 14, w - pad
        bars_w = BAR_COUNT * 3 + (BAR_COUNT - 1) * 3
        bars = QRectF(right - bars_w, pad + 3, bars_w, 16)
        self._draw_bars(p, bars, 3, 3)

        if not self.track:
            self._text(p, QRectF(x, pad, right - x, 96), "Şu an çalan yok",
                       self._font(15, QFont.Weight.DemiBold), MUTED)
            return

        self._text(p, QRectF(x, pad, bars.left() - x - 8, 22), self.track.title,
                   self._font(16, QFont.Weight.Bold), FG)
        self._text(p, QRectF(x, pad + 24, right - x, 18), self.track.artist,
                   self._font(13), MUTED)

        pos = self.player.position()
        lyric = line_at(self.lyric_times, self.lyrics, pos + 0.3)
        lyric_r = QRectF(x, pad + 50, right - x, 44)
        p.save()
        p.setClipRect(lyric_r)
        if lyric:
            p.setFont(self._font(14, QFont.Weight.DemiBold))
            p.setPen(self.accent)
            p.drawText(lyric_r, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
                                    | Qt.TextFlag.TextWordWrap), lyric)
        elif self.track.album:
            self._text(p, QRectF(x, pad + 50, right - x, 18), self.track.album,
                       self._font(12, italic=True), MUTED)
        p.restore()

        # progress bar (click to seek)
        bar = QRectF(pad, 124, w - 2 * pad, 4)
        seek = QRectF(bar.left(), bar.top() - 8, bar.width(), bar.height() + 16)
        frac = pos / self.track.length if self.track.length > 0 else 0.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 40))
        p.drawRoundedRect(bar, 2, 2)
        p.setBrush(self.accent)
        p.drawRoundedRect(QRectF(bar.left(), bar.top(), bar.width() * frac, bar.height()), 2, 2)
        if seek.translated(0, TAB_HEIGHT).contains(self.mouse):
            p.setBrush(FG)
            p.drawEllipse(QPointF(bar.left() + bar.width() * frac, bar.center().y()), 5, 5)

        small = self._font(11)
        self._text(p, QRectF(pad, 132, 60, 16), fmt_time(pos), small, MUTED)
        self._text(p, QRectF(w - pad - 60, 132, 60, 16), fmt_time(self.track.length), small,
                   MUTED, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # transport buttons
        cx, cy = w / 2, 150
        buttons = {
            "prev": QRectF(cx - 52 - 14, cy - 14, 28, 28),
            "play": QRectF(cx - 17, cy - 17, 34, 34),
            "next": QRectF(cx + 52 - 14, cy - 14, 28, 28),
        }
        for name, rect in buttons.items():
            self.hit[name] = rect.translated(0, TAB_HEIGHT)
            hovered = self.hit[name].contains(self.mouse)
            if name == "play":
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(self.accent if hovered else FG)
                p.drawEllipse(rect)
                kind = "pause" if self.status == "Playing" else "play"
                self._icon(p, kind, rect, BG)
            else:
                if hovered:
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QColor(255, 255, 255, 28))
                    p.drawEllipse(rect)
                self._icon(p, name, rect, FG)
        self.hit["seek"] = seek.translated(0, TAB_HEIGHT)

    def _draw_art(self, p: QPainter, rect: QRectF, circle: bool) -> None:
        p.save()
        clip = QPainterPath()
        if circle:
            clip.addEllipse(rect)
        else:
            clip.addRoundedRect(rect, 12, 12)
        p.setClipPath(clip, Qt.ClipOperation.IntersectClip)
        if self.art is not None:
            if circle:
                c = rect.center()
                p.translate(c)
                p.rotate(self.angle)
                p.translate(-c)
            p.drawPixmap(rect, self.art, QRectF(self.art.rect()))
        else:
            p.fillPath(clip, QColor(40, 40, 46))
            p.setFont(self._font(int(rect.height() * 0.5)))
            p.setPen(MUTED)
            p.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), "♪")
        p.restore()

    def _draw_bars(self, p: QPainter, rect: QRectF, bw: float, gap: float) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.accent)
        for i, level in enumerate(self.levels):
            bh = max(2.0, rect.height() * level)
            x = rect.left() + i * (bw + gap)
            p.drawRoundedRect(QRectF(x, rect.center().y() - bh / 2, bw, bh), bw / 2, bw / 2)

    def _icon(self, p: QPainter, kind: str, rect: QRectF, color: QColor) -> None:
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        c, s = rect.center(), rect.width() * 0.26
        cx, cy = c.x(), c.y()
        if kind == "play":
            path = QPainterPath(QPointF(cx - s * 0.6, cy - s))
            path.lineTo(cx - s * 0.6, cy + s)
            path.lineTo(cx + s, cy)
            path.closeSubpath()
            p.drawPath(path)
        elif kind == "pause":
            p.drawRoundedRect(QRectF(cx - s * 0.8, cy - s, s * 0.55, s * 2), 1, 1)
            p.drawRoundedRect(QRectF(cx + s * 0.25, cy - s, s * 0.55, s * 2), 1, 1)
        else:
            sign = 1 if kind == "next" else -1
            path = QPainterPath(QPointF(cx - sign * s, cy - s))
            path.lineTo(cx - sign * s, cy + s)
            path.lineTo(cx + sign * s * 0.5, cy)
            path.closeSubpath()
            p.drawPath(path)
            bar_x = cx + sign * s * 0.5 if sign > 0 else cx + sign * s * 0.5 - s * 0.35
            p.drawRect(QRectF(bar_x, cy - s, s * 0.35, s * 2))
        p.restore()

    # ---- mouse ------------------------------------------------------------
    def enterEvent(self, _event) -> None:
        self.hover = True
        if self.file_drag_active:
            return
        self.wheel_delta = 0
        if (self.tool_panel is None and self.t < 0.5
                and self.anim.state() != QVariantAnimation.State.Running):
            self._capture_target()
            self._set_tab(0)
        self.leave_timer.stop()
        self._animate_to(1.0)

    def leaveEvent(self, _event) -> None:
        self.hover = False
        self.mouse = QPointF(-1, -1)
        self.unsetCursor()
        self.leave_timer.start()
        self.update()

    def mouseMoveEvent(self, event) -> None:
        self.mouse = event.position()
        if self.shelf_press is not None and event.buttons() & Qt.MouseButton.LeftButton:
            index, origin = self.shelf_press
            if (self.mouse - origin).manhattanLength() >= QApplication.startDragDistance():
                self.shelf_press = None
                if index < len(self.shelf.paths):
                    path = self.shelf.paths[index]
                    if path.is_file():
                        mime = QMimeData()
                        mime.setUrls([QUrl.fromLocalFile(str(path))])
                        drag = QDrag(self)
                        drag.setMimeData(mime)
                        drag.exec(Qt.DropAction.CopyAction)
                        drag.deleteLater()
                return
        over = self.t > 0.8 and any(r.contains(self.mouse) for r in self.hit.values())
        if over:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        else:
            self.unsetCursor()
        self.update()

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        if not delta:
            return
        if self.wheel_delta * delta < 0:
            self.wheel_delta = 0
        self.wheel_delta += delta
        if abs(self.wheel_delta) >= 120:
            tab = self.tab + (1 if self.wheel_delta < 0 else -1)
            self._set_tab(max(0, min(len(TABS) - 1, tab)))
            self.wheel_delta = 0
        event.accept()

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self.t < 0.8:
            return
        pos = event.position()
        action = next((name for name, rect in self.hit.items() if rect.contains(pos)), "")
        if action.startswith("tab"):
            self._set_tab(int(action[-1]))
        elif action in ("bandanix", "cinnamon"):
            if executable := self.settings_commands[action]:
                QProcess.startDetached(executable, [])
        elif action == "file_add":
            self._open_file_dialog()
        elif action == "file_prev":
            self.shelf_page -= 1
        elif action == "file_next":
            self.shelf_page += 1
        elif action.startswith("file_remove_"):
            saved = self.shelf.remove(int(action.removeprefix("file_remove_")))
            self.shelf_message = "" if saved else "Raf kaydedilemedi"
            self.shelf_page = min(self.shelf_page, max(0, (len(self.shelf.paths) - 1) // 3))
        elif action.startswith("file_item_"):
            self.shelf_press = int(action.removeprefix("file_item_")), pos
        elif action == "calendar":
            today = QDate.currentDate()
            self.calendar_month = QDate(today.year(), today.month(), 1) if self.calendar_month is None else None
        elif action in ("calendar_prev", "calendar_next") and self.calendar_month is not None:
            self.calendar_month = self.calendar_month.addMonths(-1 if action == "calendar_prev" else 1)
        elif action.startswith("volume_"):
            self.level_monitor.adjust_volume(action.removeprefix("volume_"))
        elif action == "focus_toggle":
            self.focus.toggle()
        elif action == "focus_reset":
            self.focus.reset()
        elif action.startswith("focus_"):
            self.focus.reset(int(action.removeprefix("focus_")))
        elif action == "screenshot":
            self._animate_to(0.0)
            QTimer.singleShot(320, lambda: QProcess.startDetached(self.capture.screenshot, ["--area"]))
        elif action == "record":
            self.capture.toggle()
        elif action in ("brightness_down", "brightness_up"):
            self.brightness.request(1 if action == "brightness_up" else -1)
        elif action == "notice_clear":
            self.notifications.items.clear()
            self.seen_notification = None
            self.notification_index = None
        elif action == "notice_list":
            self.notification_index = None
        elif action.startswith("notice_item"):
            self.notification_index = int(action[-1])
        elif action == "notice_newer" and self.notification_index is not None:
            self.notification_index = max(0, self.notification_index - 1)
        elif action == "notice_older" and self.notification_index is not None:
            self.notification_index = min(len(self.notifications.items) - 1, self.notification_index + 1)
        elif action == "play":
            self.player.play_pause()
        elif action == "next":
            self.player.next()
        elif action == "prev":
            self.player.previous()
        elif action == "seek" and self.track and self.track.length > 0:
            bar = self.hit["seek"]
            frac = min(1.0, max(0.0, (pos.x() - bar.left()) / bar.width()))
            self.player.seek(frac * self.track.length)
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.shelf_press is not None:
            index, _ = self.shelf_press
            self.shelf_press = None
            if index < len(self.shelf.paths):
                path = self.shelf.paths[index]
                opened = path.is_file() and QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
                self.shelf_message = "" if opened else "Dosya açılamadı"
                self.update()

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        if self.capture.recording:
            menu.addAction("Ekran kaydını durdur", self.capture.stop)
        menu.addAction("Çıkış", QApplication.quit)
        menu.exec(event.globalPos())
