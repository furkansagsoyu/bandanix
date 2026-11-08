"""The floating island window: a slim pill that grows into a player on hover."""

from __future__ import annotations

import random

from PySide6.QtCore import (QEasingCurve, QPointF, QRectF, Qt, QTimer, QUrl,
                            QVariantAnimation)
from PySide6.QtGui import (QColor, QCursor, QFont, QFontMetrics, QGuiApplication,
                           QImage, QPainter, QPainterPath, QPen, QPixmap)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from bandanix_ada import dizilim
from bandanix_ada.cizim import BG, FG, MUTED, TOP_MARGIN, lerp, paint_shell

from .audio import AudioBars
from .config import Theme
from .lyrics import LyricsFetcher
from .parsing import Track, fmt_time, line_at
from .player import Player

COLLAPSED = (320, 42)
EXPANDED = (440, 172)
BAR_COUNT = 5
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
        self.setWindowTitle("Sound Island")

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

        self.leave_timer = self._single_shot(450, self._maybe_collapse)
        self.toast_timer = self._single_shot(2600, self._maybe_collapse)

        self.frame = QTimer(self)
        self.frame.setInterval(33)
        self.frame.timeout.connect(self._tick)
        self.frame.start()

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
        if not self.hover and not self.toast_timer.isActive():
            self._animate_to(0.0)

    def _apply_t(self, t) -> None:
        self.t = float(t)
        w = round(lerp(COLLAPSED[0], EXPANDED[0], self.t))
        h = round(lerp(COLLAPSED[1], EXPANDED[1], self.t))
        screen = self.screen() or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        x, y = geo.x() + (geo.width() - w) // 2, geo.y() + TOP_MARGIN
        self.setGeometry(x, y, w, h)
        dizilim.publish(ISLAND_NAME, x, y, w, h, self.isVisible())
        self.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        g = self.geometry()
        dizilim.publish(ISLAND_NAME, g.x(), g.y(), g.width(), g.height(), True)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        g = self.geometry()
        dizilim.publish(ISLAND_NAME, g.x(), g.y(), g.width(), g.height(), False)

    # ---- player events ----------------------------------------------------
    def _on_track(self, track: Track | None) -> None:
        self.track = track
        self.lyrics, self.lyric_times = [], []
        self.art, self.accent = None, QColor(self.base_accent)
        if track is None:
            if self.theme.hide_when_idle:
                self.hide()
        else:
            if not self.isVisible():
                self.show()
            self._load_art(track)
            self.lyrics_fetcher.fetch(track)
            self._animate_to(1.0)          # short "new song" toast
            self.toast_timer.start()
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

    def shutdown(self) -> None:
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
        if playing or moving:
            self.update()

    # ---- painting ---------------------------------------------------------
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing
                         | QPainter.RenderHint.SmoothPixmapTransform
                         | QPainter.RenderHint.TextAntialiasing)
        w, h, t = self.width(), self.height(), self.t
        radius = lerp(h / 2, 26, t)
        paint_shell(p, w, h, radius, self.accent, lerp(45, 95, t))

        self.hit = {}
        pill_alpha = max(0.0, 1 - t * 2.2)
        full_alpha = max(0.0, (t - 0.45) / 0.55)
        if pill_alpha > 0:
            p.setOpacity(pill_alpha)
            self._paint_pill(p, w)
        if full_alpha > 0:
            p.setOpacity(full_alpha)
            self._paint_player(p, w)
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
        art = QRectF(7, (ch - 28) / 2, 28, 28)
        self._draw_art(p, art, circle=True)
        bars_w = BAR_COUNT * 3 + (BAR_COUNT - 1) * 3
        bars = QRectF(w - 16 - bars_w, 12, bars_w, ch - 24)
        self._draw_bars(p, bars, 3, 3)
        text_r = QRectF(art.right() + 10, 0, bars.left() - art.right() - 20, ch)
        if self.track:
            label = self.track.title + (f"  ·  {self.track.artist}" if self.track.artist else "")
            self._text(p, text_r, label, self._font(13, QFont.Weight.DemiBold), FG)
            self._draw_thin_progress(p, text_r.left(), text_r.right(), ch - 6)
        else:
            self._text(p, text_r, "Şu an çalan yok", self._font(13), MUTED)

    def _paint_player(self, p: QPainter, w: int) -> None:
        pad = 16
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
        self.hit["seek"] = QRectF(bar.left(), bar.top() - 8, bar.width(), bar.height() + 16)
        frac = pos / self.track.length if self.track.length > 0 else 0.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 40))
        p.drawRoundedRect(bar, 2, 2)
        p.setBrush(self.accent)
        p.drawRoundedRect(QRectF(bar.left(), bar.top(), bar.width() * frac, bar.height()), 2, 2)
        if self.hit["seek"].contains(self.mouse):
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
            self.hit[name] = rect
            hovered = rect.contains(self.mouse)
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

    def _draw_thin_progress(self, p: QPainter, x0: float, x1: float, y: float) -> None:
        if not self.track or self.track.length <= 0:
            return
        frac = self.player.position() / self.track.length
        p.setPen(QPen(QColor(255, 255, 255, 30), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(x0, y), QPointF(x1, y))
        p.setPen(QPen(self.accent, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(x0, y), QPointF(x0 + (x1 - x0) * frac, y))

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
        over = self.t > 0.8 and any(r.contains(self.mouse) for r in self.hit.values())
        if over:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        else:
            self.unsetCursor()
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self.t < 0.8 or not self.track:
            return
        pos = event.position()
        if self.hit.get("play", QRectF()).contains(pos):
            self.player.play_pause()
        elif self.hit.get("next", QRectF()).contains(pos):
            self.player.next()
        elif self.hit.get("prev", QRectF()).contains(pos):
            self.player.previous()
        elif self.hit.get("seek", QRectF()).contains(pos) and self.track.length > 0:
            bar = self.hit["seek"]
            frac = min(1.0, max(0.0, (pos.x() - bar.left()) / bar.width()))
            self.player.seek(frac * self.track.length)
        self.update()

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.addAction("Çıkış", QApplication.quit)
        menu.exec(event.globalPos())
