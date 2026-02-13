#!/bin/bash
# Manual Verification Script: Security Warnings for Risky Changes
# Tests warning dialogs and audit logging for risky security changes

set -e

echo "=========================================="
echo "Security Warnings E2E Verification"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to print test result
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
        ((TESTS_FAILED++))
    fi
}

# Function to check if file exists
check_file() {
    if [ -f "$1" ]; then
        return 0
    else
        return 1
    fi
}

# Function to check if command exists
check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

echo "=== Implementation Verification ==="
echo ""

# 1. Check if warning implementation exists
echo "1. Checking SecurityLevelSelector warning implementation..."
if grep -q "showPermissiveWarning" apps/frontend/src/renderer/components/settings/security/SecurityLevelSelector.tsx 2>/dev/null; then
    print_result 0 "SecurityLevelSelector has permissive warning state"
else
    print_result 1 "SecurityLevelSelector missing permissive warning state"
fi

if grep -q "AlertDialog" apps/frontend/src/renderer/components/settings/security/SecurityLevelSelector.tsx 2>/dev/null; then
    print_result 0 "SecurityLevelSelector imports AlertDialog component"
else
    print_result 1 "SecurityLevelSelector missing AlertDialog import"
fi

# 2. Check if warning translations exist
echo ""
echo "2. Checking warning translation keys..."
if grep -q '"warnings"' apps/frontend/src/shared/i18n/locales/en/security.json 2>/dev/null; then
    print_result 0 "English security.json has warnings section"
else
    print_result 1 "English security.json missing warnings section"
fi

if grep -q '"permissiveLevel"' apps/frontend/src/shared/i18n/locales/en/security.json 2>/dev/null; then
    print_result 0 "English translations have permissiveLevel warning key"
else
    print_result 1 "English translations missing permissiveLevel key"
fi

# 3. Check if command removal warning exists
echo ""
echo "3. Checking CommandAllowlistEditor warning implementation..."
if grep -q "removeDialog" apps/frontend/src/shared/i18n/locales/en/security.json 2>/dev/null; then
    print_result 0 "English translations have removeDialog section"
else
    print_result 1 "English translations missing removeDialog section"
fi

if grep -q "AlertCircle" apps/frontend/src/renderer/components/settings/security/CommandAllowlistEditor.tsx 2>/dev/null; then
    print_result 0 "CommandAllowlistEditor has AlertCircle icon for warnings"
else
    print_result 1 "CommandAllowlistEditor missing AlertCircle icon"
fi

# 4. Check if audit logging exists
echo ""
echo "4. Checking audit logging integration..."
if grep -q "CATEGORY_PERMISSION_CHANGE" apps/backend/security/__init__.py 2>/dev/null || \
   grep -q "permission_change" apps/backend/security/audit_logger.py 2>/dev/null; then
    print_result 0 "Audit logger has permission_change category"
else
    print_result 1 "Audit logger missing permission_change category"
fi

# 5. Run automated E2E tests
echo ""
echo "=== Automated E2E Tests ==="
echo ""

if check_command "npm" && [ -f "apps/frontend/package.json" ]; then
    echo "Running security warnings E2E test suite..."
    cd apps/frontend
    if npm test -- --run security-warnings-e2e.spec.ts > /tmp/test-output.log 2>&1; then
        TEST_COUNT=$(grep -o "[0-9]* passed" /tmp/test-output.log | head -1 | grep -o "[0-9]*")
        print_result 0 "E2E test suite ($TEST_COUNT tests passed)"
    else
        print_result 1 "E2E test suite failed"
        echo "Check /tmp/test-output.log for details"
    fi
    cd - > /dev/null
else
    echo -e "${YELLOW}⊘ SKIP${NC}: npm not available or package.json not found"
fi

echo ""
echo "=== Manual UI Testing Checklist ==="
echo ""

echo "The following tests should be performed manually in the running application:"
echo ""

