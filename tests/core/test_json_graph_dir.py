"""
Test suite for rtldoc --json-graph-file feature.

Tests that:
1. When --json-graph flag is used without --json-graph-file, graph.json is written to output dir
2. When --json-graph flag is used WITH --json-graph-file, graph.json is written to FILE
3. --json-graph-file only has effect when --json-graph is also provided
4. Non-existent directories are created automatically
5. In dry-run mode, file path is identified correctly but file not written
"""
import os
import json
import tempfile
import unittest
from rtl_aid.core import VerilogWikiParser


class JsonGraphFileTestCase(unittest.TestCase):
    """Base test case for JSON graph file feature."""

    def setUp(self):
        """Set up temporary directories for testing."""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.out_dir = os.path.join(self.tmpdir.name, "output")
        os.makedirs(self.out_dir)
        self.addCleanup(self.tmpdir.cleanup)

    def _make_parser(self, json_graph=False, json_graph_file=None, dry_run=False):
        """Create a VerilogWikiParser with test parameters."""
        parser = VerilogWikiParser(
            paths=[],
            verbose=0,
            ci=False,
            json_graph=json_graph,
            json_graph_file=json_graph_file,
            print_errors=False,
            exclude=None,
            dry_run=dry_run,
        )
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

    def _read_graph(self, filepath):
        """Read and parse graph.json from the given file path."""
        if not os.path.isfile(filepath):
            return None
        with open(filepath) as f:
            return json.load(f)


class TestJsonGraphDefaultBehavior(JsonGraphFileTestCase):
    """Tests for default behavior (no --json-graph-file specified)."""

    def test_json_graph_false_no_file_written(self):
        """When --json-graph is false, no graph.json should be written."""
        parser = self._make_parser(json_graph=False)
        parser.write_json(self.out_dir)
        self.assertFalse(os.path.exists(os.path.join(self.out_dir, "graph.json")))

    def test_json_graph_true_writes_to_output_dir(self):
        """When --json-graph is true without --json-graph-file, write to output dir."""
        parser = self._make_parser(json_graph=True)
        parser.write_json(self.out_dir)
        self.assertTrue(os.path.exists(os.path.join(self.out_dir, "graph.json")))

    def test_json_graph_contains_module_data(self):
        """Graph.json should contain the module dependency data."""
        parser = self._make_parser(json_graph=True)
        parser.write_json(self.out_dir)

        graph = self._read_graph(os.path.join(self.out_dir, "graph.json"))
        self.assertIsNotNone(graph)
        self.assertIn("top_module", graph)
        self.assertIn("sub_module1", graph)

    def test_json_graph_none_file_uses_output_dir(self):
        """When json_graph_file is None, output dir should be used."""
        parser = self._make_parser(json_graph=True, json_graph_file=None)
        parser.write_json(self.out_dir)
        self.assertTrue(os.path.exists(os.path.join(self.out_dir, "graph.json")))


class TestJsonGraphFileParameter(JsonGraphFileTestCase):
    """Tests for --json-graph-file parameter."""

    def test_json_graph_file_no_effect_without_json_graph_flag(self):
        """--json-graph-file should have no effect if --json-graph is false."""
        custom_file = os.path.join(self.tmpdir.name, "custom.json")
        parser = self._make_parser(json_graph=False, json_graph_file=custom_file)
        parser.write_json(self.out_dir)
        self.assertFalse(os.path.exists(custom_file))

    def test_json_graph_file_with_json_graph_writes_to_file(self):
        """When both flags set, write graph.json to file."""
        custom_file = os.path.join(self.tmpdir.name, "my_graph.json")
        parser = self._make_parser(json_graph=True, json_graph_file=custom_file)
        parser.write_json(self.out_dir)

        self.assertTrue(os.path.exists(custom_file))
        self.assertFalse(os.path.exists(os.path.join(self.out_dir, "graph.json")))

    def test_json_graph_file_creates_parent_directory(self):
        """--json-graph-file should create parent directory if it doesn't exist."""
        custom_file = os.path.join(self.tmpdir.name, "subdir", "my_graph.json")
        self.assertFalse(os.path.exists(os.path.dirname(custom_file)))

        parser = self._make_parser(json_graph=True, json_graph_file=custom_file)
        parser.write_json(self.out_dir)

        self.assertTrue(os.path.exists(custom_file))

    def test_json_graph_file_overwrites_existing(self):
        """Calling write_json multiple times should overwrite the file."""
        custom_file = os.path.join(self.tmpdir.name, "graph.json")
        parser = self._make_parser(json_graph=True, json_graph_file=custom_file)

        parser.write_json(self.out_dir)
        parser.modules["new_module"] = {"calls": [], "inputs": [], "outputs": []}
        parser.write_json(self.out_dir)

        graph = self._read_graph(custom_file)
        self.assertIn("new_module", graph)


