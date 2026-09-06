#!/usr/bin/env python3
"""Check proposed footprint moves against every current board courtyard.

Proposal JSON maps each reference to ``[x_mm, y_mm, rotation_deg]``. This is
read-only and is retained only for legacy PCB-01 placement analysis. It is not a tscircuit-first
placement or update path.
"""

import argparse
import json
import os
from pathlib import Path

import board_model


def proposed_box(part, x: float, y: float, rotation: float) -> tuple[float, ...]:
    width, height = part.size
    if (rotation - part.rot) % 180 == 90:
        width, height = height, width
    return (x - width / 2, y - height / 2, x + width / 2, y + height / 2)


def overlaps(a: tuple[float, ...], b: tuple[float, ...], margin: float) -> bool:
    return not (
        a[2] + margin <= b[0]
        or b[2] + margin <= a[0]
        or a[3] + margin <= b[1]
        or b[3] + margin <= a[1]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("proposal", type=Path)
    parser.add_argument("--margin", type=float, default=0.1)
    args = parser.parse_args()

    os.environ["STILLAIR_BOARD"] = str(args.board.resolve())
    parts = board_model.load(str(args.board.resolve()))
    proposal = json.loads(args.proposal.read_text())
    missing = sorted(set(proposal) - parts.keys())
    if missing:
        raise SystemExit(f"unknown references: {', '.join(missing)}")

    boxes = {ref: part.abs_box() for ref, part in parts.items()}
    for ref, (x, y, rotation) in proposal.items():
        boxes[ref] = proposed_box(parts[ref], float(x), float(y), float(rotation))

    errors = []
    for ref, box in boxes.items():
        if ref in proposal and (
            box[0] < 50.3 or box[1] < 50.3 or box[2] > 137.7 or box[3] > 113.7
        ):
            errors.append(f"{ref}: outside board courtyard margin {box}")
    refs = sorted(boxes)
    for index, left in enumerate(refs):
        for right in refs[index + 1 :]:
            if left not in proposal and right not in proposal:
                continue
            if overlaps(boxes[left], boxes[right], args.margin):
                errors.append(f"{left} overlaps {right}")

    if errors:
        print(f"FAIL: {len(errors)} geometry conflicts")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"PASS: {len(proposal)} proposed moves have clear courtyards")


if __name__ == "__main__":
    main()
