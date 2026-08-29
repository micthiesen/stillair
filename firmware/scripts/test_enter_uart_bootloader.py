#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("enter_uart_bootloader.py")
SPEC = importlib.util.spec_from_file_location("enter_uart_bootloader", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FakeAdapter:
    def __init__(self):
        self.events: list[object] = []
        self._rts = False

    @property
    def rts(self):
        return self._rts

    @rts.setter
    def rts(self, value):
        self._rts = value
        self.events.append(("rts", value))

    def reset_input_buffer(self):
        self.events.append("reset_input")

    def reset_output_buffer(self):
        self.events.append("reset_output")

    def close(self):
        self.events.append("close")


class EnterBootloaderTests(unittest.TestCase):
    def test_asserts_rts_only_across_verified_power_on(self):
        adapter = FakeAdapter()
        events: list[object] = []

        def plug(_path, action):
            events.append(("plug", action, adapter.rts))

        MODULE.enter_bootloader(
            "/dev/cu.test",
            Path("utility-plug.sh"),
            serial_factory=lambda _port: adapter,
            plug_setter=plug,
            pause=lambda seconds: events.append(("pause", seconds, adapter.rts)),
        )

        self.assertEqual(events[0], ("plug", "off", False))
        self.assertIn(("plug", "on", True), events)
        self.assertEqual(adapter.events[-2:], [("rts", False), "close"])

    def test_failure_releases_rts_and_returns_power_off(self):
        adapter = FakeAdapter()
        plug_actions: list[str] = []

        def plug(_path, action):
            plug_actions.append(action)
            if action == "on":
                raise RuntimeError("no power confirmation")

        with self.assertRaisesRegex(RuntimeError, "no power confirmation"):
            MODULE.enter_bootloader(
                "/dev/cu.test",
                Path("utility-plug.sh"),
                serial_factory=lambda _port: adapter,
                plug_setter=plug,
                pause=lambda _seconds: None,
            )

        self.assertFalse(adapter.rts)
        self.assertEqual(plug_actions, ["off", "on", "off"])
        self.assertEqual(adapter.events[-1], "close")


if __name__ == "__main__":
    unittest.main()
