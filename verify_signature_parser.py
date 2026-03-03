#!/usr/bin/env python3
"""Verification script for signature_parser module."""

import sys
sys.path.insert(0, 'apps/backend')

from merge.signature_parser import parse_function_signature

# Test the exact case from the subtask verification
sig = parse_function_signature('def foo(x: int, y: str) -> bool:')

# Verify the expected output
if sig.name == 'foo':
    print('SUCCESS')
    sys.exit(0)
else:
    print(f'FAILED: Expected "foo" but got "{sig.name}"')
    sys.exit(1)
