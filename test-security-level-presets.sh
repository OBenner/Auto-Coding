#!/bin/bash
# Manual Verification Script: Security Level Presets
# Tests security level preset functionality through the UI
#
# Usage: ./test-security-level-presets.sh
#
# This script provides automated checks and a manual testing checklist

set -e

echo "========================================"
echo "Security Level Presets Verification"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "apps/frontend/package.json" ]; then
  echo -e "${RED}Error: Must run from worktree root${NC}"
  exit 1
fi

# Change to frontend directory for tests
cd apps/frontend

echo -e "${BLUE}1. Automated Implementation Checks${NC}"
echo "--------------------------------------"

# Check for SecurityLevelSelector component
if [ -f "src/renderer/components/settings/security/SecurityLevelSelector.tsx" ]; then
  echo -e "${GREEN}✓${NC} SecurityLevelSelector component exists"
else
  echo -e "${RED}✗${NC} SecurityLevelSelector component missing"
  exit 1
fi

# Check for preset definitions in SecuritySettings
if grep -q "SECURITY_LEVEL_PRESETS" src/renderer/components/settings/SecuritySettings.tsx; then
  echo -e "${GREEN}✓${NC} Preset definitions found in SecuritySettings"
else
  echo -e "${RED}✗${NC} Preset definitions missing"
  exit 1
fi

# Check for preset apply logic
if grep -q "applySecurityLevel" src/renderer/components/settings/SecuritySettings.tsx; then
  echo -e "${GREEN}✓${NC} Preset apply logic found"
else
  echo -e "${RED}✗${NC} Preset apply logic missing"
  exit 1
fi

# Check for detection logic
if grep -q "detectSecurityLevel" src/renderer/components/settings/SecuritySettings.tsx; then
  echo -e "${GREEN}✓${NC} Security level detection logic found"
else
  echo -e "${RED}✗${NC} Detection logic missing"
  exit 1
fi

echo ""
echo -e "${GREEN}All automated checks passed!${NC}"
echo ""

echo -e "${BLUE}2. Run Automated Unit Tests${NC}"
echo "--------------------------------------"
echo "Running security level presets test suite..."
npm test -- security-level-presets-e2e.spec.ts --run

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓${NC} All unit tests passed"
else
  echo -e "${RED}✗${NC} Unit tests failed"
  exit 1
fi

