#!/usr/bin/env python3
"""Print human-safe PCB-01 probing instructions from the retained probe map."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
MAP_PATH = REPO / "pcb" / "pcb-01" / "probe-map.json"


CLASS_SETUP = {
    "power24": {
        "dc": "DMM on DC volts. A scope requires a correctly configured x10 probe.",
        "scope": "Scope with a x10 probe; confirm the displayed attenuation and at least a 40 V capture range.",
    },
    "rail12": {
        "dc": "DMM on DC volts.",
        "scope": "Scope with x10 preferred, or x1 only if the selected range safely contains the rail.",
    },
    "rail3v3": {
        "dc": "DMM on DC volts.",
        "scope": "Scope with a x1 probe and a range that contains 0 to 3.3 V without clipping.",
    },
    "rail1v5": {
        "dc": "DMM on DC volts.",
        "scope": "Scope with a x1 probe and a low-voltage range that contains 0 to 1.5 V.",
    },
    "logic3v3": {
        "dc": "DMM on DC volts for a static state; use a scope for pulses or bus activity.",
        "scope": "Scope with a x1 probe and a range that contains 0 to 3.3 V without clipping.",
    },
    "analog3v3": {
        "dc": "DMM on DC volts for the mean level; use a scope for ripple or timing.",
        "scope": "Scope with a x1 probe and a range that contains 0 to 3.3 V without clipping.",
    },
    "power_ground": {
        "dc": "Use this as the DMM black-lead or power-domain scope reference, not as the measured target.",
        "scope": "Use this only as the power-domain scope reference.",
    },
    "analog_ground": {
        "dc": "Use this as the DMM black-lead or analog/logic scope reference, not as the measured target.",
        "scope": "Use this only as the analog/logic scope reference.",
    },
}


BOARD_MAP = r"""
PCB-01, component side, not to scale

  TOP: J5 / J6 USB-C
  +----------------------------------------------------------------+
  | H3   C1      C2      TP5  TP4       J5       TP26/28   J6   H4 |
  | TP1  J1/Q1       TP3                                           |
  |                   TP2       U3/TP9            ESP U2            |
  | D2   TP8/16   U1   TP12/7  TP20/17/18/19   TP22      TP23/21  |
  |                       TP11/24/27/10       U7/U9       TP6  J8  |
  | H1      C6/J2             J4                    J3          H2 |
  +----------------------------------------------------------------+
  BOTTOM: J2 / J4 / J3

