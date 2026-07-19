"""Tests for CLI vs config file precedence."""
import unittest
import tempfile
from pathlib import Path


class TestConfigPrecedence(unittest.TestCase):
    """Test that CLI args override config file values."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmproot = Path(self.tmpdir.name)

    def test_cli_dir_overrides_config_dir(self):
        """CLI --dir should override config rtldoc.dir."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  dir:
    - config_dir/
""")

        # Act
        from rtl_aid.config import merge_config_with_args
        cli_args = {
            "dir": ["cli_dir/"],
            "file": None,
            "out": None,
            "verbose": 0,
            "ci": False,
            "exclude": None,
            "export_graph": None,
            "from_graph": None,
            "dry_run": False,
            "print_errors": False,
        }
        config = {
            "rtldoc": {
                "dir": ["config_dir/"],
                "out": "docs/",
            }
        }
        merged = merge_config_with_args(config, cli_args, "rtldoc")

        # Assert
        self.assertEqual(merged["dir"], ["cli_dir/"])

    def test_cli_out_overrides_config_out(self):
        """CLI --out should override config rtldoc.out."""
        # Arrange
        cli_args = {"out": "cli_output/"}
        config = {"rtldoc": {"out": "config_output/"}}

        # Act
        from rtl_aid.config import merge_config_with_args
        merged = merge_config_with_args(
            config, cli_args, "rtldoc", ["out"]
        )

        # Assert
        self.assertEqual(merged["out"], "cli_output/")

    def test_cli_verbose_overrides_config_verbose(self):
        """CLI -v should override config rtldoc.verbose."""
        # Arrange
        cli_args = {"v": 2}  # -vv
        config = {"rtldoc": {"verbose": 0}}

        # Act
        from rtl_aid.config import merge_config_with_args
        merged = merge_config_with_args(
            config, cli_args, "rtldoc", ["verbose", "v"]
        )

        # Assert
        self.assertEqual(merged["verbose"], 2)

    def test_cli_ci_overrides_config_ci(self):
        """CLI --ci should override config rtldoc.ci."""
        # Arrange
        cli_args = {"ci": True}
        config = {"rtldoc": {"ci": False}}

        # Act
        from rtl_aid.config import merge_config_with_args
        merged = merge_config_with_args(config, cli_args, "rtldoc", ["ci"])

        # Assert
        self.assertTrue(merged["ci"])

    def test_cli_exclude_overrides_config_exclude(self):
        """CLI --exclude should override config rtldoc.exclude."""
        # Arrange
        cli_args = {"exclude": ["cli_exclude/"]}
        config = {"rtldoc": {"exclude": ["config_exclude/"]}}

        # Act
        from rtl_aid.config import merge_config_with_args
        merged = merge_config_with_args(
            config, cli_args, "rtldoc", ["exclude"]
        )

        # Assert
        self.assertEqual(merged["exclude"], ["cli_exclude/"])

    def test_cli_export_graph_overrides_config(self):
        """CLI --export-graph should override config rtldoc.export_graph."""
        # Arrange
        cli_args = {"export_graph": ["cli_graph.dot"]}
        config = {"rtldoc": {"export_graph": ["config_graph.json"]}}

        # Act
        from rtl_aid.config import merge_config_with_args
        merged = merge_config_with_args(
            config, cli_args, "rtldoc", ["export_graph"]
        )

        # Assert
        self.assertEqual(merged["export_graph"], ["cli_graph.dot"])

    def test_config_export_graph_used_when_cli_not_set(self):
        """Config rtldoc.export_graph should apply when CLI doesn't set it."""
        # Arrange
        cli_args = {"export_graph": None}
        config = {"rtldoc": {"export_graph": ["config_graph.json"]}}

        # Act
        from rtl_aid.config import merge_config_with_args
        merged = merge_config_with_args(config, cli_args, "rtldoc")

        # Assert
        self.assertEqual(merged["export_graph"], ["config_graph.json"])

    def test_cli_from_graph_overrides_config(self):
        """CLI --from-graph should override config rtldoc.from_graph."""
        # Arrange
        cli_args = {"from_graph": "cli_graph.json"}
        config = {"rtldoc": {"from_graph": "config_graph.json"}}

        # Act
        from rtl_aid.config import merge_config_with_args
        merged = merge_config_with_args(config, cli_args, "rtldoc", ["from_graph"])

        # Assert
        self.assertEqual(merged["from_graph"], "cli_graph.json")

    def test_cli_dry_run_overrides_config(self):
        """CLI --dry-run should override config rtldoc.dry_run."""
        # Arrange
        cli_args = {"dry_run": True}
        config = {"rtldoc": {"dry_run": False}}

        # Act
        from rtl_aid.config import merge_config_with_args
        merged = merge_config_with_args(
            config, cli_args, "rtldoc", ["dry_run"]
        )

        # Assert
        self.assertTrue(merged["dry_run"])

    def test_config_used_when_cli_not_set(self):
        """Config values should be used when CLI args not set."""
        # Arrange
        cli_args = {
            "dir": None,
            "file": None,
            "out": None,
            "verbose": 0,
            "ci": False,
            "exclude": None,
            "export_graph": None,
            "from_graph": None,
            "dry_run": False,
            "print_errors": False,
        }
        config = {"rtldoc": {"dir": ["config_dir/"], "out": "config_out/"}}

        # Act
        from rtl_aid.config import merge_config_with_args
        merged = merge_config_with_args(config, cli_args, "rtldoc")

        # Assert
        self.assertEqual(merged["dir"], ["config_dir/"])
        self.assertEqual(merged["out"], "config_out/")

    def test_cli_mutually_exclusive_file_overrides_config_dir(self):
        """CLI --file (mutually exclusive with --dir) should win over config dir."""
        # Arrange
        cli_args = {"file": ["cli_file.v"], "dir": None}
        config = {"rtldoc": {"dir": ["config_dir/"]}}

        # Act
        from rtl_aid.config import merge_config_with_args
        merged = merge_config_with_args(config, cli_args, "rtldoc")

        # Assert
        self.assertEqual(merged["file"], ["cli_file.v"])
        # dir should be None since file was explicitly set
        self.assertIsNone(merged.get("dir"))

    def test_unset_cli_args_use_config_defaults(self):
        """Unset CLI args (None or falsy) should fall through to config."""
        # Arrange
        cli_args = {"out": None, "verbose": 0, "ci": False}
        config = {"rtldoc": {"out": "config_docs/", "verbose": 1, "ci": True}}

        # Act
        from rtl_aid.config import merge_config_with_args
        merged = merge_config_with_args(config, cli_args, "rtldoc")

        # Assert
        self.assertEqual(merged["out"], "config_docs/")
        self.assertEqual(merged["verbose"], 1)
        self.assertTrue(merged["ci"])

    def test_rtllint_include_cli_overrides_config(self):
        """CLI -I should override config rtllint.include."""
        # Arrange
        cli_args = {"include_dirs": ["cli_include/"]}
        config = {"rtllint": {"include": ["config_include/"]}}

        # Act
        from rtl_aid.config import merge_config_with_args
        merged = merge_config_with_args(config, cli_args, "rtllint")

        # Assert
        self.assertEqual(merged["include"], ["cli_include/"])

    def test_rtllint_file_cli_overrides_config(self):
        """CLI file positional args should override config rtllint.file."""
        # Arrange
        cli_args = {"file": ["cli_module.v"]}
        config = {"rtllint": {"file": ["config_module.v"]}}

        # Act
        from rtl_aid.config import merge_config_with_args
        merged = merge_config_with_args(config, cli_args, "rtllint")

        # Assert
        self.assertEqual(merged["file"], ["cli_module.v"])


if __name__ == "__main__":
    unittest.main()
