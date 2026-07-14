# Project: Veridoc (rtl-aid)

**Purpose:** CI-native documentation generator for Verilog/RTL codebases. Auto-generates markdown module docs and dependency graphs from SystemVerilog source.

**Team:** FPGA/ASIC engineers. Solves: stale docs, poor module visibility, painful onboarding.

## Project Structure

```
veridoc/
├── src/rtl_aid/                    # Main package
│   ├── cli.py                      # CLI entry points (rtldoc, rtllint)
│   ├── core.py                     # VerilogWikiParser: parse → scan → generate
│   └── lint.py                     # Linting: verilator integration + custom checks
├── tests/                          # Test suite (181 tests)
│   ├── core/                       # Core feature tests (43)
│   ├── lint/                       # Lint feature tests (129)
│   └── integration/                # E2E integration tests (9)
├── TESTING.md                      # How testing works
├── CLAUDE.md                       # This file
└── TODO.md                         # Feature backlog
```

## Key Modules

### `core.py` — VerilogWikiParser
The heart of rtldoc. Single class:

**Main flow:**
1. `scan()` — Walk paths, extract modules + dependencies
   - Regex parse module headers, ports, parameters
   - Extract instantiations (which modules call which)
   - Build `self.modules` dict and `self.called_by` reverse map
2. `generate_markdown()` — Write module docs
   - Diff-aware: preserves existing Description sections
   - Tracks changes (added/removed ports) for verbose logging
3. `write_json()` — Export dependency graph as JSON
   - Only runs if `--json-graph` flag
   - Writes to `json_graph_dir` (or output dir if unset)
4. `run_ci_checks()` — Validate module structure
   - Each module must have inputs/outputs (no IO = error)
   - No self-instantiation allowed

**Key methods:**
- `extract_module_and_ports()` — Parse module header + ports/params
- `extract_calls()` — Find module instantiations
- `parse_existing_sections()` — Read existing markdown to preserve user edits
- `diff_lists()` — Track what changed between runs

### `lint.py` — Verilator Integration + Custom Checks
Wraps verilator for linting; adds checks verilator's `-Wall` misses.

**Main flow:**
1. `_run_lint()` — Call verilator, capture output
2. `parse_lint_output()` — Parse verilator's text output into issues dict
3. Custom checks run **after** verilator:
   - `check_sensitivity_completeness()` — Find missing signals in sensitivity lists
   - `check_unlabeled_generate()` — Flag generate blocks without labels
4. `tag_file()` — Write issues inline as comments + add headers

**Key methods:**
- `_strip_comments()` — Remove comments before regex scanning (avoids false positives)
- `_find_always_block()` — Locate the block following `always @(...)` (handles nested begin/end)
- `tag_file()` — Idempotent file tagging
  - Adds `// lint-test: rtllint ...` header after copyright/comments
  - Updates if already present (no duplication)
  - Tags each warned line with `/* Check[ID]: message */`

## Recent Changes (This Session)

### Feature 1: rtldoc `--json-graph-dir`
- **What:** Optional flag to specify custom directory for `graph.json` output
- **Where:** `cli.py` (argparse), `core.py` (VerilogWikiParser, write_json)
- **Behavior:** 
  - Default (no flag): writes to output directory
  - With flag: writes to specified directory
  - Empty string or None: falls back to output directory
  - Dry-run: identifies directory but doesn't create it

### Feature 2: rtllint Command Tagging
- **What:** Tag files with rtllint command instead of verilator in headers
- **Where:** `lint.py` (tag_file, main)
- **Behavior:**
  - Format: `// lint-test: rtllint -I<dir1> -I<dir2> ... <filepath>`
  - Idempotent: re-running updates the command, doesn't duplicate
  - Updates only: existing lint-test line + replaces old command

## Code Style & Conventions

- **No premature abstractions:** 3+ similar lines is acceptable
- **Comments only for WHY:** Non-obvious constraints, hidden invariants, workarounds
- **Error handling:** Only at system boundaries (user input, file I/O, external tools)
- **Regexes:** Patterns are named constants at module level for readability
- **Fixtures:** Test data stored in `tests/*/fixtures/`, copied before mutation via `copy_fixture()`

## How Things Work

### Parsing Verilog
Uses regex (no full parser — intentional for simplicity):
- Module extraction: `r"module\s+(\w+)..."`
- Port parsing: Split on commas, detect input/output/inout keywords
- Instantiation detection: `r"\b(\w+)\s*(?:#\s*\(.*?\))?\s+\w+\s*\("`

**Limitations:**
- No support for `include` files (passes through `resolve_defines()` only)
- Assumes single module per file (extracts first match only)
- No support for generate blocks with parameters

### Verilator Integration
- Calls: `verilator --lint-only -Wall -I<dir> <file>`
- Output format: `%Warning-TYPE: path:line:col: message` (parsed via regex)
- Workaround: Verilator 5.048+ requires `-I<dir>` (no space) — hardcoded in `_run_lint()`

### Idempotent Operations
- `write_json()` can be called repeatedly; overwrites `graph.json`
- `tag_file()` can be called repeatedly; updates existing headers in place
- `generate_markdown()` preserves user-edited sections (Description), only updates managed sections

## Testing

**Philosophy:** Behavior-first TDD. Tests are blind to implementation; focus on user-facing behavior.

**Structure:** See `TESTING.md` for full details.
- Unit tests: single feature per test
- Integration tests: cross-module E2E verification
- Fixtures: immutable test data, copied before each test

**Run:** `python -m unittest discover -s tests -p 'test_*.py'` (181 tests)

## Debugging

### "File not found" during lint
Check:
1. File exists at the path passed
2. Include directories (`-I`) are correct
3. Verilator is installed: `verilator --version`

### Module not found in docs
Check:
1. File is `.v` or `.sv` (not `_tb.v` or `_testbench.sv`)
2. Module is in a scanned directory/file list
3. Module header is valid: `module <name> #(...) (...);`

### Sensitivity list warnings not flagged
`check_sensitivity_completeness()` doesn't flag:
- `always @*` (wildcard sensitivity)
- `always @(posedge clk)` (clocked block)
- Blocks with all signals listed

See `test_gaps.py` for examples.

## Future Improvements (from TODO.md)

- Multi-file `include` resolution
- SystemVerilog interface/modport extraction
- Formal property checking integration
- Cross-repo module dependencies
- Interactive dependency graph visualization

---

**Last updated:** July 2026  
**Tests:** 181 passing (43 core, 129 lint, 9 integration)  
**Key files to modify:**
- Features on rtldoc: `src/rtl_aid/cli.py`, `src/rtl_aid/core.py`
- Features on rtllint: `src/rtl_aid/lint.py`
- Tests: `tests/{core,lint,integration}/test_*.py`
