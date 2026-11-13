#!/usr/bin/env python3
"""Command-line entry point for ggez."""
import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
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
import time
import uuid

START = '<!-- ggez:start -->'
END = '<!-- ggez:end -->'
TEMPLATES = ('prd.md', 'tasks.md')
LEGACY_TEMPLATES = ('evidence.md', 'review.md')
BUNDLE = Path(__file__).resolve().parents[1] / 'templates'
MANIFEST = '.ggez/install.json'
MANIFEST_VERSION = 2
VERSION = '0.1.0'


# Revision identities

REVISION_KINDS = ('brief', 'tasks')
REVISION_RE = re.compile(
    r'^(brief|tasks)-([0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})-([0-9a-f]{16})$')


class RevisionError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedRevision:
    kind: str
    identifier: uuid.UUID
    digest_prefix: str


@dataclass(frozen=True)
class RevisionIdentity:
    revision: str
    content_digest: str


def revision_require(condition, message):
    if not condition:
        raise RevisionError(message)


def canonical_definition(content, kind):
    revision_require(kind in REVISION_KINDS, 'Unknown revision kind: ' + str(kind))
    text = content.replace('\r\n', '\n').replace('\r', '\n')
    ignored = {'Revision', 'Content digest', 'Approval'}
    if kind == 'brief':
        ignored.add('Status')
    output = []
    for line in text.splitlines():
        match = re.match(r'^\*\*([^*]+):\*\*', line)
        if match and match.group(1) in ignored:
            continue
        if kind == 'tasks' and re.match(r'^\*\*Next task:\*\*', line):
            continue
        if kind == 'tasks' and re.match(r'^\s+- \*\*Result:\*\*', line):
            line = re.sub(r'^(\s+- \*\*Result:\*\*).*$', r'\1 Pending', line)
        line = re.sub(r'^(\s*- )\[[ xX]\](?= )', r'\1[ ]', line)
        if not line and output and not output[-1]:
            continue
        output.append(line)
    while output and not output[-1]:
        output.pop()
    return '\n'.join(output) + '\n'


def definition_digest(content, kind):
    canonical = canonical_definition(content, kind).encode('utf-8')
    return hashlib.sha256(canonical).hexdigest()


def uuid7(now_ms=None, entropy=None):
    milliseconds = int(time.time() * 1000) if now_ms is None else now_ms
    revision_require(type(milliseconds) is int and 0 <= milliseconds < 1 << 48,
                     'UUIDv7 time must be an integer from 0 through 2^48-1 milliseconds.')
    random_bytes = os.urandom(10) if entropy is None else entropy
    revision_require(isinstance(random_bytes, bytes) and len(random_bytes) == 10,
                     'UUIDv7 entropy must contain exactly 10 bytes.')
    random_bits = int.from_bytes(random_bytes, 'big') & ((1 << 74) - 1)
    random_a = random_bits >> 62
    random_b = random_bits & ((1 << 62) - 1)
    value = (milliseconds << 80) | (0x7 << 76) | (random_a << 64) | (0b10 << 62) | random_b
    return uuid.UUID(int=value)


def parse_revision_id(value, expected_kind=None):
    match = REVISION_RE.fullmatch(value or '')
    revision_require(bool(match), 'Invalid revision ID: ' + str(value))
    kind, uuid_text, digest_prefix = match.groups()
    revision_require(expected_kind is None or kind == expected_kind,
                     'Expected a ' + str(expected_kind) + ' revision ID.')
    identifier = uuid.UUID(uuid_text)
    revision_require(identifier.version == 7 and identifier.variant == uuid.RFC_4122,
                     'Invalid UUIDv7 revision ID: ' + value)
    return ParsedRevision(kind, identifier, digest_prefix)


