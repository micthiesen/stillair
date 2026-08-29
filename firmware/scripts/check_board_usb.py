#!/usr/bin/env python3
"""Permission-independent macOS check for PCB-01 native USB enumeration."""

from __future__ import annotations

import argparse
import glob
import plistlib
import subprocess
import sys
import time
from typing import Any, Iterator


ESPRESSIF_VID = 0x303A
USB_SERIAL_JTAG_PID = 0x1001

EXIT_PRESENT = 0
EXIT_NOT_DETECTED = 1
EXIT_INCONCLUSIVE = 2
EXIT_PROBE_ERROR = 3


def walk_registry(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_registry(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_registry(child)


def matching_devices(
    registry: Any, vendor_id: int = ESPRESSIF_VID, product_id: int = USB_SERIAL_JTAG_PID
) -> list[dict[str, Any]]:
    return [
        entry
        for entry in walk_registry(registry)
        if entry.get("idVendor") == vendor_id and entry.get("idProduct") == product_id
    ]


def read_usb_registry() -> Any:
    if sys.platform != "darwin":
        raise RuntimeError("this check requires macOS")
    try:
        result = subprocess.run(
            ["/usr/sbin/ioreg", "-p", "IOUSB", "-a"],
            check=True,
            capture_output=True,
            timeout=5,
        )
    except FileNotFoundError as error:
        raise RuntimeError("/usr/sbin/ioreg is unavailable") from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("ioreg did not return within 5 seconds") from error
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"ioreg failed: {detail or f'exit {error.returncode}'}") from error

    try:
        registry = plistlib.loads(result.stdout)
    except Exception as error:
        raise RuntimeError("ioreg returned an unreadable property list") from error

    classes = {entry.get("IOObjectClass") for entry in walk_registry(registry)}
    if not any(isinstance(name, str) and "USBXHCI" in name for name in classes):
        raise RuntimeError("the IOUSB registry contained no active USB host controller")
    return registry


def device_key(device: dict[str, Any]) -> tuple[Any, ...]:
    registry_id = device.get("IORegistryEntryID")
    if registry_id is not None:
        return ("registry", registry_id)
    return (
        "fallback",
        device.get("locationID"),
        device.get("USB Address"),
        device.get("USB Serial Number"),
    )


def property_text(device: dict[str, Any], *names: str) -> str:
    for name in names:
        value = device.get(name)
        if isinstance(value, bytes):
            return value.decode(errors="replace")
        if value not in (None, ""):
            return str(value)
    return "unknown"


def serial_ports() -> list[str]:
    patterns = (
        "/dev/cu.usbmodem*",
        "/dev/tty.usbmodem*",
    )
    return sorted({path for pattern in patterns for path in glob.glob(pattern)})


def parse_number(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected an integer such as 0x303a") from error


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check macOS I/O Registry for PCB-01's ESP32-C6 native USB Serial/JTAG device. "
            "This does not depend on serial-device permissions."
        )
    )
    parser.add_argument(
        "--wait",
        type=float,
        default=8.0,
        metavar="SECONDS",
        help="poll for this long before reporting not detected (default: 8)",
    )
    parser.add_argument(
        "--stable",
        type=float,
        default=0.5,
        metavar="SECONDS",
        help="require one registry entry to remain present this long (default: 0.5)",
    )
    parser.add_argument("--vid", type=parse_number, default=ESPRESSIF_VID, help=argparse.SUPPRESS)
    parser.add_argument(
        "--pid", type=parse_number, default=USB_SERIAL_JTAG_PID, help=argparse.SUPPRESS
    )
    args = parser.parse_args()

    if args.wait < 0 or args.stable < 0:
        parser.error("--wait and --stable must be non-negative")

    deadline = time.monotonic() + args.wait
    stable_key: tuple[Any, ...] | None = None
    stable_since: float | None = None
    saw_unstable_target = False

    while True:
        try:
            devices = matching_devices(read_usb_registry(), args.vid, args.pid)
        except RuntimeError as error:
            print(f"ERROR: USB probe unavailable: {error}", file=sys.stderr)
            print("No claim about PCB-01 USB state was made.", file=sys.stderr)
            return EXIT_PROBE_ERROR

        now = time.monotonic()
        if len(devices) > 1:
            print(
                f"INCONCLUSIVE: {len(devices)} devices match VID 0x{args.vid:04x}, "
                f"PID 0x{args.pid:04x}.",
                file=sys.stderr,
            )
            print("Disconnect other Espressif USB Serial/JTAG boards and rerun.", file=sys.stderr)
            return EXIT_INCONCLUSIVE

        if len(devices) == 1:
            saw_unstable_target = True
            key = device_key(devices[0])
            if key != stable_key:
                stable_key = key
                stable_since = now
            if stable_since is not None and now - stable_since >= args.stable:
                device = devices[0]
                print("PASS: PCB-01-class ESP32-C6 native USB enumerated in macOS I/O Registry.")
                print(
                    f"Identity: VID 0x{args.vid:04x}, PID 0x{args.pid:04x}, "
                    f"product {property_text(device, 'USB Product Name', 'kUSBProductString', 'IORegistryEntryName')}"
                )
                print(
                    f"Location: {property_text(device, 'locationID', 'IORegistryEntryLocation')}; "
                    f"registry entry {property_text(device, 'IORegistryEntryID')}"
                )
                ports = serial_ports()
                if ports:
                    print("Serial nodes: " + ", ".join(ports))
                else:
                    print(
                        "Serial node: not present yet. Enumeration still passed; driver, permission, "
                        "or startup state may affect /dev access."
                    )
                print("This identifies the USB device class. Disconnect other ESP boards if board identity matters.")
                return EXIT_PRESENT
        else:
            stable_key = None
            stable_since = None

        if now >= deadline:
            if saw_unstable_target:
                print(
                    f"INCONCLUSIVE: the target appeared but never remained enumerated for "
                    f"{args.stable:g} seconds.",
                    file=sys.stderr,
                )
                print("USB is unstable; this is not a pass.", file=sys.stderr)
                return EXIT_INCONCLUSIVE
            print(
                f"NOT DETECTED: no VID 0x{args.vid:04x}, PID 0x{args.pid:04x} device "
                f"enumerated during {args.wait:g} seconds.",
                file=sys.stderr,
            )
            print(
                "This result is independent of accessory and serial-port permissions. It does not "
                "distinguish power, cable, J6, U2 soldering, or U2 failure.",
                file=sys.stderr,
            )
            return EXIT_NOT_DETECTED
        time.sleep(0.1)


if __name__ == "__main__":
    raise SystemExit(main())
