#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "numpy>=2.0",
#   "vds1022 @ git+https://github.com/florentbr/OWON-VDS1022.git@4c67805713906c20b4414b4225fd293adea4cb05#subdirectory=api/python",
# ]
# ///
"""Capture timestamped OWON frames without claiming that gaps are continuous data."""

from __future__ import annotations

import argparse
import json
import math
import signal
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np


API_COMMIT = "4c67805713906c20b4414b4225fd293adea4cb05"
ALLOWED_SIGNALS = {"SOX", "FG", "SPEED", "VM24", "DRVOFF", "NFAULT"}
FORBIDDEN_SIGNAL_FRAGMENTS = {"PHASE", "MOTOR_U", "MOTOR_V", "MOTOR_W", "LINE", "MAINS"}
STOP = False


@dataclass(frozen=True)
class Channel:
    number: int
    signal: str
    range: str
    offset: float
    probe: str
    coupling: str


@dataclass(frozen=True)
class Recipe:
    name: str
    sampling_rate: str
    frame_hz: float
    channels: tuple[Channel, Channel]
    trigger: dict[str, object]


def load_recipe(path: Path) -> Recipe:
    raw = json.loads(path.read_text())
    if raw.get("schema_version") != 1:
        raise ValueError("scope recipe schema_version must be 1")
    channels = tuple(Channel(**item) for item in raw.get("channels", []))
    if len(channels) != 2 or {item.number for item in channels} != {1, 2}:
        raise ValueError("scope recipe must define channels 1 and 2 exactly once")
    for channel in channels:
        signal_name = channel.signal.upper()
        if signal_name not in ALLOWED_SIGNALS or any(
            fragment in signal_name for fragment in FORBIDDEN_SIGNAL_FRAGMENTS
        ):
            raise ValueError(f"scope signal {channel.signal!r} is not permitted")
        if not 0 <= channel.offset <= 1:
            raise ValueError(f"channel {channel.number} offset must be within 0..=1")
        if channel.coupling.upper() not in {"AC", "DC"}:
            raise ValueError(f"channel {channel.number} coupling must be AC or DC")
    frame_hz = float(raw.get("frame_hz", 0))
    if not 0.1 <= frame_hz <= 20:
        raise ValueError("scope frame_hz must be within 0.1..=20")
    trigger = raw.get("trigger", {})
    if trigger and int(trigger.get("channel", 0)) not in {1, 2}:
        raise ValueError("scope trigger channel must be 1 or 2")
    return Recipe(
        name=str(raw.get("name") or path.stem),
        sampling_rate=str(raw["sampling_rate"]),
        frame_hz=frame_hz,
        channels=channels,  # type: ignore[arg-type]
        trigger=trigger,
    )


def stop_capture(_signum: int, _frame: object) -> None:
    global STOP
    STOP = True


def simulated_frames(recipe: Recipe, count: int) -> Iterator[tuple[int, np.ndarray, np.ndarray, np.ndarray]]:
    sample_rate = 250_000.0
    sample_count = 5_000
    x = (np.arange(sample_count, dtype=np.float32) - sample_count / 2) / sample_rate
    for index in range(count):
        epoch_ns = time.time_ns()
        ch1 = 1.65 + 0.08 * np.sin(2 * math.pi * 4_000 * x + index / 10)
        ch2 = (np.sin(2 * math.pi * 1_000 * x) > 0).astype(np.float32) * 3.3
        yield epoch_ns, x, ch1.astype(np.float32), ch2


def hardware_frames(recipe: Recipe) -> tuple[dict[str, object], Iterator[tuple[int, np.ndarray, np.ndarray, np.ndarray]]]:
    from vds1022 import AC, AUTO, CH1, CH2, DC, EDGE, RISE, VDS1022

    device = VDS1022(debug=False)
    device.set_sampling(recipe.sampling_rate)
    for channel in recipe.channels:
        device.set_channel(
            CH1 if channel.number == 1 else CH2,
            range=channel.range,
            offset=channel.offset,
            probe=channel.probe,
            coupling=DC if channel.coupling.upper() == "DC" else AC,
        )
    if recipe.trigger:
        trigger_channel = CH1 if int(recipe.trigger["channel"]) == 1 else CH2
        device.set_trigger(
            trigger_channel,
            EDGE,
            RISE,
            position=float(recipe.trigger.get("position", 0.5)),
            level=recipe.trigger.get("level", "1v"),
            sweep=AUTO,
        )

    def iterator() -> Iterator[tuple[int, np.ndarray, np.ndarray, np.ndarray]]:
        try:
            for frames in device.fetch_iter(freq=recipe.frame_hz):
                yield (
                    round(frames.time() * 1_000_000_000),
                    np.asarray(frames.x(), dtype=np.float32).copy(),
                    np.asarray(frames.ch1.y(), dtype=np.float32).copy(),
                    np.asarray(frames.ch2.y(), dtype=np.float32).copy(),
                )
                if STOP:
                    break
        finally:
            device.dispose()

    return {
        "model": "VDS1022I-owner-confirmed",
        "hardware_version": device.version,
        "serial": device.serial,
        "api_commit": API_COMMIT,
    }, iterator()


