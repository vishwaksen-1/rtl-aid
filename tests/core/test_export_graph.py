"""
Test suite for the unified --export-graph / --from-graph feature.

Replaces the old separate --json-graph/--json-graph-file/--export-dot
mechanisms (formerly tests/core/test_json_graph_dir.py and
tests/core/test_export_dot.py) with a single `export_graphs(out_dir, graph=None)`
API on VerilogWikiParser, driven by a list of target file paths
(`self.export_graph`) whose format is inferred from each path's extension:

- ".json" -> write the dependency graph as JSON
- ".dot"  -> write the dependency graph as Graphviz DOT

A bare filename (no directory component) resolves inside `out_dir`; a path
with a directory component is used as given (with parent dirs auto-created).

The optional `graph=` param lets a caller supply an already-loaded graph dict
(used by --from-graph's standalone conversion mode) instead of building one
from the parser's own `self.modules`/`self.called_by` state.
"""
import os
import json
import tempfile
import unittest
from rtl_aid.core import VerilogWikiParser


class ExportGraphTestCase(unittest.TestCase):
    """Base test case for the export_graphs feature."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.out_dir = os.path.join(self.tmpdir.name, "output")
        os.makedirs(self.out_dir)
        self.addCleanup(self.tmpdir.cleanup)

    def _make_parser(self, export_graph=None, dry_run=False):
        parser = VerilogWikiParser(
            paths=[],
            verbose=0,
            ci=False,
            export_graph=export_graph,
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

    def _read_json(self, filepath):
        if not os.path.isfile(filepath):
            return None
        with open(filepath) as f:
            return json.load(f)

    def _read_text(self, filepath):
        if not os.path.isfile(filepath):
            return None
        with open(filepath) as f:
            return f.read()


class TestNoTargets(ExportGraphTestCase):
    """When export_graph is empty/unset, nothing should be written."""

    def test_no_targets_no_file_written(self):
        parser = self._make_parser(export_graph=None)
        parser.export_graphs(self.out_dir)
        self.assertFalse(os.path.exists(os.path.join(self.out_dir, "graph.json")))

    def test_empty_list_no_file_written(self):
        parser = self._make_parser(export_graph=[])
        parser.export_graphs(self.out_dir)
        self.assertEqual(os.listdir(self.out_dir), [])


class TestBareFilenameResolvesToOutDir(ExportGraphTestCase):
    """A target with no directory component lands inside out_dir."""

    def test_bare_json_filename_written_to_out_dir(self):
        parser = self._make_parser(export_graph=["graph.json"])
        parser.export_graphs(self.out_dir)
        self.assertTrue(os.path.exists(os.path.join(self.out_dir, "graph.json")))

    def test_bare_dot_filename_written_to_out_dir(self):
        parser = self._make_parser(export_graph=["graph.dot"])
        parser.export_graphs(self.out_dir)
        self.assertTrue(os.path.exists(os.path.join(self.out_dir, "graph.dot")))

    def test_bare_filename_content_matches_modules(self):
        parser = self._make_parser(export_graph=["graph.json"])
        parser.export_graphs(self.out_dir)
        graph = self._read_json(os.path.join(self.out_dir, "graph.json"))
        self.assertIn("top_module", graph)
        self.assertIn("sub_module1", graph)


class TestExplicitPathTarget(ExportGraphTestCase):
    """A target with a directory component is used as-is, not joined to out_dir."""

    def test_custom_json_path_written_and_not_duplicated_to_out_dir(self):
        custom_file = os.path.join(self.tmpdir.name, "my_graph.json")
        parser = self._make_parser(export_graph=[custom_file])
        parser.export_graphs(self.out_dir)

        self.assertTrue(os.path.exists(custom_file))
        self.assertFalse(os.path.exists(os.path.join(self.out_dir, "graph.json")))

    def test_custom_dot_path_written(self):
        custom_file = os.path.join(self.tmpdir.name, "my_graph.dot")
        parser = self._make_parser(export_graph=[custom_file])
        parser.export_graphs(self.out_dir)
        self.assertTrue(os.path.exists(custom_file))

    def test_creates_parent_directories(self):
        custom_file = os.path.join(self.tmpdir.name, "nested", "deep", "graph.dot")
        parser = self._make_parser(export_graph=[custom_file])
        parser.export_graphs(self.out_dir)

        self.assertTrue(os.path.isdir(os.path.dirname(custom_file)))
        self.assertTrue(os.path.exists(custom_file))

    def test_absolute_path_supported(self):
        abs_file = os.path.abspath(os.path.join(self.tmpdir.name, "graph.json"))
        parser = self._make_parser(export_graph=[abs_file])
        parser.export_graphs(self.out_dir)
        self.assertTrue(os.path.exists(abs_file))

    def test_trailing_slash_normalized(self):
        file_with_slash = os.path.join(self.tmpdir.name, "graph.json") + "/"
        clean_file = file_with_slash.rstrip("/")
        parser = self._make_parser(export_graph=[file_with_slash])
        parser.export_graphs(self.out_dir)
        self.assertTrue(os.path.exists(clean_file))

    def test_overwrites_on_repeated_call(self):
        custom_file = os.path.join(self.tmpdir.name, "graph.json")
        parser = self._make_parser(export_graph=[custom_file])

        parser.export_graphs(self.out_dir)
        parser.modules["new_module"] = {"calls": [], "inputs": [], "outputs": []}
        parser.export_graphs(self.out_dir)

        graph = self._read_json(custom_file)
        self.assertIn("new_module", graph)


class TestMultipleTargets(ExportGraphTestCase):
    """Multiple targets in one call write independent files in their own formats."""

    def test_json_and_dot_both_written(self):
        json_file = os.path.join(self.tmpdir.name, "graph.json")
        dot_file = os.path.join(self.tmpdir.name, "graph.dot")
        parser = self._make_parser(export_graph=[json_file, dot_file])
        parser.export_graphs(self.out_dir)

        self.assertTrue(os.path.exists(json_file))
        self.assertTrue(os.path.exists(dot_file))

        graph = self._read_json(json_file)
        self.assertIn("top_module", graph)

        dot_content = self._read_text(dot_file)
        self.assertIn("digraph", dot_content)
        self.assertIn("top_module", dot_content)


class TestDotContent(ExportGraphTestCase):
    """Content-level assertions on the generated DOT file."""

    def _export(self, parser):
        dot_file = os.path.join(self.tmpdir.name, "graph.dot")
        parser.export_graph = [dot_file]
        parser.export_graphs(self.out_dir)
        return self._read_text(dot_file)

    def test_valid_graphviz_structure(self):
        content = self._export(self._make_parser())
        self.assertIn("digraph", content)
        self.assertIn("{", content)
        self.assertIn("}", content)

    def test_includes_all_modules(self):
        content = self._export(self._make_parser())
        self.assertIn("top_module", content)
        self.assertIn("sub_module1", content)
        self.assertIn("sub_module2", content)

    def test_includes_all_edges(self):
        content = self._export(self._make_parser())
        self.assertIn("->", content)

    def test_empty_graph_still_valid(self):
        parser = self._make_parser()
        parser.modules = {}
        parser.called_by = {}
        content = self._export(parser)
        self.assertIn("digraph", content)

    def test_circular_dependency_does_not_hang(self):
        parser = VerilogWikiParser([], verbose=0, ci=False)
        parser.modules = {
            "module_a": {"file": "a.v", "inputs": [], "outputs": [], "inouts": [], "parameters": {}, "calls": ["module_b"]},
            "module_b": {"file": "b.v", "inputs": [], "outputs": [], "inouts": [], "parameters": {}, "calls": ["module_a"]},
        }
        parser.called_by = {
            "module_a": ["module_b"],
            "module_b": ["module_a"],
        }
        content = self._export(parser)
        self.assertIn("module_a", content)
        self.assertIn("module_b", content)
        self.assertIn("->", content)


class TestJsonContent(ExportGraphTestCase):
    """Content-level assertions on the generated JSON file."""

    def test_is_valid_json_dict(self):
        parser = self._make_parser(export_graph=["graph.json"])
        parser.export_graphs(self.out_dir)
        graph = self._read_json(os.path.join(self.out_dir, "graph.json"))
        self.assertIsInstance(graph, dict)

    def test_empty_modules_generates_empty_graph(self):
        parser = self._make_parser(export_graph=["graph.json"])
        parser.modules = {}
        parser.called_by = {}
        parser.export_graphs(self.out_dir)
        graph = self._read_json(os.path.join(self.out_dir, "graph.json"))
        self.assertEqual(graph, {})

    def test_preserves_module_structure(self):
        parser = self._make_parser(export_graph=["graph.json"])
        parser.export_graphs(self.out_dir)
        graph = self._read_json(os.path.join(self.out_dir, "graph.json"))
        for module_name, module_data in parser.modules.items():
            self.assertIn(module_name, graph)
            self.assertEqual(graph[module_name]["calls"], module_data["calls"])


class TestDryRun(ExportGraphTestCase):
    """In dry-run mode, no files should be written for either format."""

    def test_dry_run_json_not_written(self):
        parser = self._make_parser(export_graph=["graph.json"], dry_run=True)
        parser.export_graphs(self.out_dir)
        self.assertFalse(os.path.exists(os.path.join(self.out_dir, "graph.json")))

    def test_dry_run_dot_not_written(self):
        parser = self._make_parser(export_graph=["graph.dot"], dry_run=True)
        parser.export_graphs(self.out_dir)
        self.assertFalse(os.path.exists(os.path.join(self.out_dir, "graph.dot")))

    def test_dry_run_custom_path_not_written(self):
        custom_file = os.path.join(self.tmpdir.name, "graph.json")
        parser = self._make_parser(export_graph=[custom_file], dry_run=True)
        parser.export_graphs(self.out_dir)
        self.assertFalse(os.path.exists(custom_file))


class TestGraphOverrideParam(ExportGraphTestCase):
    """The graph= param (used by --from-graph standalone mode) bypasses self.modules."""

    def test_uses_supplied_graph_instead_of_self_modules(self):
        parser = self._make_parser(export_graph=["graph.dot"])
        # self.modules has top_module/sub_module1/sub_module2, but we pass a
        # completely different graph in — output should reflect the override.
        override_graph = {
            "module_a": {"calls": ["module_b"], "called_by": []},
            "module_b": {"calls": [], "called_by": ["module_a"]},
        }
        parser.export_graphs(self.out_dir, graph=override_graph)

        content = self._read_text(os.path.join(self.out_dir, "graph.dot"))
        self.assertIn("module_a", content)
        self.assertIn("module_b", content)
        self.assertNotIn("top_module", content)

    def test_works_with_empty_self_modules(self):
        # Standalone --from-graph mode never calls scan(), so self.modules is
        # empty; the override graph must still be exported correctly.
        parser = self._make_parser(export_graph=["graph.json"])
        parser.modules = {}
        parser.called_by = {}
        override_graph = {"solo_module": {"calls": [], "called_by": []}}

        parser.export_graphs(self.out_dir, graph=override_graph)

        graph = self._read_json(os.path.join(self.out_dir, "graph.json"))
        self.assertEqual(graph, override_graph)


class TestBadExtension(ExportGraphTestCase):
    """An unsupported extension should fail loudly, not silently."""

    def test_unsupported_extension_raises(self):
        parser = self._make_parser(export_graph=["graph.txt"])
        with self.assertRaises(ValueError):
            parser.export_graphs(self.out_dir)


if __name__ == "__main__":
    unittest.main()
