#!/usr/bin/env python3
"""Require a SemVer bump when the installable ggez payload changes."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys


MANIFEST = 'scripts/install-manifest.json'
CLI = 'scripts/ggez.py'
SEMVER_RE = re.compile(r'^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$')
SOURCE_VERSION_RE = re.compile(r"^VERSION = '([^']+)'$", re.MULTILINE)


class VersionCheckError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise VersionCheckError(message)


def semver(value, label):
    match = SEMVER_RE.fullmatch(value or '')
    require(bool(match), label + ' must use MAJOR.MINOR.PATCH SemVer: ' + str(value))
    return tuple(int(part) for part in match.groups())


def source_version(content, label):
    matches = SOURCE_VERSION_RE.findall(content)
    require(len(matches) == 1, label + ' must contain exactly one VERSION assignment.')
    semver(matches[0], label)
    return matches[0]


def manifest_paths(content, label):
    try:
        manifest = json.loads(content)
    except json.JSONDecodeError as exc:
        raise VersionCheckError(label + ' is not valid JSON.') from exc
    require(isinstance(manifest, dict)
            and set(manifest) == {'version', 'required', 'optional'},
            label + ' has an unsupported format.')
    required, optional = manifest['required'], manifest['optional']
    require(isinstance(required, list) and isinstance(optional, list)
            and all(isinstance(path, str) and path for path in required + optional),
            label + ' must contain file path lists.')
    return set(required + optional) | {MANIFEST}


def validate_change(base_version, head_version, changed, payload):
    affected = sorted(set(changed) & set(payload))
    if affected:
        require(semver(head_version, 'Current VERSION') > semver(base_version, 'Base VERSION'),
                'Install payload changed without a VERSION increase: '
                + base_version + ' -> ' + head_version + '. Changed: ' + ', '.join(affected))
    return affected


def git_text(root, *arguments):
    result = subprocess.run(['git', *arguments], cwd=root, capture_output=True,
                            text=True, timeout=15)
    require(result.returncode == 0, result.stderr.strip() or 'Git command failed.')
    return result.stdout


def check(root, base, head):
    base_manifest = git_text(root, 'show', base + ':' + MANIFEST)
    head_manifest = git_text(root, 'show', head + ':' + MANIFEST)
    payload = manifest_paths(base_manifest, 'Base install manifest')
    payload |= manifest_paths(head_manifest, 'Current install manifest')
    base_version = source_version(git_text(root, 'show', base + ':' + CLI), 'Base VERSION')
    head_version = source_version(git_text(root, 'show', head + ':' + CLI), 'Current VERSION')
    changed = set(git_text(root, 'diff', '--name-only', base, head, '--').splitlines())
    affected = validate_change(base_version, head_version, changed, payload)
    if affected:
        print('Install payload version: ' + base_version + ' -> ' + head_version)
        print('Changed: ' + ', '.join(affected))
    else:
        print('Install payload unchanged; version remains ' + head_version + '.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', nargs='?', default=os.environ.get('GGEZ_BASE_SHA'))
    parser.add_argument('head', nargs='?', default=os.environ.get('GGEZ_HEAD_SHA', 'HEAD'))
    parser.add_argument('--root', type=Path, default=Path('.'))
    args = parser.parse_args(argv)
    try:
        require(bool(args.base), 'Provide a base Git revision.')
        check(args.root.resolve(), args.base, args.head)
    except (OSError, UnicodeError, subprocess.SubprocessError, VersionCheckError) as exc:
        print('ggez version check: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
