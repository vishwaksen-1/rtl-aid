"""Tests for glob pattern expansion in config files and CLI."""
import unittest
import tempfile
import subprocess
import sys
import os
from pathlib import Path
from rtl_aid.config import load_config_for_rtldoc


class TestConfigGlobPatterns(unittest.TestCase):
    """Test that config file glob patterns are expanded correctly."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmproot = Path(self.tmpdir.name)

    def _create_verilog_files(self):
        """Create directory structure with Verilog files."""
        # Create: design/module1/file1.v, design/module1/file2.v, design/module2/file3.v
        (self.tmproot / "design" / "module1").mkdir(parents=True)
        (self.tmproot / "design" / "module2").mkdir(parents=True)
        (self.tmproot / "design" / "module1" / "file1.v").write_text("module file1(); endmodule")
        (self.tmproot / "design" / "module1" / "file2.v").write_text("module file2(); endmodule")
        (self.tmproot / "design" / "module2" / "file3.v").write_text("module file3(); endmodule")

    def test_config_dir_with_glob_pattern_single_level(self):
        """Config file should support glob patterns in dir list."""
        self._create_verilog_files()
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  dir:
    - design/*.v
  out: docs/
""")

        config = load_config_for_rtldoc(str(config_file))

        # Should have expanded glob pattern
        self.assertIn("dir", config)
        # Should find design/*.v (non-recursive) - should match 0 files at top level
        # But the glob should be in the dir list
        self.assertEqual(len(config["dir"]), 1)
        self.assertEqual(config["dir"][0], "design/*.v")

    def test_config_dir_with_glob_pattern_recursive(self):
        """Config file should support recursive glob patterns in dir list."""
        self._create_verilog_files()
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  dir:
    - design/**/*.v
  out: docs/
""")

        config = load_config_for_rtldoc(str(config_file))

        # Should have the glob pattern
        self.assertIn("dir", config)
        self.assertEqual(config["dir"][0], "design/**/*.v")

    def test_config_multiple_glob_patterns(self):
        """Config file should support multiple glob patterns."""
        self._create_verilog_files()
        (self.tmproot / "rtl").mkdir()
        (self.tmproot / "rtl" / "core.v").write_text("module core(); endmodule")

        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  dir:
    - design/**/*.v
    - rtl/*.v
  out: docs/
""")

        config = load_config_for_rtldoc(str(config_file))

        # Should have both glob patterns
        self.assertIn("dir", config)
        self.assertEqual(len(config["dir"]), 2)
        self.assertIn("design/**/*.v", config["dir"])
        self.assertIn("rtl/*.v", config["dir"])

    def test_config_file_with_glob_patterns(self):
        """Config file should support glob patterns in file list."""
        self._create_verilog_files()
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  file:
    - design/**/*.v
  out: docs/
""")

        config = load_config_for_rtldoc(str(config_file))

        # Should have the glob pattern in file list
        self.assertIn("file", config)
        self.assertEqual(config["file"][0], "design/**/*.v")


class TestCliGlobPatternExpansion(unittest.TestCase):
    """Test that CLI expands glob patterns from config file."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmproot = Path(self.tmpdir.name)
        self._create_verilog_structure()

    def _create_verilog_structure(self):
        """Create directory structure similar to user's USB4 project."""
        # design/module1/file1.v, design/module2/file2.v
        (self.tmproot / "design" / "module1").mkdir(parents=True)
        (self.tmproot / "design" / "module2").mkdir(parents=True)
        (self.tmproot / "design" / "module1" / "file1.v").write_text(
            "module file1(input a, output b); endmodule"
        )
        (self.tmproot / "design" / "module2" / "file2.v").write_text(
            "module file2(input c, output d); endmodule"
        )

    def test_cli_expands_glob_patterns_from_config(self):
        """rtldoc should expand glob patterns from config file."""
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  dir:
    - design/*/*.v
  out: docs/
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "--dry-run"],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Should find 2 modules (file1, file2) from expanded glob pattern
            self.assertIn("2 module(s) processed", result.stdout, f"stderr: {result.stderr}")
        finally:
            os.chdir(original_cwd)

    def test_cli_uses_config_glob_pattern_for_output(self):
        """rtldoc should process files found via glob pattern in config."""
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  dir:
    - design/**/*.v
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

            # Should succeed and find modules
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            # Should have generated docs for both modules
            self.assertTrue((self.tmproot / "docs" / "file1.md").exists())
            self.assertTrue((self.tmproot / "docs" / "file2.md").exists())
        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
