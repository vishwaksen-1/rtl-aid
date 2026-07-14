"""
Test suite for rtldoc --json-graph-dir feature.

Tests that:
1. When --json-graph flag is used without --json-graph-dir, graph.json is written to output dir
2. When --json-graph flag is used WITH --json-graph-dir, graph.json is written to DIR instead
3. --json-graph-dir only has effect when --json-graph is also provided
4. Non-existent directories are created automatically
5. In dry-run mode, directory is identified correctly but file not written
"""
import os
import json
import tempfile
import unittest
from rtl_aid.core import VerilogWikiParser


class JsonGraphDirTestCase(unittest.TestCase):
    """Base test case for JSON graph directory feature."""

    def setUp(self):
        """Set up temporary directories for testing."""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.out_dir = os.path.join(self.tmpdir.name, "output")
        os.makedirs(self.out_dir)
        self.addCleanup(self.tmpdir.cleanup)

    def _make_parser(self, json_graph=False, json_graph_dir=None, dry_run=False):
        """Create a VerilogWikiParser with test parameters."""
        parser = VerilogWikiParser(
            paths=[],  # No scanning needed for these tests
            verbose=0,
            ci=False,
            json_graph=json_graph,
            json_graph_dir=json_graph_dir,
            print_errors=False,
            exclude=None,
            dry_run=dry_run,
        )
        # Add a test module to the parser
        parser.modules = {
            "top_module": {
                "calls": ["sub_module1", "sub_module2"],
                "inputs": ["clk"],
                "outputs": ["data"],
            },
            "sub_module1": {
                "calls": [],
                "inputs": ["clk"],
                "outputs": ["valid"],
            },
            "sub_module2": {
                "calls": [],
                "inputs": ["clk"],
                "outputs": ["ready"],
            },
        }
        parser.called_by = {
            "sub_module1": ["top_module"],
            "sub_module2": ["top_module"],
        }
        return parser

    def _graph_exists(self, directory):
        """Check if graph.json exists in the given directory."""
        return os.path.isfile(os.path.join(directory, "graph.json"))

    def _read_graph(self, directory):
        """Read and parse graph.json from the given directory."""
        path = os.path.join(directory, "graph.json")
        if not os.path.isfile(path):
            return None
        with open(path) as f:
            return json.load(f)


class TestJsonGraphDefaultBehavior(JsonGraphDirTestCase):
    """Tests for default behavior (no --json-graph-dir specified)."""

    def test_json_graph_false_no_file_written(self):
        """When --json-graph is false, no graph.json should be written."""
        parser = self._make_parser(json_graph=False)
        parser.write_json(self.out_dir)

        # No graph.json should exist anywhere
        self.assertFalse(self._graph_exists(self.out_dir))

    def test_json_graph_true_writes_to_output_dir(self):
        """When --json-graph is true without --json-graph-dir, write to output dir."""
        parser = self._make_parser(json_graph=True)
        parser.write_json(self.out_dir)

        # graph.json should exist in output directory
        self.assertTrue(self._graph_exists(self.out_dir))

    def test_json_graph_contains_module_data(self):
        """Graph.json should contain the module dependency data."""
        parser = self._make_parser(json_graph=True)
        parser.write_json(self.out_dir)

        graph = self._read_graph(self.out_dir)
        self.assertIsNotNone(graph)

        # Check structure
        self.assertIn("top_module", graph)
        self.assertIn("sub_module1", graph)
        self.assertIn("sub_module2", graph)

        # Check top_module data
        self.assertEqual(graph["top_module"]["calls"], ["sub_module1", "sub_module2"])
        self.assertEqual(graph["top_module"]["called_by"], [])

        # Check sub_module1 data
        self.assertEqual(graph["sub_module1"]["calls"], [])
        self.assertEqual(graph["sub_module1"]["called_by"], ["top_module"])

    def test_json_graph_json_graph_dir_none_uses_output_dir(self):
        """When json_graph_dir is None, output dir should be used."""
        parser = self._make_parser(json_graph=True, json_graph_dir=None)
        parser.write_json(self.out_dir)

        # Should write to output directory
        self.assertTrue(self._graph_exists(self.out_dir))


