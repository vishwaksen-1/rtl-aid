# Project: Veridoc (rtl-aid)

**Purpose:** CI-native documentation generator for Verilog/RTL codebases. Auto-generates markdown module docs + dependency graphs. Wraps verilator linting + adds custom checks.

## Project Structure

```
src/rtl_aid/
├── cli.py          # CLI: rtldoc, rtllint entry points
├── core.py         # VerilogWikiParser (scan, generate_markdown, write_json, export_dot)
└── lint.py         # Verilator wrapper + custom checks (sensitivity, unlabeled generate)

tests/              # 235 tests organized by feature
├── core/           # Module parsing, markdown gen, JSON graph
├── lint/           # Verilator output parsing, file tagging, custom checks
└── integration/    # E2E workflows
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
   - Writes to `json_graph_file` path (or output_dir/graph.json if unset)
   - Creates parent directories automatically
4. `export_dot()` — Export dependency graph as Graphviz DOT
   - Called via `--export-dot FILE` flag
   - Can run standalone: read existing graph.json, output DOT (no scanning)
5. `run_ci_checks()` — Validate module structure
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


## Code Style & Conventions

- **No premature abstractions:** 3+ similar lines is acceptable
- **Comments only for WHY:** Non-obvious constraints, hidden invariants, workarounds
- **Error handling:** Only at system boundaries (user input, file I/O, external tools)
- **Regexes:** Patterns are named constants at module level for readability
- **Fixtures:** Test data stored in `tests/*/fixtures/`, copied before mutation via `copy_fixture()`
- **Testing:** Always use project test infrastructure (fixtures in `tests/*/fixtures/`); do NOT create ad-hoc temp files or test files outside the test suite. If fixtures are inadequate, add to the project's test data instead.

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

**Run:** `python -m unittest discover -s tests -p 'test_*.py'` (235 tests)

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

# Creating Agents:
Pass the agents relevant docs (TESTING.md, TODO.md, RULEBOOK.md, etc. according to the thing they're working on) along with the context they need for their work. Agents can be given a subset of the docs to focus on specific tasks, such as linting, documentation generation, or test coverage.

---

**Last updated:** July 2026  
**Tests:** 235 passing (73 core, 47 lint, 15 integration)

**Key files:**
- Core features: `src/rtl_aid/cli.py`, `src/rtl_aid/core.py`
- Linting: `src/rtl_aid/lint.py`
- Tests: See `docs/tests/TEST_COVERAGE.md` for quick lookup
