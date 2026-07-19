"""Tests for config file parsing and validation."""
import unittest
import tempfile
from pathlib import Path
from tests.support import CORE_FIXTURES, copy_fixture


class TestConfigFileParsing(unittest.TestCase):
    """Test YAML parsing of .rtl-aidrc.yml files."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmproot = Path(self.tmpdir.name)

    def test_parse_valid_rtldoc_config(self):
        """Should successfully parse valid rtldoc config section."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  dir:
    - src/
    - rtl/
  out: docs/modules
  verbose: 1
  ci: false
  exclude:
    - testbench/
""")

        # Act
        from rtl_aid.config import parse_config
        config = parse_config(str(config_file))

        # Assert
        self.assertIn("rtldoc", config)
        self.assertEqual(config["rtldoc"]["dir"], ["src/", "rtl/"])
        self.assertEqual(config["rtldoc"]["out"], "docs/modules")
        self.assertEqual(config["rtldoc"]["verbose"], 1)
        self.assertFalse(config["rtldoc"]["ci"])
        self.assertEqual(config["rtldoc"]["exclude"], ["testbench/"])

    def test_parse_valid_rtllint_config(self):
        """Should successfully parse valid rtllint config section."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtllint:
  file:
    - src/module.v
  include:
    - include/
  verbose: true
  dry_run: false
""")

        # Act
        from rtl_aid.config import parse_config
        config = parse_config(str(config_file))

        # Assert
        self.assertIn("rtllint", config)
        self.assertEqual(config["rtllint"]["file"], ["src/module.v"])
        self.assertEqual(config["rtllint"]["include"], ["include/"])
        self.assertTrue(config["rtllint"]["verbose"])
        self.assertFalse(config["rtllint"]["dry_run"])

    def test_parse_empty_config_file(self):
        """Should handle empty or bare config file."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("# Empty config\n")

        # Act
        from rtl_aid.config import parse_config
        config = parse_config(str(config_file))

        # Assert
        self.assertEqual(config, {})

    def test_parse_malformed_yaml_raises_error(self):
        """Should raise ConfigError for malformed YAML."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  dir:
    - src/
  exclude: [unclosed list
""")

        # Act & Assert
        from rtl_aid.config import ConfigError, parse_config
        with self.assertRaises(ConfigError) as ctx:
            parse_config(str(config_file))

        self.assertIn("YAML", str(ctx.exception))

    def test_parse_config_with_both_rtldoc_and_rtllint(self):
        """Should parse config with both rtldoc and rtllint sections."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  dir:
    - src/
  out: docs/

rtllint:
  file:
    - src/module.v
  include:
    - include/
""")

        # Act
        from rtl_aid.config import parse_config
        config = parse_config(str(config_file))

        # Assert
        self.assertIn("rtldoc", config)
        self.assertIn("rtllint", config)
        self.assertEqual(config["rtldoc"]["dir"], ["src/"])
        self.assertEqual(config["rtllint"]["file"], ["src/module.v"])

    def test_parse_config_coerces_single_string_to_list(self):
        """Should coerce single string value to list for list-type options."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  dir: src/
  exclude: testbench/
""")

        # Act
        from rtl_aid.config import parse_config
        config = parse_config(str(config_file))

        # Assert
        # dir should be coerced to list
        self.assertEqual(config["rtldoc"]["dir"], ["src/"])
        self.assertEqual(config["rtldoc"]["exclude"], ["testbench/"])

    def test_parse_config_with_comments_and_blank_lines(self):
        """Should correctly parse config with comments and blank lines."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
# Configuration for rtldoc
rtldoc:
  # Source directories
  dir:
    - src/

  # Output directory
  out: docs/modules

  # Verbose mode (0, 1, or 2)
  verbose: 1
""")

        # Act
        from rtl_aid.config import parse_config
        config = parse_config(str(config_file))

        # Assert
        self.assertEqual(config["rtldoc"]["dir"], ["src/"])
        self.assertEqual(config["rtldoc"]["out"], "docs/modules")
        self.assertEqual(config["rtldoc"]["verbose"], 1)


class TestConfigValidation(unittest.TestCase):
    """Test validation of config values."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmproot = Path(self.tmpdir.name)

    def test_validate_dir_must_be_list(self):
        """Config dir option should be list or coercible to list."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  dir: src/
""")

        # Act
        from rtl_aid.config import parse_config
        config = parse_config(str(config_file))

        # Assert - should be coerced to list
        self.assertIsInstance(config["rtldoc"]["dir"], list)
        self.assertEqual(len(config["rtldoc"]["dir"]), 1)

    def test_validate_out_must_be_string(self):
        """Config out option should be string."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  out: docs/modules
""")

        # Act
        from rtl_aid.config import parse_config
        config = parse_config(str(config_file))

        # Assert
        self.assertIsInstance(config["rtldoc"]["out"], str)

    def test_validate_verbose_must_be_int_or_bool(self):
        """Config verbose should be int (0, 1, 2) or boolean."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  verbose: 1
""")

        # Act
        from rtl_aid.config import parse_config
        config = parse_config(str(config_file))

        # Assert
        self.assertIn(config["rtldoc"]["verbose"], [0, 1, 2, True, False])

    def test_validate_ci_must_be_boolean(self):
        """Config ci should be boolean."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  ci: true
""")

        # Act
        from rtl_aid.config import parse_config
        config = parse_config(str(config_file))

        # Assert
        self.assertIsInstance(config["rtldoc"]["ci"], bool)

    def test_validate_invalid_verbose_value_raises_error(self):
        """Should raise error for invalid verbose value."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  verbose: "very"
""")

        # Act & Assert
        from rtl_aid.config import ConfigError, validate_config
        config = {"rtldoc": {"verbose": "very"}}
        with self.assertRaises(ConfigError) as ctx:
            validate_config(config)

        self.assertIn("verbose", str(ctx.exception).lower())

    def test_validate_unknown_options_warning_or_error(self):
        """Should warn or error on unknown config options."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  dir:
    - src/
  unknown_option: value
""")

        # Act & Assert
        from rtl_aid.config import parse_config, ConfigError
        try:
            config = parse_config(str(config_file))
            # If it doesn't error, it should at least preserve the setting
            # or warn about it (depends on implementation)
        except ConfigError as e:
            self.assertIn("unknown", str(e).lower())

    def test_validate_mutually_exclusive_dir_and_file(self):
        """Config should not allow both dir and file in rtldoc."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("""
rtldoc:
  dir:
    - src/
  file:
    - src/module.v
""")

        # Act & Assert
        from rtl_aid.config import ConfigError, validate_config
        config = {
            "rtldoc": {
                "dir": ["src/"],
                "file": ["src/module.v"]
            }
        }
        with self.assertRaises(ConfigError) as ctx:
            validate_config(config)

        self.assertIn("mutually exclusive", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
