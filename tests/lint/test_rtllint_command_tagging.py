"""
Test suite for rtllint command tagging feature.

Tests that when rtllint tags Verilog files for lint issues, the `// lint-test:`
line contains an rtllint command (not verilator), and that updating the command
works idempotently without creating duplicates.
"""
import os
import tempfile
import unittest
from rtl_aid.lint import tag_file
from tests.support import LINT_FIXTURES, copy_fixture


class RtllintCommandTaggingTestCase(unittest.TestCase):
    """Base test case for rtllint command tagging."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)

    def _target(self, fixture_name):
        """Copy a fixture file to temp dir and return path."""
        return copy_fixture(LINT_FIXTURES, fixture_name, self._tmpdir.name)

    def _read_file(self, filepath):
        """Read file content."""
        with open(filepath) as f:
            return f.read()

    def _get_lint_test_line(self, filepath):
        """Extract the // lint-test: line from a file."""
        content = self._read_file(filepath)
        for line in content.split('\n'):
            if line.strip().startswith('// lint-test:'):
                return line.strip()
        return None


class TestRtllintCommandInHeader(RtllintCommandTaggingTestCase):
    """Tests that // lint-test: contains rtllint command, not verilator."""

    def test_lint_test_header_contains_rtllint_not_verilator(self):
        """When tagging, // lint-test: should use rtllint command, not verilator."""
        path = self._target("tag_target_empty.v")
        rtllint_cmd = ["rtllint", "-Irtl/core/", "some_file.v"]
        tag_file(path, {1: ("", "some warning")}, rtllint_cmd)

        lint_test_line = self._get_lint_test_line(path)
        self.assertIsNotNone(lint_test_line)
        self.assertIn("rtllint", lint_test_line)
        self.assertNotIn("verilator", lint_test_line)

    def test_lint_test_header_has_complete_rtllint_command(self):
        """// lint-test: should contain the full rtllint command with include dirs."""
        path = self._target("tag_target_empty.v")
        rtllint_cmd = ["rtllint", "-Irtl/core/", "-Irtl/lib/", "myfile.v"]
        tag_file(path, {1: ("", "some warning")}, rtllint_cmd)

        lint_test_line = self._get_lint_test_line(path)
        self.assertIn("rtllint", lint_test_line)
        self.assertIn("-Irtl/core/", lint_test_line)
        self.assertIn("-Irtl/lib/", lint_test_line)
        self.assertIn("myfile.v", lint_test_line)

    def test_include_dirs_are_no_space_format(self):
        """Include dirs in rtllint command should be -I<dir> (no space)."""
        path = self._target("tag_target_empty.v")
        rtllint_cmd = ["rtllint", "-Irtl/core/", "file.v"]
        tag_file(path, {1: ("", "some warning")}, rtllint_cmd)

        lint_test_line = self._get_lint_test_line(path)
        self.assertIn("-Irtl/core/", lint_test_line)
        # Should not have space-separated form
        self.assertNotIn("-I rtl/core/", lint_test_line)

    def test_multiple_include_dirs_all_present(self):
        """Multiple include dirs should all appear in the rtllint command."""
        path = self._target("tag_target_empty.v")
        rtllint_cmd = ["rtllint", "-Irtl/core/", "-Irtl/lib/", "-Irtl/utils/", "file.v"]
        tag_file(path, {1: ("", "some warning")}, rtllint_cmd)

        lint_test_line = self._get_lint_test_line(path)
        self.assertIn("-Irtl/core/", lint_test_line)
        self.assertIn("-Irtl/lib/", lint_test_line)
        self.assertIn("-Irtl/utils/", lint_test_line)


class TestRtllintCommandIdempotency(RtllintCommandTaggingTestCase):
    """Tests that rtllint command tagging is idempotent."""

    def test_updating_rtllint_command_replaces_old_command(self):
        """Running tag_file twice with different commands should update, not duplicate."""
        path = self._target("tag_target_empty.v")

        # First tagging with one command
        rtllint_cmd_1 = ["rtllint", "-Irtl/old/", "file.v"]
        tag_file(path, {1: ("", "warning 1")}, rtllint_cmd_1)

        # Second tagging with a different command
        rtllint_cmd_2 = ["rtllint", "-Irtl/new/", "file.v"]
        tag_file(path, {1: ("", "warning 2")}, rtllint_cmd_2)

        # Should have exactly one lint-test line
        content = self._read_file(path)
        lint_test_count = content.count("// lint-test:")
        self.assertEqual(lint_test_count, 1)

        # Should contain the NEW command, not the old one
        lint_test_line = self._get_lint_test_line(path)
        self.assertIn("-Irtl/new/", lint_test_line)
        self.assertNotIn("-Irtl/old/", lint_test_line)

    def test_idempotent_multiple_taggings(self):
        """Running tag_file multiple times should not create duplicate lint-test lines."""
        path = self._target("tag_target_empty.v")
        rtllint_cmd = ["rtllint", "-Irtl/core/", "file.v"]

        # Tag the file three times
        for i in range(3):
            tag_file(path, {1: ("", f"warning {i}")}, rtllint_cmd)

        # Should still have exactly one lint-test line
        content = self._read_file(path)
        lint_test_count = content.count("// lint-test:")
        self.assertEqual(lint_test_count, 1)

    def test_rtllint_update_preserves_tb_test_header(self):
        """When updating rtllint command, tb-test header should not be duplicated."""
        path = self._target("tag_target_existing_headers.v")
        rtllint_cmd = ["rtllint", "-Irtl/core/", "file.v"]

        # Tag the file
        tag_file(path, {3: ("", "some warning")}, rtllint_cmd)

        # Should have exactly one of each header
        content = self._read_file(path)
        self.assertEqual(content.count("// lint-test:"), 1)
        self.assertEqual(content.count("// tb-test:"), 1)


