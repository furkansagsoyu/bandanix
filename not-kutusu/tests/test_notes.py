"""Tests for the quick-notes file logic: python3 -m unittest discover not-kutusu/tests"""
import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import notes  # noqa: E402

T = dt.datetime(2026, 11, 8, 20, 50)


class NotesFile(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "Notlar" / "hizli-notlar.md"

    def tearDown(self):
        self.dir.cleanup()

    def test_first_note_creates_file_with_header(self):
        notes.add(self.path, "ilk not", T)
        self.assertEqual(self.path.read_text(), "# Hızlı notlar\n\n## 2026-11-08 20:50\nilk not\n")

    def test_newest_on_top_and_multiline(self):
        notes.add(self.path, "eski", T)
        notes.add(self.path, "yeni\nikinci satır", T + dt.timedelta(minutes=5))
        items = notes.read_notes(self.path)
        self.assertEqual([n.body for n in items], ["yeni\nikinci satır", "eski"])
        self.assertEqual(items[0].title, "yeni …")

    def test_blank_note_is_ignored(self):
        self.assertIsNone(notes.add(self.path, "  \n ", T))
        self.assertFalse(self.path.exists())

    def test_hand_written_text_is_kept(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("# Benim notlarım\nbu satır elle yazıldı\n\n## 2026-11-01 10:00\neski\n")
        notes.add(self.path, "yeni", T)
        text = self.path.read_text()
        self.assertTrue(text.startswith("# Benim notlarım\nbu satır elle yazıldı\n\n## 2026-11-08 20:50\nyeni\n"))
        self.assertIn("## 2026-11-01 10:00\neski", text)

    def test_heading_inside_note_does_not_split_it(self):
        notes.add(self.path, "a\n## 2026-01-01 00:00\nb", T)
        self.assertEqual(len(notes.read_notes(self.path)), 1)

    def test_todo_toggle(self):
        notes.add(self.path, "[ ] mail at", T)
        notes.add(self.path, "- [ ] markdown görevi", T + dt.timedelta(minutes=1))
        items = notes.read_notes(self.path)
        self.assertEqual([n.todo for n in items], [False, False])
        self.assertEqual(items[1].text, "mail at")
        self.assertTrue(notes.toggle(self.path, items[1]))
        self.assertTrue(notes.toggle(self.path, items[0]))
        items = notes.read_notes(self.path)
        self.assertEqual([n.body for n in items], ["- [x] markdown görevi", "[x] mail at"])
        self.assertTrue(notes.toggle(self.path, items[1]))
        self.assertEqual(notes.read_notes(self.path)[1].body, "[ ] mail at")

    def test_toggle_refuses_changed_note(self):
        note = notes.add(self.path, "[ ] a", T)
        self.path.write_text(self.path.read_text().replace("[ ] a", "[ ] b"))
        self.assertFalse(notes.toggle(self.path, note))

    def test_plain_note_is_not_a_task(self):
        note = notes.add(self.path, "[link] değil", T)
        self.assertIsNone(note.todo)
        self.assertFalse(notes.toggle(self.path, note))


class Ago(unittest.TestCase):
    def test_texts(self):
        cases = {
            T - dt.timedelta(seconds=20): "az önce",
            T - dt.timedelta(minutes=3): "3 dk önce",
            T - dt.timedelta(hours=5): "bugün 15:50",
            dt.datetime(2026, 11, 7, 14, 20): "dün 14:20",
            dt.datetime(2026, 11, 3, 9, 5): "Salı 09:05",
            dt.datetime(2026, 10, 1, 9, 5): "1 Eki 09:05",
            dt.datetime(2025, 10, 1, 9, 5): "1 Eki 2025",
        }
        for when, want in cases.items():
            self.assertEqual(notes.ago(when, T), want)


if __name__ == "__main__":
    unittest.main()