def revision_created_at(value):
    parsed = parse_revision_id(value)
    milliseconds = parsed.identifier.int >> 80
    created = datetime.fromtimestamp(milliseconds / 1000, timezone.utc)
    return created.isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def validate_full_digest(value):
    revision_require(bool(re.fullmatch(r'sha256:[0-9a-f]{64}', value or '')),
                     'Invalid revision content digest: ' + str(value))
    return value[7:]


def verify_revision(value, stored_digest, content, kind):
    parsed = parse_revision_id(value, kind)
    full_digest = validate_full_digest(stored_digest)
    revision_require(parsed.digest_prefix == full_digest[:16],
                     'Revision ID digest does not match its content digest.')
    revision_require(full_digest == definition_digest(content, kind),
                     'Revision content changed without a new revision ID.')
    return parsed


def revision_identity(kind, content, current_id='', current_digest='', now_ms=None, entropy=None):
    revision_require(kind in REVISION_KINDS, 'Unknown revision kind: ' + str(kind))
    full_digest = definition_digest(content, kind)
    if current_id or current_digest:
        revision_require(bool(current_id) and bool(current_digest),
                         'Revision ID and content digest must be recorded together.')
        parsed = parse_revision_id(current_id, kind)
        recorded = validate_full_digest(current_digest)
        revision_require(parsed.digest_prefix == recorded[:16],
                         'Revision ID digest does not match its content digest.')
        if recorded == full_digest:
            return RevisionIdentity(current_id, current_digest)
    identifier = uuid7(now_ms, entropy)
    return RevisionIdentity(
        kind + '-' + str(identifier) + '-' + full_digest[:16],
        'sha256:' + full_digest)


# Workflow records

ProjectError = RevisionError


@dataclass(frozen=True)
class DocumentRevision:
    state: str
    revision: str = ''
    created: str = 'Unavailable'
    message: str = ''


@dataclass(frozen=True)
class Lineage:
    brief: DocumentRevision
    tasks: DocumentRevision
    state: str = 'Current'
    issue: str = ''

    @property
    def display(self):
        return self.state if not self.issue else self.state + ': ' + self.issue


@dataclass(frozen=True)
class RevisionWrite:
    path: Path
    revision: str
    content_digest: str
    created: str
    wrote: bool
    approval_cleared: bool


@dataclass(frozen=True)
class StampedDocument:
    content: str
    identity: RevisionIdentity
    approval_cleared: bool


@dataclass(frozen=True)
class RecordedRevision:
    revision: str
    content_digest: str
    actual_digest: str
    path: str
    kind: str


def require(condition, message):
    if not condition:
        raise ProjectError(message)


def digest(content):
    return hashlib.sha256(content).hexdigest()


# Managed installation

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
    print('Initialized. Start a blank Brief from .ggez/templates/prd.md; fill Slice, Outcome, and Context yourself.')
    return 0


# Project discovery and planning

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
        choice = input('Choose a number or type a feature name; Enter cancels: ').strip()
    except EOFError:
        choice = ''
    if not choice:
        return None
    if allow_new and choice == '0':
        return 'new'
    if choice.isascii() and choice.isdigit():
        require(1 <= int(choice) <= len(paths), 'Choose one of the listed numbers.')
        return paths[int(choice) - 1]
    query = re.sub(r'[^a-z0-9]+', '', choice.lower())
    require(bool(query), 'Type a feature name or choose one of the listed numbers.')
    names = {path: re.sub(r'[^a-z0-9]+', '', path.name.lower()) for path in paths}
    matches = [path for path, name in names.items() if query in name]
    if len(matches) == 1:
        return matches[0]
    scores = sorted(((difflib.SequenceMatcher(None, query, name).ratio(), path)
                     for path, name in names.items()), reverse=True,
                    key=lambda item: (item[0], item[1].name))
    require(bool(scores) and scores[0][0] >= 0.45,
            'No feature matches "' + choice + '".')
    require(len(scores) == 1 or scores[0][0] - scores[1][0] >= 0.1,
            'Several features match "' + choice + '"; type more of the name or choose a number.')
    return scores[0][1]


