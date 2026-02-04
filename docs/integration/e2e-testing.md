# End-to-End Testing with Electron MCP Server

Comprehensive guide for automated E2E testing of the Auto Claude Electron frontend using the Electron MCP (Model Context Protocol) server integration.

## Overview

Auto Claude's QA agents can perform automated end-to-end testing of the Electron desktop application using the Electron MCP server. This integration allows AI agents to:

- Interact with the running Electron app via Chrome DevTools Protocol (CDP)
- Click buttons, fill forms, and navigate the UI
- Take screenshots for visual verification
- Inspect page structure and element states
- Read console logs for debugging
- Validate user flows and acceptance criteria

**Key Benefits:**
- **Automated regression testing** - QA agents can verify features work after changes
- **Bug reproduction** - Reproduce issues before applying fixes
- **Feature validation** - Test new features end-to-end before approval
- **Visual verification** - Screenshot-based validation of UI changes

## Electron MCP Server Architecture

The Electron MCP server acts as a bridge between AI agents and the running Electron application:

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   QA Agent      │  MCP    │  Electron MCP    │   CDP   │   Electron App  │
│  (qa_reviewer/  │ ◄─────► │     Server       │ ◄─────► │  (Frontend UI)  │
│   qa_fixer)     │  Tools  │                  │ Protocol│                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
```

**Communication Flow:**
1. QA agent calls MCP tool (e.g., `mcp__electron__take_screenshot`)
2. MCP server translates to Chrome DevTools Protocol command
3. Electron app (running with remote debugging) executes command
4. Result flows back through MCP server to QA agent
5. Agent analyzes result and continues test flow

## Setup

### Prerequisites

1. **Electron App with Remote Debugging**
   - The app must be running with Chrome DevTools Protocol enabled
   - Port 9222 is the default remote debugging port

2. **Environment Configuration**
   - `ELECTRON_MCP_ENABLED=true` in `apps/backend/.env`
   - `ELECTRON_DEBUG_PORT=9222` (optional, defaults to 9222)

### Step-by-Step Setup

**1. Start the Electron App**

```bash
# From project root
npm run dev  # Already configured with --remote-debugging-port=9222
```

The `dev` script automatically starts Electron with remote debugging enabled:
```json
{
  "scripts": {
    "dev": "NODE_ENV=development electron apps/frontend/dist/main/main.js --remote-debugging-port=9222"
  }
}
```

**2. Enable Electron MCP in Backend**

Create or edit `apps/backend/.env`:
```bash
# Enable Electron MCP server
ELECTRON_MCP_ENABLED=true

