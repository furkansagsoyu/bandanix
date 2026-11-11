"""Cinnamon uygulama bildirimlerini adaya ileten oturum köprüsü.

Sistem Python'uyla çalışır. Üst pencere kapanınca stdin kesilir ve Cinnamon
bildirim ayarı geri yüklenir. Bildirim içeriği diske yazılmaz.
"""
from __future__ import annotations

import fcntl
import json
import signal
import sys
from pathlib import Path

from gi.repository import Gio, GLib

SCHEMA = "org.cinnamon.desktop.notifications"
KEY = "display-notifications"
DESTINATION = "org.freedesktop.Notifications"
OBJECT = "/org/freedesktop/Notifications"
MATCH = (f"type='method_call',destination='{DESTINATION}',path='{OBJECT}',"
         f"interface='{DESTINATION}',member='Notify'")


def main() -> int:
    schema = Gio.SettingsSchemaSource.get_default().lookup(SCHEMA, True)
    if schema is None or not schema.has_key(KEY):
        return 1
    runtime = Path(GLib.get_user_runtime_dir()) / "bandanix"
    runtime.mkdir(parents=True, exist_ok=True)
    with (runtime / "notifications.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return run(Gio.Settings.new_full(schema, None, None))


def run(settings: Gio.Settings) -> int:
    loop = GLib.MainLoop()
    connection = Gio.DBusConnection.new_for_address_sync(
        Gio.dbus_address_get_for_bus_sync(Gio.BusType.SESSION, None),
        Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,
        None, None,
    )
    connection.set_exit_on_close(False)
    connection.connect("closed", lambda *_: loop.quit())

    def send(payload):
        try:
            print(json.dumps(payload, ensure_ascii=True), flush=True)
        except BrokenPipeError:
            loop.quit()
        return GLib.SOURCE_REMOVE

    def receive(_conn, message, incoming, _data):
        if not incoming or message.get_message_type() != Gio.DBusMessageType.METHOD_CALL:
            return message
        if (message.get_path() == OBJECT and message.get_interface() == DESTINATION
                and message.get_member() == "Notify" and message.get_signature() == "susssasa{sv}i"):
            body = message.get_body()
            app, summary, text = (body.get_child_value(i).get_string() for i in (0, 3, 4))
            GLib.idle_add(send, {"app": app[:120], "summary": summary[:400], "body": text[:2000]})
        # GDBus'in izlenen yöntem çağrılarına otomatik cevap vermesini önle.
        return None

    connection.add_filter(receive, None)
    connection.call_sync(
        "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus.Monitoring",
        "BecomeMonitor", GLib.Variant("(asu)", ([MATCH], 0)), None, Gio.DBusCallFlags.NONE, 3000, None,
    )

    def parent_closed(_fd, _condition):
        loop.quit()
        return GLib.SOURCE_REMOVE

    GLib.unix_fd_add_full(GLib.PRIORITY_DEFAULT, sys.stdin.fileno(),
                          GLib.IOCondition.HUP | GLib.IOCondition.ERR, parent_closed)
    def stop():
        loop.quit()
        return GLib.SOURCE_REMOVE

    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, stop)

    previous = settings.get_user_value(KEY)
    enabled = settings.get_boolean(KEY)
    if enabled and not settings.set_boolean(KEY, False):
        return 1
    try:
        Gio.Settings.sync()
        print('{"ready": true}', flush=True)
        loop.run()
    finally:
        if enabled and not settings.get_boolean(KEY):
            if previous is None:
                settings.reset(KEY)
            else:
                settings.set_value(KEY, previous)
            Gio.Settings.sync()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (GLib.Error, OSError) as error:
        print(f"Sound Island bildirim köprüsü: {error}", file=sys.stderr)
        sys.exit(1)