echo ""
echo -e "${YELLOW}3. Manual UI Testing Checklist${NC}"
echo "--------------------------------------"
echo "The automated tests verify the logic, but you should manually test the UI."
echo ""
echo "Prerequisites:"
echo "  1. Build and start the app: npm start (or npm run dev)"
echo "  2. Navigate to Settings → Security"
echo ""
echo "Test Cases:"
echo ""
echo -e "${YELLOW}Test 1: Paranoid Preset${NC}"
echo "  Steps:"
echo "  1. Note current command count in 'Security Profile' section"
echo "  2. Click on 'Paranoid' preset card"
echo "  3. Verify command count reduced to ≤10"
echo "  4. Verify 'Filesystem Access' shows 'Restricted'"
echo "  5. Verify 'API Access' shows 'Restricted'"
echo "  6. Verify 'Paranoid' card shows 'Active' badge"
echo ""
echo -e "${YELLOW}Test 2: Standard Preset${NC}"
echo "  Steps:"
echo "  1. Click on 'Standard' preset card"
echo "  2. Verify command count ≤50"
echo "  3. Verify 'Filesystem Access' shows 'Full Access'"
echo "  4. Verify 'API Access' shows 'Full Access'"
echo "  5. Verify 'Standard' card shows 'Active' badge"
echo ""
echo -e "${YELLOW}Test 3: Permissive Preset${NC}"
echo "  Steps:"
echo "  1. Click on 'Permissive' preset card"
echo "  2. Verify warning dialog appears"
echo "  3. Click 'I understand the risks' to confirm"
echo "  4. Verify command count ≤100"
echo "  5. Verify 'Filesystem Access' shows 'Full Access'"
echo "  6. Verify 'API Access' shows 'Full Access'"
echo "  7. Verify 'Permissive' card shows 'Active' badge"
echo "  8. Verify warning banner appears at top of Security section"
echo ""
echo -e "${YELLOW}Test 4: Preset Persistence${NC}"
echo "  Steps:"
echo "  1. Select 'Paranoid' preset"
echo "  2. Close and reopen the app"
echo "  3. Navigate back to Settings → Security"
echo "  4. Verify 'Paranoid' is still selected as active"
echo "  5. Verify command count is still ≤10"
echo ""
echo -e "${YELLOW}Test 5: Preset Switching${NC}"
echo "  Steps:"
echo "  1. Select 'Paranoid' preset"
echo "  2. Wait for save to complete (spinner disappears)"
echo "  3. Immediately select 'Permissive' preset"
echo "  4. Confirm warning dialog"
echo "  5. Verify command count increases"
echo "  6. Verify restrictions are removed"
echo ""
echo -e "${YELLOW}Test 6: Disabled State During Save${NC}"
echo "  Steps:"
echo "  1. Select any preset"
echo "  2. Verify spinner appears on that preset card"
echo "  3. Verify clicking other presets does nothing during save"
echo "  4. Wait for save to complete"
echo "  5. Verify other presets become clickable again"
echo ""
echo -e "${YELLOW}Test 7: Permissive Warning Dialog${NC}"
echo "  Steps:"
echo "  1. Select 'Permissive' preset"
echo "  2. Verify dialog appears with warning icon"
echo "  3. Verify warning message is clear"
echo "  4. Click 'Cancel' button"
echo "  5. Verify dialog closes without applying permissive"
echo "  6. Verify previous preset remains active"
echo "  7. Click 'Permissive' again"
echo "  8. Click 'I understand the risks'"
echo "  9. Verify permissive is applied"
echo ""
echo -e "${YELLOW}Test 8: Profile Summary Updates${NC}"
echo "  Steps:"
echo "  1. Find 'Security Profile' section below presets"
echo "  2. Note current values"
echo "  3. Switch to different preset"
echo "  4. Verify profile summary updates immediately:"
echo "     - Total Commands count changes"
echo "     - Filesystem Access status changes"
echo "     - API Access status changes"
echo ""
echo -e "${YELLOW}Test 9: Audit Log Recording${NC}"
echo "  Steps:"
echo "  1. Scroll to 'Audit Log' section"
echo "  2. Note current event count"
echo "  3. Switch to a different preset"
echo "  4. Click refresh button in audit log section"
echo "  5. Verify new security event appears (permission change)"
echo ""
echo -e "${YELLOW}Test 10: Visual Indicators${NC}"
echo "  Steps:"
echo "  1. Verify each preset has correct icon (ShieldAlert, ShieldCheck, Shield)"
echo "  2. Verify active preset has highlighted border"
echo "  3. Verify active preset shows checkmark icon"
echo "  4. Verify risk level badges have correct colors:"
echo "     - Paranoid: green/low risk"
echo "     - Standard: yellow/medium risk"
echo "     - Permissive: red/high risk"
echo ""

echo -e "${BLUE}4. Verification Summary${NC}"
echo "--------------------------------------"
echo ""
echo "Automated checks:"
echo -e "  ${GREEN}✓${NC} Implementation files present"
echo -e "  ${GREEN}✓${NC} Unit tests passing"
echo ""
echo "Manual verification:"
echo "  Complete the 10 test cases above"
echo "  Check each step carefully"
echo "  Report any issues found"
echo ""
echo -e "${BLUE}Expected Results:${NC}"
echo "  - Paranoid: ≤10 commands, both restrictions enabled"
echo "  - Standard: ≤50 commands, no restrictions"
echo "  - Permissive: ≤100 commands, no restrictions"
echo "  - All presets persist across app restarts"
echo "  - Warning dialog shows for permissive mode"
echo "  - Profile summary updates in real-time"
echo "  - Audit log records preset changes"
echo ""
echo -e "${GREEN}Verification complete!${NC}"
echo ""
echo "If all tests pass, the security level preset feature is working correctly."
