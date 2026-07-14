#!/bin/bash

#
# Release Management Script for rtl-aid
#
# Orchestrates the full release workflow:
# 1. Queries PyPI for the current published version
# 2. Validates new version against current version
# 3. Confirms changes to version files
# 4. Confirms documentation updates
# 5. Builds distribution packages
# 6. Uploads to TestPyPI and PyPI
#
# Usage: ./scripts/release.sh
#

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYPROJECT_TOML="$PROJECT_ROOT/pyproject.toml"
INIT_PY="$PROJECT_ROOT/src/rtl_aid/__init__.py"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    printf "\n${BLUE}==== %s ====${NC}\n\n" "$1"
}

print_success() {
    printf "${GREEN}✓ %s${NC}\n" "$1"
}

print_error() {
    printf "${RED}✗ %s${NC}\n" "$1"
}

print_warning() {
    printf "${YELLOW}⚠ %s${NC}\n" "$1"
}

print_info() {
    printf "${BLUE}%s${NC}\n" "$1"
}

ask_yes_no() {
    local prompt="$1"
    local answer
    while true; do
        printf "${BLUE}%s${NC} (y/n) " "$prompt"
        read -r -n 1 answer
        printf "\n"
        case $answer in
            [Yy]) return 0 ;;
            [Nn]) return 1 ;;
            *) echo "Please answer y or n" ;;
        esac
    done
}

# Get version from PyPI API
get_pypi_version() {
    python3 << 'EOF'
try:
    import json
    import urllib.request
    response = urllib.request.urlopen('https://pypi.org/pypi/rtl-aid/json', timeout=5)
    data = json.loads(response.read().decode())
    print(data['info']['version'])
except Exception as e:
    print(f"unknown")
EOF
}

# Compare semantic versions
# Returns: 0 if $1 > $2, 1 if $1 <= $2
version_gt() {
    local new=$1
    local current=$2

    # If versions are equal, not greater
    if [[ "$new" == "$current" ]]; then
        return 1
    fi

    # Check if new is greater than current using sort -V
    [[ "$(printf '%s\n' "$current" "$new" | sort -V | head -n1)" == "$current" ]]
}

# Extract version from file
get_file_version() {
    grep -oP 'version = "\K[^"]+' "$PYPROJECT_TOML"
}

