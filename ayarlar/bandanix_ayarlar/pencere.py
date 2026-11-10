"""The settings window: section list on the left, the chosen section on the right,
and a status line at the bottom for longer jobs."""
from __future__ import annotations

import json

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402

from . import isler, ortam  # noqa: E402

APP_ID = "io.github.furkansagsoyu.bandanix.ayarlar"


def css(accent: str) -> bytes:
    return f"""
    .bx-baslik {{ font-size: 22px; font-weight: bold; }}
    .bx-aciklama {{ opacity: 0.7; }}
    .bx-grup-baslik {{ font-weight: bold; margin-top: 6px; }}
    .bx-liste row {{ padding: 10px 14px; }}
    .bx-kart {{ padding: 6px; border-radius: 12px; border: 2px solid transparent; background: none; }}
    .bx-kart.bx-secili {{ border-color: {accent}; }}
    .bx-kurulu {{ color: #3FBF6F; }}
    .bx-soluk {{ opacity: 0.6; }}
    .bx-durum {{ padding: 6px 12px; }}
    .bx-mono {{ font-family: monospace; }}
    """.encode()


# ---- small building blocks shared by the pages ---------------------------------------------
def label(text: str, *classes: str, wrap: bool = False, xalign: float = 0.0) -> Gtk.Label:
    lab = Gtk.Label(label=text, xalign=xalign)
    lab.set_line_wrap(wrap)
    for c in classes:
        lab.get_style_context().add_class(c)
    return lab


def row(title: str, subtitle: str, control: Gtk.Widget | None) -> Gtk.ListBoxRow:
    r = Gtk.ListBoxRow()
    r.set_activatable(False)
    box = Gtk.Box(spacing=12)
    texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    texts.pack_start(label(title), False, False, 0)
    if subtitle:
        texts.pack_start(label(subtitle, "bx-aciklama", wrap=True), False, False, 0)
    box.pack_start(texts, True, True, 0)
    if control is not None:
        control.set_valign(Gtk.Align.CENTER)
        box.pack_end(control, False, False, 0)
    r.add(box)
    return r


def group(title: str, rows: list[Gtk.ListBoxRow]) -> Gtk.Box:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    if title:
        box.pack_start(label(title, "bx-grup-baslik"), False, False, 0)
    frame = Gtk.Frame()
    lst = Gtk.ListBox()
    lst.set_selection_mode(Gtk.SelectionMode.NONE)
    lst.get_style_context().add_class("bx-liste")
    for r in rows:
        lst.add(r)
    frame.add(lst)
    box.pack_start(frame, False, False, 0)
    box.listbox = lst
    return box


def button(text: str, handler, *classes: str) -> Gtk.Button:
    b = Gtk.Button(label=text)
    for c in classes:
        b.get_style_context().add_class(c)
    b.connect("clicked", lambda *_: handler())
    return b


class Debounce:
    """Call fn once, ms after the last trigger (sliders and spin buttons fire a lot)."""

    def __init__(self, ms: int, fn):
        self.ms, self.fn, self.source = ms, fn, 0

    def __call__(self, *_):
        if self.source:
            GLib.source_remove(self.source)
        self.source = GLib.timeout_add(self.ms, self._fire)

    def _fire(self):
        self.source = 0
        self.fn()
        return False


