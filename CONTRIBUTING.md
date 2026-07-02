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
  test_core.py  Thin entry point — re-exports everything from tests/core/
  test_lint.py  Thin entry point — re-exports everything from tests/lint/
  support.py    Shared fixture-loading helpers
  core/
    fixtures/         .v/.sv fixture files used by core tests
    test_parsing.py   Port/parameter/dependency extraction
    test_ci.py        --ci checks, --json-graph
    test_markdown.py  Doc generation, idempotency
    test_gaps.py       Known-gap regression tests (see "TDD gap tests" below)
  lint/
    fixtures/                     .v fixture files used by lint tests
    test_parse_output.py         verilator-output parsing
    test_tag_file.py             inline tagging / header insertion
    test_include_dirs.py         -I flag command construction (mocked subprocess)
    test_gaps.py                  Known-gap regression tests
    test_verilator_integration.py Real-verilator end-to-end checks (skipped if verilator absent)

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

Most tests run without verilator or any external dependencies — they exercise the parser and file-tagging logic in isolation, mocking the subprocess call where needed. The exception is `tests/lint/test_verilator_integration.py`, which shells out to a real `verilator` to prove behavior that's specific to verilator's actual CLI parsing (e.g. the `-I` flag) — those tests `skipUnless(shutil.which("verilator"))` and are silently skipped if verilator isn't installed, so the suite as a whole never requires it.

Note: `python -m unittest discover tests/ -v` recurses into `tests/core/` and `tests/lint/` directly *and* runs them again via the `tests/test_core.py`/`tests/test_lint.py` re-export wrappers, so each test appears to run twice under two different qualified names. This is expected — it's the tradeoff of keeping thin top-level entry points via `import *` re-export rather than dropping them in favor of bare `discover` recursion.

### Fixtures, not inline source

RTL source used by a test belongs in that suite's `fixtures/` directory as a real `.v`/`.sv` file, not built inline with `f.write(...)`/tempfile string literals. Reasons: it's readable as actual RTL, it's reusable across tests, and diffs on fixture changes are easy to review. If a test needs to *mutate* a file (e.g. `tag_file`), copy the fixture into a `tempfile.TemporaryDirectory()` first via `tests/support.copy_fixture()` — never mutate the checked-in fixture.

### TDD gap tests

`tests/core/test_gaps.py` and `tests/lint/test_gaps.py` hold tests written *before* their corresponding fix, asserting the correct/desired behavior (not the current one) for known gaps tracked in `TODO.md`. When one of these was red and is now green, the fix has landed — see `TODO.md` and `checklist.md` for the current status of each. New known gaps should get a test here first, red, before the fix.

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

- Add a test case (with a fixture file under `tests/core/fixtures/`, ideally in `test_gaps.py`) that reproduces the failure before touching `core.py`. It should fail first, then pass once the fix lands.
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
