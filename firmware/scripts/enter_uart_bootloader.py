#!/usr/bin/env python3
"""Enter the ESP32-C6 UART ROM bootloader through RTS plus Kasa power control."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable


FTDI_VID = 0x0403
FTDI_PID = 0x6001


def find_adapter_port() -> str:
    from serial.tools import list_ports

    matches = [
        port.device
        for port in list_ports.comports()
        if port.vid == FTDI_VID and port.pid == FTDI_PID and port.device.startswith("/dev/cu.")
    ]
    if len(matches) != 1:
        raise RuntimeError(
            "expected exactly one FTDI FT232 USB-UART callout port; "
            f"found {len(matches)}: {', '.join(matches) or 'none'}"
        )
    return matches[0]


def open_adapter(port: str):
    import serial

    return serial.Serial(port, 115_200, timeout=0.2, exclusive=True)


def set_utility_plug(
    utility_plug: Path,
    action: str,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> None:
    completed = run(
        [str(utility_plug), action],
        check=True,
        capture_output=True,
        text=True,
    )
    reports = []
    for line in completed.stdout.splitlines():
        try:
            reports.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    expected = action == "on"
    if not reports or reports[-1].get("on") is not expected:
        raise RuntimeError(f"Utility Plug did not verify {action}: {completed.stdout.strip()}")


def enter_bootloader(
    port: str,
    utility_plug: Path,
    *,
    serial_factory: Callable[[str], object] = open_adapter,
    plug_setter: Callable[[Path, str], None] = set_utility_plug,
    pause: Callable[[float], None] = time.sleep,
) -> None:
    """Assert active-low RTS during cold power-up, then leave the ROM loader running."""
    plug_setter(utility_plug, "off")
    adapter = None
    try:
        adapter = serial_factory(port)
        # PySerial's logical True asserts FTDI RTS#, which drives the labeled RTS pin low.
        adapter.rts = False
        adapter.reset_input_buffer()
        adapter.reset_output_buffer()
        adapter.rts = True
        pause(0.1)
        plug_setter(utility_plug, "on")
        pause(0.35)
        adapter.rts = False
        pause(0.1)
    except BaseException:
        if adapter is not None:
            try:
                adapter.rts = False
            except Exception:
                pass
        try:
            plug_setter(utility_plug, "off")
        except Exception:
            pass
        raise
    finally:
        if adapter is not None:
            adapter.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cold-enter PCB-01's UART ROM bootloader using D/BOOT on adapter RTS."
    )
    parser.add_argument("--port", help="FTDI callout port; auto-detected when omitted")
    parser.add_argument(
        "--print-port",
        action="store_true",
        help="print the uniquely detected FTDI callout port without changing hardware state",
    )
    parser.add_argument(
        "--utility-plug",
        type=Path,
        default=Path(__file__).with_name("utility-plug.sh"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        port = args.port or find_adapter_port()
        if args.print_port:
            print(port)
            return 0
        if not args.utility_plug.is_file():
            raise RuntimeError(f"Utility Plug controller not found: {args.utility_plug}")
        enter_bootloader(port, args.utility_plug)
        print(json.dumps({"event": "uart_rom_bootloader_ready", "port": port}))
        return 0
    except Exception as error:
        print(f"UART bootloader entry failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
