"""Integration tests for config file feature with rtldoc/rtllint CLI."""
import unittest
import tempfile
import subprocess
import sys
import os
from pathlib import Path


class TestRtldocWithConfigFile(unittest.TestCase):
    """Integration tests: rtldoc with config file."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmproot = Path(self.tmpdir.name)
        self._create_test_verilog()

    def _create_test_verilog(self):
        """Create sample Verilog files for testing."""
        src_dir = self.tmproot / "src"
        src_dir.mkdir()

        (src_dir / "top.v").write_text("""
module top (
    input clk,
    output reg out
);
    always @(posedge clk) out <= 1;
endmodule
""")

    def _create_test_config(self, config_content):
        """Helper to create test config file."""
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text(config_content)
        return config_file

    def test_rtldoc_reads_config_from_current_dir(self):
        """rtldoc should read .rtl-aidrc.yml from current directory."""
        # Arrange
        self._create_test_config("""
rtldoc:
  dir:
    - src/
  out: docs/modules
""")

        # Act
        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))

            # Import and call directly (since subprocess is complex to test)
            from rtl_aid.cli import main
            from rtl_aid.config import load_config_for_rtldoc

            config = load_config_for_rtldoc()

            # Assert
            self.assertIsNotNone(config)
            self.assertIn("dir", config)
            self.assertEqual(config["dir"], ["src/"])
            self.assertEqual(config["out"], "docs/modules")
        finally:
            os.chdir(original_cwd)

    def test_rtldoc_cli_args_override_config(self):
        """rtldoc CLI args should override config file values."""
        # Arrange
        self._create_test_config("""
rtldoc:
  dir:
    - config_dir/
  out: config_out/
""")

        # Act
        from rtl_aid.config import load_config_for_rtldoc, merge_config_with_args

        config = load_config_for_rtldoc()

        # Simulate CLI args (--dir src/ --out cli_out/)
        cli_args = {
            "dir": ["src/"],
            "out": "cli_out/",
            "file": None,
            "verbose": 0,
            "ci": False,
            "exclude": None,
            "json_graph": False,
            "json_graph_file": None,
            "export_dot": None,
            "dry_run": False,
            "print_errors": False,
        }

        merged = merge_config_with_args(config, cli_args, "rtldoc")

        # Assert
        self.assertEqual(merged["dir"], ["src/"])
        self.assertEqual(merged["out"], "cli_out/")

    def test_rtldoc_with_config_flag_uses_explicit_path(self):
        """rtldoc --config FILE should use explicit config path."""
        # Arrange
        custom_config = self.tmproot / "custom.yml"
        custom_config.write_text("""
rtldoc:
  dir:
    - custom_dir/
""")

        # Act
        from rtl_aid.config import find_config_file

        # Simulate --config custom.yml
        found = find_config_file(
            start_dir=str(self.tmproot),
            config_flag=str(custom_config)
        )

        # Assert
        self.assertEqual(found, str(custom_config))

    def test_rtldoc_processes_all_config_options(self):
        """rtldoc should process all config options correctly."""
        # Arrange
        self._create_test_config("""
rtldoc:
  dir:
    - src/
  out: docs/
  verbose: 1
  ci: true
  print_errors: true
  json_graph: true
  json_graph_file: docs/graph.json
  exclude:
    - testbench/
  dry_run: false
