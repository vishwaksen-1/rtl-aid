# Quick Start: Running Config Tests

## Run All Config Tests

```bash
cd /home/vishwaksen/vishwaksen/atp/dummy/veridoc

# All config tests
python -m unittest tests.test_config -v

# Or discover all
python -m unittest discover -s tests/config -p 'test_*.py' -v
```

## Run Specific Test Modules

```bash
# Config discovery tests
python -m unittest tests.config.test_config_discovery -v

# Config parsing tests
python -m unittest tests.config.test_config_parsing -v

# Config precedence tests
python -m unittest tests.config.test_config_precedence -v

# Init workflow tests
python -m unittest tests.config.test_init_workflow_config -v

# Integration tests
python -m unittest tests.config.test_config_integration -v
```

## Run Specific Test Classes

```bash
# Test config file upward search
python -m unittest tests.config.test_config_discovery.TestConfigDiscovery -v

# Test YAML parsing
python -m unittest tests.config.test_config_parsing.TestConfigFileParsing -v

# Test config validation
python -m unittest tests.config.test_config_parsing.TestConfigValidation -v

# Test CLI precedence
python -m unittest tests.config.test_config_precedence.TestConfigPrecedence -v

# Test init-workflow generation
python -m unittest tests.config.test_init_workflow_config.TestInitWorkflowGeneratesConfig -v
```

## Run Single Test

```bash
# Example: Config discovery in current directory
python -m unittest tests.config.test_config_discovery.TestConfigDiscovery.test_find_config_in_current_directory -v
```

## Run All Tests (Including Existing)

```bash
# All tests across core, lint, and config
python -m unittest discover -s tests -p 'test_*.py' -v

# Or use entry points
python -m unittest tests.test_core tests.test_lint tests.test_config -v
```

## Expected Initial Status

These tests will **FAIL** until the feature is implemented:

```
FAIL: test_find_config_in_current_directory
ModuleNotFoundError: No module named 'rtl_aid.config'
```

This is expected! The tests define the expected behavior. Follow the implementation guide in `TIER2_CONFIG_TESTS.md` to make them pass.

## Implementation Checklist

Track progress as you implement `rtl_aid/config.py`:

- [ ] Create `rtl_aid/config.py`
- [ ] Implement `ConfigError` exception class
- [ ] Implement `find_config_file()` — config discovery
- [ ] Test: `python -m unittest tests.config.test_config_discovery -v`
- [ ] Implement `parse_config()` — YAML parsing
- [ ] Implement `validate_config()` — validation
- [ ] Test: `python -m unittest tests.config.test_config_parsing -v`
- [ ] Implement `merge_config_with_args()` — CLI override
- [ ] Test: `python -m unittest tests.config.test_config_precedence -v`
- [ ] Add `--config FILE` to CLI
- [ ] Implement config loading in `cli.py` and `lint.py`
- [ ] Implement `init_workflow()` config generation
- [ ] Test: `python -m unittest tests.config.test_init_workflow_config -v`
- [ ] Run integration tests
- [ ] Test: `python -m unittest tests.config.test_config_integration -v`
- [ ] Run full test suite
- [ ] Test: `python -m unittest discover -s tests -p 'test_*.py' -v`

## Fixture Files

Test config files are in `tests/config/fixtures/`:

```
fixtures/
├── rtldoc-valid.yml              # Valid rtldoc config
├── rtllint-valid.yml             # Valid rtllint config
├── combined-valid.yml            # Both rtldoc + rtllint
├── malformed.yml                 # Invalid YAML
├── invalid-types.yml             # Wrong option types
├── single-values.yml             # Coercion test (single → list)
├── empty.yml                     # Empty config
├── unknown-keys.yml              # Unknown options
└── rtl-aidrc-template.yml        # Template for --init-workflow
```

Use these in tests by reading them:

```python
from pathlib import Path

fixture_dir = Path(__file__).parent / "fixtures"
config = (fixture_dir / "rtldoc-valid.yml").read_text()
```

## Reference Documentation

- `README.md` — Comprehensive test guide
- `TIER2_CONFIG_TESTS.md` — Feature design and test summary
- `../../docs/TEST_COVERAGE.md` — Updated test coverage reference

---

**Status:** Tests ready for implementation (TDD mode)  
**Expected pass rate:** 0% initially, 100% after feature implementation
