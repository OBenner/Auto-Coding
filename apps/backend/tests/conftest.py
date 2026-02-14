"""
Pytest configuration for backend tests.
"""
import sys
from pathlib import Path

# Add apps/backend to path for imports
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
