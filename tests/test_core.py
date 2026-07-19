"""High-level entry point for core.py tests — real tests live in tests/core/."""
from tests.core.test_parsing import *  # noqa: F401,F403
from tests.core.test_ci import *  # noqa: F401,F403
from tests.core.test_markdown import *  # noqa: F401,F403
from tests.core.test_gaps import *  # noqa: F401,F403
from tests.core.test_export_graph import *  # noqa: F401,F403

if __name__ == "__main__":
    import unittest

    unittest.main()
