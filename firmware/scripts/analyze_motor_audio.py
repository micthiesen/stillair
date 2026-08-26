#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "numpy>=2.0",
# ]
# ///
"""Compare synchronized motor-audio windows without treating room sound as motor evidence."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16_000


def parse_window(value: str) -> tuple[str, float, float]:
    try:
        label, start, end = value.split(",", 2)
        parsed = (label, float(start), float(end))
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected LABEL,START_S,END_S") from error
    if not label or parsed[1] < 0 or parsed[2] <= parsed[1]:
        raise argparse.ArgumentTypeError("audio window must have a label and positive duration")
    return parsed


def decode(path: Path, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    result = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "f32le",
            "pipe:1",
        ],
        check=True,
        capture_output=True,
    )
    samples = np.frombuffer(result.stdout, dtype="<f4")
    if len(samples) < sample_rate:
        raise ValueError("recording contains less than one second of audio")
    return samples


def db(value: float) -> float:
    return 10 * math.log10(max(value, 1e-20))


def spectral_peaks(
    frequencies: np.ndarray,
    spectrum: np.ndarray,
    low_hz: float,
    high_hz: float,
    *,
    count: int = 8,
) -> list[dict[str, float]]:
    eligible = (frequencies >= low_hz) & (frequencies <= high_hz)
    indices = np.flatnonzero(eligible)
    if len(indices) == 0:
        return []
    ordered = indices[np.argsort(spectrum[indices])[-count:]][::-1]
    reference = db(float(np.max(spectrum[eligible])))
    return [
        {
            "hz": round(float(frequencies[index]), 2),
            "relative_db": round(db(float(spectrum[index])) - reference, 2),
        }
        for index in ordered
    ]


def envelope_metrics(per_frame_power: np.ndarray, frame_rate: float) -> dict[str, float]:
    power_db = np.asarray([db(float(value)) for value in per_frame_power])
    centered = power_db - np.mean(power_db)
    frequencies = np.fft.rfftfreq(len(centered), 1 / frame_rate)
    spectrum = np.abs(np.fft.rfft(centered * np.hanning(len(centered)))) ** 2
    eligible = (frequencies >= 0.15) & (frequencies <= min(10.0, frame_rate / 2))
    modulation_hz = 0.0
    if np.any(eligible) and float(np.max(spectrum[eligible])) > 1e-12:
        candidates = np.flatnonzero(eligible)
        modulation_hz = float(frequencies[candidates[np.argmax(spectrum[candidates])]])
    return {
        "p95_minus_median_db": round(float(np.percentile(power_db, 95) - np.median(power_db)), 2),
        "stddev_db": round(float(np.std(power_db)), 2),
        "dominant_modulation_hz": round(modulation_hz, 3),
    }


def metrics(
    samples: np.ndarray,
    label: str,
    start: float,
    end: float,
    sample_rate: int = SAMPLE_RATE,
) -> dict[str, object]:
    selected = samples[round(start * sample_rate) : round(end * sample_rate)]
    if len(selected) < 4_096:
        raise ValueError(f"{label}: audio window contains fewer than 4096 samples")
    selected = selected - np.mean(selected)
    frame_size = 8_192 if sample_rate >= 32_000 else 2_048
    hop = frame_size // 4
    frame_count = 1 + (len(selected) - frame_size) // hop
    frames = np.lib.stride_tricks.sliding_window_view(selected, frame_size)[::hop][:frame_count]
    spectra = np.abs(np.fft.rfft(frames * np.hanning(frame_size), axis=1)) ** 2
    frequencies = np.fft.rfftfreq(frame_size, 1 / sample_rate)
    mean_spectrum = np.mean(spectra, axis=0)
    total_power = float(np.mean(selected * selected))

    band_limits = [
        ("sub_200", 20, 200),
        ("grind_200_500", 200, 500),
        ("mid_500_2000", 500, 2_000),
        ("high_2000_7500", 2_000, 7_500),
    ]
    if sample_rate / 2 > 7_500:
        band_limits.append(
            ("upper_7500_20000", 7_500, min(20_000, sample_rate / 2))
        )

    bands = {}
    for name, low, high in band_limits:
        mask = (frequencies >= low) & (frequencies < high)
        per_frame = np.mean(spectra[:, mask], axis=1)
        bands[name] = {
            "mean_db": round(db(float(np.mean(per_frame))), 2),
            **envelope_metrics(per_frame, sample_rate / hop),
        }

    return {
        "type": "motor_audio_window",
        "label": label,
        "start_s": start,
        "end_s": end,
        "sample_rate_hz": sample_rate,
        "rms_dbfs": round(db(total_power), 2),
        "crest_db": round(20 * math.log10(max(float(np.max(np.abs(selected))), 1e-10) / math.sqrt(max(total_power, 1e-20))), 2),
        "bands": bands,
        "low_peaks": spectral_peaks(frequencies, mean_spectrum, 40, 1_000),
        "electrical_peaks": spectral_peaks(
            frequencies, mean_spectrum, 1_000, min(20_000, sample_rate / 2)
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("recording", type=Path)
    parser.add_argument("--window", action="append", type=parse_window, required=True)
    parser.add_argument("--sample-rate", type=int, default=48_000)
    args = parser.parse_args()
    if not 8_000 <= args.sample_rate <= 96_000:
        parser.error("sample rate must be within 8000..=96000")
    samples = decode(args.recording, args.sample_rate)
    for label, start, end in args.window:
        print(
            json.dumps(
                metrics(samples, label, start, end, args.sample_rate), separators=(",", ":")
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
