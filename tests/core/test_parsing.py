import unittest
from rtl_aid.core import VerilogWikiParser
from tests.support import CORE_FIXTURES


class TestParsingPortsAndParameters(unittest.TestCase):
    def setUp(self):
        self.basic_dir = f"{CORE_FIXTURES}/basic"

    def test_parsing_ports_and_parameters(self):
        parser = VerilogWikiParser([self.basic_dir])
        parser.scan()

        self.assertIn("mod_a", parser.modules)
        mod_a = parser.modules["mod_a"]

        # Check params
        self.assertEqual(len(mod_a["parameters"]), 2)
        self.assertTrue(any("WIDTH" in p for p in mod_a["parameters"]))

        # Check ports with comma inheritance
        self.assertEqual(mod_a["inputs"], ["clk", "rst"])
        self.assertEqual(mod_a["outputs"], ["s_read", "s_write"])
        self.assertEqual(mod_a["inouts"], ["bus"])

    def test_dependency_extraction(self):
        parser = VerilogWikiParser([self.basic_dir])
        parser.scan()

        # mod_a calls mod_b and mod_a
        self.assertIn("mod_b", parser.modules["mod_a"]["calls"])
        self.assertIn("mod_a", parser.modules["mod_a"]["calls"])

        # mod_b is called by mod_a
        self.assertIn("mod_a", parser.called_by["mod_b"])


if __name__ == "__main__":
    unittest.main()
