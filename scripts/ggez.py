#!/usr/bin/env python3
"""Command-line entry point for ggez."""
import argparse
import difflib
import hashlib
import json
import math
import os
import re
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

START = '<!-- ggez:start -->'
END = '<!-- ggez:end -->'
TEMPLATES = ('prd.md', 'tasks.md')
LEGACY_TEMPLATES = ('evidence.md', 'review.md')
BUNDLE = Path(__file__).resolve().parents[1] / 'templates'
MANIFEST = '.ggez/install.json'
MANIFEST_VERSION = 2


class ProjectError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ProjectError(message)


def digest(content):
    return hashlib.sha256(content).hexdigest()


def read_target(root, name):
    path = root / name
    for part in (path, *path.parents):
        if part == root:
            break
        require(not part.is_symlink(), 'Resolve symlink before init: ' + str(part))
        if part != path and part.exists():
            require(part.is_dir(), 'Expected directory: ' + str(part))
    if not path.exists():
        return None
    require(path.is_file(), 'Expected file: ' + str(path))
    return path.read_bytes()


def agent_block(content):
    text = content.decode('utf-8')
    if START not in text and END not in text:
        return None
    require(text.count(START) == 1 and text.count(END) == 1,
            'Resolve duplicate or incomplete ggez markers in AGENTS.md.')
    start, end = text.index(START), text.index(END)
    require(start < end, 'Resolve reversed ggez markers in AGENTS.md.')
    return text[start:end + len(END)].encode()


def plan_init(root):
    require(root.is_dir(), 'Create the project directory first, then run ggez init.')
    manifest_bytes = read_target(root, MANIFEST)
    hashes = {}
    manifest_version = None
    names = {'AGENTS.md', *('.ggez/templates/' + name for name in TEMPLATES)}
    legacy_names = names | {'.ggez/templates/' + name for name in LEGACY_TEMPLATES}
    if manifest_bytes is not None:
        try:
            manifest = json.loads(manifest_bytes)
            require(isinstance(manifest, dict) and set(manifest) == {'version', 'files'}
                    and type(manifest['version']) is int
                    and manifest['version'] in (1, MANIFEST_VERSION),
                    'Invalid init manifest; restore it before retrying.')
            manifest_version = manifest['version']
            hashes = manifest['files']
            expected_names = legacy_names if manifest_version == 1 else names
            require(isinstance(hashes, dict) and set(hashes) == expected_names
                    and all(isinstance(value, str) and len(value) == 64
                            and all(c in '0123456789abcdef' for c in value) for value in hashes.values()),
                    'Invalid init manifest; restore it before retrying.')
        except (ValueError, TypeError) as exc:
            raise ProjectError('Invalid init manifest; restore it before retrying.') from exc
    desired = {'.ggez/templates/' + name: (BUNDLE / name).read_bytes() for name in TEMPLATES}
    block = (START + '\n' + (BUNDLE / 'agent-rules.md').read_text().rstrip() + '\n' + END).encode()
    agents = read_target(root, 'AGENTS.md')
    old_block = agent_block(agents) if agents is not None else None
    if old_block is not None:
        require(old_block == block or hashes.get('AGENTS.md') == digest(old_block),
                'Conflict: edited ggez instructions in AGENTS.md. Resolve them before retrying.')
        desired['AGENTS.md'] = agents.replace(old_block, block, 1)
    else:
        require('AGENTS.md' not in hashes, 'Conflict: managed ggez instructions were removed from AGENTS.md.')
        existing = agents or b''
        require(not re.search(r'^#{1,6}\s+ggez workflow\s*#*\s*$',
                              existing.decode('utf-8'), re.I | re.M),
                'Conflict: unmarked ggez section in AGENTS.md. Resolve it before retrying.')
        separator = b'' if not existing or existing.endswith(b'\n\n') else (b'\n' if existing.endswith(b'\n') else b'\n\n')
        desired['AGENTS.md'] = existing + separator + block + b'\n'
    before = {}
    for name, content in desired.items():
        current = read_target(root, name)
        before[name] = current
        if name != 'AGENTS.md' and current is not None and current != content:
            require(hashes.get(name) == digest(current),
                    'Conflict: edited or unrelated template ' + name + '. Resolve it before retrying.')
        if name in hashes and current is None:
            raise ProjectError('Conflict: managed file was removed: ' + name)
    if manifest_version == 1:
        for template in LEGACY_TEMPLATES:
            name = '.ggez/templates/' + template
            current = read_target(root, name)
            before[name] = current
            if current is not None:
                require(hashes.get(name) == digest(current),
                        'Conflict: edited legacy template ' + name + '. Resolve it before retrying.')
            desired[name] = None
    new_hashes = {name: digest(block if name == 'AGENTS.md' else content)
                  for name, content in desired.items() if content is not None}
    desired[MANIFEST] = (json.dumps({'version': MANIFEST_VERSION, 'files': new_hashes},
                                    indent=2, sort_keys=True) + '\n').encode()
    before[MANIFEST] = manifest_bytes
    return before, desired


