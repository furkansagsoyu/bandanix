"""The clipboard history list (GTK 3). Imported only when the list is opened."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Pango  # noqa: E402

import pano_gecmis as pano  # noqa: E402

WIDTH = 560
TOP = 84                   # below Sound Island
LIST_HEIGHT = 380
GRACE_US = 1_000_000
CONFIRM_MS = 4000
DEBUG = bool(os.environ.get("BANDANIX_PANO_DEBUG"))
HINT = "↑↓ seç · Enter yapıştır · Del sil · Esc kapat"


def log(msg: str) -> None:
    if DEBUG:
        print(f"[bandanix-pano] {msg}", file=sys.stderr, flush=True)


def theme_look() -> tuple[str, str]:
    try:
        import tomllib
        data = tomllib.loads(pano.THEME.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    colors = data.get("colors") if isinstance(data.get("colors"), dict) else {}
    fonts = data.get("fonts") if isinstance(data.get("fonts"), dict) else {}
    accent = colors.get("accent") if isinstance(colors.get("accent"), str) else ""
    font = fonts.get("ui") if isinstance(fonts.get("ui"), str) else ""
    return (accent if re.fullmatch(r"#[0-9A-Fa-f]{6}", accent) else "#C8102E"), font.strip()


def css(accent: str, font: str) -> bytes:
    r, g, b = (int(accent[i:i + 2], 16) for i in (1, 3, 5))
    family = f'font-family: "{font}";' if font and '"' not in font else ""
    return f"""
    window.bx-pano, window.bx-pano.background {{ background-color: transparent; }}
    .bx-kutu {{
        background-color: rgba(18, 18, 20, 0.92);
        border: 1px solid rgba({r}, {g}, {b}, 0.35);
        border-radius: 18px;
        padding: 12px 12px 8px 12px;
        {family}
    }}
    .bx-kutu entry {{
        background-color: rgba(255, 255, 255, 0.06);
        color: #EDEDED;
        caret-color: {accent};
        border: none;
        border-radius: 10px;
        box-shadow: none;
        padding: 6px 10px;
        font-size: 15px;
        margin-bottom: 8px;
    }}
    .bx-kutu scrolledwindow, .bx-kutu viewport, .bx-kutu list, .bx-kutu row {{
        background-color: transparent;
        border: none;
    }}
    .bx-kutu row {{ border-radius: 10px; padding: 4px 8px; }}
    .bx-kutu row:hover {{ background-color: rgba(255, 255, 255, 0.05); }}
    .bx-kutu row:selected {{ background-color: rgba({r}, {g}, {b}, 0.28); }}
    .bx-metin {{ color: #E2E2E6; font-size: 13px; }}
    .bx-igne {{ font-size: 11px; }}
    .bx-zaman {{ color: rgba(237, 237, 237, 0.40); font-size: 11px; }}
    .bx-dugme {{
        background: none; border: none; box-shadow: none;
        color: rgba(237, 237, 237, 0.55); padding: 0 6px; min-height: 0; min-width: 0;
        opacity: 0;
    }}
    .bx-kutu row:hover .bx-dugme, .bx-kutu row:selected .bx-dugme {{ opacity: 1; }}
    .bx-dugme:hover {{ color: #FFFFFF; }}
    .bx-bos {{ color: rgba(237, 237, 237, 0.40); font-size: 13px; padding: 16px; }}
    .bx-alt {{ color: rgba(237, 237, 237, 0.35); font-size: 11px; }}
    .bx-temizle {{
        background: none; border: none; box-shadow: none; padding: 2px 8px;
        color: rgba(237, 237, 237, 0.45); font-size: 11px; min-height: 0;
    }}
    .bx-temizle:hover {{ color: #FFFFFF; }}
    .bx-temizle.bx-uyari {{ color: #FFFFFF; background-color: {accent}; border-radius: 8px; }}
    .bx-ayrac {{ background-color: rgba(255, 255, 255, 0.07); min-height: 1px; margin: 6px 0; }}
    """.encode()


def active_window_class() -> str:
    """WM_CLASS of the window that had focus before the list opened."""
    try:
        root = subprocess.run(["xprop", "-root", "_NET_ACTIVE_WINDOW"], capture_output=True,
                              text=True, timeout=2).stdout
        m = re.search(r"(0x[0-9a-fA-F]+)", root)
        if not m or int(m.group(1), 16) == 0:
            return ""
        out = subprocess.run(["xprop", "-id", m.group(1), "WM_CLASS"], capture_output=True,
                             text=True, timeout=2).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""
    names = re.findall(r'"([^"]*)"', out)
    return next((n for n in names if n.lower() in pano.TERMINALS), names[0] if names else "")


class Row(Gtk.ListBoxRow):
    def __init__(self, item: dict, box: "ClipBox", now: float):
        super().__init__()
        self.item = item
        line = Gtk.Box(spacing=8)
        if item["sabit"]:
            pin = Gtk.Label(label="📌")
            pin.get_style_context().add_class("bx-igne")
            line.pack_start(pin, False, False, 0)
        text = Gtk.Label(label=pano.title(item["metin"]), xalign=0)
        text.set_ellipsize(Pango.EllipsizeMode.END)
        text.set_max_width_chars(60)
        text.get_style_context().add_class("bx-metin")
        line.pack_start(text, True, True, 0)
        if len(item["metin"]) > 60 or "\n" in item["metin"].strip():
            self.set_tooltip_text(item["metin"][:600])
        delete = self.button("✕", "Sil", lambda *_: box.delete(item["metin"]))
        pin_b = self.button("📌", "Sabitlemeyi kaldır" if item["sabit"] else "Sabitle",
                            lambda *_: box.toggle_pin(item["metin"]))
        line.pack_end(delete, False, False, 0)
        line.pack_end(pin_b, False, False, 0)
        when = Gtk.Label(label=pano.ago(item["zaman"], now))
        when.get_style_context().add_class("bx-zaman")
        line.pack_end(when, False, False, 4)
        self.add(line)

    @staticmethod
    def button(label: str, tip: str, handler) -> Gtk.Button:
        b = Gtk.Button(label=label)
        b.set_relief(Gtk.ReliefStyle.NONE)
        b.set_can_focus(False)
        b.set_tooltip_text(tip)
        b.get_style_context().add_class("bx-dugme")
        b.connect("clicked", handler)
        return b


class ClipBox:
    def __init__(self, app: Gtk.Application):
        self.app = app
        self.target_class = active_window_class()        # before we take the focus
        log(f"önceki pencere: {self.target_class or '?'}")
        self.had_focus = False
        self.retried = False
        self.closing = False
        self.confirm_timer = 0
        self.opened_at = GLib.get_monotonic_time()

        win = self.win = Gtk.ApplicationWindow(application=app)
        win.set_title("Bandanix pano geçmişi")
        win.set_decorated(False)
        win.set_resizable(False)
        win.set_keep_above(True)
        win.set_skip_taskbar_hint(True)
        win.set_skip_pager_hint(True)
        win.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        win.get_style_context().add_class("bx-pano")
        screen = win.get_screen()
        visual = screen.get_rgba_visual()
        if visual is not None and screen.is_composited():
            win.set_visual(visual)
            win.set_app_paintable(True)
        provider = Gtk.CssProvider()
        provider.load_from_data(css(*theme_look()))
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.get_style_context().add_class("bx-kutu")
        box.set_size_request(WIDTH, -1)
        win.add(box)

        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Ara…")
        self.entry.connect("changed", lambda *_: self.refilter())
        box.pack_start(self.entry, False, False, 0)

        self.list = Gtk.ListBox()
        self.list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list.set_activate_on_single_click(True)
        self.list.set_filter_func(self.filter)
        self.list.connect("row-activated", lambda _l, row: self.paste(row.item["metin"]))
        self.empty = Gtk.Label(label="")
        self.empty.get_style_context().add_class("bx-bos")
        self.list.set_placeholder(self.empty)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(LIST_HEIGHT)
        scroll.set_propagate_natural_height(True)
        scroll.add(self.list)
        self.scroll = scroll
        box.pack_start(scroll, True, True, 0)

        sep = Gtk.Box()
        sep.get_style_context().add_class("bx-ayrac")
        box.pack_start(sep, False, False, 0)
        bottom = Gtk.Box(spacing=8)
        hint = Gtk.Label(label=HINT, xalign=0)
        hint.get_style_context().add_class("bx-alt")
        bottom.pack_start(hint, True, True, 0)
        self.clear_button = Gtk.Button(label="Geçmişi temizle")
        self.clear_button.set_relief(Gtk.ReliefStyle.NONE)
        self.clear_button.set_can_focus(False)
        self.clear_button.get_style_context().add_class("bx-temizle")
        self.clear_button.connect("clicked", self.on_clear)
        bottom.pack_end(self.clear_button, False, False, 0)
        box.pack_start(bottom, False, False, 0)

        win.connect("key-press-event", self.on_key)
        win.connect("focus-in-event", self.on_focus_in)
        win.connect("focus-out-event", self.on_focus_out)
        win.connect("delete-event", lambda *_: self.close() or True)

        box.show_all()
        self.fill()
        self.place()
        win.show()
        self.entry.grab_focus()
        self.present()

    # ---- placement and focus (same rules as the note box) --------------------------------
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
            if not self.retried:
                self.retried = True
                GLib.timeout_add(60, lambda: self.present() or False)
            return False
        if self.had_focus:
            GLib.timeout_add(250, self.close_if_inactive)
        return False

    def close_if_inactive(self):
        if not self.closing and not self.win.is_active():
            log("dışarı tıklandı, kapanıyor")
            self.close()
        return False

    # ---- list ---------------------------------------------------------------------------
    def fill(self) -> None:
        for child in self.list.get_children():
            self.list.remove(child)
        now = time.time()
        data = pano.items()
        for item in data:
            self.list.add(Row(item, self, now))
        self.list.show_all()
        self.empty.set_text("Pano geçmişi boş. Bir şey kopyaladığında burada görünür." if not data
                            else "Eşleşen yok.")
        self.empty.show()
        self.select_first()

    def filter(self, row) -> bool:
        query = self.entry.get_text().strip()
        return not query or pano.matches(row.item["metin"], query)

    def refilter(self) -> None:
        self.list.invalidate_filter()
        self.select_first()

    def visible_rows(self) -> list:
        return [r for r in self.list.get_children() if r.get_child_visible()]

    def select_first(self) -> None:
        rows = self.visible_rows()
        if rows:
            self.list.select_row(rows[0])
        else:
            self.list.unselect_all()

    def move(self, step: int) -> None:
        rows = self.visible_rows()
        if not rows:
            return
        current = self.list.get_selected_row()
        index = rows.index(current) + step if current in rows else 0
        row = rows[max(0, min(len(rows) - 1, index))]
        self.list.select_row(row)
        adj = self.scroll.get_vadjustment()
        alloc = row.get_allocation()
        if adj is not None and alloc.height > 0:
            if alloc.y < adj.get_value():
                adj.set_value(alloc.y)
            elif alloc.y + alloc.height > adj.get_value() + adj.get_page_size():
                adj.set_value(alloc.y + alloc.height - adj.get_page_size())

    def delete(self, text: str) -> None:
        pano.delete(text)
        self.fill()
        self.refilter()

    def toggle_pin(self, text: str) -> None:
        pano.toggle_pin(text)
        self.fill()
        self.refilter()

    def on_clear(self, *_):
        ctx = self.clear_button.get_style_context()
        if not ctx.has_class("bx-uyari"):
            ctx.add_class("bx-uyari")
            self.clear_button.set_label("Emin misin? Sabitlenenler kalır")
            self.confirm_timer = GLib.timeout_add(CONFIRM_MS, self.reset_clear)
            return
        if self.confirm_timer:
            GLib.source_remove(self.confirm_timer)
        self.reset_clear()
        pano.clear()
        self.fill()

    def reset_clear(self):
        self.clear_button.get_style_context().remove_class("bx-uyari")
        self.clear_button.set_label("Geçmişi temizle")
        self.confirm_timer = 0
        return False

    # ---- keys and pasting ---------------------------------------------------------------
    def on_key(self, _win, event) -> bool:
        key = event.keyval
        if key == Gdk.KEY_Escape:
            self.close()
            return True
        if key == Gdk.KEY_Down:
            self.move(1)
            return True
        if key == Gdk.KEY_Up:
            self.move(-1)
            return True
        if key in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            row = self.list.get_selected_row()
            if row is not None and row.get_child_visible():
                self.paste(row.item["metin"])
            return True
        if key == Gdk.KEY_Delete and not self.entry.get_text():
            row = self.list.get_selected_row()
            if row is not None:
                self.delete(row.item["metin"])
            return True
        return False

    def paste(self, text: str) -> None:
        if self.closing:
            return
        self.closing = True
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        clipboard.store()
        self.win.hide()
        keys = pano.paste_keys(self.target_class)
        log(f"yapıştırılıyor: {keys}")
        # give the previous window its focus back, press the keys, and stay alive long
        # enough to hand the text over in case no clipboard manager took it
        GLib.timeout_add(150, self.press, keys)

    def press(self, keys: str):
        if shutil.which("xdotool"):
            try:
                subprocess.run(["xdotool", "key", "--clearmodifiers", keys], timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                pass
        GLib.timeout_add(600, self.finish)
        return False

    def finish(self):
        self.win.destroy()
        return False

    def close(self) -> None:
        if self.closing and not self.win.get_visible():
            return
        self.closing = True
        self.win.destroy()


def run(app_id: str) -> int:
    app = Gtk.Application(application_id=app_id, flags=Gio.ApplicationFlags.FLAGS_NONE)
    state = {"box": None}

    def activate(application):
        box = state["box"]
        if box is not None and not box.closing:
            box.close()                 # second Super+V closes the list
            return
        state["box"] = ClipBox(application)

    app.connect("activate", activate)
    return app.run(None)
