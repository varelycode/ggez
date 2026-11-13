import json
import unittest

from scripts import check_version


class VersionCheckTests(unittest.TestCase):
    def test_payload_change_requires_a_version_increase(self):
        with self.assertRaisesRegex(check_version.VersionCheckError,
                                    'without a VERSION increase'):
            check_version.validate_change(
                '0.1.0', '0.1.0', {'scripts/ggez.py'}, {'scripts/ggez.py'})
        affected = check_version.validate_change(
            '0.1.0', '0.1.1', {'scripts/ggez.py'}, {'scripts/ggez.py'})
        self.assertEqual(affected, ['scripts/ggez.py'])

    def test_non_payload_change_needs_no_bump(self):
        affected = check_version.validate_change(
            '0.1.0', '0.1.0', {'docs/versioning.md'}, {'scripts/ggez.py'})
        self.assertEqual(affected, [])

    def test_manifest_union_catches_added_and_removed_files(self):
        base = json.dumps({'version': 1, 'required': ['scripts/old.py'], 'optional': []})
        head = json.dumps({'version': 1, 'required': ['scripts/new.py'], 'optional': []})
        paths = check_version.manifest_paths(base, 'base')
        paths |= check_version.manifest_paths(head, 'head')
        self.assertEqual(paths, {
            'scripts/install-manifest.json', 'scripts/new.py', 'scripts/old.py'})

    def test_version_source_is_strict_semver(self):
        self.assertEqual(check_version.source_version("VERSION = '1.2.3'\n", 'version'),
                         '1.2.3')
        for content in ("VERSION = '1.2'\n", "VERSION = '01.2.3'\n", ''):
            with self.subTest(content=content):
                with self.assertRaises(check_version.VersionCheckError):
                    check_version.source_version(content, 'version')


if __name__ == '__main__':
    unittest.main()
