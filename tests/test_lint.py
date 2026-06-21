import os
import tempfile
import unittest
from unittest.mock import patch, Mock
from veridoc.lint import parse_lint_output, tag_file, _run_lint


SAMPLE_OUTPUT = """\
%Warning-WIDTHEXPAND: rtl/rx_ram.v:75:65: Operator EQ expects 32 bits on the LHS, but LHS's VARREF 'axi_awaddr_core' generates 6 bits.
                                         : ... note: In instance 'rx_ram'
   75 |     assign reset_rd_addr_axi = (slv_reg_wren && axi_awaddr_core == RD_DATA_AXI_REG_IDX);
      |                                                                 ^~
%Warning-UNUSED: rtl/rx_ram.v:102:12: Signal is not used: 'temp_sig'
%Warning-WIDTHEXPAND: other_file.v:10:5: Some warning for another file.
%Error: rtl/rx_ram.v:200:1: Syntax issue here.
"""


class TestParseLintOutput(unittest.TestCase):
    def test_extracts_issues_for_target_file(self):
        issues = parse_lint_output(SAMPLE_OUTPUT, "rtl/rx_ram.v")
        self.assertIn(75, issues)
        self.assertIn(102, issues)
        self.assertIn(200, issues)

    def test_ignores_other_files(self):
        issues = parse_lint_output(SAMPLE_OUTPUT, "rtl/rx_ram.v")
        # Line 10 belongs to other_file.v — must not appear
        self.assertNotIn(10, issues)

    def test_first_message_per_line_wins(self):
        output = """\
%Warning-A: myfile.v:5:1: First warning on line 5.
%Warning-B: myfile.v:5:3: Second warning on line 5.
"""
        issues = parse_lint_output(output, "myfile.v")
        self.assertEqual(issues[5], "First warning on line 5.")

    def test_continuation_lines_ignored(self):
        # Lines without leading % must not produce issues
        output = "%Warning-X: myfile.v:3:1: Real warning.\n   3 | some code\n      | ^~\n"
        issues = parse_lint_output(output, "myfile.v")
        self.assertEqual(list(issues.keys()), [3])

    def test_empty_output(self):
        self.assertEqual(parse_lint_output("", "myfile.v"), {})


class TestTagFile(unittest.TestCase):
    def _write(self, content):
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".v", delete=False)
        tmp.write(content)
        tmp.close()
        return tmp.name

    def tearDown(self):
        pass  # individual tests clean up their own files

    def test_tags_warned_line(self):
        path = self._write("module foo (input clk);\nassign x = y;\nendmodule\n")
        tag_file(path, {2: "Signal is not used: 'y'"}, ["verilator", "--lint-only", path])
        with open(path) as f:
            lines = f.readlines()
        # 2 headers inserted before the module, so original line 2 (idx 1) -> idx 3
        self.assertIn("/* Check: Signal is not used: 'y' */", lines[3])
        os.unlink(path)

    def test_adds_header_lines(self):
        path = self._write("module foo ();\nendmodule\n")
        tag_file(path, {1: "some warning"}, ["verilator", "--lint-only", path])
        with open(path) as f:
            content = f.read()
        self.assertIn("// lint-test:", content)
        self.assertIn("// tb-test: tba", content)
        os.unlink(path)

    def test_idempotent_headers(self):
        existing = "// lint-test: verilator --lint-only foo.v\n// tb-test: tba\nmodule foo ();\nendmodule\n"
        path = self._write(existing)
        tag_file(path, {3: "some warning"}, ["verilator", "--lint-only", path])
        with open(path) as f:
            content = f.read()
        self.assertEqual(content.count("// lint-test:"), 1)
        self.assertEqual(content.count("// tb-test:"), 1)
        os.unlink(path)

    def test_replaces_existing_check_comment(self):
        path = self._write("module foo ();\nassign x = y;  /* Check: old message */\nendmodule\n")
        tag_file(path, {2: "new message"}, ["verilator", "--lint-only", path])
        with open(path) as f:
            lines = f.readlines()
        # 2 headers inserted before the module, so original line 2 (idx 1) -> idx 3
        self.assertIn("/* Check: new message */", lines[3])
        self.assertNotIn("old message", lines[3])
        os.unlink(path)

    def test_out_of_bounds_line_number_ignored(self):
        path = self._write("module foo ();\nendmodule\n")
        # Line 999 doesn't exist — should not crash
        tag_file(path, {999: "phantom warning"}, ["verilator", "--lint-only", path])
        with open(path) as f:
            content = f.read()
        self.assertNotIn("phantom", content)
        os.unlink(path)

    def test_header_inserted_after_leading_comments(self):
        src = "// Copyright 2024\n// Author: eng\nmodule foo ();\nendmodule\n"
        path = self._write(src)
        tag_file(path, {3: "some warning"}, ["verilator", "--lint-only", path])
        with open(path) as f:
            lines = f.readlines()
        # First two lines must remain the copyright block
        self.assertTrue(lines[0].startswith("// Copyright"))
        self.assertTrue(lines[1].startswith("// Author"))
        # Headers come next
        self.assertTrue(lines[2].startswith("// lint-test:"))
        self.assertTrue(lines[3].startswith("// tb-test:"))
        os.unlink(path)


