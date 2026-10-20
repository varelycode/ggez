from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WorkflowTests(unittest.TestCase):
    def test_installed_workflow_in_fresh_and_existing_projects(self):
        with tempfile.TemporaryDirectory(prefix='ggez-walkthrough-') as temp:
            root = Path(temp).resolve()
            env = dict(os.environ, HOME=str(root), GGEZ_PYTHON=sys.executable)
            install = subprocess.run(['/bin/sh', str(ROOT / 'scripts/install.sh'), '--source',
                                      str(ROOT), '--prefix', str(root / 'install')],
                                     env=env, capture_output=True, text=True)
            self.assertEqual(install.returncode, 0, install.stderr)
            command = root / 'install/bin/ggez'
            for kind in ('fresh', 'existing'):
                with self.subTest(project=kind):
                    project = root / kind
                    project.mkdir()
                    original = b'# Local rules\nKeep the current app.\n'
                    if kind == 'existing':
                        (project / 'AGENTS.md').write_bytes(original)
                        (project / 'app.txt').write_text('original app\n')
                    def run(*args):
                        result = subprocess.run([str(command), *args], cwd=project,
                                                env=env, input='', capture_output=True, text=True)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        return result.stdout
                    run('init', '--yes')
                    run('plan', 'Login')
                    output = run('status')
                    self.assertIn('Stage: Brief', output)
                    self.assertNotIn('State:', output)
                    self.assertNotIn('Goal:', output)
                    self.assertNotIn('Next:', output)
                    self.assertIn('0/0 (Not available)', output)
                    feature = project / 'features/login'
                    brief = feature / 'brief.md'
                    text = brief.read_text()
                    self.assertIn('**Goal:** [What', text)
                    self.assertIn('**Approval:** [Reviewer', text)
                    # Sample approvals exercise the read model; no real feature is accepted.
                    brief.write_text(text.replace('[What should this feature let the person do?]',
                                                  'Sign in').replace('[Reviewer and date; leave blank until approved]',
                                                                    'Fixture reviewer, 2026-10-06').replace(
                                                                      '- [Path or URL] — [Why the agent needs it]',
                                                                      'None beyond AGENTS.md and this Brief'))
                    (feature / 'tasks.md').write_text(
                        '# Tasks\n\n**Approval:** Fixture reviewer\n\n## Queue\n\n'
                        '- [x] TASK-1 — Test login\n\n  - **Result:** Pass\n')
                    output = run('status')
                    self.assertIn('1/1 (100%)', output)
                    self.assertIn('Stage: Review', output)
                    self.assertNotIn('State:', output)
                    self.assertNotIn('Goal:', output)
                    self.assertNotIn('Next:', output)
                    self.assertIn('Unavailable', output)
                    brief.write_text(brief.read_text().replace('- [ ]', '- [x]'))
                    accepted_output = run('status')
                    self.assertIn('Stage: Review', accepted_output)
                    self.assertIn('1/1 (100%)', accepted_output)
                    self.assertIn(str(feature / 'brief.md'), accepted_output)
                    self.assertNotIn('evidence.md', accepted_output)
                    self.assertNotIn('review.md', accepted_output)
                    self.assertNotIn('State:', accepted_output)
                    self.assertIn('no changes', run('init'))
                    if kind == 'existing':
                        self.assertTrue((project / 'AGENTS.md').read_bytes().startswith(original))
                        self.assertEqual((project / 'app.txt').read_text(), 'original app\n')
                    self.assertFalse((project / '.git').exists())

    def test_untracked_parent_preserves_two_child_repositories(self):
        with tempfile.TemporaryDirectory(prefix='ggez-parent-') as temp:
            root = Path(temp).resolve()
            env = dict(os.environ, HOME=str(root), GGEZ_PYTHON=sys.executable)
            install = subprocess.run(['/bin/sh', str(ROOT / 'scripts/install.sh'), '--source',
                                      str(ROOT), '--prefix', str(root / 'install')],
                                     env=env, capture_output=True, text=True)
            self.assertEqual(install.returncode, 0, install.stderr)
            command = root / 'install/bin/ggez'
            parent = root / 'aramco'
            parent.mkdir()
            children = []
            for name in ('web', 'service'):
                child = parent / name
                child.mkdir()
                result = subprocess.run(['git', 'init', '-q', str(child)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                (child / 'AGENTS.md').write_text('# Child rules\n')
                (child / 'app.txt').write_text(name + '\n')
                children.append(child)

            def snapshot(path):
                return {str(item.relative_to(path)): item.read_bytes()
                        for item in path.rglob('*') if item.is_file()}

            before = {child.name: snapshot(child) for child in children}

            def run(*args):
                result = subprocess.run([str(command), *args], cwd=parent, env=env,
                                        input='', capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                return result.stdout

            run('init', '--yes')
            run('plan', 'Shared context')
            brief = parent / 'features/shared-context/brief.md'
            text = brief.read_text().replace(
                '[What should this feature let the person do?]', 'Coordinate both repositories').replace(
                '[Reviewer and date; leave blank until approved]', 'Fixture reviewer, 2026-10-20').replace(
                '- [Path or URL] — [Why the agent needs it]',
                '- web/AGENTS.md — Defines web rules.\n- service/AGENTS.md — Defines service rules.')
            brief.write_text(text)
            self.assertIn('Stage: Tasks', run('status'))
            self.assertFalse((parent / '.git').exists())
            self.assertEqual(before, {child.name: snapshot(child) for child in children})


if __name__ == '__main__':
    unittest.main()
