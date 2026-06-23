# Contributing

Contributions are welcome. This document covers how to set up the project, run tests, and submit changes.

---

## Setup

```bash
git clone https://github.com/your-org/rtl-aid
cd rtl-aid
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

For `rtllint` development, verilator must be installed:

```bash
# Debian / Ubuntu
apt install verilator

# macOS
brew install verilator
```

---

## Project structure

```
src/rtl_aid/
  core.py       VerilogWikiParser — parse, scan, generate docs
  cli.py        rtldoc CLI entry point
  lint.py       rtllint CLI entry point
  __init__.py

tests/
  test_core.py  Tests for core doc generation
  test_lint.py  Tests for lint output parsing and file tagging

docs/
  specs.md      Formal specification
  graph_schema.json  JSON schema for --json-graph output

examples/
  USB4-project/ Real-world Verilog/SV example project
```

---

## Running tests

```bash
python -m unittest discover tests/ -v
```

All tests run without verilator or any external dependencies. Tests in `test_lint.py` exercise the parser and file-tagging logic in isolation — the subprocess call to verilator is not tested.

---

## Coding conventions

- **No external runtime dependencies.** Everything must work with the Python standard library. Dev/test dependencies are fine but must not be required for the package itself.
- **Keep `core.py` and `lint.py` self-contained.** Avoid creating abstractions just to share a few lines between them.
- **Diff-safe by default.** Any change to `generate_markdown` must preserve the property that a second run on unchanged RTL produces zero file writes.
- **No silent failures.** Parsing failures (unrecognised file, no module found) should be handled gracefully and surfaced — not swallowed.
- **Comments only when the why is non-obvious.** No docstrings restating the function name; no commented-out code.

---

## Adding a feature

1. Check `SKILLS.md` — if it is listed under "Planned / not yet implemented", it is fair game.
2. Open an issue first for anything that changes parsing behaviour or CI exit codes — these affect existing users.
3. Write tests before or alongside the implementation. The test suite uses `unittest` with no additional frameworks.
4. Run the full test suite before submitting.
5. If the change adds a new CLI flag, update:
   - The relevant `argparse` block in `cli.py` or `lint.py`
   - `README.md` CLI reference section
   - `SKILLS.md` capability table
   - `docs/specs.md` if it affects documented behaviour

---

## Fixing a parser bug

The parser is regex-based and will have edge cases. When fixing one:

- Add a test case that reproduces the failure before touching `core.py`.
- Check that `test_markdown_generation_and_logging` still passes — it verifies the idempotency guarantee.
- Run against the `examples/USB4-project/` directory to catch regressions on real RTL:

```bash
rtldoc -d examples/USB4-project/design --dry-run
```

---

## Submitting a pull request

- Keep PRs focused — one feature or one bug fix per PR.
- Title: imperative present tense (`Add --stat flag`, `Fix parameter type stripping`).
- Include a brief description of what changed and why.
- All tests must pass.

---

## What is out of scope

- Parser rewrites using heavy dependencies (pyverilog, tree-sitter) — these may become an optional backend, but the default parser must stay stdlib-only.
- HTML generation or web serving — out of scope for this tool; use the JSON graph output and pipe it into a renderer.
- Windows-specific path handling — patches welcome but not a priority.
