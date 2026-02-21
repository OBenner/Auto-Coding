#!/usr/bin/env python3
"""
End-to-End Verification Script for Token Statistics Display in Electron App

This script verifies that all components for the TokenStatsDisplay feature are
correctly implemented and integrated.

Usage:
    python verify_token_stats_e2e.py
"""

import json
import sys
from pathlib import Path
from typing import List


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}\n")


def print_success(text: str):
    """Print a success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text: str):
    """Print an error message"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_warning(text: str):
    """Print a warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_info(text: str):
    """Print an info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


def check_file_exists(filepath: Path, description: str) -> bool:
    """Check if a file exists and print result"""
    if filepath.exists():
        print_success(f"{description}: {filepath}")
        return True
    else:
        print_error(f"{description} NOT FOUND: {filepath}")
        return False


def check_json_structure(filepath: Path, required_keys: List[str], description: str) -> bool:
    """Check if a JSON file has required keys"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        missing_keys = [key for key in required_keys if key not in data]
        if missing_keys:
            print_error(f"{description} - Missing keys: {', '.join(missing_keys)}")
            return False

        print_success(f"{description} - All required keys present")
        return True
    except json.JSONDecodeError as e:
        print_error(f"{description} - Invalid JSON: {e}")
        return False
    except Exception as e:
        print_error(f"{description} - Error reading file: {e}")
        return False


def verify_token_stats_json():
    """Verify token_stats.json file structure"""
    print_header("1. Token Stats JSON File Verification")

    spec_dir = Path(".auto-claude/specs/039-")
    token_stats_file = spec_dir / "token_stats.json"

    if not check_file_exists(token_stats_file, "Token stats file"):
        return False

    # Check JSON structure
    required_root_keys = ["phases", "total_input_tokens", "total_output_tokens", "total_tokens", "created_at", "updated_at"]
    if not check_json_structure(token_stats_file, required_root_keys, "Token stats file structure"):
        return False

    # Load and validate detailed structure
    try:
        with open(token_stats_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Check phases
        phases = data.get("phases", {})
        expected_phases = ["planning", "coding", "validation"]

        print_info(f"\nPhase Data:")
        for phase_name in expected_phases:
            if phase_name in phases:
                phase_data = phases[phase_name]
                print_success(f"  {phase_name.capitalize()}: {phase_data['input_tokens']:,} input / {phase_data['output_tokens']:,} output = {phase_data['total_tokens']:,} total ({phase_data['session_count']} session(s))")
            else:
                print_warning(f"  {phase_name.capitalize()}: Not present (may not have executed yet)")

        # Verify totals
        print_info(f"\nTotal Tokens:")
        print_info(f"  Input:  {data['total_input_tokens']:,}")
        print_info(f"  Output: {data['total_output_tokens']:,}")
        print_info(f"  Total:  {data['total_tokens']:,}")

        # Verify totals match sum of phases
        calculated_input = sum(p.get('input_tokens', 0) for p in phases.values())
        calculated_output = sum(p.get('output_tokens', 0) for p in phases.values())
        calculated_total = calculated_input + calculated_output

        if (calculated_input == data['total_input_tokens'] and
            calculated_output == data['total_output_tokens'] and
            calculated_total == data['total_tokens']):
            print_success("Total tokens correctly calculated from phase data")
        else:
            print_error(f"Total mismatch! Calculated: {calculated_total:,}, Stored: {data['total_tokens']:,}")
            return False

        return True

    except Exception as e:
        print_error(f"Error validating token stats structure: {e}")
        return False


def verify_backend_implementation():
    """Verify backend implementation files"""
    print_header("2. Backend Implementation Verification")

    backend_files = {
        "apps/backend/core/token_stats.py": "Token stats data structures",
        "apps/backend/agents/session.py": "Session management with token tracking",
        "apps/backend/agents/planner.py": "Planner agent token reporting",
        "apps/backend/agents/coder.py": "Coder agent token reporting",
        "apps/backend/qa/reviewer.py": "QA reviewer token reporting",
    }

    all_exist = True
    for filepath, description in backend_files.items():
        path = Path(filepath)
        if not check_file_exists(path, description):
            all_exist = False

    return all_exist


def verify_frontend_types():
    """Verify frontend TypeScript types"""
    print_header("3. Frontend TypeScript Types Verification")

    types_file = Path("apps/frontend/src/shared/types/task.ts")
    if not check_file_exists(types_file, "Task types file"):
        return False

    # Check for required type definitions
    try:
        with open(types_file, 'r', encoding='utf-8') as f:
            content = f.read()

        required_types = [
            "PhaseTokenStats",
            "TaskTokenStats",
            "tokenStats",  # Field in Task interface
        ]

        for type_name in required_types:
            if type_name in content:
                print_success(f"Type definition found: {type_name}")
            else:
                print_error(f"Type definition NOT FOUND: {type_name}")
                return False

        return True

    except Exception as e:
        print_error(f"Error reading types file: {e}")
        return False


def verify_frontend_components():
    """Verify frontend components"""
    print_header("4. Frontend Components Verification")

    component_files = {
        "apps/frontend/src/renderer/components/task-detail/TokenStatsDisplay.tsx": "TokenStatsDisplay component",
        "apps/frontend/src/renderer/components/task-detail/TaskDetailModal.tsx": "TaskDetailModal integration",
    }

    all_exist = True
    for filepath, description in component_files.items():
        path = Path(filepath)
        if not check_file_exists(path, description):
            all_exist = False

    # Check TokenStatsDisplay component content
    try:
        component_file = Path("apps/frontend/src/renderer/components/task-detail/TokenStatsDisplay.tsx")
        with open(component_file, 'r', encoding='utf-8') as f:
            content = f.read()

        required_features = {
            "formatNumber": "Number formatting function",
            "getPhaseColor": "Phase color function",
            "PhaseTokenStats": "PhaseTokenStats type import",
            "lucide-react": "Icon library import",
            "useTranslation": "i18n translation hook",
        }

        print_info("\nComponent Features:")
        for feature, description in required_features.items():
            if feature in content:
                print_success(f"  {description}")
            else:
                print_warning(f"  {description} - NOT FOUND")

    except Exception as e:
        print_error(f"Error checking component content: {e}")
        all_exist = False

    return all_exist


def verify_ipc_handlers():
    """Verify IPC handlers"""
    print_header("5. IPC Handlers Verification")

    handler_files = {
        "apps/frontend/src/main/ipc-handlers/token-stats-handler.ts": "Token stats IPC handler",
        "apps/frontend/src/shared/constants/ipc.ts": "IPC constants",
    }

    all_exist = True
    for filepath, description in handler_files.items():
        path = Path(filepath)
        if not check_file_exists(path, description):
            all_exist = False
        else:
            # Check IPC constants
            if "ipc.ts" in filepath:
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    if "TASK_TOKEN_STATS_GET" in content:
                        print_success("  TASK_TOKEN_STATS_GET constant defined")
                    else:
                        print_warning("  TASK_TOKEN_STATS_GET constant NOT FOUND")
                        all_exist = False
                except Exception as e:
                    print_error(f"  Error checking IPC constants: {e}")
                    all_exist = False

    return all_exist


def verify_translations():
    """Verify i18n translations"""
    print_header("6. i18n Translations Verification")

    translation_files = {
        "apps/frontend/src/shared/i18n/locales/en/tasks.json": "English translations",
        "apps/frontend/src/shared/i18n/locales/fr/tasks.json": "French translations",
    }

    all_exist = True
    for filepath, description in translation_files.items():
        path = Path(filepath)
        if not check_file_exists(path, description):
            all_exist = False
        else:
            # Check for tokenStats translations
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if "tokenStats" in data:
                    token_stats_keys = data["tokenStats"]
                    required_keys = ["title", "noStats", "noStatsHint", "totalTokens", "inputTokens", "outputTokens"]

                    missing = [k for k in required_keys if k not in token_stats_keys]
                    if missing:
                        print_error(f"  Missing translation keys: {', '.join(missing)}")
                        all_exist = False
                    else:
                        print_success(f"  All tokenStats translation keys present")
                else:
                    print_error(f"  tokenStats section NOT FOUND")
                    all_exist = False

            except Exception as e:
                print_error(f"  Error checking translations: {e}")
                all_exist = False

    return all_exist


def verify_task_store():
    """Verify task store implementation"""
    print_header("7. Task Store Verification")

    store_file = Path("apps/frontend/src/renderer/stores/task-store.ts")
    if not check_file_exists(store_file, "Task store file"):
        return False

    try:
        with open(store_file, 'r', encoding='utf-8') as f:
            content = f.read()

        required_features = {
            "updateTokenStats": "updateTokenStats action",
            "fetchAndUpdateTokenStats": "fetchAndUpdateTokenStats helper",
            "TaskTokenStats": "TaskTokenStats type import",
            "TASK_TOKEN_STATS_GET": "IPC channel constant",
        }

        print_info("\nTask Store Features:")
        all_present = True
        for feature, description in required_features.items():
            if feature in content:
                print_success(f"  {description}")
            else:
                print_error(f"  {description} - NOT FOUND")
                all_present = False

        return all_present

    except Exception as e:
        print_error(f"Error checking task store: {e}")
        return False


def print_manual_verification_steps():
    """Print manual E2E verification steps"""
    print_header("8. Manual E2E Verification Steps")

    print_info("To complete the E2E verification, perform these manual steps:")
    print()
    print(f"{Colors.BOLD}Step 1: Start the Electron App{Colors.RESET}")
    print("  $ npm run dev")
    print()
    print(f"{Colors.BOLD}Step 2: Open Task Detail Window{Colors.RESET}")
    print("  - Click on a task in the task list")
    print("  - Or click 'View Details' for an existing task")
    print()
    print(f"{Colors.BOLD}Step 3: Navigate to Token Stats Tab{Colors.RESET}")
    print("  - In the task detail modal, click the 'Token Usage' tab")
    print("  - The tab should be visible alongside Overview, Subtasks, Logs, Files")
    print()
    print(f"{Colors.BOLD}Step 4: Verify TokenStatsDisplay Renders{Colors.RESET}")
    print("  ✓ Component should render without errors")
    print("  ✓ Should show token statistics if token_stats.json exists")
    print("  ✓ Should show empty state if no token stats available")
    print()
    print(f"{Colors.BOLD}Step 5: Verify Phase Breakdown{Colors.RESET}")
    print("  For spec 039-, verify these exact values:")
    print(f"  {Colors.GREEN}Planning Phase:{Colors.RESET}")
    print("    - Input Tokens:  5,234")
    print("    - Output Tokens: 1,823")
    print("    - Total Tokens:  7,057")
    print("    - Session Count: 1")
    print(f"  {Colors.GREEN}Coding Phase:{Colors.RESET}")
    print("    - Input Tokens:  28,456")
    print("    - Output Tokens: 12,034")
    print("    - Total Tokens:  40,490")
    print("    - Session Count: 5")
    print(f"  {Colors.GREEN}Validation Phase:{Colors.RESET}")
    print("    - Input Tokens:  8,923")
    print("    - Output Tokens: 3,421")
    print("    - Total Tokens:  12,344")
    print("    - Session Count: 2")
    print()
    print(f"{Colors.BOLD}Step 6: Verify Total Tokens{Colors.RESET}")
    print("  - Total Input:  42,613")
    print("  - Total Output: 17,278")
    print("  - Total Tokens: 59,891")
    print()
    print(f"{Colors.BOLD}Step 7: Verify Number Formatting{Colors.RESET}")
    print("  ✓ All numbers should have thousand separators (e.g., 1,234)")
    print("  ✓ Phase colors should be visible (blue, purple, green)")
    print("  ✓ Hover effects should work on phase cards")
    print()
    print(f"{Colors.BOLD}Step 8: Verify UI Responsiveness{Colors.RESET}")
    print("  ✓ Component should be scrollable if content overflows")
    print("  ✓ Dark mode should work correctly")
    print("  ✓ Tooltips should show additional info on hover")
    print()
    print(f"{Colors.BOLD}Step 9: Test Empty State{Colors.RESET}")
    print("  - Create a new task or select a task without token_stats.json")
    print("  - Verify empty state message appears:")
    print("    'No token statistics available'")
    print("    'Token usage will appear here after task execution begins'")
    print()


def main():
    """Main verification function"""
    print_header("Token Stats E2E Verification")
    print_info("This script verifies the TokenStatsDisplay implementation")

    results = []

    # Run all verification checks
    results.append(("Token Stats JSON", verify_token_stats_json()))
    results.append(("Backend Implementation", verify_backend_implementation()))
    results.append(("Frontend Types", verify_frontend_types()))
    results.append(("Frontend Components", verify_frontend_components()))
    results.append(("IPC Handlers", verify_ipc_handlers()))
    results.append(("i18n Translations", verify_translations()))
    results.append(("Task Store", verify_task_store()))

    # Print summary
    print_header("Verification Summary")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        if result:
            print_success(f"{name}")
        else:
            print_error(f"{name}")

    print()
    print(f"{Colors.BOLD}Automated Checks: {passed}/{total} passed{Colors.RESET}")

    if passed == total:
        print_success("\n✓ All automated verification checks passed!")
        print_manual_verification_steps()
        return 0
    else:
        print_error(f"\n✗ {total - passed} verification check(s) failed")
        print_warning("Please fix the issues above before proceeding with manual E2E testing")
        return 1


if __name__ == "__main__":
    sys.exit(main())
