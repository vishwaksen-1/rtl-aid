# AGENTS.md - rtl-aid

Machine-readable reference for AI agents and agentic workflows.

## What this is

Two CLI tools for Verilog/SystemVerilog RTL projects:

- `rtldoc` — generates per-module Markdown docs from source. Extracts ports, parameters, and instantiation graph. Diff-aware: only rewrites changed files. Safe to run on every commit.
- `rtllint` — runs verilator lint on a file, plus two rtl-aid-native checks (incomplete sensitivity lists, unlabeled `generate` blocks) verilator's `-Wall` doesn't cover, and tags each warned line inline with `/* Check: message */` (or `/* Check[ID]: message */` when a rule ID is available). Idempotent. Does not block builds.

Primary agentic value: index an unfamiliar RTL codebase without reading every file. Use docs and the JSON graph to navigate module hierarchy, understand interfaces, and locate problems — at a fraction of the token cost of reading raw Verilog.

## Install

```
pip install rtl-aid
```

No Python runtime dependencies. Requires Python 3.7+. `rtllint` requires verilator (system binary — `apt install verilator` / `brew install verilator`). If verilator is absent, `rtllint` exits 1 with install instructions; `rtldoc` is unaffected.

## rtldoc

### Syntax

```
rtldoc (-d DIR [DIR...] | -f FILE [FILE...]) [-o OUT_DIR] [flags]
```

### Flags

| Flag | Effect |
|------|--------|
| `-d DIR` | Scan directory recursively for .v / .sv |
| `-f FILE` | Parse specific files |
| `-o OUT_DIR` | Output directory (default: temp/docs/modules) |
| `--dry-run` | Show what would change, write nothing |
| `--ci` | Exit 1 if missing descriptions, no-IO modules, or self-instantiation |
| `--print-errors` | Print CI failures to stdout |
| `--json-graph` | Write dependency graph to OUT_DIR/graph.json |
| `--exclude STR` | Skip paths containing STR |
| `-v` / `-vv` | Verbose: file list / file list + section diffs |

### Outputs

**Per-module Markdown** at `OUT_DIR/<module_name>.md`

Sections always present: Description, Parameters, Inputs, Outputs, Inouts, Calls, Called By.

`Description` is user-managed — never overwritten. All other sections are auto-generated.

**Port entries** include width/type detail when available:
- Vector port: `data [7:0]`
- Struct/enum-typed port (typedef'd, not a base type): `p (pair_t)`, `st (state_t)`
- Plain scalar port: just the name, e.g. `clk`

**Parameter entries** resolve simple integer arithmetic alongside the raw expression: `DERIVED = BASE * 2  (= 8)`. Unresolvable expressions are marked `(unresolved)`, never guessed. `localparam` entries are included, suffixed `(localparam)`.

**graph.json** (with `--json-graph`):

```json
{
  "module_name": {
    "calls": ["child_module_a", "child_module_b"],
    "called_by": ["parent_module"]
  }
}
```

**stdout summary** (always):

```
N module(s) processed — M doc(s) written, K unchanged
```

**Log file** (when docs are modified): path printed to stdout. Contains modified file list and section diffs.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | CI checks failed (only with `--ci`) |

### Agentic patterns

Understand a codebase without reading source:
```
rtldoc -d rtl/ -o .agent/docs/ --json-graph
```
Then read `.agent/docs/<module>.md` for any module and `graph.json` for the full dependency map.

Check if docs are in sync before editing:
```
rtldoc -d rtl/ -o docs/ --dry-run
```
Zero "would be written" = docs are current.

Enforce documentation completeness in CI:
```
rtldoc -d rtl/ -o docs/ --ci --print-errors
```

Preview impact of a source change:
```
rtldoc -f rtl/changed_module.v -o docs/ --dry-run -vv
```
Shows exactly which sections would change.

## rtllint

### Syntax

```
rtllint FILE [FILE...] [-I DIR] [--dry-run] [-v]
```

### Flags

| Flag | Effect |
|------|--------|
| `-I DIR` | Include directory for verilator (repeatable) |
| `--dry-run` | Show issues per line, write nothing |
| `-v` | Print full verilator output |

### Output

Runs `verilator --lint-only -Wall`, then merges in two rtl-aid-native checks that verilator doesn't perform:
- `SENSINCOMPLETE` — an `always @(sig, ...)` block (explicit list, not `@*`, not clocked) reads a signal missing from its own sensitivity list
- `GENUNNAMED` — a `generate` block contains an unlabeled `begin` (no `: label`)

A verilator finding on a given line always takes priority over a custom-check finding on the same line.

Modifies source file in-place:
- Appends `/* Check: message */` to each warned line — or `/* Check[ID]: message */` when a rule ID is available (verilator's own dashed category, e.g. `WIDTHEXPAND`, or one of the two IDs above)
- Inserts `// lint-test: <command>` and `// tb-test: tba` after the leading comment block
- Re-running replaces existing `/* Check: */` tags — does not stack

`--dry-run` stdout:
```
rtl/module.v: 3 issue(s) would be tagged:
  Line 42: Operator EQ expects 32 bits on the LHS ...
  Line 87: Signal is not used: 'temp_wire'
  Line 103: ...
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | No issues found |
| 1 | One or more warnings/errors found |

### Agentic patterns

Find all lint issues in a file without reading it:
```
rtllint --dry-run rtl/module.v
```
Returns line numbers and messages. Agent can jump directly to flagged lines.

Tag and surface lint debt for code review:
```
rtllint rtl/module.v
```
`/* Check: */` comments are then searchable with grep or any code search tool.

## Key behaviors for agents

- **Testbench files are auto-excluded**: `_tb.v`, `_tb.sv`, `_bench.v`, `_testbench.v` and `.sv` variants
- **Idempotent**: running either tool twice on unchanged input produces no changes
- **Diff-aware writes**: rtldoc never writes a file unless content changed — safe to run unconditionally
- **Structured JSON output**: `--json-graph` produces machine-parseable dependency data
- **First run on a legacy codebase**: use `--dry-run` first to preview scope, then run without it

## Limitations agents should know

- One module parsed per file (first `module` block only)
- Pre-2001 Verilog port style not supported
- SystemVerilog interfaces, packages are not extracted; `typedef` port types are shown by name only (e.g. `p (pair_t)`) — the typedef's own definition is not resolved or flattened
- `` `define `` is substituted before parsing, but only within a single file — `` `include ``-based macro sharing across files is not supported
- rtllint line-number tagging may be imprecise inside macro expansions (guarded, not fatal)
- rtllint's custom checks (`SENSINCOMPLETE`, `GENUNNAMED`) are regex-based on a single file's text, same precision tier as the rest of the parser — not a full elaborator
