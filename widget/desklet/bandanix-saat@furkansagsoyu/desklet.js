// Bandanix Saat: big clock, Turkish date and one line of weather + system info.
// Weather comes from ~/.cache/bandanix/hava.json (written by bandanix-widget every 30 min);
// CPU, RAM and temperature are read straight from /proc and /sys every 5 seconds.

const Desklet = imports.ui.desklet;
const St = imports.gi.St;
const GLib = imports.gi.GLib;
const Gio = imports.gi.Gio;
const Clutter = imports.gi.Clutter;

const MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
                "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
const DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"];
const WEATHER_FILE = GLib.build_filenamev([GLib.get_user_cache_dir(), "bandanix", "hava.json"]);
const SEP = "   ·   ";
const STALE_SECONDS = 2 * 60 * 60;

function readText(path) {
    try {
        let [ok, bytes] = GLib.file_get_contents(path);
        return ok ? new TextDecoder("utf-8").decode(bytes) : null;
    } catch (e) {
        return null;
    }
}

function pad(n) {
    return n < 10 ? "0" + n : "" + n;
}

function cpuTimes() {
    let text = readText("/proc/stat");
    if (!text)
        return null;
    let nums = text.split("\n")[0].trim().split(/\s+/).slice(1, 9).map(Number);
    if (nums.length < 4 || nums.some(isNaN))
        return null;
    let idle = nums[3] + (nums[4] || 0);
    let total = nums.reduce((a, b) => a + b, 0);
    return [total - idle, total];
}

function ramPercent() {
    let text = readText("/proc/meminfo");
    if (!text)
        return null;
    let total = /MemTotal:\s+(\d+)/.exec(text), avail = /MemAvailable:\s+(\d+)/.exec(text);
    if (!total || !avail)
        return null;
    return (1 - Number(avail[1]) / Number(total[1])) * 100;
}

function findSensors() {
    // hottest CPU sensor: Intel package / AMD Tctl first, then ACPI, then thermal zones
    let preferred = ["coretemp", "k10temp", "zenpower", "cpu_thermal", "acpitz"];
    let found = {};
    for (let i = 0; i < 16; i++) {
        let dir = "/sys/class/hwmon/hwmon" + i;
        let name = readText(dir + "/name");
        if (name === null)
            continue;
        name = name.trim();
        if (preferred.indexOf(name) < 0)
            continue;
        let inputs = [];
        for (let j = 1; j <= 32; j++) {
            let p = dir + "/temp" + j + "_input";
            if (GLib.file_test(p, GLib.FileTest.EXISTS))
                inputs.push(p);
        }
        if (inputs.length)
            found[name] = inputs;
    }
    for (let name of preferred)
        if (found[name])
            return found[name];
    let zones = [];
    for (let i = 0; i < 10; i++) {
        let p = "/sys/class/thermal/thermal_zone" + i + "/temp";
        if (GLib.file_test(p, GLib.FileTest.EXISTS))
            zones.push(p);
    }
    return zones;
}

function temperature(paths) {
    let best = null;
    for (let p of paths) {
        let v = Number((readText(p) || "").trim()) / 1000;
        if (v > 0 && v < 150 && (best === null || v > best))
            best = v;
    }
    return best;
}

function diskPercent(path) {
    try {
        let info = Gio.File.new_for_path(path).query_filesystem_info("filesystem::size,filesystem::free", null);
        let size = info.get_attribute_uint64("filesystem::size");
        let free = info.get_attribute_uint64("filesystem::free");
        return size > 0 ? (size - free) / size * 100 : null;
    } catch (e) {
        return null;
    }
}

class BandanixSaat extends Desklet.Desklet {
    constructor(metadata, deskletId) {
        super(metadata, deskletId);
        this._bx_sources = [];
        this._bx_clockSource = 0;
        this._bx_sensors = findSensors();
        this._bx_lastCpu = null;
        this._bx_cpu = null;
        this._bx_ram = null;
        this._bx_temp = null;
        this._bx_weather = null;
        this._bx_build();
        this._bx_tickClock();
        this._bx_tickSystem();
        this._bx_loadWeather();
        this._bx_every(5, () => this._bx_tickSystem());
        this._bx_every(60, () => this._bx_loadWeather());
    }

    _bx_build() {
        this._bx_box = new St.BoxLayout({ vertical: true, style_class: "bx-saat-kutu" });
        this._bx_clock = new St.Label({ style_class: "bx-saat", x_expand: true, x_align: Clutter.ActorAlign.CENTER });
        this._bx_date = new St.Label({ style_class: "bx-tarih", x_expand: true, x_align: Clutter.ActorAlign.CENTER });

        this._bx_line = new St.BoxLayout({ style_class: "bx-satir", reactive: true, track_hover: true,
                                        x_expand: true, x_align: Clutter.ActorAlign.CENTER });
        this._bx_icon = new St.Icon({ icon_name: "weather-overcast-symbolic", icon_size: 20,
                                   style_class: "bx-ikon", y_align: Clutter.ActorAlign.CENTER });
        this._bx_info = new St.Label({ style_class: "bx-bilgi", y_align: Clutter.ActorAlign.CENTER });
        this._bx_line.add_child(this._bx_icon);
        this._bx_line.add_child(this._bx_info);

        this._bx_detail = new St.BoxLayout({ vertical: true, style_class: "bx-detay",
                                          x_expand: true, x_align: Clutter.ActorAlign.CENTER });
        this._bx_detail.hide();
        this._bx_line.connect("notify::hover", () => {
            if (this._bx_line.hover) {
                this._bx_fillDetail();
                this._bx_detail.show();
            } else {
                this._bx_detail.hide();
            }
        });

        this._bx_box.add_child(this._bx_clock);
        this._bx_box.add_child(this._bx_date);
        this._bx_box.add_child(this._bx_line);
        this._bx_box.add_child(this._bx_detail);
        this.setContent(this._bx_box);
    }

