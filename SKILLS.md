# rtl-aid skill

Use this skill whenever you add, modify, or are asked to document a Verilog/SystemVerilog RTL file.
Also use it when asked to lint a file or check for Verilator warnings.

---

## Tools

Both tools live in the project venv. Always activate it first:

```bash
source .venv/bin/activate
```

- **`rtldoc`** — generates and updates Markdown docs from RTL source
- **`rtllint`** — runs Verilator lint and tags warnings inline in source files

---

## Critical: always pass `-o docs/modules`

The default output directory is `temp/docs/modules`. The project docs live in `docs/modules`.
**Every rtldoc invocation must include `-o docs/modules`** or docs land in the wrong place.

---

## When to run rtldoc

| Situation | Command |
|-----------|---------|
| Single file added or modified | `rtldoc -f rtl/path/to/file.v -o docs/modules` |
| Multiple files modified | `rtldoc -f rtl/a.v rtl/b.v -o docs/modules` |
| Full rescan (e.g. after a refactor that touches many files) | `rtldoc -d rtl/ -o docs/modules` |
| Also regenerate the dependency graph | add `--json-graph` → writes `docs/modules/graph.json` |
| Preview without writing anything | add `--dry-run` |
| See which files changed | add `-v` |
| See which sections changed within each file | add `-vv` |

### What rtldoc manages (auto-updated from source):
- Parameters, Inputs, Outputs, Inouts, Calls, Called By
- Vector ports show their width (`data [7:0]`); struct/enum-typed ports show the type name (`p (pair_t)`); plain scalar ports show just the name
- Parameters resolve simple integer arithmetic alongside the raw expression (`DERIVED = BASE * 2  (= 8)`); unresolvable expressions are marked `(unresolved)`
- `localparam` entries are listed too, suffixed `(localparam)` to distinguish them from `parameter`

### What rtldoc never touches:
- The `## Description` section — preserved as-is once written; defaults to `TODO: Add description` on first generation
- Any extra sections you add manually (e.g. `## State Machine`, `## Notes`) — left alone

### After generating a new module doc:
Open the generated `docs/modules/<module>.md` and fill in the `## Description` section. rtldoc will never overwrite it.

---

## When to run rtllint

Run rtllint on any RTL file you have just edited or created, before updating its doc.

```bash
# See issues without modifying the file
rtllint rtl/path/to/file.v --dry-run

# Tag issues inline (idempotent — re-running updates existing tags)
rtllint rtl/path/to/file.v

# If the file uses `include with headers in another dir
rtllint rtl/path/to/file.v -I rtl/include/
```

### What rtllint checks:
1. Everything verilator's `--lint-only -Wall` flags
2. Two rtl-aid-native checks verilator doesn't perform: incomplete sensitivity lists (`always @(a) y = a & b;` missing `b`) and unlabeled `generate` blocks (missing `: label`)

### What rtllint does to the source file:
1. Inserts `// lint-test: verilator --lint-only -Wall <file>` header (once, idempotent)
2. Inserts `// tb-test: tba` header placeholder (once, idempotent)
3. Appends `/* Check: <message> */` at the end of any warned line — or `/* Check[ID]: <message> */` when a stable rule ID is available (verilator's own, e.g. `WIDTHEXPAND`, or rtl-aid's own `SENSINCOMPLETE`/`GENUNNAMED`)
4. Re-running replaces existing `/* Check: */` tags — does not stack them

### What to do with Check tags:
- Fix the underlying issue in the RTL
- Re-run rtllint to confirm the tag disappears (exit 0 = clean)
- Do not remove tags manually unless you are deliberately suppressing a known false positive

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

---

## CI check (do not run routinely — only when asked)

```bash
rtldoc -d rtl/ -o docs/modules --ci --print-errors
```

Exits 1 if any module has: missing description, no IO, or self-instantiation.

---

## Known limitations (do not work around — just be aware)

- Pre-2001 Verilog port style (`input clk;` inside body) is not parsed
- Only the first `module` block in a file is parsed
- SV interfaces and packages are not extracted; `typedef` port types are shown by name only (e.g. `p (pair_t)`) — the typedef's own definition is not resolved
- `` `define `` is substituted before parsing, but only within a single file — `` `include ``-based macro sharing across files is not supported
- Descriptions are always hand-written — rtldoc does not parse doc-comments from RTL source (decided by design: comments are often multi-line, multi-style, or vendor-autogenerated rather than documentation)
