"""Test suite for rtldoc --export-dot feature."""

import os
import json
import tempfile
import unittest
from rtl_aid.core import VerilogWikiParser


class TestExportDot(unittest.TestCase):
    """Tests for Graphviz DOT export functionality."""

    def setUp(self):
        """Set up temporary directories for testing."""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.out_dir = os.path.join(self.tmpdir.name, "output")
        os.makedirs(self.out_dir)
        self.addCleanup(self.tmpdir.cleanup)

    def _make_parser(self):
        """Create a VerilogWikiParser with test modules."""
        parser = VerilogWikiParser([], verbose=0, ci=False)
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

    def test_export_dot_creates_file(self):
        """export_dot should create a DOT file."""
        parser = self._make_parser()
        dot_file = os.path.join(self.tmpdir.name, "graph.dot")

        parser.export_dot(dot_file)

        self.assertTrue(os.path.exists(dot_file))

    def test_export_dot_contains_valid_graphviz(self):
        """Generated DOT file should contain valid Graphviz syntax."""
        parser = self._make_parser()
        dot_file = os.path.join(self.tmpdir.name, "graph.dot")

        parser.export_dot(dot_file)

        with open(dot_file) as f:
            content = f.read()

        # Check for basic Graphviz structure
        self.assertIn("digraph", content)
        self.assertIn("{", content)
        self.assertIn("}", content)

    def test_export_dot_includes_all_modules(self):
        """DOT file should include all modules as nodes."""
        parser = self._make_parser()
        dot_file = os.path.join(self.tmpdir.name, "graph.dot")

        parser.export_dot(dot_file)

        with open(dot_file) as f:
            content = f.read()

        self.assertIn("top_module", content)
        self.assertIn("sub_module1", content)
        self.assertIn("sub_module2", content)

    def test_export_dot_includes_all_edges(self):
        """DOT file should include all call edges."""
        parser = self._make_parser()
        dot_file = os.path.join(self.tmpdir.name, "graph.dot")

        parser.export_dot(dot_file)

        with open(dot_file) as f:
            content = f.read()

        # Check for edges
        self.assertIn("top_module", content)
        self.assertIn("sub_module1", content)
        self.assertIn("->", content)

    def test_export_dot_from_file(self):
        """export_dot_from_file should read JSON and export DOT."""
        json_file = os.path.join(self.tmpdir.name, "graph.json")
        dot_file = os.path.join(self.tmpdir.name, "graph.dot")

        # Create a test graph.json
        graph = {
            "module_a": {"calls": ["module_b"], "called_by": []},
            "module_b": {"calls": [], "called_by": ["module_a"]},
        }
        with open(json_file, "w") as f:
            json.dump(graph, f)

        parser = VerilogWikiParser([])
        parser.export_dot_from_file(json_file, dot_file)

        self.assertTrue(os.path.exists(dot_file))
        with open(dot_file) as f:
            content = f.read()

        self.assertIn("module_a", content)
        self.assertIn("module_b", content)

    def test_export_dot_from_file_missing_json(self):
        """export_dot_from_file should handle missing JSON gracefully."""
        json_file = os.path.join(self.tmpdir.name, "nonexistent.json")
        dot_file = os.path.join(self.tmpdir.name, "graph.dot")

        parser = VerilogWikiParser([])

        with self.assertRaises(SystemExit):
            parser.export_dot_from_file(json_file, dot_file)

    def test_export_dot_from_file_invalid_json(self):
        """export_dot_from_file should handle invalid JSON gracefully."""
        json_file = os.path.join(self.tmpdir.name, "invalid.json")
        dot_file = os.path.join(self.tmpdir.name, "graph.dot")

        with open(json_file, "w") as f:
            f.write("{ invalid json")

        parser = VerilogWikiParser([])

        with self.assertRaises(SystemExit):
            parser.export_dot_from_file(json_file, dot_file)

    def test_dry_run_no_file_written(self):
        """In dry-run mode, DOT file should not be written."""
        parser = self._make_parser()
        parser.dry_run = True
        dot_file = os.path.join(self.tmpdir.name, "graph.dot")

        parser.export_dot(dot_file)

        self.assertFalse(os.path.exists(dot_file))

    def test_export_dot_empty_graph(self):
        """export_dot should handle empty module graphs."""
        parser = self._make_parser()
        parser.modules = {}
        parser.called_by = {}
        dot_file = os.path.join(self.tmpdir.name, "graph.dot")

        parser.export_dot(dot_file)

        with open(dot_file) as f:
            content = f.read()

        self.assertIn("digraph", content)

    def test_export_dot_creates_parent_directories(self):
        """export_dot should create parent directories for output file."""
        parser = self._make_parser()
        dot_file = os.path.join(self.tmpdir.name, "nested", "output", "graph.dot")

        parser.export_dot(dot_file)

        # Parent directories should be created
        self.assertTrue(os.path.isdir(os.path.dirname(dot_file)))
        # DOT file should exist
        self.assertTrue(os.path.exists(dot_file))

    def test_export_dot_circular_dependency(self):
        """export_dot should handle circular dependencies (A->B->A)."""
        parser = VerilogWikiParser([], verbose=0, ci=False)
        parser.modules = {
            "module_a": {"file": "a.v", "inputs": [], "outputs": [], "inouts": [], "parameters": {}, "calls": ["module_b"]},
            "module_b": {"file": "b.v", "inputs": [], "outputs": [], "inouts": [], "parameters": {}, "calls": ["module_a"]},
        }
        parser.called_by = {
            "module_a": ["module_b"],
            "module_b": ["module_a"],
        }
        dot_file = os.path.join(self.tmpdir.name, "circular.dot")

        # Should not hang or error
        parser.export_dot(dot_file)

        self.assertTrue(os.path.exists(dot_file))
        with open(dot_file) as f:
            content = f.read()

        self.assertIn("module_a", content)
        self.assertIn("module_b", content)
        # Both directions should be present
        self.assertIn("->", content)


if __name__ == "__main__":
    unittest.main()
