"""
Verification test for signature_parser module.
This test verifies that the parse_function_signature function works correctly.
"""

from merge.signature_parser import parse_function_signature

# Test case from the subtask verification
sig = parse_function_signature('def foo(x: int, y: str) -> bool:')
assert sig.name == 'foo', f"Expected 'foo', got '{sig.name}'"
assert sig.params == ['x', 'y'], f"Expected ['x', 'y'], got {sig.params}"
assert sig.return_type == 'bool', f"Expected 'bool', got '{sig.return_type}'"

print("✓ All verification tests passed")
print(f"  Function name: {sig.name}")
print(f"  Parameters: {sig.params}")
print(f"  Return type: {sig.return_type}")