def select_feature(root, feature=None):
    paths = feature_paths(root)
    require(bool(paths), 'No features yet. Start one with ggez plan "Feature title".')
    if feature is not None:
        matches = [path for path in paths if path.name == feature]
        require(bool(matches), 'Feature not found: ' + feature)
        return matches[0]
    if len(paths) == 1:
        return paths[0]
    return choose_feature(paths)


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
    print('Loop: fill Brief → record and approve revisions → build and test → accept the outcome.')
    print('\nCopy into Codex, Cursor, or Claude:')
    print('Read AGENTS.md and ' + str(path / 'brief.md') + '. '
          'I fill Slice and Outcome; never fill those required sections for me. '
          'I also provide the Context sources or exact no-context statement. '
          'Before preparing tasks, read the direct sources in Context. Do not load references '
          'found inside them unless the work requires it. Record the completed Brief with '
          '`ggez revise brief`, then get my approval. Prepare tasks from that exact Brief, record '
          'them with `ggez revise tasks`, then get my approval of that task revision. '
          'Execute only approved tasks. Each task has one Result: Pending, Pass, Fail, Blocked, '
          'or Interrupted; check it only with Pass. Verified is default: test one task, update its '
          'Result, then wait for my review. If I explicitly choose Unverified, continue approved '
          'tasks after tests. Use `ggez check` to validate lineage. Stop on failures or blockers. '
          'Final Brief acceptance is mine.')


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


# Feature document model

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


def valid_context(text):
    body = section(text, 'Context — **Required**')
    body = re.sub(r'<!--.*?-->', '', body, flags=re.S).strip()
    if body == 'None beyond AGENTS.md and this Brief':
        return True
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    first_source = next((index for index, line in enumerate(lines)
                         if line.startswith('- ')), None)
    if first_source is None:
        return False
    source_lines = []
    for line in lines[first_source:]:
        if line.startswith('- '):
            source_lines.append(line)
            continue
        if not re.match(r'^\*\*[^*]+\*\*$', line):
            return False
        break
    references = 0
    for line in source_lines:
        parts = line[2:].split(' — ', 1)
        if len(parts) != 2:
            return False
        source, reason = (part.strip() for part in parts)
        if (not source or not reason or source == '[Path or URL]'
                or reason == '[Why the agent needs it]'):
            return False
        targets = re.findall(r'\[[^\]]+\]\(([^)\s]+)\)', source)
        if targets:
            references += len(targets)
            continue
        if re.search(r'\s', source) or not (re.match(r'https?://', source)
                                              or '/' in source
                                              or re.search(r'\.[A-Za-z0-9]+$', source)):
            return False
        references += 1
    return 1 <= references <= 5


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


# Revision lifecycle

def replace_managed_fields(text, values):
    missing = []
    for name, value in values:
        pattern = r'^\*\*' + re.escape(name) + r':\*\*[^\n]*$'
        matches = list(re.finditer(pattern, text, re.M))
        require(len(matches) <= 1, 'Duplicate field: ' + name)
        if matches:
            match = matches[0]
            text = text[:match.start()] + '**' + name + ':** ' + value + text[match.end():]
        else:
            missing.append((name, value))
    if missing:
        first_line = text.find('\n')
        require(first_line >= 0 and text.startswith('# '), 'Document needs a Markdown title.')
        block = '\n\n'.join('**' + name + ':** ' + value for name, value in missing)
        text = text[:first_line] + '\n\n' + block + text[first_line:]
    return text


def clear_approval(text, kind):
    pattern = r'^\*\*Approval:\*\*[^\n]*$'
    if re.search(pattern, text, re.M):
        text = re.sub(pattern, '**Approval:** [Reviewer and date; leave blank until approved]',
                      text, count=1, flags=re.M)
    if kind == 'brief' and re.search(r'^\*\*Status:\*\*[^\n]*$', text, re.M):
        text = re.sub(r'^\*\*Status:\*\*[^\n]*$', '**Status:** Draft',
                      text, count=1, flags=re.M)
    return text


