# Testing Guide

## Test Organization

Tests are organized by module and organized into focused units:

```
tests/
├── __init__.py
├── test_core.py              # Entry point for core tests
├── test_lint.py              # Entry point for lint tests
├── support.py                # Test utilities (fixture handling)
├── core/                      # Core feature tests
│   ├── fixtures/             # Test data files for core
│   ├── test_parsing.py        # Module/port extraction
│   ├── test_gaps.py           # Custom lint rules
│   ├── test_ci.py             # CI mode behavior
│   ├── test_markdown.py        # Markdown generation
│   └── test_json_graph_dir.py # --json-graph-dir feature
├── lint/                      # Lint feature tests
│   ├── fixtures/             # Test data files for lint
│   ├── test_parse_output.py    # Verilator output parsing
│   ├── test_tag_file.py        # File tagging logic
│   ├── test_gaps.py            # Sensitivity & unlabeled generate
│   ├── test_include_dirs.py    # Include directory handling
│   ├── test_verilator_integration.py  # End-to-end lint
│   └── test_rtllint_command_tagging.py # rtllint command feature
└── integration/              # Cross-module integration tests
    └── test_features_e2e.py  # End-to-end feature verification
```

## Running Tests

**All tests:**
```bash
python -m unittest discover -s tests -p 'test_*.py'
```

**By module:**
```bash
python -m unittest tests.test_core      # All core tests (43 tests)
python -m unittest tests.test_lint      # All lint tests (129 tests)
python -m unittest tests.integration.test_features_e2e  # Integration tests (9 tests)
```

**Specific test class:**
```bash
python -m unittest tests.core.test_json_graph_dir.TestJsonGraphDirParameter -v
```

**Specific test:**
```bash
python -m unittest tests.lint.test_rtllint_command_tagging.TestRtllintCommandInHeader.test_lint_test_header_contains_rtllint_not_verilator
```

## Fixture Files

Fixture files are pre-built test data stored in `fixtures/` subdirectories:

### Core Fixtures (`tests/core/fixtures/`)
- Used by markdown generation and parsing tests
- Examples: Verilog files with various module structures, parameter types, etc.

### Lint Fixtures (`tests/lint/fixtures/`)
- Used by file tagging and output parsing tests
- Examples: `tag_target_empty.v`, `tag_target_basic.v` — files used by `tag_file()` tests

**Important:** Fixtures must be copied before modification. Use `support.copy_fixture()`:
```python
from tests.support import LINT_FIXTURES, copy_fixture

path = copy_fixture(LINT_FIXTURES, "tag_target_basic.v", tmpdir)
# Now safe to modify path
tag_file(path, ...)
```

## Test Style Patterns

### Unit Tests (Feature-focused)
Focus on a single behavior. Example:
```python
def test_json_graph_dir_creates_directory_if_not_exists(self):
    """--json-graph-dir should create directory if it doesn't exist."""
    # Test only: directory creation for non-existent paths
```

### Integration Tests (Cross-module E2E)
Verify features work end-to-end with real file I/O. Located in `tests/integration/`:
```python
def test_custom_dir_writes_only_to_custom(self):
    """With --json-graph-dir, graph.json goes only to custom directory."""
    # Verify full feature works: CLI arg → VerilogWikiParser → write_json → file I/O
```

### Testing Philosophy

- **Behavior-first:** Tests describe expected user-facing behavior, not implementation details
- **Isolated:** Each test is independent; no test should depend on another
- **Repeatable:** Tests use temporary directories (`tempfile.TemporaryDirectory`)
- **Blind to implementation:** Tests verify what happens, not how it happens

## Adding New Tests

**Before writing a new test, check [`docs/tests/TEST_COVERAGE.md`](../docs/TEST_COVERAGE.md)** to see if the feature is already covered. This prevents duplicate test work and guides placement of new tests.

1. **Unit test:** Add to appropriate `tests/core/test_*.py` or `tests/lint/test_*.py`
2. **Integration test:** Add to `tests/integration/test_features_e2e.py`
3. **With fixtures:** Create fixture file in `core/fixtures/` or `lint/fixtures/`, use `copy_fixture()`

### Template
```python
import unittest
import tempfile
from rtl_aid.core import VerilogWikiParser  # or other module

class TestFeatureName(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
    
    def test_expected_behavior(self):
        """One sentence describing expected behavior."""
        # Arrange
        # Act
        # Assert
```

## Test Count Summary (v0.2.8)

- **Core tests:** 121 (49 new: markdown output handling, DOT parent dirs, circular deps, large ports)
- **Lint tests:** 43 (unchanged)
- **Config tests:** 80 (70 existing + 10 new: CLI edge cases, nested paths, special characters)
- **Integration tests:** 10 (unchanged)
- **Total:** 254 tests

### v0.2.8 Additions

**Edge Case Tests** (`tests/config/test_cli_edge_cases.py` — 10 new)
- DOT/JSON export with nested output paths (parent dir auto-creation)
- Paths with spaces in directory names
- Mixed absolute/relative paths in config
- Graph-only export mode (--json-graph-file + --export-dot without rescanning)

**Markdown Enhancements** (`tests/core/test_markdown.py` — 3 new)
- Nested output directory creation
- Dry-run mode (verify no files written)
- Large port lists (50+ ports) without truncation

**DOT Export Enhancements** (`tests/core/test_export_dot.py` — 2 new)
- Parent directory creation for nested output paths
- Circular dependency handling (A→B→A without infinite loops)

### Bug Fixed in v0.2.8
**DOT Export missing parent directory creation** — Added `os.makedirs()` before file writes in `export_dot()` and `export_dot_from_file()` (src/rtl_aid/core.py lines 565, 583). Resolves FileNotFoundError when using nested output paths like `--export-dot output/nested/graph.dot`.
