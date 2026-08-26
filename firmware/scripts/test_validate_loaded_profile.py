import tempfile
import unittest
from pathlib import Path

from validate_loaded_profile import validate


class LoadedProfileValidationTests(unittest.TestCase):
    def profile(self, text: str) -> Path:
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        handle.write(text)
        handle.close()
        self.addCleanup(Path(handle.name).unlink)
        return Path(handle.name)

    def test_accepts_verified_bounded_profile_with_final_stop(self) -> None:
        result = validate(
            self.profile(
                """config check
wait idle_off --for 20
run 50
wait speed 50 --within 2 --for 90
stream 10 --for 20
stop
wait idle_off --for 120
"""
            ),
            "verified",
        )
        self.assertEqual(result["measurement_windows"], 1)
        self.assertEqual(result["worst_case_seconds"], 310)

    def test_rejects_out_of_envelope_speed(self) -> None:
        with self.assertRaisesRegex(ValueError, "outside 50..=170"):
            validate(
                self.profile("config check\nrun 180\nstream 1 --for 2\nstop\nwait idle_off\n"),
                "verified",
            )

    def test_rejects_implicit_stage_or_write(self) -> None:
        for command in ("config stage", "config apply", "reg write CLOSED_LOOP1 0"):
            with self.subTest(command=command), self.assertRaisesRegex(ValueError, "may not|raw"):
                validate(
                    self.profile(
                        f"config check\n{command}\nrun 50\nstream 1 --for 2\nstop\nwait idle_off\n"
                    ),
                    "verified",
                )

    def test_requires_final_stopped_state(self) -> None:
        with self.assertRaisesRegex(ValueError, "wait idle_off"):
            validate(
                self.profile("config check\nrun 50\nstream 1 --for 2\nstop\n"),
                "verified",
            )

    def test_direction_change_requires_verified_stop(self) -> None:
        with self.assertRaisesRegex(ValueError, "immediately preceding"):
            validate(
                self.profile(
                    "config check\nrun 50\nstream 1 --for 2\nstop\ndir rev\nwait idle_off\n"
                ),
                "verified",
            )

    def test_accepts_known_candidate_with_configuration_owned_by_wrapper(self) -> None:
        result = validate(
            self.profile("run 50\nstream 1 --for 2\nstop\nwait idle_off\n"),
            "candidate",
            "pwm-30khz",
        )
        self.assertEqual(result["candidate"], "pwm-30khz")

    def test_rejects_unknown_candidate_and_in_profile_tune(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown loaded tuning candidate"):
            validate(
                self.profile("run 50\nstream 1 --for 2\nstop\nwait idle_off\n"),
                "candidate",
                "anything",
            )
        with self.assertRaisesRegex(ValueError, "may not stage"):
            validate(
                self.profile(
                    "config tune pwm-30khz\nrun 50\nstream 1 --for 2\nstop\nwait idle_off\n"
                ),
                "candidate",
                "pwm-30khz",
            )


if __name__ == "__main__":
    unittest.main()