def apply_init(root, before, desired):
    changed = [name for name in desired if before[name] != desired[name]]
    if not changed:
        return
    stage = Path(tempfile.mkdtemp(prefix='.ggez-init-', dir=root))
    applied, directories = [], []
    retain_stage = False
    try:
        for index, name in enumerate(changed):
            if desired[name] is not None:
                file = stage / str(index)
                file.write_bytes(desired[name])
                mode = stat.S_IMODE((root / name).stat().st_mode) if before[name] is not None else 0o644
                file.chmod(mode)
            if before[name] is not None:
                backup = stage / ('backup-' + str(index))
                backup.write_bytes(before[name])
                backup.chmod(stat.S_IMODE((root / name).stat().st_mode))
        # Refuse a stale preview before changing any project files.
        require(all(read_target(root, name) == old for name, old in before.items()),
                'Project changed after preview. Run init again.')
        for index, name in enumerate(changed):
            target = root / name
            missing = []
            parent = target.parent
            while parent != root and not parent.exists():
                missing.append(parent)
                parent = parent.parent
            for directory in reversed(missing):
                directory.mkdir()
                directories.append(directory)
            require(read_target(root, name) == before[name], 'Project changed during init: ' + name)
            if desired[name] is None:
                target.unlink()
            else:
                os.replace(stage / str(index), target)
            applied.append((index, name))
    except (OSError, ProjectError, KeyboardInterrupt):
        for index, name in reversed(applied):
            try:
                require(read_target(root, name) == desired[name], 'File changed during rollback: ' + name)
                if before[name] is None:
                    if desired[name] is not None:
                        (root / name).unlink()
                else:
                    os.replace(stage / ('backup-' + str(index)), root / name)
            except (OSError, ProjectError):
                retain_stage = True
        for directory in reversed(directories):
            try:
                directory.rmdir()
            except OSError:
                pass
        if retain_stage:
            raise ProjectError('Init failed; preserve and inspect recovery files in ' + str(stage))
        raise
    finally:
        if not retain_stage:
            shutil.rmtree(stage)


def init_project(args):
    root = args.directory.resolve()
    before, desired = plan_init(root)
    changed = [name for name in desired if before[name] != desired[name]]
    if not changed:
        print('Already initialized; no changes.')
        return 0
    print('Init preview: ' + str(root))
    for name in changed:
        action = 'Remove ' if desired[name] is None else ('Create ' if before[name] is None else 'Update ')
        print(action + name)
    if 'AGENTS.md' in changed:
        old = (before['AGENTS.md'] or b'').decode('utf-8')
        new = desired['AGENTS.md'].decode('utf-8')
        print(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                         fromfile='AGENTS.md (current)', tofile='AGENTS.md (proposed)')))
        if old:
            print('Check these instructions against your existing project rules; resolve conflicts before applying.')
    if args.dry_run:
        print('Preview only; no files changed.')
        return 0
    if not args.yes:
        try:
            response = input('Apply this preview and confirm the rules are compatible? [y/N] ')
        except EOFError:
            response = ''
        if response.strip().lower() not in ('y', 'yes'):
            print('Cancelled; no files changed. Use --yes after reviewing the preview.')
            return 0
    apply_init(root, before, desired)
    print('Initialized. Start a blank Brief from .ggez/templates/prd.md; fill Slice and Outcome yourself.')
    return 0


def project_root(directory):
    root = directory.resolve()
    manifest = read_target(root, MANIFEST)
    require(manifest is not None, 'Project is not initialized. Run ggez init first.')
    try:
        record = json.loads(manifest)
        require(isinstance(record, dict) and record.get('version') in (1, MANIFEST_VERSION)
                and isinstance(record.get('files'), dict), 'Invalid init manifest. Run ggez init to inspect it.')
    except ValueError as exc:
        raise ProjectError('Invalid init manifest. Run ggez init to inspect it.') from exc
    return root


