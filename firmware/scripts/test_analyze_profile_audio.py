import tempfile
import unittest
from pathlib import Path

from analyze_profile_audio import profile_windows


class ProfileAudioTests(unittest.TestCase):
    def log(self, text: str) -> Path:
        handle = tempfile.NamedTemporaryFile(mode="w", delete=False)
        handle.write(text)
        handle.close()
        self.addCleanup(Path(handle.name).unlink)
        return Path(handle.name)

    def test_maps_motor_windows_onto_earlier_audio_timeline(self) -> None:
        windows = profile_windows(
            self.log(
                """# t=1.000s run 50
# t=20.000s stream 10 --for 30
# t=51.000s run 80
# t=70.000s dwell 20
"""
            ),
            3.5,
        )
        self.assertEqual(windows[0].label, "50rpm-1")
        self.assertEqual(windows[0].start, 25.5)
        self.assertEqual(windows[0].end, 52.5)
        self.assertEqual(windows[1].label, "80rpm-2")

    def test_rejects_log_without_measured_speed_window(self) -> None:
        with self.assertRaisesRegex(ValueError, "no speed-labelled"):
            profile_windows(self.log("# t=1.000s run 50\n# t=2.000s stop\n"), 0)


if __name__ == "__main__":
    unittest.main()
