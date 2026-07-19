# Test Coverage Reference

Quick lookup guide showing which tests cover which features. Total: **234 tests** across 4 directories.

---

## Core Features (`tests/core/`) — 116 tests

### `test_parsing.py` — 2 tests
**Port/parameter parsing and module dependency extraction**
- `TestParsingPortsAndParameters`: Port extraction with comma inheritance, dependency mapping

### `test_ci.py` — 2 tests
**CI validation and JSON graph export**
- `TestCiValidation`: Module validation (empty IO, self-instantiation), graph.json generation

### `test_markdown.py` — 1 test
**Markdown generation and idempotency**
- `TestMarkdownGenerationAndLogging`: File generation, change detection, idempotent runs

### `test_gaps.py` — 46 tests
**Regression suite: port width, parameters, attributes, and edge cases**
- `TestPortWidthsAndTypesRendered` (5): Basic widths, struct/enum types
- `TestParameterExpressionResolution` (2): Parameter literals, expression evaluation
- `TestLocalparamDistinction` (2): Parameter vs. localparam distinction
- `TestMacroDrivenPortsNotDropped` (3): Macro-defined port directions
- `TestBacktickAttributesNotCorruptPorts` (8): v0.2.2 regression — backtick attributes with commas
- `TestAttributeVariantsHandled` (10): Verilog attribute syntax variants
- `TestPortWidthsWithSpaces` (7): v0.2.3 regression — `[15 : 0]` width specifications with spaces
- `TestShuffledPortOrdering` (9): Interleaved input/output/inout declarations

### `test_json_graph_dir.py` — 15 tests
**JSON graph export with custom output directory**
- `TestJsonGraphDefaultBehavior` (4): Default output dir, flag combinations, file validation
- `TestJsonGraphFileParameter` (4): Custom file path, directory creation, idempotency
- `TestJsonGraphFileDryRun` (2): Dry-run mode (no file writes)
- `TestJsonGraphFileEdgeCases` (5): Empty graphs, absolute paths, structure preservation

### `test_export_dot.py` — 8 tests
**Graphviz DOT export for dependency graphs**
- `TestExportDot` (8): File creation, Graphviz syntax, node/edge inclusion, JSON→DOT conversion

### `test_builtin_functions.py` — 39 tests (Tier 2)
**SystemVerilog built-in function evaluation ($clog2, $bits, $size, $high)**
- `TestFunctionsConfigLoading` (6): Config loading, merging, user overrides, malformed config fallback
- `TestFunctionEvaluation` (5): $clog2, $bits, $size, $high evaluation with constant arguments
- `TestFunctionMarkdownOutput` (3): Display format showing both function and evaluated value
- `TestFunctionEdgeCases` (8): Zero/large values, non-integer args, undefined params, unresolved fallback
- `TestNestedFunctionCalls` (3): Nested evaluation, partial failures, bottom-up resolution
- `TestFunctionErrorHandling` (3): Missing functions, invalid arguments, graceful degradation
- `TestMalformedConfigFallback` (2): Config parse errors, invalid YAML
- `TestVerbosityLevelWarnings` (3): Warning output at different verbosity levels (-v, -vv)
- `TestFunctionConfigIntegration` (5): End-to-end workflow, config loading in scan(), markdown generation
- `TestFunctionDocumentation` (2): Config file format, usage examples

---

## Lint Features (`tests/lint/`) — 47 tests

### `test_parse_output.py` — 8 tests
**Verilator output parsing**
- `TestParseLintOutput`: Line extraction, file filtering, warning IDs, continuation lines

### `test_tag_file.py` — 10 tests
**File tagging with lint issues and idempotent headers**
- `TestTagFile` (8): Warning tags, issue IDs, header insertion, copyright block handling
- `TestTagFileDuplicateHeaders` (2): No duplicate headers when not in leading comment block

