import importlib.util
import json
from pathlib import Path
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
        self.write('brief.md', '# Login\n\n**Goal:** Let people sign in\n\n**Approval:** Reviewer, 2026-10-06\n')
        self.tasks = '# Tasks\n\n**Approval:** Reviewer, 2026-10-06\n\n**Mode:** Unverified\n\n## Queue\n\n- [ ] TASK-1 — Setup\n- [ ] TASK-2 — Login\n'
        self.write('tasks.md', self.tasks)

    def write(self, name, content):
        (self.feature / name).write_text(content)

    def status(self):
        return ggez.feature_status(self.root, self.feature)

    def record(self, task='TASK-1', result='Pass', checks='Tests passed', review='Pending'):
        with (self.feature / 'evidence.md').open('a') as output:
            output.write(f'## {task} — date\n\n**Result:** {result}\n\n**Checks:** {checks}\n\n**Human review:** {review}\n\n')

    def check_tasks(self, count=1):
        self.write('tasks.md', self.tasks.replace('- [ ]', '- [x]', count))

    def complete(self):
        self.check_tasks(2)
        self.record()
        self.record('TASK-2')
        self.write('review.md', '# Review\n\n## Acceptance\n\n- [x] Checks passed\n- [x] Evidence reviewed\n\n## Decision\n\n- [x] Accepted\n- [ ] Revise\n')

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

    def test_checked_task_requires_pass_and_checks(self):
        self.check_tasks()
        self.assertEqual(self.status()['completed'], 0)
        self.record(checks='')
        self.assertEqual(self.status()['completed'], 0)
        self.record(checks='Unit tests passed')
        result = self.status()
        self.assertEqual(result['completed'], 1)
        self.assertIn('TASK-2', result['current'])

    def test_latest_attempt_wins_and_failure_blocks(self):
        self.check_tasks()
        self.record()
        self.record(result='Fail')
        self.assertEqual(self.status()['reason'], 'Check failed')
        self.assertEqual(self.status()['completed'], 0)
        self.record()
        self.assertEqual(self.status()['state'], 'Ready')

    def test_blocked_and_interrupted_and_unverified_running(self):
        for result, reason in [('Blocked', 'Missing prerequisite'), ('Interrupted', 'Run interrupted'), ('Running', 'Run interrupted')]:
            self.record(result=result)
            info = self.status()
            self.assertEqual(info['reason'], reason)
            self.assertNotEqual(info['state'], 'Running')

    def test_verified_needs_review_between_tasks(self):
        self.tasks = self.tasks.replace('Unverified', 'Verified')
        self.check_tasks()
        self.record()
        self.assertEqual(self.status()['reason'], 'Approval required')
        self.record(review='Approved')
        self.assertEqual(self.status()['state'], 'Ready')

    def test_all_passing_tasks_still_need_human_acceptance(self):
        self.check_tasks(2)
        self.record()
        self.record('TASK-2')
        info = self.status()
        self.assertEqual((info['stage'], info['state'], info['reason']), ('Review', 'Needs attention', 'Approval required'))

    def test_complete_requires_acceptance_checklist_and_evidence(self):
        self.complete()
        self.assertEqual(self.status()['state'], 'Complete')
        review = (self.feature / 'review.md').read_text()
        self.write('review.md', review.replace('- [x] Checks', '- [ ] Checks'))
        self.assertNotEqual(self.status()['state'], 'Complete')
        self.write('review.md', review)
        self.record('TASK-2', 'Fail')
        self.assertNotEqual(self.status()['state'], 'Complete')

    def test_conflicting_review_decisions_are_rejected(self):
        self.complete()
        p = self.feature / 'review.md'
        p.write_text(p.read_text().replace('- [ ] Revise', '- [x] Revise'))
        with self.assertRaisesRegex(ggez.ProjectError, 'conflicting'):
            self.status()

    def test_duplicate_tasks_and_malformed_evidence_are_rejected(self):
        self.write('tasks.md', self.tasks + '- [ ] TASK-1 — Duplicate\n')
        with self.assertRaisesRegex(ggez.ProjectError, 'Duplicate task'):
            self.status()
        self.write('tasks.md', self.tasks)
        self.record(result='Maybe')
        with self.assertRaisesRegex(ggez.ProjectError, 'Invalid evidence'):
            self.status()

    def test_usage_counts_retries_dedupes_and_excludes_wait(self):
        row = {'attempt_id': 'a', 'execution_seconds': 3, 'approval_wait_seconds': 100, 'outcome': 'failed'}
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
            [{'attempt_id': 'a', 'execution_seconds': 1e308}, {'attempt_id': 'b', 'execution_seconds': 1e308}],
            [{'attempt_id': 'a', 'execution_seconds': 2}, {'attempt_id': 'a', 'execution_seconds': 3}],
        ]
        for rows in cases:
            self.usage(rows)
            with self.assertRaises(ggez.ProjectError):
                self.status()

    def test_cli_selects_single_feature_reports_progress_and_never_writes(self):
        self.check_tasks()
        self.record()
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/ggez.py'),
                                 'status', '--project', str(self.root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        for value in ('Feature: login', 'Current task: TASK-2', 'Stage: Implementation', '1/2 (50%)', 'Execution time: Unavailable'):
            self.assertIn(value, result.stdout)
        labels = [line.split(':', 1)[0] for line in result.stdout.splitlines()]
        self.assertEqual(labels, ['Feature', 'Current task', 'Stage', 'Completed', 'Execution time',
                                  'brief.md', 'tasks.md', 'evidence.md'])
        for name in ('brief.md', 'tasks.md', 'evidence.md'):
            self.assertIn(str(self.feature / name), result.stdout)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_multiple_feature_selection_and_cancel(self):
        ggez.create_feature(self.root, 'Other')
        command = [sys.executable, '-B', str(ROOT / 'scripts/ggez.py'), 'status', '--project', str(self.root)]
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
