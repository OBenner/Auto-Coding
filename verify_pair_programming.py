#!/usr/bin/env python3
"""Verification script for pair_programming module."""

import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent / "apps" / "backend"
sys.path.insert(0, str(backend_dir))

# Import and verify
from agents.pair_programming import PairProgrammingAgent

print("OK")
