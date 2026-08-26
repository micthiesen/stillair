#!/usr/bin/env python3
"""Reject a loaded tuning profile before any command can reach the installed fan."""

from __future__ import annotations

import argparse
import json
import shlex
from dataclasses import dataclass
from pathlib import Path


MIN_RPM = 50
MAX_RPM = 170
CANDIDATES = frozenset(
    line
    for line in Path(__file__).with_name("loaded-tune-candidates.txt").read_text().splitlines()
    if line
)


@dataclass(frozen=True)
class Command:
    line: int
    words: tuple[str, ...]
    optional: bool


def commands(path: Path) -> list[Command]:
    parsed: list[Command] = []
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        text = raw.split("#", 1)[0].strip()
        if not text:
            continue
        optional = text.startswith("-")
        if optional:
            text = text[1:].strip()
        words = tuple(shlex.split(text))
        if words:
            parsed.append(Command(number, words, optional))
    if not parsed:
        raise ValueError("profile contains no commands")
    return parsed


def integer(command: Command, index: int, label: str) -> int:
    try:
        return int(command.words[index])
    except (IndexError, ValueError) as error:
        raise ValueError(f"line {command.line}: {label} must be an integer") from error


def flag_integer(command: Command, flag: str, default: int) -> int:
    if flag not in command.words:
        return default
    index = command.words.index(flag) + 1
    return integer(command, index, flag)


def duration_seconds(command: Command) -> int:
    words = command.words
    if words[0] == "dwell":
        return integer(command, 1, "dwell duration")
    if words[0] == "stream" and len(words) > 1 and words[1].isdigit():
        return flag_integer(command, "--for", 10)
    if words[:2] == ("speed", "sample") or words[:2] == ("estimator", "sample"):
        return flag_integer(command, "--for", 10)
    if words[0] == "wait":
        return flag_integer(command, "--for", 60)
    if words[:2] == ("mpet", "run"):
        return flag_integer(command, "--for", 120)
    return 0


def validate(path: Path, mode: str, candidate: str | None = None) -> dict[str, object]:
    parsed = commands(path)
    errors: list[str] = []
    measurement_count = 0
    last_actuation: Command | None = None
    stopped_wait_after_last_stop = False

    if mode == "verified" and parsed[0].words[:2] != ("config", "check"):
        errors.append("verified profiles must begin with `config check`")
    if mode == "candidate" and candidate not in CANDIDATES:
        errors.append(f"unknown loaded tuning candidate {candidate!r}")

    for index, command in enumerate(parsed):
        words = command.words
        prefix = f"line {command.line}"
        if command.optional and words[0] in {"run", "pct", "dir", "stop", "disarm"}:
            errors.append(f"{prefix}: motor commands may not be optional")

        if words[:2] in {
            ("config", "apply"),
            ("config", "stage"),
            ("config", "tune"),
        }:
            errors.append(f"{prefix}: loaded profiles may not stage or commit configuration")
        if mode == "candidate" and words[:2] == ("config", "check"):
            errors.append(f"{prefix}: the candidate wrapper owns configuration verification")
        if words[:2] == ("reg", "write"):
            errors.append(f"{prefix}: raw configuration writes are not a loaded tuning mode")

        if words[0] == "run":
            rpm = integer(command, 1, "run RPM")
            if not MIN_RPM <= rpm <= MAX_RPM:
                errors.append(f"{prefix}: run RPM {rpm} is outside {MIN_RPM}..={MAX_RPM}")
            last_actuation = command
            stopped_wait_after_last_stop = False
        elif words[0] == "pct":
            percent = integer(command, 1, "percent")
            if not 0 <= percent <= 100:
                errors.append(f"{prefix}: percent must be within 0..=100")
            last_actuation = command
            stopped_wait_after_last_stop = percent == 0
        elif words[0] in {"stop", "disarm"}:
            last_actuation = command
            stopped_wait_after_last_stop = False
        elif words[:2] == ("wait", "idle_off") and last_actuation is not None:
            if last_actuation.words[0] in {"stop", "disarm"} or last_actuation.words[:2] == (
                "pct",
                "0",
            ):
                stopped_wait_after_last_stop = True

        if words[0] == "dir":
            prior = parsed[index - 1] if index else None
            if prior is None or prior.words[:2] != ("wait", "idle_off"):
                errors.append(f"{prefix}: direction changes require an immediately preceding `wait idle_off`")

        if words[0] in {"dwell", "stream"} or words[:2] in {
            ("speed", "sample"),
            ("estimator", "sample"),
        }:
            measurement_count += 1

    if last_actuation is None:
        errors.append("profile never commands the fan")
    elif last_actuation.words[0] not in {"stop", "disarm"} and last_actuation.words[:2] != (
        "pct",
        "0",
    ):
        errors.append("profile must end its actuation sequence with stop, disarm, or pct 0")
    elif not stopped_wait_after_last_stop:
        errors.append("profile must verify `wait idle_off` after its final stop")
    if measurement_count == 0:
        errors.append("profile contains no telemetry or estimator measurement window")

    if errors:
        raise ValueError("\n".join(errors))

    result: dict[str, object] = {
        "type": "loaded_profile_validation",
        "profile": str(path),
        "mode": mode,
        "commands": len(parsed),
        "measurement_windows": measurement_count,
        "worst_case_seconds": sum(duration_seconds(command) for command in parsed) + 60,
        "rpm_min": MIN_RPM,
        "rpm_max": MAX_RPM,
    }
    if candidate is not None:
        result["candidate"] = candidate
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--mode", choices=("verified", "candidate"), default="verified")
    parser.add_argument("--candidate")
    args = parser.parse_args()
    print(
        json.dumps(
            validate(args.profile, args.mode, args.candidate), separators=(",", ":")
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
