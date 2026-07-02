import os
import shutil

_TESTS_DIR = os.path.dirname(__file__)

CORE_FIXTURES = os.path.join(_TESTS_DIR, "core", "fixtures")
LINT_FIXTURES = os.path.join(_TESTS_DIR, "lint", "fixtures")


def copy_fixture(fixtures_dir, name, dest_dir):
    """Copy a fixture file into dest_dir and return the new path.

    Tools under test (tag_file, rtldoc writes) mutate files in place, so
    tests must never point them at the checked-in fixture directly.
    """
    src = os.path.join(fixtures_dir, name)
    dst = os.path.join(dest_dir, os.path.basename(name))
    shutil.copy(src, dst)
    return dst