""")

        # Act
        from rtl_aid.config import parse_config

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))
            config = parse_config(".rtl-aidrc.yml")

            # Assert
            self.assertEqual(config["rtldoc"]["dir"], ["src/"])
            self.assertEqual(config["rtldoc"]["out"], "docs/")
            self.assertEqual(config["rtldoc"]["verbose"], 1)
            self.assertTrue(config["rtldoc"]["ci"])
            self.assertTrue(config["rtldoc"]["print_errors"])
            self.assertTrue(config["rtldoc"]["json_graph"])
            self.assertEqual(config["rtldoc"]["json_graph_file"], "docs/graph.json")
            self.assertEqual(config["rtldoc"]["exclude"], ["testbench/"])
            self.assertFalse(config["rtldoc"]["dry_run"])
        finally:
            os.chdir(original_cwd)


class TestRtllintWithConfigFile(unittest.TestCase):
    """Integration tests: rtllint with config file."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmproot = Path(self.tmpdir.name)
        self._create_test_verilog()

    def _create_test_verilog(self):
        """Create sample Verilog files for testing."""
        src_dir = self.tmproot / "src"
        src_dir.mkdir()

        (src_dir / "test.v").write_text("""
module test (
    input clk
);
    always @(clk) begin
        // missing sensitivity
    end
endmodule
""")

    def _create_test_config(self, config_content):
        """Helper to create test config file."""
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text(config_content)
        return config_file

    def test_rtllint_reads_config_from_current_dir(self):
        """rtllint should read .rtl-aidrc.yml from current directory."""
        # Arrange
        self._create_test_config("""
rtllint:
  file:
    - src/test.v
  include:
    - include/
""")

        # Act
        from rtl_aid.config import load_config_for_rtllint

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))
            config = load_config_for_rtllint()

            # Assert
            self.assertIsNotNone(config)
            self.assertIn("file", config)
            self.assertEqual(config["file"], ["src/test.v"])
            self.assertEqual(config["include"], ["include/"])
        finally:
            os.chdir(original_cwd)

    def test_rtllint_cli_args_override_config(self):
        """rtllint CLI args should override config file values."""
        # Arrange
        self._create_test_config("""
rtllint:
  file:
    - config_file.v
  include:
    - config_include/
""")

        # Act
        from rtl_aid.config import parse_config, merge_config_with_args

        config = parse_config(str(self.tmproot / ".rtl-aidrc.yml"))

        # Simulate CLI args (different file and include)
        cli_args = {
            "file": ["cli_file.v"],
            "include_dirs": ["cli_include/"],
            "dry_run": False,
            "v": False,
        }

        merged = merge_config_with_args(config, cli_args, "rtllint")

        # Assert
        self.assertEqual(merged["file"], ["cli_file.v"])
        self.assertEqual(merged["include"], ["cli_include/"])

    def test_rtllint_processes_all_config_options(self):
        """rtllint should process all config options correctly."""
        # Arrange
        self._create_test_config("""
rtllint:
  file:
    - src/test.v
  include:
    - include/
    - common/
  verbose: true
  dry_run: false
""")

        # Act
        from rtl_aid.config import parse_config

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))
            config = parse_config(".rtl-aidrc.yml")

            # Assert
            self.assertEqual(config["rtllint"]["file"], ["src/test.v"])
            self.assertEqual(config["rtllint"]["include"], ["include/", "common/"])
            self.assertTrue(config["rtllint"]["verbose"])
            self.assertFalse(config["rtllint"]["dry_run"])
        finally:
            os.chdir(original_cwd)


class TestConfigSearchUpward(unittest.TestCase):
    """Integration tests: config file upward search."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmproot = Path(self.tmpdir.name)

    def test_find_config_from_deep_subdirectory(self):
        """Should find .rtl-aidrc.yml from deep subdirectory."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("rtldoc:\n  dir:\n    - src/\n")

        deepdir = self.tmproot / "a" / "b" / "c"
        deepdir.mkdir(parents=True)

        # Act
        from rtl_aid.config import find_config_file

        found = find_config_file(start_dir=str(deepdir))

        # Assert
        self.assertEqual(found, str(config_file))

    def test_find_nearest_config_in_hierarchy(self):
        """Should prefer nearest config over distant one."""
        # Arrange
        root_config = self.tmproot / ".rtl-aidrc.yml"
        root_config.write_text("rtldoc:\n  dir:\n    - root/\n")

        mid_dir = self.tmproot / "project"
        mid_dir.mkdir()
        mid_config = mid_dir / ".rtl-aidrc.yml"
        mid_config.write_text("rtldoc:\n  dir:\n    - project/\n")

        search_dir = mid_dir / "src"
        search_dir.mkdir()

        # Act
        from rtl_aid.config import find_config_file

        found = find_config_file(start_dir=str(search_dir))

        # Assert
        self.assertEqual(found, str(mid_config))

    def test_stop_at_first_config_found(self):
        """Should stop searching once config found."""
        # Arrange
        root_config = self.tmproot / ".rtl-aidrc.yml"
        root_config.write_text("rtldoc:\n  dir:\n    - root/\n")

        search_dir = self.tmproot / "src" / "rtl"
        search_dir.mkdir(parents=True)

        # Act
        from rtl_aid.config import find_config_file

        found = find_config_file(start_dir=str(search_dir))

        # Assert
        # Should find root config (only one in this test)
        self.assertEqual(found, str(root_config))


class TestConfigErrorHandling(unittest.TestCase):
    """Integration tests: error handling with config files."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmproot = Path(self.tmpdir.name)

    def test_malformed_config_produces_clear_error(self):
        """Malformed config should produce clear error message."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("rtldoc:\n  dir:\n    - src/\n  invalid: [unclosed\n")

        # Act & Assert
        from rtl_aid.config import parse_config, ConfigError

        with self.assertRaises(ConfigError) as ctx:
            parse_config(str(config_file))

        self.assertIn("YAML", str(ctx.exception))

    def test_invalid_option_type_produces_error(self):
        """Invalid option type should produce clear error."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("rtldoc:\n  verbose: invalid\n")

        # Act & Assert
        from rtl_aid.config import parse_config, validate_config, ConfigError

        config = parse_config(str(config_file))
        with self.assertRaises(ConfigError):
            validate_config(config)

    def test_missing_config_with_config_flag_errors(self):
        """Should error if --config FILE points to missing file."""
        # Arrange
        nonexistent = str(self.tmproot / "nonexistent.yml")

        # Act & Assert
        from rtl_aid.config import find_config_file, ConfigError

        with self.assertRaises(ConfigError):
            find_config_file(start_dir=str(self.tmproot), config_flag=nonexistent)


if __name__ == "__main__":
    unittest.main()
