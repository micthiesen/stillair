import json
import tempfile
import unittest
from pathlib import Path

from capture_owon_scope import capture, load_recipe


class OwonCaptureTests(unittest.TestCase):
    def recipe_file(self, *, signal: str = "SOX") -> Path:
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root))
        path = root / "recipe.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "name": "test",
                    "sampling_rate": "250k",
                    "frame_hz": 2,
                    "channels": [
                        {
                            "number": 1,
                            "signal": signal,
                            "range": "5v",
                            "offset": 0.5,
                            "probe": "x1",
                            "coupling": "DC",
                        },
                        {
                            "number": 2,
                            "signal": "FG",
                            "range": "5v",
                            "offset": 0.5,
                            "probe": "x1",
                            "coupling": "DC",
                        },
                    ],
                    "trigger": {"channel": 2, "level": "1.5v", "position": 0.25},
                }
            )
        )
        return path

    def test_simulated_capture_writes_timestamped_discrete_frames(self) -> None:
        recipe = load_recipe(self.recipe_file())
        output = Path(tempfile.mkdtemp()) / "capture"
        ready = output.parent / "ready"
        summary = capture(
            recipe,
            output,
            seconds=10,
            frame_limit=2,
            ready_file=ready,
            simulate=True,
        )
        self.assertEqual(summary["frames"], 2)
        self.assertTrue(ready.exists())
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertEqual(manifest["continuity"], "discrete_frames_with_unknown_interframe_data")
        rows = (output / "frames.jsonl").read_text().splitlines()
        self.assertEqual(len(rows), 2)
        self.assertTrue((output / json.loads(rows[0])["file"]).exists())

    def test_rejects_phase_measurement(self) -> None:
        with self.assertRaisesRegex(ValueError, "not permitted"):
            load_recipe(self.recipe_file(signal="MOTOR_U"))


if __name__ == "__main__":
    unittest.main()
