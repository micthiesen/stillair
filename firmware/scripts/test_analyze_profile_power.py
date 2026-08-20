#!/usr/bin/env python3

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from analyze_profile_plateaus import Plateau
from analyze_profile_power import PowerSample, measure, power_samples, wall_start


class ProfilePowerTests(unittest.TestCase):
    def test_parses_sync_marker_and_scores_only_the_plateau_window(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            motor = root / "motor.log"
            power = root / "power.log"
            motor.write_text(
                "# wall_start=2026-08-20T10:00:00Z\n"
                "# t=5.000s dwell 6\n"
            )
            rows = [
                {
                    "type": "utility_plug",
                    "event": "sample",
                    "timestamp": f"2026-08-20T10:00:{second:02d}.200Z",
                    "on": True,
                    "volts": 117.0,
                    "amps": 0.03,
                    "watts": watts,
                }
                for second, watts in [(6, 9.0), (7, 1.5), (8, 1.7), (10, 1.6), (11, 8.0)]
            ]
            power.write_text("\n".join(json.dumps(row) for row in rows) + "\n")

            anchor = wall_start(motor)
            result = measure(Plateau(100, 1, 7.0, 11.0), anchor, power_samples(power))

        self.assertEqual(anchor, datetime(2026, 8, 20, 10, tzinfo=timezone.utc))
        self.assertEqual(result["samples"], 3)
        self.assertEqual(result["mean_watts"], 1.6)
        self.assertEqual(result["direction"], "forward")

    def test_rejects_a_log_without_a_sync_marker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "motor.log"
            path.write_text("# t=1.000s dwell 5\n")
            with self.assertRaisesRegex(ValueError, "wall_start"):
                wall_start(path)

    def test_long_plateau_reports_minute_power_drift(self) -> None:
        anchor = datetime(2026, 8, 20, 10, tzinfo=timezone.utc)
        samples = [
            PowerSample(
                timestamp=anchor + timedelta(minutes=minute, seconds=second),
                volts=115.0,
                amps=0.03,
                watts=2.0 + minute * 0.1,
            )
            for minute in range(3)
            for second in range(60)
        ]
        result = measure(Plateau(170, 1, 0.0, 180.0), anchor, samples)
        self.assertEqual(result["minute_mean_watts"], [2.0, 2.1, 2.2])
        self.assertEqual(result["last_minus_first_minute_watts"], 0.2)

    def test_rejects_a_gap_in_endurance_power_evidence(self) -> None:
        anchor = datetime(2026, 8, 20, 10, tzinfo=timezone.utc)
        samples = [
            PowerSample(anchor + timedelta(seconds=second), 115.0, 0.03, 2.0)
            for second in range(180)
            if not 70 <= second < 80
        ]
        with self.assertRaisesRegex(ValueError, "power evidence gap"):
            measure(Plateau(170, 1, 0.0, 180.0), anchor, samples)

    def test_nonfinite_power_samples_are_discarded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "power.log"
            rows = [
                {
                    "type": "utility_plug",
                    "event": "sample",
                    "timestamp": "2026-08-20T10:00:00Z",
                    "on": True,
                    "volts": 115.0,
                    "amps": 0.03,
                    "watts": value,
                }
                for value in [float("nan"), 2.0]
            ]
            path.write_text("\n".join(json.dumps(row) for row in rows))
            self.assertEqual(len(power_samples(path)), 1)


if __name__ == "__main__":
    unittest.main()