# Optional: Custom debug port (default: 9222)
ELECTRON_DEBUG_PORT=9222
```

**3. Verify Connection**

Run a simple QA test to verify the connection:
```bash
cd apps/backend
python run.py --spec 001 --qa
```

The QA agent will automatically detect the Electron MCP server and use it for testing.

## Available Testing Capabilities

QA agents (`qa_reviewer` and `qa_fixer`) automatically get access to Electron MCP tools when enabled. These tools are categorized into four main groups:

### 1. Window Management

**`mcp__electron__get_electron_window_info`**
- Get information about running Electron windows
- Returns: Window ID, title, URL, state

**`mcp__electron__take_screenshot`**
- Capture screenshots of the Electron app
- Returns: Base64-encoded screenshot image
- Automatically compressed (1280x720, JPEG quality 60) to fit Claude SDK's 1MB message limit
- Use for: Visual verification, debugging UI state

**Example:**
```python
# Agent command: "Take a screenshot to see the current UI state"
# Tool: mcp__electron__take_screenshot
# Result: Screenshot image displayed in agent context
```

### 2. UI Interaction

**`mcp__electron__send_command_to_electron`**

This is the primary tool for UI automation. It accepts various commands:

#### `click_by_text`
Click buttons, links, or elements by their visible text.

**Parameters:**
- `text` (string): The visible text to click
- `exact` (boolean, optional): Require exact text match (default: false)

**Example:**
```python
# Agent: "Click the 'Create New Spec' button"
# Tool: mcp__electron__send_command_to_electron
# Command: click_by_text
# Args: {"text": "Create New Spec"}
```

#### `click_by_selector`
Click elements by CSS selector.

**Parameters:**
- `selector` (string): CSS selector for the element

**Example:**
```python
# Agent: "Click the settings icon"
# Tool: mcp__electron__send_command_to_electron
# Command: click_by_selector
# Args: {"selector": ".settings-icon"}
```

#### `fill_input`
Fill form fields by placeholder text or CSS selector.

**Parameters:**
- `placeholder` (string, optional): Input placeholder text
- `selector` (string, optional): CSS selector (if no placeholder)
- `value` (string): The value to enter

**Example:**
```python
# Agent: "Fill the task description field with 'Add login feature'"
# Tool: mcp__electron__send_command_to_electron
# Command: fill_input
# Args: {"placeholder": "Describe your task", "value": "Add login feature"}
```

#### `select_option`
Select dropdown options.

**Parameters:**
- `selector` (string): CSS selector for the select element
- `value` (string): Option value to select

**Example:**
```python
# Agent: "Select 'complex' complexity level"
# Tool: mcp__electron__send_command_to_electron
# Command: select_option
# Args: {"selector": "#complexity-select", "value": "complex"}
```

#### `send_keyboard_shortcut`
Send keyboard shortcuts.

**Parameters:**
- `shortcut` (string): Keyboard shortcut (e.g., "Enter", "Ctrl+N", "Cmd+S")

**Example:**
```python
# Agent: "Press Enter to submit the form"
# Tool: mcp__electron__send_command_to_electron
# Command: send_keyboard_shortcut
# Args: {"shortcut": "Enter"}
```

#### `navigate_to_hash`
Navigate to hash-based routes.

**Parameters:**
- `hash` (string): Hash route (e.g., "#settings", "#create")

**Example:**
```python
# Agent: "Navigate to the settings page"
# Tool: mcp__electron__send_command_to_electron
# Command: navigate_to_hash
# Args: {"hash": "#settings"}
```

### 3. Page Inspection

#### `get_page_structure`
Get an organized overview of page elements.

**Returns:**
- List of buttons, links, forms, and interactive elements
- Element text, classes, IDs
- Organized by semantic meaning

**Example:**
```python
# Agent: "Get page structure to find available buttons"
# Tool: mcp__electron__send_command_to_electron
# Command: get_page_structure
# Result: {"buttons": ["Create New Spec", "Cancel"], "forms": [...]}
```

#### `debug_elements`
Get detailed debugging info about buttons and forms.

**Returns:**
- Element selectors, attributes, computed styles
- Event listeners
- Detailed state information

**Example:**
```python
# Agent: "Debug the submit button to see why it's disabled"
# Tool: mcp__electron__send_command_to_electron
# Command: debug_elements
# Result: {"submitButton": {"disabled": true, "reason": "form validation failed"}}
```

#### `verify_form_state`
Check form state and validation.

**Parameters:**
- `selector` (string, optional): Form selector

**Returns:**
- Form validity status
- Field values and validation states
- Error messages

**Example:**
```python
# Agent: "Verify the spec creation form is valid"
# Tool: mcp__electron__send_command_to_electron
# Command: verify_form_state
# Args: {"selector": "#spec-form"}
# Result: {"valid": false, "errors": ["Task description is required"]}
```

#### `eval`
Execute custom JavaScript code in the page context.

**Parameters:**
- `code` (string): JavaScript code to execute

**Returns:**
- Result of the JavaScript expression

**Example:**
```python
# Agent: "Check if user is authenticated"
# Tool: mcp__electron__send_command_to_electron
# Command: eval
# Args: {"code": "window.localStorage.getItem('authToken') !== null"}
# Result: true
```

### 4. Logging

**`mcp__electron__read_electron_logs`**

Read console logs from the Electron app for debugging.

**Returns:**
- Console log entries (log, warn, error)
- Timestamps
- Stack traces for errors

**Example:**
```python
# Agent: "Read logs to see if there are any errors"
# Tool: mcp__electron__read_electron_logs
# Result: ["[ERROR] Failed to load spec: Network error", ...]
```

## Example E2E Test Flows

### Example 1: Create New Spec Flow

```python
# 1. Agent takes screenshot to see current state
agent: "Take a screenshot to see the current UI"
# Uses: mcp__electron__take_screenshot
# Result: Screenshot shows main dashboard