def stamped_text(content, kind, source_revision='', now_ms=None, entropy=None):
    current_id = field(content, 'Revision')
    current_digest = field(content, 'Content digest')
    prospective = content
    values = []
    if kind == 'tasks':
        parse_revision_id(source_revision, 'brief')
        prospective = replace_managed_fields(prospective, [('Derived from', source_revision)])
        values.append(('Derived from', source_revision))
    identity = revision_identity(
        kind, prospective, current_id, current_digest, now_ms, entropy)
    changed_definition = bool(current_id and identity.revision != current_id)
    values[:0] = [('Revision', identity.revision),
                  ('Content digest', identity.content_digest)]
    result = replace_managed_fields(prospective, values)
    if changed_definition:
        result = clear_approval(result, kind)
    return StampedDocument(result, identity, changed_definition)


def atomic_document_write(root, relative_name, before, after, replace_file=None):
    path = root / relative_name
    before_bytes = before.encode('utf-8')
    after_bytes = after.encode('utf-8')
    require(read_target(root, relative_name) == before_bytes,
            'Document changed before its revision could be recorded: ' + relative_name)
    if before_bytes == after_bytes:
        return False
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.ggez-revise-', dir=path.parent,
                                         delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(after_bytes)
        temporary.chmod(stat.S_IMODE(path.stat().st_mode))
        require(read_target(root, relative_name) == before_bytes,
                'Document changed while its revision was being recorded: ' + relative_name)
        (replace_file or os.replace)(temporary, path)
        temporary = None
        return True
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def revise_document(root, path, kind, now_ms=None, entropy=None, replace_file=None):
    require(kind in REVISION_KINDS, 'Choose brief or tasks.')
    base = 'features/' + path.name + '/'
    brief = read_document(root, base + 'brief.md')
    require(bool(brief), 'Brief is missing or empty: ' + base + 'brief.md')
    require(bool(field(brief, 'Goal')) and valid_context(brief),
            'Complete the Brief goal and Context before recording a revision.')
    source_revision = ''
    if kind == 'brief':
        name, content = base + 'brief.md', brief
    else:
        require(approved(brief), 'Approve the Brief before recording a task-set revision.')
        source_revision = field(brief, 'Revision')
        source_digest = field(brief, 'Content digest')
        require(bool(source_revision) and bool(source_digest),
                'Run ggez revise brief before recording a task-set revision.')
        verify_revision(source_revision, source_digest, brief, 'brief')
        name = base + 'tasks.md'
        content = read_document(root, name)
        require(bool(content), 'Tasks are missing or empty: ' + name)
        require(bool(read_tasks(content)), 'Add at least one task before recording its revision.')
    stamped = stamped_text(content, kind, source_revision, now_ms, entropy)
    wrote = atomic_document_write(
        root, name, content, stamped.content, replace_file)
    return RevisionWrite(
        root / name, stamped.identity.revision, stamped.identity.content_digest,
        revision_created_at(stamped.identity.revision), wrote,
        stamped.approval_cleared)


def revise_feature(args):
    root = project_root(args.project)
    path = select_feature(root, args.feature)
    if path is None:
        print('Cancelled; no files changed.')
        return 0
    result = revise_document(root, path, args.document)
    print('Feature: ' + path.name)
    print('Revision: ' + result.revision)
    print('Created: ' + result.created)
    print(('Updated: ' if result.wrote else 'Unchanged: ') + str(result.path))
    if result.approval_cleared:
        print('Approval cleared: review and approve this new revision before continuing.')
    return 0


# Revision validation

