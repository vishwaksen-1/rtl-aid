import unittest
from unittest.mock import patch, Mock
from rtl_aid.lint import _run_lint


class TestRunLintIncludeDirs(unittest.TestCase):
    """checklist: rtllint's -I flag was built as `["-I", dir]` (space
    separated). On Verilator 5.048 that form is NOT accepted as an include
    path — verilator parses the directory argument as a bare positional
    module-search request and hard-errors ("Cannot find file containing
    module: '<dir>'"), confirmed by shelling real verilator during review.
    Only the attached form `-I<dir>` works. See TODO.md."""

    def _run(self, include_dirs):
        mock_result = Mock(stdout="", stderr="")
        with patch("rtl_aid.lint.subprocess.run", return_value=mock_result):
            return _run_lint("foo.v", include_dirs)

    def test_include_dir_is_attached_no_space(self):
        _, cmd = self._run(["rtl/core/"])
        self.assertIn("-Irtl/core/", cmd)
        self.assertNotIn("-I", cmd)

    def test_include_dir_joined_string_has_no_space(self):
        # The joined cmd string is what ends up in the lint-test header comment
        _, cmd = self._run(["rtl/core/"])
        cmd_str = " ".join(cmd)
        self.assertIn("-Irtl/core/", cmd_str)
        self.assertNotIn("-I rtl/core/", cmd_str)

    def test_multiple_include_dirs(self):
        _, cmd = self._run(["rtl/core/", "rtl/lib/"])
        cmd_str = " ".join(cmd)
        self.assertIn("-Irtl/core/", cmd_str)
        self.assertIn("-Irtl/lib/", cmd_str)


if __name__ == "__main__":
    unittest.main()