# 2. Agent inspects page structure
agent: "Get page structure to find available buttons"
# Uses: mcp__electron__send_command_to_electron (command: "get_page_structure")
# Result: {"buttons": ["Create New Spec", "View Specs", ...]}

# 3. Agent clicks Create button
agent: "Click the 'Create New Spec' button"
# Uses: mcp__electron__send_command_to_electron (command: "click_by_text", args: {text: "Create New Spec"})
# Result: Navigates to spec creation form

# 4. Agent fills form fields
agent: "Fill the task description field"
# Uses: mcp__electron__send_command_to_electron (command: "fill_input", args: {placeholder: "Describe your task", value: "Add login feature"})

agent: "Select 'standard' complexity"
# Uses: mcp__electron__send_command_to_electron (command: "select_option", args: {selector: "#complexity", value: "standard"})

# 5. Agent submits and verifies
agent: "Click Submit button"
# Uses: mcp__electron__send_command_to_electron (command: "click_by_text", args: {text: "Submit"})

agent: "Take screenshot to verify success"
# Uses: mcp__electron__take_screenshot
# Result: Screenshot shows success message

agent: "Verify we're on the spec page"
# Uses: mcp__electron__send_command_to_electron (command: "eval", args: {code: "window.location.hash"})
# Result: "#spec-001"
```

### Example 2: Bug Fix Verification

```python
# 1. Reproduce the bug
agent: "Navigate to settings page"
# Uses: mcp__electron__send_command_to_electron (command: "navigate_to_hash", args: {hash: "#settings"})

agent: "Click the 'Clear Cache' button"
# Uses: mcp__electron__send_command_to_electron (command: "click_by_text", args: {text: "Clear Cache"})

agent: "Check console logs for errors"
# Uses: mcp__electron__read_electron_logs
# Result: ["[ERROR] Cannot read property 'size' of undefined"]

# 2. Apply fix (agent implements code changes)
# ... implementation happens here ...

# 3. Verify fix
agent: "Restart test - click Clear Cache again"
# Uses: mcp__electron__send_command_to_electron (command: "click_by_text", args: {text: "Clear Cache"})

agent: "Check logs again - should have no errors"
# Uses: mcp__electron__read_electron_logs
# Result: ["[INFO] Cache cleared successfully"]

agent: "Take screenshot to confirm UI state"
# Uses: mcp__electron__take_screenshot
# Result: Screenshot shows success toast
```

### Example 3: Form Validation Testing

```python
# 1. Navigate to form
agent: "Click 'Create New Spec'"
# Uses: mcp__electron__send_command_to_electron (command: "click_by_text", args: {text: "Create New Spec"})

# 2. Test empty submission
agent: "Click Submit without filling fields"
# Uses: mcp__electron__send_command_to_electron (command: "click_by_text", args: {text: "Submit"})

agent: "Verify form shows validation errors"
# Uses: mcp__electron__send_command_to_electron (command: "verify_form_state", args: {selector: "#spec-form"})
# Result: {"valid": false, "errors": ["Task description is required"]}

agent: "Take screenshot of validation state"
# Uses: mcp__electron__take_screenshot
# Result: Screenshot shows red error messages

# 3. Fix validation and retry
agent: "Fill task description"
# Uses: mcp__electron__send_command_to_electron (command: "fill_input", args: {placeholder: "Describe your task", value: "Test task"})

agent: "Verify form is now valid"
# Uses: mcp__electron__send_command_to_electron (command: "verify_form_state", args: {selector: "#spec-form"})
# Result: {"valid": true, "errors": []}

