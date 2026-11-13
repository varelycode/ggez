from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from scripts import ggez

ROOT = Path(__file__).resolve().parents[1]


class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.now = 1794600000123
        self.entropy = bytes(range(10))

    def test_uuid7_keeps_time_version_and_random_uniqueness(self):
        first = ggez.uuid7(self.now, self.entropy)
        repeated = ggez.uuid7(self.now, self.entropy)
        other = ggez.uuid7(self.now, b'\xff' * 10)
        self.assertEqual(first, repeated)
        self.assertNotEqual(first, other)
        self.assertEqual(first.version, 7)
        self.assertEqual(first.int >> 80, self.now)

    def test_revision_identity_verifies_digest_and_decodes_time(self):
        text = '# Brief\n\n**Goal:** Trace tasks\n'
        identity = ggez.revision_identity(
            'brief', text, now_ms=self.now, entropy=self.entropy)
        parsed = ggez.verify_revision(
            identity.revision, identity.content_digest, text, 'brief')
        self.assertEqual(parsed.kind, 'brief')
        self.assertEqual(parsed.digest_prefix, identity.content_digest[7:23])
        self.assertEqual(ggez.revision_created_at(identity.revision),
                         '2026-11-13T20:00:00.123Z')

    def test_mutable_brief_state_does_not_change_definition(self):
        draft = ('# Brief\n\n**Revision:** [Generated]\n\n**Content digest:** [Generated]\n\n'
                 '**Status:** Draft\n\n**Approval:** [Reviewer]\n\n'
                 '## Acceptance checks\n\n- [ ] Works\n')
        approved = draft.replace('Draft', 'Approved').replace(
            '[Reviewer]', 'Viviana, 2026-11-13').replace('- [ ] Works', '- [x] Works')
        self.assertEqual(ggez.definition_digest(draft, 'brief'),
                         ggez.definition_digest(approved, 'brief'))

    def test_mutable_task_state_does_not_change_definition(self):
        pending = ('# Tasks\n\n**Revision:** [Generated]\n\n**Content digest:** [Generated]\n\n'
                   '**Derived from:** [Brief]\n\n**Approval:** [Reviewer]\n\n'
                   '## Queue\n\n- [ ] TASK-1 — Work\n\n  - **Result:** Pending\n\n'
                   '  - [ ] Check it\n\n## Status\n\n**Next task:** TASK-1\n')
        passed = pending.replace('[Reviewer]', 'Viviana').replace(
            '- [ ] TASK-1', '- [x] TASK-1').replace(
            '**Result:** Pending', '**Result:** Pass').replace(
            '- [ ] Check it', '- [x] Check it').replace('TASK-1\n', 'None\n', 1)
        self.assertEqual(ggez.definition_digest(pending, 'tasks'),
                         ggez.definition_digest(passed, 'tasks'))

    def test_substantive_change_mints_a_new_identity(self):
        first_text = '# Brief\n\n**Goal:** Trace tasks\n'
        first = ggez.revision_identity(
            'brief', first_text, now_ms=self.now, entropy=self.entropy)
        same = ggez.revision_identity(
            'brief', first_text, first.revision, first.content_digest,
            now_ms=self.now + 1, entropy=b'\xff' * 10)
        changed = ggez.revision_identity(
            'brief', first_text + '\n**Why now:** Drift\n',
            first.revision, first.content_digest,
            now_ms=self.now + 1, entropy=b'\xff' * 10)
        self.assertEqual(same, first)
        self.assertNotEqual(changed.revision, first.revision)
        self.assertNotEqual(changed.content_digest, first.content_digest)

    def test_malformed_and_conflicting_metadata_is_rejected(self):
        text = '# Tasks\n\n- [ ] TASK-1 — Work\n\n  - **Result:** Pending\n'
        identity = ggez.revision_identity(
            'tasks', text, now_ms=self.now, entropy=self.entropy)
        cases = [
            ('bad', identity.content_digest),
            (identity.revision.replace('tasks-', 'brief-', 1), identity.content_digest),
            (identity.revision, 'sha256:' + '0' * 64),
        ]
        for value, recorded in cases:
            with self.subTest(value=value, recorded=recorded):
                with self.assertRaises(ggez.ProjectError):
                    ggez.verify_revision(value, recorded, text, 'tasks')

    def test_same_uuid_with_different_content_has_a_different_full_id(self):
        first = ggez.revision_identity(
            'brief', '# A\n', now_ms=self.now, entropy=self.entropy).revision
        second = ggez.revision_identity(
            'brief', '# B\n', now_ms=self.now, entropy=self.entropy).revision
        self.assertNotEqual(first, second)
        self.assertEqual(first.split('-')[1:6], second.split('-')[1:6])


class RevisionLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ggez-revisions-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        before, desired = ggez.plan_init(self.root)
        ggez.apply_init(self.root, before, desired)
        self.feature = self.make_feature('Login')

    def brief_text(self, goal='Trace tasks', approved=True):
        approval = 'Viviana, 2026-11-13' if approved else '[Reviewer]'
        return ('# Login — Brief\n\n**Status:** Approved\n\n'
                '**Approval:** ' + approval + '\n\n'
                '**Goal:** ' + goal + '\n\n## Context — **Required**\n\n'
                'None beyond AGENTS.md and this Brief\n\n'
                '## Acceptance checks\n\n- [ ] Lineage works\n')

    def tasks_text(self, title='Trace tasks', approved=True):
        approval = 'Viviana, 2026-11-13' if approved else '[Reviewer]'
        return ('# Login — Tasks\n\n**Approval:** ' + approval + '\n\n'
                '## Queue\n\n- [ ] TASK-1 — ' + title + '\n\n'
                '  - **Result:** Pending\n')

    def make_feature(self, title):
        feature = ggez.create_feature(self.root, title)
        (feature / 'brief.md').write_text(self.brief_text())
        return feature

    def run_revise(self, document, feature=None, answer=''):
        command = [sys.executable, '-B', str(ROOT / 'scripts/ggez.py'), 'revise',
                   document]
        if feature is not None:
            command.append(feature)
        command.extend(['--project', str(self.root)])
        return subprocess.run(command, input=answer, capture_output=True, text=True)

    def run_check(self, feature=None, answer=''):
        command = [sys.executable, '-B', str(ROOT / 'scripts/ggez.py'), 'check']
        if feature is not None:
            command.append(feature)
        command.extend(['--project', str(self.root)])
        return subprocess.run(command, input=answer, capture_output=True, text=True)

    def stamp_feature(self):
        self.assertEqual(self.run_revise('brief', 'login').returncode, 0)
        (self.feature / 'tasks.md').write_text(self.tasks_text())
        self.assertEqual(self.run_revise('tasks', 'login').returncode, 0)

    def test_brief_stamping_is_idempotent_and_changed_content_clears_approval(self):
        first = self.run_revise('brief', 'login')
        self.assertEqual(first.returncode, 0, first.stderr)
        stamped = (self.feature / 'brief.md').read_text()
        revision = ggez.field(stamped, 'Revision')
        self.assertTrue(revision.startswith('brief-'))
        ggez.verify_revision(revision, ggez.field(stamped, 'Content digest'), stamped, 'brief')
        repeated = self.run_revise('brief', 'login')
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertIn('Unchanged:', repeated.stdout)
        self.assertEqual((self.feature / 'brief.md').read_text(), stamped)
        (self.feature / 'brief.md').write_text(stamped.replace('Trace tasks', 'Trace revised tasks'))
        changed = self.run_revise('brief', 'login')
        self.assertEqual(changed.returncode, 0, changed.stderr)
        revised = (self.feature / 'brief.md').read_text()
        self.assertNotEqual(ggez.field(revised, 'Revision'), revision)
        self.assertEqual(ggez.field(revised, 'Status'), 'Draft')
        self.assertFalse(ggez.approved(revised))
        self.assertIn('Approval cleared', changed.stdout)

    def test_task_revision_tracks_exact_brief_and_ignores_result_state(self):
        self.assertEqual(self.run_revise('brief', 'login').returncode, 0)
        (self.feature / 'tasks.md').write_text(self.tasks_text())
        stamped = self.run_revise('tasks', 'login')
        self.assertEqual(stamped.returncode, 0, stamped.stderr)
        brief = (self.feature / 'brief.md').read_text()
        tasks = (self.feature / 'tasks.md').read_text()
        task_revision = ggez.field(tasks, 'Revision')
        self.assertEqual(ggez.field(tasks, 'Derived from'), ggez.field(brief, 'Revision'))
        state_change = tasks.replace('- [ ] TASK-1', '- [x] TASK-1').replace(
            '**Result:** Pending', '**Result:** Pass')
        (self.feature / 'tasks.md').write_text(state_change)
        repeated = self.run_revise('tasks', 'login')
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(ggez.field((self.feature / 'tasks.md').read_text(), 'Revision'),
                         task_revision)
        instruction_change = state_change.replace('Trace tasks', 'Trace revised tasks')
        (self.feature / 'tasks.md').write_text(instruction_change)
        changed = self.run_revise('tasks', 'login')
        self.assertEqual(changed.returncode, 0, changed.stderr)
        revised = (self.feature / 'tasks.md').read_text()
        self.assertNotEqual(ggez.field(revised, 'Revision'), task_revision)
        self.assertFalse(ggez.approved(revised))

    def test_new_brief_revision_mints_a_new_task_set_revision(self):
        self.assertEqual(self.run_revise('brief', 'login').returncode, 0)
        (self.feature / 'tasks.md').write_text(self.tasks_text())
        self.assertEqual(self.run_revise('tasks', 'login').returncode, 0)
        old_tasks = (self.feature / 'tasks.md').read_text()
        old_task_revision = ggez.field(old_tasks, 'Revision')
        brief = (self.feature / 'brief.md').read_text().replace('Trace tasks', 'Trace better tasks')
        (self.feature / 'brief.md').write_text(brief)
        self.assertEqual(self.run_revise('brief', 'login').returncode, 0)
        revised_brief = (self.feature / 'brief.md').read_text().replace(
            '[Reviewer and date; leave blank until approved]', 'Viviana, 2026-11-13').replace(
            '**Status:** Draft', '**Status:** Approved')
        (self.feature / 'brief.md').write_text(revised_brief)
        refreshed = self.run_revise('tasks', 'login')
        self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
        new_tasks = (self.feature / 'tasks.md').read_text()
        self.assertNotEqual(ggez.field(new_tasks, 'Revision'), old_task_revision)
        self.assertEqual(ggez.field(new_tasks, 'Derived from'),
                         ggez.field(revised_brief, 'Revision'))
        self.assertFalse(ggez.approved(new_tasks))

    def test_optional_feature_uses_auto_fuzzy_and_cancel_selection(self):
        only = self.run_revise('brief')
        self.assertEqual(only.returncode, 0, only.stderr)
        self.assertIn('Feature: login', only.stdout)
        beta = self.make_feature('Beta reports')
        selected = self.run_revise('brief', answer='bta rep\n')
        self.assertEqual(selected.returncode, 0, selected.stderr)
        self.assertTrue(ggez.field((beta / 'brief.md').read_text(), 'Revision'))
        cancelled = self.run_revise('brief', answer='')
        self.assertEqual(cancelled.returncode, 0, cancelled.stderr)
        self.assertIn('Cancelled', cancelled.stdout)
        missing = self.run_revise('brief', answer='zzzzzz\n')
        self.assertEqual(missing.returncode, 1)
        self.assertIn('No feature matches', missing.stderr)

    def test_task_revision_requires_approved_stamped_brief_and_tasks(self):
        (self.feature / 'brief.md').write_text(self.brief_text(approved=False))
        (self.feature / 'tasks.md').write_text(self.tasks_text())
        unapproved = self.run_revise('tasks', 'login')
        self.assertEqual(unapproved.returncode, 1)
        self.assertIn('Approve the Brief', unapproved.stderr)
        (self.feature / 'brief.md').write_text(self.brief_text())
        unstamped = self.run_revise('tasks', 'login')
        self.assertEqual(unstamped.returncode, 1)
        self.assertIn('revise brief', unstamped.stderr)

    def test_failed_atomic_replace_preserves_document(self):
        before = (self.feature / 'brief.md').read_text()
        replace = mock.Mock(side_effect=PermissionError('denied'))
        with self.assertRaises(PermissionError):
            ggez.revise_document(
                self.root, self.feature, 'brief', replace_file=replace)
        self.assertEqual((self.feature / 'brief.md').read_text(), before)
        self.assertFalse(list(self.feature.glob('.ggez-revise-*')))

    def test_check_reports_matching_lineage_and_never_writes(self):
        self.stamp_feature()
        before = {path: path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        result = self.run_check('login')
        self.assertEqual(result.returncode, 0, result.stderr)
        for value in ('Feature: login', 'Brief revision: brief-', 'Brief created: 20',
                      'Task revision: tasks-', 'Task created: 20', 'Lineage: Current'):
            self.assertIn(value, result.stdout)
        self.assertEqual(before, {path: path.read_bytes()
                                  for path in self.root.rglob('*') if path.is_file()})

    def test_check_rejects_changed_content_stale_lineage_and_missing_metadata(self):
        self.stamp_feature()
        brief_path = self.feature / 'brief.md'
        brief_path.write_text(brief_path.read_text().replace('Trace tasks', 'Edited without revise'))
        changed = self.run_check('login')
        self.assertEqual(changed.returncode, 1)
        self.assertIn('changed without a new revision', changed.stderr)
        self.assertEqual(self.run_revise('brief', 'login').returncode, 0)
        brief_path.write_text(brief_path.read_text().replace(
            '[Reviewer and date; leave blank until approved]', 'Viviana, 2026-11-13').replace(
            '**Status:** Draft', '**Status:** Approved'))
        stale = self.run_check('login')
        self.assertEqual(stale.returncode, 1)
        self.assertIn('Regenerate the tasks', stale.stderr)
        legacy = self.make_feature('Legacy')
        (legacy / 'tasks.md').write_text(self.tasks_text())
        missing = self.run_check('legacy')
        self.assertEqual(missing.returncode, 1)
        self.assertIn('revise brief', missing.stderr)
        info = ggez.feature_status(self.root, legacy)
        self.assertEqual((info['state'], info['reason']),
                         ('Needs attention', 'Missing prerequisite'))
        self.assertIn('revise brief', dict(info['revision_fields'])['Lineage'])

    def test_check_rejects_conflicting_duplicates(self):
        self.stamp_feature()
        duplicate = self.make_feature('Duplicate')
        original = (self.feature / 'brief.md').read_text()
        (duplicate / 'brief.md').write_text(original.replace('Trace tasks', 'Different content'))
        result = self.run_check('login')
        self.assertEqual(result.returncode, 1)
        self.assertIn('Conflicting duplicate revision ID', result.stderr)

    def test_check_warns_when_identical_content_has_distinct_ids(self):
        self.stamp_feature()
        copy = self.make_feature('Copy')
        original = (self.feature / 'brief.md').read_text()
        second = ggez.revision_identity(
            'brief', original, now_ms=1794600000123, entropy=b'\xff' * 10)
        copied = ggez.replace_managed_fields(
            original, [('Revision', second.revision),
                       ('Content digest', second.content_digest)])
        (copy / 'brief.md').write_text(copied)
        result = self.run_check('login')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Identical content has multiple revision IDs', result.stdout)

    def test_check_supports_fuzzy_feature_selection(self):
        self.stamp_feature()
        beta = self.make_feature('Beta reports')
        self.assertEqual(self.run_revise('brief', 'beta-reports').returncode, 0)
        (beta / 'tasks.md').write_text(self.tasks_text())
        self.assertEqual(self.run_revise('tasks', 'beta-reports').returncode, 0)
        selected = self.run_check(answer='bta rep\n')
        self.assertEqual(selected.returncode, 0, selected.stderr)
        self.assertIn('Feature: beta-reports', selected.stdout)


if __name__ == '__main__':
    unittest.main()
