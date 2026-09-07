import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.input = self.root / '输入.txt'
        self.input.write_bytes(b'abc')
        self.output = self.root / 'output'
        self.env = {k:v for k,v in os.environ.items() if not k.startswith('RS_')}
    def run_cli(self, *args, **env):
        return subprocess.run([sys.executable, '-m', 'rs_container', *args], env={**self.env, **env}, text=True, capture_output=True)
    def args(self):
        return ['--algorithm', 'smoke', '--input', str(self.input), '--output-dir', str(self.output)]
    def test_help(self):
        self.assertEqual(self.run_cli('--help').returncode, 0)
    def test_health(self):
        r=self.run_cli('--healthcheck');self.assertEqual(r.returncode,0)
        self.assertEqual(json.loads(r.stderr)['message'], 'framework_health_ok')
    def test_pending_algorithms(self):
        r=self.run_cli('--list');data=json.loads(r.stdout)
        self.assertEqual(data['MNDWI'], 'implemented_example')
        self.assertEqual(sum(v=='not_implemented' for v in data.values()),12)
    def test_missing_arguments(self):
        r=self.run_cli();self.assertEqual(r.returncode,2);json.loads(r.stderr)
    def test_unknown_algorithm(self):
        self.assertEqual(self.run_cli(*self.args(),'--algorithm','NDVI').returncode,3)
    def test_missing_input(self):
        self.assertEqual(self.run_cli(*self.args(),'--input',str(self.root/'missing')).returncode,4)
    def test_invalid_params(self):
        for value in ('[1]', '{', '{"threshold":1}'):
            self.assertEqual(self.run_cli(*self.args(),'--params',value).returncode,2)
    def test_smoke_and_logs(self):
        r=self.run_cli(*self.args(),'--task-id','test-001');self.assertEqual(r.returncode,0,r.stderr)
        data=json.loads((self.output/'smoke-result.json').read_text())
        self.assertEqual(data['sha256'],hashlib.sha256(b'abc').hexdigest())
        self.assertEqual(data['bytes'],3)
        log=json.loads(r.stderr)
        for key in ('timestamp','level','module','task_id','message','elapsed_seconds','process_peak_rss_kib'):
            self.assertIn(key,log)
    def test_environment_and_cli_override(self):
        r=self.run_cli('--algorithm','smoke',RS_ALGORITHM='unknown',RS_INPUT=str(self.input),RS_OUTPUT_DIR=str(self.output),RS_PARAMS='{}')
        self.assertEqual(r.returncode,0,r.stderr)
    def test_existing_result_not_overwritten(self):
        self.assertEqual(self.run_cli(*self.args()).returncode,0)
        original=(self.output/'smoke-result.json').read_bytes()
        self.assertEqual(self.run_cli(*self.args()).returncode,5)
        self.assertEqual((self.output/'smoke-result.json').read_bytes(),original)
    def test_output_is_file(self):
        self.output.write_text('occupied')
        self.assertEqual(self.run_cli(*self.args()).returncode,5)
