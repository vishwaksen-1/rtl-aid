"""High-level entry point for config feature tests — real tests live in tests/config/."""
from tests.config.test_config_discovery import *  # noqa: F401,F403
from tests.config.test_config_parsing import *  # noqa: F401,F403
from tests.config.test_config_precedence import *  # noqa: F401,F403
from tests.config.test_init_workflow_config import *  # noqa: F401,F403
from tests.config.test_config_integration import *  # noqa: F401,F403

if __name__ == "__main__":
    import unittest
    unittest.main()
