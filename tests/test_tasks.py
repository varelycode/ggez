import copy
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('tasks', ROOT / 'scripts/tasks.py')
tasks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tasks)


class TaskFilesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / 'templates/ralph/.agent', self.root / '.agent')
        for path in (self.root / '.agent').rglob('*.json'):
            path.write_text(re.sub(r'\{\{.*?\}\}', 'Concrete fixture result', path.read_text()))
        self.index_path = self.root / '.agent/tasks.json'
        self.spec_path = self.root / '.agent/tasks/TASK-2.json'
        self.index = json.loads(self.index_path.read_text())
        self.spec = json.loads(self.spec_path.read_text())

    def save(self):
        self.index_path.write_text(json.dumps(self.index))
        self.spec_path.write_text(json.dumps(self.spec))

    def test_valid_unstarted_queue(self):
        records = tasks.load_tasks(self.root)
        self.assertEqual([row['id'] for row, _ in records], ['TASK-1', 'TASK-2'])
        self.assertFalse(any(row['passes'] for row, _ in records))

    def test_template_requires_explicit_placeholder_flag(self):
        template = ROOT / 'templates/ralph'
        with self.assertRaisesRegex(tasks.TaskError, 'placeholders'):
            tasks.load_tasks(template)
        self.assertEqual(len(tasks.load_tasks(template, allow_placeholders=True)), 2)

    def test_rejects_invalid_specs(self):
        mutations = [
            lambda s: s.pop('acceptanceCriteria'),
            lambda s: s.update(acceptanceCriteria=[]),
            lambda s: s.update(id='TASK-9'),
            lambda s: s.update(title='Mismatched title'),
            lambda s: s.update(category='Different category'),
            lambda s: s.update(unknownField=True),
            lambda s: s['steps'][0].update(step=2),
            lambda s: s['steps'][0].update(**{'pass': 'false'}),
            lambda s: s['steps'][1].update(description='No verification marker'),
            lambda s: s.update(dependencies=['TASK-99']),
            lambda s: s.update(dependencies=['TASK-2']),
            lambda s: s.update(dependencies=['TASK-1', 'TASK-1']),
            lambda s: s.update(estimatedComplexity='unknown'),
        ]
        original = copy.deepcopy(self.spec)
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                self.spec = copy.deepcopy(original)
                mutate(self.spec)
                self.save()
                with self.assertRaises(tasks.TaskError):
                    tasks.load_tasks(self.root)

    def test_rejects_duplicate_ids_and_false_boolean(self):
        self.index.append(self.index[0])
        self.save()
        with self.assertRaisesRegex(tasks.TaskError, 'duplicate ID'):
            tasks.load_tasks(self.root)
        self.index.pop()
        self.index[0]['passes'] = 0
        self.save()
        with self.assertRaisesRegex(tasks.TaskError, 'boolean'):
            tasks.load_tasks(self.root)

    def test_requires_setup_first(self):
        self.index.reverse()
        self.spec['dependencies'] = []
        self.save()
        with self.assertRaisesRegex(tasks.TaskError, 'First task'):
            tasks.load_tasks(self.root)

    def test_rejects_missing_spec_and_unsafe_path(self):
        self.spec_path.unlink()
        with self.assertRaisesRegex(tasks.TaskError, 'Cannot read JSON'):
            tasks.load_tasks(self.root)
        self.index[1]['specFilePath'] = '../outside.json'
        self.save()
        with self.assertRaisesRegex(tasks.TaskError, 'specFilePath'):
            tasks.load_tasks(self.root)

    def test_rejects_symlink_outside_root(self):
        external = self.root.parent / (self.root.name + '-outside.json')
        external.write_text(json.dumps(self.spec))
        self.addCleanup(external.unlink)
        self.spec_path.unlink()
        self.spec_path.symlink_to(external)
        with self.assertRaisesRegex(tasks.TaskError, 'outside root'):
            tasks.load_tasks(self.root)

    def test_rejects_completed_task_with_unfinished_steps_or_dependency(self):
        self.index[1]['passes'] = True
        self.save()
        with self.assertRaisesRegex(tasks.TaskError, 'unfinished steps'):
            tasks.load_tasks(self.root)
        for step in self.spec['steps']:
            step['pass'] = True
        self.save()
        with self.assertRaisesRegex(tasks.TaskError, 'incomplete dependency'):
            tasks.load_tasks(self.root)

    def test_completed_queue_renders_from_json_without_writing(self):
        for row in self.index:
            row['passes'] = True
            path = self.root / row['specFilePath']
            spec = json.loads(path.read_text())
            for step in spec['steps']:
                step['pass'] = True
            path.write_text(json.dumps(spec))
        self.index_path.write_text(json.dumps(self.index))
        before = {p: p.read_bytes() for p in self.root.rglob('*.json')}
        output = tasks.render(tasks.load_tasks(self.root), 'Test', 'brief.md', 'evidence.md')
        self.assertIn('- [x] TASK-2', output)
        self.assertIn('None — queue complete', output)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*.json')})

    def test_render_preserves_details_constraints_and_step_state(self):
        self.spec['description'] = '<script>unsafe</script>\n## Heading'
        self.spec['technicalNotes'] += ['Ordinary technical note']
        self.spec['steps'][0]['pass'] = True
        self.save()
        output = tasks.render(tasks.load_tasks(self.root), 'Test', 'brief.md', 'evidence.md')
        for text in ['Done when:', 'Verify:', 'Must not:', 'Depends on: TASK-1',
                     'Ordinary technical note', '- [x] 1.', '- [ ] TASK-2',
                     '**Next task:** TASK-1', '&lt;script&gt;']:
            self.assertIn(text, output)
        self.assertNotIn('<script>', output)
        self.assertNotIn('**Blocked by:** Nothing', output)

    def test_duplicate_json_keys_are_rejected(self):
        self.spec_path.write_text('{"id":"TASK-2","id":"TASK-3"}')
        with self.assertRaisesRegex(tasks.TaskError, 'duplicate JSON key'):
            tasks.load_tasks(self.root)

    def test_cli_rejects_invalid_input_without_a_partial_view(self):
        self.spec_path.write_text('{broken')
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/tasks.py'),
                                 'render', '--root', str(self.root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertIn('Invalid tasks:', result.stderr)


if __name__ == '__main__':
    unittest.main()