def feature_paths(root):
    folder = root / 'features'
    require(not folder.is_symlink(), 'Resolve symlink before planning: ' + str(folder))
    if not folder.exists():
        return []
    require(folder.is_dir(), 'Expected directory: ' + str(folder))
    paths = []
    for path in sorted(folder.iterdir()):
        require(not path.is_symlink(), 'Resolve feature symlink: ' + path.name)
        if path.is_dir() and read_target(root, 'features/' + path.name + '/brief.md') is not None:
            paths.append(path)
    return paths


def choose_feature(paths, allow_new=False):
    for index, path in enumerate(paths, 1):
        print(str(index) + '. ' + path.name)
    if allow_new:
        print('0. New feature')
    try:
        choice = input('Choose a number, or Enter to cancel: ').strip()
    except EOFError:
        choice = ''
    if not choice:
        return None
    if allow_new and choice == '0':
        return 'new'
    require(choice.isascii() and choice.isdigit() and 1 <= int(choice) <= len(paths),
            'Choose one of the listed numbers.')
    return paths[int(choice) - 1]


def create_feature(root, title):
    title = title.strip()
    require(1 <= len(title) <= 100 and not any(ord(c) < 32 or ord(c) == 127 for c in title)
            and '/' not in title and '\\' not in title and title not in ('.', '..'),
            'Use a title of 1–100 characters without paths or control characters.')
    template = read_target(root, '.ggez/templates/prd.md')
    require(template is not None, 'Brief template is missing. Restore it before planning.')
    text = template.decode('utf-8')
    require(text.startswith('# [Feature name] — Brief\n'), 'Brief template needs its original title placeholder.')
    # Replacing only the title preserves every required and optional placeholder.
    text = text.replace('# [Feature name] — Brief', '# ' + title + ' — Brief', 1)
    feature_paths(root)
    folder = root / 'features'
    created_folder = not folder.exists()
    folder.mkdir(exist_ok=True)
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:60].rstrip('-') or 'feature'
    path = None
    try:
        for number in range(1, 1001):
            candidate = folder / (slug if number == 1 else slug + '-' + str(number))
            try:
                candidate.mkdir()
            except FileExistsError:
                continue
            path = candidate
            break
        require(path is not None, 'Too many features with this title. Choose a different title.')
        with (path / 'brief.md').open('x', encoding='utf-8') as output:
            output.write(text)
        return path
    except (OSError, ProjectError, KeyboardInterrupt):
        if path is not None:
            (path / 'brief.md').unlink(missing_ok=True)
            path.rmdir()
        if created_folder:
            try:
                folder.rmdir()
            except OSError:
                pass
        raise


def print_handoff(path):
    print('Brief: ' + str(path / 'brief.md'))
    print('Loop: fill Brief → approve tasks → build and test → accept the outcome.')
    print('\nCopy into Codex, Cursor, or Claude:')
    print('Read AGENTS.md and ' + str(path / 'brief.md') + '. '
          'I fill Slice and Outcome; never fill those required sections for me. '
          'After I approve the Brief, prepare tasks for my approval. '
          'Execute only approved tasks. Each task has one Result: Pending, Pass, Fail, Blocked, '
          'or Interrupted; check it only with Pass. Verified is default: test one task, update its '
          'Result, then wait for my review. If I explicitly choose Unverified, continue approved '
          'tasks after tests. Stop on failures or blockers. Final Brief acceptance is mine.')


def plan_feature(args):
    root = project_root(args.project)
    if args.title is not None:
        path = create_feature(root, args.title)
    else:
        selected = choose_feature(feature_paths(root), allow_new=True)
        if selected is None:
            print('Cancelled; no files changed.')
            return 0
        if selected == 'new':
            try:
                title = input('Feature title (Enter to cancel): ')
            except EOFError:
                title = ''
            if not title.strip():
                print('Cancelled; no files changed.')
                return 0
            path = create_feature(root, title)
        else:
            path = selected
    print_handoff(path)
    return 0


def field(text, name):
    values = re.findall(r'^\*\*' + re.escape(name) + r':\*\*[ \t]*([^\n]*)', text, re.M)
    require(len(values) <= 1, 'Duplicate field: ' + name)
    value = values[0].strip() if values else ''
    return '' if value.startswith('[') else value


