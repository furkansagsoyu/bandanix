"""The floating note box (GTK 3). Imported only when the box is opened."""
from __future__ import annotations

import os
import sys

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Pango  # noqa: E402

import notes  # noqa: E402

WIDTH = 520
TOP = 84            # below Sound Island
SHOWN = 5
GRACE_US = 1_000_000  # first second after opening: a lost focus is taken back, not a close
DEBUG = bool(os.environ.get("BANDANIX_NOT_DEBUG"))
HINT = "Enter kaydet · Shift+Enter yeni satır · Esc kapat"


def css(accent: str, font: str) -> bytes:
    r, g, b = (int(accent[i:i + 2], 16) for i in (1, 3, 5))
    family = f'font-family: "{font}";' if font and '"' not in font else ""
    return f"""
    window.bx-not, window.bx-not.background {{ background-color: transparent; }}
    .bx-kutu {{
        background-color: rgba(18, 18, 20, 0.92);
        border: 1px solid rgba({r}, {g}, {b}, 0.35);
        border-radius: 18px;
        padding: 14px 16px 10px 16px;
        {family}
    }}
    .bx-kutu textview, .bx-kutu textview text {{
        background-color: transparent;
        color: #EDEDED;
        caret-color: {accent};
        font-size: 15px;
    }}
    .bx-ipucu-yazi {{ color: rgba(237, 237, 237, 0.35); font-size: 15px; }}
    .bx-ayrac {{ background-color: rgba(255, 255, 255, 0.07); min-height: 1px; margin: 10px 0 6px 0; }}
    .bx-kutu list, .bx-kutu row {{ background-color: transparent; }}
    .bx-kutu row {{ border-radius: 10px; padding: 5px 8px; }}
    .bx-kutu row:hover {{ background-color: rgba(255, 255, 255, 0.05); }}
    .bx-not-yazi {{ color: #DADADA; font-size: 13px; }}
    .bx-zaman {{ color: rgba(237, 237, 237, 0.40); font-size: 12px; }}
    .bx-alt {{ color: rgba(237, 237, 237, 0.35); font-size: 11px; margin-top: 8px; }}
    .bx-alt.bx-tamam {{ color: {accent}; }}
    """.encode()


def log(msg: str) -> None:
    if DEBUG:
        print(f"[bandanix-not] {msg}", file=sys.stderr, flush=True)


