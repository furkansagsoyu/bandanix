"""Odak süresini duvar saati değişikliklerinden bağımsız tutar."""
from __future__ import annotations

import math
import time


class FocusTimer:
    PRESETS = (5, 15, 25, 45)

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.minutes = 25
        self.remaining = self.minutes * 60
        self.deadline: float | None = None

    def reset(self, minutes: int | None = None) -> None:
        if minutes is not None:
            self.minutes = minutes
        self.deadline = None
        self.remaining = self.minutes * 60

    def toggle(self) -> None:
        if self.deadline is None:
            if not self.remaining:
                self.reset()
            self.deadline = self.clock() + self.remaining
        else:
            self.tick()
            self.deadline = None

    def tick(self) -> bool:
        if self.deadline is None:
            return False
        self.remaining = max(0, math.ceil(self.deadline - self.clock()))
        if self.remaining:
            return False
        self.deadline = None
        return True
