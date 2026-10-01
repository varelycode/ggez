#!/usr/bin/env python3
"""Validate Ralph tasks and render a read-only Markdown checklist."""
import argparse
import json
from pathlib import Path
import re
import sys


class TaskError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise TaskError(message)


def object_fields(value, required, optional, label):
    require(isinstance(value, dict), f'{label}: expected an object')
    require(required <= value.keys(), f'{label}: missing fields {sorted(required - value.keys())}')
    require(value.keys() <= required | optional, f'{label}: unknown fields {sorted(value.keys() - required - optional)}')


def nonempty(value, label):
    require(isinstance(value, str) and bool(value.strip()), f'{label}: expected nonempty text')


def strings(value, label, minimum=0):
    require(isinstance(value, list) and len(value) >= minimum, f'{label}: expected a list with at least {minimum} entries')
    for entry in value:
        nonempty(entry, label)


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f'{path.name}: duplicate JSON key {key}')
            result[key] = value
        return result
    try:
        return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TaskError(f'Cannot read JSON: {path}') from exc


def load_tasks(root, allow_placeholders=False):
    root = Path(root).resolve()
    index = read_json(root / '.agent/tasks.json')
    require(isinstance(index, list) and bool(index), 'Task index must be a nonempty array')
    tasks = []
    seen = {}
    for row in index:
        object_fields(row, {'id', 'title', 'category', 'specFilePath', 'passes'}, set(), 'Index entry')
        task_id = row['id']
        require(isinstance(task_id, str) and re.fullmatch(r'TASK-[1-9][0-9]*', task_id), 'Invalid task ID')
        require(task_id not in seen, f'{task_id}: duplicate ID')
        for key in ('title', 'category'):
            nonempty(row[key], f'{task_id}.{key}')
        require(type(row['passes']) is bool, f'{task_id}: passes must be boolean')
        expected = f'.agent/tasks/{task_id}.json'
        require(row['specFilePath'] == expected, f'{task_id}: specFilePath must be {expected}')
        path = (root / expected).resolve()
        require(root in path.parents, f'{task_id}: spec resolves outside root')
        spec = read_json(path)
        object_fields(spec, {'id', 'title', 'category', 'description', 'acceptanceCriteria', 'steps'},
                      {'dependencies', 'estimatedComplexity', 'technicalNotes'}, task_id)
        for key in ('id', 'title', 'category'):
            require(spec[key] == row[key], f'{task_id}: index/spec {key} mismatch')
        nonempty(spec['description'], f'{task_id}.description')
        strings(spec['acceptanceCriteria'], f'{task_id}.acceptanceCriteria', 1)
        steps = spec['steps']
        require(isinstance(steps, list) and bool(steps), f'{task_id}: steps must be nonempty')
        for number, step in enumerate(steps, 1):
            object_fields(step, {'step', 'description', 'details', 'pass'}, set(), f'{task_id} step {number}')
            require(type(step['step']) is int and step['step'] == number, f'{task_id}: steps must be sequential from 1')
            nonempty(step['description'], f'{task_id} step description')
            nonempty(step['details'], f'{task_id} step details')
            require(type(step['pass']) is bool, f'{task_id}: step pass must be boolean')
        require(any(step['description'].startswith('Verify:') for step in steps), f'{task_id}: add a Verify: step')
        require(not row['passes'] or all(step['pass'] for step in steps), f'{task_id}: complete task has unfinished steps')
        deps = spec.get('dependencies', [])
        strings(deps, f'{task_id}.dependencies')
        require(len(deps) == len(set(deps)), f'{task_id}: duplicate dependencies')
        for dep in deps:
            require(dep in seen, f'{task_id}: dependency {dep} must exist earlier in the queue')
            require(not row['passes'] or seen[dep], f'{task_id}: complete task has an incomplete dependency')
        if not tasks:
            require(task_id == 'TASK-1' and row['category'] == 'setup', 'First task must be TASK-1, category setup')
            require(row['title'] == 'Verify project prerequisites and access', 'TASK-1 must verify prerequisites')
        if 'estimatedComplexity' in spec:
            require(spec['estimatedComplexity'] in ('low', 'medium', 'high', 'very high'), f'{task_id}: invalid complexity')
        if 'technicalNotes' in spec:
            strings(spec['technicalNotes'], f'{task_id}.technicalNotes')
        if not allow_placeholders:
            require(not re.search(r'\{\{.*?\}\}', json.dumps([row, spec])), f'{task_id}: replace template placeholders')
        seen[task_id] = row['passes']
        tasks.append((row, spec))
    return tasks


