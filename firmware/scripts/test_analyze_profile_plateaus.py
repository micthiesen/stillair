#!/usr/bin/env python3

import argparse
import math
import tempfile
import unittest
from pathlib import Path

from analyze_profile_plateaus import Plateau, plateaus, qualify, raw_measure, summarize


def thresholds() -> argparse.Namespace:
    return argparse.Namespace(
        error_rpm=2.0,
        error_fraction=0.03,
        maximum_stddev=3.0,
        maximum_range=15.0,
        stall_rpm=2.0,
        reverse_rpm=2.0,
        maximum_stall=0.25,
        maximum_reverse=0.10,
        minimum_coverage=0.90,
        minimum_window_coverage=0.90,
        minimum_sample_hz=10.0,
        maximum_scored_rpm=140.0,
    )


def rows(rpm: float, duration: float = 6.0, step: float = 0.05):
    result = []
    time_s = 0.0
    while time_s < duration:
        angle = time_s * rpm * 2 * math.pi / 60
        result.append((time_s, angle, rpm))
        time_s += step
    return result


class PlateauAnalysisTests(unittest.TestCase):
    def test_extracts_direction_and_dwell_after_latest_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "motor.log"
            log.write_text(
                "# t=1.000s run 60\n# t=5.000s dwell 6\n"
                "# t=12.000s dir reverse\n# t=13.000s run 100\n# t=20.000s dwell 5\n"
            )
            self.assertEqual(
                [(p.target_rpm, p.direction, p.start_s, p.end_s) for p in plateaus(log, 1.0)],
                [(60, 1, 6.0, 11.0), (100, -1, 21.0, 25.0)],
            )

    def test_exact_angle_rate_and_steady_speed_qualify(self) -> None:
        window = Plateau(60, 1, 0, 6)
        camera = rows(60)
        raw = raw_measure(window, camera, 0)
        result = qualify(window, camera, raw, 1, 0, thresholds())
        self.assertAlmostEqual(float(result["exact_rpm"]), 60.0)
        self.assertTrue(result["qualified"])

    def test_wrong_direction_fails_even_when_magnitude_is_exact(self) -> None:
        window = Plateau(60, -1, 0, 6)
        camera = rows(60)
        raw = raw_measure(window, camera, 0)
        result = qualify(window, camera, raw, 1, 0, thresholds())
        self.assertLess(float(result["exact_rpm"]), 0)
        self.assertFalse(result["qualified"])

    def test_mid_plateau_stall_cannot_be_hidden_by_endpoint_speed(self) -> None:
        window = Plateau(60, 1, 0, 6)
        camera = rows(60)
        stopped_angle = camera[40][1]
        camera = [
            (time_s, stopped_angle if 2.0 <= time_s <= 3.0 else angle, 0.0 if 2.0 <= time_s <= 3.0 else speed)
            for time_s, angle, speed in camera
        ]
        raw = raw_measure(window, camera, 0)
        result = qualify(window, camera, raw, 1, 0, thresholds())
        self.assertGreater(float(result["longest_stall_s"]), 0.9)
        self.assertFalse(result["qualified"])

    def test_sparse_window_fails_coverage(self) -> None:
        window = Plateau(60, 1, 0, 6)
        camera = rows(60)[::20]
        raw = raw_measure(window, camera, 0)
        result = qualify(window, camera, raw, 1, 0, thresholds())
        self.assertFalse(result["qualified"])

    def test_high_speed_optical_slip_is_reported_but_not_used_as_tachometer(self) -> None:
        window = Plateau(170, 1, 0, 6)
        camera = rows(155)
        raw = raw_measure(window, camera, 0)
        result = qualify(window, camera, raw, 1, 0, thresholds())
        self.assertFalse(result["speed_scored"])
        self.assertTrue(result["qualified"])

    def test_summary_handles_only_unscored_high_speed_plateaus(self) -> None:
        summary = summarize(
            [{"speed_scored": False, "qualified": True, "error_rpm": 12.0}],
            2.0,
            1,
        )
        self.assertEqual(summary["speed_scored_plateaus"], 0)
        self.assertIsNone(summary["max_abs_error_rpm"])
        self.assertTrue(summary["qualified"])


if __name__ == "__main__":
    unittest.main()
