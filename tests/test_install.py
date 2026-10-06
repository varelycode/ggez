import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('install', ROOT / 'scripts/install.py')
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ggez installer ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.prefix = self.root / 'local install'
        self.env = dict(os.environ, HOME=str(self.root), GGEZ_PYTHON=sys.executable)
        self.payload = installer.local_payload(ROOT)

    def run_install(self, *args):
        return subprocess.run(['/bin/sh', str(ROOT / 'scripts/install.sh'),
                               '--source', str(ROOT), '--prefix', str(self.prefix), *args],
                              env=self.env, capture_output=True, text=True)

    def help_output(self, launcher):
        return subprocess.run([str(launcher), '--help'], env=self.env,
                              capture_output=True, text=True)

    def archive(self, names=None):
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode='w:gz') as archive:
            for name, content in (names or self.payload).items():
                entry = tarfile.TarInfo('ggez-main/' + name)
                entry.size = len(content)
                archive.addfile(entry, io.BytesIO(content))
        return output.getvalue()

    def test_checkout_install_and_help_with_spaces_in_paths(self):
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        launcher = self.prefix / 'bin/ggez'
        help_result = self.help_output(launcher)
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn('usage: ggez', help_result.stdout)
        self.assertIn('export PATH=', result.stdout)
        self.assertFalse((self.root / '.zshrc').exists())
        self.assertFalse((self.root / '.bashrc').exists())
        releases = list((self.prefix / 'share/ggez/releases').iterdir())
        self.assertEqual(len(releases), 1)
        for name, content in self.payload.items():
            self.assertEqual((releases[0] / name).read_bytes(), content)
        self.assertFalse(list(self.prefix.rglob('__pycache__')))

    def test_default_install_is_user_local(self):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/install.py'),
                                 '--source', str(ROOT)], env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / '.local/bin/ggez').is_file())

    def test_repeat_install_keeps_one_release_and_same_launcher(self):
        self.assertEqual(self.run_install().returncode, 0)
        launcher = self.prefix / 'bin/ggez'
        before = launcher.read_bytes()
        self.assertEqual(self.run_install().returncode, 0)
        self.assertEqual(launcher.read_bytes(), before)
        self.assertEqual(len(list((self.prefix / 'share/ggez/releases').iterdir())), 1)

    def test_update_activates_new_release_and_retains_previous(self):
        launcher = installer.install(self.payload, self.prefix)
        previous = launcher.read_bytes()
        changed = dict(self.payload)
        changed['templates/prd.md'] += b'\nUpdated fixture\n'
        installer.install(changed, self.prefix)
        self.assertNotEqual(launcher.read_bytes(), previous)
        self.assertEqual(self.help_output(launcher).returncode, 0)
        self.assertEqual(len(list((self.prefix / 'share/ggez/releases').iterdir())), 2)

    def test_broken_release_keeps_previous_launcher(self):
        launcher = installer.install(self.payload, self.prefix)
        previous = launcher.read_bytes()
        changed = dict(self.payload, **{'scripts/ggez.py': b'raise SystemExit(1)\n'})
        with self.assertRaisesRegex(installer.InstallError, 'help check failed'):
            installer.install(changed, self.prefix)
        self.assertEqual(launcher.read_bytes(), previous)
        self.assertEqual(self.help_output(launcher).returncode, 0)
        self.assertFalse(list(self.prefix.rglob('.staging-*')))

    def test_failed_activation_keeps_previous_launcher(self):
        launcher = installer.install(self.payload, self.prefix)
        before = launcher.read_bytes()
        changed = dict(self.payload)
        changed['templates/prd.md'] += b'\nNew release\n'
        real_replace = os.replace
        def replace(source, target):
            if Path(target) == launcher:
                raise PermissionError('fixture: launcher directory denied')
            return real_replace(source, target)
        with mock.patch.object(installer.os, 'replace', side_effect=replace):
            with self.assertRaises(PermissionError):
                installer.install(changed, self.prefix)
        self.assertEqual(launcher.read_bytes(), before)
        self.assertEqual(self.help_output(launcher).returncode, 0)
        self.assertFalse(list((self.prefix / 'bin').glob('.ggez-*')))

    def test_nonexecutable_install_filesystem_preserves_previous_launcher(self):
        launcher = installer.install(self.payload, self.prefix)
        before = launcher.read_bytes()
        real_run = subprocess.run
        def run(command, **kwargs):
            if Path(command[0]).name.startswith('.ggez-'):
                raise PermissionError('fixture: filesystem blocks execution')
            return real_run(command, **kwargs)
        with mock.patch.object(installer.subprocess, 'run', side_effect=run):
            with self.assertRaises(PermissionError):
                installer.install(self.payload, self.prefix)
        self.assertEqual(launcher.read_bytes(), before)
        self.assertEqual(self.help_output(launcher).returncode, 0)
        self.assertFalse(list((self.prefix / 'bin').glob('.ggez-*')))

    def test_missing_python_stops_bootstrap_without_writes(self):
        self.env['GGEZ_PYTHON'] = 'ggez-python-does-not-exist'
        result = self.run_install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Python 3.9+', result.stderr)
        self.assertFalse(self.prefix.exists())

    def test_old_python_stops_bootstrap(self):
        fake = self.root / 'old-python'
        fake.write_text('#!/bin/sh\nexit 1\n')
        fake.chmod(0o755)
        self.env['GGEZ_PYTHON'] = str(fake)
        result = self.run_install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Python 3.9+', result.stderr)
        self.assertFalse(self.prefix.exists())

    def test_download_failure_reports_error_and_preserves_install(self):
        launcher = installer.install(self.payload, self.prefix)
        before = launcher.read_bytes()
        with mock.patch.object(installer.urllib.request, 'urlopen',
                               side_effect=urllib.error.URLError('fixture: offline')):
            with contextlib.redirect_stderr(io.StringIO()) as output:
                code = installer.main(['--prefix', str(self.prefix)])
        self.assertEqual(code, 1)
        self.assertIn('offline', output.getvalue())
        self.assertNotIn('Traceback', output.getvalue())
        self.assertEqual(launcher.read_bytes(), before)
        self.assertEqual(self.help_output(launcher).returncode, 0)

    def test_archive_download_installs_valid_payload(self):
        with mock.patch.object(installer.urllib.request, 'urlopen',
                               return_value=io.BytesIO(self.archive())):
            with contextlib.redirect_stdout(io.StringIO()):
                code = installer.main(['--prefix', str(self.prefix)])
        self.assertEqual(code, 0)
        self.assertEqual(self.help_output(self.prefix / 'bin/ggez').returncode, 0)

    def test_bootstrap_download_failure_does_not_execute_partial_script(self):
        tools = self.root / 'tools'
        tools.mkdir()
        fake = tools / 'curl'
        fake.write_text('#!/bin/sh\nprintf "raise Exception(123)\\n"\nexit 22\n')
        fake.chmod(0o755)
        self.env['PATH'] = str(tools) + os.pathsep + os.environ['PATH']
        self.env['TMPDIR'] = str(self.root)
        result = subprocess.run(['/bin/sh', str(ROOT / 'scripts/install.sh')],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 22)
        self.assertNotIn('Exception', result.stderr)
        self.assertFalse(list(self.root.glob('ggez-install.*')))
        self.assertFalse((self.root / '.local').exists())

    def test_permission_error_is_readable(self):
        with mock.patch.object(installer, 'safe_directory', side_effect=PermissionError('denied')):
            with contextlib.redirect_stderr(io.StringIO()) as output:
                code = installer.main(['--source', str(ROOT), '--prefix', str(self.prefix)])
        self.assertEqual(code, 1)
        self.assertIn('denied', output.getvalue())
        self.assertNotIn('Traceback', output.getvalue())
        self.assertFalse(self.prefix.exists())

    def test_unrelated_command_is_preserved(self):
        launcher = self.prefix / 'bin/ggez'
        launcher.parent.mkdir(parents=True)
        launcher.write_text('my existing command')
        result = self.run_install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unrelated command', result.stderr)
        self.assertEqual(launcher.read_text(), 'my existing command')

    def test_symlinked_launcher_and_install_directory_are_rejected(self):
        outside = self.root / 'outside'
        outside.mkdir()
        self.prefix.mkdir()
        (self.prefix / 'bin').symlink_to(outside, target_is_directory=True)
        result = self.run_install()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])
        (self.prefix / 'bin').unlink()
        (self.prefix / 'bin').mkdir()
        (self.prefix / 'bin/ggez').symlink_to(outside / 'absent')
        self.assertNotEqual(self.run_install().returncode, 0)
        self.assertFalse((outside / 'absent').exists())

    def test_edited_release_is_preserved_and_rejected(self):
        launcher = installer.install(self.payload, self.prefix)
        before = launcher.read_bytes()
        release = next((self.prefix / 'share/ggez/releases').iterdir())
        template = release / 'templates/prd.md'
        template.write_text('user edit')
        with self.assertRaisesRegex(installer.InstallError, 'edited'):
            installer.install(self.payload, self.prefix)
        self.assertEqual(template.read_text(), 'user edit')
        self.assertEqual(launcher.read_bytes(), before)

    def test_incomplete_source_is_rejected_before_writes(self):
        source = self.root / 'source'
        source.mkdir()
        with contextlib.redirect_stderr(io.StringIO()) as output:
            code = installer.main(['--source', str(source), '--prefix', str(self.prefix)])
        self.assertEqual(code, 1)
        self.assertIn('missing required', output.getvalue())
        self.assertFalse(self.prefix.exists())

    def test_archive_rejects_traversal_and_missing_files(self):
        for data in [self.archive({'../escape': b'bad'}), self.archive({'unrelated': b'bad'})]:
            with self.subTest(data=data):
                with self.assertRaises(installer.InstallError):
                    installer.archive_payload(data)

    def test_archive_rejects_links_and_duplicates(self):
        for kind in ('symlink', 'duplicate'):
            output = io.BytesIO()
            with tarfile.open(fileobj=output, mode='w:gz') as archive:
                entry = tarfile.TarInfo('ggez-main/scripts/ggez.py')
                if kind == 'symlink':
                    entry.type = tarfile.SYMTYPE
                    entry.linkname = '/outside'
                    archive.addfile(entry)
                else:
                    for _ in range(2):
                        archive.addfile(entry, io.BytesIO(b''))
            with self.assertRaises(installer.InstallError):
                installer.archive_payload(output.getvalue())

    def test_unsupported_platform_is_rejected_before_writes(self):
        with mock.patch.object(installer.sys, 'platform', 'win32'):
            with contextlib.redirect_stderr(io.StringIO()) as output:
                code = installer.main(['--source', str(ROOT), '--prefix', str(self.prefix)])
        self.assertEqual(code, 1)
        self.assertIn('macOS and Linux', output.getvalue())
        self.assertFalse(self.prefix.exists())


if __name__ == '__main__':
    unittest.main()
