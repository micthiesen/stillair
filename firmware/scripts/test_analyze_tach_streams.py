#!/usr/bin/env python3

import tempfile
import unittest
from pathlib import Path

from analyze_tach_streams import summarize


class TachStreamTests(unittest.TestCase):
    def test_stream_block_reports_sampled_hall_period_estimates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "motor.log"
            path.write_text(
                "# t=1.000s run 160\n"
                "# t=2.000s stream 1 --for 3\n"
                "t_ms,state,fault,on,tgt_mrpm,cmd_mrpm,fg_mrpm,hall_mrpm,duty,dir,req_dir,min_mrpm,config,dropped\n"
                "2000,running,null,true,160000,160000,159000,160000,1,fwd,fwd,35000,provisional,0\n"
                "3000,running,null,true,160000,160000,160000,160000,1,fwd,fwd,35000,provisional,0\n"
                "4000,running,null,true,160000,160000,161000,161000,1,fwd,fwd,35000,provisional,0\n"
                "# t=5.000s stop\n"
            )
            result = summarize(path)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["target_rpm"], 160)
        self.assertEqual(result[0]["hall_period_samples"], 3)
        self.assertEqual(result[0]["fg_mean_rpm"], 160.0)
        self.assertEqual(result[0]["faults"], [])
        self.assertTrue(result[0]["qualified"])

    def test_rejects_faults_or_fg_hall_disagreement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "motor.log"
            path.write_text(
                "# t=1.000s run 160\n"
                "# t=2.000s stream 1 --for 2\n"
                "t_ms,state,fault,on,tgt_mrpm,cmd_mrpm,fg_mrpm,hall_mrpm,duty,dir,req_dir,min_mrpm,config,dropped\n"
                "2000,running,null,true,160000,160000,160000,120000,1,fwd,fwd,35000,provisional,0\n"
                "3000,running,null,true,160000,160000,160000,120000,1,fwd,fwd,35000,provisional,0\n"
                "# t=4.000s stop\n"
            )
            with self.assertRaisesRegex(ValueError, "fg_hall_disagreement"):
                summarize(path)


if __name__ == "__main__":
    unittest.main()
