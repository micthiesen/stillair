#!/usr/bin/env python3
"""Align Utility Plug AC measurements with timestamped motor-profile dwells."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from analyze_profile_plateaus import Plateau, plateaus

WALL_START = "# wall_start="


@dataclass(frozen=True)
class PowerSample:
    timestamp: datetime
    volts: float
    amps: float
    watts: float


def wall_start(path: Path) -> datetime:
    for line in path.read_text().splitlines():
        if line.startswith(WALL_START):
            parsed = datetime.fromisoformat(line.removeprefix(WALL_START).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
    raise ValueError("motor log has no # wall_start synchronization marker")


def power_samples(path: Path) -> list[PowerSample]:
    samples: list[PowerSample] = []
    for line in path.read_text().splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("type") != "utility_plug" or item.get("event") != "sample":
            continue
        if not item.get("on"):
            continue
        try:
            timestamp = datetime.fromisoformat(str(item["timestamp"]).replace("Z", "+00:00"))
            values = (float(item["volts"]), float(item["amps"]), float(item["watts"]))
            if not all(math.isfinite(value) for value in values):
                continue
            samples.append(PowerSample(timestamp=timestamp, volts=values[0], amps=values[1], watts=values[2]))
        except (KeyError, TypeError, ValueError):
            continue
    if not samples:
        raise ValueError("power log has no usable relay-on samples")
    return sorted(samples, key=lambda item: item.timestamp)


def validate_coverage(
    samples: list[PowerSample],
    anchor: datetime,
    start_s: float,
    end_s: float,
    *,
    minimum_samples: int = 2,
    maximum_gap_s: float = 3.0,
) -> float:
    if len(samples) < minimum_samples:
        raise ValueError(
            f"only {len(samples)} power samples from {start_s:.3f}s through {end_s:.3f}s"
        )
    offsets = [(item.timestamp - anchor).total_seconds() for item in samples]
    gaps = [offsets[0] - start_s, end_s - offsets[-1]]
    gaps.extend(later - earlier for earlier, later in zip(offsets, offsets[1:]))
    maximum_gap = max(gaps)
    if maximum_gap > maximum_gap_s:
        raise ValueError(
            f"power evidence gap {maximum_gap:.3f}s exceeds {maximum_gap_s:.3f}s"
        )
    return maximum_gap


def measure(
    plateau: Plateau,
    anchor: datetime,
    samples: list[PowerSample],
) -> dict[str, object]:
    selected = [
        item
        for item in samples
        if plateau.start_s <= (item.timestamp - anchor).total_seconds() < plateau.end_s
    ]
    maximum_gap_s = validate_coverage(selected, anchor, plateau.start_s, plateau.end_s)
    watts = [item.watts for item in selected]
    amps = [item.amps for item in selected]
    volts = [item.volts for item in selected]
    result: dict[str, object] = {
        "type": "power_plateau",
        "target_rpm": plateau.target_rpm,
        "direction": "forward" if plateau.direction > 0 else "reverse",
        "start_s": round(plateau.start_s, 3),
        "end_s": round(plateau.end_s, 3),
        "samples": len(selected),
        "maximum_gap_s": round(maximum_gap_s, 3),
        "mean_watts": round(statistics.fmean(watts), 4),
        "min_watts": round(min(watts), 4),
        "max_watts": round(max(watts), 4),
        "mean_amps": round(statistics.fmean(amps), 5),
        "mean_volts": round(statistics.fmean(volts), 3),
    }
    duration = plateau.end_s - plateau.start_s
    if duration >= 120:
        minute_means = []
        for minute in range(int(duration // 60)):
            start_s = plateau.start_s + minute * 60
            end_s = start_s + 60
            bucket = [
                item
                for item in selected
                if start_s <= (item.timestamp - anchor).total_seconds() < end_s
            ]
            validate_coverage(
                bucket,
                anchor,
                start_s,
                end_s,
                minimum_samples=45,
            )
            minute_means.append(round(statistics.fmean(item.watts for item in bucket), 4))
        result["minute_mean_watts"] = minute_means
        result["last_minus_first_minute_watts"] = round(
            minute_means[-1] - minute_means[0], 4
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("motor_log", type=Path)
    parser.add_argument("power_log", type=Path)
    parser.add_argument("--settle", type=float, default=2.0)
    args = parser.parse_args()

    anchor = wall_start(args.motor_log)
    windows = plateaus(args.motor_log, args.settle)
    if not windows:
        raise ValueError("motor profile contained no timestamped dwell windows")
    samples = power_samples(args.power_log)
    measured = [measure(item, anchor, samples) for item in windows]
    for item in measured:
        print(json.dumps(item, separators=(",", ":")))
    means = [float(item["mean_watts"]) for item in measured]
    print(
        json.dumps(
            {
                "type": "power_plateau_summary",
                "plateaus": len(measured),
                "mean_watts": round(statistics.fmean(means), 4),
                "maximum_watts": round(max(float(item["max_watts"]) for item in measured), 4),
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