### `test_include_dirs.py` — 3 tests
**Include directory handling for verilator**
- `TestRunLintIncludeDirs`: `-I<dir>` format (no space), multiple directories

### `test_verilator_integration.py` — 2 tests
**Real verilator integration (requires installed verilator)**
- `TestIncludeDirEndToEnd`: Include paths resolve submodules, space-separated form fails

### `test_gaps.py` — 6 tests
**Custom lint checks beyond verilator**
- `TestSensitivityListCompleteness` (4): Missing signals in sensitivity lists, `always @*`/clocked exceptions
- `TestUnlabeledGenerateBlocks` (2): Unlabeled generate block detection

### `test_rtllint_command_tagging.py` — 18 tests
**rtllint command tagging (not verilator) in headers**
- `TestRtllintCommandInHeader` (4): Header contains `rtllint`, not `verilator`; preserves include dirs
- `TestRtllintCommandIdempotency` (3): No duplicates on re-run, preserves tb-test header
- `TestRtllintCommandUpdatesBehavior` (3): Command added/updated, different from verilator format
- `TestRtllintCommandEdgeCases` (8): No include dirs, absolute paths, special chars, multi-warning files

---

## Config Features (`tests/config/`) — ~70 tests (Tier 2)

### `test_config_discovery.py` — 8 tests
**Config file discovery and upward search**
- `TestConfigDiscovery` (7): Current dir, parent dir, grandparent dir, upward search, prefer nearest, stop at root, --config override
- `TestConfigFileDefaults` (1): Missing config uses CLI defaults

### `test_config_parsing.py` — 16 tests
**YAML parsing and validation**
- `TestConfigFileParsing` (6): rtldoc section, rtllint section, empty file, malformed YAML, combined sections, type coercion
- `TestConfigValidation` (10): Type validation (dir list, out string, verbose int/bool, ci bool), invalid types error, unknown options, mutually exclusive options

### `test_config_precedence.py` — 12 tests
**CLI args override config file**
- `TestConfigPrecedence` (12): CLI overrides for all options (dir, out, verbose, ci, exclude, json_graph, dry_run), config defaults when CLI not set, mutually exclusive handling

### `test_init_workflow_config.py` — 20 tests
**--init-workflow generates config files**
- `TestInitWorkflowGeneratesConfig` (7): Creates config file, valid YAML, template sections, no overwrite existing, no overwrite workflow, error messages, creates directories
- `TestInitWorkflowConfigContent` (5): Has rtldoc/rtllint sections, documentation comments, shows common options
- `TestInitWorkflowErrorHandling` (2): Permission errors, unwritable directory

### `test_config_integration.py` — ~14 tests
**End-to-end config feature integration**
- `TestRtldocWithConfigFile` (4): Reads config from current dir, CLI override, --config flag, all options processed
- `TestRtllintWithConfigFile` (3): Reads config, CLI override, all options processed
- `TestConfigSearchUpward` (3): Deep subdirectory search, prefer nearest, stop at first
- `TestConfigErrorHandling` (3): Malformed YAML errors, invalid types, missing --config errors

---

## Integration Tests (`tests/integration/`) — 10 tests

### `test_features_e2e.py` — 10 tests
**End-to-end feature validation**
- `TestJsonGraphFileFeatureE2E` (4): Custom file output, parent dir creation, dry-run mode
- `TestRtllintCommandTaggingFeatureE2E` (5): rtllint command in tags, include preservation, idempotency, inline tags
- `TestTier1ComprehensiveE2E` (1): All Tier 1 features working together (parsing, JSON graph, DOT export)

---

## Entry Points (`tests/`)

### `test_core.py`
**High-level import shim** — Re-exports all tests from `tests/core/*` for unified test discovery.

### `test_lint.py`
**High-level import shim** — Re-exports all tests from `tests/lint/*` for unified test discovery.

### `test_config.py`
**High-level import shim** — Re-exports all tests from `tests/config/*` for unified test discovery (Tier 2 feature).

