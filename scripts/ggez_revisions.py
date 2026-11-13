"""Pure revision identity and content canonicalization."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
import re
import time
import uuid


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


def _require(condition, message):
    if not condition:
        raise RevisionError(message)


def canonical_definition(content, kind):
    _require(kind in REVISION_KINDS, 'Unknown revision kind: ' + str(kind))
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
    _require(type(milliseconds) is int and 0 <= milliseconds < 1 << 48,
             'UUIDv7 time must be an integer from 0 through 2^48-1 milliseconds.')
    random_bytes = os.urandom(10) if entropy is None else entropy
    _require(isinstance(random_bytes, bytes) and len(random_bytes) == 10,
             'UUIDv7 entropy must contain exactly 10 bytes.')
    random_bits = int.from_bytes(random_bytes, 'big') & ((1 << 74) - 1)
    random_a = random_bits >> 62
    random_b = random_bits & ((1 << 62) - 1)
    value = (milliseconds << 80) | (0x7 << 76) | (random_a << 64) | (0b10 << 62) | random_b
    return uuid.UUID(int=value)


def parse_revision_id(value, expected_kind=None):
    match = REVISION_RE.fullmatch(value or '')
    _require(bool(match), 'Invalid revision ID: ' + str(value))
    kind, uuid_text, digest_prefix = match.groups()
    _require(expected_kind is None or kind == expected_kind,
             'Expected a ' + str(expected_kind) + ' revision ID.')
    identifier = uuid.UUID(uuid_text)
    _require(identifier.version == 7 and identifier.variant == uuid.RFC_4122,
             'Invalid UUIDv7 revision ID: ' + value)
    return ParsedRevision(kind, identifier, digest_prefix)


def revision_created_at(value):
    parsed = parse_revision_id(value)
    milliseconds = parsed.identifier.int >> 80
    created = datetime.fromtimestamp(milliseconds / 1000, timezone.utc)
    return created.isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def validate_full_digest(value):
    _require(bool(re.fullmatch(r'sha256:[0-9a-f]{64}', value or '')),
             'Invalid revision content digest: ' + str(value))
    return value[7:]


def verify_revision(value, stored_digest, content, kind):
    parsed = parse_revision_id(value, kind)
    full_digest = validate_full_digest(stored_digest)
    _require(parsed.digest_prefix == full_digest[:16],
             'Revision ID digest does not match its content digest.')
    _require(full_digest == definition_digest(content, kind),
             'Revision content changed without a new revision ID.')
    return parsed


def revision_identity(kind, content, current_id='', current_digest='', now_ms=None, entropy=None):
    _require(kind in REVISION_KINDS, 'Unknown revision kind: ' + str(kind))
    full_digest = definition_digest(content, kind)
    if current_id or current_digest:
        _require(bool(current_id) and bool(current_digest),
                 'Revision ID and content digest must be recorded together.')
        parsed = parse_revision_id(current_id, kind)
        recorded = validate_full_digest(current_digest)
        _require(parsed.digest_prefix == recorded[:16],
                 'Revision ID digest does not match its content digest.')
        if recorded == full_digest:
            return RevisionIdentity(current_id, current_digest)
    identifier = uuid7(now_ms, entropy)
    return RevisionIdentity(
        kind + '-' + str(identifier) + '-' + full_digest[:16],
        'sha256:' + full_digest)
