# Scripts

Utility scripts for project maintenance and releases.

## release.sh

Automated release management script for publishing new versions to PyPI.

### Features

- **Version validation:** Checks that new version is greater than current version
- **File verification:** Confirms version updates in `pyproject.toml` and `src/rtl_aid/__init__.py`
- **Documentation check:** Reminds you to update docs before release
- **Build automation:** Creates distribution packages (wheel + tar.gz)
- **Two-stage upload:** Upload to TestPyPI first for validation, then to PyPI
- **User confirmations:** Asks for explicit confirmation before each major step

### Usage

```bash
./scripts/release.sh
```

### Workflow

1. **Prepare:** Update version in `pyproject.toml` and `src/rtl_aid/__init__.py`
2. **Run script:** `./scripts/release.sh`
3. **Enter version:** Type the new version number (e.g., `0.2.2`)
4. **Confirm updates:** Tell the script you've already updated version files
5. **Review docs:** Confirm any documentation updates
6. **Build:** Script builds distribution packages automatically
7. **TestPyPI:** Upload to test repository first (recommended)
8. **PyPI:** Upload to production after validation

### Version Format

Versions must follow semantic versioning: `X.Y.Z` (e.g., `0.2.1`)

The script validates that the new version is greater than the current version.

### Requirements

- Python 3.7+
- `build` package: `pip install build`
- `twine` package: `pip install twine`
- PyPI/TestPyPI credentials configured in `~/.pypirc`

### Troubleshooting

**"Invalid version format"**
- Version must be in X.Y.Z format (e.g., 0.2.1)

**"New version must be greater than current"**
- The new version must be higher than the current version
- Check that you're using correct semantic versioning

**"Build artifacts not found"**
- The `build` package may not be installed
- Run: `pip install --upgrade build`

**"twine: command not found"**
- The `twine` package is not installed
- Run: `pip install twine`

**PyPI upload fails with authentication error**
- Credentials not configured in `~/.pypirc`
- See: https://packaging.python.org/guides/publishing-package-distribution-releases-using-twine/

### Notes

- The script uses semantic versioning and validates version ordering
- TestPyPI upload is recommended before production PyPI upload
- All confirmations require explicit user action (y/n)
- The script stops on first error and provides clear error messages
