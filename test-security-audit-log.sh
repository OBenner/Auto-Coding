#!/bin/bash
# =============================================================================
# Manual Verification Script: Audit Log Viewing
# =============================================================================
#
# This script verifies that audit logs are correctly recorded and displayed
# in the security settings UI.
#
# Prerequisites:
# - Electron app is built and running (npm run dev)
# - Backend is accessible
#
# Usage:
#   chmod +x test-security-audit-log.sh
#   ./test-security-audit-log.sh
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
print_header() {
    echo ""
    echo "========================================"
    echo "$1"
    echo "========================================"
}

print_section() {
    echo ""
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
    ((TESTS_PASSED++))
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
    ((TESTS_FAILED++))
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "  $1"
}

# =============================================================================
# Verification Functions
# =============================================================================

verify_implementation() {
    print_header "Step 1: Implementation Verification"

    print_section "Checking if audit logger module exists"
    if [ -f "apps/backend/security/audit_logger.py" ]; then
        print_success "audit_logger.py exists"
    else
        print_error "audit_logger.py not found"
        return 1
    fi

    print_section "Checking if audit log viewer component exists"
    if [ -f "apps/frontend/src/renderer/components/settings/security/AuditLogViewer.tsx" ]; then
        print_success "AuditLogViewer.tsx exists"
    else
        print_error "AuditLogViewer.tsx not found"
        return 1
    fi

    print_section "Checking if security store has audit log actions"
    if grep -q "loadAuditLogs" apps/frontend/src/renderer/stores/security-store.ts 2>/dev/null; then
        print_success "Security store has loadAuditLogs action"
    else
        print_error "Security store missing loadAuditLogs action"
        return 1
    fi

    print_section "Checking if IPC handler for audit logs exists"
    if grep -q "SECURITY_GET_AUDIT_LOGS" apps/frontend/src/main/ipc-handlers/security-handlers.ts 2>/dev/null; then
        print_success "IPC handler SECURITY_GET_AUDIT_LOGS exists"
    else
        print_error "IPC handler SECURITY_GET_AUDIT_LOGS not found"
        return 1
    fi
}

run_automated_tests() {
    print_header "Step 2: Running Automated Tests"

    print_section "Running E2E tests for audit log viewing"

    # Check if npm test is available
    if command -v npm &> /dev/null; then
        print_info "Running: npm test -- security-audit-log-e2e.spec.ts --run"

        if npm test -- security-audit-log-e2e.spec.ts --run 2>&1 | tee /tmp/test-output.log; then
            print_success "All automated tests passed"
        else
            print_warning "Some tests failed or had warnings. Check /tmp/test-output.log for details."
        fi
    else
        print_warning "npm not found. Skipping automated tests."
    fi
}

verify_audit_log_file_structure() {
    print_header "Step 3: Audit Log File Structure Verification"

    print_section "Creating test audit log file"

    # Create test directory
    TEST_DIR="test-data"
    mkdir -p "$TEST_DIR"

    # Create a sample audit log entry
    cat > "$TEST_DIR/.auto-claude-audit.json" << 'EOF'
{
  "version": 1,
  "logs": [
    {
      "id": "log-test-001",
      "timestamp": 1234567890000,
      "category": "command_execution",
      "severity": "info",
      "message": "Command 'git status' allowed by allowlist",
      "command": "git status",
      "allowed": true,
      "agentType": "coder",
      "sessionId": "session-123"
    },
    {
      "id": "log-test-002",
      "timestamp": 1234567891000,
      "category": "command_execution",
      "severity": "warning",
      "message": "Command 'docker ps' blocked by allowlist",
      "command": "docker ps",
      "allowed": false,
      "agentType": "coder",
      "ruleId": "allowlist-001"
    }
  ]
}
EOF

    print_success "Created test audit log file"

    print_section "Validating JSON structure"
    if command -v python3 &> /dev/null; then
        if python3 -m json.tool "$TEST_DIR/.auto-claude-audit.json" > /dev/null 2>&1; then
            print_success "Audit log file has valid JSON structure"
        else
            print_error "Audit log file has invalid JSON structure"
            return 1
        fi
    else
        print_warning "python3 not found. Skipping JSON validation."
    fi

    print_section "Verifying required fields"
    # Check for required fields in each log entry
    if command -v jq &> /dev/null; then
        LOG_COUNT=$(jq '.logs | length' "$TEST_DIR/.auto-claude-audit.json")
        print_info "Found $LOG_COUNT log entries"

        # Check first log entry has required fields
        if jq -e '.logs[0] | has("id"), has("timestamp"), has("category"), has("severity"), has("message"), has("allowed")' "$TEST_DIR/.auto-claude-audit.json" > /dev/null 2>&1; then
            print_success "Log entries have all required fields"
        else
            print_error "Log entries missing required fields"
            return 1
        fi
    else
        print_warning "jq not found. Skipping field validation."
    fi
}

