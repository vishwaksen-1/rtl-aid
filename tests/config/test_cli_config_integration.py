"""Integration tests for CLI with config file (rtldoc with config, not just config loading)."""
import unittest
import tempfile
import subprocess
import sys
import os
from pathlib import Path


class TestRtldocCliUsesConfig(unittest.TestCase):
    """Test that rtldoc CLI actually loads and uses config file values."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmproot = Path(self.tmpdir.name)
        self._create_test_verilog()

    def _create_test_verilog(self):
        """Create sample Verilog file."""
        src_dir = self.tmproot / "src"
        src_dir.mkdir()
        (src_dir / "test.v").write_text("""
module test_mod (
    input clk,
    output reg out
);
    always @(posedge clk) out <= 1;
endmodule
""")

    def _create_config(self, content):
        """Create config file."""
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text(content)
        return config_file

    def test_rtldoc_works_without_cli_args_when_config_has_dir(self):
        """rtldoc should work without -d/--dir if config file specifies dir."""
        self._create_config("""
rtldoc:
  dir:
    - src/
  out: docs/
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))
            # Run rtldoc WITHOUT CLI args - should succeed because config has dir
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli"],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Should succeed (exit code 0)
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            # Should generate markdown
            self.assertTrue((self.tmproot / "docs" / "test_mod.md").exists())
        finally:
            os.chdir(original_cwd)

    def test_rtldoc_works_without_cli_args_when_config_has_file(self):
        """rtldoc should work without -f/--file if config file specifies file."""
        self._create_config("""
rtldoc:
  file:
    - src/test.v
  out: docs/
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli"],
                capture_output=True,
                text=True,
                timeout=10
            )

            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertTrue((self.tmproot / "docs" / "test_mod.md").exists())
        finally:
            os.chdir(original_cwd)

    def test_rtldoc_uses_output_dir_from_config(self):
        """rtldoc should use output directory from config file."""
        self._create_config("""
rtldoc:
  dir:
    - src/
  out: custom_output/
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli"],
                capture_output=True,
                text=True,
                timeout=10
            )

            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            # Should write to custom_output/, not default temp/docs/modules/
            self.assertTrue((self.tmproot / "custom_output" / "test_mod.md").exists())
            self.assertFalse((self.tmproot / "temp" / "docs" / "modules").exists())
        finally:
            os.chdir(original_cwd)

    def test_cli_args_override_config_dir(self):
        """CLI -d should override config file dir."""
        cli_src = self.tmproot / "cli_src"
        cli_src.mkdir()
        (cli_src / "cli_test.v").write_text("""
module cli_test (input a);
endmodule
""")

        self._create_config("""
rtldoc:
  dir:
    - src/
  out: docs/
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))
            # Use CLI to override config's dir
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "-d", "cli_src"],
                capture_output=True,
                text=True,
                timeout=10
            )

            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            # Should find cli_test from cli_src, not test_mod from src
            self.assertTrue((self.tmproot / "docs" / "cli_test.md").exists())
            # src/test.v should NOT be processed (from config's dir)
            self.assertFalse((self.tmproot / "docs" / "test_mod.md").exists())
        finally:
            os.chdir(original_cwd)

    def test_cli_args_override_config_out(self):
        """CLI -o should override config file out."""
        self._create_config("""
rtldoc:
  dir:
    - src/
  out: config_docs/
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))
            # Use CLI to override config's out directory
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "-o", "cli_docs"],
                capture_output=True,
                text=True,
                timeout=10
            )

            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            # Should write to cli_docs (from CLI), not config_docs (from config)
            self.assertTrue((self.tmproot / "cli_docs" / "test_mod.md").exists())
            self.assertFalse((self.tmproot / "config_docs").exists())
        finally:
            os.chdir(original_cwd)

    def test_rtldoc_fails_without_config_and_without_cli_args(self):
        """rtldoc should fail if neither config nor CLI args specify dir/file."""
        # Create config WITHOUT dir/file
        self._create_config("""
rtldoc:
  out: docs/
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli"],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Should fail because no dir or file specified anywhere
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("required", result.stderr.lower())
        finally:
            os.chdir(original_cwd)

    def test_config_file_upward_search_used_by_cli(self):
        """rtldoc should find config file in parent directory."""
        # Create config in root with absolute paths
        self._create_config(f"""
rtldoc:
  dir:
    - {self.tmproot}/src/
  out: {self.tmproot}/docs/
""")

        # Create subdir where we'll run rtldoc
        subdir = self.tmproot / "subdir"
        subdir.mkdir()

        original_cwd = os.getcwd()
        try:
            os.chdir(str(subdir))
            # Run from subdir, should find config in parent
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli"],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Should succeed by finding parent's config
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            # Docs should be in parent's docs/ dir (using absolute path from config)
            self.assertTrue((self.tmproot / "docs" / "test_mod.md").exists())
        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
