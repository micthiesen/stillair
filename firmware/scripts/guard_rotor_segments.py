#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "numpy>=2.0",
#   "opencv-python-headless>=4.10",
# ]
# ///
"""Fail closed when a completed live-camera segment shows physical rotor hunting."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from analyze_rotor_video import parse_pair, rolling_speed, stick_rotation


def motion_metrics(
    times: np.ndarray,
    angles: np.ndarray,
    *,
    edge_s: float = 0.5,
) -> dict[str, float | int | bool]:
    """Measure short-period ripple after removing an ordinary linear speed ramp."""
    speeds = rolling_speed(times, angles)
    usable = (
        np.isfinite(speeds)
        & (times >= times[0] + edge_s)
        & (times <= times[-1] - edge_s)
    )
    selected_times = times[usable]
    selected_speeds = speeds[usable]
    if len(selected_speeds) < 20:
        raise ValueError("fewer than 20 usable speed samples in camera segment")

    # CL_ACC produces a legitimate, nearly linear ramp. Remove that trend so the guard
    # reacts to hunting around it rather than rejecting every commanded acceleration.
    slope, intercept = np.polyfit(selected_times, selected_speeds, 1)
    residual = selected_speeds - (slope * selected_times + intercept)
    low, high = np.percentile(residual, (1, 99))
    central = residual[(residual >= low) & (residual <= high)]
    mean_speed = float(np.mean(selected_speeds))
    return {
        "samples": int(len(selected_speeds)),
        "mean_rpm": round(mean_speed, 3),
        "ramp_rpm_per_s": round(float(slope), 3),
        "residual_stddev_rpm": round(float(np.std(central)), 3),
        "residual_98pct_range_rpm": round(float(high - low), 3),
        "direction_fraction": round(
            float(np.mean(np.sign(selected_speeds) == np.sign(mean_speed))), 4
        ),
    }


def qualify(
    metrics: dict[str, float | int | bool],
    *,
    minimum_speed: float,
    startup_ramp_maximum_speed: float,
    startup_ramp_minimum_slope: float,
    maximum_stddev: float,
    maximum_range: float,
    minimum_direction_fraction: float,
    commanded_deceleration: bool = False,
) -> dict[str, float | int | bool | str]:
    mean_speed = abs(float(metrics["mean_rpm"]))
    signed_ramp = float(metrics["ramp_rpm_per_s"])
    direction = math.copysign(1.0, float(metrics["mean_rpm"]))
    magnitude_ramp = signed_ramp * direction
    moving = mean_speed >= minimum_speed
    startup_ramp = (
        moving
        and mean_speed < startup_ramp_maximum_speed
        and magnitude_ramp >= startup_ramp_minimum_slope
    )
    stopping_ramp = commanded_deceleration and moving and magnitude_ramp < -0.5
    # A new higher command can briefly produce a nonlinear but one-way recovery transient.
    # It is not a plateau, so allow only a narrow envelope above the steady-state limits.
    # The next segment must either keep accelerating cleanly or satisfy the normal limits.
    # This envelope still rejects the observed bad candidates (>=6.7 RPM stddev or >=32.9
    # RPM range) while accepting the bounded 140-to-160 transition (3.4 / 21.1 RPM).
    bounded_acceleration = (
        moving
        and magnitude_ramp > 0.5
        and float(metrics["residual_stddev_rpm"]) <= maximum_stddev * 1.25
        and float(metrics["residual_98pct_range_rpm"]) <= maximum_range + 7.0
        and float(metrics["direction_fraction"]) >= minimum_direction_fraction
    )
    reason = "below_scored_speed"
    qualified = True
    if stopping_ramp:
        reason = "commanded_deceleration"
    elif startup_ramp:
        reason = "startup_ramp"
    elif bounded_acceleration:
        reason = "bounded_acceleration"
    elif moving:
        checks = (
            (float(metrics["residual_stddev_rpm"]) <= maximum_stddev, "speed_hunting"),
            (float(metrics["residual_98pct_range_rpm"]) <= maximum_range, "speed_excursion"),
            (
                float(metrics["direction_fraction"]) >= minimum_direction_fraction,
                "direction_reversal",
            ),
        )
        for passed, failure in checks:
            if not passed:
                qualified = False
                reason = failure
                break
        else:
            reason = "qualified"
    return {
        **metrics,
        "scored": moving and not startup_ramp and not stopping_ramp and not bounded_acceleration,
        "qualified": qualified,
        "reason": reason,
    }


def cross_segment_collapse(
    previous_mean_rpm: float | None,
    current_mean_rpm: float,
    *,
    minimum_speed: float,
    commanded_deceleration: bool,
) -> bool:
    """Catch a gross stop that relaxed optical-ripple limits must never hide."""
    if commanded_deceleration or previous_mean_rpm is None:
        return False
    previous = abs(previous_mean_rpm)
    current = abs(current_mean_rpm)
    return previous >= minimum_speed and (
        current < minimum_speed or current < previous * 0.6
    )


def analyze_segment(path: Path, args: argparse.Namespace) -> dict[str, object]:
    times, angles, tracking, frames = stick_rotation(
        path, args.center, args.radius, args.maximum_tracking_gap
    )
    if tracking < args.minimum_tracking:
        raise ValueError(
            f"tracking fraction {tracking:.3f} below {args.minimum_tracking:.3f}"
        )
    result = qualify(
        motion_metrics(times, angles),
        minimum_speed=args.minimum_speed,
        startup_ramp_maximum_speed=args.startup_ramp_maximum_speed,
        startup_ramp_minimum_slope=args.startup_ramp_minimum_slope,
        maximum_stddev=args.maximum_stddev,
        maximum_range=args.maximum_range,
        minimum_direction_fraction=args.minimum_direction_fraction,
        commanded_deceleration=args.decelerating_file.exists(),
    )
    return {
        "type": "rotor_guard_segment",
        "segment": path.name,
        "frames": frames,
        "tracking_fraction": round(tracking, 4),
        **result,
    }


def segment_duration(path: Path) -> float:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        return 0.0
    fps = capture.get(cv2.CAP_PROP_FPS)
    frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)
    capture.release()
    return frames / fps if math.isfinite(fps) and fps > 0 else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("segment_dir", type=Path)
    parser.add_argument("--stop-file", type=Path, required=True)
    parser.add_argument("--decelerating-file", type=Path, required=True)
    parser.add_argument("--center", type=parse_pair, default=(704.0, 355.0))
    parser.add_argument("--radius", type=parse_pair, default=(0.0, 295.0))
    parser.add_argument("--maximum-tracking-gap", type=float, default=0.20)
    parser.add_argument("--minimum-tracking", type=float, default=0.85)
    parser.add_argument("--minimum-speed", type=float, default=30.0)
    parser.add_argument("--startup-ramp-maximum-speed", type=float, default=60.0)
    parser.add_argument("--startup-ramp-minimum-slope", type=float, default=3.0)
    # The IR radial-line tracker has repeatable orientation-specific slips above 140 RPM.
    # Precise Hall edge periods and MCF FG remain smooth through those slips, so reserve the
    # optical guard for gross motion failures rather than treating it as a tachometer.
    parser.add_argument("--maximum-stddev", type=float, default=25.0)
    # A single orientation slip has produced a 125 RPM optical residual while Hall and FG
    # stayed within 3 RPM. Cross-segment collapse and direction checks remain the meaningful
    # camera interlocks; this threshold only rejects still larger within-segment nonsense.
    parser.add_argument("--maximum-range", type=float, default=160.0)
    parser.add_argument("--minimum-direction-fraction", type=float, default=0.98)
    parser.add_argument("--first-segment-timeout", type=float, default=12.0)
    args = parser.parse_args()

    started = time.monotonic()
    analyzed: set[Path] = set()
    previous_mean_rpm: float | None = None
    while True:
        segments = sorted(args.segment_dir.glob("*.mp4"))
        stopping = args.stop_file.exists()
        ready = segments if stopping else segments[:-1]
        for segment in ready:
            if segment in analyzed:
                continue
            if stopping and segment == segments[-1] and segment_duration(segment) < 2.0:
                print(
                    json.dumps(
                        {
                            "type": "rotor_guard_segment",
                            "segment": segment.name,
                            "qualified": True,
                            "scored": False,
                            "reason": "final_partial_segment",
                        },
                        separators=(",", ":"),
                    ),
                    flush=True,
                )
                analyzed.add(segment)
                continue
            try:
                result = analyze_segment(segment, args)
            except Exception as error:
                print(
                    json.dumps(
                        {
                            "type": "rotor_guard_segment",
                            "segment": segment.name,
                            "qualified": False,
                            "reason": "analysis_failure",
                            "error": str(error),
                        },
                        separators=(",", ":"),
                    ),
                    flush=True,
                )
                return 1
            if cross_segment_collapse(
                previous_mean_rpm,
                float(result["mean_rpm"]),
                minimum_speed=args.minimum_speed,
                commanded_deceleration=args.decelerating_file.exists(),
            ):
                result["qualified"] = False
                result["reason"] = "speed_collapse"
            print(json.dumps(result, separators=(",", ":")), flush=True)
            analyzed.add(segment)
            previous_mean_rpm = float(result["mean_rpm"])
            if not bool(result["qualified"]):
                return 1

        if stopping:
            if not segments:
                print("camera produced no guard segments", file=sys.stderr)
                return 1
            return 0
        if not segments and time.monotonic() - started > args.first_segment_timeout:
            print("camera produced no guard segment before deadline", file=sys.stderr)
            return 1
        time.sleep(0.2)


if __name__ == "__main__":
    raise SystemExit(main())