class TestJsonGraphDirParameter(JsonGraphDirTestCase):
    """Tests for --json-graph-dir parameter."""

    def test_json_graph_dir_no_effect_without_json_graph_flag(self):
        """--json-graph-dir should have no effect if --json-graph is false."""
        custom_dir = os.path.join(self.tmpdir.name, "custom")
        parser = self._make_parser(json_graph=False, json_graph_dir=custom_dir)
        parser.write_json(self.out_dir)

        # No file should be written anywhere
        self.assertFalse(self._graph_exists(self.out_dir))
        self.assertFalse(self._graph_exists(custom_dir))

    def test_json_graph_dir_with_json_graph_writes_to_custom_dir(self):
        """When both flags set, write graph.json to custom directory."""
        custom_dir = os.path.join(self.tmpdir.name, "custom_graphs")
        os.makedirs(custom_dir)

        parser = self._make_parser(json_graph=True, json_graph_dir=custom_dir)
        parser.write_json(self.out_dir)

        # Should write to custom directory
        self.assertTrue(self._graph_exists(custom_dir))
        # Should NOT write to output directory
        self.assertFalse(self._graph_exists(self.out_dir))

    def test_json_graph_dir_not_output_dir_writes_only_to_custom(self):
        """graph.json should only be in --json-graph-dir, not output dir."""
        custom_dir = os.path.join(self.tmpdir.name, "my_graphs")
        os.makedirs(custom_dir)

        parser = self._make_parser(json_graph=True, json_graph_dir=custom_dir)
        parser.write_json(self.out_dir)

        # Custom dir has the file
        self.assertTrue(self._graph_exists(custom_dir))
        # Output dir does not
        self.assertFalse(self._graph_exists(self.out_dir))

    def test_json_graph_dir_creates_directory_if_not_exists(self):
        """--json-graph-dir should create directory if it doesn't exist."""
        new_dir = os.path.join(self.tmpdir.name, "does", "not", "exist", "yet")
        self.assertFalse(os.path.exists(new_dir))

        parser = self._make_parser(json_graph=True, json_graph_dir=new_dir)
        parser.write_json(self.out_dir)

        # Directory should be created
        self.assertTrue(os.path.isdir(new_dir))
        # And graph.json should be written there
        self.assertTrue(self._graph_exists(new_dir))

    def test_json_graph_dir_creates_nested_directories(self):
        """--json-graph-dir should create multiple nested directories."""
        nested_dir = os.path.join(self.tmpdir.name, "level1", "level2", "level3")
        self.assertFalse(os.path.exists(nested_dir))

        parser = self._make_parser(json_graph=True, json_graph_dir=nested_dir)
        parser.write_json(self.out_dir)

        # All directories should be created
        self.assertTrue(os.path.isdir(nested_dir))
        self.assertTrue(self._graph_exists(nested_dir))

    def test_json_graph_dir_with_existing_directory(self):
        """--json-graph-dir should work with already-existing directory."""
        custom_dir = os.path.join(self.tmpdir.name, "existing")
        os.makedirs(custom_dir)

        parser = self._make_parser(json_graph=True, json_graph_dir=custom_dir)
        parser.write_json(self.out_dir)

        # Should write to existing directory without error
        self.assertTrue(self._graph_exists(custom_dir))

    def test_json_graph_dir_overwrites_existing_graph_json(self):
        """Calling write_json multiple times should overwrite graph.json."""
        custom_dir = os.path.join(self.tmpdir.name, "graphs")
        os.makedirs(custom_dir)

        # First write
        parser1 = self._make_parser(json_graph=True, json_graph_dir=custom_dir)
        parser1.write_json(self.out_dir)

        # Modify the parser's modules
        parser1.modules["new_module"] = {
            "calls": [],
            "inputs": [],
            "outputs": [],
        }

        # Second write
        parser1.write_json(self.out_dir)

        # Should have the new module
        graph = self._read_graph(custom_dir)
        self.assertIn("new_module", graph)


class TestJsonGraphDryRun(JsonGraphDirTestCase):
    """Tests for dry-run mode behavior."""

    def test_dry_run_with_json_graph_no_file_written(self):
        """In dry-run mode, graph.json should not be written."""
        parser = self._make_parser(json_graph=True, dry_run=True)
        parser.write_json(self.out_dir)

        # No file should be written
        self.assertFalse(self._graph_exists(self.out_dir))

    def test_dry_run_with_json_graph_dir_no_file_written(self):
        """In dry-run with --json-graph-dir, file should not be written."""
        custom_dir = os.path.join(self.tmpdir.name, "graphs")

        parser = self._make_parser(
            json_graph=True,
            json_graph_dir=custom_dir,
            dry_run=True,
        )
        parser.write_json(self.out_dir)

        # File should not be written
        self.assertFalse(self._graph_exists(custom_dir))

    def test_dry_run_with_json_graph_dir_identifies_directory(self):
        """In dry-run mode, --json-graph-dir should be identified correctly."""
        custom_dir = os.path.join(self.tmpdir.name, "graphs")
        self.assertFalse(os.path.exists(custom_dir))

        parser = self._make_parser(
            json_graph=True,
            json_graph_dir=custom_dir,
            dry_run=True,
        )
        parser.write_json(self.out_dir)

        # In dry-run mode, directory should not be created and file should not be written
        self.assertFalse(os.path.exists(custom_dir))
        self.assertFalse(self._graph_exists(custom_dir))

    def test_dry_run_false_writes_file(self):
        """When dry_run is false, file should be written."""
        parser = self._make_parser(json_graph=True, dry_run=False)
        parser.write_json(self.out_dir)

        # File should be written
        self.assertTrue(self._graph_exists(self.out_dir))