class TestRunLintIncludeDirs(unittest.TestCase):
    def _run(self, include_dirs):
        mock_result = Mock(stdout="", stderr="")
        with patch("veridoc.lint.subprocess.run", return_value=mock_result):
            return _run_lint("foo.v", include_dirs)

    def test_include_dir_is_separate_arg(self):
        _, cmd = self._run(["rtl/core/"])
        # Must appear as two separate elements, not concatenated
        self.assertIn("-I", cmd)
        self.assertNotIn("-Irtl/core/", cmd)
        idx = cmd.index("-I")
        self.assertEqual(cmd[idx + 1], "rtl/core/")

    def test_include_dir_joined_string_has_space(self):
        # The joined cmd string is what ends up in the lint-test header comment
        _, cmd = self._run(["rtl/core/"])
        cmd_str = " ".join(cmd)
        self.assertIn("-I rtl/core/", cmd_str)
        self.assertNotIn("-Irtl/core/", cmd_str)

    def test_multiple_include_dirs(self):
        _, cmd = self._run(["rtl/core/", "rtl/lib/"])
        cmd_str = " ".join(cmd)
        self.assertIn("-I rtl/core/", cmd_str)
        self.assertIn("-I rtl/lib/", cmd_str)


class TestTagFileDuplicateHeaders(unittest.TestCase):
    def _write(self, content):
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".v", delete=False)
        tmp.write(content)
        tmp.close()
        return tmp.name

    def test_no_duplicate_when_headers_outside_leading_block(self):
        # Headers appear after module declaration (not in the leading comment block).
        # Old code only checked header_block (leading comments) and would add duplicates here.
        src = "module foo ();\n// lint-test: verilator --lint-only foo.v\n// tb-test: tba\nendmodule\n"
        path = self._write(src)
        tag_file(path, {1: "some warning"}, ["verilator", "--lint-only", path])
        with open(path) as f:
            content = f.read()
        self.assertEqual(content.count("// lint-test:"), 1)
        self.assertEqual(content.count("// tb-test:"), 1)
        os.unlink(path)

    def test_no_duplicate_tb_test_when_only_tb_present(self):
        # Only tb-test already exists; lint-test should be added but tb-test must not duplicate.
        src = "// tb-test: some_script\nmodule foo ();\nendmodule\n"
        path = self._write(src)
        tag_file(path, {2: "some warning"}, ["verilator", "--lint-only", path])
        with open(path) as f:
            content = f.read()
        self.assertEqual(content.count("// tb-test:"), 1)
        os.unlink(path)


if __name__ == "__main__":
    unittest.main()