def capture(
    recipe: Recipe,
    output: Path,
    *,
    seconds: float,
    frame_limit: int | None,
    ready_file: Path | None,
    simulate: bool,
) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=False)
    started_ns = time.time_ns()
    if simulate:
        device = {"model": "simulated", "serial": "simulation", "api_commit": API_COMMIT}
        source = simulated_frames(recipe, frame_limit or max(1, round(seconds * recipe.frame_hz)))
    else:
        device, source = hardware_frames(recipe)
    metadata = {
        "type": "owon_scope_capture",
        "schema_version": 1,
        "started_epoch_ns": started_ns,
        "recipe": {
            "name": recipe.name,
            "sampling_rate": recipe.sampling_rate,
            "frame_hz": recipe.frame_hz,
            "channels": [channel.__dict__ for channel in recipe.channels],
            "trigger": recipe.trigger,
        },
        "device": device,
        "continuity": "discrete_frames_with_unknown_interframe_data",
    }
    (output / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")

    deadline = time.monotonic() + seconds
    previous_epoch_ns: int | None = None
    largest_gap_ms = 0.0
    frames_written = 0
    with (output / "frames.jsonl").open("w") as manifest:
        for epoch_ns, x, ch1, ch2 in source:
            if STOP or (frame_limit is None and time.monotonic() >= deadline):
                break
            if len(x) < 2 or len(ch1) != len(x) or len(ch2) != len(x):
                raise ValueError("scope returned inconsistent channel arrays")
            frames_written += 1
            frame_name = f"frame-{frames_written:06d}.npz"
            np.savez_compressed(output / frame_name, time_s=x, ch1_v=ch1, ch2_v=ch2)
            gap_ms = 0.0 if previous_epoch_ns is None else (epoch_ns - previous_epoch_ns) / 1_000_000
            largest_gap_ms = max(largest_gap_ms, gap_ms)
            previous_epoch_ns = epoch_ns
            sample_rate = float(1 / np.median(np.diff(x)))
            record = {
                "sequence": frames_written,
                "file": frame_name,
                "epoch_ns": epoch_ns,
                "arrival_gap_ms": round(gap_ms, 3),
                "samples": len(x),
                "sample_rate_hz": round(sample_rate, 3),
                "ch1_min_v": round(float(np.min(ch1)), 6),
                "ch1_max_v": round(float(np.max(ch1)), 6),
                "ch1_rms_v": round(float(np.sqrt(np.mean(np.square(ch1)))), 6),
                "ch2_min_v": round(float(np.min(ch2)), 6),
                "ch2_max_v": round(float(np.max(ch2)), 6),
                "ch2_rms_v": round(float(np.sqrt(np.mean(np.square(ch2)))), 6),
            }
            manifest.write(json.dumps(record, separators=(",", ":")) + "\n")
            manifest.flush()
            if frames_written == 1 and ready_file is not None:
                ready_file.write_text("ready\n")
            if frame_limit is not None and frames_written >= frame_limit:
                break
    if frames_written == 0:
        raise RuntimeError("scope capture produced no frames")
    summary = {
        "type": "owon_scope_summary",
        "frames": frames_written,
        "largest_arrival_gap_ms": round(largest_gap_ms, 3),
        "ended_epoch_ns": time.time_ns(),
        "continuity": "discrete_frames_with_unknown_interframe_data",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=float, required=True)
    parser.add_argument("--frames", type=int)
    parser.add_argument("--ready-file", type=Path)
    parser.add_argument("--simulate", action="store_true")
    args = parser.parse_args()
    if args.seconds <= 0 or args.frames is not None and args.frames <= 0:
        parser.error("seconds and frames must be positive")
    signal.signal(signal.SIGINT, stop_capture)
    signal.signal(signal.SIGTERM, stop_capture)
    summary = capture(
        load_recipe(args.recipe),
        args.output,
        seconds=args.seconds,
        frame_limit=args.frames,
        ready_file=args.ready_file,
        simulate=args.simulate,
    )
    print(json.dumps(summary, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
