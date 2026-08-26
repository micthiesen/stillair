#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "numpy>=2.0",
# ]
# ///

import math
import unittest

import numpy as np

from analyze_motor_audio import SAMPLE_RATE, metrics


class MotorAudioTests(unittest.TestCase):
    def test_reports_electrical_tone_and_cyclical_modulation(self) -> None:
        duration = 8.0
        times = np.arange(round(duration * SAMPLE_RATE)) / SAMPLE_RATE
        envelope = 0.35 + 0.2 * np.sin(2 * math.pi * 1.25 * times)
        samples = envelope * np.sin(2 * math.pi * 3_200 * times)

        result = metrics(samples.astype(np.float32), "synthetic", 0.0, duration)

        self.assertAlmostEqual(result["electrical_peaks"][0]["hz"], 3_200, delta=8)
        high = result["bands"]["high_2000_7500"]
        self.assertAlmostEqual(high["dominant_modulation_hz"], 1.25, delta=0.15)
        self.assertGreater(high["stddev_db"], 1.0)

    def test_dedicated_mic_rate_preserves_upper_audible_tone(self) -> None:
        sample_rate = 48_000
        duration = 2.0
        times = np.arange(round(duration * sample_rate)) / sample_rate
        samples = np.sin(2 * math.pi * 12_000 * times)

        result = metrics(samples.astype(np.float32), "upper", 0.0, duration, sample_rate)

        self.assertEqual(result["sample_rate_hz"], sample_rate)
        self.assertAlmostEqual(result["electrical_peaks"][0]["hz"], 12_000, delta=6)
        self.assertIn("upper_7500_20000", result["bands"])


if __name__ == "__main__":
    unittest.main()