agent: "Submit successfully"
# Uses: mcp__electron__send_command_to_electron (command: "click_by_text", args: {text: "Submit"})
```

## When to Use E2E Testing

### ✅ Use E2E Testing For:

**Bug Fixes**
- Reproduce the bug before fixing
- Verify the fix resolves the issue
- Ensure no regression in related functionality

**New Features**
- Test the complete user flow end-to-end
- Verify UI interactions work as expected
- Validate acceptance criteria

**UI Changes**
- Verify visual changes render correctly
- Test responsive layouts
- Validate color, spacing, typography changes

**Form Validation**
- Test field validation rules
- Verify error messages display correctly
- Test submission success/failure flows

**Navigation & Routing**
- Test hash-based routing
- Verify page transitions
- Test back/forward navigation

### ❌ Don't Use E2E Testing For:

**Unit-Level Logic**
- Use Jest/Vitest for unit tests
- E2E testing is too slow for unit-level coverage

**Backend API Testing**
- Use pytest for backend API tests
- E2E is for frontend UI validation only

**Performance Profiling**
- Use Chrome DevTools or dedicated profiling tools
- E2E testing adds overhead

**Simple Code Reviews**
- E2E testing is for functional validation
- Code style/patterns should be reviewed separately

## Configuration

### Backend Configuration (`apps/backend/.env`)

```bash
# Enable/disable Electron MCP server
ELECTRON_MCP_ENABLED=true

# Custom debug port (optional, default: 9222)
ELECTRON_DEBUG_PORT=9222
```

### Client Integration (`core/client.py`)

The Claude SDK client automatically enables Electron MCP tools when:
1. Project is detected as Electron (`is_electron` capability)
2. `ELECTRON_MCP_ENABLED=true` is set in `.env`
3. Agent type is `qa_reviewer` or `qa_fixer`

**Code Reference:**
```python
# apps/backend/core/client.py
def create_client(...):
    # ...
    if capabilities.get('is_electron') and os.getenv('ELECTRON_MCP_ENABLED') == 'true':
        if agent_type in ['qa_reviewer', 'qa_fixer']:
            # Enable Electron MCP server
            mcp_servers['electron'] = {
                'command': 'npx',
                'args': ['-y', '@modelcontextprotocol/server-electron'],
                'env': {
                    'ELECTRON_DEBUG_PORT': os.getenv('ELECTRON_DEBUG_PORT', '9222')
                }
            }
```

### Agent Permission Model

Only QA-related agents have access to Electron MCP tools:

| Agent Type | Electron MCP Access |
|------------|---------------------|
| `qa_reviewer` | ✅ Full access |
| `qa_fixer` | ✅ Full access |
| `planner` | ❌ No access |
| `coder` | ❌ No access |

**Rationale:** Electron MCP is specifically for testing, not implementation.

## Best Practices

### 1. Start with Screenshots

Always take a screenshot first to understand the current UI state:
```python
agent: "Take a screenshot to see what we're working with"
```

### 2. Use Semantic Selectors

Prefer `click_by_text` over `click_by_selector` when possible:
```python
# ✅ Good: Semantic and readable
click_by_text("Create New Spec")

# ❌ Avoid: Brittle and hard to understand
click_by_selector("#app > div > button:nth-child(2)")
```

### 3. Verify State After Actions

After clicking buttons or filling forms, verify the expected state:
```python
# Click button
agent: "Click Submit"

# Verify success
agent: "Check if we navigated to the success page"
agent: "Take screenshot to confirm"
```

### 4. Read Logs for Debugging

When tests fail, check console logs for clues:
```python
agent: "Action failed - read logs to see why"
# Uses: mcp__electron__read_electron_logs
```

### 5. Use Form State Inspection

Before submitting forms, verify they're valid:
```python
agent: "Verify form is valid before submitting"
# Uses: verify_form_state
# Avoids submitting invalid forms
```

### 6. Test Error Paths

Don't just test the happy path - test validation and error handling:
```python
# Test empty form submission
agent: "Try submitting without required fields"
agent: "Verify validation errors appear"