class TestRtllintCommandUpdatesBehavior(RtllintCommandTaggingTestCase):
    """Tests specific behaviors when updating rtllint commands."""

    def test_new_rtllint_command_added_when_none_exists(self):
        """If file has no lint-test line, rtllint command should be added."""
        path = self._target("tag_target_empty.v")
        rtllint_cmd = ["rtllint", "-Irtl/core/", "newfile.v"]
        tag_file(path, {1: ("", "some warning")}, rtllint_cmd)

        content = self._read_file(path)
        self.assertIn("// lint-test:", content)
        self.assertIn("rtllint", content)

    def test_rtllint_command_updated_in_existing_file_with_headers(self):
        """If file already has lint-test line, it should be updated."""
        path = self._target("tag_target_existing_headers.v")

        # Get original content
        content_before = self._read_file(path)
        original_lint_test_line = None
        for line in content_before.split('\n'):
            if line.strip().startswith('// lint-test:'):
                original_lint_test_line = line.strip()
                break

        # Now tag with a new rtllint command
        new_rtllint_cmd = ["rtllint", "-Inew/include/", "file.v"]
        tag_file(path, {3: ("", "some warning")}, new_rtllint_cmd)

        # Get new content
        content_after = self._read_file(path)
        new_lint_test_line = None
        for line in content_after.split('\n'):
            if line.strip().startswith('// lint-test:'):
                new_lint_test_line = line.strip()
                break

        # Lines should be different
        self.assertNotEqual(original_lint_test_line, new_lint_test_line)
        # New line should have new command
        self.assertIn("-Inew/include/", new_lint_test_line)

    def test_rtllint_command_different_from_verilator_format(self):
        """Rtllint command format should differ from verilator format."""
        path = self._target("tag_target_empty.v")

        # Create a command that looks like it came from _run_lint (which returns verilator)
        verilator_cmd = ["verilator", "--lint-only", "-Wall", "-Irtl/core/", "file.v"]
        rtllint_cmd = ["rtllint", "-Irtl/core/", "file.v"]

        # Tag with rtllint command
        tag_file(path, {1: ("", "warning")}, rtllint_cmd)

        lint_test_line = self._get_lint_test_line(path)

        # Should start with rtllint, not verilator
        self.assertIn("rtllint", lint_test_line)
        # Should not have verilator flags
        self.assertNotIn("--lint-only", lint_test_line)
        self.assertNotIn("-Wall", lint_test_line)


class TestRtllintCommandEdgeCases(RtllintCommandTaggingTestCase):
    """Edge cases for rtllint command tagging."""

    def test_rtllint_command_with_no_include_dirs(self):
        """Rtllint command with no -I flags should still be correctly tagged."""
        path = self._target("tag_target_empty.v")
        rtllint_cmd = ["rtllint", "file.v"]
        tag_file(path, {1: ("", "some warning")}, rtllint_cmd)

        lint_test_line = self._get_lint_test_line(path)
        self.assertIn("rtllint", lint_test_line)
        self.assertIn("file.v", lint_test_line)

    def test_rtllint_command_with_absolute_paths(self):
        """Rtllint command with absolute include paths should be preserved."""
        path = self._target("tag_target_empty.v")
        rtllint_cmd = ["rtllint", "-I/home/user/rtl/core/", "/home/user/file.v"]
        tag_file(path, {1: ("", "some warning")}, rtllint_cmd)

        lint_test_line = self._get_lint_test_line(path)
        self.assertIn("-I/home/user/rtl/core/", lint_test_line)
        self.assertIn("/home/user/file.v", lint_test_line)

    def test_rtllint_command_preserves_tb_test_when_updating(self):
        """When updating rtllint command, existing tb-test header should be preserved."""
        path = self._target("tag_target_tb_only.v")
        rtllint_cmd = ["rtllint", "-Irtl/core/", "file.v"]

        tag_file(path, {2: ("", "some warning")}, rtllint_cmd)

        content = self._read_file(path)
        # tb-test should still exist and not be duplicated
        self.assertEqual(content.count("// tb-test:"), 1)
        # lint-test should now exist
        self.assertIn("// lint-test:", content)

    def test_rtllint_command_with_special_characters_in_path(self):
        """Rtllint command with special characters in paths should be handled."""
        path = self._target("tag_target_empty.v")
        rtllint_cmd = ["rtllint", "-Irtl/core_v2.1/", "file_v1.0.v"]
        tag_file(path, {1: ("", "some warning")}, rtllint_cmd)

        lint_test_line = self._get_lint_test_line(path)
        self.assertIn("-Irtl/core_v2.1/", lint_test_line)
        self.assertIn("file_v1.0.v", lint_test_line)

    def test_multiple_warnings_same_file_one_lint_test_header(self):
        """Multiple warnings in same file should still have only one lint-test header."""
        path = self._target("tag_target_empty.v")
        issues = {
            1: ("WIDTHTRUNC", "width mismatch warning 1"),
            2: ("WIDTHEXPAND", "width mismatch warning 2"),
            3: ("", "generic warning"),
        }
        rtllint_cmd = ["rtllint", "-Irtl/core/", "file.v"]
        tag_file(path, issues, rtllint_cmd)

        content = self._read_file(path)
        # Still exactly one lint-test header
        self.assertEqual(content.count("// lint-test:"), 1)
        # Command should be in that single header
        lint_test_line = self._get_lint_test_line(path)
        self.assertIn("rtllint", lint_test_line)
        self.assertIn("-Irtl/core/", lint_test_line)


if __name__ == "__main__":
    unittest.main()