class NoteBox:
    def __init__(self, app: Gtk.Application):
        self.app = app
        self.path = notes.notes_path()
        self.had_focus = False
        self.retried = False
        self.opened_at = GLib.get_monotonic_time()
        self.closing = False
        self.hint_timer = 0

        win = self.win = Gtk.ApplicationWindow(application=app)
        win.set_title("Bandanix hızlı not")
        win.set_decorated(False)
        win.set_resizable(False)
        win.set_keep_above(True)
        win.set_skip_taskbar_hint(True)
        win.set_skip_pager_hint(True)
        win.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        win.get_style_context().add_class("bx-not")
        screen = win.get_screen()
        visual = screen.get_rgba_visual()
        if visual is not None and screen.is_composited():
            win.set_visual(visual)
            win.set_app_paintable(True)

        provider = Gtk.CssProvider()
        provider.load_from_data(css(notes.accent(), notes.theme_value("fonts", "ui")))
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.get_style_context().add_class("bx-kutu")
        box.set_size_request(WIDTH, -1)
        win.add(box)

        # writing area with a placeholder on top of it
        self.view = Gtk.TextView()
        self.view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.view.set_accepts_tab(False)
        self.view.set_top_margin(4)
        self.view.set_bottom_margin(4)
        self.buffer = self.view.get_buffer()
        self.buffer.set_text(notes.load_draft())
        self.buffer.connect("changed", lambda *_: self.update_placeholder())

        self.placeholder = Gtk.Label(label="Aklına geleni yaz…", xalign=0)
        self.placeholder.get_style_context().add_class("bx-ipucu-yazi")
        self.placeholder.set_halign(Gtk.Align.START)
        self.placeholder.set_valign(Gtk.Align.START)
        self.placeholder.set_margin_top(4)
        self.placeholder.set_margin_start(2)
        overlay = Gtk.Overlay()
        overlay.add(self.view)
        overlay.add_overlay(self.placeholder)
        overlay.set_overlay_pass_through(self.placeholder, True)
        box.pack_start(overlay, False, False, 0)

        # last notes
        self.separator = Gtk.Box()
        self.separator.get_style_context().add_class("bx-ayrac")
        box.pack_start(self.separator, False, False, 0)
        self.list = Gtk.ListBox()
        self.list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list.set_activate_on_single_click(True)
        self.list.connect("row-activated", self.on_row)
        box.pack_start(self.list, False, False, 0)

        self.hint = Gtk.Label(label=HINT, xalign=0)
        self.hint.get_style_context().add_class("bx-alt")
        box.pack_start(self.hint, False, False, 0)

        win.connect("key-press-event", self.on_key)
        win.connect("focus-in-event", self.on_focus_in)
        win.connect("focus-out-event", self.on_focus_out)
        win.connect("delete-event", lambda *_: self.close() or True)

        box.show_all()
        self.fill_list()
        self.update_placeholder()
        self.place()
        win.show()
        self.view.grab_focus()
        end = self.buffer.get_end_iter()
        self.buffer.place_cursor(end)
        self.present()

    # ---- window placement and focus ------------------------------------------------------
    def place(self) -> None:
        display = Gdk.Display.get_default()
        monitor = None
        try:
            _screen, px, py = display.get_default_seat().get_pointer().get_position()
            monitor = display.get_monitor_at_point(px, py)
        except Exception:
            pass
        monitor = monitor or display.get_primary_monitor() or display.get_monitor(0)
        area = monitor.get_workarea()
        self.win.move(area.x + (area.width - WIDTH) // 2, area.y + TOP)

    def present(self) -> None:
        try:
            gi.require_version("GdkX11", "3.0")
            from gi.repository import GdkX11
            self.win.present_with_time(GdkX11.x11_get_server_time(self.win.get_window()))
        except Exception:
            self.win.present()

    def on_focus_in(self, *_):
        log("odak geldi")
        self.had_focus = True
        return False

    def on_focus_out(self, *_):
        log("odak gitti")
        if self.closing:
            return False
        if GLib.get_monotonic_time() - self.opened_at < GRACE_US:
            # right after opening the window manager may hand focus back to the
            # previous window; ask for it once more instead of disappearing
            if not self.retried:
                self.retried = True
                log("odak geri isteniyor")
                GLib.timeout_add(60, lambda: self.present() or False)
            return False
        if self.had_focus:
            # short delay: a shortcut grab or a click on our own list must not close the box
            GLib.timeout_add(250, self.close_if_inactive)
        return False

    def close_if_inactive(self):
        if not self.closing and not self.win.is_active():
            log("dışarı tıklandı, kapanıyor")
            self.close()
        return False

    # ---- list ---------------------------------------------------------------------------
    def fill_list(self) -> None:
        for child in self.list.get_children():
            self.list.remove(child)
        items = notes.read_notes(self.path)[:SHOWN]
        for note in items:
            self.list.add(self.make_row(note))
        self.list.show_all()
        self.list.set_visible(bool(items))
        self.separator.set_visible(bool(items))

    def make_row(self, note: notes.Note) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.note = note
        line = Gtk.Box(spacing=10)
        if note.todo is not None:
            check = Gtk.CheckButton()
            check.set_active(note.todo)
            check.set_valign(Gtk.Align.CENTER)
            check.connect("toggled", self.on_check, note)
            line.pack_start(check, False, False, 0)
        text = Gtk.Label(xalign=0)
        title = GLib.markup_escape_text(note.title or " ")
        text.set_markup(f"<s>{title}</s>" if note.todo else title)
        text.set_ellipsize(Pango.EllipsizeMode.END)
        text.set_max_width_chars(48)
        text.get_style_context().add_class("bx-not-yazi")
        if note.todo:
            text.set_opacity(0.5)
        line.pack_start(text, True, True, 0)
        when = Gtk.Label(label=notes.ago(note.when))
        when.get_style_context().add_class("bx-zaman")
        line.pack_end(when, False, False, 0)
        row.add(line)
        row.set_tooltip_text(note.text if "\n" in note.text or len(note.text) > 48 else None)
        return row

    def on_row(self, _list, row) -> None:
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(row.note.text, -1)
        clipboard.store()
        self.flash("Kopyalandı ✓")

    def on_check(self, _button, note) -> None:
        if notes.toggle(self.path, note):
            GLib.idle_add(self.refresh)
        else:
            self.flash("Not dosyada değişmiş, liste yenilendi")
            GLib.idle_add(self.refresh)

    def refresh(self):
        self.fill_list()
        return False

    def flash(self, text: str) -> None:
        self.hint.set_text(text)
        self.hint.get_style_context().add_class("bx-tamam")
        if self.hint_timer:
            GLib.source_remove(self.hint_timer)
        self.hint_timer = GLib.timeout_add(1400, self.reset_hint)

    def reset_hint(self):
        self.hint.set_text(HINT)
        self.hint.get_style_context().remove_class("bx-tamam")
        self.hint_timer = 0
        return False

    # ---- writing ------------------------------------------------------------------------
    def text(self) -> str:
        start, end = self.buffer.get_bounds()
        return self.buffer.get_text(start, end, False)

    def update_placeholder(self) -> None:
        self.placeholder.set_visible(self.buffer.get_char_count() == 0)

    def on_key(self, _win, event) -> bool:
        key = event.keyval
        if key == Gdk.KEY_Escape:
            self.close()
            return True
        if (key in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and self.view.has_focus()
                and not event.state & Gdk.ModifierType.SHIFT_MASK):
            text = self.text()
            if text.strip():
                notes.add(self.path, text)
                self.buffer.set_text("")
            self.close()
            return True
        return False

    def close(self) -> None:
        if self.closing:
            return
        self.closing = True
        notes.save_draft(self.text())
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).store()
        self.win.destroy()


def run(app_id: str) -> int:
    app = Gtk.Application(application_id=app_id, flags=Gio.ApplicationFlags.FLAGS_NONE)
    state = {"box": None}

    def activate(application):
        box = state["box"]
        if box is not None and not box.closing:
            log("kısayola tekrar basıldı, kapanıyor")
            box.close()                 # second Super+N closes the box
            return
        log("açılıyor")
        state["box"] = NoteBox(application)

    app.connect("activate", activate)
    return app.run(None)
