"""
Pytest configuration for tests directory.

This ensures that the backend package is importable from tests.
CRITICAL: This runs BEFORE any test module imports, so we can fix sys.path here.
"""

import sys
from pathlib import Path

# CRITICAL: Remove any tests directories from sys.path to prevent import conflicts
# pytest adds tests/ and tests/context/ to sys.path, which causes Python to
# try importing from tests.context instead of the actual context module
tests_dirs = [p for p in sys.path if "tests" in p and "context" in p]
for td in tests_dirs[:]:  # Use slice copy to modify during iteration
    if td in sys.path:
        sys.path.remove(td)

# Add the parent directory (apps/backend) to the FRONT of sys.path
# so that 'from context.token_estimator import TokenEstimator' imports from
# apps/backend/context/token_estimator.py, not tests/context/token_estimator.py
_backend_root = Path(__file__).parent.parent
_backend_root_str = str(_backend_root)

# Remove if already present, then add to front
if _backend_root_str in sys.path:
    sys.path.remove(_backend_root_str)
sys.path.insert(0, _backend_root_str)