---

## How to Find Tests for a Feature

| Feature | Test File(s) | Test Classes |
|---------|--------------|--------------|
| **Module parsing** | `core/test_parsing.py` | `TestParsingPortsAndParameters` |
| **Port widths/attributes** | `core/test_gaps.py` | `TestPortWidthsAndTypesRendered`, `TestBacktickAttributesNotCorruptPorts`, `TestPortWidthsWithSpaces` |
| **Parameters** | `core/test_gaps.py` | `TestParameterExpressionResolution`, `TestLocalparamDistinction` |
| **JSON graph export** | `core/test_ci.py`, `core/test_json_graph_dir.py` | `TestCiValidation`, `TestJsonGraphDefaultBehavior`, `TestJsonGraphFileParameter` |
| **DOT/Graphviz export** | `core/test_export_dot.py` | `TestExportDot` |
| **Markdown generation** | `core/test_markdown.py` | `TestMarkdownGenerationAndLogging` |
| **Verilator linting** | `lint/test_parse_output.py`, `lint/test_verilator_integration.py` | `TestParseLintOutput`, `TestIncludeDirEndToEnd` |
| **File tagging** | `lint/test_tag_file.py`, `lint/test_rtllint_command_tagging.py` | `TestTagFile`, `TestRtllintCommandInHeader`, `TestRtllintCommandIdempotency` |
| **Include directories** | `lint/test_include_dirs.py`, `lint/test_verilator_integration.py` | `TestRunLintIncludeDirs`, `TestIncludeDirEndToEnd` |
| **Sensitivity list checks** | `lint/test_gaps.py` | `TestSensitivityListCompleteness` |
| **Generate block validation** | `lint/test_gaps.py` | `TestUnlabeledGenerateBlocks` |
| **Config file discovery** | `config/test_config_discovery.py` | `TestConfigDiscovery`, `TestConfigFileDefaults` |
| **Config parsing & validation** | `config/test_config_parsing.py` | `TestConfigFileParsing`, `TestConfigValidation` |
| **Config file format** | `config/test_config_parsing.py` | `TestConfigFileParsing` |
| **CLI vs config precedence** | `config/test_config_precedence.py` | `TestConfigPrecedence` |
| **--init-workflow config generation** | `config/test_init_workflow_config.py` | `TestInitWorkflowGeneratesConfig`, `TestInitWorkflowConfigContent`, `TestInitWorkflowErrorHandling` |
| **Config integration** | `config/test_config_integration.py` | `TestRtldocWithConfigFile`, `TestRtllintWithConfigFile`, `TestConfigSearchUpward`, `TestConfigErrorHandling` |
| **Built-in functions** | `core/test_builtin_functions.py` | `TestFunctionEvaluation`, `TestFunctionMarkdownOutput`, `TestFunctionEdgeCases` |
| **Built-in function config** | `core/test_builtin_functions.py` | `TestFunctionsConfigLoading`, `TestMalformedConfigFallback` |
| **Nested function evaluation** | `core/test_builtin_functions.py` | `TestNestedFunctionCalls` |
| **Function error handling** | `core/test_builtin_functions.py` | `TestFunctionErrorHandling`, `TestFunctionEdgeCases` |

---

## Notes

- **Entry shims:** `tests/test_core.py` and `tests/test_lint.py` are import shims that consolidate all real tests for unified discovery via `python -m unittest`.
- **Fixtures:** Test data stored in `tests/core/fixtures/` and `tests/lint/fixtures/`, copied before mutation (non-destructive).
- **Run all:** `python -m unittest discover -s tests -p 'test_*.py'` (235 tests)
- **Skip integration tests:** Add `@unittest.skipUnless` for features requiring external tools (e.g., verilator).
- **Regression suite:** `tests/core/test_gaps.py` documents known parsing edge cases and v0.2.2/v0.2.3 fixes.
