import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('ggez', ROOT / 'scripts/ggez.py')
ggez = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ggez)


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ggez-plan-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        before, desired = ggez.plan_init(self.root)
        ggez.apply_init(self.root, before, desired)

    def run_plan(self, *args, answer=''):
        return subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/ggez.py'),
                               'plan', '--project', str(self.root), *args],
                              input=answer, capture_output=True, text=True)

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def test_title_only_preserves_all_placeholders(self):
        result = self.run_plan('Login settings')
        self.assertEqual(result.returncode, 0, result.stderr)
        brief = self.root / 'features/login-settings/brief.md'
        expected = (self.root / '.ggez/templates/prd.md').read_text().replace(
            '# [Feature name] — Brief', '# Login settings — Brief', 1)
        self.assertEqual(brief.read_text(), expected)
        self.assertEqual(list(brief.parent.iterdir()), [brief])
        for required in ('Codex', 'Cursor', 'Claude', 'Verified', 'Unverified',
                         'never fill', 'approve', 'Stop on failures', str(brief)):
            self.assertIn(required, result.stdout)

    def test_title_collision_preserves_previous_feature(self):
        self.assertEqual(self.run_plan('Login').returncode, 0)
        first = self.root / 'features/login/brief.md'
        first.write_text('Existing user draft')
        self.assertEqual(self.run_plan('Login').returncode, 0)
        self.assertEqual(first.read_text(), 'Existing user draft')
        self.assertTrue((self.root / 'features/login-2/brief.md').exists())

    def test_picker_selects_without_writing(self):
        self.run_plan('Beta')
        self.run_plan('Alpha')
        before = self.snapshot()
        result = self.run_plan(answer='2\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('1. alpha', result.stdout)
        self.assertIn('2. beta', result.stdout)
        self.assertIn('0. New feature', result.stdout)
        self.assertIn(str(self.root / 'features/beta/brief.md'), result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_empty_picker_creates_after_explicit_choice(self):
        result = self.run_plan(answer='0\nFirst feature\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / 'features/first-feature/brief.md').exists())

    def test_cancel_eof_and_empty_title_do_not_write(self):
        before = self.snapshot()
        for answer in ('', '\n', '0\n\n'):
            result = self.run_plan(answer=answer)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Cancelled', result.stdout)
            self.assertEqual(self.snapshot(), before)
            self.assertFalse((self.root / 'features').exists())

    def test_invalid_selection_is_noop(self):
        before = self.snapshot()
        result = self.run_plan(answer='99\n')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.snapshot(), before)

    def test_invalid_title_is_noop(self):
        before = self.snapshot()
        for title in (' ', '../escape', '/tmp/escape', 'a\\b', '.', 'a\nb', 'x' * 101, 'a\x1bb'):
            with self.subTest(title=title):
                result = self.run_plan(title)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(self.snapshot(), before)
                self.assertFalse((self.root / 'features').exists())

    def test_symlinked_features_cannot_redirect_writes(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (self.root / 'features').symlink_to(outside, target_is_directory=True)
        result = self.run_plan('Login')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(list(outside.iterdir()), [])

    def test_symlinked_brief_is_not_selected(self):
        self.run_plan('Login')
        brief = self.root / 'features/login/brief.md'
        brief.unlink()
        brief.symlink_to(self.root / 'AGENTS.md')
        self.assertEqual(self.run_plan(answer='1\n').returncode, 1)

    def test_missing_initialization_gives_next_step(self):
        (self.root / '.ggez/install.json').unlink()
        result = self.run_plan('Login')
        self.assertEqual(result.returncode, 1)
        self.assertIn('ggez init', result.stderr)
        self.assertFalse((self.root / 'features').exists())

    def test_failed_write_removes_new_feature(self):
        original = Path.open
        def deny(path, *args, **kwargs):
            if path.name == 'brief.md':
                raise PermissionError('fixture: denied')
            return original(path, *args, **kwargs)
        with mock.patch.object(Path, 'open', deny):
            with self.assertRaises(PermissionError):
                ggez.create_feature(self.root, 'Login')
        self.assertFalse((self.root / 'features').exists())


if __name__ == '__main__':
    unittest.main()
