# rtl-aid

**Docs and lint for Verilog/SystemVerilog that actually stay in sync with your RTL.**

`rtl-aid` gives hardware projects the CI-native tooling that software has had for years: auto-generated module docs that update themselves, a dependency graph of your design, and a lint layer that catches what verilator's `-Wall` doesn't.

```bash
pip install rtl-aid
```

---

## Why

- **Docs that don't rot.** `rtldoc` regenerates per-module Markdown from source on every commit — ports, parameters, and the calls graph — while leaving your hand-written descriptions untouched.
- **Zero config needed, real config supported.** Run it with just `-d rtl/`, or drop a `.rtl-aidrc.yml` in your repo root and just run `rtldoc`.
- **Lint debt you can see.** `rtllint` wraps verilator and tags every warning inline in the source (`/* Check[WIDTHEXPAND]: ... */`), plus two checks verilator misses: incomplete sensitivity lists and unlabeled `generate` blocks.
- **Built for CI, not just humans.** `--ci` fails the build on undocumented or structurally broken modules. `--dry-run` previews changes. Everything is diff-aware and idempotent — safe to run unconditionally on every commit.
- **No heavy dependencies.** Stdlib-only regex parser (plus PyYAML for config files) — no tree-sitter, no full elaborator, nothing to compile.

## Quick start

```bash
# Generate docs for every module in a directory
rtldoc -d rtl/ -o docs/modules/

# Lint a file and tag warnings inline
rtllint rtl/core/alu.v
```

`rtldoc` writes one Markdown file per module:

```markdown
# alu

## Description
TODO: Add description

## Parameters
- DATA_WIDTH = 8

## Inputs
- clk
- operand_a [DATA_WIDTH-1:0]

## Outputs
- result [DATA_WIDTH-1:0]

## Calls
- [mux4](mux4.md)
```

The `Description` section is yours — write it once, `rtldoc` never touches it again.

## What's supported

Verilog-2001 and SystemVerilog port/parameter parsing, ANSI ports, `localparam`, simple parameter arithmetic (`BASE * 2`), common SV built-in functions (`$clog2`, `$bits`, `$size`, `$high`), struct/enum-typed ports, `.rtl-aidrc.yml` config files, JSON + Graphviz DOT graph export, and CI-mode exit codes. Testbenches are auto-excluded from scanning.

**Requirements:** Python 3.7+. `rtllint` additionally needs [verilator](https://verilator.org) (`apt install verilator` / `brew install verilator`) — `rtldoc` has no external tool dependency.

## Learn more

- Full CLI reference, config file format, and usage patterns for LLM agents: [`SKILLS.md`](SKILLS.md)
- Contributing / dev setup: [`CONTRIBUTING.md`](CONTRIBUTING.md)

## License

MIT
