#!/usr/bin/env python3
"""Quick verification script for analytics platform components."""

import sys
import json
from pathlib import Path

# Add cli to path
sys.path.insert(0, str(Path(__file__).parent / 'apps' / 'backend'))

def test_json_output():
    """Test JSON output module."""
    from cli.json_output import format_build_result, BuildStatus
    from cli.exit_codes import ExitCode

    result = format_build_result(
        BuildStatus.SUCCESS,
        'test-spec',
        ExitCode.SUCCESS,
        120.5
    )
    parsed = json.loads(result)
    assert parsed['status'] == 'success'
    assert parsed['exitCode'] == 0
    print('✅ JSON output format is valid')
    return True

def test_exit_codes():
    """Test exit codes module."""
    from cli.exit_codes import ExitCode

    assert ExitCode.SUCCESS == 0
    assert ExitCode.BUILD_FAILED == 1
    assert ExitCode.QA_FAILED == 2
    assert ExitCode.SYSTEM_ERROR == 3
    print('✅ Exit codes module is correct')
    return True

def test_model_locks_manager():
    """Test model locks manager exists and is importable."""
    import subprocess
    result = subprocess.run(
        ['python', 'apps/backend/scripts/model_locks_manager.py', '--help'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert 'Commands:' in result.stdout
    print('✅ Model locks manager CLI is functional')
    return True

if __name__ == '__main__':
    print('Running E2E verification of analytics platform...\n')

    tests = [
        ('Exit Codes Module', test_exit_codes),
        ('JSON Output Module', test_json_output),
        ('Model Locks Manager CLI', test_model_locks_manager),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            print(f'Testing {name}...')
            test_func()
            passed += 1
            print()
        except Exception as e:
            print(f'❌ {name} failed: {e}\n')
            failed += 1

    print(f'\n{"="*60}')
    print(f'Tests passed: {passed}/{len(tests)}')
    print(f'Tests failed: {failed}/{len(tests)}')
    print(f'{"="*60}')

    if failed > 0:
        sys.exit(1)
    else:
        print('\n✅ All E2E verification tests passed!')
        sys.exit(0)