def inspect_document_revision(text, kind):
    revision = field(text, 'Revision')
    content_digest = field(text, 'Content digest')
    if not revision and not content_digest:
        return DocumentRevision(
            'missing', message='Run ggez revise ' + kind + ' to record this document revision.')
    if not revision or not content_digest:
        return DocumentRevision(
            'invalid', revision or 'Incomplete',
            message='Revision ID and content digest must be recorded together.')
    try:
        verify_revision(revision, content_digest, text, kind)
        return DocumentRevision('valid', revision, revision_created_at(revision))
    except ProjectError as exc:
        return DocumentRevision('invalid', revision, message=str(exc))


def inspect_lineage(brief, tasks):
    brief_info = inspect_document_revision(brief, 'brief')
    task_info = (inspect_document_revision(tasks, 'tasks') if tasks else
                 DocumentRevision(
                     'missing', message='Create tasks.md, then run ggez revise tasks.'))
    if brief_info.state != 'valid':
        return Lineage(brief_info, task_info, 'Missing revision metadata', brief_info.message)
    if task_info.state != 'valid':
        return Lineage(brief_info, task_info, 'Missing revision metadata', task_info.message)
    source = field(tasks, 'Derived from')
    try:
        parse_revision_id(source, 'brief')
    except ProjectError as exc:
        return Lineage(brief_info, task_info, 'Invalid task lineage', str(exc))
    if source != brief_info.revision:
        issue = ('Tasks derive from ' + source + ', but the current Brief is ' +
                 brief_info.revision + '. Regenerate the tasks, then run ggez revise tasks.')
        return Lineage(brief_info, task_info, 'Stale', issue)
    return Lineage(brief_info, task_info)


def lineage_fields(lineage):
    return (
        ('Brief revision', lineage.brief.revision or 'Untracked'),
        ('Brief created', lineage.brief.created),
        ('Task revision', lineage.tasks.revision or 'Untracked'),
        ('Task created', lineage.tasks.created),
        ('Lineage', lineage.display),
    )


def duplicate_revision_warnings(root, selected_ids):
    records = []
    for path in feature_paths(root):
        for kind, filename in (('brief', 'brief.md'), ('tasks', 'tasks.md')):
            text = read_document(root, 'features/' + path.name + '/' + filename)
            if not text:
                continue
            revision = field(text, 'Revision')
            content_digest = field(text, 'Content digest')
            if not revision or not content_digest:
                continue
            try:
                parsed = parse_revision_id(revision, kind)
                recorded = validate_full_digest(content_digest)
            except ProjectError:
                continue
            records.append(RecordedRevision(
                revision, recorded, definition_digest(text, kind),
                str(path / filename), parsed.kind))
    by_id = {}
    for record in records:
        by_id.setdefault(record.revision, []).append(record)
    for revision, rows in by_id.items():
        if len(rows) > 1 and len({(row.content_digest, row.actual_digest)
                                  for row in rows}) > 1:
            raise ProjectError('Conflicting duplicate revision ID ' + revision + ': ' +
                               ', '.join(row.path for row in rows))
    by_content = {}
    for record in records:
        if record.content_digest == record.actual_digest:
            by_content.setdefault((record.kind, record.content_digest), []).append(record)
    warnings = []
    for rows in by_content.values():
        ids = {row.revision for row in rows}
        if len(ids) > 1 and ids.intersection(selected_ids):
            warnings.append('Identical content has multiple revision IDs: ' +
                            ', '.join(sorted(ids)) + '. Reuse the existing revision when possible.')
    return warnings


