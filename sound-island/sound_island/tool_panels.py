"""Pano geçmişi ve hızlı not için adanın içindeki Qt sayfaları."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit, QListView, QListWidget,
                               QListWidgetItem, QMenu, QPlainTextEdit, QPushButton,
                               QVBoxLayout, QWidget)

USER_ROLE = Qt.ItemDataRole.UserRole
BACKENDS = {"pano": ("pano", "pano_gecmis"), "not": ("not-kutusu", "notes")}
STYLE = """
QWidget { color: #eeeef2; font-size: 13px; }
QLabel { color: #aaaab4; }
QLineEdit, QPlainTextEdit, QListWidget {
    background: #17171c; border: 1px solid #2c2c34; border-radius: 10px; padding: 6px;
    selection-background-color: #454052; selection-color: #ffffff;
}
QListWidget::item { padding: 5px 7px; border-radius: 5px; }
QListWidget::item:hover { background: #25252d; }
QListWidget#clipboardCards::item {
    background: #202027; border: 1px solid #30303b; border-radius: 9px; margin: 3px;
}
QListWidget#clipboardCards::item:selected { background: #37313f; border-color: #685b73; }
QPushButton { background: #26262e; border: 0; border-radius: 8px; padding: 6px 12px; }
QPushButton:hover { background: #383842; }
QPushButton:disabled { color: #777783; }
"""


def load_backend(panel: str):
    folder, module = BACKENDS[panel]
    path = Path(__file__).resolve().parents[2] / folder / f"{module}.py"
    if not path.is_file():
        return None
    name = f"_bandanix_island_{module}"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    backend = importlib.util.module_from_spec(spec)
    sys.modules[name] = backend
    try:
        spec.loader.exec_module(backend)
    except Exception:
        del sys.modules[name]
        raise
    return backend


class ClipboardPanel(QWidget):
    paste = Signal(str)

    def __init__(self, backend, parent: QWidget):
        super().__init__(parent)
        self.backend = backend
        self.setStyleSheet(STYLE)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Pano geçmişinde ara")
        self.search.installEventFilter(self)
        self.search.textChanged.connect(self.refresh)
        self.search.returnPressed.connect(self.activate)

        self.items = QListWidget()
        self.items.setObjectName("clipboardCards")
        self.items.setViewMode(QListView.ViewMode.IconMode)
        self.items.setResizeMode(QListView.ResizeMode.Adjust)
        self.items.setMovement(QListView.Movement.Static)
        self.items.setGridSize(QSize(126, 62))
        self.items.setWordWrap(True)
        self.items.itemActivated.connect(self.activate)
        self.items.itemClicked.connect(self.activate)
        self.items.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.items.customContextMenuRequested.connect(self.menu)
        self.items.installEventFilter(self)

        self.hint = QLabel()
        self.clear = QPushButton("Temizle")
        self.clear.clicked.connect(self.clear_history)
        self.confirm = QTimer(self)
        self.confirm.setSingleShot(True)
        self.confirm.timeout.connect(lambda: self.clear.setText("Temizle"))

        footer = QHBoxLayout()
        footer.addWidget(self.hint, 1)
        footer.addWidget(self.clear)
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(self.search)
        box.addWidget(self.items, 1)
        box.addLayout(footer)

    def prepare(self) -> None:
        self.search.clear()
        self.refresh()

    def take_focus(self) -> None:
        self.search.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def refresh(self, *_args) -> None:
        current = self.items.currentItem()
        selected = current.data(USER_ROLE)["metin"] if current else None
        self.items.clear()
        query = self.search.text()
        for entry in self.backend.items():
            if not self.backend.matches(entry["metin"], query):
                continue
            prefix = "📌 " if entry["sabit"] else ""
            row = QListWidgetItem(prefix + self.backend.title(entry["metin"], 82), self.items)
            row.setData(USER_ROLE, entry)
            row.setSizeHint(QSize(120, 56))
            if entry["metin"] == selected:
                self.items.setCurrentItem(row)
        count = self.items.count()
        if count and self.items.currentRow() < 0:
            self.items.setCurrentRow(0)
        self.hint.setText("↑↓ seç · Enter yapıştır" if count else
                          "Eşleşme yok" if query else "Pano geçmişi boş")

    def activate(self, item=None) -> None:
        item = item or self.items.currentItem()
        if item:
            self.paste.emit(item.data(USER_ROLE)["metin"])

    def menu(self, point) -> None:
        item = self.items.itemAt(point)
        if not item:
            return
        entry = item.data(USER_ROLE)
        menu = QMenu(self)
        pin = menu.addAction("Sabitlemeyi kaldır" if entry["sabit"] else "Sabitle")
        delete = menu.addAction("Sil")
        selected = menu.exec(self.items.viewport().mapToGlobal(point))
        if selected == pin:
            self.backend.toggle_pin(entry["metin"])
        elif selected == delete:
            self.backend.delete(entry["metin"])
        self.refresh()

    def clear_history(self) -> None:
        if self.confirm.isActive():
            self.confirm.stop()
            self.clear.setText("Temizle")
            self.backend.clear()
            self.refresh()
        else:
            self.clear.setText("Sabitlenmemişleri sil?")
            self.confirm.start(4000)

    def eventFilter(self, watched, event) -> bool:
        if event.type() != QEvent.Type.KeyPress:
            return False
        key = event.key()
        if watched == self.search and key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            step = -1 if key == Qt.Key.Key_Up else 1
            self.items.setCurrentRow(max(0, min(self.items.count() - 1, self.items.currentRow() + step)))
            return True
        if key == Qt.Key.Key_Delete and (watched == self.items or not self.search.text()):
            if item := self.items.currentItem():
                self.backend.delete(item.data(USER_ROLE)["metin"])
                self.refresh()
            return True
        return False


class NotesPanel(QWidget):
    saved = Signal()

    def __init__(self, backend, parent: QWidget):
        super().__init__(parent)
        self.backend = backend
        self.setStyleSheet(STYLE)
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("Aklına geleni yaz…")
        self.editor.setTabChangesFocus(True)
        self.editor.installEventFilter(self)
        self.editor.setFixedHeight(65)

        self.items = QListWidget()
        self.items.installEventFilter(self)
        self.items.setStyleSheet("""
            QListWidget::indicator { width: 14px; height: 14px; border-radius: 4px;
                                      border: 1px solid #81818e; background: #1c1c23; }
            QListWidget::indicator:checked { background: #38836d; border-color: #62aa93; }
        """)
        self.items.itemActivated.connect(self.copy)
        self.items.itemChanged.connect(self.toggle_task)
        self.remove_button = QPushButton("Seçileni sil")
        self.remove_button.clicked.connect(self.delete_selected)
        self.remove_button.setEnabled(False)
        self.items.currentRowChanged.connect(lambda row: self.remove_button.setEnabled(row >= 0))
        self.hint = QLabel()
        save = QPushButton("Kaydet")
        save.clicked.connect(self.save)

        footer = QHBoxLayout()
        footer.addWidget(self.hint, 1)
        footer.addWidget(self.remove_button)
        footer.addWidget(save)
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(self.editor)
        box.addWidget(self.items, 1)
        box.addLayout(footer)

    def prepare(self) -> None:
        self.editor.setPlainText(self.backend.load_draft())
        self.editor.moveCursor(QTextCursor.MoveOperation.End)
        self.refresh()

    def take_focus(self) -> None:
        self.editor.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def store_draft(self) -> None:
        self.backend.save_draft(self.editor.toPlainText())

    def refresh(self) -> None:
        self.hint.setText("Enter kaydet · Shift+Enter yeni satır")
        selected = self.items.currentRow()
        self.notes = self.backend.read_notes(self.backend.notes_path())
        previous = self.items.blockSignals(True)
        try:
            self.items.clear()
            for index, note in enumerate(self.notes):
                row = QListWidgetItem(note.title, self.items)
                row.setData(USER_ROLE, index)
                row.setCheckState(Qt.CheckState.Checked if note.todo else Qt.CheckState.Unchecked)
                if note.todo:
                    font = row.font()
                    font.setStrikeOut(True)
                    row.setFont(font)
        finally:
            self.items.blockSignals(previous)
        self.items.setCurrentRow(min(selected, len(self.notes) - 1))
        self.remove_button.setEnabled(self.items.currentRow() >= 0)

    def save(self) -> None:
        try:
            note = self.backend.add(self.backend.notes_path(), self.editor.toPlainText())
        except (OSError, ValueError):
            self.hint.setText("Not kaydedilemedi")
            return
        if note is not None:
            self.editor.clear()
            self.saved.emit()

    def copy(self, row) -> None:
        QApplication.clipboard().setText(self.notes[row.data(USER_ROLE)].text)
        self.hint.setText("Not kopyalandı")

    def toggle_task(self, row) -> None:
        note = self.notes[row.data(USER_ROLE)]
        try:
            changed = self.backend.toggle(self.backend.notes_path(), note, include_plain=True)
        except (OSError, ValueError):
            changed = False
        self.refresh()
        if not changed:
            self.hint.setText("Not güncellenemedi")

    def delete_selected(self) -> None:
        row = self.items.currentItem()
        if row is None:
            return
        note = self.notes[row.data(USER_ROLE)]
        try:
            removed = self.backend.delete(self.backend.notes_path(), note)
        except (OSError, ValueError):
            removed = False
        self.refresh()
        self.hint.setText("Not silindi" if removed else "Not silinemedi")

    def eventFilter(self, watched, event) -> bool:
        if (watched == self.items and event.type() == QEvent.Type.KeyPress
                and event.key() == Qt.Key.Key_Delete):
            self.delete_selected()
            return True
        if (watched == self.editor and event.type() == QEvent.Type.KeyPress
                and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.save()
            return True
        return False
