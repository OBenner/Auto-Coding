"""Simple test to verify run_qa_reviewer can be imported."""
import os
os.environ['AI_ENGINE_PROVIDER'] = 'claude'

# Try to import
try:
    from qa.reviewer import run_qa_reviewer
    print("OK")
except ImportError as e:
    print(f"FAIL: {e}")
    exit(1)
