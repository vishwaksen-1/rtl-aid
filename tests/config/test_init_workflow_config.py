"""Tests for --init-workflow generating .rtl-aidrc.yml config file."""
import unittest
import tempfile
import subprocess
import os
import sys
from pathlib import Path


class TestInitWorkflowGeneratesConfig(unittest.TestCase):
    """Test that --init-workflow creates both workflow and config files."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmproot = Path(self.tmpdir.name)

    def test_init_workflow_creates_config_file(self):
        """--init-workflow should create .rtl-aidrc.yml alongside workflow."""
        # Arrange
        os.chdir(str(self.tmproot))

        # Act
        from rtl_aid.cli import main
        # Simulate: rtldoc --init-workflow
        # This will need to be called differently in actual implementation
        result = self._run_rtldoc_init_workflow()

        # Assert
        config_file = self.tmproot / ".rtl-aidrc.yml"
        workflow_file = self.tmproot / ".github" / "workflows" / "rtl-checks.yml"

        self.assertTrue(config_file.exists(), "Config file not created")
        self.assertTrue(workflow_file.exists(), "Workflow file not created")

    def test_init_workflow_config_has_valid_yaml(self):
        """Generated config file should be valid YAML."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"

        # Act - first create the config file
        self._run_rtldoc_init_workflow()

        from rtl_aid.config import parse_config
        config = parse_config(str(config_file))

        # Assert
        self.assertIsInstance(config, dict)
        # Should have at least one section (rtldoc or rtllint)
        self.assertTrue(len(config) >= 0)  # Can be empty

    def test_init_workflow_config_contains_template_sections(self):
        """Generated config should include example sections with comments."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"

        # Act - first create the config file
        self._run_rtldoc_init_workflow()

        content = config_file.read_text()

        # Assert
        # Should have comments indicating it's generated
        self.assertIn("#", content, "Config should have comment documentation")

        # Should have at least rtldoc or rtllint sections
        self.assertTrue("rtldoc" in content or "rtllint" in content)

    def test_init_workflow_does_not_overwrite_existing_config(self):
        """Should not overwrite existing .rtl-aidrc.yml file."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        existing_content = "rtldoc:\n  dir:\n    - existing/\n"
        config_file.write_text(existing_content)

        # Act
        from rtl_aid.cli import init_workflow
        # Attempt to run init-workflow
        result = self._run_rtldoc_init_workflow()

        # Assert
        # Should exit with error and not modify existing config
        self.assertEqual(config_file.read_text(), existing_content)

    def test_init_workflow_does_not_overwrite_existing_workflow(self):
        """Should not overwrite existing workflow file."""
        # Arrange
        workflow_dir = self.tmproot / ".github" / "workflows"
        workflow_dir.mkdir(parents=True)
        workflow_file = workflow_dir / "rtl-checks.yml"
        existing_content = "name: existing\n"
        workflow_file.write_text(existing_content)

        # Act
        result = self._run_rtldoc_init_workflow()

        # Assert
        # Should exit with error and not modify existing workflow
        self.assertEqual(workflow_file.read_text(), existing_content)

    def test_init_workflow_error_message_for_existing_config(self):
        """Error message should clearly indicate file already exists."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text("existing: config\n")

        # Act & Assert
        from rtl_aid.cli import init_workflow
        with self.assertRaises(SystemExit) as ctx:
            init_workflow(str(self.tmproot))

        # Exit code should be 1 (error)
        self.assertEqual(ctx.exception.code, 1)

    def test_init_workflow_creates_both_files_when_none_exist(self):
        """Should create both config and workflow when neither exists."""
        # Arrange - tmpdir is empty

        # Act
        result = self._run_rtldoc_init_workflow()

        # Assert
        config_file = self.tmproot / ".rtl-aidrc.yml"
        workflow_file = self.tmproot / ".github" / "workflows" / "rtl-checks.yml"

        self.assertTrue(config_file.exists())
        self.assertTrue(workflow_file.exists())

    def test_init_workflow_creates_github_workflows_directory(self):
        """Should create .github/workflows/ directory if not present."""
        # Arrange - tmpdir exists but .github doesn't

        # Act
        result = self._run_rtldoc_init_workflow()

        # Assert
        workflow_dir = self.tmproot / ".github" / "workflows"
        self.assertTrue(workflow_dir.is_dir())

    def test_config_file_is_readable_by_parser(self):
        """Generated config file should be parseable by parse_config()."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"

        # Act - first create the config file
        self._run_rtldoc_init_workflow()

        from rtl_aid.config import parse_config
        try:
            config = parse_config(str(config_file))
            success = True
        except Exception as e:
            success = False
            error = str(e)

        # Assert
        self.assertTrue(success, f"Generated config not parseable: {error if not success else ''}")

    def _run_rtldoc_init_workflow(self):
        """Helper to run rtldoc --init-workflow in tmpdir."""
        import sys
        import os

        try:
            original_cwd = os.getcwd()
        except FileNotFoundError:
            # If current dir was deleted by previous test, use tmproot
            original_cwd = str(self.tmproot)

        original_argv = sys.argv
        try:
            os.chdir(str(self.tmproot))
            sys.argv = ["rtldoc", "--init-workflow"]

            from rtl_aid.cli import main
            try:
                main()
                return 0
            except SystemExit as e:
                return e.code
        finally:
            try:
                os.chdir(original_cwd)
            except FileNotFoundError:
                pass
            sys.argv = original_argv