def section(text, heading):
    match = re.search(r'^## ' + re.escape(heading) + r'\s*\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    return match.group(1) if match else ''


def approved(text):
    value = field(text, 'Approval')
    if value and not re.match(r'^(pending|none|not approved|unapproved|draft)\b', value, re.I):
        return True
    return bool(re.search(r'^Approved by \S', text, re.M))


def read_document(root, name):
    content = read_target(root, name)
    return content.decode('utf-8') if content is not None else ''


def read_tasks(text):
    queue = section(text, 'Queue')
    matches = list(re.finditer(
        r'^- \[([ xX])\] (TASK-[1-9][0-9]*) (?:—|-) ([^\n]+)\n(.*?)(?=^- \[[ xX]\] TASK-|\Z)',
        queue, re.M | re.S))
    require(len(matches) == len(re.findall(r'^- \[.*\].*TASK-', queue, re.M)),
            'Malformed task queue; use the task template.')
    rows = []
    for match in matches:
        check, task_id, title, body = match.groups()
        results = re.findall(r'^\s+- \*\*Result:\*\*[ \t]*([^\n]+)', body, re.M)
        require(len(results) == 1, task_id + ' needs exactly one Result in tasks.md.')
        result = results[0].strip()
        require(result in ('Pending', 'Pass', 'Fail', 'Blocked', 'Interrupted'),
                'Invalid task Result for ' + task_id)
        checked = check.lower() == 'x'
        require(checked == (result == 'Pass'),
                task_id + ' must be checked exactly when Result is Pass.')
        rows.append((task_id, title, checked, result))
    require(len({row[0] for row in rows}) == len(rows), 'Duplicate task ID in tasks.md.')
    return rows


def acceptance_checks(text):
    body = section(text, 'Acceptance checks')
    matches = re.findall(r'^- \[([ xX])\] .+$', body, re.M)
    require(len(matches) == len(re.findall(r'^- \[.*\]', body, re.M)),
            'Malformed Brief acceptance checks.')
    return [check.lower() == 'x' for check in matches]


def execution_time(root, feature_id):
    text = read_document(root, '.ggez/features/' + feature_id + '/usage.jsonl')
    if not text.strip():
        return 'Unavailable (no execution records)'
    attempts = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise ProjectError('Malformed usage.jsonl; repair the execution records.') from exc
        require(isinstance(row, dict) and isinstance(row.get('attempt_id'), str)
                and bool(row['attempt_id'].strip()), 'Each usage record needs an attempt_id.')
        attempt_id = row['attempt_id']
        require(attempt_id not in attempts or attempts[attempt_id] == row,
                'Conflicting usage records for attempt ' + attempt_id)
        seconds = row.get('execution_seconds')
        require(seconds is None or type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0,
                'execution_seconds must be a finite, nonnegative number.')
        require(type(row.get('timing_complete', True)) is bool, 'timing_complete must be true or false.')
        attempts[attempt_id] = row
    measured = [row for row in attempts.values() if row.get('execution_seconds') is not None]
    if not measured:
        return 'Unavailable (execution time was not reported)'
    seconds = sum(row['execution_seconds'] for row in measured)
    require(math.isfinite(seconds), 'Recorded execution time exceeds the supported range.')
    partial = len(measured) != len(attempts) or any(not row.get('timing_complete', True) for row in measured)
    return format(seconds, '.1f') + 's recorded' + (' (partial coverage)' if partial else '')


def feature_status(root, path):
    base = 'features/' + path.name + '/'
    brief = read_document(root, base + 'brief.md')
    require(bool(brief), 'Brief is missing or empty: ' + base + 'brief.md')
    tasks = read_document(root, base + 'tasks.md')
    rows = read_tasks(tasks)
    passed = {task_id for task_id, _, checked, result in rows if checked and result == 'Pass'}
    pending = [(task_id, title) for task_id, title, _, _ in rows if task_id not in passed]
    result = {'goal': field(brief, 'Goal') or 'Not filled in', 'stage': 'Brief',
              'state': 'Needs attention', 'reason': 'Approval required',
              'current': pending[0][0] + ' — ' + pending[0][1] if pending else 'None',
              'completed': len(passed), 'total': len(rows), 'next': 'Fill the Brief and record human approval.',
              'time': execution_time(root, path.name)}
    if not approved(brief) or not field(brief, 'Goal'):
        return result
    result['stage'] = 'Tasks'
    if not rows:
        result.update(reason='Missing prerequisite', next='Prepare tasks from the template for approval.')
        return result
    if not approved(tasks):
        result['next'] = 'Review the task list and record human approval.'
        return result
    result['stage'] = 'Implementation'
    for _, _, _, task_result in rows:
        reason = {'Fail': 'Check failed', 'Blocked': 'Missing prerequisite',
                  'Interrupted': 'Run interrupted'}.get(task_result)
        if reason:
            result.update(reason=reason, next='Resolve the current task result before continuing.')
            return result
    if len(passed) == len(rows):
        result['stage'] = 'Review'
        checks = acceptance_checks(brief)
        if checks and all(checks):
            result.update(state='Complete', reason='', next='Outcome accepted.')
        else:
            result['next'] = 'Review the outcome and check every Brief acceptance item.'
        return result
    result.update(state='Ready', reason='', next='Continue the first unfinished approved task with your agent.')
    return result


def status_project(args):
    root = project_root(args.project)
    paths = feature_paths(root)
    if args.feature:
        matches = [path for path in paths if path.name == args.feature]
        require(bool(matches), 'Feature not found. Run ggez plan to list this project’s features.')
        path = matches[0]
    elif len(paths) == 1:
        path = paths[0]
    elif not paths:
        print('No features yet. Start one with ggez plan "Feature title".')
        return 0
    else:
        path = choose_feature(paths)
        if path is None:
            print('Cancelled; no files changed.')
            return 0
    info = feature_status(root, path)
    # Keep document text from emitting terminal control sequences.
    def show(label, value):
        clean = ''.join(c if c.isprintable() else ' ' for c in str(value))
        print(label + ': ' + clean)
    show('Feature', path.name)
    show('Current task', info['current'])
    show('Stage', info['stage'])
    count = str(info['completed']) + '/' + str(info['total'])
    percent = format(100 * info['completed'] / info['total'], '.0f') + '%' if info['total'] else 'Not available'
    show('Completed', count + ' (' + percent + ')')
    show('Execution time', info['time'])
    for name in ('brief.md', 'tasks.md'):
        if (path / name).is_file():
            show(name, path / name)
    return 0


def installation_prefix():
    script = Path(__file__).resolve()
    parents = script.parents
    require(len(parents) > 5 and parents[0].name == 'scripts'
            and parents[2].name == 'releases' and parents[3].name == 'ggez'
            and parents[4].name == 'share',
            'Update is available only from a managed ggez installation. Reinstall ggez, then retry.')
    prefix = parents[5]
    launcher = prefix / 'bin/ggez'
    require(not launcher.is_symlink() and launcher.is_file(),
            'Managed ggez launcher is missing. Reinstall ggez, then retry.')
    text = launcher.read_text()
    require(text.startswith('#!/bin/sh\n# ggez-managed-launcher-v1\n') and str(script) in text,
            'Managed ggez launcher does not match this release. Reinstall ggez, then retry.')
    installer = script.with_name('install.py')
    require(not installer.is_symlink() and installer.is_file(),
            'This ggez release cannot update itself. Reinstall ggez, then retry.')
    return prefix, installer


def update_cli():
    prefix, installer = installation_prefix()
    result = subprocess.run([sys.executable, '-B', str(installer), '--prefix', str(prefix)])
    return result.returncode


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='ggez', description='Plan features, approve tasks, and track progress.')
    commands = parser.add_subparsers(dest='command')
    init = commands.add_parser('init', help='Preview and install ggez in a project.')
    init.add_argument('directory', nargs='?', type=Path, default=Path('.'))
    init.add_argument('--dry-run', action='store_true', help='Preview without writing files.')
    init.add_argument('--yes', action='store_true', help='Confirm the preview and compatibility with existing rules.')
    plan = commands.add_parser('plan', help='Create a blank Brief or select a feature.')
    plan.add_argument('title', nargs='?')
    plan.add_argument('--project', type=Path, default=Path('.'))
    status = commands.add_parser('status', help='Show task progress, recorded time, and file paths.')
    status.add_argument('feature', nargs='?')
    status.add_argument('--project', type=Path, default=Path('.'))
    commands.add_parser('update', help='Download, validate, and activate the latest ggez release.')
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            return init_project(args)
        if args.command == 'plan':
            return plan_feature(args)
        if args.command == 'status':
            return status_project(args)
        if args.command == 'update':
            return update_cli()
        if read_target(Path.cwd().resolve(), MANIFEST) is not None:
            return status_project(argparse.Namespace(project=Path.cwd(), feature=None))
        parser.print_help()
        print('\nStart here: ggez init --dry-run')
        return 0
    except (ProjectError, OSError, UnicodeError) as exc:
        print('ggez: ' + str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\nggez: cancelled.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