# Test invalid input
agent: "Enter invalid email format"
agent: "Verify email validation error"
```

### 7. Clean Up Test State

Reset state between tests if needed:
```python
# Clear form fields
agent: "Navigate back to home"
agent: "Click Create New Spec to start fresh"
```

## Troubleshooting

### Connection Issues

**Problem:** Agent can't connect to Electron app

**Solutions:**
1. Verify Electron is running with remote debugging:
   ```bash
   npm run dev  # Should show "Remote debugging port: 9222"
   ```

2. Check the debug port matches:
   ```bash
   # In apps/backend/.env
   ELECTRON_DEBUG_PORT=9222
   ```

3. Verify no firewall blocking port 9222

### Screenshot Size Limit

**Problem:** Screenshots fail with "message too large" error

**Solution:** Screenshots are automatically compressed (1280x720, JPEG quality 60) to stay under Claude SDK's 1MB JSON message buffer limit. If still failing:
- Check for extremely detailed/colorful UI that resists compression
- Consider reducing window size before taking screenshot

### Element Not Found

**Problem:** `click_by_text` or `click_by_selector` fails to find element

**Solutions:**
1. Use `get_page_structure` to see available elements:
   ```python
   agent: "Get page structure to see what's available"
   ```

2. Use `debug_elements` for detailed element info:
   ```python
   agent: "Debug elements to find the right selector"
   ```

3. Check if element is hidden or disabled:
   ```python
   agent: "Evaluate if element is visible"
   # Uses: eval with "document.querySelector('#my-btn').style.display"
   ```

4. Wait for element to load (React rendering):
   ```python
   agent: "Take screenshot to see current state"
   # Visual confirmation that page is ready
   ```

### Console Log Overload

**Problem:** Too many console logs make it hard to debug

**Solution:** Filter logs by severity or time:
```python
# Agent can ask for specific time range or severity
agent: "Show only error logs from the last 5 seconds"
```

### Form Submission Fails

**Problem:** Form doesn't submit even though fields are filled

**Solutions:**
1. Verify form validation state:
   ```python
   agent: "Check form validation state"
   # Uses: verify_form_state
   ```

2. Check if submit button is enabled:
   ```python
   agent: "Debug the submit button"
   # Uses: debug_elements
   ```

3. Try keyboard shortcut instead:
   ```python
   agent: "Press Enter to submit"
   # Uses: send_keyboard_shortcut
   ```

## Technical Details

### Chrome DevTools Protocol (CDP)

The Electron MCP server uses CDP to communicate with Electron. CDP is the same protocol used by:
- Chrome DevTools
- Puppeteer
- Playwright
- Selenium WebDriver

**Key CDP Domains Used:**
- `Runtime` - Execute JavaScript, read console logs
- `Input` - Simulate keyboard/mouse input
- `Page` - Navigate, take screenshots, get DOM
- `DOM` - Query elements, get attributes

### Screenshot Compression

Screenshots are automatically compressed to fit Claude SDK's 1MB message limit:

**Compression Settings:**
- Resolution: 1280x720 (16:9 aspect ratio)
- Format: JPEG
- Quality: 60
- Estimated size: ~100-300KB (well under 1MB limit)

**Why these settings:**
- 1280x720 is readable for UI verification
- JPEG compression reduces file size significantly
- Quality 60 balances size vs. readability

### Security Considerations

**Electron MCP Access Control:**
- Only QA agents (`qa_reviewer`, `qa_fixer`) have access
- Requires explicit opt-in via `ELECTRON_MCP_ENABLED=true`
- Runs on localhost only (no external access)
- Chrome DevTools Protocol is local-only by design

**Risk Mitigation:**
- Electron app must be started manually by user
- No automatic remote debugging without user consent
- MCP server only runs during QA sessions
- All commands are logged for audit trail

## Related Documentation

- [Backend API Reference](../api/backend-api.md) - QA commands and options
- [Backend Architecture](../modules/backend-architecture.md) - QA agent implementation
- [CLAUDE.md](../../CLAUDE.md) - End-to-End Testing section
- [Frontend Architecture](../modules/frontend-architecture.md) - Electron app structure

## Summary

End-to-end testing with Electron MCP provides automated UI testing capabilities for Auto Claude's Electron frontend. QA agents can:

✅ Interact with the UI (click, fill forms, navigate)
✅ Take screenshots for visual verification
✅ Inspect page structure and element states
✅ Read console logs for debugging
✅ Validate acceptance criteria end-to-end

**Key Takeaways:**
1. Enable with `ELECTRON_MCP_ENABLED=true` in `apps/backend/.env`
2. Start Electron with `npm run dev` (includes remote debugging)
3. QA agents automatically use E2E testing during `--qa` runs
4. Use for bug fixes, new features, and UI validation
5. Always start tests with screenshots for context
