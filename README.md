# rtl-aid

CI-native documentation layer for RTL projects.

Parses Verilog/SystemVerilog source files, extracts module structure, and generates Markdown documentation that stays in sync with your RTL — automatically.

---

## Tools

| Command | Purpose |
|---------|---------|
| `rtldoc` | Generate and maintain module documentation |
| `rtllint` | Run verilator lint and tag warnings inline in source |

---

## Installation

```bash
pip install rtl-aid
```

Or from source:

```bash
git clone https://github.com/vishwaksen-1/rtl-aid
cd rtl-aid
pip install -e .
```

**Requirements**

- Python 3.7+
- `rtllint` requires [verilator](https://verilator.org) — a system binary, not installable via pip:

```bash
# Debian / Ubuntu
sudo apt install verilator

# macOS
brew install verilator
```

`rtldoc` has no external dependencies. If verilator is missing, `rtllint` will exit with a clear error and install instructions.

---

## rtldoc

### Quick start

```bash
# Document all modules in a directory
rtldoc -d rtl/

# Document specific files
rtldoc -f rtl/core/alu.v rtl/core/decoder.v

# Custom output directory
rtldoc -d rtl/ -o docs/modules/
```

### What gets generated

For each module, a Markdown file is created or updated:

```markdown
# alu

## Description
TODO: Add description

## Parameters
- DATA_WIDTH = 8
- OP_WIDTH = 4

## Inputs
- clk
- rst
- op [OP_WIDTH-1:0]
- operand_a [DATA_WIDTH-1:0]
- operand_b [DATA_WIDTH-1:0]

## Outputs
- result [DATA_WIDTH-1:0]
- overflow

## Calls
- [mux4](mux4.md)

## Called By
- [cpu_core](cpu_core.md)
```

The `Description` section is **never overwritten** — you write it once, rtldoc preserves it on every run. All other sections are auto-managed.

### Port and parameter detail

- **Vector ports** show their packed width next to the name: `operand_a [DATA_WIDTH-1:0]`.
- **Struct- or enum-typed ports** (typedef'd, not a base type) show the type name instead: `p (pair_t)`, `st (state_t)`.
- **Plain scalar ports** (`input logic clk`) render as just the name — no width or type to add.
- **Parameters** resolve simple integer arithmetic and show both the raw expression and the resolved value: `DERIVED = BASE * 2  (= 8)`. Anything rtldoc can't resolve (sized literals, unknown references, non-arithmetic expressions) is marked `(unresolved)` rather than guessed at.
- **`localparam`** entries are listed alongside `parameter`s, suffixed `(localparam)` to distinguish them: `DEPTH = WIDTH*2  (= 16) (localparam)`.

### CLI reference

```
rtldoc (-d DIR [DIR...] | -f FILE [FILE...]) [options]

Input:
  -d, --dir DIR [DIR...]    Recursively scan directories for .v / .sv files
  -f, --file FILE [FILE...]  Parse specific files (no directory traversal)

Output:
  -o, --out OUT_DIR          Output directory (default: temp/docs/modules)
  --json-graph               Write dependency graph to graph.json

Filtering:
  --exclude PATTERN [...]    Exclude paths containing any of these strings

Run modes:
  --dry-run                  Show what would be written without touching files
  --ci                       Fail (exit 1) on missing descriptions, no-IO modules,
                             or self-instantiations
  --print-errors             Print CI issues to stdout (in addition to the error log)

Verbosity:
  -v                         Print modified file paths
  -vv                        Print modified files + section-level diffs (+adds/-removals)
```

### CI integration

```yaml
# .github/workflows/docs.yml
- name: Check RTL docs
  run: rtldoc -d rtl/ -o docs/modules/ --ci --print-errors
```

Exit codes: `0` = clean, `1` = CI check failed.

Testbench files (`_tb.v`, `_tb.sv`, `_bench.v`, `_testbench.v`, and `.sv` variants) are automatically excluded from scanning.

### Dry run

Preview what would change before committing:

```bash
rtldoc -d rtl/ --dry-run
```

```
[DRY RUN] Would write:
  docs/modules/alu.md
  docs/modules/decoder.md

5 module(s) processed — 2 doc(s) would be written, 3 unchanged
```

### Dependency graph

```bash
rtldoc -d rtl/ --json-graph -o docs/modules/
```

Writes `docs/modules/graph.json`:

```json
{
  "cpu_core": {
    "calls": ["alu", "decoder", "register_file"],
    "called_by": []
  },
  "alu": {
    "calls": ["mux4"],
    "called_by": ["cpu_core"]
  }
}
```

---

## rtllint

Runs `verilator --lint-only -Wall` on a file, plus two rtl-aid-native checks verilator's `-Wall` doesn't cover, and tags each warned line with an inline comment. Useful for tracking lint debt without blocking a build.

**Beyond verilator**, rtllint also flags:
- Incomplete sensitivity lists — `always @(a) y = a & b;` with `b` missing from the list
- Unlabeled `generate` blocks — `generate ... begin ... end ... endgenerate` with no `: label`

Both run directly on the source text, independent of the verilator subprocess call.

### Usage

```bash
rtllint rtl/core/alu.v

# With include directories
rtllint -I rtl/includes -I rtl/common rtl/core/alu.v

# Multiple files
rtllint rtl/core/*.v

# Preview without modifying files
rtllint --dry-run rtl/core/alu.v
```

### What gets written

Given a verilator warning on line 75:

```
%Warning-WIDTHEXPAND: rtl/alu.v:75:12: Operator ADD generates 9 bits ...
```

rtllint modifies `alu.v` in place:

```verilog
// lint-test: verilator --lint-only -Wall rtl/alu.v
// tb-test: tba
...
assign result = a + b;  /* Check[WIDTHEXPAND]: Operator ADD generates 9 bits ... */
```

When a rule ID is available — verilator's own (e.g. `WIDTHEXPAND`) or rtl-aid's custom checks (`SENSINCOMPLETE`, `GENUNNAMED`) — the tag includes it as `/* Check[ID]: message */` so it can be cited when suppressing or grepped for later. A bare `%Error` with no dashed ID falls back to plain `/* Check: message */`.

Re-running rtllint replaces existing `/* Check: */` tags — it does not stack duplicates.

### CLI reference

```
rtllint FILE [FILE...] [options]

  -I, --include DIR    Add include directory (repeatable)
  --dry-run            Show issues without modifying files
  -v                   Print full verilator output
```

Exit codes: `0` = no issues found, `1` = one or more warnings/errors.

---

## Design principles

- **No heavy dependencies** — stdlib only, no parser frameworks
- **CI-first** — every flag is designed for scripted use
- **Safe for teams** — manual descriptions are never overwritten
- **Diff-aware** — files are only touched when content actually changes

---

## Supported syntax

| Feature | Status |
|---------|--------|
| Verilog-2001 (`.v`) | Supported |
| SystemVerilog (`.sv`) | Supported (port/param parsing) |
| ANSI port declarations | Supported |
| Comma-inherited port direction (`output reg a, b`) | Supported |
| Parameterised modules (`#(parameter ...)`) | Supported |
| `localparam` (distinguished from `parameter`) | Supported |
| Simple integer parameter expressions (`BASE * 2`) | Supported (resolved alongside the raw expression) |
| Port widths and struct/enum types in generated docs | Supported |
| `` `define `` macro substitution before parsing | Supported (single-file only) |
| `` `include `` across files | Not supported |
| Module instantiations with `#()` param override | Supported |
| Testbench auto-exclusion | Supported |
| Pre-2001 Verilog style | Not supported |
| Multi-module files | Not supported (first module only) |
