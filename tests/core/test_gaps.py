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


class TestBacktickAttributesNotCorruptPorts(unittest.TestCase):
    """v0.2.2 regression: Verilog backtick-prefixed attributes (e.g., `KEEP_FOR_DBG)
    with commas in their expansions break port parsing, causing:
    - Attribute text to leak into port names
    - Bit widths to be truncated
    - Duplicate/orphaned port entries from split attributes

    Example corruption:
    - Old (correct): ref_1pps
    - New (broken): (*mark_debug="true" + ref_1pps (DONT_TOUCH="TRUE"*)

    See: examples/issues/{ble_ll,auxiliary_daemon}_{old,new}.md for regression evidence.
    """

    def setUp(self):
        parser = VerilogWikiParser([f"{CORE_FIXTURES}/backtick_attributes.v"])
        parser.scan()
        self.mod = parser.modules["backtick_attrs"]

    def test_backtick_prefixed_input_port_name_clean(self):
        """Port name should not contain attribute text."""
        self.assertIn("ref_1pps", self.mod["inputs"])
        # Should NOT have attribute text pollution
        for port in self.mod["inputs"]:
            self.assertNotIn("(*mark_debug", port,
                f"Attribute text leaked into port name: {port}")
            self.assertNotIn("DONT_TOUCH", port,
                f"Attribute text leaked into port name: {port}")

    def test_backtick_prefixed_output_port_with_width(self):
        """Backtick output port widths should be fully extracted."""
        self.assertIn("tx_tap_index [3:0]", self.mod["outputs"],
            f"tx_tap_index width not found. outputs: {self.mod['outputs']}")
        # Should NOT be truncated
        self.assertNotIn("tx_tap_index [3", self.mod["outputs"],
            "tx_tap_index width was truncated")

    def test_backtick_prefixed_signed_port_with_width(self):
        """Backtick signed ports with full width should parse correctly."""
        self.assertIn("tx_tap_value [15:0]", self.mod["outputs"],
            f"tx_tap_value with full range not found. outputs: {self.mod['outputs']}")

    def test_normal_output_port_widths_still_work(self):
        """Non-backtick ports should still parse correctly."""
        self.assertIn("tx_addr [31:0]", self.mod["outputs"])
        self.assertIn("axi_bresp [1:0]", self.mod["outputs"],
            f"axi_bresp [1:0] not found. outputs: {self.mod['outputs']}")

    def test_debug_input_port_width_complete(self):
        """Backtick input port with width should be complete."""
        self.assertIn("debug_data [7:0]", self.mod["inputs"])

    def test_debug_output_port_width_complete(self):
        """Backtick output port with width should be complete."""
        self.assertIn("debug_status [15:0]", self.mod["outputs"])

    def test_total_input_port_count_correct(self):
        """All input ports should be present (no duplicates/orphans from attribute splits)."""
        # clk, rst, ref_1pps, uart_rx, debug_data
        self.assertEqual(len(self.mod["inputs"]), 5,
            f"Expected 5 inputs, got {len(self.mod['inputs'])}: {self.mod['inputs']}")

    def test_total_output_port_count_correct(self):
        """All output ports should be present (no duplicates/orphans from attribute splits)."""
        # tx_tap_index, tx_tap_value, tx_addr, axi_bresp, debug_status
        self.assertEqual(len(self.mod["outputs"]), 5,
            f"Expected 5 outputs, got {len(self.mod['outputs'])}: {self.mod['outputs']}")


