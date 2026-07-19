"""Tests for functions_config integration with config files and CLI."""
import unittest
import tempfile
import os
from pathlib import Path
from rtl_aid.config import load_config_for_rtldoc
from rtl_aid.core import VerilogWikiParser


class TestFunctionsConfigInTemplate(unittest.TestCase):
    """Verify functions_config is documented in template."""

    def test_template_includes_functions_config_option(self):
        """Template should include commented functions_config option."""
        from rtl_aid.functions import PACKAGED_FUNCTIONS_PATH
        template_path = PACKAGED_FUNCTIONS_PATH.parent.parent / "templates" / "rtl-aidrc-template.yml"

        self.assertTrue(template_path.exists(), f"Template not found: {template_path}")

        with open(template_path) as f:
            content = f.read()

        self.assertIn("functions_config", content, "Template should mention functions_config")
        self.assertIn("# functions_config:", content, "functions_config should be commented out in template")


class TestFunctionsConfigLoading(unittest.TestCase):
    """Test loading functions_config from config file."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmproot = Path(self.tmpdir.name)

    def _create_test_verilog(self):
        """Create sample Verilog file."""
        src_dir = self.tmproot / "src"
        src_dir.mkdir()
        (src_dir / "test.v").write_text("""
module test_mod (
    input clk
);
    parameter DEPTH = $clog2(256);
endmodule
""")

    def _create_config_file(self, config_content):
        """Helper to create test config file."""
        config_file = self.tmproot / ".rtl-aidrc.yml"
        config_file.write_text(config_content)
        return config_file

    def _create_custom_functions(self, functions_content):
        """Helper to create custom functions config file."""
        config_dir = self.tmproot / "config"
        config_dir.mkdir(exist_ok=True)
        functions_file = config_dir / "custom-functions.yaml"
        functions_file.write_text(functions_content)
        return functions_file

    def test_config_file_with_functions_config_option(self):
        """Config file should support functions_config option."""
        self._create_test_verilog()
        custom_funcs = self._create_custom_functions("""
functions:
  $clog2:
    python_func: "math.ceil(math.log2(max(1, x)))"
    library: "math"
""")

        self._create_config_file(f"""
rtldoc:
  dir:
    - src/
  out: docs/
  functions_config: config/custom-functions.yaml
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))
            config = load_config_for_rtldoc()

            # Should load functions_config from config file
            self.assertIn("functions_config", config)
            self.assertEqual(config["functions_config"], "config/custom-functions.yaml")
        finally:
            os.chdir(original_cwd)

    def test_functions_config_passed_to_parser(self):
        """VerilogWikiParser should accept functions_config from config."""
        self._create_test_verilog()
        custom_funcs = self._create_custom_functions("""
functions:
  $clog2:
    python_func: "math.ceil(math.log2(max(1, x)))"
    library: "math"
""")

        # Create parser with custom functions config
        parser = VerilogWikiParser(
            paths=[str(self.tmproot / "src" / "test.v")],
            verbose=0,
            functions_config=str(custom_funcs)
        )

        self.assertIsNotNone(parser)
        # Parser should have loaded the functions config
        self.assertEqual(parser.functions_config, str(custom_funcs))

    def test_functions_config_is_optional(self):
        """functions_config should be optional; default packaged config used if omitted."""
        self._create_test_verilog()

        self._create_config_file("""
rtldoc:
  dir:
    - src/
  out: docs/
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.tmproot))
            config = load_config_for_rtldoc()

            # functions_config should not be in config if not specified
            self.assertNotIn("functions_config", config)
        finally:
            os.chdir(original_cwd)

    def test_parser_uses_custom_functions_config(self):
        """Parser should use custom functions config when provided."""
        self._create_test_verilog()

        # Create custom functions file with additional function
        custom_funcs = self._create_custom_functions("""
functions:
  $clog2:
    python_func: "math.ceil(math.log2(max(1, x)))"
    library: "math"
  $custom_func:
    python_func: "42"
    library: "builtin"
""")

        parser = VerilogWikiParser(
            paths=[str(self.tmproot / "src" / "test.v")],
            verbose=0,
            functions_config=str(custom_funcs)
        )

        # Load functions config
        parser.scan()
        loaded_config = parser._load_functions_config()

        # Should have both packaged and custom functions
        self.assertIn("$clog2", loaded_config)
        self.assertIn("$custom_func", loaded_config)


if __name__ == "__main__":
    unittest.main()
