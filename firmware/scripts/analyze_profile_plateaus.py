#!/usr/bin/env python3
"""Qualify timestamped motor-profile dwells against synchronized physical rotor motion."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from dataclasses import dataclass
from pathlib import Path

STEP = re.compile(r"^# t=(?P<time>[0-9.]+)s (?P<command>.+)$")


@dataclass(frozen=True)
class Plateau:
    target_rpm: int
    direction: int
    start_s: float
    end_s: float


def plateaus(path: Path, settle_s: float) -> list[Plateau]:
    target: int | None = None
    direction = 1
    found: list[Plateau] = []
    for raw in path.read_text().splitlines():
        match = STEP.match(raw)
        if not match:
            continue
        command = match.group("command").split()
        if not command:
            continue
        if command[0] == "dir" and len(command) == 2:
            if command[1] in ("fwd", "forward"):
                direction = 1
            elif command[1] in ("rev", "reverse"):
                direction = -1
        elif command[0] == "run" and len(command) == 2:
            target = int(command[1])
        elif command[0] == "dwell" and len(command) == 2 and target is not None:
            start = float(match.group("time")) + settle_s
            end = float(match.group("time")) + float(command[1])
            if start >= end:
                raise ValueError("settling allowance consumes an entire dwell")
            found.append(Plateau(target, direction, start, end))
    return found


def camera_rows(path: Path) -> list[tuple[float, float, float]]:
    rows: list[tuple[float, float, float]] = []
    with path.open(newline="") as source:
        for row in csv.DictReader(source):
            angle = row.get("raw_angle_rad") or row.get("angle_rad") or "nan"
            speed = row.get("raw_speed_rpm") or row.get("speed_rpm") or "nan"
            rows.append((float(row["t_s"]), float(angle), float(speed)))
    return rows


def longest_duration(condition: list[bool], times: list[float]) -> float:
    longest = 0.0
    started: float | None = None
    for matches, time_s in zip(condition, times, strict=True):
        if matches and started is None:
            started = time_s
        elif not matches and started is not None:
            longest = max(longest, time_s - started)
            started = None
    if started is not None and times:
        longest = max(longest, times[-1] - started)
    return longest


def raw_measure(
    plateau: Plateau,
    rows: list[tuple[float, float, float]],
    camera_offset_s: float,
) -> dict[str, float | int]:
    start = plateau.start_s + camera_offset_s
    end = plateau.end_s + camera_offset_s
    selected = [row for row in rows if start <= row[0] < end]
    if len(selected) < 4:
        raise ValueError(
            f"fewer than four camera rows for {plateau.target_rpm} RPM at {start:.3f}s"
        )
    finite = [row for row in selected if math.isfinite(row[1]) and math.isfinite(row[2])]
    if len(finite) < 4:
        raise ValueError(f"no usable physical motion for {plateau.target_rpm} RPM")
    elapsed = finite[-1][0] - finite[0][0]
    if elapsed <= 0:
        raise ValueError("camera timestamps did not advance")
    raw_exact = (finite[-1][1] - finite[0][1]) / elapsed * 60 / (2 * math.pi)
    return {
        "target_rpm": plateau.target_rpm,
        "direction": plateau.direction,
        "start_s": round(start, 3),
        "end_s": round(end, 3),
        "samples": len(selected),
        "finite_samples": len(finite),
        "coverage": len(finite) / len(selected),
        "window_coverage": elapsed / (end - start),
        "raw_exact_rpm": raw_exact,
    }


def qualify(
    plateau: Plateau,
    rows: list[tuple[float, float, float]],
    raw: dict[str, float | int],
    forward_sign: int,
    camera_offset_s: float,
    args: argparse.Namespace,
) -> dict[str, float | int | bool | str]:
    start = plateau.start_s + camera_offset_s
    end = plateau.end_s + camera_offset_s
    selected = [row for row in rows if start <= row[0] < end]
    expected_sign = forward_sign * plateau.direction
    finite = [row for row in selected if math.isfinite(row[1]) and math.isfinite(row[2])]
    times = [row[0] for row in finite]
    speeds = [row[2] * expected_sign for row in finite]
    sample_hz = (len(finite) - 1) / max(times[-1] - times[0], 1e-9)
    exact = float(raw["raw_exact_rpm"]) * expected_sign
    tolerance = max(args.error_rpm, plateau.target_rpm * args.error_fraction)
    stalled = [abs(speed) < args.stall_rpm for speed in speeds]
    reversed_motion = [speed < -args.reverse_rpm for speed in speeds]
    longest_stall = longest_duration(stalled, times)
    longest_reverse = longest_duration(reversed_motion, times)
    error = exact - plateau.target_rpm
    stddev = statistics.pstdev(speeds)
    percentiles = statistics.quantiles(speeds, n=100, method="inclusive")
    low, high = percentiles[0], percentiles[98]
    central_speeds = [speed for speed in speeds if low <= speed <= high]
    central_stddev = statistics.pstdev(central_speeds)
    central_range = high - low
    tracking_qualified = (
        float(raw["coverage"]) >= args.minimum_coverage
        and float(raw["window_coverage"]) >= args.minimum_window_coverage
        and sample_hz >= args.minimum_sample_hz
        and longest_stall <= args.maximum_stall
        and longest_reverse <= args.maximum_reverse
    )
    speed_scored = plateau.target_rpm <= args.maximum_scored_rpm
    speed_qualified = (
        abs(error) <= tolerance
        and central_stddev <= args.maximum_stddev
        and central_range <= args.maximum_range
    )
    qualified = tracking_qualified and (not speed_scored or speed_qualified)
    return {
        "target_rpm": plateau.target_rpm,
        "direction": "forward" if plateau.direction > 0 else "reverse",
        "start_s": raw["start_s"],
        "end_s": raw["end_s"],
        "samples": raw["samples"],
        "coverage": round(float(raw["coverage"]), 4),
        "window_coverage": round(float(raw["window_coverage"]), 4),
        "sample_hz": round(sample_hz, 3),
        "exact_rpm": round(exact, 3),
        "error_rpm": round(error, 3),
        "rolling_mean_rpm": round(statistics.fmean(speeds), 3),
        "rolling_stddev_rpm": round(stddev, 3),
        "central_stddev_rpm": round(central_stddev, 3),
        "central_98pct_range_rpm": round(central_range, 3),
        "rolling_min_rpm": round(min(speeds), 3),
        "rolling_max_rpm": round(max(speeds), 3),
        "longest_stall_s": round(longest_stall, 3),
        "longest_reverse_s": round(longest_reverse, 3),
        "speed_scored": speed_scored,
        "qualified": qualified,
    }


def summarize(
    measured: list[dict[str, float | int | bool | str]],
    camera_offset: float,
    forward_sign: int,
) -> dict[str, object]:
    errors = [
        abs(float(item["error_rpm"]))
        for item in measured
        if bool(item["speed_scored"])
    ]
    return {
        "type": "physical_plateau_summary",
        "plateaus": len(measured),
        "speed_scored_plateaus": len(errors),
        "max_abs_error_rpm": round(max(errors), 3) if errors else None,
        "mean_abs_error_rpm": round(statistics.fmean(errors), 3) if errors else None,
        "failed_plateaus": sum(not bool(item["qualified"]) for item in measured),
        "qualified": all(bool(item["qualified"]) for item in measured),
        "camera_offset_s": round(camera_offset, 6),
        "camera_forward_sign": forward_sign,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("motor_log", type=Path)
    parser.add_argument("camera_csv", type=Path)
    parser.add_argument("--settle", type=float, default=1.0)
    parser.add_argument("--camera-offset-us", type=int, required=True)
    parser.add_argument("--forward-sign", type=int, choices=(-1, 1))
    parser.add_argument("--error-rpm", type=float, default=2.0)
    parser.add_argument("--error-fraction", type=float, default=0.03)
    parser.add_argument("--maximum-stddev", type=float, default=3.0)
    parser.add_argument("--maximum-range", type=float, default=15.0)
    parser.add_argument("--stall-rpm", type=float, default=2.0)
    parser.add_argument("--reverse-rpm", type=float, default=2.0)
    parser.add_argument("--maximum-stall", type=float, default=0.25)
    parser.add_argument("--maximum-reverse", type=float, default=0.10)
    parser.add_argument("--minimum-coverage", type=float, default=0.90)
    parser.add_argument("--minimum-window-coverage", type=float, default=0.90)
    parser.add_argument("--minimum-sample-hz", type=float, default=10.0)
    parser.add_argument("--maximum-scored-rpm", type=float, default=140.0)
    args = parser.parse_args()

    camera_offset = args.camera_offset_us / 1_000_000
    rows = camera_rows(args.camera_csv)
    windows = plateaus(args.motor_log, args.settle)
    if not windows:
        raise ValueError("motor profile contained no timestamped dwell windows")
    raw = [raw_measure(item, rows, camera_offset) for item in windows]
    if args.forward_sign is not None:
        forward_sign = args.forward_sign
    else:
        forward_rates = [
            float(item["raw_exact_rpm"])
            for window, item in zip(windows, raw, strict=True)
            if window.direction > 0 and abs(float(item["raw_exact_rpm"])) >= args.stall_rpm
        ]
        if not forward_rates:
            raise ValueError("profile has no forward plateau; pass --forward-sign from calibration")
        forward_sign = 1 if statistics.median(forward_rates) > 0 else -1

    measured = [
        qualify(window, rows, item, forward_sign, camera_offset, args)
        for window, item in zip(windows, raw, strict=True)
    ]
    for item in measured:
        print(json.dumps({"type": "physical_plateau", **item}, separators=(",", ":")))
    summary = summarize(measured, camera_offset, forward_sign)
    print(json.dumps(summary, separators=(",", ":")))
    return 0 if summary["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
