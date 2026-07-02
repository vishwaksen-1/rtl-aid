"""High-level entry point for lint.py tests — real tests live in tests/lint/."""
from tests.lint.test_parse_output import *  # noqa: F401,F403
from tests.lint.test_tag_file import *  # noqa: F401,F403
from tests.lint.test_include_dirs import *  # noqa: F401,F403
from tests.lint.test_gaps import *  # noqa: F401,F403
from tests.lint.test_verilator_integration import *  # noqa: F401,F403

if __name__ == "__main__":
    import unittest

    unittest.main()