echo "Permissive Mode Warning Tests:"
echo "-------------------------------------------"
echo ""
echo "1. ✓ Open Security Settings"
echo "   - Navigate to Settings → Security"
echo "   - Verify security settings page loads"
echo ""
echo "2. ✓ Switch to Permissive Mode"
echo "   - Click security level dropdown"
echo "   - Select 'Permissive' option"
echo "   - Verify warning dialog appears with:"
echo "     * Warning icon (AlertTriangle)"
echo "     * Title: 'Confirm Security Change'"
echo "     * Message about broad system access risks"
echo "     * 'Cancel' button"
echo "     * 'Confirm Risk' button (orange/warning color)"
echo ""
echo "3. ✓ Cancel Permissive Mode Warning"
echo "   - Click 'Cancel' button"
echo "   - Verify security level remains unchanged"
echo "   - Verify no audit log entry for change"
echo ""
echo "4. ✓ Confirm Permissive Mode Warning"
echo "   - Click 'Permissive' again"
echo "   - Click 'Confirm Risk' button"
echo "   - Verify security level changes to 'Permissive'"
echo "   - Verify success toast appears"
echo "   - Verify audit log entry shows:"
echo "     * Category: permission_change"
echo "     * Severity: warning"
echo "     * Metadata.from: previous level"
echo "     * Metadata.to: permissive"
echo "     * Metadata.warningAcknowledged: true"
echo ""
echo "5. ✓ No Warning for Non-Risky Changes"
echo "   - From 'Paranoid', switch to 'Standard'"
echo "   - Verify NO warning dialog appears"
echo "   - Verify change happens immediately"
echo ""

echo "Critical Command Removal Warning Tests:"
echo "-------------------------------------------"
echo ""
echo "6. ✓ Remove Critical Command"
echo "   - Scroll to Command Allowlist section"
echo "   - Find 'git' command (or other critical command)"
echo "   - Click trash icon to remove"
echo "   - Verify warning dialog appears with:"
echo "     * Danger icon (AlertCircle)"
echo "     * Title: 'Remove Command?'"
echo "     * Command name in description"
echo "     * Warning message: 'This action cannot be undone'"
echo "     * Hint about reverting to default security behavior"
echo "     * 'Cancel' button"
echo "     * 'Remove' button (destructive/red)"
echo ""
echo "7. ✓ Cancel Command Removal"
echo "   - Click 'Cancel' button"
echo "   - Verify command remains in allowlist"
echo "   - Verify no audit log entry for removal"
echo ""
echo "8. ✓ Confirm Command Removal"
echo "   - Click trash icon again"
echo "   - Click 'Remove' button"
echo "   - Verify command is removed from allowlist"
echo "   - Verify success toast appears"
echo "   - Verify audit log entry shows:"
echo "     * Category: permission_change"
echo "     * Severity: warning"
echo "     * Message includes 'Critical command removed'"
echo "     * Metadata.command: removed command name"
echo "     * Metadata.warningAcknowledged: true"
echo ""

echo "Audit Log Verification Tests:"
echo "-------------------------------------------"
echo ""
echo "9. ✓ Warning Logged Correctly"
echo "   - After confirming permissive mode, navigate to Audit Log section"
echo "   - Verify warning event appears at top of log"
echo "   - Verify timestamp is current"
echo "   - Verify severity badge shows 'warning'"
echo "   - Click event to view details"
echo "   - Verify details panel shows all metadata fields"
echo ""
echo "10. ✓ Multiple Warnings Logged Sequentially"
echo "   - Perform multiple risky changes:"
echo "     * Remove 'npm' command"
echo "     * Remove 'node' command"
echo "     * Switch to permissive mode"
echo "   - Navigate to Audit Log section"
echo "   - Verify all three warnings appear in chronological order"
echo "   - Verify each has correct metadata"
echo "   - Verify timestamps increase sequentially"
echo ""

