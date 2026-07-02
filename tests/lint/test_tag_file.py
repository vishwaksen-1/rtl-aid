import os
import tempfile
import unittest
from rtl_aid.lint import tag_file
from tests.support import LINT_FIXTURES, copy_fixture


class TagFileTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)

    def _target(self, fixture_name):
        return copy_fixture(LINT_FIXTURES, fixture_name, self._tmpdir.name)


class TestTagFile(TagFileTestCase):
    def test_tags_warned_line(self):
        path = self._target("tag_target_basic.v")
        tag_file(path, {2: ("", "Signal is not used: 'y'")}, ["verilator", "--lint-only", path])
        with open(path) as f:
            lines = f.readlines()
        # 2 headers inserted before the module, so original line 2 (idx 1) -> idx 3
        self.assertIn("/* Check: Signal is not used: 'y' */", lines[3])

    def test_tags_warned_line_with_id(self):
        path = self._target("tag_target_basic.v")
        tag_file(path, {2: ("UNUSEDSIGNAL", "Signal is not used: 'y'")}, ["verilator", "--lint-only", path])
        with open(path) as f:
            lines = f.readlines()
        self.assertIn("/* Check[UNUSEDSIGNAL]: Signal is not used: 'y' */", lines[3])

    def test_adds_header_lines(self):
        path = self._target("tag_target_empty.v")
        tag_file(path, {1: ("", "some warning")}, ["verilator", "--lint-only", path])
        with open(path) as f:
            content = f.read()
        self.assertIn("// lint-test:", content)
        self.assertIn("// tb-test: tba", content)

    def test_idempotent_headers(self):
        path = self._target("tag_target_existing_headers.v")
        tag_file(path, {3: ("", "some warning")}, ["verilator", "--lint-only", path])
        with open(path) as f:
            content = f.read()
        self.assertEqual(content.count("// lint-test:"), 1)
        self.assertEqual(content.count("// tb-test:"), 1)

    def test_replaces_existing_check_comment(self):
        path = self._target("tag_target_existing_check.v")
        tag_file(path, {2: ("", "new message")}, ["verilator", "--lint-only", path])
        with open(path) as f:
            lines = f.readlines()
        # 2 headers inserted before the module, so original line 2 (idx 1) -> idx 3
        self.assertIn("/* Check: new message */", lines[3])
        self.assertNotIn("old message", lines[3])

    def test_replaces_existing_check_comment_with_id(self):
        path = self._target("tag_target_existing_check.v")
        tag_file(path, {2: ("WIDTHTRUNC", "new message")}, ["verilator", "--lint-only", path])
        with open(path) as f:
            lines = f.readlines()
        self.assertIn("/* Check[WIDTHTRUNC]: new message */", lines[3])
        self.assertNotIn("old message", lines[3])

    def test_out_of_bounds_line_number_ignored(self):
        path = self._target("tag_target_empty.v")
        # Line 999 doesn't exist — should not crash
        tag_file(path, {999: ("", "phantom warning")}, ["verilator", "--lint-only", path])
        with open(path) as f:
            content = f.read()
        self.assertNotIn("phantom", content)

    def test_header_inserted_after_leading_comments(self):
        path = self._target("tag_target_copyright.v")
        tag_file(path, {3: ("", "some warning")}, ["verilator", "--lint-only", path])
        with open(path) as f:
            lines = f.readlines()
        # First two lines must remain the copyright block
        self.assertTrue(lines[0].startswith("// Copyright"))
        self.assertTrue(lines[1].startswith("// Author"))
        # Headers come next
        self.assertTrue(lines[2].startswith("// lint-test:"))
        self.assertTrue(lines[3].startswith("// tb-test:"))


class TestTagFileDuplicateHeaders(TagFileTestCase):
    def test_no_duplicate_when_headers_outside_leading_block(self):
        # Headers appear after module declaration (not in the leading comment block).
        # Old code only checked header_block (leading comments) and would add duplicates here.
        path = self._target("tag_target_headers_after_module.v")
        tag_file(path, {1: ("", "some warning")}, ["verilator", "--lint-only", path])
        with open(path) as f:
            content = f.read()
        self.assertEqual(content.count("// lint-test:"), 1)
        self.assertEqual(content.count("// tb-test:"), 1)

    def test_no_duplicate_tb_test_when_only_tb_present(self):
        # Only tb-test already exists; lint-test should be added but tb-test must not duplicate.
        path = self._target("tag_target_tb_only.v")
        tag_file(path, {2: ("", "some warning")}, ["verilator", "--lint-only", path])
        with open(path) as f:
            content = f.read()
        self.assertEqual(content.count("// tb-test:"), 1)


if __name__ == "__main__":
    unittest.main()