class Page:
    """A section: its content, or a "not installed" note when its component is missing."""
    id = ""
    title = ""
    heading = ""
    description = ""
    component: str | None = None

    def __init__(self, win: "Window"):
        self.win = win
        self.loading = False
        self.stack = Gtk.Stack()
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        for side in ("top", "bottom", "start", "end"):
            getattr(content, f"set_margin_{side}")(24)
        content.pack_start(label(self.heading or self.title, "bx-baslik"), False, False, 0)
        if self.description:
            content.pack_start(label(self.description, "bx-aciklama", wrap=True), False, False, 0)
        self.build(content)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(content)
        self.stack.add_named(scroll, "icerik")
        self.stack.add_named(self.missing_box(), "yok")

    def missing_box(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        name = ortam.NAMES.get(self.component or "", self.title)
        box.pack_start(label(f"{name} kurulu değil.", "bx-grup-baslik", xalign=0.5), False, False, 0)
        box.pack_start(button("Kur", lambda: self.win.install(self.component), "suggested-action"),
                       False, False, 0)
        return box

    def refresh(self) -> None:
        ok = self.component is None or ortam.installed(self.component)
        self.stack.set_visible_child_name("icerik" if ok else "yok")
        if ok:
            self.loading = True
            try:
                self.load()
            finally:
                self.loading = False

    def build(self, box: Gtk.Box) -> None:
        pass

    def load(self) -> None:
        pass


# ---- the window ---------------------------------------------------------------------------
class Window:
    def __init__(self, app: Gtk.Application):
        from .sayfalar import PAGES
        self.win = Gtk.ApplicationWindow(application=app, title="Bandanix Ayarlar")
        self.win.set_default_size(960, 660)
        self.win.set_icon_name("bandanix-ayarlar")
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("Bandanix Ayarlar")
        header.set_subtitle("Bandana'nın masaüstü kiti")
        self.win.set_titlebar(header)

        accent = ortam.get("colors", "accent", ortam.BANDANA_RED)
        provider = Gtk.CssProvider()
        provider.load_from_data(css(accent if ortam.valid_hex(accent) else ortam.BANDANA_RED))
        Gtk.StyleContext.add_provider_for_screen(self.win.get_screen(), provider,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # update banner: shown only when GitHub has news or a part waits for reinstalling
        self.update_bar = Gtk.InfoBar()
        self.update_bar.set_message_type(Gtk.MessageType.INFO)
        self.update_bar.set_show_close_button(True)
        self.update_bar.add_button("Güncelle", Gtk.ResponseType.ACCEPT)
        self.update_text = label("", wrap=True)
        self.update_bar.get_content_area().add(self.update_text)
        self.update_bar.connect("response", self.on_update_response)
        self.update_bar.set_no_show_all(True)
        outer.pack_start(self.update_bar, False, False, 0)

        body = Gtk.Box()
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        sidebar = Gtk.StackSidebar()
        sidebar.set_stack(self.stack)
        sidebar.set_size_request(220, -1)
        body.pack_start(sidebar, False, False, 0)
        body.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)
        body.pack_start(self.stack, True, True, 0)
        outer.pack_start(body, True, True, 0)

        # status line: progress of longer jobs and short messages
        self.status = Gtk.Box(spacing=10)
        self.status.get_style_context().add_class("bx-durum")
        self.progress = Gtk.ProgressBar()
        self.progress.set_size_request(180, -1)
        self.progress.set_valign(Gtk.Align.CENTER)
        self.message = label("", "bx-aciklama")
        self.details = button("Ayrıntılar", self.show_log)
        self.status.pack_start(self.progress, False, False, 0)
        self.status.pack_start(self.message, True, True, 0)
        self.status.pack_end(self.details, False, False, 0)
        outer.pack_start(Gtk.Separator(), False, False, 0)
        outer.pack_start(self.status, False, False, 0)
        self.win.add(outer)

        self.log = ""
        self.message_source = 0
        self.jobs = isler.Jobs(self.on_progress, self.on_finish)
        self.pages = [cls(self) for cls in PAGES]
        for page in self.pages:
            self.stack.add_titled(page.stack, page.id, page.title)

        self.win.show_all()
        self.progress.hide()
        self.details.hide()
        self.refresh_all()
        GLib.idle_add(lambda: self.check_updates(fetch=True) and False)

    # ---- updates -------------------------------------------------------------------------
    def check_updates(self, fetch: bool) -> None:
        """Ask the shared helper (in the background: git fetch may take a second)."""
        script = next((p for p in (ortam.CORE / "bandanix_guncelle.py",
                                   (ortam.source() or ortam.HOME) / "core" / "bandanix_guncelle.py")
                       if p.is_file()), None)
        if script is None:
            return
        args = ["/usr/bin/python3", str(script), "durum", "--json"] + (["--fetch"] if fetch else [])
        isler.background(args, self.on_update_state)

    def on_update_state(self, ok: bool, out: str) -> None:
        try:
            st = json.loads(out) if ok else {}
        except ValueError:
            st = {}
        text = update_message(st)
        self.update_text.set_text(text)
        self.update_text.show()
        self.update_bar.set_visible(bool(text))

    def on_update_response(self, bar, response) -> None:
        bar.hide()
        if response != Gtk.ResponseType.ACCEPT:
            return
        command = f"{ortam.BIN / 'bandanix'} guncelle"
        if isler.terminal(command, on_exit=lambda: (self.refresh_all(), self.check_updates(fetch=False))):
            self.say("Güncelleme terminal penceresinde sürüyor; bitince bu pencere kendini yeniler.", 10)
        else:
            self.say("Terminal açılamadı. Komutu kendin çalıştır: " + command, 20)

    # ---- status line ---------------------------------------------------------------------
    def say(self, text: str, seconds: int = 5) -> None:
        self.message.set_text(text)
        if self.message_source:
            GLib.source_remove(self.message_source)
        self.message_source = GLib.timeout_add_seconds(seconds, self._clear_message)

    def _clear_message(self):
        self.message_source = 0
        if not self.jobs.busy:
            self.message.set_text("")
        return False

    def on_progress(self, fraction: float, text: str) -> None:
        if text:
            self.progress.show()
            self.progress.set_fraction(fraction)
            self.message.set_text(text + "…")
            self.details.hide()
        else:
            self.progress.hide()

    def on_finish(self, ok: bool, title: str, log: str) -> None:
        self.log = log
        if ok:
            self.say(f"{title}: tamamlandı.")
        else:
            self.say(f"{title}: bir adım başarısız oldu.", 30)
            self.details.show()
        self.refresh_all()

    def show_log(self) -> None:
        dialog = Gtk.Dialog(title="Ayrıntılar", transient_for=self.win, modal=True)
        dialog.add_button("Kapat", Gtk.ResponseType.CLOSE)
        dialog.set_default_size(720, 420)
        view = Gtk.TextView()
        view.set_editable(False)
        view.set_monospace(True)
        view.get_buffer().set_text(self.log[-20000:])
        scroll = Gtk.ScrolledWindow()
        scroll.add(view)
        scroll.set_vexpand(True)
        dialog.get_content_area().pack_start(scroll, True, True, 0)
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    # ---- shared actions ------------------------------------------------------------------
    def refresh_all(self) -> None:
        for page in self.pages:
            page.refresh()

    def install(self, component: str | None, remove: bool = False) -> None:
        if not component:
            return
        command = isler.in_source("./uninstall.sh" if remove else "./install.sh", component)
        if not command:
            self.say("Bandanix klasörü bulunamadı (~/bandanix). Klasörde bir kez ./install.sh çalıştır.", 10)
            return
        if isler.terminal(command, on_exit=self.refresh_all):
            self.say("İşlem terminal penceresinde sürüyor; bitince bu pencere kendini yeniler.", 10)
        else:
            self.say("Terminal açılamadı. Komutu kendin çalıştır: " + command, 20)

    def installer_steps(self, components: list[str]) -> list[tuple[str, list[str]]]:
        src = ortam.source()
        if src is None:
            return []
        return [(ortam.NAMES.get(c, c), ["bash", str(src / c / "install.sh")])
                for c in components if ortam.installed(c) and (src / c / "install.sh").is_file()]


def update_message(st: dict) -> str:
    """The banner text for a `bandanix_guncelle durum --json` answer ('' = nothing to say)."""
    parts = []
    behind = st.get("geride") or 0
    if behind and not st.get("kirli"):
        parts.append(f"GitHub'da {behind} yeni değişiklik var.")
    changed = [ortam.NAMES.get(c, c) for c in st.get("degisen", [])]
    if changed:
        parts.append(("Güncellenmeyi bekleyen parçalar: " if len(changed) > 1 else "Güncellenmeyi bekleyen parça: ")
                     + ", ".join(changed) + ".")
    elif st.get("core"):
        parts.append("Ortak araçlar güncellenmeyi bekliyor.")
    return " ".join(parts)


def run() -> int:
    app = Gtk.Application(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
    state = {"window": None}

    def activate(application):
        if state["window"] is None:
            state["window"] = Window(application)
        else:
            state["window"].win.present()

    app.connect("activate", activate)
    return app.run(None)
