import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from write_evidence_manifest import main


class EvidenceManifestTests(unittest.TestCase):
    def test_hashes_file_and_every_directory_member(self) -> None:
        root = Path(tempfile.mkdtemp())
        output = root / "manifest.json"
        log = root / "motor.log"
        log.write_text("evidence\n")
        scope = root / "scope"
        scope.mkdir()
        (scope / "frame.npz").write_bytes(b"1234")
        with patch(
            "sys.argv",
            [
                "write_evidence_manifest.py",
                str(output),
                "--field",
                "config_mode=verified",
                "--artifact",
                f"motor_log={log}",
                "--artifact",
                f"scope={scope}",
            ],
        ):
            self.assertEqual(main(), 0)
        payload = json.loads(output.read_text())
        self.assertEqual(payload["fields"]["config_mode"], "verified")
        self.assertEqual(payload["artifacts"]["scope"]["files"], 1)
        self.assertEqual(len(payload["artifacts"]["scope"]["members"][0]["sha256"]), 64)
        self.assertEqual(len(payload["artifacts"]["motor_log"]["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
