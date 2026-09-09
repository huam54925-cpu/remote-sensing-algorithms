import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from rs_container.selftest import run

class SelfTestReports(unittest.TestCase):
    def test_algorithm_failure_is_reported_and_previous_run_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('rs_container.selftest.subprocess.run', return_value=subprocess.CompletedProcess([], 99, '', 'injected failure')):
                self.assertEqual(run(tmp), 1)
                first = next(Path(tmp).glob('selftest-*'))
                original = (first/'report.json').read_bytes()
                report = json.loads(original)
                self.assertEqual(report['status'], 'FAIL')
                self.assertEqual(len(report['checks']), 4)
                self.assertTrue(all(c['status'] == 'FAIL' for c in report['checks']))
                self.assertTrue((first/'report.md').is_file())
                self.assertTrue((first/'SHA256SUMS').is_file())
                self.assertEqual(run(tmp), 1)
                self.assertEqual(len(list(Path(tmp).glob('selftest-*'))), 2)
                self.assertEqual((first/'report.json').read_bytes(), original)

    def test_invalid_report_destination_returns_io_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'file'; path.write_text('keep')
            self.assertEqual(run(path), 4)
            self.assertEqual(path.read_text(), 'keep')