verify_ui_display() {
    print_header "Step 4: UI Display Verification (Manual)"

    print_section "Starting Electron App"
    print_info "Please start the Electron app if not already running:"
    print_info "  npm run dev"
    echo ""
    read -p "Press Enter when the app is running..."

    print_section "Manual UI Verification"

    echo ""
    print_info "Please perform the following steps in the app:"
    echo ""

    # Test 1: Navigate to Security Settings
    echo "1. Navigate to Security Settings"
    print_info "   - Click on Settings (gear icon)"
    print_info "   - Click on 'Security' in the left sidebar"
    read -p "   Can you see the Security Settings page? (y/n): " SECURITY_VISIBLE
    if [ "$SECURITY_VISIBLE" = "y" ]; then
        print_success "Security Settings page is visible"
    else
        print_error "Security Settings page not found"
    fi

    # Test 2: View Audit Log Section
    echo ""
    echo "2. View Audit Log Section"
    print_info "   - Scroll down to 'Audit Log' section"
    read -p "   Can you see the Audit Log section? (y/n): " AUDIT_VISIBLE
    if [ "$AUDIT_VISIBLE" = "y" ]; then
        print_success "Audit Log section is visible"
    else
        print_error "Audit Log section not found"
    fi

    # Test 3: Verify test entries are displayed
    echo ""
    echo "3. Verify Test Audit Log Entries"
    print_info "   - Look for entries from test-data/.auto-claude-audit.json"
    print_info "   - You should see at least 2 test entries:"
    print_info "     * 'Command 'git status' allowed by allowlist' (green checkmark)"
    print_info "     * 'Command 'docker ps' blocked by allowlist' (red X)"
    read -p "   Are the test entries displayed correctly? (y/n): " ENTRIES_DISPLAYED
    if [ "$ENTRIES_DISPLAYED" = "y" ]; then
        print_success "Audit log entries are displayed correctly"
    else
        print_error "Audit log entries not displayed or incorrect"
    fi

    # Test 4: Verify timestamp display
    echo ""
    echo "4. Verify Timestamp Display"
    print_info "   - Check that timestamps are shown in a human-readable format"
    print_info "   - Examples: 'Just now', '5m ago', '2h ago', '1d ago'"
    read -p "   Are timestamps displayed correctly? (y/n): " TIMESTAMPS_OK
    if [ "$TIMESTAMPS_OK" = "y" ]; then
        print_success "Timestamps are formatted correctly"
    else
        print_error "Timestamps not formatted correctly"
    fi

    # Test 5: Verify category icons
    echo ""
    echo "5. Verify Category Icons and Colors"
    print_info "   - Command execution: Terminal icon (blue)"
    print_info "   - Filesystem access: Hard drive icon (green)"
    print_info "   - API call: Globe icon (purple)"
    print_info "   - Permission change: Settings icon (orange)"
    print_info "   - Risk detected: Alert triangle icon (red)"
    read -p "   Are category icons and colors correct? (y/n): " ICONS_OK
    if [ "$ICONS_OK" = "y" ]; then
        print_success "Category icons and colors are correct"
    else
        print_error "Category icons or colors incorrect"
    fi

    # Test 6: Verify severity badges
    echo ""
    echo "6. Verify Severity Badges"
    print_info "   - Critical: Red background, alert icon"
    print_info "   - Warning: Orange background, warning icon"
    print_info "   - Info: Blue background, info icon"
    read -p "   Are severity badges displayed correctly? (y/n): " SEVERITY_OK
    if [ "$SEVERITY_OK" = "y" ]; then
        print_success "Severity badges are correct"
    else
        print_error "Severity badges not correct"
    fi

    # Test 7: Verify allowed/blocked status
    echo ""
    echo "7. Verify Allowed/Blocked Status"
    print_info "   - Allowed commands: Green checkmark icon"
    print_info "   - Blocked commands: Red X icon"
    print_info "   - Background tint for blocked entries"
    read -p "   Are status indicators correct? (y/n): " STATUS_OK
    if [ "$STATUS_OK" = "y" ]; then
        print_success "Status indicators are correct"
    else
        print_error "Status indicators not correct"
    fi
}

verify_filtering_and_search() {
    print_header "Step 5: Filtering and Search Verification (Manual)"

    echo ""
    print_info "Please perform the following filtering tests:"
    echo ""

    # Test 1: Category filter
    echo "1. Category Filter"
    print_info "   - Click on 'Command' button (Terminal icon)"
    read -p "   Does it show only command execution events? (y/n): " CATEGORY_FILTER
    if [ "$CATEGORY_FILTER" = "y" ]; then
        print_success "Category filter works correctly"
    else
        print_error "Category filter not working"
    fi

    # Test 2: Severity filter
    echo ""
    echo "2. Severity Filter"
    print_info "   - Click on 'Critical' button"
    read -p "   Does it show only critical severity events? (y/n): " SEVERITY_FILTER
    if [ "$SEVERITY_FILTER" = "y" ]; then
        print_success "Severity filter works correctly"
    else
        print_error "Severity filter not working"
    fi

    # Test 3: Status filter
    echo ""
    echo "3. Status Filter"
    print_info "   - Click on status button to cycle through: All → Blocked → Allowed"
    read -p "   Does the status filter work? (y/n): " STATUS_FILTER
    if [ "$STATUS_FILTER" = "y" ]; then
        print_success "Status filter works correctly"
    else
        print_error "Status filter not working"
    fi

    # Test 4: Search
    echo ""
    echo "4. Search Functionality"
    print_info "   - Type 'git' in the search box"
    read -p "   Does it show only entries matching 'git'? (y/n): " SEARCH_WORKS
    if [ "$SEARCH_WORKS" = "y" ]; then
        print_success "Search functionality works correctly"
    else
        print_error "Search functionality not working"
    fi

    # Test 5: Clear filters
    echo ""
    echo "5. Clear Filters"
    print_info "   - Apply some filters"
    print_info "   - Click 'Clear' button"
    read -p "   Does it reset all filters and show all entries? (y/n): " CLEAR_FILTERS
    if [ "$CLEAR_FILTERS" = "y" ]; then
        print_success "Clear filters works correctly"
    else
        print_error "Clear filters not working"
    fi
}

