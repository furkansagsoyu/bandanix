import unittest

from sound_island.focus import FocusTimer


class FocusTimerTests(unittest.TestCase):
    def test_pause_resume_and_finish(self):
        now = 100
        timer = FocusTimer(lambda: now)
        timer.reset(5)
        timer.toggle()
        now += 42
        self.assertFalse(timer.tick())
        self.assertEqual(timer.remaining, 258)
        timer.toggle()
        now += 60
        self.assertFalse(timer.tick())
        self.assertEqual(timer.remaining, 258)
        timer.toggle()
        now += 258
        self.assertTrue(timer.tick())
        self.assertFalse(timer.tick())
        self.assertEqual(timer.remaining, 0)
        timer.toggle()
        self.assertEqual(timer.remaining, 300)