class TestJsonGraphDirEdgeCases(JsonGraphDirTestCase):
    """Edge cases and special scenarios."""

    def test_json_graph_dir_same_as_output_dir(self):
        """When --json-graph-dir equals output dir, should work correctly."""
        parser = self._make_parser(json_graph=True, json_graph_dir=self.out_dir)
        parser.write_json(self.out_dir)

        # Should write to the directory
        self.assertTrue(self._graph_exists(self.out_dir))

    def test_json_graph_dir_with_relative_path(self):
        """--json-graph-dir with relative path should work."""
        # Create a subdirectory and use relative path
        rel_dir = os.path.join(self.tmpdir.name, "relative")
        os.makedirs(rel_dir)

        parser = self._make_parser(json_graph=True, json_graph_dir=rel_dir)
        parser.write_json(self.out_dir)

        # Should write correctly
        self.assertTrue(self._graph_exists(rel_dir))

    def test_json_graph_dir_with_trailing_slash(self):
        """--json-graph-dir with trailing slash should work."""
        custom_dir = os.path.join(self.tmpdir.name, "graphs") + "/"
        # Clean up the trailing slash for os.makedirs
        clean_dir = custom_dir.rstrip("/")
        os.makedirs(clean_dir)

        parser = self._make_parser(json_graph=True, json_graph_dir=custom_dir)
        parser.write_json(self.out_dir)

        # Should write correctly despite trailing slash
        self.assertTrue(self._graph_exists(clean_dir))

    def test_empty_modules_generates_empty_graph(self):
        """Parser with no modules should generate empty graph."""
        parser = self._make_parser(json_graph=True)
        parser.modules = {}
        parser.called_by = {}
        parser.write_json(self.out_dir)

        graph = self._read_graph(self.out_dir)
        self.assertEqual(graph, {})

    def test_json_graph_is_valid_json(self):
        """Generated graph.json should be valid JSON."""
        custom_dir = os.path.join(self.tmpdir.name, "graphs")
        os.makedirs(custom_dir)

        parser = self._make_parser(json_graph=True, json_graph_dir=custom_dir)
        parser.write_json(self.out_dir)

        # Should be readable and valid JSON
        graph = self._read_graph(custom_dir)
        self.assertIsInstance(graph, dict)

    def test_json_graph_dir_absolute_path(self):
        """--json-graph-dir with absolute path should work."""
        abs_dir = os.path.abspath(os.path.join(self.tmpdir.name, "absolute"))
        os.makedirs(abs_dir)

        parser = self._make_parser(json_graph=True, json_graph_dir=abs_dir)
        parser.write_json(self.out_dir)

        # Should write correctly with absolute path
        self.assertTrue(self._graph_exists(abs_dir))

    def test_multiple_write_json_calls_same_dir(self):
        """Multiple calls to write_json with same directory should work."""
        custom_dir = os.path.join(self.tmpdir.name, "graphs")
        os.makedirs(custom_dir)

        parser = self._make_parser(json_graph=True, json_graph_dir=custom_dir)

        # Call write_json multiple times
        parser.write_json(self.out_dir)
        parser.write_json(self.out_dir)
        parser.write_json(self.out_dir)

        # Should still have exactly one graph.json
        self.assertTrue(self._graph_exists(custom_dir))

    def test_json_graph_preserves_module_structure(self):
        """Graph should preserve all module structure information."""
        custom_dir = os.path.join(self.tmpdir.name, "graphs")
        os.makedirs(custom_dir)

        parser = self._make_parser(json_graph=True, json_graph_dir=custom_dir)
        parser.write_json(self.out_dir)

        graph = self._read_graph(custom_dir)

        # Verify complete structure
        for module_name, module_data in parser.modules.items():
            self.assertIn(module_name, graph)
            self.assertEqual(graph[module_name]["calls"], module_data["calls"])
            self.assertEqual(
                graph[module_name]["called_by"],
                parser.called_by.get(module_name, [])
            )


class TestJsonGraphDirInteraction(JsonGraphDirTestCase):
    """Tests for interactions between parameters."""

    def test_json_graph_true_json_graph_dir_none_output_dir_output(self):
        """Standard case: --json-graph without --json-graph-dir uses output dir."""
        parser = self._make_parser(json_graph=True, json_graph_dir=None)
        parser.write_json(self.out_dir)

        self.assertTrue(self._graph_exists(self.out_dir))

    def test_json_graph_false_json_graph_dir_set_ignored(self):
        """--json-graph-dir ignored when --json-graph is false."""
        custom_dir = os.path.join(self.tmpdir.name, "ignored")
        os.makedirs(custom_dir)

        parser = self._make_parser(json_graph=False, json_graph_dir=custom_dir)
        parser.write_json(self.out_dir)

        # Nothing written anywhere
        self.assertFalse(self._graph_exists(self.out_dir))
        self.assertFalse(self._graph_exists(custom_dir))

    def test_json_graph_true_json_graph_dir_empty_string_uses_output_dir(self):
        """Empty string for --json-graph-dir should use output dir."""
        parser = self._make_parser(json_graph=True, json_graph_dir="")
        # Treat empty string as None (using output dir)
        if not parser.json_graph_dir:
            parser.json_graph_dir = None
        parser.write_json(self.out_dir)

        # Should write to output directory
        self.assertTrue(self._graph_exists(self.out_dir))


if __name__ == "__main__":
    unittest.main()
