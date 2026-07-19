# rtl-aid skill

Use this skill whenever you add, modify, or are asked to document a Verilog/SystemVerilog RTL file.
Also use it when asked to lint a file or check for Verilator warnings.

Primary value: index an unfamiliar RTL codebase without reading every file. Use generated docs and the JSON graph to navigate module hierarchy, understand interfaces, and locate problems — at a fraction of the token cost of reading raw Verilog.

---

## Tools

Both tools live in the project venv. Always activate it first:

```bash
source .venv/bin/activate
```

- **`rtldoc`** — generates and updates Markdown docs from RTL source
- **`rtllint`** — runs Verilator lint and tags warnings inline in source files

No Python runtime dependencies beyond PyYAML. `rtllint` requires verilator (system binary — `apt install verilator` / `brew install verilator`). If verilator is absent, `rtllint` exits 1 with install instructions; `rtldoc` is unaffected.

---

## rtldoc

### Syntax

```
rtldoc [--config FILE] (-d DIR [DIR...] | -f FILE [FILE...]) [-o OUT_DIR] [flags]
```

### Flags

| Flag | Effect |
|------|--------|
| `--config FILE` | Config file path (searches upward if not specified) |
| `--init-workflow` | Create `.rtl-aidrc.yml` and GitHub Actions workflow template |
| `-d DIR` | Scan directory recursively for `.v` / `.sv` |
| `-f FILE` | Parse specific files |
| `-o OUT_DIR` | Output directory (default: `temp/docs/modules`) |
| `--dry-run` | Show what would change, write nothing |
| `--ci` | Exit 1 if missing descriptions, no-IO modules, or self-instantiation |
| `--print-errors` | Print CI failures to stdout |
| `--json-graph` | Write dependency graph to `OUT_DIR/graph.json` |
| `--json-graph-file FILE` | Write graph to FILE instead of `OUT_DIR/graph.json` |
| `--export-dot FILE` | Export dependency graph as Graphviz DOT file |
| `--exclude STR` | Skip paths containing STR |
| `-v` / `-vv` | Verbose: file list / file list + section diffs |

### Outputs

**Per-module Markdown** at `OUT_DIR/<module_name>.md`. Sections always present: Description, Parameters, Inputs, Outputs, Inouts, Calls, Called By.

- `## Description` is user-managed — never overwritten; defaults to `TODO: Add description` on first generation.
- Vector ports show width: `data [7:0]`. Struct/enum-typed ports show the type name: `p (pair_t)`. Plain scalars show just the name.
- Parameters resolve simple integer arithmetic and common SV built-ins (`$clog2`, `$bits`, `$size`, `$high`) alongside the raw expression: `DERIVED = BASE * 2  (= 8)`. Unresolvable expressions are marked `(unresolved)`, never guessed. `localparam` entries are included, suffixed `(localparam)`.
- Any extra sections you add manually (e.g. `## State Machine`) are left alone.

**graph.json** (with `--json-graph` / `--json-graph-file`):

```json
{
  "module_name": {
    "calls": ["child_module_a", "child_module_b"],
    "called_by": ["parent_module"]
  }
}
```

**Graphviz DOT** (with `--export-dot FILE`): renderable with `dot -Tsvg graph.dot -o graph.svg`. Graph-only mode — convert an existing `graph.json` without rescanning source:

```bash
rtldoc --json-graph-file graph.json --export-dot graph.dot
```

**stdout summary** (always): `N module(s) processed — M doc(s) written, K unchanged`.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | CI checks failed (only with `--ci`) |

### Config file (`.rtl-aidrc.yml`)

`rtldoc` searches for `.rtl-aidrc.yml` in the current directory and parent directories (override with `--config FILE`).

```yaml
rtldoc:
  dir:
    - design/**/*.v      # Glob patterns expanded relative to config file location
    - rtl/*.v
  out: docs/modules      # Resolved relative to config file directory
  verbose: 0
  ci: false
  json_graph: false
  exclude:
    - testbench/
    - _tb.v

rtllint:
  file:
    - rtl/*.v
  include:
    - rtl/include/
```

**Key behaviors:**
- Relative paths resolve to the config file's location, not the current working directory. Absolute paths are used unchanged.
- CLI arguments always override config file values.
- Run `rtldoc --init-workflow` to scaffold a starter `.rtl-aidrc.yml` and a GitHub Actions workflow.
- Works from any subdirectory — paths still resolve correctly.

For multi-module projects with complex directory structures, a config file avoids repeated `-d` flags.

---

## Output directory

The project docs typically live in `docs/modules`. When using config, set `out: docs/modules` in `.rtl-aidrc.yml`. When running without config, **always pass `-o docs/modules`** or docs land in the default `temp/docs/modules`.

---

## When to run rtldoc

