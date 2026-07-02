import unittest
from rtl_aid.lint import check_sensitivity_completeness, check_unlabeled_generate
from tests.support import LINT_FIXTURES


def _read(fixture_name):
    with open(f"{LINT_FIXTURES}/{fixture_name}") as f:
        return f.read()


class TestSensitivityListCompleteness(unittest.TestCase):
    """checklist item 24 — verilator's -Wall does not flag an always @(...)
    block that reads a signal missing from its own sensitivity list (confirmed
    empirically during review). rtl-aid needs its own check for this."""

    def test_incomplete_list_is_flagged(self):
        issues = check_sensitivity_completeness(_read("sens_incomplete.v"))
        self.assertTrue(issues, "missing signal 'b' should have been flagged")
        _, message = next(iter(issues.values()))
        self.assertIn("b", message)

    def test_complete_list_is_not_flagged(self):
        issues = check_sensitivity_completeness(_read("sens_complete.v"))
        self.assertEqual(issues, {})

    def test_always_star_is_never_flagged(self):
        text = "always @(*) begin\n  y = a & b;\nend\n"
        self.assertEqual(check_sensitivity_completeness(text), {})

    def test_clocked_block_is_never_flagged(self):
        text = "always @(posedge clk) begin\n  q <= d;\nend\n"
        self.assertEqual(check_sensitivity_completeness(text), {})


class TestUnlabeledGenerateBlocks(unittest.TestCase):
    """checklist items 27, 75 — verilator's -Wall does not flag an unlabeled
    generate/begin block (confirmed empirically during review)."""

    def test_unlabeled_block_is_flagged(self):
        issues = check_unlabeled_generate(_read("gen_unlabeled.v"))
        self.assertTrue(issues, "unlabeled generate begin block should have been flagged")

    def test_labeled_block_is_not_flagged(self):
        issues = check_unlabeled_generate(_read("gen_labeled.v"))
        self.assertEqual(issues, {})


if __name__ == "__main__":
    unittest.main()
