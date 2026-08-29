#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("check_board_usb.py")
SPEC = importlib.util.spec_from_file_location("check_board_usb", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
usb = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(usb)


class RegistryMatchingTests(unittest.TestCase):
    def test_finds_only_exact_espressif_serial_jtag_identity(self) -> None:
        target = {
            "idVendor": 0x303A,
            "idProduct": 0x1001,
            "IORegistryEntryID": 42,
        }
        registry = {
            "IORegistryEntryChildren": [
                target,
                {"idVendor": 0x303A, "idProduct": 0x0002},
                {"idVendor": 0x1234, "idProduct": 0x1001},
            ]
        }
        self.assertEqual(usb.matching_devices(registry), [target])

    def test_nested_registry_is_walked(self) -> None:
        target = {"idVendor": 0x303A, "idProduct": 0x1001}
        registry = {"children": [{"interfaces": [target]}]}
        self.assertEqual(usb.matching_devices(registry), [target])

    def test_missing_target_does_not_match(self) -> None:
        registry = {"children": [{"idVendor": 0x303A}]}
        self.assertEqual(usb.matching_devices(registry), [])


if __name__ == "__main__":
    unittest.main()
