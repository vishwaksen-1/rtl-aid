"""End-to-end integration tests for rtldoc and rtllint features."""

import os
import tempfile
import unittest
import json

from rtl_aid.core import VerilogWikiParser
from rtl_aid.lint import tag_file


class TestJsonGraphDirFeatureE2E(unittest.TestCase):
    """End-to-end tests for the --json-graph-dir feature."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.test_file = os.path.join(self.tmpdir.name, "test.v")
        with open(self.test_file, "w") as f:
            f.write("""
module test_module(
    input clk,
    output reg data
);
endmodule
""")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_default_writes_to_output_dir(self):
        """Without --json-graph-dir, graph.json goes to output directory."""
        out_dir = os.path.join(self.tmpdir.name, "docs")
        parser = VerilogWikiParser(
            [self.test_file],
            json_graph=True,
            json_graph_dir=None
        )
        parser.scan()
        parser.write_json(out_dir)

        graph_file = os.path.join(out_dir, "graph.json")
        self.assertTrue(os.path.exists(graph_file))
        with open(graph_file) as f:
            data = json.load(f)
        self.assertIsInstance(data, dict)

    def test_custom_dir_writes_only_to_custom(self):
        """With --json-graph-dir, graph.json goes only to custom directory."""
        out_dir = os.path.join(self.tmpdir.name, "docs")
        graph_dir = os.path.join(self.tmpdir.name, "graphs")

        parser = VerilogWikiParser(
            [self.test_file],
            json_graph=True,
            json_graph_dir=graph_dir
        )
        parser.scan()
        parser.write_json(out_dir)

        # Should be in custom dir
        custom_graph = os.path.join(graph_dir, "graph.json")
        self.assertTrue(os.path.exists(custom_graph))

        # Should NOT be in output dir
        out_graph = os.path.join(out_dir, "graph.json")
        self.assertFalse(os.path.exists(out_graph))

    def test_custom_dir_creates_nested_dirs(self):
        """--json-graph-dir should create nested directories if needed."""
        out_dir = os.path.join(self.tmpdir.name, "docs")
        graph_dir = os.path.join(self.tmpdir.name, "a", "b", "c", "graphs")

        parser = VerilogWikiParser(
            [self.test_file],
            json_graph=True,
            json_graph_dir=graph_dir
        )
        parser.scan()
        parser.write_json(out_dir)

        graph_file = os.path.join(graph_dir, "graph.json")
        self.assertTrue(os.path.exists(graph_file))

    def test_dry_run_creates_no_files(self):
        """In dry-run mode, graph.json should not be written."""
        out_dir = os.path.join(self.tmpdir.name, "docs")
        graph_dir = os.path.join(self.tmpdir.name, "graphs")

        parser = VerilogWikiParser(
            [self.test_file],
            json_graph=True,
            json_graph_dir=graph_dir,
            dry_run=True
        )
        parser.scan()
        parser.write_json(out_dir)

        # Neither should exist
        self.assertFalse(os.path.exists(os.path.join(out_dir, "graph.json")))
        self.assertFalse(os.path.exists(os.path.join(graph_dir, "graph.json")))


class TestRtllintCommandTaggingFeatureE2E(unittest.TestCase):
    """End-to-end tests for rtllint command tagging feature."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.test_file = os.path.join(self.tmpdir.name, "test.v")
        with open(self.test_file, "w") as f:
            f.write("""// File header comment
// More comments

module test_module(
    input clk,
    output reg data
);
endmodule
""")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_tags_with_rtllint_not_verilator(self):
        """When tagging, // lint-test: should contain rtllint command."""
        rtllint_cmd = ["rtllint", "-Irtl/core/", self.test_file]
        tag_file(self.test_file, {5: ("WIDTHEXPAND", "Width mismatch")}, rtllint_cmd)

        with open(self.test_file) as f:
            content = f.read()

        self.assertIn("// lint-test:", content)
        self.assertIn("rtllint", content)
        self.assertNotIn("verilator", content)

    def test_includes_preserved_in_command(self):
        """Include directories should be in the rtllint command."""
        rtllint_cmd = ["rtllint", "-Irtl/core/", "-Irtl/lib/", self.test_file]
        tag_file(self.test_file, {5: ("WIDTHEXPAND", "Width mismatch")}, rtllint_cmd)

        with open(self.test_file) as f:
            content = f.read()

        self.assertIn("-Irtl/core/", content)
        self.assertIn("-Irtl/lib/", content)

    def test_update_existing_lint_test_line(self):
        """Updating an existing lint-test line should not duplicate it."""
        # First tag
        rtllint_cmd_1 = ["rtllint", "-Irtl/core/", self.test_file]
        tag_file(self.test_file, {5: ("WIDTHEXPAND", "Width mismatch")}, rtllint_cmd_1)

        # Update with different command
        rtllint_cmd_2 = ["rtllint", "-Idifferent/path/", self.test_file]
        tag_file(self.test_file, {5: ("WIDTHEXPAND", "Width mismatch")}, rtllint_cmd_2)

        with open(self.test_file) as f:
            lines = f.readlines()

        lint_test_count = sum(1 for line in lines if "// lint-test:" in line)
        self.assertEqual(lint_test_count, 1, "Should have exactly one lint-test line")
        self.assertIn("rtllint -Idifferent/path/", "".join(lines))

    def test_idempotent_tagging(self):
        """Running tag_file multiple times should not create duplicates."""
        rtllint_cmd = ["rtllint", "-Irtl/core/", self.test_file]
        issues = {5: ("WIDTHEXPAND", "Width mismatch")}

        # Tag three times
        tag_file(self.test_file, issues, rtllint_cmd)
        tag_file(self.test_file, issues, rtllint_cmd)
        tag_file(self.test_file, issues, rtllint_cmd)

        with open(self.test_file) as f:
            lines = f.readlines()

        lint_test_count = sum(1 for line in lines if "// lint-test:" in line)
        self.assertEqual(lint_test_count, 1, "Should still have only one lint-test line")

    def test_warning_tags_appear_on_source(self):
        """Warning tags should appear as inline comments on the correct lines."""
        rtllint_cmd = ["rtllint", "-Irtl/core/", self.test_file]
        tag_file(self.test_file, {7: ("UNUSEDSIGNAL", "Signal not used")}, rtllint_cmd)

        with open(self.test_file) as f:
            lines = f.readlines()

        # Line 7 should have the warning comment
        # (accounting for 2 header lines inserted at the top)
        self.assertIn("/* Check[UNUSEDSIGNAL]:", lines[8])


if __name__ == "__main__":
    unittest.main()
