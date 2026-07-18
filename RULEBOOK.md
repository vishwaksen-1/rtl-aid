# Developer Rulebook: Maintaining rtllint Rules

This guide ensures that `rtllint --list-rules` stays in sync with the actual checks implemented in the codebase.

## When to Update LINT_RULES

**Every time you add a new custom lint check** to `src/rtl_aid/lint.py`, you must also update the `LINT_RULES` dict at the top of the file.

### Checklist

- [ ] Implemented new check function in `src/rtl_aid/lint.py` (e.g., `check_new_rule()`)
- [ ] Assigned a stable rule ID (uppercase, e.g., `MYNEWRULE`)
- [ ] Added entry to `LINT_RULES` dict:
  ```python
  LINT_RULES = {
      "SENSINCOMPLETE": "...",
      "GENUNNAMED": "...",
      "MYNEWRULE": "Description of what this rule checks for",  # NEW
  }
  ```
- [ ] Added test cases in `tests/lint/test_*.py`
- [ ] Run `rtllint --list-rules` and verify output includes your new rule
- [ ] Run full test suite: `python -m unittest discover -s tests -p 'test_*.py'`

## Format Guidelines

**Rule ID:** Uppercase, no spaces, 8-20 characters (e.g., `SENSINCOMPLETE`, `GENUNNAMED`)

**Description:** One sentence describing what the rule detects. Avoid technical jargon; write for RTL engineers. Examples:

- ✅ `"Signal(s) read but missing from sensitivity list in always @(...) block"`
- ✅ `"generate block contains an unlabeled 'begin' (missing ': label')"`
- ❌ `"sensitivity list completeness check"`
- ❌ `"flag unlabeled generates"`

## Notes on Verilator Rules

Custom checks in this tool have stable IDs (they don't change between versions). Verilator's built-in rules are version-dependent and should not be hardcoded into `LINT_RULES`. Users should consult verilator's own documentation (`verilator --lint-only -Wall <file>` or https://verilator.org/guide/latest/warnings.html).

## Example

Adding a hypothetical rule to flag unconstrained parameters:

```python
# src/rtl_aid/lint.py
LINT_RULES = {
    "SENSINCOMPLETE": "Signal(s) read but missing from sensitivity list in always @(...) block",
    "GENUNNAMED": "generate block contains an unlabeled 'begin' (missing ': label')",
    "PARAMUNCONSTRAINED": "Parameter has no default value and may cause elaboration issues",  # NEW
}

def check_unconstrained_params(text):
    """Flag parameters without default values."""
    issues = {}
    # ... implementation ...
    return issues
```

Then in the main() function's custom checks section:

```python
for ln, issue in {
    **check_sensitivity_completeness(source),
    **check_unlabeled_generate(source),
    **check_unconstrained_params(source),  # NEW
}.items():
    issues.setdefault(ln, issue)
```

Finally, add tests and verify:

```bash
rtllint --list-rules
```

Should now show:

```
rtllint custom rules:

  GENUNNAMED             generate block contains an unlabeled 'begin' (missing ': label')
  PARAMUNCONSTRAINED     Parameter has no default value and may cause elaboration issues
  SENSINCOMPLETE         Signal(s) read but missing from sensitivity list in always @(...) block
```
