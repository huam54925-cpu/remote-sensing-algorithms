import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('envrun',Path(__file__).resolve().parents[1]/'scripts/env-run.py')
# Deployed image tests mount /tests only; host config tests run on host.
if spec.origin and Path(spec.origin).exists():
    envrun=importlib.util.module_from_spec(spec);spec.loader.exec_module(envrun)
else:
    envrun=None

@unittest.skipIf(envrun is None,'host-side configuration test')
class EnvTests(unittest.TestCase):
    def test_literal_and_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'test.env'
            p.write_text('INPUT_DIR=中文 路径\nRS_PARAMS={"clusters":3}\nRS_TASK_ID=$(touch sentinel)\n')
            result=envrun.parse(p)
            self.assertEqual(result['INPUT_DIR'],'中文 路径')
            self.assertEqual(result['RS_TASK_ID'],'$(touch sentinel)')
            self.assertFalse((Path(tmp)/'sentinel').exists())
            for value in ('TYPO=1','IMAGE=one\nIMAGE=two'):
                p.write_text(value)
                with self.assertRaises(ValueError):envrun.parse(p)
