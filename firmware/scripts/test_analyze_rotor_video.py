#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "numpy>=2.0",
#   "opencv-python-headless>=4.10",
# ]
# ///
"""Focused regression tests for physical rotor tracking."""

from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from analyze_rotor_video import (
    Detection,
    first_sustained_motion,
    fit_trajectory,
    flow_rotation,
    marker_detection,
    rolling_speed,
    stick_rotation,
    unwrap_angles,
)


class RotorTrackingTests(unittest.TestCase):
    def test_perspective_ellipse_recovers_constant_physical_speed(self) -> None:
        fps = 30.0
        times = np.arange(0, 25, 1 / fps)
        rpm = 35.0
        angle = times * rpm * 2 * math.pi / 60
        rotation = math.radians(27)
        major, minor = 180.0, 142.0
        x = 704 + major * np.cos(angle) * math.cos(rotation) - minor * np.sin(angle) * math.sin(rotation)
        y = 355 + major * np.cos(angle) * math.sin(rotation) + minor * np.sin(angle) * math.cos(rotation)
        detections = [
            Detection(index, float(time_s), float(px), float(py), 300)
            for index, (time_s, px, py) in enumerate(zip(times, x, y, strict=True))
        ]
        center, axes, fitted_rotation = fit_trajectory(detections)
        unwrapped = unwrap_angles(detections, center, axes, fitted_rotation)
        speeds = rolling_speed(times, unwrapped)

        self.assertAlmostEqual(abs(float(np.nanmean(speeds))), rpm, delta=0.05)
        self.assertLess(float(np.nanstd(np.abs(speeds))), 0.05)

    def test_compact_marker_wins_over_stationary_green_wire(self) -> None:
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        cv2.line(frame, (560, 300), (650, 355), (0, 150, 0), 4)
        cv2.circle(frame, (800, 230), 14, (0, 220, 0), -1)

        detection = marker_detection(frame, 0, 30.0, (704, 355), (110, 205))

        self.assertIsNotNone(detection)
        assert detection is not None
        self.assertAlmostEqual(detection.x, 800, delta=2)
        self.assertAlmostEqual(detection.y, 230, delta=2)

    def test_alignment_twitch_is_not_mistaken_for_sustained_rotation(self) -> None:
        fps = 30.0
        times = np.arange(0, 5, 1 / fps)
        moving = np.zeros(len(times), dtype=bool)
        moving[15:20] = True
        moving[60:] = True

        start = first_sustained_motion(moving, times)

        self.assertIsNotNone(start)
        assert start is not None
        self.assertAlmostEqual(times[start], 2.0, delta=1 / fps)

    def test_monochrome_rotor_features_recover_rotation_behind_a_static_occluder(self) -> None:
        fps = 30.0
        rpm = 35.0
        center = (160, 120)
        with tempfile.TemporaryDirectory(prefix="stillair-rotor-test-") as directory:
            video = Path(directory) / "rotor.avi"
            writer = cv2.VideoWriter(
                str(video), cv2.VideoWriter_fourcc(*"MJPG"), fps, (320, 240), False
            )
            self.assertTrue(writer.isOpened())
            base = np.zeros((240, 320), dtype=np.uint8)
            cv2.circle(base, center, 92, 175, -1)
            for offset in range(0, 360, 30):
                angle = math.radians(offset)
                point = (
                    round(center[0] + 70 * math.cos(angle)),
                    round(center[1] + 70 * math.sin(angle)),
                )
                cv2.circle(base, point, 3 + (offset // 30) % 4, 30, -1)
            cv2.putText(base, "GL100", (115, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.45, 20, 1)
            for frame_index in range(120):
                angle_deg = frame_index / fps * rpm * 360 / 60
                transform = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
                frame = cv2.warpAffine(base, transform, (320, 240))
                cv2.line(frame, (70, 210), (245, 28), 230, 7)
                writer.write(frame)
            writer.release()

            times, angles, quality, _ = flow_rotation(video, center, (25, 95))
            speeds = rolling_speed(times, angles)

            self.assertGreater(quality, 0.9)
            self.assertAlmostEqual(abs(float(np.nanmedian(speeds))), rpm, delta=0.8)

    def test_radial_stick_recovers_high_speed_across_half_turn_wraps(self) -> None:
        fps = 30.0
        rpm = 170.0
        center = (160, 120)
        with tempfile.TemporaryDirectory(prefix="stillair-stick-test-") as directory:
            video = Path(directory) / "stick.avi"
            writer = cv2.VideoWriter(
                str(video), cv2.VideoWriter_fourcc(*"MJPG"), fps, (320, 240), False
            )
            self.assertTrue(writer.isOpened())
            for frame_index in range(150):
                frame = np.zeros((240, 320), dtype=np.uint8)
                cv2.circle(frame, center, 90, 150, -1)
                angle = frame_index / fps * rpm * 2 * math.pi / 60
                endpoint_a = (
                    round(center[0] - 65 * math.cos(angle)),
                    round(center[1] - 65 * math.sin(angle)),
                )
                endpoint_b = (
                    round(center[0] + 115 * math.cos(angle)),
                    round(center[1] + 115 * math.sin(angle)),
                )
                cv2.line(frame, endpoint_a, endpoint_b, 225, 13)
                writer.write(frame)
            writer.release()

            times, angles, quality, _ = stick_rotation(video, center, (0, 145))
            speeds = rolling_speed(times, angles)

            self.assertGreater(quality, 0.9)
            self.assertAlmostEqual(abs(float(np.nanmedian(speeds))), rpm, delta=2.0)

    def test_radial_stick_rejects_a_gap_that_could_hide_a_stall(self) -> None:
        fps = 30.0
        center = (160, 120)
        with tempfile.TemporaryDirectory(prefix="stillair-stick-gap-test-") as directory:
            video = Path(directory) / "stick-gap.avi"
            writer = cv2.VideoWriter(
                str(video), cv2.VideoWriter_fourcc(*"MJPG"), fps, (320, 240), False
            )
            self.assertTrue(writer.isOpened())
            for frame_index in range(90):
                frame = np.zeros((240, 320), dtype=np.uint8)
                if not 30 <= frame_index < 45:
                    angle = frame_index / fps * 35 * 2 * math.pi / 60
                    endpoint_a = (
                        round(center[0] - 65 * math.cos(angle)),
                        round(center[1] - 65 * math.sin(angle)),
                    )
                    endpoint_b = (
                        round(center[0] + 115 * math.cos(angle)),
                        round(center[1] + 115 * math.sin(angle)),
                    )
                    cv2.line(frame, endpoint_a, endpoint_b, 225, 13)
                writer.write(frame)
            writer.release()

            with self.assertRaisesRegex(ValueError, "tracking gap"):
                stick_rotation(video, center, (0, 145), maximum_gap_s=0.2)


if __name__ == "__main__":
    unittest.main()