echo "UI State Consistency Tests:"
echo "-------------------------------------------"
echo ""
echo "11. ✓ Profile Unchanged on Cancel"
echo "   - Before opening warning dialog, note current security level"
echo "   - Open warning dialog and cancel"
echo "   - Verify security level is unchanged"
echo "   - Verify command list is unchanged (for removal warnings)"
echo ""
echo "12. ✓ Profile Updated on Confirm"
echo "   - Before confirming, note current state"
echo "   - Confirm warning dialog"
echo "   - Verify profile is updated immediately"
echo "   - Verify UI reflects new state (level selector, command list)"
echo ""

echo "Edge Cases:"
echo "-------------------------------------------"
echo ""
echo "13. ✓ Already Permissive - No Warning"
echo "   - Ensure security level is already 'Permissive'"
echo "   - Click dropdown and select 'Permissive' again"
echo "   - Verify NO warning dialog appears"
echo "   - Verify no duplicate audit log entry"
echo ""
echo "14. ✓ Non-Existent Command Removal"
echo "   - Try to remove a command that doesn't exist"
echo "   - Verify no warning appears (or graceful error handling)"
echo "   - Verify no audit log entry created"
echo ""
echo "15. ✓ Empty Allowlist Handling"
echo "   - Remove all commands from allowlist"
echo "   - Verify warnings still work correctly"
echo "   - Verify audit logs reflect each removal"
echo ""

echo "Accessibility & Visual Design:"
echo "-------------------------------------------"
echo ""
echo "16. ✓ Warning Dialog Accessibility"
echo "   - Verify warning dialogs have proper focus management"
echo "   - Verify keyboard navigation (Escape to cancel, Enter to confirm)"
echo "   - Verify screen reader announces warning messages"
echo "   - Verify color contrast meets accessibility standards"
echo ""
echo "17. ✓ Visual Indicators"
echo "   - Verify warning dialogs use warning colors (orange/yellow)"
echo "   - Verify destructive actions use red color
echo "   - Verify warning icons are visible and clear"
echo "   - Verify button hierarchy (primary vs secondary)"
echo ""

echo "=== Expected Results Summary ==="
echo ""
echo "Permissive Mode Warning:"
echo "  ✓ AlertDialog appears when switching to permissive mode"
echo "  ✓ Shows warning icon, title, message, cancel, and confirm risk buttons"
echo "  ✓ Cancel keeps previous security level"
echo "  ✓ Confirm switches to permissive mode and logs audit entry"
echo "  ✓ No warning when already in permissive mode"
echo "  ✓ Audit log includes: from, to, warningAcknowledged metadata"
echo ""
echo "Command Removal Warning:"
echo "  ✓ AlertDialog appears when removing commands"
echo "  ✓ Shows danger icon, command name, warning message"
echo "  ✓ Cancel keeps command in allowlist"
echo "  ✓ Confirm removes command and logs audit entry"
echo "  ✓ Audit log includes: command, action, warningAcknowledged metadata"
echo ""
echo "Audit Logging:"
echo "  ✓ All confirmed warnings are logged with severity: 'warning'"
echo "  ✓ Canceled warnings are NOT logged"
echo "  ✓ Metadata includes context (from/to levels, command names)"
echo "  ✓ Timestamps are accurate and sequential"
echo "  ✓ Audit logs persist across page reloads"
echo ""

echo "=== Test Summary ==="
echo ""
echo "Automated Tests: $TESTS_PASSED passed, $TESTS_FAILED failed"
echo ""
echo "Manual Tests: 17 test scenarios"
echo "  - Permissive Mode Warning: 5 tests"
echo "  - Critical Command Removal: 3 tests"
echo "  - Audit Log Verification: 2 tests"
echo "  - UI State Consistency: 2 tests"
echo "  - Edge Cases: 3 tests"
echo "  - Accessibility & Visual Design: 2 tests"
echo ""
echo "To complete verification:"
echo "  1. Ensure all automated tests pass"
echo "  2. Run through manual UI testing checklist above"
echo "  3. Verify all expected results match"
echo ""