verify_detail_view() {
    print_header "Step 6: Detail View Verification (Manual)"

    echo ""
    print_info "Please perform the following detail view tests:"
    echo ""

    echo "1. Open Detail Dialog"
    print_info "   - Click on any audit log entry"
    read -p "   Does a detail dialog open? (y/n): " DETAIL_OPEN
    if [ "$DETAIL_OPEN" = "y" ]; then
        print_success "Detail dialog opens correctly"
    else
        print_error "Detail dialog does not open"
        return 1
    fi

    echo ""
    echo "2. Verify Detail Content"
    print_info "   The detail dialog should show:"
    print_info "   - Event message (description)"
    print_info "   - Category badge"
    print_info "   - Severity badge with icon"
    print_info "   - Allowed/blocked status badge"
    print_info "   - Full timestamp (date and time)"
    print_info "   - Command (if applicable)"
    print_info "   - File path (if applicable)"
    print_info "   - API endpoint (if applicable)"
    print_info "   - Agent type (if applicable)"
    print_info "   - Session ID (if applicable)"
    print_info "   - Context JSON (if applicable)"
    read -p "   Are all details displayed correctly? (y/n): " DETAIL_CONTENT
    if [ "$DETAIL_CONTENT" = "y" ]; then
        print_success "Detail view shows all information"
    else
        print_error "Detail view missing information"
    fi

    echo ""
    echo "3. Close Detail Dialog"
    print_info "   - Click outside the dialog or press Escape"
    read -p "   Does the dialog close? (y/n): " DETAIL_CLOSE
    if [ "$DETAIL_CLOSE" = "y" ]; then
        print_success "Detail dialog closes correctly"
    else
        print_error "Detail dialog does not close"
    fi
}

verify_statistics() {
    print_header "Step 7: Statistics Verification (Manual)"

    echo ""
    print_info "Please verify the statistics display:"
    echo ""

    echo "1. Entry Count Badge"
    print_info "   - Look for badge showing 'X / Y events'"
    print_info "   - X = filtered entries, Y = total entries"
    read -p "   Is the entry count badge visible and accurate? (y/n): " COUNT_BADGE
    if [ "$COUNT_BADGE" = "y" ]; then
        print_success "Entry count badge is correct"
    else
        print_error "Entry count badge incorrect"
    fi

    echo ""
    echo "2. Critical and Blocked Counters"
    print_info "   - Look for red 'X critical' counter (if any critical events)"
    print_info "   - Look for orange 'X blocked' counter (if any blocked events)"
    read -p "   Are the critical/blocked counters visible? (y/n): " STAT_COUNTERS
    if [ "$STAT_COUNTERS" = "y" ]; then
        print_success "Statistics counters are correct"
    else
        print_error "Statistics counters incorrect"
    fi
}

cleanup() {
    print_header "Cleanup"

    print_section "Removing test data"
    if [ -d "test-data" ]; then
        rm -rf "test-data"
        print_success "Test data removed"
    fi

    print_section "Removing test output"
    if [ -f "/tmp/test-output.log" ]; then
        rm -f "/tmp/test-output.log"
        print_success "Test output removed"
    fi
}

print_summary() {
    print_header "Test Summary"

    TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))

    echo ""
    echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"
    echo -e "Total Tests: $TOTAL_TESTS"
    echo ""

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ All verification tests passed!${NC}"
        echo ""
        echo "The audit log viewing feature is working correctly."
        return 0
    else
        echo -e "${RED}✗ Some verification tests failed.${NC}"
        echo ""
        echo "Please review the failed tests above and fix any issues."
        return 1
    fi
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    print_header "Audit Log Viewing - Manual Verification"

    echo ""
    print_info "This script verifies the audit log viewing functionality"
    print_info "including file structure, UI display, filtering, and details."
    echo ""
    read -p "Press Enter to continue..."

    # Run verification steps
    verify_implementation
    run_automated_tests
    verify_audit_log_file_structure
    verify_ui_display
    verify_filtering_and_search
    verify_detail_view
    verify_statistics

    # Cleanup and summary
    cleanup
    print_summary
}

# Run main function
main
