import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(project):
    spec = importlib.util.spec_from_file_location(project.replace('-', '_'), ROOT / 'cli.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProjectTests(unittest.TestCase):
    def test_all_help_and_invalid_arguments(self):
        for path in [ROOT / 'cli.py']:
            with self.subTest(project=path.parent.name):
                result = subprocess.run([sys.executable, str(path), '--help'], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                result = subprocess.run([sys.executable, str(path), '--not-a-real-option'], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn('Traceback', result.stderr)

    def test_prompt_pass_fail_validation(self):
        module = load('prompt-regression-kit')
        cases = [{'id': 'one', 'response': 'Hello', 'contains': ['Hello']}, {'id': 'two', 'response': 'secret', 'excludes': ['secret']}]
        result = module.evaluate(cases)
        self.assertTrue(result[0]['passed'])
        self.assertFalse(result[1]['passed'])
        with self.assertRaises(ValueError):
            module.evaluate([cases[0], cases[0]])
        with self.assertRaises(ValueError):
            module.evaluate([{'id': 'one', 'response': 'x', 'max_chars': -1}])

    def test_prompt_baseline_regression(self):
        with tempfile.TemporaryDirectory() as tmp:
            cases, baseline = Path(tmp) / 'cases.json', Path(tmp) / 'baseline.json'
            cases.write_text(json.dumps([{'id': 'one', 'response': 'bye', 'contains': ['Hello']}]))
            baseline.write_text(json.dumps({'results': [{'id': 'one', 'passed': True}]}))
            result = subprocess.run([sys.executable, str(ROOT / 'cli.py'), str(cases), '--baseline', str(baseline)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)['regressions'], ['one'])

if __name__ == '__main__':
    unittest.main()
