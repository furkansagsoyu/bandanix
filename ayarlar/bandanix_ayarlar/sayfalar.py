"""The sections of Bandanix Ayarlar."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

from . import isler, ortam
from .pencere import Debounce, Page, button, group, label, row

BIN = ortam.BIN


def rgba(hex_value: str) -> Gdk.RGBA:
    color = Gdk.RGBA()
    color.parse(hex_value)
    return color


def to_hex(color: Gdk.RGBA) -> str:
    return "#{:02X}{:02X}{:02X}".format(*(round(max(0.0, min(1.0, c)) * 255)
                                           for c in (color.red, color.green, color.blue)))


def combo(choices: list[tuple[str, str]]) -> Gtk.ComboBoxText:
    c = Gtk.ComboBoxText()
    for cid, text in choices:
        c.append(cid, text)
    return c


def spin(lo: int, hi: int, step: int = 1) -> Gtk.SpinButton:
    s = Gtk.SpinButton.new_with_range(lo, hi, step)
    s.set_digits(0)
    return s


# ---- 1. Görünüm ---------------------------------------------------------------------------
class Gorunum(Page):
    id, title = "gorunum", "Görünüm"
    heading = "Görünüm"
    description = ("Vurgu rengi temada, ikonlarda, imleçte, panelde, adalarda ve saatte kullanılır. "
                   "Uygulamak bir dakika kadar sürer; bu sırada pencereyi kullanmaya devam edebilirsin. "
                   "Giriş ekranını da yeni renge uydurmak için Duvar kağıdı bölümündeki düğmeyi kullan.")
    STEPS = ["cinnamon-tema", "ikonlar", "panel-duzeni", "terminal", "widget", "ayarlar"]

    def build(self, box):
        self.color = Gtk.ColorButton()
        self.color.set_use_alpha(False)
        reset = button("Bandana kırmızısı", lambda: self.color.set_rgba(rgba(ortam.BANDANA_RED)))
        colors = Gtk.Box(spacing=8)
        colors.pack_start(reset, False, False, 0)
        colors.pack_start(self.color, False, False, 0)

        self.font = Gtk.FontButton()
        self.font.set_level(Gtk.FontChooserLevel.FAMILY)
        self.system_font = Gtk.CheckButton(label="Sistemin yazı tipi")
        self.system_font.connect("toggled", lambda *_: self.font.set_sensitive(not self.system_font.get_active()))
        fonts = Gtk.Box(spacing=8)
        fonts.pack_start(self.system_font, False, False, 0)
        fonts.pack_start(self.font, False, False, 0)

        box.pack_start(group("", [
            row("Vurgu rengi", "Varsayılan: bandana kırmızısı (#C8102E)", colors),
            row("Yazı tipi", "Adalarda, not kutusunda, panoda ve saatte", fonts),
        ]), False, False, 0)
        self.apply = button("Uygula", self.on_apply, "suggested-action")
        self.apply.set_halign(Gtk.Align.END)
        box.pack_start(self.apply, False, False, 0)
        self.note = label("", "bx-aciklama", wrap=True)
        box.pack_start(self.note, False, False, 0)

    def load(self):
        data = ortam.load()
        accent = ortam.get("colors", "accent", ortam.BANDANA_RED, data)
        self.color.set_rgba(rgba(accent if ortam.valid_hex(accent) else ortam.BANDANA_RED))
        font = ortam.get("fonts", "ui", "", data).strip()
        self.system_font.set_active(not font)
        self.font.set_sensitive(bool(font))
        if font:
            self.font.set_font(f"{font} 11")
        has_source = ortam.source() is not None
        self.apply.set_sensitive(has_source)
        self.note.set_text("" if has_source else
                           "Bandanix klasörü bulunamadı (~/bandanix); renk kaydedilir ama temalar yeniden üretilemez.")

    def chosen_font(self) -> str:
        if self.system_font.get_active():
            return ""
        family = self.font.get_font_family()
        if family is not None:
            return family.get_name()
        return re.sub(r"\s+\d+(\.\d+)?$", "", self.font.get_font() or "").strip()

    def on_apply(self):
        accent = to_hex(self.color.get_rgba())
        ortam.set_values("colors", {"accent": accent})
        ortam.set_values("fonts", {"ui": self.chosen_font()})
        steps = self.win.installer_steps(self.STEPS)
        self.win.jobs.run("Görünüm", steps, then=lambda ok: isler.restart_sound_island())


# ---- 2. Duvar kağıdı ----------------------------------------------------------------------
class Duvar(Page):
    id, title = "duvar", "Duvar kağıdı"
    heading = "Duvar kağıdı"
    description = "Bir resme tıkla, hemen uygulanır."
    component = "duvar-kagidi"

    def build(self, box):
        self.thumbs: dict[str, GdkPixbuf.Pixbuf] = {}
        self.flow = Gtk.FlowBox()
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_max_children_per_line(3)
        self.flow.set_min_children_per_line(2)
        self.flow.set_column_spacing(12)
        self.flow.set_row_spacing(12)
        self.flow.set_homogeneous(True)
        box.pack_start(self.flow, False, False, 0)
        self.login = button("Giriş ekranına da uygula", self.on_login)
        self.login.set_halign(Gtk.Align.START)
        box.pack_start(self.login, False, False, 0)

    def current(self) -> str:
        ok, out = isler.quick(["dconf", "read", "/org/cinnamon/desktop/background/picture-uri"])
        m = re.search(r"/backgrounds/bandanix/([a-z0-9-]+)\.\w+'?$", out.strip()) if ok else None
        return m.group(1) if m else ""

    def load(self):
        for child in self.flow.get_children():
            self.flow.remove(child)
        ok, out = isler.quick([str(BIN / "bandanix-duvar"), "_json"])
        try:
            walls = json.loads(out) if ok else []
        except ValueError:
            walls = []
        now = self.current()
        for w in walls:
            card = Gtk.Button()
            card.set_relief(Gtk.ReliefStyle.NONE)
            card.get_style_context().add_class("bx-kart")
            if w["id"] == now:
                card.get_style_context().add_class("bx-secili")
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            pix = self.thumb(w["dosya"])
            if pix is not None:
                inner.pack_start(Gtk.Image.new_from_pixbuf(pix), False, False, 0)
            inner.pack_start(label(w["ad"] + ("  ✓" if w["id"] == now else ""), xalign=0.5), False, False, 0)
            card.add(inner)
            card.connect("clicked", lambda _b, wid=w["id"], name=w["ad"]: self.choose(wid, name))
            self.flow.add(card)
        self.flow.show_all()
        self.login.set_sensitive(ortam.installed("giris-ekrani"))

    def thumb(self, path: str):
        if path not in self.thumbs:
            try:
                self.thumbs[path] = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 256, 144, True)
            except GLib.Error:
                return None
        return self.thumbs[path]

    def choose(self, wid: str, name: str):
        ok, out = isler.quick([str(BIN / "bandanix-duvar"), wid])
        self.win.say(f"Duvar kağıdı: {name}" if ok else out.splitlines()[0] if out else "Duvar kağıdı değiştirilemedi.")
        self.refresh()

    def on_login(self):
        if isler.terminal(str(BIN / "bandanix-giris") + " guncelle"):
            self.win.say("Giriş ekranı terminal penceresinde güncelleniyor (şifre ister).", 10)


# ---- 3. Panel -----------------------------------------------------------------------------
class Panel(Page):
    id, title = "panel", "Panel"
    heading = "Panel"
    description = "Değişiklikler \"Uygula\"ya basınca geçerli olur."
    component = "panel-duzeni"

    def build(self, box):
        self.layout = combo([("orta", "Orta (Windows 11 gibi)"), ("uc-ada", "Üç ada")])
        self.height = spin(40, 64)
        self.icons = spin(16, 48)
        box.pack_start(group("", [
            row("Düzen", "Ortada tek ada ve tepsi, ya da menü · pencereler · tepsi", self.layout),
            row("Panel yüksekliği", "Adalar bundan 12 piksel kısa olur", self.height),
            row("İkon boyutu", "Adalardaki uygulama ikonları", self.icons),
        ]), False, False, 0)
        apply = button("Uygula", self.on_apply, "suggested-action")
        apply.set_halign(Gtk.Align.END)
        box.pack_start(apply, False, False, 0)

    def load(self):
        data = ortam.load()
        self.layout.set_active_id(ortam.get("panel", "duzen", "orta", data))
        self.height.set_value(ortam.get("panel", "yukseklik", 54, data))
        self.icons.set_value(ortam.get("panel", "ikon_boyutu", 32, data))

    def on_apply(self):
        ortam.set_values("panel", {"duzen": self.layout.get_active_id() or "orta",
                                   "yukseklik": int(self.height.get_value()),
                                   "ikon_boyutu": int(self.icons.get_value())})
        self.win.jobs.run("Panel", self.win.installer_steps(["panel-duzeni"]))


# ---- 4. Sound Island ----------------------------------------------------------------------
class SoundIsland(Page):
    id, title = "sound-island", "Sound Island"
    heading = "Sound Island"
    description = "Değişince ada kendiliğinden yeniden başlar."
    component = "sound-island"

    def build(self, box):
        self.follow = Gtk.Switch()
        self.hide = Gtk.Switch()
        self.indicator = Gtk.Switch()
        self.bars = combo([("auto", "Gerçek ses (cava)"), ("simulated", "Temsili")])
        box.pack_start(group("", [
            row("Albüm kapağı rengi", "Vurgu rengini çalan şarkının kapağından al", self.follow),
            row("Boşta gizlen", "Çalan bir şey yokken adayı gizle", self.hide),
            row("Ses ve parlaklık göstergesi", "Kapalıysa Cinnamon'ın kendi göstergesi çıkar", self.indicator),
            row("Ses çubukları", "Gerçek ses cava ile, sadece müzik çalarken çalışır", self.bars),
        ]), False, False, 0)
        self.restart = Debounce(700, isler.restart_sound_island)
        for sw in (self.follow, self.hide, self.indicator):
            sw.connect("notify::active", self.on_change)
        self.bars.connect("changed", self.on_change)

    def load(self):
        data = ortam.load()
        self.follow.set_active(ortam.get("sound-island", "follow_cover", True, data))
        self.hide.set_active(ortam.get("sound-island", "hide_when_idle", True, data))
        self.indicator.set_active(ortam.get("sound-island", "gosterge", True, data))
        self.bars.set_active_id(ortam.get("sound-island", "bars", "auto", data))

    def on_change(self, *_):
        if self.loading:
            return
        before = ortam.get("sound-island", "gosterge", True)
        ortam.set_values("sound-island", {"follow_cover": self.follow.get_active(),
                                          "hide_when_idle": self.hide.get_active(),
                                          "gosterge": self.indicator.get_active(),
                                          "bars": self.bars.get_active_id() or "auto"})
        if before != self.indicator.get_active():
            isler.cinnamon_osd(self.indicator.get_active())
        self.restart()
        self.win.say("Sound Island ayarları kaydedildi.")


# ---- 5. Sistem adası ve saat --------------------------------------------------------------
class Sistem(Page):
    id, title = "sistem", "Sistem adası ve saat"
    heading = "Sistem adası ve saat"

    LIMITS = [("islemci", "İşlemci", "1 dakikalık ortalama, yüzde", 50, 100, 90),
              ("sicaklik", "Sıcaklık", "°C", 60, 105, 90),
              ("ram", "RAM", "Dolu yüzdesi", 50, 99, 90),
              ("disk", "Disk", "Dolu yüzdesi", 50, 99, 95)]

    def build(self, box):
        self.spins = {}
        rows = []
        for key, name, sub, lo, hi, _default in self.LIMITS:
            self.spins[key] = spin(lo, hi)
            rows.append(row(name, sub, self.spins[key]))
        self.limits_group = group("Sistem adası: ada bu sınırlar aşılınca belirir", rows)
        self.limits_missing = button("Sistem adasını kur", lambda: self.win.install("sistem-adasi"))
        save = Debounce(600, self.save_limits)
        for s in self.spins.values():
            s.connect("value-changed", lambda *_: None if self.loading else save())
        box.pack_start(self.limits_group, False, False, 0)
        box.pack_start(self.limits_missing, False, False, 0)

        self.city_now = label("", "bx-aciklama")
        self.query = Gtk.Entry()
        self.query.set_placeholder_text("Şehir adı")
        self.query.connect("activate", lambda *_: self.search())
        find = button("Ara", self.search)
        search = Gtk.Box(spacing=6)
        search.pack_start(self.query, False, False, 0)
        search.pack_start(find, False, False, 0)
        self.results = combo([])
        self.found: list[dict] = []
        pick = button("Seç", self.pick)
        choose = Gtk.Box(spacing=6)
        choose.pack_start(self.results, False, False, 0)
        choose.pack_start(pick, False, False, 0)
        self.city_group = group("Saat widget'ı: hava durumu", [
            row("Şehir", "", self.city_now),
            row("Şehir ara", "Open-Meteo'da aranır", search),
            row("Sonuçlar", "", choose),
        ])
        self.city_missing = button("Saat widget'ını kur", lambda: self.win.install("widget"))
        box.pack_start(self.city_group, False, False, 0)
        box.pack_start(self.city_missing, False, False, 0)

    def load(self):
        data = ortam.load()
        for key, *_rest, default in self.LIMITS:
            self.spins[key].set_value(ortam.get("sistem-adasi", key, default, data))
        has_sys, has_widget = ortam.installed("sistem-adasi"), ortam.installed("widget")
        self.limits_group.set_visible(has_sys)
        self.limits_missing.set_visible(not has_sys)
        self.city_group.set_visible(has_widget)
        self.city_missing.set_visible(not has_widget)
        self.city_now.set_text(ortam.get("widget", "sehir", "", data) or "ayarlı değil")

    def save_limits(self):
        ortam.set_values("sistem-adasi", {k: int(s.get_value()) for k, s in self.spins.items()})
        self.win.say("Sistem adası sınırları kaydedildi; bir sonraki ölçümde geçerli.")

    def search(self):
        text = self.query.get_text().strip()
        if not text:
            return
        self.win.say("Aranıyor…")

        def done(ok, out):
            try:
                self.found = json.loads(out) if ok else []
            except ValueError:
                self.found = []
            self.found = self.found or []
            self.results.remove_all()
            for n, place in enumerate(self.found):
                self.results.append(str(n), place["ad"])
            if self.found:
                self.results.set_active(0)
                self.win.say(f"{len(self.found)} yer bulundu; birini seçip \"Seç\"e bas.")
            else:
                self.win.say("Bulunamadı (internet bağlantısı var mı?).")

        isler.background([str(BIN / "bandanix-widget"), "_ara", text], done)

    def pick(self):
        index = self.results.get_active()
        if index < 0 or index >= len(self.found):
            return
        place = self.found[index]
        self.win.say(f"{place['ad']} için hava durumu alınıyor…")

        def done(ok, _out):
            self.win.say(f"Şehir: {place['ad']}" if ok else "Şehir kaydedildi ama hava durumu alınamadı.")
            self.refresh()

        isler.background([str(BIN / "bandanix-widget"), "_sec", place["sehir"] or place["ad"],
                          str(place["enlem"]), str(place["boylam"])], done)


# ---- 6. Pil -------------------------------------------------------------------------------
class Pil(Page):
    id, title = "pil", "Pil"
    heading = "Pil"
    component = "pil"

    def build(self, box):
        self.info = label("", "bx-mono")
        self.info.set_selectable(True)
        box.pack_start(self.info, False, False, 0)
        self.limit = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 50, 100, 5)
        self.limit.set_digits(0)
        self.limit.set_size_request(260, -1)
        for mark in (60, 80, 100):
            self.limit.add_mark(mark, Gtk.PositionType.BOTTOM, f"%{mark}")
        self.low = spin(5, 50)
        box.pack_start(group("", [
            row("Şarj sınırı", "Şarj bu yüzdede durur; %80 pilin ömrünü uzatır", self.limit),
            row("Düşük pil uyarısı", "Pil bu yüzdenin altına inince bildirim gelir", self.low),
        ]), False, False, 0)
        box.pack_start(label("Bu seferlik %100 şarj için terminalde: bandanix-pil tam", "bx-aciklama"),
                       False, False, 0)
        set_limit = Debounce(800, self.save_limit)
        save_low = Debounce(600, self.save_low)
        self.limit.connect("value-changed", lambda *_: None if self.loading else set_limit())
        self.low.connect("value-changed", lambda *_: None if self.loading else save_low())

    def load(self):
        data = ortam.load()
        self.limit.set_value(ortam.get("pil", "ust", 80, data))
        self.low.set_value(ortam.get("pil", "alt", 20, data))
        ok, out = isler.quick([str(BIN / "bandanix-pil")])
        self.info.set_text(out if out else "Pil bilgisi okunamadı.")

    def save_limit(self):
        value = int(round(self.limit.get_value() / 5) * 5)

        def done(ok, out):
            last = out.strip().splitlines()[-1] if out.strip() else ""
            self.win.say(last.lstrip("• ") if last else (f"Şarj sınırı %{value}" if ok else "Sınır değiştirilemedi."))
            self.refresh()

        isler.background([str(BIN / "bandanix-pil"), "sinir", str(value)], done)

    def save_low(self):
        ortam.set_values("pil", {"alt": int(self.low.get_value())})
        self.win.say("Düşük pil uyarısı kaydedildi.")


# ---- 7. Kısayollar ------------------------------------------------------------------------
class Kisayollar(Page):
    id, title = "kisayollar", "Kısayollar"
    heading = "Kısayollar"
    description = "\"Değiştir\"e bas, sonra yeni tuş kombinasyonuna bas."

    def build(self, box):
        self.labels: dict[str, Gtk.Label] = {}
        self.buttons: dict[str, Gtk.Button] = {}
        rows = []
        for cid, (own_id, name, _default) in ortam.SHORTCUTS.items():
            lab = label("", "bx-mono")
            change = button("Değiştir", lambda c=cid: self.capture(c))
            controls = Gtk.Box(spacing=10)
            controls.pack_start(lab, False, False, 0)
            controls.pack_start(change, False, False, 0)
            self.labels[cid], self.buttons[cid] = lab, change
            rows.append(row(name, ortam.NAMES.get(cid, cid), controls))
        box.pack_start(group("", rows), False, False, 0)

    def load(self):
        for cid, (own_id, _name, _default) in ortam.SHORTCUTS.items():
            on = ortam.installed(cid)
            self.buttons[cid].set_sensitive(on)
            self.labels[cid].set_text(ortam.pretty_accel(ortam.current_shortcut(own_id)) if on else "kurulu değil")

    def capture(self, cid: str):
        own_id, name, default = ortam.SHORTCUTS[cid]
        dialog = Gtk.Dialog(title=f"{name} kısayolu", transient_for=self.win.win, modal=True)
        dialog.add_button("Vazgeç", Gtk.ResponseType.CANCEL)
        prompt = label("Yeni kısayola bas…\n(Super, Ctrl ya da Alt ile birlikte bir tuş)", xalign=0.5)
        for side in ("top", "bottom", "start", "end"):
            getattr(prompt, f"set_margin_{side}")(24)
        dialog.get_content_area().pack_start(prompt, True, True, 0)
        kisayol = ortam.core_module("bandanix_kisayol")

        modifier_keys = {getattr(Gdk, f"KEY_{n}", -1) for n in (
            "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Super_L", "Super_R",
            "Meta_L", "Meta_R", "Hyper_L", "Hyper_R", "ISO_Level3_Shift", "Caps_Lock", "Num_Lock")}

        def on_key(_w, event):
            if event.keyval in modifier_keys:
                return True                      # wait for the real key
            state = event.state
            try:
                state = Gdk.Keymap.get_for_display(Gdk.Display.get_default()).add_virtual_modifiers(state)
            except Exception:
                pass
            mods = int(state) & (int(Gtk.accelerator_get_default_mod_mask()) | int(Gdk.ModifierType.MOD4_MASK))
            if mods & int(Gdk.ModifierType.SUPER_MASK):
                mods &= ~int(Gdk.ModifierType.MOD4_MASK)   # Super is reported twice on X11
            if event.keyval == Gdk.KEY_Escape and not mods:
                dialog.response(Gtk.ResponseType.CANCEL)
                return True
            needed = (Gdk.ModifierType.SUPER_MASK, Gdk.ModifierType.MOD4_MASK,
                      Gdk.ModifierType.CONTROL_MASK, Gdk.ModifierType.MOD1_MASK)
            if not any(mods & int(m) for m in needed):
                prompt.set_text("Super, Ctrl ya da Alt ile birlikte basmalısın.")
                return True
            accel = Gtk.accelerator_name(Gdk.keyval_to_lower(event.keyval), Gdk.ModifierType(mods))
            accel = accel.replace("<Mod4>", "<Super>")
            if kisayol is not None and kisayol.norm_accel(accel) in kisayol.bindings_in_use(own_id):
                prompt.set_text(f"{ortam.pretty_accel(accel)} başka bir işe atanmış. Başka bir tuş dene.")
                return True
            dialog.accel = accel
            dialog.response(Gtk.ResponseType.OK)
            return True

        dialog.accel = ""
        dialog.connect("key-press-event", on_key)
        dialog.show_all()
        answer = dialog.run()
        accel = dialog.accel
        dialog.destroy()
        if answer != Gtk.ResponseType.OK or not accel:
            return
        section = "not-kutusu" if cid == "not-kutusu" else "pano"
        ortam.set_values(section, {"kisayol": accel})
        if kisayol is None:
            self.win.say("Kaydedildi; geçerli olması için parçayı yeniden kur.")
            return
        command = str(BIN / ("bandanix-not" if cid == "not-kutusu" else "bandanix-pano"))
        title = "Bandanix hızlı not" if cid == "not-kutusu" else "Bandanix pano geçmişi"
        try:
            kisayol.install(own_id, title, command, accel, accel)
            self.win.say(f"{name}: {ortam.pretty_accel(accel)}")
        except (OSError, subprocess.CalledProcessError):
            self.win.say("Kısayol kaydedilemedi.")
        self.refresh()


# ---- 8. Parçalar --------------------------------------------------------------------------
class Parcalar(Page):
    id, title = "parcalar", "Parçalar"
    heading = "Parçalar"
    description = ("Kurma ve kaldırma ayrı bir terminal penceresinde çalışır, çünkü bazı parçalar şifre "
                   "ya da onay isteyebilir. Bitince bu pencere kendini yeniler.")

    def build(self, box):
        self.warning = label("", "bx-aciklama", wrap=True)
        box.pack_start(self.warning, False, False, 0)
        self.holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(self.holder, False, False, 0)

    def load(self):
        for child in self.holder.get_children():
            self.holder.remove(child)
        src = ortam.source()
        self.warning.set_visible(src is None)
        self.warning.set_text("" if src else
                              "Bandanix klasörü bulunamadı (~/bandanix). Kurma ve kaldırma için klasörü geri koy "
                              "ya da içinde bir kez ./install.sh çalıştır.")
        rows = []
        for comp in ortam.components():
            state = label("Kurulu ✓" if comp["kurulu"] else "Kurulu değil",
                          "bx-kurulu" if comp["kurulu"] else "bx-soluk")
            action = button("Kaldır" if comp["kurulu"] else "Kur",
                            lambda c=comp: self.win.install(c["id"], remove=c["kurulu"]),
                            *(() if comp["kurulu"] else ("suggested-action",)))
            action.set_sensitive(src is not None)
            controls = Gtk.Box(spacing=12)
            controls.pack_start(state, False, False, 0)
            controls.pack_start(action, False, False, 0)
            rows.append(row(comp["ad"], comp["aciklama"], controls))
        self.holder.pack_start(group("", rows), False, False, 0)
        self.holder.show_all()


# ---- 9. Yedekler --------------------------------------------------------------------------
class Yedekler(Page):
    id, title = "yedekler", "Yedekler"
    heading = "Yedekler"
    description = ("Bandanix her kurulumda masaüstü ayarlarının yedeğini alır. ★ orijinal olan, Bandanix "
                   "öncesindeki masaüstündür ve hiç silinmez. Geri yükleme terminalde neyin değişeceğini "
                   "gösterir ve onay ister.")

    def build(self, box):
        self.note = Gtk.Entry()
        self.note.set_placeholder_text("Not (isteğe bağlı)")
        take = button("Yedek al", self.take, "suggested-action")
        bar = Gtk.Box(spacing=8)
        bar.pack_start(self.note, True, True, 0)
        bar.pack_start(take, False, False, 0)
        box.pack_start(bar, False, False, 0)
        self.holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(self.holder, False, False, 0)

    def load(self):
        for child in self.holder.get_children():
            self.holder.remove(child)
        items = ortam.backups()
        if not items:
            self.holder.pack_start(label("Henüz yedek yok.", "bx-aciklama"), False, False, 0)
        else:
            rows = []
            for b in reversed(items):
                restore = button("Geri yükle", lambda no=b["no"]: self.restore(no))
                title = f"{b['no']}. {b['tarih']}  ·  {b['tur']}"
                rows.append(row(title, b["not"], restore))
            self.holder.pack_start(group("", rows), False, False, 0)
        self.holder.show_all()

    def take(self):
        note = self.note.get_text().strip() or "Bandanix Ayarlar'dan"
        self.note.set_text("")
        self.win.jobs.run("Yedek", [("yedek alınıyor", [str(BIN / "bandanix-yedek"), "al", note])])

    def restore(self, no: int):
        if isler.terminal(f"{BIN / 'bandanix-yedek'} geri-yukle {no}", on_exit=self.win.refresh_all):
            self.win.say("Geri yükleme terminal penceresinde; neyin değişeceğini gösterip onay isteyecek.", 10)


PAGES = [Gorunum, Duvar, Panel, SoundIsland, Sistem, Pil, Kisayollar, Parcalar, Yedekler]
