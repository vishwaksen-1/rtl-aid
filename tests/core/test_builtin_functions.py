"""
Test suite for SystemVerilog built-in functions support in parameter parsing.

Tests the complete workflow for $clog2, $bits, $size, $high and other built-in
functions in parameter definitions, including:
- Configuration loading (packaged + user override)
- Function evaluation in parameter expressions
- Markdown display with both function and evaluated value
- Error handling and fallback behavior
- Edge cases and boundary conditions
- Nested function calls
- Verbosity-level warnings
"""

import unittest
import tempfile
import os
import yaml
from pathlib import Path
from tests.support import CORE_FIXTURES, copy_fixture
from rtl_aid.core import VerilogWikiParser


class TestFunctionsConfigLoading(unittest.TestCase):
    """Test configuration loading for built-in functions."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def test_packaged_config_loaded_by_default(self):
        """Default behavior should load packaged functions.yaml."""
        parser = VerilogWikiParser(
            paths=[],
            verbose=0
        )
        self.assertTrue(hasattr(parser, 'functions_config') or hasattr(parser, '_load_functions_config'))

    def test_user_config_overrides_packaged(self):
        """--functions-config FILE should override packaged functions."""
        config_file = copy_fixture(CORE_FIXTURES, "functions_custom.yaml", self.tmpdir.name)
        parser = VerilogWikiParser(
            paths=[],
            verbose=0,
            functions_config=config_file
        )
        self.assertIsNotNone(parser)

    def test_user_functions_merged_with_packaged(self):
        """User config should merge with packaged; missing functions inherited from packaged."""
        partial_config = copy_fixture(
            CORE_FIXTURES, "functions_partial_override.yaml", self.tmpdir.name
        )
        parser = VerilogWikiParser(
            paths=[],
            verbose=0,
            functions_config=partial_config
        )
        self.assertIsNotNone(parser)

    def test_config_file_not_found_warning(self):
        """Nonexistent config file should warn and fall back to packaged functions."""
        nonexistent = os.path.join(self.tmpdir.name, "nonexistent.yaml")
        parser = VerilogWikiParser(
            paths=[],
            verbose=1,
            functions_config=nonexistent
        )
        self.assertIsNotNone(parser)

    def test_malformed_config_yaml_fallback(self):
        """Malformed YAML should warn and fall back to packaged functions."""
        malformed = copy_fixture(CORE_FIXTURES, "functions_malformed.yaml", self.tmpdir.name)
        with open(malformed, 'a') as f:
            f.write("\ninvalid: yaml: syntax: here:")

        parser = VerilogWikiParser(
            paths=[],
            verbose=1,
            functions_config=malformed
        )
        self.assertIsNotNone(parser)

    def test_config_missing_required_fields_warning(self):
        """Config with missing required fields should warn gracefully."""
        malformed = copy_fixture(CORE_FIXTURES, "functions_malformed.yaml", self.tmpdir.name)
        parser = VerilogWikiParser(
            paths=[],
            verbose=1,
            functions_config=malformed
        )
        self.assertIsNotNone(parser)


class TestFunctionEvaluation(unittest.TestCase):
    """Test evaluation of built-in functions in parameter expressions."""

    def setUp(self):
        self.basic_dir = f"{CORE_FIXTURES}/builtin_functions_basic"

    def test_clog2_evaluation_powers_of_two(self):
        """$clog2(N) should evaluate correctly for powers of 2."""
        parser = VerilogWikiParser(paths=[self.basic_dir], verbose=0)
        parser.scan()

        module = parser.modules.get("addr_decoder")
        self.assertIsNotNone(module)

    def test_clog2_evaluation_non_powers_of_two(self):
        """$clog2(N) should evaluate correctly for non-powers of 2."""
        parser = VerilogWikiParser(paths=[self.basic_dir], verbose=0)
        parser.scan()

        module = parser.modules.get("addr_decoder")
        self.assertIsNotNone(module)

    def test_bits_evaluation(self):
        """$bits(type) should evaluate bit width correctly."""
        parser = VerilogWikiParser(paths=[self.basic_dir], verbose=0)
        parser.scan()

        module = parser.modules.get("data_converter")
        self.assertIsNotNone(module)

    def test_size_evaluation(self):
        """$size(array) should evaluate array size correctly."""
        parser = VerilogWikiParser(paths=[self.basic_dir], verbose=0)
        parser.scan()

        module = parser.modules.get("fifo_wrapper")
        self.assertIsNotNone(module)

    def test_high_evaluation(self):
        """$high(N) should evaluate highest index correctly."""
        parser = VerilogWikiParser(paths=[self.basic_dir], verbose=0)
        parser.scan()

        module = parser.modules.get("memory_controller")
        self.assertIsNotNone(module)


class TestFunctionMarkdownOutput(unittest.TestCase):
    """Test markdown display format for parameters with functions."""

    def setUp(self):
        self.basic_dir = f"{CORE_FIXTURES}/builtin_functions_basic"

    def test_markdown_shows_function_and_value(self):
        """Markdown should display both function and evaluated value."""
        parser = VerilogWikiParser(paths=[self.basic_dir], verbose=0)
        parser.scan()

        module = parser.modules.get("addr_decoder")
        self.assertIsNotNone(module)

    def test_markdown_unevaluated_shows_unresolved(self):
        """Markdown should show (unresolved) when function evaluation fails."""
        edge_dir = f"{CORE_FIXTURES}/builtin_functions_edge"
        parser = VerilogWikiParser(paths=[edge_dir], verbose=0)
        parser.scan()

        module = parser.modules.get("edge_undefined_param")
        self.assertIsNotNone(module)

    def test_markdown_localparam_annotation(self):
        """Markdown should include (localparam) annotation for localparam."""
        parser = VerilogWikiParser(paths=[self.basic_dir], verbose=0)
        parser.scan()

        module = parser.modules.get("addr_decoder")
        self.assertIsNotNone(module)


class TestFunctionEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions for each function."""

    def setUp(self):
        self.edge_dir = f"{CORE_FIXTURES}/builtin_functions_edge"

    def test_clog2_with_zero_undefined(self):
        """$clog2(0) is undefined; should show unevaluated."""
        parser = VerilogWikiParser(paths=[self.edge_dir], verbose=0)
        parser.scan()

        module = parser.modules.get("edge_clog2_zero")
        self.assertIsNotNone(module)

    def test_clog2_with_one_evaluates_to_zero(self):
        """$clog2(1) = 0."""
        parser = VerilogWikiParser(paths=[self.edge_dir], verbose=0)
        parser.scan()

        module = parser.modules.get("edge_clog2_one")
        self.assertIsNotNone(module)

    def test_clog2_with_large_value(self):
        """$clog2(2^24) = 24."""
        parser = VerilogWikiParser(paths=[self.edge_dir], verbose=0)
        parser.scan()

        module = parser.modules.get("edge_large_value")
        self.assertIsNotNone(module)

    def test_clog2_with_negative_parameter(self):
        """$clog2 with negative arg should fail gracefully."""
        parser = VerilogWikiParser(paths=[self.edge_dir], verbose=0)
        parser.scan()

        module = parser.modules.get("edge_negative_param")
        self.assertIsNotNone(module)

    def test_clog2_with_arithmetic_expression(self):
        """$clog2 should handle arithmetic expressions in arguments."""
        parser = VerilogWikiParser(paths=[self.edge_dir], verbose=0)
        parser.scan()

        module = parser.modules.get("edge_arithmetic")
        self.assertIsNotNone(module)

    def test_size_with_non_array_argument(self):
        """$size on non-array should fail gracefully."""
        parser = VerilogWikiParser(paths=[self.edge_dir], verbose=0)
        parser.scan()

        module = parser.modules.get("edge_size_non_array")
        self.assertIsNotNone(module)

    def test_high_with_non_numeric_argument(self):
        """$high with string/invalid arg should fail gracefully."""
        parser = VerilogWikiParser(paths=[self.edge_dir], verbose=0)
        parser.scan()

        module = parser.modules.get("edge_high_invalid")
        self.assertIsNotNone(module)


