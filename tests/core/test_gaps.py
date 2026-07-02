import unittest
from rtl_aid.core import VerilogWikiParser
from tests.support import CORE_FIXTURES


class TestPortWidthsAndTypesRendered(unittest.TestCase):
    """checklist items 62, 65, 66 — port widths and custom types (structs,
    enums) are currently discarded; extract_module_and_ports keeps only the
    bare port name, so every generated doc shows names with zero type info."""

    def setUp(self):
        parser = VerilogWikiParser([f"{CORE_FIXTURES}/widths.sv"])
        parser.scan()
        self.mod = parser.modules["widths"]

    def test_plain_scalar_port_has_no_annotation(self):
        self.assertIn("clk", self.mod["inputs"])

    def test_vector_port_shows_width(self):
        self.assertIn("data_in [7:0]", self.mod["inputs"])

    def test_output_vector_port_shows_width(self):
        self.assertIn("data_out [15:0]", self.mod["outputs"])

    def test_packed_struct_port_shows_type_name(self):
        self.assertIn("p (pair_t)", self.mod["inputs"])

    def test_enum_port_shows_type_name(self):
        self.assertIn("st (state_t)", self.mod["inputs"])


class TestParameterExpressionResolution(unittest.TestCase):
    """checklist item 63 — parameter defaults are copied verbatim from
    source, never evaluated, even for trivial integer arithmetic."""

    def setUp(self):
        parser = VerilogWikiParser([f"{CORE_FIXTURES}/paramexpr.v"])
        parser.scan()
        self.params = parser.modules["paramexpr"]["parameters"]

    def test_plain_literal_untouched(self):
        self.assertIn("BASE = 4", self.params)

    def test_expression_shows_raw_and_resolved_value(self):
        derived = next(p for p in self.params if p.startswith("DERIVED"))
        self.assertIn("BASE * 2", derived)
        self.assertIn("= 8", derived)


class TestLocalparamDistinction(unittest.TestCase):
    """checklist item 64 — localparam entries are silently dropped
    entirely (never rendered anywhere), not merely left unmarked."""

    def setUp(self):
        parser = VerilogWikiParser([f"{CORE_FIXTURES}/localparam.v"])
        parser.scan()
        self.params = parser.modules["localp"]["parameters"]

    def test_parameter_present(self):
        self.assertTrue(any(p.startswith("WIDTH") for p in self.params))

    def test_localparam_present_and_marked(self):
        localparam_entries = [p for p in self.params if "DEPTH" in p]
        self.assertTrue(localparam_entries, "localparam DEPTH was dropped entirely")
        self.assertIn("(localparam)", localparam_entries[0])


class TestMacroDrivenPortsNotDropped(unittest.TestCase):
    """checklist item 57 — a `define standing in for a direction keyword
    causes the port to silently vanish from the doc, with no error raised."""

    def setUp(self):
        parser = VerilogWikiParser([f"{CORE_FIXTURES}/macroport.v"])
        parser.scan()
        self.mod = parser.modules["macroport"]

    def test_macro_declared_scalar_port_is_kept(self):
        self.assertIn("clk", self.mod["inputs"])

    def test_macro_declared_vector_port_is_kept(self):
        self.assertIn("data [7:0]", self.mod["inputs"])

    def test_normal_port_still_parsed(self):
        self.assertIn("valid", self.mod["outputs"])


if __name__ == "__main__":
    unittest.main()
