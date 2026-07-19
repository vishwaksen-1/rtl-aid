"""Tests for CLI edge cases discovered during real-world testing."""

import unittest
import tempfile
import subprocess
import sys
import os
from pathlib import Path


class TestGraphExportCLI(unittest.TestCase):
    """Tests for the unified --export-graph / --from-graph CLI surface."""

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

    def test_export_graph_dot_with_nested_output_path(self):
        """--export-graph with a nested .dot path should create parent directories."""
        output_path = str(self.tmproot / "output" / "nested" / "graph.dot")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "-f", "src/top.v", "--export-graph", output_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertTrue(os.path.exists(output_path))
        finally:
            os.chdir(original_cwd)

    def test_export_graph_dot_with_absolute_path(self):
        """--export-graph with an absolute .dot path should work."""
        output_path = os.path.join(self.tmproot, "graph.dot")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "-f", "src/top.v", "--export-graph", output_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertTrue(os.path.exists(output_path))
        finally:
            os.chdir(original_cwd)

    def test_export_graph_json_with_nested_path(self):
        """--export-graph with a nested .json path should create parent dirs."""
        json_path = str(self.tmproot / "output" / "graphs" / "deps.json")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "-f", "src/top.v", "--export-graph", json_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertTrue(os.path.exists(json_path))
        finally:
            os.chdir(original_cwd)

    def test_export_graph_json_and_dot_in_one_run(self):
        """A single --export-graph per format, repeated, writes both files from one scan."""
        json_path = str(self.tmproot / "graph.json")
        dot_path = str(self.tmproot / "graph.dot")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "-f", "src/top.v",
                 "--export-graph", json_path, "--export-graph", dot_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertTrue(os.path.exists(json_path))
            self.assertTrue(os.path.exists(dot_path))
        finally:
            os.chdir(original_cwd)

    def test_from_graph_converts_without_rescanning(self):
        """--from-graph should convert an existing JSON graph to DOT without scanning source."""
        json_path = str(self.tmproot / "graph.json")
        dot_path = str(self.tmproot / "output.dot")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))

            # Step 1: Generate JSON graph from a real scan.
            result1 = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "-f", "src/top.v", "--export-graph", json_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            self.assertEqual(result1.returncode, 0)
            self.assertTrue(os.path.exists(json_path))

            # Step 2: Convert JSON -> DOT via --from-graph, no -d/-f at all.
            result2 = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "--from-graph", json_path, "--export-graph", dot_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            self.assertEqual(result2.returncode, 0, f"stderr: {result2.stderr}")
            self.assertTrue(os.path.exists(dot_path))
        finally:
            os.chdir(original_cwd)

    def test_from_graph_ignores_config_dir_no_rescan(self):
        """Regression test: --from-graph must convert without rescanning, even when
        the project's .rtl-aidrc.yml sets 'dir' (the bug that made the old
        --json-graph-file/--export-dot graph-only shortcut unreachable in real
        projects, since it only fired when neither dir nor file was configured)."""
        json_path = str(self.tmproot / "graph.json")
        dot_path = str(self.tmproot / "output.dot")

        (self.tmproot / ".rtl-aidrc.yml").write_text(f"""
rtldoc:
  dir:
    - src/
  out: docs/
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))

            # Seed a graph.json to convert (independent of the config's dir).
            with open(json_path, "w") as f:
                f.write('{"top": {"calls": ["sub_mod"], "called_by": []}, "sub_mod": {"calls": [], "called_by": ["top"]}}')

            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "--from-graph", json_path, "--export-graph", dot_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            self.assertTrue(os.path.exists(dot_path))
            # No rescan happened: config's out dir was never created/written to.
            self.assertFalse(os.path.exists(self.tmproot / "docs"))
        finally:
            os.chdir(original_cwd)

    def test_export_graph_only_config_value_takes_effect(self):
        """Regression test: export_graph set only in .rtl-aidrc.yml (no CLI flag)
        must actually produce the file — previously the normal run path read
        args.export_dot directly instead of the merged config+CLI value, so a
        config-only setting was silently ignored."""
        (self.tmproot / ".rtl-aidrc.yml").write_text("""
rtldoc:
  dir:
    - src/
  out: docs/
  export_graph:
    - graph.dot
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
            # Bare filename with no CLI flag involved -> resolved into out dir.
            self.assertTrue(os.path.exists(self.tmproot / "docs" / "graph.dot"))
        finally:
            os.chdir(original_cwd)

    def test_from_graph_with_dir_flag_errors(self):
        """--from-graph combined with -d should error clearly (ambiguous request)."""
        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "--from-graph", "graph.json",
                 "-d", "src/", "--export-graph", "graph.dot"],
                capture_output=True,
                text=True,
                timeout=10
            )
            self.assertNotEqual(result.returncode, 0)
        finally:
            os.chdir(original_cwd)

    def test_export_graph_bad_extension_errors(self):
        """--export-graph with an unsupported extension should error clearly."""
        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))
            result = subprocess.run(
                [sys.executable, "-m", "rtl_aid.cli", "-f", "src/top.v", "--export-graph", "graph.txt"],
                capture_output=True,
                text=True,
                timeout=10
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(".json", result.stderr + result.stdout)
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