Orientation check: C1/C2 are upper-left and J8 is lower-right.
""".strip()


def load_map() -> dict:
    return json.loads(MAP_PATH.read_text())


def normalize_net(net: str) -> str:
    return net.rsplit("/", 1)[-1]


def connector_diagram(ref: str, pins: dict[str, str]) -> str:
    if ref == "J8":
        return "\n".join(
            [
                "    inboard       board edge",
                f"  1 {pins['1']:<12}  2 {pins['2']}",
                f"  3 {pins['3']:<12}  4 {pins['4']}",
                f"  5 {pins['5']:<12}  6 {pins['6']}",
                f"  7 {pins['7']:<12}  8 {pins['8']}",
                f"  9 {pins['9']:<12} 10 {pins['10']}",
                "        top to bottom",
            ]
        )
    if ref == "J7":
        return "\n".join(
            [
                f"  top:     2 {pins['2']:<8}  4 {pins['4']:<8}  6 {pins['6']}",
                f"  bottom:  1 {pins['1']:<8}  3 {pins['3']:<8}  5 {pins['5']}",
            ]
        )
    return "  " + " | ".join(f"{pin} {net}" for pin, net in pins.items())


def show_connector(data: dict, ref: str) -> int:
    item = data["connectors"][ref]
    print(f"{ref} ({item['name']})")
    print("Board: Components up, large capacitors upper-left.")
    print(f"Find:  {item['location']}")
    print(f"Pins:  {item['orientation']}")
    print(connector_diagram(ref, item["pins"]))
    if ref == "J8":
        print("Wire:  Use a populated header or temporary pigtails for repeated work; do not keep hooking the bare pads.")
    else:
        print("Wire:  Use the matching test point instead when one exists.")
        print(f"Note:  {item['warning']}")
    return 0


def show_probe(data: dict, ref: str, mode: str) -> int:
    item = data["test_points"][ref]
    if item.get("available") is False:
        print(f"{ref} ({item['net']}) is unavailable on this board: {item['condition']}")
        print(f"Use {data['references'][item['net']]} instead.")
        return 1
    reference = item.get("reference")
    reference_net = (
        data["test_points"][reference]["net"] if reference in data["test_points"] else None
    )
    print(f"{ref} ({item['net']}), {mode}")
    print("Board:  Components up, large capacitors upper-left.")
    print(f"Find:   {item['location']}")

    if mode == "resistance":
        if reference:
            print(
                f"Clip:   With power and USB off and the board discharged, black to "
                f"{reference} ({reference_net}), red to {ref}. Use resistance mode."
            )
        else:
            print(f"Clip:   {ref} is a reference node; name the other node before measuring.")
        print("Wire:   Clip directly for one reading. Add a temporary pigtail only if the clip will not stay or we will repeat it.")
        print(
            "Expect: The reading may start low and climb as capacitors charge; it should not stay near 0 ohms."
        )
        print(f"Report: `{ref} to {reference or '<other>'}: initial __ ohm -> settled __ ohm; continuous beep yes/no`")
        return 0

    setup = CLASS_SETUP[item["class"]][mode]
    if reference:
        print(
            f"Clip:   With power off, ground/black to {reference} ({reference_net}); "
            f"tip/red to {ref}."
        )
    else:
        print(f"Clip:   {ref} is the {item['net']} reference node, not a signal target.")
    print(f"Meter:  {setup}")
    print("Wire:   Clip directly for one reading. Add a temporary pigtail for repeated captures or if the clip will not stay.")
    print(f"Expect: {item['expected']}")
    if mode == "scope":
        print("Report: capture plus min, max, mean, frequency if present, probe ratio, and ground point.")
    else:
        print(f"Report: `{ref} ({item['net']}): __ V, steady/rising/falling`")
    return 0


def list_targets(data: dict) -> int:
    for ref, item in data["test_points"].items():
        print(f"{ref:4}  {item['net']:<16}  {item['location']}")
    print("\nConnectors: " + " ".join(data["connectors"]))
    return 0


def verify_board(data: dict) -> int:
    sys.path.insert(0, str(REPO / "pcb" / "tools"))
    import board_model

    parts = board_model.load(str(REPO / data["source_board"]))
    errors: list[str] = []
    for ref, expected in data["test_points"].items():
        part = parts.get(ref)
        if part is None:
            errors.append(f"{ref}: missing from board")
            continue
        if abs(part.anchor[0] - expected["x_mm"]) > 0.01 or abs(part.anchor[1] - expected["y_mm"]) > 0.01:
            errors.append(f"{ref}: map coordinate differs from board {part.anchor}")
        nets = {normalize_net(net) for _, net, _, _ in part.pads if net}
        if normalize_net(expected["net"]) not in nets:
            errors.append(f"{ref}: map net {expected['net']} differs from board {sorted(nets)}")

    for ref, expected in data["connectors"].items():
        if ref == "J6":
            continue
        part = parts.get(ref)
        if part is None:
            errors.append(f"{ref}: missing from board")
            continue
        board_pins = {
            number: normalize_net(net)
            for number, net, _, _ in part.pads
            if number and number.isdigit() and net
        }
        for pin, net in expected["pins"].items():
            if board_pins.get(pin) != normalize_net(net):
                errors.append(f"{ref}.{pin}: map {net} differs from board {board_pins.get(pin)}")

    if errors:
        print("FAIL: probe map differs from the board:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        f"PASS: {len(data['test_points'])} test points and "
        f"{len(data['connectors']) - 1} pin-mapped connectors match PCB-01"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print standardized PCB-01 probe hookup and reporting instructions."
    )
    parser.add_argument("target", nargs="?", help="TP1..TP28, J1..J8, JP1, list, or map")
    parser.add_argument("--mode", choices=("dc", "resistance", "scope"), default="dc")
    parser.add_argument("--verify-board", action="store_true")
    args = parser.parse_args()
    data = load_map()

    if args.verify_board:
        return verify_board(data)
    if not args.target or args.target.lower() == "list":
        return list_targets(data)
    if args.target.lower() == "map":
        print(BOARD_MAP)
        return 0

    ref = args.target.upper()
    if ref in data["test_points"]:
        return show_probe(data, ref, args.mode)
    if ref in data["connectors"]:
        return show_connector(data, ref)
    parser.error(f"unknown target {args.target!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
