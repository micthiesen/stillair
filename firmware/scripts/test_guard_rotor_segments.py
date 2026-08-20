#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "numpy>=2.0",
#   "opencv-python-headless>=4.10",
# ]
# ///

import math
import unittest

import numpy as np

from guard_rotor_segments import cross_segment_collapse, motion_metrics, qualify


def trajectory(speed_fn, duration: float = 5.0, fps: float = 30.0):
    times = np.arange(0.0, duration, 1 / fps)
    speeds = np.asarray([speed_fn(value) for value in times])
    steps = speeds / 60 * 2 * math.pi / fps
    return times, np.cumsum(steps)


class RotorGuardTests(unittest.TestCase):
    def test_relaxed_optical_ripple_never_hides_a_gross_speed_collapse(self) -> None:
        self.assertTrue(
            cross_segment_collapse(
                160.0,
                20.0,
                minimum_speed=30.0,
                commanded_deceleration=False,
            )
        )
        self.assertFalse(
            cross_segment_collapse(
                160.0,
                20.0,
                minimum_speed=30.0,
                commanded_deceleration=True,
            )
        )

    def test_ordinary_linear_acceleration_is_removed_before_scoring(self) -> None:
        times, angles = trajectory(lambda t: 100 + 1.5 * t)
        result = qualify(
            motion_metrics(times, angles),
            minimum_speed=30,
            startup_ramp_maximum_speed=60,
            startup_ramp_minimum_slope=3,
            maximum_stddev=4,
            maximum_range=18,
            minimum_direction_fraction=0.98,
        )
        self.assertTrue(result["qualified"])
        self.assertLess(float(result["residual_stddev_rpm"]), 0.1)

    def test_sustained_hunting_fails(self) -> None:
        times, angles = trajectory(lambda t: 150 + 18 * math.sin(2 * math.pi * 2.5 * t))
        result = qualify(
            motion_metrics(times, angles),
            minimum_speed=30,
            startup_ramp_maximum_speed=60,
            startup_ramp_minimum_slope=3,
            maximum_stddev=4,
            maximum_range=18,
            minimum_direction_fraction=0.98,
        )
        self.assertFalse(result["qualified"])
        self.assertEqual(result["reason"], "speed_hunting")

    def test_stationary_segment_is_observed_but_not_scored(self) -> None:
        times, angles = trajectory(lambda _: 0)
        result = qualify(
            motion_metrics(times, angles),
            minimum_speed=30,
            startup_ramp_maximum_speed=60,
            startup_ramp_minimum_slope=3,
            maximum_stddev=4,
            maximum_range=18,
            minimum_direction_fraction=0.98,
        )
        self.assertTrue(result["qualified"])
        self.assertFalse(result["scored"])

    def test_fast_low_speed_startup_ramp_is_not_misclassified_as_hunting(self) -> None:
        result = qualify(
            {
                "mean_rpm": 33.0,
                "ramp_rpm_per_s": 7.5,
                "residual_stddev_rpm": 5.8,
                "residual_98pct_range_rpm": 22.1,
                "direction_fraction": 1.0,
            },
            minimum_speed=30,
            startup_ramp_maximum_speed=60,
            startup_ramp_minimum_slope=3,
            maximum_stddev=4,
            maximum_range=18,
            minimum_direction_fraction=0.98,
        )
        self.assertTrue(result["qualified"])
        self.assertFalse(result["scored"])
        self.assertEqual(result["reason"], "startup_ramp")

    def test_bounded_high_speed_acceleration_is_not_misclassified(self) -> None:
        result = qualify(
            {
                "mean_rpm": 147.5,
                "ramp_rpm_per_s": 2.9,
                "residual_stddev_rpm": 3.4,
                "residual_98pct_range_rpm": 21.1,
                "direction_fraction": 1.0,
            },
            minimum_speed=30,
            startup_ramp_maximum_speed=60,
            startup_ramp_minimum_slope=3,
            maximum_stddev=4,
            maximum_range=18,
            minimum_direction_fraction=0.98,
        )
        self.assertTrue(result["qualified"])
        self.assertFalse(result["scored"])
        self.assertEqual(result["reason"], "bounded_acceleration")

    def test_fast_high_speed_hunting_exceeding_transient_envelope_fails(self) -> None:
        result = qualify(
            {
                "mean_rpm": 145.8,
                "ramp_rpm_per_s": 2.6,
                "residual_stddev_rpm": 6.7,
                "residual_98pct_range_rpm": 32.9,
                "direction_fraction": 1.0,
            },
            minimum_speed=30,
            startup_ramp_maximum_speed=60,
            startup_ramp_minimum_slope=3,
            maximum_stddev=4,
            maximum_range=18,
            minimum_direction_fraction=0.98,
        )
        self.assertFalse(result["qualified"])
        self.assertTrue(result["scored"])

    def test_explicit_commanded_deceleration_is_not_steady_state_hunting(self) -> None:
        result = qualify(
            {
                "mean_rpm": 118.0,
                "ramp_rpm_per_s": -1.5,
                "residual_stddev_rpm": 4.2,
                "residual_98pct_range_rpm": 19.0,
                "direction_fraction": 1.0,
            },
            minimum_speed=30,
            startup_ramp_maximum_speed=60,
            startup_ramp_minimum_slope=3,
            maximum_stddev=4,
            maximum_range=18,
            minimum_direction_fraction=0.98,
            commanded_deceleration=True,
        )
        self.assertTrue(result["qualified"])
        self.assertFalse(result["scored"])
        self.assertEqual(result["reason"], "commanded_deceleration")

    def test_reverse_commanded_deceleration_is_classified_by_speed_magnitude(self) -> None:
        result = qualify(
            {
                "mean_rpm": -118.0,
                "ramp_rpm_per_s": 1.5,
                "residual_stddev_rpm": 4.2,
                "residual_98pct_range_rpm": 19.0,
                "direction_fraction": 1.0,
            },
            minimum_speed=30,
            startup_ramp_maximum_speed=60,
            startup_ramp_minimum_slope=3,
            maximum_stddev=4,
            maximum_range=18,
            minimum_direction_fraction=0.98,
            commanded_deceleration=True,
        )
        self.assertTrue(result["qualified"])
        self.assertFalse(result["scored"])
        self.assertEqual(result["reason"], "commanded_deceleration")

    def test_reverse_acceleration_uses_increasing_speed_magnitude(self) -> None:
        result = qualify(
            {
                "mean_rpm": -147.5,
                "ramp_rpm_per_s": -2.9,
                "residual_stddev_rpm": 3.4,
                "residual_98pct_range_rpm": 21.1,
                "direction_fraction": 1.0,
            },
            minimum_speed=30,
            startup_ramp_maximum_speed=60,
            startup_ramp_minimum_slope=3,
            maximum_stddev=4,
            maximum_range=18,
            minimum_direction_fraction=0.98,
        )
        self.assertTrue(result["qualified"])
        self.assertFalse(result["scored"])
        self.assertEqual(result["reason"], "bounded_acceleration")

    def test_uncommanded_speed_collapse_remains_a_failure(self) -> None:
        result = qualify(
            {
                "mean_rpm": 118.0,
                "ramp_rpm_per_s": -1.5,
                "residual_stddev_rpm": 4.2,
                "residual_98pct_range_rpm": 19.0,
                "direction_fraction": 1.0,
            },
            minimum_speed=30,
            startup_ramp_maximum_speed=60,
            startup_ramp_minimum_slope=3,
            maximum_stddev=4,
            maximum_range=18,
            minimum_direction_fraction=0.98,
        )
        self.assertFalse(result["qualified"])
        self.assertTrue(result["scored"])


if __name__ == "__main__":
    unittest.main()
