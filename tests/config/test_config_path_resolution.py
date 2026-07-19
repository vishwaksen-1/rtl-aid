"""Tests for config file path resolution relative to config file directory."""
import unittest
import tempfile
import subprocess
import sys
import os
from pathlib import Path


class TestConfigPathResolution(unittest.TestCase):
    """Test that config paths are resolved relative to config file location."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmproot = Path(self.tmpdir.name)
        self._create_project_structure()

    def _create_project_structure(self):
        """Create: project_root/.rtl-aidrc.yml and project_root/subdir/design/*.v"""
        # Create: subdir/design/module1/file1.v, subdir/design/module2/file2.v
        (self.tmproot / "subdir" / "design" / "module1").mkdir(parents=True)
        (self.tmproot / "subdir" / "design" / "module2").mkdir(parents=True)
        (self.tmproot / "subdir" / "design" / "module1" / "file1.v").write_text(
            "module file1(input a); endmodule"
        )
        (self.tmproot / "subdir" / "design" / "module2" / "file2.v").write_text(
            "module file2(output b); endmodule"
        )

    def test_paths_resolved_relative_to_config_file_directory(self):
        """Config paths should be resolved relative to config file location, not cwd."""
        # Create config in project root
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  dir:
    - subdir/design/*/*.v
  out: docs/
""")

        original_cwd = os.getcwd()
        try:
            # Change to subdirectory (NOT project root)
            os.chdir(str(self.tmproot / "subdir"))

            # Run rtldoc with explicit config pointing to root
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "--config", "../.rtl-aidrc.yml", "--dry-run", "-vv"],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Should find 2 modules (from subdir/design/*/*.v relative to root)
            # NOT try to find subdir/subdir/design/*/*.v (which would fail)
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertIn("2 module(s) processed", result.stdout,
                         f"Expected 2 modules. stdout: {result.stdout}")
        finally:
            os.chdir(original_cwd)

    def test_upward_search_finds_config_and_resolves_paths_correctly(self):
        """Config found via upward search should resolve paths relative to its location."""
        # Create config in project root
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  dir:
    - subdir/design/*/*.v
  out: docs/
""")

        original_cwd = os.getcwd()
        try:
            # Change to subdirectory (upward search will find parent config)
            os.chdir(str(self.tmproot / "subdir"))

            # Run rtldoc WITHOUT explicit config (will find parent via upward search)
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "--dry-run"],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Should find 2 modules using upward-found config
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertIn("2 module(s) processed", result.stdout)
        finally:
            os.chdir(original_cwd)

    def test_absolute_paths_in_config_remain_absolute(self):
        """Absolute paths in config should not be adjusted."""
        # Create config with absolute path
        config_file = self.tmproot / ".rtl-aidrc.yml"
        abs_path = str(self.tmproot / "subdir" / "design" / "*" / "*.v")
        config_file.write_text(f"""
rtldoc:
  dir:
    - {abs_path}
  out: docs/
""")

        original_cwd = os.getcwd()
        try:
            # Change to different directory
            os.chdir(str(self.tmproot / "subdir"))

            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "--config", "../.rtl-aidrc.yml", "--dry-run"],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Should find 2 modules using absolute path
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertIn("2 module(s) processed", result.stdout)
        finally:
            os.chdir(original_cwd)

    def test_mixed_absolute_and_relative_paths(self):
        """Config can mix absolute and relative paths; each resolved correctly."""
        config_file = self.tmproot / ".rtl-aidrc.yml"
        abs_path = str(self.tmproot / "subdir" / "design" / "module1" / "*.v")
        config_file.write_text(f"""
rtldoc:
  dir:
    - {abs_path}
    - subdir/design/module2/*.v
  out: docs/
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot / "subdir"))

            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "--config", "../.rtl-aidrc.yml", "--dry-run"],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Should find 2 modules: 1 from absolute path, 1 from relative path
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertIn("2 module(s) processed", result.stdout)
        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
