#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "numpy>=2.0",
# ]
# ///
"""Measure fixed-microphone audio during every settled stream/dwell profile window."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

from analyze_motor_audio import decode, metrics


COMMAND = re.compile(r"^# t=([0-9.]+)s (.+)$")
RUN = re.compile(r"^run ([0-9]+)$")
STREAM = re.compile(r"^stream [0-9]+ --for ([0-9]+)$")
DWELL = re.compile(r"^dwell ([0-9]+)$")


@dataclass(frozen=True)
class Window:
    label: str
    start: float
    end: float


def profile_windows(
    motor_log: Path,
    audio_offset_s: float,
    *,
    trim_start_s: float = 2,
    trim_end_s: float = 1,
) -> list[Window]:
    rpm: int | None = None
    sequence = 0
    windows: list[Window] = []
    for raw in motor_log.read_text().splitlines():
        match = COMMAND.match(raw)
        if not match:
            continue
        at = float(match.group(1))
        command = match.group(2)
        if run := RUN.match(command):
            rpm = int(run.group(1))
            continue
        measured = STREAM.match(command) or DWELL.match(command)
        if measured is None or rpm is None:
            continue
        duration = float(measured.group(1))
        start = audio_offset_s + at + trim_start_s
        end = audio_offset_s + at + duration - trim_end_s
        if end <= start:
            raise ValueError(f"{command}: trim removes the complete audio window")
        sequence += 1
        windows.append(Window(f"{rpm}rpm-{sequence}", start, end))
    if not windows:
        raise ValueError("motor log contains no speed-labelled stream or dwell windows")
    return windows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("motor_log", type=Path)
    parser.add_argument("recording", type=Path)
    parser.add_argument("--audio-start-ns", type=int, required=True)
    parser.add_argument("--motor-start-ns", type=int, required=True)
    parser.add_argument("--sample-rate", type=int, default=48_000)
    parser.add_argument("--trim-start", type=float, default=2)
    parser.add_argument("--trim-end", type=float, default=1)
    args = parser.parse_args()
    offset = (args.motor_start_ns - args.audio_start_ns) / 1_000_000_000
    samples = decode(args.recording, args.sample_rate)
    windows = profile_windows(
        args.motor_log,
        offset,
        trim_start_s=args.trim_start,
        trim_end_s=args.trim_end,
    )
    for window in windows:
        print(
            json.dumps(
                metrics(samples, window.label, window.start, window.end, args.sample_rate),
                separators=(",", ":"),
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
