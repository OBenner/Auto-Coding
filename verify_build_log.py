#!/usr/bin/env python3
"""
Verification script for subtask-4-2: Build log artifact generation

This script demonstrates that build log artifacts are correctly generated
when using --ci --json flags.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend"))

from cli.artifacts import ArtifactManager


def verify_artifact_manager():
    """Verify that ArtifactManager can create build logs."""
    print("=" * 70)
    print("Verifying Build Log Artifact Generation")
    print("=" * 70)
    print()

    # Create a temporary test directory
    test_dir = Path(__file__).parent / ".auto-claude" / "specs" / "test-artifacts"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create artifact manager
    manager = ArtifactManager(spec_dir=test_dir, enabled=True)
    print(f"✓ Artifact manager created: {manager.artifact_dir}")
    print()

    # Test build log creation
    build_log_data = {
        "status": "success",
        "duration": 120.5,
        "exitCode": 0,
        "changedFiles": ["src/main.py", "tests/test_main.py"],
        "filesChanged": 2,
        "metadata": {
            "model": "claude-sonnet-4-5-20250929",
            "workspaceMode": "isolated",
        },
    }

    print("Saving build log artifact...")
    build_log_path = manager.save_build_log(build_log_data)

    if build_log_path and build_log_path.exists():
        print(f"✓ Build log saved: {build_log_path}")
        print()

        # Read and display the saved build log
        with open(build_log_path, encoding="utf-8") as f:
            saved_data = json.load(f)

        print("Build log contents:")
        print("-" * 70)
        print(json.dumps(saved_data, indent=2))
        print("-" * 70)
        print()

        # Verify required fields
        assert "timestamp" in saved_data, "Missing timestamp"
        assert "status" in saved_data, "Missing status"
        assert "duration" in saved_data, "Missing duration"
        assert "exitCode" in saved_data, "Missing exitCode"
        assert "changedFiles" in saved_data, "Missing changedFiles"
        assert "metadata" in saved_data, "Missing metadata"

        print("✓ All required fields present")
        print()

        # List artifacts
        artifacts = manager.list_artifacts()
        print(f"✓ Artifacts generated: {len(artifacts)}")
        for artifact in artifacts:
            print(f"  - {artifact}")
        print()

        # Get artifact summary
        summary = manager.get_artifact_summary()
        print(f"✓ Artifact directory: {summary['artifactDir']}")
        print(f"✓ Total artifacts: {summary['count']}")
        print()

        print("=" * 70)
        print("✅ VERIFICATION PASSED")
        print("=" * 70)
        print()
        print("Build log artifacts are correctly generated!")
        print()
        print("To test in CI mode:")
        print("  cd apps/backend")
        print("  python run.py --spec 128 --ci --json")
        print()
        print("Check artifact location:")
        print(f"  {test_dir / 'artifacts' / 'build-log.json'}")

        return True
    else:
        print("✗ Failed to save build log")
        return False


if __name__ == "__main__":
    try:
        success = verify_artifact_manager()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"✗ Verification failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
