#!/usr/bin/env python
"""Test script for pattern library generator."""

import sys
import tempfile
from pathlib import Path

# Add apps/backend to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend"))

from integrations.graphiti.pattern_library_generator import PatternLibraryGenerator

# Test generation
g = PatternLibraryGenerator(".")
output_file = tempfile.mktemp(suffix=".py")
g.generate_library_file(output_file, "python", {})
print("OK")