def check_feature(args):
    root = project_root(args.project)
    path = select_feature(root, args.feature)
    if path is None:
        print('Cancelled; no files changed.')
        return 0
    base = 'features/' + path.name + '/'
    brief = read_document(root, base + 'brief.md')
    tasks = read_document(root, base + 'tasks.md')
    require(bool(brief), 'Brief is missing or empty: ' + base + 'brief.md')
    require(bool(field(brief, 'Goal')) and valid_context(brief),
            'Complete the Brief goal and Context before checking revisions.')
    require(bool(tasks), 'Tasks are missing or empty: ' + base + 'tasks.md')
    require(bool(read_tasks(tasks)), 'Add at least one task before checking revisions.')
    lineage = inspect_lineage(brief, tasks)
    require(not lineage.issue, lineage.issue)
    selected_ids = {lineage.brief.revision, lineage.tasks.revision}
    warnings = duplicate_revision_warnings(root, selected_ids)
    print('Feature: ' + path.name)
    for label, value in lineage_fields(lineage):
        print(label + ': ' + value)
    for warning in warnings:
        print('Warning: ' + warning)
    return 0


# Status read model

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
    checks = acceptance_checks(brief)
    lineage = inspect_lineage(brief, tasks)
    passed = {task_id for task_id, _, checked, result in rows if checked and result == 'Pass'}
    pending = [(task_id, title) for task_id, title, _, _ in rows if task_id not in passed]
    result = {'goal': field(brief, 'Goal') or 'Not filled in', 'stage': 'Brief',
              'state': 'Needs attention', 'reason': 'Approval required',
              'current': pending[0][0] + ' — ' + pending[0][1] if pending else 'None',
              'completed': len(passed), 'total': len(rows), 'next': 'Fill the Brief and record human approval.',
              'time': execution_time(root, path.name),
              'revision_fields': lineage_fields(lineage)}
    if not approved(brief) or not field(brief, 'Goal') or not valid_context(brief):
        return result
    if lineage.brief.state != 'valid':
        result.update(reason='Missing prerequisite', next=lineage.issue)
        return result
    result['stage'] = 'Tasks'
    if not rows:
        result.update(reason='Missing prerequisite', next='Prepare tasks from the template for approval.')
        return result
    if lineage.tasks.state != 'valid' or lineage.state != 'Current':
        result.update(reason='Missing prerequisite', next=lineage.issue)
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
    for label, value in info['revision_fields']:
        show(label, value)
    for name in ('brief.md', 'tasks.md'):
        if (path / name).is_file():
            show(name, path / name)
    return 0


# Installed CLI updates

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


def update_command(_args):
    return update_cli()


# Command-line interface

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='ggez', description='Plan features, approve tasks, and track progress.')
    parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)
    commands = parser.add_subparsers(dest='command')
    init = commands.add_parser('init', help='Preview and install ggez in a project.')
    init.add_argument('directory', nargs='?', type=Path, default=Path('.'))
    init.add_argument('--dry-run', action='store_true', help='Preview without writing files.')
    init.add_argument('--yes', action='store_true', help='Confirm the preview and compatibility with existing rules.')
    init.set_defaults(handler=init_project)
    plan = commands.add_parser('plan', help='Create a blank Brief or select a feature.')
    plan.add_argument('title', nargs='?')
    plan.add_argument('--project', type=Path, default=Path('.'))
    plan.set_defaults(handler=plan_feature)
    status = commands.add_parser('status', help='Show task progress, recorded time, and file paths.')
    status.add_argument('feature', nargs='?')
    status.add_argument('--project', type=Path, default=Path('.'))
    status.set_defaults(handler=status_project)
    revise = commands.add_parser('revise', help='Record an immutable Brief or task-set revision.')
    revise.add_argument('document', choices=REVISION_KINDS)
    revise.add_argument('feature', nargs='?')
    revise.add_argument('--project', type=Path, default=Path('.'))
    revise.set_defaults(handler=revise_feature)
    check = commands.add_parser('check', help='Validate Brief and task-set revision lineage.')
    check.add_argument('feature', nargs='?')
    check.add_argument('--project', type=Path, default=Path('.'))
    check.set_defaults(handler=check_feature)
    update = commands.add_parser('update', help='Download, validate, and activate the latest ggez release.')
    update.set_defaults(handler=update_command)
    args = parser.parse_args(argv)
    try:
        if hasattr(args, 'handler'):
            return args.handler(args)
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