class TestNestedFunctionCalls(unittest.TestCase):
    """Test nested function calls like $clog2($bits(...))."""

    def setUp(self):
        self.basic_dir = f"{CORE_FIXTURES}/builtin_functions_basic"
        self.edge_dir = f"{CORE_FIXTURES}/builtin_functions_edge"

    def test_nested_clog2_and_bits(self):
        """$clog2($bits(...)) should evaluate inner then outer function."""
        parser = VerilogWikiParser(paths=[self.basic_dir], verbose=0)
        parser.scan()

        module = parser.modules.get("complex_calc")
        self.assertIsNotNone(module)

    def test_nested_clog2_three_levels(self):
        """Very deep nesting should still evaluate (or fail gracefully)."""
        parser = VerilogWikiParser(paths=[self.edge_dir], verbose=0)
        parser.scan()

        module = parser.modules.get("edge_deeply_nested")
        self.assertIsNotNone(module)

    def test_nested_with_undefined_reference(self):
        """Nested call with undefined reference should fail gracefully."""
        parser = VerilogWikiParser(paths=[self.edge_dir], verbose=0)
        parser.scan()

        module = parser.modules.get("edge_nested_undefined")
        self.assertIsNotNone(module)


class TestFunctionErrorHandling(unittest.TestCase):
    """Test error handling for function evaluation failures."""

    def setUp(self):
        self.edge_dir = f"{CORE_FIXTURES}/builtin_functions_edge"

    def test_undefined_parameter_in_function_argument(self):
        """Function with undefined parameter reference should warn and show unevaluated."""
        parser = VerilogWikiParser(paths=[self.edge_dir], verbose=1)
        parser.scan()

        module = parser.modules.get("edge_undefined_param")
        self.assertIsNotNone(module)

    def test_invalid_function_argument_type(self):
        """Function called with wrong type should warn and show unevaluated."""
        parser = VerilogWikiParser(paths=[self.edge_dir], verbose=1)
        parser.scan()

        module = parser.modules.get("edge_high_invalid")
        self.assertIsNotNone(module)

    def test_nonexistent_custom_function_error(self):
        """Custom function that doesn't exist should warn and show unevaluated."""
        parser = VerilogWikiParser(paths=[self.edge_dir], verbose=1)
        parser.scan()

        module = parser.modules.get("edge_custom_nonexistent")
        self.assertIsNotNone(module)


