import os
import shutil
import unittest
from rtl_aid.lint import _run_lint, parse_lint_output
from tests.support import LINT_FIXTURES

_HAS_VERILATOR = shutil.which("verilator") is not None


@unittest.skipUnless(_HAS_VERILATOR, "verilator not installed")
class TestIncludeDirEndToEnd(unittest.TestCase):
    """Real-verilator proof that the -I fix works, not just that the cmd
    list looks right. fixtures/toppw.v instantiates sub8, whose definition
    lives in fixtures/incdir/sub8.v and is only found via -I."""

    def test_include_dir_resolves_submodule(self):
        toppw = os.path.join(LINT_FIXTURES, "toppw.v")
        incdir = os.path.join(LINT_FIXTURES, "incdir")

        output, cmd = _run_lint(toppw, [incdir])

        self.assertNotIn("Cannot find file containing module", output)
        issues = parse_lint_output(output, toppw)
        # sub8's `a` port is 8 bits, toppw connects a 4-bit signal to it —
        # should surface as a width warning, not an elaboration failure.
        self.assertTrue(issues, f"expected a width warning, got: {output}")

    def test_space_separated_include_still_broken(self):
        # Documents the regression this fix addresses: the old space-separated
        # form is genuinely rejected by this verilator version, not just a
        # theoretical concern.
        import subprocess

        toppw = os.path.join(LINT_FIXTURES, "toppw.v")
        incdir = os.path.join(LINT_FIXTURES, "incdir")
        result = subprocess.run(
            ["verilator", "--lint-only", "-Wall", "-I", incdir, toppw],
            capture_output=True,
            text=True,
        )
        self.assertIn("Cannot find file containing module", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
