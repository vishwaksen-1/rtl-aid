import unittest
from rtl_aid.lint import parse_lint_output


SAMPLE_OUTPUT = """\
%Warning-WIDTHEXPAND: rtl/rx_ram.v:75:65: Operator EQ expects 32 bits on the LHS, but LHS's VARREF 'axi_awaddr_core' generates 6 bits.
                                         : ... note: In instance 'rx_ram'
   75 |     assign reset_rd_addr_axi = (slv_reg_wren && axi_awaddr_core == RD_DATA_AXI_REG_IDX);
      |                                                                 ^~
%Warning-UNUSED: rtl/rx_ram.v:102:12: Signal is not used: 'temp_sig'
%Warning-WIDTHEXPAND: other_file.v:10:5: Some warning for another file.
%Error: rtl/rx_ram.v:200:1: Syntax issue here.
"""


class TestParseLintOutput(unittest.TestCase):
    def test_extracts_issues_for_target_file(self):
        issues = parse_lint_output(SAMPLE_OUTPUT, "rtl/rx_ram.v")
        self.assertIn(75, issues)
        self.assertIn(102, issues)
        self.assertIn(200, issues)

    def test_ignores_other_files(self):
        issues = parse_lint_output(SAMPLE_OUTPUT, "rtl/rx_ram.v")
        # Line 10 belongs to other_file.v — must not appear
        self.assertNotIn(10, issues)

    def test_first_message_per_line_wins(self):
        output = """\
%Warning-A: myfile.v:5:1: First warning on line 5.
%Warning-B: myfile.v:5:3: Second warning on line 5.
"""
        issues = parse_lint_output(output, "myfile.v")
        _, message = issues[5]
        self.assertEqual(message, "First warning on line 5.")

    def test_continuation_lines_ignored(self):
        # Lines without leading % must not produce issues
        output = "%Warning-X: myfile.v:3:1: Real warning.\n   3 | some code\n      | ^~\n"
        issues = parse_lint_output(output, "myfile.v")
        self.assertEqual(list(issues.keys()), [3])

    def test_empty_output(self):
        self.assertEqual(parse_lint_output("", "myfile.v"), {})

    def test_warning_id_is_preserved(self):
        # checklist items 12/77 — an agent citing a suppression justification
        # needs a stable rule ID, not just the free-text message.
        issues = parse_lint_output(SAMPLE_OUTPUT, "rtl/rx_ram.v")
        warning_id, _ = issues[75]
        self.assertEqual(warning_id, "WIDTHEXPAND")

    def test_bare_error_has_empty_id(self):
        issues = parse_lint_output(SAMPLE_OUTPUT, "rtl/rx_ram.v")
        warning_id, _ = issues[200]
        self.assertEqual(warning_id, "")


if __name__ == "__main__":
    unittest.main()
