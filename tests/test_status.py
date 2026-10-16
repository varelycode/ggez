import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('ggez', ROOT / 'scripts/ggez.py')
ggez = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ggez)


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ggez-status-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        before, desired = ggez.plan_init(self.root)
        ggez.apply_init(self.root, before, desired)
        self.feature = ggez.create_feature(self.root, 'Login')
        self.brief = ('# Login\n\n**Goal:** Let people sign in\n\n'
                      '**Approval:** Reviewer, 2026-10-06\n\n'
                      '## Acceptance checks\n\n- [ ] Login works\n- [ ] Reviewer accepts the outcome\n')
        self.tasks = ('# Tasks\n\n**Approval:** Reviewer, 2026-10-06\n\n## Queue\n\n'
                      '- [ ] TASK-1 — Setup\n\n  - **Result:** Pending\n\n'
                      '- [ ] TASK-2 — Login\n\n  - **Result:** Pending\n')
        self.write('brief.md', self.brief)
        self.write('tasks.md', self.tasks)

    def write(self, name, content):
        (self.feature / name).write_text(content)

    def status(self):
        return ggez.feature_status(self.root, self.feature)

    def set_result(self, task_id, result):
        path = self.feature / 'tasks.md'
        text = path.read_text()
        pattern = (r'(^- \[[ xX]\] ' + re.escape(task_id) + r' (?:—|-) [^\n]+\n)'
                   r'(.*?)(?=^- \[[ xX]\] TASK-|\Z)')
        match = re.search(pattern, text, re.M | re.S)
        self.assertIsNotNone(match)
        body = re.sub(r'(\*\*Result:\*\*\s*)[^\n]+', r'\g<1>' + result,
                      match.group(2), count=1)
        checked = 'x' if result == 'Pass' else ' '
        header = re.sub(r'^- \[[ xX]\]', '- [' + checked + ']', match.group(1))
        path.write_text(text[:match.start()] + header + body + text[match.end():])

    def accept(self):
        path = self.feature / 'brief.md'
        path.write_text(path.read_text().replace('- [ ]', '- [x]'))

    def complete(self):
        self.set_result('TASK-1', 'Pass')
        self.set_result('TASK-2', 'Pass')
        self.accept()

    def usage(self, rows):
        path = self.root / '.ggez/features/login/usage.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join(json.dumps(row) for row in rows))
        return path

    def test_approved_pending_work_is_ready(self):
        result = self.status()
        self.assertEqual((result['state'], result['stage']), ('Ready', 'Implementation'))
        self.assertEqual(result['completed'], 0)
        self.assertIn('TASK-1', result['current'])
        self.assertIn('Unavailable', result['time'])

    def test_draft_brief_needs_approval(self):
        self.write('brief.md', '# Brief\n\n**Goal:** [Goal]\n\n**Approval:** [Reviewer]\n')
        result = self.status()
        self.assertEqual((result['stage'], result['reason']), ('Brief', 'Approval required'))

    def test_blank_goal_does_not_read_next_field(self):
        self.write('brief.md', '# Brief\n\n**Goal:**\n\n**Approval:** Reviewer\n')
        self.assertEqual(self.status()['stage'], 'Brief')

    def test_missing_tasks_and_empty_queue_have_no_percentage(self):
        for content in ('', '# Tasks\n\n## Queue\n'):
            self.write('tasks.md', content)
            result = self.status()
            self.assertEqual(result['total'], 0)
            self.assertEqual(result['reason'], 'Missing prerequisite')

    def test_draft_tasks_need_approval(self):
        self.write('tasks.md', self.tasks.replace('Reviewer, 2026-10-06', '[Reviewer]'))
        self.assertEqual(self.status()['stage'], 'Tasks')
        self.assertEqual(self.status()['reason'], 'Approval required')

    def test_passed_task_is_counted_and_advances_current_task(self):
        self.set_result('TASK-1', 'Pass')
        result = self.status()
        self.assertEqual(result['completed'], 1)
        self.assertIn('TASK-2', result['current'])
        self.assertEqual(result['state'], 'Ready')

    def test_failure_results_map_to_fixed_reasons(self):
        for task_result, reason in [('Fail', 'Check failed'),
                                    ('Blocked', 'Missing prerequisite'),
                                    ('Interrupted', 'Run interrupted')]:
            self.write('tasks.md', self.tasks)
            self.set_result('TASK-1', task_result)
            info = self.status()
            self.assertEqual(info['reason'], reason)
            self.assertEqual(info['state'], 'Needs attention')

    def test_checked_and_result_state_must_agree(self):
        self.write('tasks.md', self.tasks.replace('- [ ] TASK-1', '- [x] TASK-1'))
        with self.assertRaisesRegex(ggez.ProjectError, 'checked exactly'):
            self.status()
        self.write('tasks.md', self.tasks.replace('**Result:** Pending', '**Result:** Pass', 1))
        with self.assertRaisesRegex(ggez.ProjectError, 'checked exactly'):
            self.status()

    def test_each_task_requires_one_valid_result(self):
        self.write('tasks.md', self.tasks.replace('  - **Result:** Pending\n\n', '', 1))
        with self.assertRaisesRegex(ggez.ProjectError, 'exactly one Result'):
            self.status()
        duplicate = self.tasks.replace('  - **Result:** Pending',
                                       '  - **Result:** Pending\n  - **Result:** Pending', 1)
        self.write('tasks.md', duplicate)
        with self.assertRaisesRegex(ggez.ProjectError, 'exactly one Result'):
            self.status()
        self.write('tasks.md', self.tasks.replace('**Result:** Pending', '**Result:** Maybe', 1))
        with self.assertRaisesRegex(ggez.ProjectError, 'Invalid task Result'):
            self.status()

    def test_duplicate_tasks_are_rejected(self):
        duplicate = self.tasks + '\n- [ ] TASK-1 — Duplicate\n\n  - **Result:** Pending\n'
        self.write('tasks.md', duplicate)
        with self.assertRaisesRegex(ggez.ProjectError, 'Duplicate task'):
            self.status()

    def test_all_passing_tasks_need_brief_acceptance(self):
        self.set_result('TASK-1', 'Pass')
        self.set_result('TASK-2', 'Pass')
        info = self.status()
        self.assertEqual((info['stage'], info['state'], info['reason']),
                         ('Review', 'Needs attention', 'Approval required'))

    def test_complete_requires_every_brief_acceptance_check(self):
        self.complete()
        self.assertEqual(self.status()['state'], 'Complete')
        brief = (self.feature / 'brief.md').read_text()
        self.write('brief.md', brief.replace('- [x] Login', '- [ ] Login'))
        self.assertNotEqual(self.status()['state'], 'Complete')

    def test_malformed_brief_acceptance_check_is_rejected(self):
        self.complete()
        brief = (self.feature / 'brief.md').read_text()
        self.write('brief.md', brief.replace('- [x] Login', '- [!] Login'))
        with self.assertRaisesRegex(ggez.ProjectError, 'Malformed Brief acceptance'):
            self.status()

    def test_usage_counts_retries_dedupes_and_excludes_wait(self):
        row = {'attempt_id': 'a', 'execution_seconds': 3,
               'approval_wait_seconds': 100, 'outcome': 'failed'}
        self.usage([row, row, {'attempt_id': 'b', 'execution_seconds': 4, 'outcome': 'passed'}])
        self.assertEqual(self.status()['time'], '7.0s recorded')

    def test_missing_and_partial_timing_are_labeled(self):
        self.usage([{'attempt_id': 'a'}])
        self.assertIn('Unavailable', self.status()['time'])
        self.usage([{'attempt_id': 'a', 'execution_seconds': 3}, {'attempt_id': 'b'}])
        self.assertEqual(self.status()['time'], '3.0s recorded (partial coverage)')
        self.usage([{'attempt_id': 'a', 'execution_seconds': 3, 'timing_complete': False}])
        self.assertIn('partial coverage', self.status()['time'])

    def test_invalid_timing_and_conflicting_duplicates_are_rejected(self):
        cases = [
            [{'attempt_id': 'a', 'execution_seconds': -1}],
            [{'attempt_id': 'a', 'execution_seconds': True}],
            [{'attempt_id': 'a', 'execution_seconds': float('nan')}],
            [{'attempt_id': 'a', 'execution_seconds': 1e308},
             {'attempt_id': 'b', 'execution_seconds': 1e308}],
            [{'attempt_id': 'a', 'execution_seconds': 2},
             {'attempt_id': 'a', 'execution_seconds': 3}],
        ]
        for rows in cases:
            self.usage(rows)
            with self.assertRaises(ggez.ProjectError):
                self.status()

    def test_cli_reports_only_brief_and_tasks_without_writing(self):
        self.set_result('TASK-1', 'Pass')
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/ggez.py'),
                                 'status', '--project', str(self.root)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        for value in ('Feature: login', 'Current task: TASK-2', 'Stage: Implementation',
                      '1/2 (50%)', 'Execution time: Unavailable'):
            self.assertIn(value, result.stdout)
        labels = [line.split(':', 1)[0] for line in result.stdout.splitlines()]
        self.assertEqual(labels, ['Feature', 'Current task', 'Stage', 'Completed',
                                  'Execution time', 'brief.md', 'tasks.md'])
        for name in ('brief.md', 'tasks.md'):
            self.assertIn(str(self.feature / name), result.stdout)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_multiple_feature_selection_and_cancel(self):
        ggez.create_feature(self.root, 'Other')
        command = [sys.executable, '-B', str(ROOT / 'scripts/ggez.py'),
                   'status', '--project', str(self.root)]
        selected = subprocess.run(command, input='2\n', capture_output=True, text=True)
        self.assertEqual(selected.returncode, 0, selected.stderr)
        self.assertIn('Feature: other', selected.stdout)
        cancelled = subprocess.run(command, input='', capture_output=True, text=True)
        self.assertEqual(cancelled.returncode, 0)
        self.assertIn('Cancelled', cancelled.stdout)

    def test_bare_command_shows_status_in_initialized_project(self):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/ggez.py')],
                                cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Feature: login', result.stdout)


if __name__ == '__main__':
    unittest.main()