| Situation | Command |
|-----------|---------|
| Single file added or modified | `rtldoc -f rtl/path/to/file.v -o docs/modules` |
| Multiple files modified | `rtldoc -f rtl/a.v rtl/b.v -o docs/modules` |
| Full rescan (e.g. after a refactor that touches many files) | `rtldoc -d rtl/ -o docs/modules` |
| Also regenerate the dependency graph | add `--json-graph` |
| Export graph as Graphviz DOT | add `--export-dot graph.dot` |
| Custom graph output location | add `--json-graph-file custom/path/graph.json` |
| Preview without writing anything | add `--dry-run` |
| See which files changed | add `-v` |
| See which sections changed within each file | add `-vv` |
| No flags, project has a config file | `rtldoc` — auto-discovers `.rtl-aidrc.yml` via upward search |

### After generating a new module doc

Open the generated `docs/modules/<module>.md` and fill in the `## Description` section. rtldoc will never overwrite it.

---

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
| `--list-rules` | List all custom rule IDs and exit |

### What rtllint checks

1. Everything verilator's `--lint-only -Wall` flags.
2. Two rtl-aid-native checks verilator doesn't perform:
   - `SENSINCOMPLETE` — an `always @(sig, ...)` block (explicit list, not `@*`, not clocked) reads a signal missing from its own sensitivity list
   - `GENUNNAMED` — a `generate` block contains an unlabeled `begin` (no `: label`)

A verilator finding on a given line always takes priority over a custom-check finding on the same line.

### What rtllint does to the source file

1. Inserts `// lint-test: <command>` and `// tb-test: tba` headers after the leading comment block (once, idempotent).
2. Appends `/* Check: message */` to each warned line — or `/* Check[ID]: message */` when a stable rule ID is available (verilator's own dashed category, e.g. `WIDTHEXPAND`, or `SENSINCOMPLETE`/`GENUNNAMED`).
3. Re-running replaces existing `/* Check: */` tags — does not stack them.

```bash
# See issues without modifying the file
rtllint rtl/path/to/file.v --dry-run

# Tag issues inline (idempotent — re-running updates existing tags)
rtllint rtl/path/to/file.v

# If the file uses `include with headers in another dir
rtllint rtl/path/to/file.v -I rtl/include/
```

`--dry-run` stdout:
```
rtl/module.v: 3 issue(s) would be tagged:
  Line 42: Operator EQ expects 32 bits on the LHS ...
  Line 87: Signal is not used: 'temp_wire'
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | No issues found |
| 1 | One or more warnings/errors found |

### What to do with Check tags

- Fix the underlying issue in the RTL.
- Re-run rtllint to confirm the tag disappears (exit 0 = clean).
- Do not remove tags manually unless you are deliberately suppressing a known false positive.

---

## Standard workflow (modify an existing RTL file)

```bash
source .venv/bin/activate

# 1. Lint the file — fix any Check-tagged lines
rtllint rtl/path/to/module.v
# fix issues in source, then re-run until exit 0

# 2. Regenerate the doc
rtldoc -f rtl/path/to/module.v -o docs/modules -vv
```

## Standard workflow (add a new RTL file)

```bash
source .venv/bin/activate

# 1. Lint the new file
rtllint rtl/path/to/new_module.v

# 2. Generate its doc (also rebuild graph so new module appears)
rtldoc -f rtl/path/to/new_module.v -o docs/modules --json-graph -vv

# 3. Open the generated doc and write the Description section
# docs/modules/new_module.md  →  replace "TODO: Add description" with real text
```

## Agentic patterns

Understand a codebase without reading source:
```bash
rtldoc -d rtl/ -o .agent/docs/ --json-graph
```
Then read `.agent/docs/<module>.md` for any module and `graph.json` for the full dependency map.

Check if docs are in sync before editing:
```bash
rtldoc -d rtl/ -o docs/ --dry-run
```
Zero "would be written" = docs are current.

Preview impact of a source change:
```bash
rtldoc -f rtl/changed_module.v -o docs/ --dry-run -vv
```
Shows exactly which sections would change.

Find all lint issues in a file without reading it:
```bash
rtllint --dry-run rtl/module.v
```
Returns line numbers and messages — jump directly to flagged lines.

---

## CI check (do not run routinely — only when asked)

```bash
rtldoc -d rtl/ -o docs/modules --ci --print-errors
```

Exits 1 if any module has: missing description, no IO, or self-instantiation.

---

## Known limitations (do not work around — just be aware)

- One module parsed per file (first `module` block only); pre-2001 Verilog port style (`input clk;` inside body) is not parsed.
- SV interfaces and packages are not extracted; `typedef` port types are shown by name only (e.g. `p (pair_t)`) — the typedef's own definition is not resolved or flattened.
- `` `define `` is substituted before parsing, but only within a single file — `` `include ``-based macro sharing across files is not supported.
- rtllint line-number tagging may be imprecise inside macro expansions (guarded, not fatal).
- Descriptions are always hand-written — rtldoc does not parse doc-comments from RTL source (by design: comments are often multi-line, multi-style, or vendor-autogenerated rather than documentation).
- Testbench files are auto-excluded from scanning: `_tb.v`, `_tb.sv`, `_bench.v`, `_testbench.v` and `.sv` variants.
