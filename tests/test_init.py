import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('ggez', ROOT / 'scripts/ggez.py')
ggez = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ggez)


class InitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ggez init ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'project'
        self.root.mkdir()

    def run_init(self, *flags, answer=''):
        return subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/ggez.py'),
                               'init', str(self.root), *flags], input=answer,
                              capture_output=True, text=True)

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def install(self):
        result = self.run_init('--yes')
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def test_dry_run_previews_without_creating_files(self):
        result = self.run_init('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Create AGENTS.md', result.stdout)
        self.assertIn('Verified is the default', result.stdout)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_decline_and_eof_preserve_empty_project(self):
        for answer in ('', 'n\n'):
            result = self.run_init(answer=answer)
            self.assertEqual(result.returncode, 0)
            self.assertIn('Cancelled', result.stdout)
            self.assertEqual(list(self.root.iterdir()), [])

    def test_interactive_confirmation_installs_only_expected_files(self):
        result = self.run_init(answer='yes\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = {'.ggez/install.json', 'AGENTS.md'} | {
            '.ggez/templates/' + name for name in ggez.TEMPLATES}
        self.assertEqual(set(self.snapshot()), expected)
        self.assertFalse((self.root / '.git').exists())
        self.assertFalse((self.root / 'features').exists())
        for name in ggez.TEMPLATES:
            self.assertEqual((self.root / '.ggez/templates' / name).read_bytes(),
                             (ROOT / 'templates' / name).read_bytes())

    def test_existing_project_rules_git_and_modes_survive(self):
        old = b'# Project rules\r\nKeep my formatting.\r\n'
        path = self.root / 'AGENTS.md'
        path.write_bytes(old)
        path.chmod(0o640)
        (self.root / '.git').mkdir()
        (self.root / '.git/HEAD').write_text('ref: refs/heads/existing\n')
        (self.root / 'app.py').write_text('existing app\n')
        result = self.run_init(answer='y\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('resolve conflicts', result.stdout)
        self.assertTrue(path.read_bytes().startswith(old))
        self.assertEqual(path.stat().st_mode & 0o777, 0o640)
        self.assertEqual((self.root / '.git/HEAD').read_text(), 'ref: refs/heads/existing\n')
        self.assertEqual((self.root / 'app.py').read_text(), 'existing app\n')

    def test_repeated_init_is_noop(self):
        self.install()
        before = self.snapshot()
        result = self.run_init()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('no changes', result.stdout)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual((self.root / 'AGENTS.md').read_text().count(ggez.START), 1)

    def test_unmodified_templates_upgrade_and_outside_rules_survive(self):
        self.install()
        agents = self.root / 'AGENTS.md'
        agents.write_text('User prefix\n' + agents.read_text() + '\nUser suffix\n')
        bundle = self.root.parent / 'new-bundle'
        shutil.copytree(ggez.BUNDLE, bundle)
        (bundle / 'prd.md').write_text('Updated blank template\n')
        with (bundle / 'agent-rules.md').open('a') as output:
            output.write('\nNew managed instruction.\n')
        with mock.patch.object(ggez, 'BUNDLE', bundle):
            before, desired = ggez.plan_init(self.root)
            ggez.apply_init(self.root, before, desired)
        self.assertEqual((self.root / '.ggez/templates/prd.md').read_text(), 'Updated blank template\n')
        self.assertTrue(agents.read_text().startswith('User prefix\n'))
        self.assertTrue(agents.read_text().endswith('\nUser suffix\n'))
        self.assertEqual(agents.read_text().count(ggez.START), 1)

    def test_edited_template_blocks_all_writes(self):
        self.install()
        (self.root / '.ggez/templates/prd.md').write_text('User customization\n')
        before = self.snapshot()
        result = self.run_init('--yes')
        self.assertEqual(result.returncode, 1)
        self.assertIn('Conflict', result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_edited_managed_instructions_block_all_writes(self):
        self.install()
        path = self.root / 'AGENTS.md'
        path.write_text(path.read_text().replace('Verified is the default', 'Never test tasks'))
        before = self.snapshot()
        result = self.run_init('--yes')
        self.assertEqual(result.returncode, 1)
        self.assertIn('Conflict', result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_unrelated_template_is_not_overwritten(self):
        path = self.root / '.ggez/templates/tasks.md'
        path.parent.mkdir(parents=True)
        path.write_text('My tasks template')
        before = self.snapshot()
        result = self.run_init('--yes')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.snapshot(), before)

    def test_unmarked_ggez_section_is_not_duplicated(self):
        path = self.root / 'AGENTS.md'
        path.write_text('# Project\n\n## ggez workflow\nExisting instructions\n')
        before = self.snapshot()
        result = self.run_init('--yes')
        self.assertEqual(result.returncode, 1)
        self.assertIn('unmarked ggez section', result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_malformed_markers_require_resolution(self):
        for text in (ggez.START, ggez.END + ggez.START, ggez.START * 2 + ggez.END):
            with self.subTest(text=text):
                (self.root / 'AGENTS.md').write_text(text)
                result = self.run_init('--yes')
                self.assertEqual(result.returncode, 1)
                self.assertEqual((self.root / 'AGENTS.md').read_text(), text)
                self.assertFalse((self.root / '.ggez').exists())

    def test_malformed_manifest_is_readable_error_and_noop(self):
        self.install()
        (self.root / '.ggez/install.json').write_text('{bad')
        before = self.snapshot()
        result = self.run_init('--yes')
        self.assertEqual(result.returncode, 1)
        self.assertIn('Invalid init manifest', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_removed_managed_file_is_not_silently_recreated(self):
        self.install()
        (self.root / '.ggez/templates/prd.md').unlink()
        before = self.snapshot()
        result = self.run_init('--yes')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.snapshot(), before)

    def test_symlinked_directory_cannot_redirect_writes(self):
        outside = self.root.parent / 'outside'
        outside.mkdir()
        (self.root / '.ggez').symlink_to(outside, target_is_directory=True)
        result = self.run_init('--yes')
        self.assertEqual(result.returncode, 1)
        self.assertIn('symlink', result.stderr)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.root / 'AGENTS.md').exists())

    def test_symlinked_agents_cannot_redirect_writes(self):
        outside = self.root.parent / 'outside.md'
        outside.write_text('Keep me')
        (self.root / 'AGENTS.md').symlink_to(outside)
        self.assertEqual(self.run_init('--yes').returncode, 1)
        self.assertEqual(outside.read_text(), 'Keep me')
        self.assertFalse((self.root / '.ggez').exists())

    def test_directory_at_file_target_is_rejected(self):
        (self.root / 'AGENTS.md').mkdir()
        result = self.run_init('--yes')
        self.assertEqual(result.returncode, 1)
        self.assertIn('Expected file', result.stderr)
        self.assertFalse((self.root / '.ggez').exists())

    def test_missing_project_is_not_created(self):
        self.root.rmdir()
        result = self.run_init('--yes')
        self.assertEqual(result.returncode, 1)
        self.assertIn('Create the project directory', result.stderr)
        self.assertFalse(self.root.exists())

    def test_write_failure_rolls_back_files_modes_and_new_directories(self):
        agents = self.root / 'AGENTS.md'
        agents.write_text('Existing instructions\n')
        agents.chmod(0o640)
        original = self.snapshot()
        before, desired = ggez.plan_init(self.root)
        replace = os.replace
        def fail_manifest(source, target):
            if Path(target).name == 'install.json':
                raise PermissionError('fixture: write denied')
            return replace(source, target)
        with mock.patch.object(ggez.os, 'replace', side_effect=fail_manifest):
            with self.assertRaises(PermissionError):
                ggez.apply_init(self.root, before, desired)
        self.assertEqual(self.snapshot(), original)
        self.assertEqual(agents.stat().st_mode & 0o777, 0o640)
        self.assertEqual(list(self.root.iterdir()), [agents])

    def test_stale_preview_preserves_new_user_changes(self):
        before, desired = ggez.plan_init(self.root)
        (self.root / 'AGENTS.md').write_text('Added after preview')
        original = self.snapshot()
        with self.assertRaisesRegex(ggez.ProjectError, 'changed after preview'):
            ggez.apply_init(self.root, before, desired)
        self.assertEqual(self.snapshot(), original)
        self.assertFalse(list(self.root.glob('.ggez-init-*')))

    def test_keyboard_interrupt_rolls_back(self):
        before, desired = ggez.plan_init(self.root)
        real_replace = os.replace
        calls = 0
        def interrupt(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise KeyboardInterrupt()
            return real_replace(source, target)
        with mock.patch.object(ggez.os, 'replace', side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                ggez.apply_init(self.root, before, desired)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_installed_cli_initializes_without_source_checkout(self):
        prefix = self.root.parent / 'installation'
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/install.py'),
                                 '--source', str(ROOT), '--prefix', str(prefix)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run([str(prefix / 'bin/ggez'), 'init', str(self.root), '--yes'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        rules = (self.root / 'AGENTS.md').read_text()
        for required in ('Slice and Outcome', 'Verified', 'Unverified', 'usage.jsonl',
                         'evidence.md', 'review.md', 'fresh approval', 'live signal'):
            self.assertIn(required, rules)


if __name__ == '__main__':
    unittest.main()
