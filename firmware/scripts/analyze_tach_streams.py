#!/usr/bin/env python3
"""Validate sampled Hall-period and MCF FG telemetry blocks from a hardware script log."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from pathlib import Path

RUN = re.compile(r"^# t=[0-9.]+s run ([0-9]+)$")
STREAM = re.compile(r"^# t=[0-9.]+s stream ([0-9]+) --for ([0-9]+)$")


def summarize(path: Path) -> list[dict[str, object]]:
    target = 0
    rate_hz = 0
    duration = 0
    header: list[str] | None = None
    rows: list[dict[str, str]] = []
    results: list[dict[str, object]] = []

    def finish() -> None:
        nonlocal rows, header
        if not rows:
            header = None
            return
        numeric_fields = ("t_ms", "tgt_mrpm", "cmd_mrpm", "fg_mrpm", "hall_mrpm", "dropped")
        valid = [row for row in rows if all(row.get(field, "").isdigit() for field in numeric_fields)]
        invalid_rows = len(rows) - len(valid)
        if not valid:
            raise ValueError("telemetry block contains no complete tach rows")
        timestamps = [int(row["t_ms"]) for row in valid]
        fg = [int(row["fg_mrpm"]) / 1_000 for row in valid]
        hall = [int(row["hall_mrpm"]) / 1_000 for row in valid]
        faults = sorted({row["fault"] for row in valid if row["fault"] != "null"})
        coverage_s = (timestamps[-1] - timestamps[0]) / 1_000 + 1 / rate_hz
        gaps_ms = [later - earlier for earlier, later in zip(timestamps, timestamps[1:])]
        maximum_gap_ms = max(gaps_ms, default=0)
        fg_mean = statistics.fmean(fg)
        hall_mean = statistics.fmean(hall)
        dropped = [int(row["dropped"]) for row in valid]
        minimum_samples = max(2, math.floor(rate_hz * duration * 0.75))
        failures = []
        if invalid_rows:
            failures.append("invalid_rows")
        if len(valid) < minimum_samples or coverage_s < duration * 0.75:
            failures.append("insufficient_coverage")
        if maximum_gap_ms > max(500, math.ceil(4_000 / rate_hz)):
            failures.append("telemetry_gap")
        if any(row["state"] != "running" or row["on"] != "true" for row in valid):
            failures.append("not_running")
        if faults:
            failures.append("fault")
        if any(value <= 0 for value in hall):
            failures.append("hall_missing")
        if max(dropped) != min(dropped):
            failures.append("output_dropped")
        if abs(fg_mean - hall_mean) > 5.0:
            failures.append("fg_hall_disagreement")
        if abs(fg_mean - target) > 5.0 or abs(hall_mean - target) > 5.0:
            failures.append("target_error")
        results.append(
            {
                "type": "tach_plateau",
                "target_rpm": target,
                "rate_hz": rate_hz,
                "declared_duration_s": duration,
                "samples": len(valid),
                "invalid_rows": invalid_rows,
                "coverage_s": round(coverage_s, 3),
                "maximum_gap_ms": maximum_gap_ms,
                "hall_period_samples": len(hall),
                "fg_mean_rpm": round(fg_mean, 3),
                "fg_stddev_rpm": round(statistics.pstdev(fg), 3),
                "fg_range_rpm": round(max(fg) - min(fg), 3),
                "hall_mean_rpm": round(hall_mean, 3),
                "hall_stddev_rpm": round(statistics.pstdev(hall), 3),
                "hall_range_rpm": round(max(hall) - min(hall), 3),
                "fg_hall_mean_error_rpm": round(fg_mean - hall_mean, 3),
                "dropped_delta": max(dropped) - min(dropped),
                "faults": faults,
                "qualified": not failures,
                "failures": failures,
            }
        )
        if failures:
            raise ValueError(
                f"{target} RPM tach block failed validation: {', '.join(failures)}"
            )
        rows = []
        header = None

    for line in path.read_text().splitlines():
        if match := RUN.match(line):
            finish()
            target = int(match.group(1))
            continue
        if match := STREAM.match(line):
            finish()
            rate_hz = int(match.group(1))
            duration = int(match.group(2))
            continue
        if line.startswith("t_ms,state,fault,on,"):
            finish()
            header = next(csv.reader([line]))
            continue
        if header is not None and line and line[0].isdigit():
            values = next(csv.reader([line]))
            if len(values) == len(header):
                rows.append(dict(zip(header, values)))
            continue
        if header is not None and line.startswith("# t="):
            finish()
    finish()
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("motor_log", type=Path)
    args = parser.parse_args()
    results = summarize(args.motor_log)
    if not results:
        raise SystemExit("no telemetry stream blocks found")
    for result in results:
        print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