    _bx_every(seconds, fn) {
        let id = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, seconds, () => {
            fn();
            return GLib.SOURCE_CONTINUE;
        });
        this._bx_sources.push(id);
    }

    // ---- clock: redrawn at every minute change (and every 5 s, in case of sleep) ----
    _bx_showClock() {
        let now = GLib.DateTime.new_now_local();
        this._bx_clock.set_text(pad(now.get_hour()) + ":" + pad(now.get_minute()));
        this._bx_date.set_text(now.get_day_of_month() + " " + MONTHS[now.get_month() - 1] + " "
                            + DAYS[now.get_day_of_week() - 1]);
        return now;
    }

    _bx_tickClock() {
        let now = this._bx_showClock();
        let wait = (60 - now.get_second()) * 1000 + 50;
        this._bx_clockSource = GLib.timeout_add(GLib.PRIORITY_DEFAULT, wait, () => {
            this._bx_clockSource = 0;
            this._bx_tickClock();
            return GLib.SOURCE_REMOVE;
        });
    }

    // ---- system ----
    _bx_tickSystem() {
        this._bx_showClock();
        let times = cpuTimes();
        if (times && this._bx_lastCpu && times[1] > this._bx_lastCpu[1])
            this._bx_cpu = (times[0] - this._bx_lastCpu[0]) / (times[1] - this._bx_lastCpu[1]) * 100;
        this._bx_lastCpu = times;
        this._bx_ram = ramPercent();
        this._bx_temp = temperature(this._bx_sensors);
        this._bx_render();
    }

    // ---- weather ----
    _bx_loadWeather() {
        let text = readText(WEATHER_FILE);
        try {
            this._bx_weather = text ? JSON.parse(text) : null;
        } catch (e) {
            this._bx_weather = null;
        }
        this._bx_render();
    }

    _bx_weatherStale() {
        let w = this._bx_weather;
        if (!w || !w.guncellendi)
            return true;
        return Date.now() / 1000 - w.guncellendi > STALE_SECONDS;
    }

    _bx_render() {
        let parts = [];
        let w = this._bx_weather;
        let now = w && w.simdi;
        if (now && now.sicaklik !== null && now.sicaklik !== undefined) {
            parts.push(now.sicaklik + "°C " + (now.yazi || ""));
            this._bx_icon.icon_name = now.ikon || "weather-overcast-symbolic";
            this._bx_icon.show();
        } else {
            parts.push("Hava durumu bekleniyor");
            this._bx_icon.hide();
        }
        if (w && w.gunler && w.gunler.length)
            parts.push("Yarın " + w.gunler[0].en_yuksek + "° / " + w.gunler[0].en_dusuk + "°");
        if (this._bx_cpu !== null)
            parts.push("İşlemci %" + Math.round(this._bx_cpu));
        if (this._bx_ram !== null)
            parts.push("RAM %" + Math.round(this._bx_ram));
        if (this._bx_temp !== null)
            parts.push(Math.round(this._bx_temp) + "°C");
        if (w && w.simdi && this._bx_weatherStale())
            parts.push("güncellenemedi");
        this._bx_info.set_text(parts.join(SEP));
    }

    _bx_fillDetail() {
        this._bx_detail.destroy_all_children();
        let w = this._bx_weather;
        for (let d of (w && w.gunler) || []) {
            let row = new St.BoxLayout({ style_class: "bx-detay-satir" });
            row.add_child(new St.Label({ text: d.gun, style_class: "bx-gun", y_align: Clutter.ActorAlign.CENTER }));
            row.add_child(new St.Icon({ icon_name: d.ikon, icon_size: 18, style_class: "bx-ikon",
                                        y_align: Clutter.ActorAlign.CENTER }));
            row.add_child(new St.Label({ text: d.en_yuksek + "° / " + d.en_dusuk + "°", style_class: "bx-derece",
                                         y_align: Clutter.ActorAlign.CENTER }));
            row.add_child(new St.Label({ text: d.yazi, style_class: "bx-soluk", y_align: Clutter.ActorAlign.CENTER }));
            this._bx_detail.add_child(row);
        }
        let extra = [];
        let disk = diskPercent("/");
        if (disk !== null)
            extra.push("Disk %" + Math.round(disk));
        if (w && w.sehir)
            extra.push(w.sehir);
        if (w && w.guncellendi) {
            let t = GLib.DateTime.new_from_unix_local(Math.floor(w.guncellendi));
            extra.push(pad(t.get_hour()) + ":" + pad(t.get_minute()) + "'de güncellendi");
        }
        if (w && w.hata)
            extra.push("son deneme başarısız");
        this._bx_detail.add_child(new St.Label({ text: extra.join(SEP), style_class: "bx-soluk" }));
    }

    on_desklet_removed() {
        for (let id of this._bx_sources)
            GLib.source_remove(id);
        this._bx_sources = [];
        if (this._bx_clockSource) {
            GLib.source_remove(this._bx_clockSource);
            this._bx_clockSource = 0;
        }
    }
}

function main(metadata, deskletId) {
    return new BandanixSaat(metadata, deskletId);
}
