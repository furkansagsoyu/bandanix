import unittest

from sound_island.parsing import (SEP, fmt_time, line_at, parse_cava_frame,
                                  parse_lrc, parse_metadata_line,
                                  parse_poll_line, pick_search_result)


def follow_line(*fields):
    return SEP.join(fields) + "\n"


class MetadataTests(unittest.TestCase):
    def test_spotify_line(self):
        status, track = parse_metadata_line(follow_line(
            "Playing", "Uyku", "Son Feci Bisiklet", "Sistemik",
            "https://i.scdn.co/image/abc", "264960000",
            "/com/spotify/track/11IvpUALm0Canz1N6JBGEJ"))
        self.assertEqual(status, "Playing")
        self.assertEqual(track.title, "Uyku")
        self.assertEqual(track.artist, "Son Feci Bisiklet")
        self.assertAlmostEqual(track.length, 264.96)
        self.assertEqual(track.track_id, "/com/spotify/track/11IvpUALm0Canz1N6JBGEJ")

    def test_empty_line_means_no_player(self):
        self.assertEqual(parse_metadata_line("\n"), ("", None))

    def test_missing_title_means_nothing_playing(self):
        status, track = parse_metadata_line(follow_line("Stopped", "", "", "", "", "", ""))
        self.assertEqual(status, "Stopped")
        self.assertIsNone(track)

    def test_missing_trackid_gets_fallback_id(self):
        _, track = parse_metadata_line(follow_line("Paused", "Song", "Band", "", "", "", ""))
        self.assertEqual(track.track_id, "Band::Song")
        self.assertEqual(track.length, 0.0)

    def test_poll_line(self):
        self.assertEqual(parse_poll_line("Playing" + SEP + "207500000\n"), ("Playing", 207.5))
        self.assertEqual(parse_poll_line("garbage"), ("", None))


class LyricsTests(unittest.TestCase):
    LRC = "[00:12.50] Birinci satır\n[00:20.00][01:05.00] Nakarat\nno stamp here\n[00:30.1] Üçüncü"

    def test_parse_sorted_and_repeated_stamps(self):
        lines = parse_lrc(self.LRC)
        self.assertEqual([t for t, _ in lines], [12.5, 20.0, 30.1, 65.0])
        self.assertEqual(lines[-1][1], "Nakarat")

    def test_line_at(self):
        lines = parse_lrc(self.LRC)
        times = [t for t, _ in lines]
        self.assertEqual(line_at(times, lines, 5), "")
        self.assertEqual(line_at(times, lines, 12.5), "Birinci satır")
        self.assertEqual(line_at(times, lines, 25), "Nakarat")
        self.assertEqual(line_at(times, lines, 31), "Üçüncü")
        self.assertEqual(line_at([], [], 10), "")

    def test_pick_search_result_prefers_matching_duration(self):
        items = [
            {"duration": 200, "syncedLyrics": "[00:01.00] wrong"},
            {"duration": 265, "syncedLyrics": "[00:01.00] right"},
            {"duration": 265, "syncedLyrics": None},
        ]
        self.assertEqual(pick_search_result(items, 264.96)["syncedLyrics"], "[00:01.00] right")
        self.assertIsNone(pick_search_result(items[:1], 264.96))
        self.assertIsNone(pick_search_result({"error": 1}, 100))


class CavaTests(unittest.TestCase):
    def test_frame(self):
        self.assertEqual(parse_cava_frame("0;50;100;25;10;\n", 5), [0.0, 0.5, 1.0, 0.25, 0.1])

    def test_garbage(self):
        self.assertIsNone(parse_cava_frame("a;b;c;d;e;", 5))
        self.assertIsNone(parse_cava_frame("", 5))

    def test_other_bar_counts_are_resampled(self):
        six = parse_cava_frame("10;20;30;40;50;60;", 5)
        self.assertEqual(len(six), 5)
        self.assertEqual((six[0], six[-1]), (0.1, 0.6))   # both ends kept
        self.assertEqual(parse_cava_frame("10;90;", 5), [0.1, 0.1, 0.9, 0.9, 0.9])
        self.assertEqual(parse_cava_frame("10;90;", 1), [0.9])

    def test_clamped(self):
        self.assertEqual(parse_cava_frame("150;0;0;0;0;", 5)[0], 1.0)


class FormatTests(unittest.TestCase):
    def test_fmt_time(self):
        self.assertEqual(fmt_time(207.9), "3:27")
        self.assertEqual(fmt_time(-3), "0:00")


if __name__ == "__main__":
    unittest.main()


class LevelParsing(unittest.TestCase):
    def test_volume_events(self):
        from sound_island.parsing import is_volume_event
        self.assertTrue(is_volume_event("Event 'change' on sink #48"))
        self.assertTrue(is_volume_event("Event 'change' on server #4294967295"))
        self.assertFalse(is_volume_event("Event 'change' on sink-input #112"))
        self.assertFalse(is_volume_event("Event 'new' on sink #48"))
        self.assertFalse(is_volume_event("Event 'change' on source #2"))

    def test_volume(self):
        from sound_island.parsing import parse_volume
        text = ("Volume: front-left: 26214 /  40% / -23.88 dB,   front-right: 27525 /  42% / -22.6 dB\n"
                "        balance 0.05\nMute: no\n")
        self.assertEqual(parse_volume(text), (42, False))
        self.assertEqual(parse_volume("Volume: mono: 78643 / 120% / 4.75 dB\nMute: yes\n"), (120, True))
        self.assertIsNone(parse_volume("Failed to get sink volume"))

    def test_brightness(self):
        from sound_island.parsing import parse_brightness
        line = ("/org/cinnamon/SettingsDaemon/Power: org.freedesktop.DBus.Properties.PropertiesChanged "
                "('org.cinnamon.SettingsDaemon.Power.Screen', {'Brightness': <75>}, @as [])")
        self.assertEqual(parse_brightness(line), 75)
        self.assertIsNone(parse_brightness("something else"))


class Backlight(unittest.TestCase):
    def test_screen_changed_and_percent(self):
        from sound_island.parsing import backlight_percent, is_screen_changed
        self.assertTrue(is_screen_changed(
            "/org/cinnamon/SettingsDaemon/Power: org.cinnamon.SettingsDaemon.Power.Screen.Changed ()"))
        self.assertFalse(is_screen_changed("The name org.cinnamon.SettingsDaemon.Power is owned by :1.37"))
        self.assertEqual(backlight_percent("48000\n", "96000\n"), 50)
        self.assertIsNone(backlight_percent("x", "100"))
        self.assertIsNone(backlight_percent("5", "0"))
