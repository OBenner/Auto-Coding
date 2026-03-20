#!/usr/bin/env python3
"""
Manual Verification Script for Merge Completion Persistence
============================================================

This script verifies that merge completion data persists across sessions.
It simulates a merge operation and verifies that:
1. merge_history.json is created in .auto-claude/file_evolution/
2. The file contains merge records
3. Records can be loaded after restart (new session)
"""

import json
import shutil
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from merge.file_evolution.tracker import FileEvolutionTracker, MergeCompletionRecord


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def print_check(description: str, passed: bool) -> None:
    """Print a check result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {description}")


def setup_test_environment() -> tuple[Path, Path]:
    """Setup test environment with temporary directories."""
    test_root = Path(".auto-claude") / "verification_test"
    test_root.mkdir(parents=True, exist_ok=True)

    project_dir = test_root / "project"
    project_dir.mkdir(exist_ok=True)

    storage_dir = test_root / ".auto-claude" / "file_evolution"
    storage_dir.mkdir(parents=True, exist_ok=True)

    return project_dir, storage_dir


def cleanup_test_environment(test_root: Path) -> None:
    """Clean up test environment."""
    if test_root.exists():
        shutil.rmtree(test_root)
        print(f"\n🧹 Cleaned up test environment: {test_root}")


def verify_file_creation(storage_dir: Path) -> bool:
    """Verify that merge_history.json file is created."""
    merge_file = storage_dir / "merge_history.json"

    if not merge_file.exists():
        return False

    print(f"   📄 File location: {merge_file}")
    print(f"   📏 File size: {merge_file.stat().st_size} bytes")
    return True


def verify_file_content(storage_dir: Path) -> bool:
    """Verify that merge_history.json contains valid data."""
    merge_file = storage_dir / "merge_history.json"

    try:
        with open(merge_file, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            print(f"   ❌ Data is not a list: {type(data)}")
            return False

        if len(data) == 0:
            print(f"   ❌ Data list is empty")
            return False

        # Validate structure of first record
        record = data[0]
        required_fields = ["merge_id", "timestamp", "task_ids", "resolved_files", "success"]
        for field in required_fields:
            if field not in record:
                print(f"   ❌ Missing required field: {field}")
                return False

        print(f"   📊 Records in file: {len(data)}")
        print(f"   🆔 First merge ID: {record['merge_id']}")
        print(f"   📅 Timestamp: {record['timestamp']}")
        print(f"   📋 Task IDs: {record['task_ids']}")
        print(f"   📁 Resolved files: {record['resolved_files']}")
        print(f"   ✅ Success: {record['success']}")

        return True

    except json.JSONDecodeError as e:
        print(f"   ❌ Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error reading file: {e}")
        return False


def run_verification() -> bool:
    """Run the complete verification test."""
    print_section("Merge Completion Persistence Verification")

    # Setup
    print("\n🔧 Setting up test environment...")
    test_root = Path(".auto-claude") / "verification_test"
    project_dir, storage_dir = setup_test_environment()

    print(f"   📁 Test root: {test_root.absolute()}")
    print(f"   📁 Project dir: {project_dir.absolute()}")
    print(f"   📁 Storage dir: {storage_dir.absolute()}")

    all_passed = True

    # Session 1: Record a merge
    print_section("Session 1: Recording Merge Completion")

    try:
        tracker1 = FileEvolutionTracker(
            project_dir=project_dir,
            storage_dir=storage_dir,
        )

        print("\n📝 Recording merge completion...")
        record = tracker1.record_merge_completion(
            task_ids=["spec-156", "spec-157"],
            resolved_files=[
                "apps/backend/core/workspace.py",
                "apps/backend/merge/file_evolution/tracker.py",
            ],
            success=True,
        )

        print(f"   🆔 Merge ID: {record.merge_id}")
        print(f"   ⏰ Timestamp: {record.timestamp.isoformat()}")
        print(f"   📋 Task IDs: {record.task_ids}")
        print(f"   📁 Resolved files: {len(record.resolved_files)} files")
        print(f"   ✅ Success: {record.success}")

        print_check("Merge recorded successfully", record is not None)

    except Exception as e:
        print_check("Merge recorded successfully", False)
        print(f"   ❌ Error: {e}")
        all_passed = False
        cleanup_test_environment(test_root)
        return False

    # Verify file creation
    print_section("Verification 1: File Creation")

    file_exists = verify_file_creation(storage_dir)
    print_check("merge_history.json file created", file_exists)
    all_passed = all_passed and file_exists

    # Verify file content
    print_section("Verification 2: File Content")

    content_valid = verify_file_content(storage_dir)
    print_check("File contains valid merge data", content_valid)
    all_passed = all_passed and content_valid

    # Session 2: Load from disk (simulate restart)
    print_section("Session 2: Loading After Restart (Simulated)")

    try:
        # Create new tracker instance (simulates app restart)
        print("\n🔄 Creating new tracker instance (simulating restart)...")
        tracker2 = FileEvolutionTracker(
            project_dir=project_dir,
            storage_dir=storage_dir,
        )

        print("\n📖 Loading merge completion history...")
        history = tracker2.get_merge_completion_history()

        if len(history) == 0:
            print_check("History loaded from disk", False)
            all_passed = False
        else:
            print(f"   📊 Loaded {len(history)} record(s)")
            loaded_record = history[0]

            print(f"   🆔 Merge ID: {loaded_record.merge_id}")
            print(f"   ⏰ Timestamp: {loaded_record.timestamp.isoformat()}")
            print(f"   📋 Task IDs: {loaded_record.task_ids}")
            print(f"   📁 Resolved files: {len(loaded_record.resolved_files)} files")
            print(f"   ✅ Success: {loaded_record.success}")

            # Verify data integrity
            data_integrity = (
                loaded_record.merge_id == record.merge_id
                and loaded_record.task_ids == record.task_ids
                and loaded_record.resolved_files == record.resolved_files
                and loaded_record.success == record.success
            )

            print_check("History loaded from disk", len(history) > 0)
            print_check("Data integrity maintained across sessions", data_integrity)
            all_passed = all_passed and data_integrity

    except Exception as e:
        print_check("History loaded from disk", False)
        print(f"   ❌ Error: {e}")
        all_passed = False

    # Test append functionality
    print_section("Session 3: Appending New Merge")

    try:
        print("\n📝 Recording additional merge...")
        record2 = tracker2.record_merge_completion(
            task_ids=["spec-158"],
            resolved_files=["apps/backend/core/client.py"],
            success=True,
        )

        history = tracker2.get_merge_completion_history()
        append_works = len(history) == 2

        print_check("New merge appended to history", append_works)
        print(f"   📊 Total records after append: {len(history)}")

        all_passed = all_passed and append_works

        # Verify file content again
        content_valid = verify_file_content(storage_dir)
        print_check("File contains valid data after append", content_valid)
        all_passed = all_passed and content_valid

    except Exception as e:
        print_check("New merge appended to history", False)
        print(f"   ❌ Error: {e}")
        all_passed = False

    # Cleanup
    cleanup_test_environment(test_root)

    # Final result
    print_section("Final Result")

    if all_passed:
        print("\n✅ ALL CHECKS PASSED")
        print("\n✨ Merge completion data persists successfully across sessions!")
        print("\n📋 Summary:")
        print("   • merge_history.json is created in .auto-claude/file_evolution/")
        print("   • File contains valid merge records with all required fields")
        print("   • Records persist across tracker instances (simulated restart)")
        print("   • New merges are appended to existing history")
        print("   • Data integrity is maintained")
    else:
        print("\n❌ SOME CHECKS FAILED")
        print("\n⚠️  Please review the failed checks above.")

    return all_passed


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
