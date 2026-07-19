"""Tests for config file discovery (.rtl-aidrc.yml search)."""
import unittest
import tempfile
import os
from pathlib import Path


class TestConfigDiscovery(unittest.TestCase):
    """Test upward search for .rtl-aidrc.yml config file."""

    def setUp(self):
        """Create temporary directory structure for testing."""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmproot = Path(self.tmpdir.name)

    def test_find_config_in_current_directory(self):
        """Should find .rtl-aidrc.yml in current working directory."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("rtldoc:\n  dir:\n    - src/\n")

        # Act
        from rtl_aid.config import find_config_file
        found = find_config_file(start_dir=str(self.tmproot))

        # Assert
        self.assertEqual(found, str(config_file))

    def test_find_config_in_parent_directory(self):
        """Should find .rtl-aidrc.yml in parent directory by searching upward."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("rtldoc:\n  dir:\n    - src/\n")

        subdir = self.tmproot / "src" / "rtl"
        subdir.mkdir(parents=True)

        # Act
        from rtl_aid.config import find_config_file
        found = find_config_file(start_dir=str(subdir))

        # Assert
        self.assertEqual(found, str(config_file))

    def test_find_config_in_grandparent_directory(self):
        """Should find .rtl-aidrc.yml multiple levels up."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("rtldoc:\n  dir:\n    - src/\n")

        deepdir = self.tmproot / "a" / "b" / "c" / "d"
        deepdir.mkdir(parents=True)

        # Act
        from rtl_aid.config import find_config_file
        found = find_config_file(start_dir=str(deepdir))

        # Assert
        self.assertEqual(found, str(config_file))

    def test_no_config_file_returns_none(self):
        """Should return None if no config file found."""
        # Arrange
        subdir = self.tmproot / "src"
        subdir.mkdir()

        # Act
        from rtl_aid.config import find_config_file
        found = find_config_file(start_dir=str(subdir))

        # Assert
        self.assertIsNone(found)

    def test_stops_at_filesystem_root(self):
        """Should stop searching at filesystem root."""
        # Arrange
        subdir = self.tmproot / "src"
        subdir.mkdir()

        # Act
        from rtl_aid.config import find_config_file
        found = find_config_file(start_dir=str(subdir))

        # Assert
        self.assertIsNone(found)

    def test_prefers_nearest_config_in_search_path(self):
        """Should return the nearest (closest) config file in search path."""
        # Arrange
        root_config = self.tmproot / ".rtl-aidrc.yml"
        root_config.write_text("rtldoc:\n  dir:\n    - root/\n")

        mid_config = self.tmproot / "src" / ".rtl-aidrc.yml"
        mid_config.parent.mkdir(parents=True)
        mid_config.write_text("rtldoc:\n  dir:\n    - mid/\n")

        deepdir = self.tmproot / "src" / "rtl"
        deepdir.mkdir(parents=True)

        # Act
        from rtl_aid.config import find_config_file
        found = find_config_file(start_dir=str(deepdir))

        # Assert
        self.assertEqual(found, str(mid_config))

    def test_config_flag_overrides_search(self):
        """--config FILE flag should override upward search."""
        # Arrange
        root_config = self.tmproot / ".rtl-aidrc.yml"
        root_config.write_text("rtldoc:\n  dir:\n    - root/\n")

        explicit_config = self.tmproot / "custom.yml"
        explicit_config.write_text("rtldoc:\n  dir:\n    - custom/\n")

        # Act
        from rtl_aid.config import find_config_file
        found = find_config_file(start_dir=str(self.tmproot), config_flag=str(explicit_config))

        # Assert
        self.assertEqual(found, str(explicit_config))

    def test_config_flag_with_relative_path(self):
        """--config FILE should support relative paths."""
        # Arrange
        explicit_config = self.tmproot / "subdir" / "custom.yml"
        explicit_config.parent.mkdir(parents=True)
        explicit_config.write_text("rtldoc:\n  dir:\n    - custom/\n")

        # Change to tmproot, use relative path to config
        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))

            # Act
            from rtl_aid.config import find_config_file
            found = find_config_file(start_dir=str(self.tmproot), config_flag="subdir/custom.yml")

            # Assert
            # Should resolve relative to cwd
            self.assertTrue(os.path.isabs(found) or "subdir/custom.yml" in found)
        finally:
            os.chdir(original_cwd)

    def test_missing_config_file_with_flag_raises_error(self):
        """Should raise error if --config FILE points to nonexistent file."""
        # Arrange
        nonexistent = str(self.tmproot / "nonexistent.yml")

        # Act & Assert
        from rtl_aid.config import ConfigError, find_config_file
        with self.assertRaises(ConfigError) as ctx:
            find_config_file(start_dir=str(self.tmproot), config_flag=nonexistent)

        self.assertIn("not found", str(ctx.exception).lower())


class TestConfigFileDefaults(unittest.TestCase):
    """Test behavior when no config file exists (defaults)."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmproot = Path(self.tmpdir.name)

    def test_missing_config_uses_cli_defaults(self):
        """If no config file found, should use CLI argument defaults."""
        # Arrange - no config file created

        # Act
        from rtl_aid.config import find_config_file
        found = find_config_file(start_dir=str(self.tmproot))

        # Assert
        self.assertIsNone(found)


if __name__ == "__main__":
    unittest.main()