# Main script
main() {
    cd "$PROJECT_ROOT"

    print_header "rtl-aid Release Manager"

    # Get current published version from PyPI
    printf "Querying PyPI for current published version...\n"
    PYPI_VERSION=$(get_pypi_version)

    if [[ "$PYPI_VERSION" == "unknown" ]]; then
        print_warning "Could not reach PyPI (offline?). Using local pyproject.toml instead."
        PYPI_VERSION=$(get_file_version)
    fi

    printf "Published on PyPI: ${YELLOW}%s${NC}\n" "$PYPI_VERSION"
    printf "Local version in pyproject.toml: ${YELLOW}%s${NC}\n\n" "$(get_file_version)"

    # Ask for new version
    printf "${BLUE}Enter new version number:${NC} "
    read -r NEW_VERSION

    # Validate version format (basic check for X.Y.Z)
    if ! [[ "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        print_error "Invalid version format. Expected X.Y.Z (e.g., 0.2.1)"
        exit 1
    fi

    # Check if new version is greater than PyPI version
    if ! version_gt "$NEW_VERSION" "$PYPI_VERSION"; then
        print_error "New version ($NEW_VERSION) must be greater than published version ($PYPI_VERSION)"
        exit 1
    fi

    print_success "Version $NEW_VERSION is valid (greater than $PYPI_VERSION)"

    # Check version file updates
    print_header "Version Files Verification"

    echo "Files that need updating:"
    echo "  1. pyproject.toml       (version = \"...\")"
    echo "  2. src/rtl_aid/__init__.py  (__version__ = \"...\")"
    echo

    if ! ask_yes_no "Have you already updated both files with version $NEW_VERSION?"; then
        print_error "Please update the version files first, then run this script again"
        exit 1
    fi

    # Verify the files actually have the new version
    PYPROJECT_VERSION=$(get_file_version)
    INIT_VERSION=$(grep -oP '__version__ = "\K[^"]+' "$INIT_PY")

    if [[ "$PYPROJECT_VERSION" != "$NEW_VERSION" ]]; then
        print_error "pyproject.toml still has version $PYPROJECT_VERSION, expected $NEW_VERSION"
        exit 1
    fi

    if [[ "$INIT_VERSION" != "$NEW_VERSION" ]]; then
        print_error "src/rtl_aid/__init__.py still has version $INIT_VERSION, expected $NEW_VERSION"
        exit 1
    fi

    print_success "pyproject.toml has correct version"
    print_success "src/rtl_aid/__init__.py has correct version"

    # Check documentation updates
    print_header "Documentation Updates"
    echo "Have you updated/created the following?"
    echo "  - CHANGELOG or release notes (optional)"
    echo "  - README if needed (optional)"
    echo "  - TODO.md if needed (optional)"
    echo

    if ask_yes_no "Have you reviewed and updated any necessary documentation?"; then
        print_success "Documentation confirmed"
    else
        print_warning "Skipping documentation verification"
    fi

    # Build distributions
    print_header "Building Distribution Packages"

    if ! command -v python &> /dev/null; then
        print_error "Python is not installed"
        exit 1
    fi

    # Install build tools if needed
    printf "Installing/updating build tools...\n"
    python -m pip install --upgrade build twine -q

    printf "Building distribution packages for version %s...\n" "$NEW_VERSION"
    python -m build

    # Verify built artifacts
    WHEEL_FILE="dist/rtl_aid-${NEW_VERSION}-py3-none-any.whl"
    TAR_FILE="dist/rtl_aid-${NEW_VERSION}.tar.gz"

    if [[ ! -f "$WHEEL_FILE" ]] || [[ ! -f "$TAR_FILE" ]]; then
        print_error "Build artifacts not found. Expected:"
        echo "  $WHEEL_FILE"
        echo "  $TAR_FILE"
        exit 1
    fi

    print_success "Build artifacts created:"
    ls -lh "$WHEEL_FILE" "$TAR_FILE" | awk '{printf "  %s (%s)\n", $9, $5}'

    # TestPyPI upload
    print_header "TestPyPI Upload"

    if ask_yes_no "Upload to TestPyPI first (recommended)?"; then
        echo
        printf "Uploading %s to TestPyPI...\n" "$NEW_VERSION"
        printf "%s\n" "=================================================="

        if python -m twine upload --repository testpypi "dist/rtl_aid-${NEW_VERSION}."*; then
            print_success "TestPyPI upload successful!"
            printf "View at: https://test.pypi.org/project/rtl-aid/%s/\n" "$NEW_VERSION"
        else
            print_error "TestPyPI upload failed"
            exit 1
        fi
    else
        print_warning "Skipping TestPyPI upload"
    fi

    # PyPI upload
    print_header "PyPI (Production) Upload"

    if ask_yes_no "Upload to PyPI (production)?"; then
        echo
        printf "${YELLOW}This will make %s publicly available!${NC}\n" "$NEW_VERSION"
        if ask_yes_no "Are you absolutely sure?"; then
            printf "Uploading %s to PyPI...\n" "$NEW_VERSION"
            printf "%s\n" "=================================================="

            if python -m twine upload "dist/rtl_aid-${NEW_VERSION}."*; then
                print_success "PyPI upload successful!"
                printf "View at: https://pypi.org/project/rtl-aid/%s/\n" "$NEW_VERSION"
            else
                print_error "PyPI upload failed"
                exit 1
            fi
        else
            print_warning "PyPI upload cancelled"
            exit 0
        fi
    else
        print_warning "Skipping PyPI upload"
    fi

    # Final summary
    print_header "Release Complete!"
    printf "Version %s has been successfully released\n" "$NEW_VERSION"
    echo
    echo "Next steps:"
    echo "  1. Create a git tag: git tag -a v$NEW_VERSION -m 'Release v$NEW_VERSION'"
    echo "  2. Push to GitHub: git push origin v$NEW_VERSION"
    echo "  3. Create a GitHub release with changelog"
    echo
    echo "Users can now install with:"
    printf "  pip install rtl-aid==%s\n" "$NEW_VERSION"
}

# Run main
main "$@"
