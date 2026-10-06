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
                                                                    'Fixture reviewer, 2026-10-06'))
                    (feature / 'tasks.md').write_text('# Tasks\n\n**Approval:** Fixture reviewer\n\n**Mode:** Unverified\n\n## Queue\n\n- [x] TASK-1 — Test login\n')
                    (feature / 'evidence.md').write_text('# Evidence\n\n## TASK-1\n\n**Result:** Pass\n\n**Checks:** Fixture login test passed\n')
                    output = run('status')
                    self.assertIn('1/1 (100%)', output)
                    self.assertIn('Stage: Review', output)
                    self.assertNotIn('State:', output)
                    self.assertNotIn('Goal:', output)
                    self.assertNotIn('Next:', output)
                    self.assertIn('Unavailable', output)
                    (feature / 'review.md').write_text('# Review\n\n## Acceptance\n\n- [x] Checks reviewed\n\n## Decision\n\n- [x] Accepted\n')
                    accepted_output = run('status')
                    self.assertIn('Stage: Review', accepted_output)
                    self.assertIn('1/1 (100%)', accepted_output)
                    self.assertIn(str(feature / 'review.md'), accepted_output)
                    self.assertNotIn('State:', accepted_output)
                    self.assertIn('no changes', run('init'))
                    if kind == 'existing':
                        self.assertTrue((project / 'AGENTS.md').read_bytes().startswith(original))
                        self.assertEqual((project / 'app.txt').read_text(), 'original app\n')
                    self.assertFalse((project / '.git').exists())


if __name__ == '__main__':
    unittest.main()
