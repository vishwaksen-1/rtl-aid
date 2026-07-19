import unittest
import os
import json
import tempfile
from rtl_aid.core import VerilogWikiParser
from tests.support import CORE_FIXTURES


class TestCiValidation(unittest.TestCase):
    def setUp(self):
        self.basic_dir = f"{CORE_FIXTURES}/basic"

    def test_ci_validation(self):
        parser = VerilogWikiParser([self.basic_dir], ci=True)
        parser.scan()

        with tempfile.TemporaryDirectory() as out_dir:
            parser.generate_markdown(out_dir)

            with self.assertRaises(SystemExit) as cm:
                parser.run_ci_checks()
            self.assertEqual(cm.exception.code, 1)

        self.assertIn("empty_mod: no IO", parser.issues)
        self.assertIn("mod_a: self-instantiation", parser.issues)
        self.assertIn("mod_a: missing description", parser.issues)

    def test_json_graph(self):
        parser = VerilogWikiParser([self.basic_dir], export_graph=["graph.json"])
        parser.scan()

        with tempfile.TemporaryDirectory() as out_dir:
            parser.export_graphs(out_dir)

            graph_path = os.path.join(out_dir, "graph.json")
            self.assertTrue(os.path.exists(graph_path))

            with open(graph_path) as f:
                data = json.load(f)
                self.assertIn("mod_a", data)
                self.assertIn("mod_b", data["mod_a"]["calls"])


if __name__ == "__main__":
    unittest.main()
