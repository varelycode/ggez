#!/usr/bin/env python3
"""Install a checked ggez release without changing shell configuration."""
import argparse
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request


ARCHIVE_URL = 'https://codeload.github.com/varelycode/ggez/tar.gz/refs/heads/main'
LIMIT = 10 * 1024 * 1024
MARKER = '# ggez-managed-launcher-v1\n'
REQUIRED = ('scripts/ggez.py', 'templates/prd.md', 'templates/tasks.md',
            'templates/evidence.md', 'templates/review.md', 'templates/agent-rules.md')
OPTIONAL = ('scripts/tasks.py', 'templates/ralph/.agent/tasks.json',
            'templates/ralph/.agent/tasks/TASK-1.json',
            'templates/ralph/.agent/tasks/TASK-2.json')


class InstallError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InstallError(message)


def check_payload(payload):
    require(all(name in payload for name in REQUIRED), 'Release is missing required files.')
    require(sum(map(len, payload.values())) <= LIMIT, 'Release is too large.')
    require(all(payload[name].strip() for name in REQUIRED), 'Release contains empty required files.')
    return payload


def local_payload(source):
    source = source.resolve(strict=True)
    payload = {}
    for name in REQUIRED + OPTIONAL:
        path = source / name
        require(not any(p.is_symlink() for p in (path, *path.parents) if p != source),
                'Source files must not use symlinks.')
        if path.exists():
            require(path.is_file(), 'Expected a regular source file: ' + name)
            require(path.stat().st_size <= LIMIT, 'Source file is too large: ' + name)
            payload[name] = path.read_bytes()
    return check_payload(payload)


def archive_payload(data):
    payload = {}
    root = None
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        for member in archive:
            path = PurePosixPath(member.name)
            require(not path.is_absolute() and '..' not in path.parts, 'Unsafe archive path.')
            require(bool(path.parts), 'Empty archive path.')
            root = root or path.parts[0]
            require(path.parts[0] == root, 'Archive has multiple roots.')
            name = '/'.join(path.parts[1:])
            if name not in REQUIRED + OPTIONAL:
                continue
            require(member.isfile(), 'Archive payload must contain regular files.')
            require(name not in payload, 'Duplicate archive file: ' + name)
            require(0 <= member.size <= LIMIT, 'Archive file is too large.')
            payload[name] = archive.extractfile(member).read(LIMIT + 1)
            require(sum(map(len, payload.values())) <= LIMIT, 'Release is too large.')
    return check_payload(payload)


def download_payload():
    with urllib.request.urlopen(ARCHIVE_URL, timeout=30) as response:
        data = response.read(LIMIT + 1)
    require(len(data) <= LIMIT, 'Download is too large.')
    return archive_payload(data)


def safe_directory(path):
    require(not any(p.is_symlink() for p in (path, *path.parents)),
            'Install directories must not use symlinks: ' + str(path))
    path.mkdir(parents=True, exist_ok=True)


def check_release(release, payload):
    for name, content in payload.items():
        path = release / name
        require(not any(p.is_symlink() for p in (path, *path.parents))
                and path.is_file() and path.read_bytes() == content,
                'Existing release was edited: ' + str(release))
    result = subprocess.run([sys.executable, '-B', str(release / 'scripts/ggez.py'), '--help'],
                            capture_output=True, text=True, timeout=15)
    require(result.returncode == 0 and 'ggez' in result.stdout,
            'Release help check failed; previous installation is unchanged.')


def install(payload, prefix):
    # Resolve existing system aliases (such as /var on macOS) at the chosen root.
    require(not prefix.is_symlink(), 'Install prefix must not be a symlink.')
    prefix = prefix.resolve()
    bin_dir = prefix / 'bin'
    releases = prefix / 'share/ggez/releases'
    launcher = bin_dir / 'ggez'
    require(not launcher.is_symlink(), 'Refusing to replace a symlink at ' + str(launcher))
    if launcher.exists():
        require(launcher.is_file() and launcher.read_text().startswith('#!/bin/sh\n' + MARKER),
                'Refusing to replace an unrelated command at ' + str(launcher))
    safe_directory(bin_dir)
    safe_directory(releases)
    digest = hashlib.sha256()
    for name, content in sorted(payload.items()):
        digest.update(name.encode() + b'\0' + content + b'\0')
    release = releases / digest.hexdigest()
    require(not release.is_symlink(), 'Release directory must not be a symlink.')
    with tempfile.TemporaryDirectory(prefix='.staging-', dir=releases) as staging:
        staged = Path(staging) / 'release'
        for name, content in payload.items():
            target = staged / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        check_release(staged, payload)
        if release.exists():
            check_release(release, payload)
        else:
            os.replace(staged, release)
    command = ('#!/bin/sh\n' + MARKER + 'exec ' + shlex.quote(sys.executable) + ' -B ' +
               shlex.quote(str(release / 'scripts/ggez.py')) + ' "$@"\n')
    temp_launcher = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', prefix='.ggez-', dir=bin_dir,
                                         delete=False) as handle:
            temp_launcher = Path(handle.name)
            handle.write(command)
        temp_launcher.chmod(0o755)
        result = subprocess.run([str(temp_launcher), '--help'], capture_output=True,
                                text=True, timeout=15)
        require(result.returncode == 0 and 'ggez' in result.stdout,
                'Launcher check failed; previous installation is unchanged.')
        # Replacing one file activates the checked release; older releases stay intact.
        os.replace(temp_launcher, launcher)
    finally:
        if temp_launcher is not None:
            temp_launcher.unlink(missing_ok=True)
    return launcher


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='Install from a local checkout without downloading.')
    parser.add_argument('--prefix', type=Path, default=Path.home() / '.local',
                        help='Install root (default: ~/.local).')
    args = parser.parse_args(argv)
    try:
        require(sys.version_info >= (3, 9), 'Python 3.9+ is required.')
        require(sys.platform in ('darwin', 'linux'), 'Supported platforms: macOS and Linux.')
        payload = local_payload(args.source) if args.source else download_payload()
        launcher = install(payload, args.prefix)
    except (InstallError, OSError, ValueError, tarfile.TarError,
            subprocess.SubprocessError, urllib.error.URLError) as exc:
        print('ggez: ' + str(exc), file=sys.stderr)
        return 1
    print('Installed: ' + str(launcher))
    if shutil.which('ggez') != str(launcher):
        print('For this terminal: export PATH=' + shlex.quote(str(launcher.parent)) + ':"$PATH"')
    print('Try: ggez --help')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
