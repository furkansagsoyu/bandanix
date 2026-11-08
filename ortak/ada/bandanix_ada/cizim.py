"""Qt painting shared by the islands: colours and the pill shell."""
from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen

TOP_MARGIN = 8

BG = QColor(12, 12, 14, 240)
FG = QColor(245, 245, 247)
MUTED = QColor(150, 150, 160)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def paint_shell(p: QPainter, w: int, h: int, radius: float, edge: QColor,
                edge_alpha: int) -> QPainterPath:
    """Dark rounded body with a thin accent edge; clips later painting to the shape."""
    shape = QPainterPath()
    shape.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), radius, radius)
    p.fillPath(shape, BG)
    line = QColor(edge)
    line.setAlpha(int(edge_alpha))
    p.setPen(QPen(line, 1))
    p.drawPath(shape)
    p.setClipPath(shape)
    return shape