class TestAttributeVariantsHandled(unittest.TestCase):
    """Verify the fix generalizes to various Verilog attribute syntaxes,
    not just the specific `KEEP_FOR_DBG pattern from the regression examples.
    Tests: simple attributes, multiple attributes, macro-expanded attributes,
    attributes with multiple comma-separated values inside parentheses.
    """

    def setUp(self):
        parser = VerilogWikiParser([f"{CORE_FIXTURES}/verilog_attributes_variants.v"])
        parser.scan()
        self.mod = parser.modules["attr_variants"]

    def test_simple_keep_attribute(self):
        """Simple (*keep*) attribute should be stripped."""
        self.assertIn("clk", self.mod["inputs"])
        for port in self.mod["inputs"]:
            self.assertNotIn("(*keep*)", port)

    def test_multiple_attributes_on_port(self):
        """Multiple attributes on same port should be stripped."""
        self.assertIn("rst", self.mod["inputs"])
        for port in self.mod["inputs"]:
            self.assertNotIn("(*mark_debug", port)
            self.assertNotIn("(*keep*)", port)

    def test_attribute_with_commas_inside(self):
        """Attributes with comma-separated values inside should be stripped.
        This is the core regression issue."""
        self.assertIn("data_in", self.mod["inputs"])
        # Verify no orphaned attribute fragments
        self.assertNotIn("(*mark_debug", self.mod["inputs"],
            "Attribute fragment leaked into port list")

    def test_macro_expanded_attribute(self):
        """Macro-expanded attributes should be stripped."""
        self.assertIn("enable", self.mod["inputs"])
        for port in self.mod["inputs"]:
            self.assertNotIn("(*keep*)", port)

    def test_attribute_in_middle_of_line(self):
        """Attributes in middle of port declaration should be handled."""
        self.assertIn("addr", self.mod["inputs"])
        self.assertNotIn("(*some_attr*)", self.mod["inputs"])

    def test_output_with_attributes(self):
        """Output ports with attributes should be properly parsed."""
        self.assertIn("result [7:0]", self.mod["outputs"])
        self.assertNotIn("(*keep*)", self.mod["outputs"])

    def test_complex_attribute_with_multiple_values(self):
        """Complex attribute with multiple comma-separated values."""
        self.assertIn("valid", self.mod["outputs"])
        # Ensure no attribute pollution
        for port in self.mod["outputs"]:
            self.assertNotIn("DONT_TOUCH", port,
                f"Attribute text in port: {port}")
            self.assertNotIn("mark_debug", port,
                f"Attribute text in port: {port}")

    def test_no_attributes_unaffected(self):
        """Ports without attributes should be unaffected by attribute stripping."""
        self.assertIn("simple_port", self.mod["inputs"])
        self.assertIn("wide_output [15:0]", self.mod["outputs"])

    def test_no_orphaned_attribute_fragments(self):
        """No orphaned attribute fragments should appear in port lists."""
        all_ports = self.mod["inputs"] + self.mod["outputs"]
        # Check for any leftover attribute markers
        for port in all_ports:
            self.assertNotIn("(*", port, f"Orphaned attribute in: {port}")
            self.assertNotIn("*)", port, f"Orphaned attribute in: {port}")

    def test_correct_total_port_count(self):
        """Correct number of ports should be extracted (no duplicates from attributes)."""
        # Expected: clk, rst, data_in, enable, addr, simple_port = 6 inputs
        # Expected: result, magic, valid, wide_output = 4 outputs
        self.assertEqual(len(self.mod["inputs"]), 6,
            f"Expected 6 inputs, got {len(self.mod['inputs'])}: {self.mod['inputs']}")
        self.assertEqual(len(self.mod["outputs"]), 4,
            f"Expected 4 outputs, got {len(self.mod['outputs'])}: {self.mod['outputs']}")


class TestShuffledPortOrdering(unittest.TestCase):
    """Verify the parser correctly handles ports when inputs and outputs
    are interleaved/shuffled in the port list, not grouped together.

    The parser uses stateful direction tracking (current_direction), so this
    test confirms that mechanism works correctly even with shuffled ordering.
    """

    def setUp(self):
        parser = VerilogWikiParser([f"{CORE_FIXTURES}/shuffled_ports.v"])
        parser.scan()
        self.mod = parser.modules["shuffled_ports"]

    def test_first_input_correctly_classified(self):
        """First input port should be in inputs list."""
        self.assertIn("clk", self.mod["inputs"])

    def test_first_output_correctly_classified(self):
        """First output port should be in outputs list."""
        self.assertIn("data_out [7:0]", self.mod["outputs"])

    def test_second_input_after_output(self):
        """Input appearing after output should still be in inputs list."""
        self.assertIn("rst", self.mod["inputs"])

    def test_second_output_after_input(self):
        """Output appearing after input should still be in outputs list."""
        self.assertIn("valid", self.mod["outputs"])

    def test_input_with_width_in_shuffled_order(self):
        """Input with width in shuffled position should be correctly parsed."""
        self.assertIn("addr [15:0]", self.mod["inputs"])

    def test_output_with_reg_keyword(self):
        """Output with 'reg' keyword should be in outputs."""
        self.assertIn("ready", self.mod["outputs"])

    def test_output_with_wire_keyword(self):
        """Output with 'wire' keyword should be in outputs."""
        self.assertIn("status [3:0]", self.mod["outputs"])

    def test_no_misclassification_due_to_shuffling(self):
        """No inputs should be in outputs list and vice versa."""
        # Inputs should not appear in outputs
        for inp in self.mod["inputs"]:
            self.assertNotIn(inp, self.mod["outputs"],
                f"Port {inp} appears in both inputs and outputs")
        # Outputs should not appear in inputs
        for out in self.mod["outputs"]:
            self.assertNotIn(out, self.mod["inputs"],
                f"Port {out} appears in both inputs and outputs")

    def test_correct_total_count_shuffled(self):
        """Correct total count of inputs and outputs despite shuffling."""
        # inputs: clk, rst, addr, enable = 4
        # outputs: data_out, valid, ready, status = 4
        self.assertEqual(len(self.mod["inputs"]), 4,
            f"Expected 4 inputs, got {len(self.mod['inputs'])}: {self.mod['inputs']}")
        self.assertEqual(len(self.mod["outputs"]), 4,
            f"Expected 4 outputs, got {len(self.mod['outputs'])}: {self.mod['outputs']}")


if __name__ == "__main__":
    unittest.main()
