"""Tests for CLI edge cases discovered during real-world testing."""

import unittest
import tempfile
import subprocess
import sys
import os
from pathlib import Path


class TestDotExportCLI(unittest.TestCase):
    """Tests for DOT export via CLI with various scenarios."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmproot = Path(self.tmpdir.name)
        self._create_test_verilog()

    def _create_test_verilog(self):
        """Create sample Verilog files for testing."""
        (self.tmproot / "src").mkdir()
        (self.tmproot / "src" / "top.v").write_text("""
module top (input clk);
    sub_mod inst(.clk(clk));
endmodule
module sub_mod (input clk);
endmodule
""")

    def test_dot_export_with_nested_output_path(self):
        """--export-dot with nested path should create parent directories."""
        output_path = str(self.tmproot / "output" / "nested" / "graph.dot")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "-f", "src/top.v", "--export-dot", output_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Should succeed
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            # File should exist
            self.assertTrue(os.path.exists(output_path))
        finally:
            os.chdir(original_cwd)

    def test_dot_export_with_absolute_path(self):
        """--export-dot with absolute path should work."""
        output_path = os.path.join(self.tmproot, "graph.dot")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "-f", "src/top.v", "--export-dot", output_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertTrue(os.path.exists(output_path))
        finally:
            os.chdir(original_cwd)

    def test_json_graph_file_with_nested_path(self):
        """--json-graph-file with nested path should create parent dirs."""
        json_path = str(self.tmproot / "output" / "graphs" / "deps.json")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "-f", "src/top.v", "--json-graph", "--json-graph-file", json_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertTrue(os.path.exists(json_path))
        finally:
            os.chdir(original_cwd)

    def test_dot_export_graph_only_mode(self):
        """--export-dot with existing graph should read from JSON (graph-only mode)."""
        # First generate graph.json
        json_path = str(self.tmproot / "graph.json")
        dot_path = str(self.tmproot / "output.dot")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))

            # Step 1: Generate JSON graph
            result1 = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "-f", "src/top.v", "--json-graph", "--json-graph-file", json_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            self.assertEqual(result1.returncode, 0)
            self.assertTrue(os.path.exists(json_path))

            # Step 2: Export to DOT from JSON (no scanning)
            result2 = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "--json-graph-file", json_path, "--export-dot", dot_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            self.assertEqual(result2.returncode, 0, f"stderr: {result2.stderr}")
            self.assertTrue(os.path.exists(dot_path))
        finally:
            os.chdir(original_cwd)


class TestConfigWithSpecialPaths(unittest.TestCase):
    """Tests for config with special path cases."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmproot = Path(self.tmpdir.name)

    def test_config_with_spaces_in_directory_names(self):
        """Config should handle paths with spaces."""
        # Create directories with spaces
        design_dir = self.tmproot / "design with spaces" / "module one"
        design_dir.mkdir(parents=True)
        (design_dir / "core.v").write_text("module core(input a); endmodule")

        # Create config with spaces in path
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  dir:
    - design with spaces/module one/*.v
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

            # Should find the module despite spaces
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertIn("1 module(s) processed", result.stdout)
        finally:
            os.chdir(original_cwd)

    def test_config_with_relative_output_directory(self):
        """Config output dir should resolve relative to config file location."""
        subdir = self.tmproot / "subdir"
        subdir.mkdir()
        design_dir = self.tmproot / "design"
        design_dir.mkdir()
        (design_dir / "mod.v").write_text("module mod(input a); endmodule")

        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  dir:
    - design/*.v
  out: docs/output/
""")

        original_cwd = os.getcwd()
        try:
            # Run from subdirectory; config should resolve paths from root
            os.chdir(str(subdir))
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "--config", "../.rtl-aidrc.yml"],
                capture_output=True,
                text=True,
                timeout=10
            )

            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            # Docs should be in root's docs/output/, not subdir/docs/output/
            self.assertTrue(os.path.exists(self.tmproot / "docs" / "output" / "mod.md"))
        finally:
            os.chdir(original_cwd)

    def test_absolute_paths_in_config_not_relative_to_config_dir(self):
        """Absolute paths in config should not be modified."""
        design_dir = self.tmproot / "design"
        design_dir.mkdir()
        (design_dir / "mod.v").write_text("module mod(input a); endmodule")

        # Use absolute path in config
        abs_pattern = str(self.tmproot / "design" / "*.v")
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text(f"""
rtldoc:
  dir:
    - {abs_pattern}
  out: docs/
""")

        original_cwd = os.getcwd()
        try:
            # Run from different directory
            os.chdir("/tmp")
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "--config", str(config_file), "--dry-run"],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Should find module via absolute path
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertIn("1 module(s) processed", result.stdout)
        finally:
            os.chdir(original_cwd)


class TestConfigMergingPrecedence(unittest.TestCase):
    """Tests for config merging and CLI precedence."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmproot = Path(self.tmpdir.name)
        self._create_test_verilog()

    def _create_test_verilog(self):
        """Create test Verilog structure."""
        (self.tmproot / "design" / "mod1").mkdir(parents=True)
        (self.tmproot / "design" / "mod2").mkdir(parents=True)
        (self.tmproot / "design" / "mod1" / "a.v").write_text("module a(input x); endmodule")
        (self.tmproot / "design" / "mod2" / "b.v").write_text("module b(input y); endmodule")

    def test_cli_dir_flag_overrides_config_dir(self):
        """CLI -d should completely override config dir."""
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  dir:
    - design/mod1/*.v
  out: docs/
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))

            # Use CLI override to process mod2 instead
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "-d", "design/mod2", "--dry-run"],
                capture_output=True,
                text=True,
                timeout=10
            )

            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            # Should find b (from mod2), not a (from config's mod1)
            self.assertIn("1 module(s) processed", result.stdout)
        finally:
            os.chdir(original_cwd)

    def test_cli_out_flag_overrides_config_out(self):
        """CLI -o should override config out."""
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  dir:
    - design/mod1/*.v
  out: config_docs/
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))

            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "-o", "cli_docs/"],
                capture_output=True,
                text=True,
                timeout=10
            )

            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            # Docs should be in cli_docs/, not config_docs/
            self.assertTrue(os.path.exists(self.tmproot / "cli_docs" / "a.md"))
            self.assertFalse(os.path.exists(self.tmproot / "config_docs"))
        finally:
            os.chdir(original_cwd)

    def test_config_used_when_no_cli_args(self):
        """Config should be used when no CLI dir/file specified."""
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  dir:
    - design/mod1/*.v
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

            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            # Should find a (from config's mod1)
            self.assertIn("1 module(s) processed", result.stdout)
        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