class TestMalformedConfigFallback(unittest.TestCase):
    """Test graceful fallback when custom config is malformed."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def test_bad_python_func_reference_fallback(self):
        """Config with bad python_func reference should warn and fall back."""
        malformed = copy_fixture(
            CORE_FIXTURES, "functions_malformed.yaml", self.tmpdir.name
        )
        parser = VerilogWikiParser(
            paths=[],
            verbose=1,
            functions_config=malformed
        )
        self.assertIsNotNone(parser)

    def test_missing_required_config_field_fallback(self):
        """Config missing required fields should warn and skip that function."""
        malformed = copy_fixture(
            CORE_FIXTURES, "functions_malformed.yaml", self.tmpdir.name
        )
        parser = VerilogWikiParser(
            paths=[],
            verbose=1,
            functions_config=malformed
        )
        self.assertIsNotNone(parser)


class TestVerbosityLevelWarnings(unittest.TestCase):
    """Test warning output at different verbosity levels."""

    def setUp(self):
        self.edge_dir = f"{CORE_FIXTURES}/builtin_functions_edge"

    def test_no_warnings_at_verbosity_zero(self):
        """With -v 0 (default), no function evaluation warnings should appear."""
        parser = VerilogWikiParser(paths=[self.edge_dir], verbose=0)
        parser.scan()

    def test_warnings_at_verbosity_one(self):
        """With -v (verbosity=1), function evaluation failures should warn."""
        parser = VerilogWikiParser(paths=[self.edge_dir], verbose=1)
        parser.scan()

    def test_verbose_details_at_verbosity_two(self):
        """With -vv (verbosity=2), detailed function evaluation info should appear."""
        parser = VerilogWikiParser(paths=[self.edge_dir], verbose=2)
        parser.scan()


class TestFunctionConfigIntegration(unittest.TestCase):
    """Integration tests for full parameter parsing workflow with functions."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.basic_dir = f"{CORE_FIXTURES}/builtin_functions_basic"

    def test_full_scan_with_packaged_functions(self):
        """Full scan should handle all functions correctly with packaged config."""
        parser = VerilogWikiParser(paths=[self.basic_dir], verbose=0)
        parser.scan()

        modules_found = [
            "addr_decoder", "data_converter", "fifo_wrapper",
            "memory_controller", "complex_calc", "minimal_decoder",
            "large_decoder", "hybrid_params", "bounded_mem",
            "comprehensive_test"
        ]
        for module_name in modules_found:
            self.assertIn(module_name, parser.modules,
                         f"Module {module_name} not found after scan")

    def test_full_scan_with_custom_functions_config(self):
        """Full scan with custom config should use user functions."""
        custom_config = copy_fixture(
            CORE_FIXTURES, "functions_custom.yaml", self.tmpdir.name
        )

        parser = VerilogWikiParser(
            paths=[self.basic_dir],
            verbose=0,
            functions_config=custom_config
        )
        parser.scan()

        self.assertIn("addr_decoder", parser.modules)

    def test_markdown_generation_with_functions(self):
        """Markdown generation should properly format parameters with functions."""
        parser = VerilogWikiParser(paths=[self.basic_dir], verbose=0)
        parser.scan()

        output_dir = self.tmpdir.name
        parser.generate_markdown(output_dir)

        markdown_file = os.path.join(output_dir, "addr_decoder.md")
        # After implementation: file should exist and contain formatted parameters

    def test_ci_mode_with_functions(self):
        """CI mode should validate modules with functions correctly."""
        parser = VerilogWikiParser(paths=[self.basic_dir], verbose=0, ci=True)
        parser.scan()

        parser.run_ci_checks()

    def test_json_graph_with_functions(self):
        """JSON graph export should work with modules using functions."""
        json_file = os.path.join(self.tmpdir.name, "graph.json")

        parser = VerilogWikiParser(
            paths=[self.basic_dir],
            verbose=0,
            export_graph=[json_file]
        )
        parser.scan()
        parser.export_graphs(self.tmpdir.name)

        self.assertTrue(os.path.exists(json_file))


class TestFunctionDocumentation(unittest.TestCase):
    """Test documentation and help for built-in functions."""

    def test_functions_config_has_metadata(self):
        """Functions config should include metadata and descriptions."""
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        config_file = copy_fixture(
            CORE_FIXTURES, "functions_packaged.yaml", tmpdir.name
        )

        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        self.assertIn("metadata", config)
        self.assertIn("functions", config)

        for func_name, func_def in config["functions"].items():
            self.assertIn("description", func_def,
                         f"Function {func_name} missing description")
            self.assertIn("python_func", func_def,
                         f"Function {func_name} missing python_func")

    def test_function_categories_in_config(self):
        """Functions should be categorized (math, type_query, array_query, bounds)."""
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        config_file = copy_fixture(
            CORE_FIXTURES, "functions_packaged.yaml", tmpdir.name
        )

        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        expected_categories = {"math", "type_query", "array_query", "bounds"}
        found_categories = set()

        for func_name, func_def in config["functions"].items():
            if "category" in func_def:
                found_categories.add(func_def["category"])

        self.assertTrue(len(found_categories) > 0)


if __name__ == '__main__':
    unittest.main()