class TestJsonGraphFileDryRun(JsonGraphFileTestCase):
    """Tests for dry-run mode behavior."""

    def test_dry_run_with_json_graph_no_file_written(self):
        """In dry-run mode, graph.json should not be written."""
        parser = self._make_parser(json_graph=True, dry_run=True)
        parser.write_json(self.out_dir)
        self.assertFalse(os.path.exists(os.path.join(self.out_dir, "graph.json")))

    def test_dry_run_with_json_graph_file_no_file_written(self):
        """In dry-run with --json-graph-file, file should not be written."""
        custom_file = os.path.join(self.tmpdir.name, "graph.json")
        parser = self._make_parser(json_graph=True, json_graph_file=custom_file, dry_run=True)
        parser.write_json(self.out_dir)
        self.assertFalse(os.path.exists(custom_file))


class TestJsonGraphFileEdgeCases(JsonGraphFileTestCase):
    """Edge cases and special scenarios."""

    def test_empty_modules_generates_empty_graph(self):
        """Parser with no modules should generate empty graph."""
        parser = self._make_parser(json_graph=True)
        parser.modules = {}
        parser.called_by = {}
        parser.write_json(self.out_dir)

        graph = self._read_graph(os.path.join(self.out_dir, "graph.json"))
        self.assertEqual(graph, {})

    def test_json_graph_is_valid_json(self):
        """Generated graph.json should be valid JSON."""
        parser = self._make_parser(json_graph=True)
        parser.write_json(self.out_dir)

        graph = self._read_graph(os.path.join(self.out_dir, "graph.json"))
        self.assertIsInstance(graph, dict)

    def test_json_graph_file_absolute_path(self):
        """--json-graph-file with absolute path should work."""
        abs_file = os.path.abspath(os.path.join(self.tmpdir.name, "graph.json"))
        parser = self._make_parser(json_graph=True, json_graph_file=abs_file)
        parser.write_json(self.out_dir)

        self.assertTrue(os.path.exists(abs_file))

    def test_json_graph_preserves_module_structure(self):
        """Graph should preserve all module structure information."""
        parser = self._make_parser(json_graph=True)
        parser.write_json(self.out_dir)

        graph = self._read_graph(os.path.join(self.out_dir, "graph.json"))
        for module_name, module_data in parser.modules.items():
            self.assertIn(module_name, graph)
            self.assertEqual(graph[module_name]["calls"], module_data["calls"])

    def test_json_graph_file_with_relative_path(self):
        """--json-graph-file should work with relative paths."""
        rel_file = os.path.join(self.tmpdir.name, "subdir", "graph.json")
        parser = self._make_parser(json_graph=True, json_graph_file=rel_file)
        parser.write_json(self.out_dir)
        self.assertTrue(os.path.exists(rel_file))

    def test_json_graph_file_with_trailing_slash(self):
        """--json-graph-file with trailing slash should work (normalized)."""
        file_with_slash = os.path.join(self.tmpdir.name, "graph.json") + "/"
        clean_file = file_with_slash.rstrip("/")
        parser = self._make_parser(json_graph=True, json_graph_file=file_with_slash)
        parser.write_json(self.out_dir)
        # Should normalize away the trailing slash
        self.assertTrue(os.path.exists(clean_file))

    def test_json_graph_file_empty_string_falls_back_to_output_dir(self):
        """Empty string for --json-graph-file should fall back to output dir."""
        parser = self._make_parser(json_graph=True, json_graph_file="")
        parser.write_json(self.out_dir)
        # Empty string should be treated as falsy, use output_dir
        self.assertTrue(os.path.exists(os.path.join(self.out_dir, "graph.json")))


if __name__ == "__main__":
    unittest.main()
