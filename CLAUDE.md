# Project: Veridoc (rtl-aid)

**Purpose:** CI-native documentation generator for Verilog/RTL codebases. Auto-generates markdown module docs + dependency graphs. Wraps verilator linting + adds custom checks.

## Project Structure

```
src/rtl_aid/
├── cli.py              # CLI: rtldoc, rtllint entry points; config loading + merge
├── core.py             # VerilogWikiParser (scan, generate_markdown, write_json, export_dot)
├── lint.py             # Verilator wrapper + custom checks (sensitivity, unlabeled generate)
├── config/
│   ├── __init__.py     # find_config_file, parse_config, validate_config, merge_config_with_args
│   └── functions.yaml  # Packaged defaults for SV built-in function resolution
├── functions.py         # Loads/merges functions.yaml, evaluates $clog2/$bits/$size/$high etc.
├── sv_builtin_functions.py  # Built-in function implementations used by functions.py
└── templates/           # Templates for --init-workflow (.rtl-aidrc.yml, GitHub Actions workflow)

tests/                  # 254 tests organized by feature
├── core/               # Module parsing, markdown gen, JSON graph, DOT export, builtin functions
├── lint/               # Verilator output parsing, file tagging, custom checks
├── config/             # Config file discovery, parsing, precedence, glob patterns, CLI integration
└── integration/        # E2E workflows
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

### `config/__init__.py` — Config File Support (`.rtl-aidrc.yml`)
Lets `rtldoc`/`rtllint` read defaults from a YAML config file instead of (or alongside) CLI flags.

**Main flow:**
1. `find_config_file()` — Search upward from CWD for `.rtl-aidrc.yml` (or use `--config FILE`)
2. `parse_config()` / `validate_config()` — Load YAML, check shape
3. `merge_config_with_args()` — CLI args always take precedence over config values
4. In `cli.py`: relative paths (dirs, globs, `-o`) resolve against the **config file's directory**, not CWD
5. `create_config_file()` — Backs `--init-workflow`, which also writes a GitHub Actions template from `templates/`

### `functions.py` / `sv_builtin_functions.py` — SV Built-in Function Resolution
Used by `core.py` when evaluating parameter expressions (e.g. `parameter W = $clog2(DEPTH)`) so generated docs show resolved values, not raw expressions.

- `load_packaged_functions()` — Loads `config/functions.yaml` (default function defs: `$clog2`, `$bits`, `$size`, `$high`, ...)
- `merge_user_functions()` — Merges a user-supplied functions config over the packaged defaults
- `evaluate_builtin_function()` — Evaluates a single function call given known parameter values
- `resolve_parameter_with_functions()` — Entry point `core.py` calls to resolve a parameter expression end-to-end

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

### Config Files
- `rtldoc` searches upward from CWD for `.rtl-aidrc.yml` (override with `--config FILE`); `rtllint` supports the same
- CLI flags always override config file values
- Relative paths in the config (dirs, globs, `-o`) resolve relative to the **config file's location**, not the CWD `rtldoc` is invoked from
- `rtldoc --init-workflow` scaffolds both `.rtl-aidrc.yml` and `.github/workflows/rtl-checks.yml` from `templates/`

### CLI Flags (rtldoc) — beyond `-d`/`-f`/`-o`/`-v`/`--ci`
| Flag | Effect |
|------|--------|
| `--config FILE` | Explicit config file path |
| `--init-workflow` | Scaffold `.rtl-aidrc.yml` + GitHub Actions workflow, then exit |
| `--json-graph` | Write dependency graph JSON |
| `--json-graph-file FILE` | Custom path for graph JSON (default: `<out>/graph.json`) |
| `--export-dot FILE` | Export dependency graph as Graphviz DOT (can run standalone against an existing `graph.json`, no scan needed) |
| `--exclude PATH...` | Skip paths containing any of these substrings |
| `--dry-run` | Show what would change without writing files |
| `--print-errors` | Print CI errors to stdout in addition to the log file |

`rtllint` also takes `-I/--include DIR` (repeatable, passed to verilator), `--list-rules`, and `--dry-run`.

## Testing

**Philosophy:** Behavior-first TDD. Tests are blind to implementation; focus on user-facing behavior.
**environment:** Local python venv [`.venv`](.venv).

**Structure:** See `TESTING.md` for full details.
- Unit tests: single feature per test
- Integration tests: cross-module E2E verification
- Fixtures: immutable test data, copied before each test

**Run:** `python -m unittest discover -s tests -p 'test_*.py'` (254 tests: 121 core, 43 lint, 80 config, 10 integration)

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
**Tests:** 254 passing (121 core, 43 lint, 80 config, 10 integration)

**Key files:**
- Core features: `src/rtl_aid/cli.py`, `src/rtl_aid/core.py`
- Config file support: `src/rtl_aid/config/__init__.py`
- SV built-in function resolution: `src/rtl_aid/functions.py`, `src/rtl_aid/sv_builtin_functions.py`
- Linting: `src/rtl_aid/lint.py`
- Tests: See `docs/TEST_COVERAGE.md` for quick lookup