def markdown(value):
    value = ' '.join(value.split())
    value = value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return re.sub(r'([\\`*_\[\]#|])', r'\\\1', value)


def render(tasks, title, brief, evidence):
    lines = [f'# {markdown(title)} — Tasks', '',
             '> Generated from Ralph JSON. Edit JSON and regenerate; checklist edits do not update task state.', '',
             f'**Brief:** {markdown(brief)}', '', f'**Evidence:** {markdown(evidence)}', '', '## Queue', '']
    for row, spec in tasks:
        checked = 'x' if row['passes'] else ' '
        lines += [f'- [{checked}] {row["id"]} — {markdown(row["title"])}', '',
                  '  - Done when: ' + '; '.join(markdown(s) for s in spec['acceptanceCriteria'])]
        verification = [s for s in spec['steps'] if s['description'].startswith('Verify:')]
        lines += ['  - Verify: ' + '; '.join(markdown(s['description'][7:].strip() + ': ' + s['details']) for s in verification)]
        notes = spec.get('technicalNotes', [])
        exclusions = [n[len('Must not:'):].strip() for n in notes if n.startswith('Must not:')]
        if exclusions:
            lines += ['  - Must not: ' + '; '.join(markdown(n) for n in exclusions)]
        if spec.get('dependencies'):
            lines += ['  - Depends on: ' + ', '.join(spec['dependencies'])]
        lines += ['', '  <details>', '  <summary>Implementation details</summary>', '',
                  '  ' + markdown(spec['description']), '', '  Category: ' + markdown(spec['category'])]
        if 'estimatedComplexity' in spec:
            lines += ['  Complexity: ' + markdown(spec['estimatedComplexity'])]
        lines += ['']
        for step in spec['steps']:
            checked = 'x' if step['pass'] else ' '
            lines += [f'  - [{checked}] {step["step"]}. {markdown(step["description"])}: {markdown(step["details"])}']
        remaining = [n for n in notes if not n.startswith('Must not:')]
        if remaining:
            lines += ['', '  Notes: ' + '; '.join(markdown(n) for n in remaining)]
        lines += ['', '  </details>', '']
    next_task = next((row for row, _ in tasks if not row['passes']), None)
    status = f'{next_task["id"]} — {markdown(next_task["title"])}' if next_task else 'None — queue complete'
    lines += ['## Ralph rules', '',
              '1. Read the Brief. Work on the first unchecked task only; stop if blocked.',
              '2. Stay within its scope and honor the Brief’s stop conditions.',
              '3. Record checks, failures, corrections, and results in Evidence. Keep secrets and private data out.',
              '4. Update JSON completion fields only after verification, then regenerate this view.',
              '5. Stop on scope expansion or repeated failure; record the blocker in Evidence.', '',
              '## Status', '', f'**Next task:** {status}', '',
              '**Blocked by:** Runtime blockers are recorded in Evidence, not in task JSON.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('validate', 'render'))
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--allow-placeholders', action='store_true', help='Inspect templates only; not ready for execution')
    parser.add_argument('--title', default='Feature')
    parser.add_argument('--brief', default='.agent/prd/PRD.md')
    parser.add_argument('--evidence', default='Not created yet')
    args = parser.parse_args()
    try:
        tasks = load_tasks(args.root, args.allow_placeholders)
        if args.command == 'render':
            print(render(tasks, args.title, args.brief, args.evidence), end='')
        else:
            suffix = ' (template placeholders allowed)' if args.allow_placeholders else ''
            print(f'Validated {len(tasks)} task records{suffix}. Implementation and evidence were not checked.')
    except TaskError as exc:
        print(f'Invalid tasks: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