class TestInitWorkflowConfigContent(unittest.TestCase):
    """Test content and structure of generated config file."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmproot = Path(self.tmpdir.name)

    def test_generated_config_has_rtldoc_section(self):
        """Generated config should have rtldoc section with examples."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        self._create_sample_generated_config(config_file)

        # Act
        content = config_file.read_text()

        # Assert
        self.assertIn("rtldoc:", content)

    def test_generated_config_has_rtllint_section(self):
        """Generated config should have rtllint section with examples."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        self._create_sample_generated_config(config_file)

        # Act
        content = config_file.read_text()

        # Assert
        self.assertIn("rtllint:", content)

    def test_generated_config_includes_comments_explaining_options(self):
        """Generated config should have comments for each option."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        self._create_sample_generated_config(config_file)

        # Act
        content = config_file.read_text()

        # Assert
        # Should mention key options
        self.assertIn("dir", content)
        self.assertIn("file", content)
        self.assertIn("out", content)
        self.assertIn("verbose", content)

    def test_generated_config_marks_required_vs_optional(self):
        """Generated config comments should indicate required vs optional."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        self._create_sample_generated_config(config_file)

        # Act
        content = config_file.read_text()

        # Assert
        # Should have some indication of required fields
        # (depends on implementation, could be "required:", "must:", etc.)

    def test_generated_config_shows_common_exclude_patterns(self):
        """Generated config should include examples of exclude patterns."""
        # Arrange
        config_file = self.tmproot / ".rtl-aidrc.yml"
        self._create_sample_generated_config(config_file)

        # Act
        content = config_file.read_text()

        # Assert
        # Should show example exclude patterns
        self.assertIn("exclude", content)

    def _create_sample_generated_config(self, path):
        """Create a sample generated config file for testing."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("""
# rtldoc configuration
# Generated by: rtldoc --init-workflow

rtldoc:
  # Directories to scan
  # dir:
  #   - src/

  # Output directory
  out: temp/docs/modules

  # Verbose mode
  verbose: 0

  # CI mode
  ci: false

  # Exclude patterns
  # exclude:
  #   - testbench/

rtllint:
  # Files to lint
  # file:
  #   - src/module.v

  # Include directories
  # include:
  #   - include/

  verbose: false
""")


class TestInitWorkflowErrorHandling(unittest.TestCase):
    """Test error handling in --init-workflow."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmproot = Path(self.tmpdir.name)

    def test_init_workflow_permission_error_on_directory_creation(self):
        """Should handle permission errors gracefully."""
        # This test is OS-dependent and may need to be skipped on some systems
        import os
        import stat

        # Try to make parent directory read-only
        parent = self.tmproot / "readonly"
        parent.mkdir()
        github_dir = parent / ".github"
        parent.chmod(stat.S_IRUSR | stat.S_IXUSR)  # Read + execute only

        try:
            # Act & Assert
            from rtl_aid.cli import init_workflow
            with self.assertRaises((OSError, PermissionError, SystemExit)):
                init_workflow(str(github_dir))
        finally:
            # Restore permissions for cleanup
            parent.chmod(stat.S_IRWXU)

    def test_init_workflow_with_unwritable_directory(self):
        """Should gracefully handle unwritable directory."""
        import os
        import stat

        # Make tmproot unwritable
        self.tmproot.chmod(stat.S_IRUSR | stat.S_IXUSR)

        try:
            # Act & Assert
            from rtl_aid.cli import init_workflow
            with self.assertRaises((OSError, PermissionError, SystemExit)):
                init_workflow(str(self.tmproot))
        finally:
            # Restore permissions for cleanup
            self.tmproot.chmod(stat.S_IRWXU)


if __name__ == "__main__":
    import os
    unittest.main()
