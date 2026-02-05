# Electron MCP Integration Guide

This document covers setting up and using Electron MCP (Model Context Protocol) integration with Auto Claude for end-to-end testing of Electron applications. Electron MCP integration is **optional** - if not configured, Auto Claude continues to work with standard code-based testing only.

## What It Does

Electron MCP integration enables AI QA agents to visually validate Electron applications through Chrome DevTools Protocol:

- **Screenshot Capture**: Agents capture screenshots of the running Electron app
- **UI Inspection**: Agents analyze page structure, buttons, forms, and interactive elements
- **User Interaction**: Agents simulate clicks, form filling, keyboard shortcuts, and navigation
- **Console Monitoring**: Agents read console logs for JavaScript errors and warnings
- **E2E Testing**: QA agents validate bug fixes and new features through the actual UI

## When to Use Electron MCP

- You're building an Electron/desktop application with Auto Claude
- You want AI agents to visually test the UI, not just unit tests
- You're debugging UI issues that require seeing the actual app state
- You want to catch visual regressions and interaction bugs automatically
- You're running QA validation on frontend changes and need E2E verification

## Prerequisites

- Electron application (any Electron app can work)
- Chrome DevTools Protocol support (built into Electron)
- Auto Claude backend installed
- Electron app must be startable with remote debugging enabled

## Setup

**Step 1:** Enable Electron MCP in environment

Navigate to the backend directory:

```bash
cd apps/backend
```

Edit `.env` and enable Electron MCP:

```bash
# Electron MCP Integration (OPTIONAL)
ELECTRON_MCP_ENABLED=true

# Chrome DevTools debugging port (default: 9222)
ELECTRON_DEBUG_PORT=9222
```

**Step 2:** Start your Electron app with remote debugging

For **auto-claude-ui** (Auto Claude's desktop app), use the MCP-enabled scripts:

```bash
cd apps/frontend

# Development mode with MCP debugging
pnpm run dev:mcp

# OR production mode with MCP debugging
pnpm run start:mcp
```

For **custom Electron apps**, start with the debug flag:

```bash
# Windows
./YourElectronApp.exe --remote-debugging-port=9222

# macOS
./YourElectronApp.app/Contents/MacOS/YourElectronApp --remote-debugging-port=9222

# Linux
./YourElectronApp --remote-debugging-port=9222
```

**Step 3:** Run Auto Claude with QA validation

```bash
cd apps/backend

# Run a build with QA (E2E testing will be used for frontend changes)
python run.py --spec 001 --qa

# Or run QA manually
python run.py --spec 001 --qa
```

## How It Works

### QA Agent Workflow

When Electron MCP is enabled and the app is running, QA agents follow this validation flow:

**1. Connect to Electron App**
```
Tool: mcp__electron__get_electron_window_info
```
The agent verifies the app is running and gets window information.

**2. Capture Baseline Screenshot**
```
Tool: mcp__electron__take_screenshot
```
The agent captures a screenshot to visually verify the current state.

**3. Analyze Page Structure**
```
Tool: mcp__electron__send_command_to_electron
Command: get_page_structure
```
The agent gets an organized overview of all interactive elements (buttons, inputs, selects, links).

**4. Test UI Interactions**
```
Tool: mcp__electron__send_command_to_electron
Command: click_by_text
Args: {"text": "Create New Spec"}
```
The agent clicks buttons, fills forms, sends keyboard shortcuts, and navigates the UI.

**5. Verify Results**
```
Tool: mcp__electron__take_screenshot
Tool: mcp__electron__read_electron_logs
```
The agent captures another screenshot and checks console logs for errors.

**6. Document Findings**
The agent adds results to the QA report with:
- Screenshots showing before/after states
- List of interactions performed
- Any console errors or warnings
- Pass/fail status for each validation

### Example QA Session

Here's an example of how a QA agent validates a bug fix:

```markdown
QA AGENT: Validating login button fix...

1. Taking screenshot to see current UI...
   → [Screenshot captured]

2. Getting page structure...
   → Found: Login button (#login-btn), Email input (#email), Password input (#password)

3. Testing login flow:
   - Fill email input: test@example.com ✓
   - Fill password input: ******** ✓
   - Click login button ✓

4. Verifying result...
   → [Screenshot captured] - Shows successful login

5. Checking console logs...
   → No errors ✓

ELECTRON VALIDATION:
- App Connection: PASS
  - Debug port accessible: YES
  - Connected to correct window: YES
- UI Verification: PASS
  - Screenshots captured: 2 (before, after)
  - Visual elements correct: PASS
  - Interactions working: PASS
- Console Errors: None
- Issues: None

✅ QA PASSED: Login button fix verified working in Electron app
```

## Available Electron MCP Tools

When Electron MCP integration is enabled and the app is running, QA agents have access to these MCP tools:

| Tool | Purpose |
|------|---------|
| `mcp__electron__get_electron_window_info` | Get info about running Electron windows |
| `mcp__electron__take_screenshot` | Capture screenshot of Electron window |
| `mcp__electron__send_command_to_electron` | Send commands (click, fill, evaluate JS, etc.) |
| `mcp__electron__read_electron_logs` | Read console logs from Electron app |

### Available Commands

The `send_command_to_electron` tool supports these commands:

| Command | Purpose | Example Args |
|---------|---------|--------------|
| `get_page_structure` | Get organized overview of page elements | `{}` |
| `click_by_text` | Click button/link by visible text | `{"text": "Submit"}` |
| `click_by_selector` | Click element by CSS selector | `{"selector": "button.submit"}` |
| `fill_input` | Fill input field by selector or placeholder | `{"selector": "#email", "value": "test@example.com"}` |
| `select_option` | Select dropdown option | `{"selector": "#role", "value": "admin"}` |
| `send_keyboard_shortcut` | Send keyboard shortcut | `{"text": "Enter"}` or `{"text": "Ctrl+N"}` |
| `navigate_to_hash` | Navigate to hash route | `{"text": "#settings"}` |
| `eval` | Execute custom JavaScript | `{"code": "document.title"}` |
| `debug_elements` | Get debug info about buttons and forms | `{}` |
| `verify_form_state` | Check form state and validation | `{}` |

## Troubleshooting

### Issue: Electron MCP not connecting

**Symptoms:** Agent logs "Electron validation skipped - app not running"

**Solutions:**

1. Verify Electron MCP is enabled:
   ```bash
   grep ELECTRON_MCP_ENABLED apps/backend/.env
   # Should show: ELECTRON_MCP_ENABLED=true
   ```

2. Check Electron app is running with debug port:
   ```bash
   # Check if port 9222 is listening
   lsof -i :9222  # macOS/Linux
   netstat -an | findstr :9222  # Windows
   ```

3. Verify debug port configuration matches:
   ```bash
   # .env should match app startup
   ELECTRON_DEBUG_PORT=9222

   # App should start with:
   ./YourElectronApp --remote-debugging-port=9222
   ```

### Issue: Screenshots not captured

**Symptoms:** Agent connects but screenshots fail or are blank

**Solutions:**

1. Check Electron app window is visible and not minimized:
   - The window must be on screen for screenshots
   - Minimized windows may not render properly

2. Verify window has finished loading:
   - Wait for app to fully start before running QA
   - Check console logs for ready state

3. Try alternative screenshot capture:
   ```bash
   # For auto-claude-ui, verify the window is focused
   # The app may need to be the active window
   ```

### Issue: Clicks not working

**Symptoms:** Agent reports clicking but nothing happens

**Solutions:**

1. Verify element is clickable:
   - Element must be visible (not hidden by CSS)
   - Element must be enabled (not disabled)
   - Element must not be obscured by other elements

2. Use more specific selector:
   ```javascript
   // Instead of: click_by_text("Submit")
   // Try: click_by_selector("#login-form button[type='submit']")
   ```

3. Add wait for dynamic content:
   ```javascript
   // Wait for element to appear before clicking
   eval: "await new Promise(r => setTimeout(r, 1000))"
   ```

### Issue: Console logs not accessible

**Symptoms:** `read_electron_logs` returns empty or errors

**Solutions:**

1. Check Electron app's console output:
   - Open DevTools manually (Ctrl+Shift+I or Cmd+Option+I)
   - Verify console.log statements are being executed

2. Ensure log type is correct:
   ```bash
   # Default reads "console" logs
   # Can also read "debug", "info", "warn", "error"
   ```

3. Verify log level filtering:
   - Some Electron builds may filter console output
   - Check app's main process logging configuration

### Issue: Headless environment (CI/CD)

**Symptoms:** "Electron UI validation skipped - headless environment"

**Solutions:**

1. For CI/CD, use xvfb (Virtual Framebuffer) on Linux:
   ```bash
   # Install xvfb
   sudo apt install xvfb

   # Run Electron app with xvfb
   xvfb-run --auto-servernum ./YourElectronApp --remote-debugging-port=9222
   ```

2. Document that E2E testing was skipped:
   - QA agent will automatically note this in the report
   - Rely on unit/integration tests for CI/CD validation

3. For local development, always test in graphical environment

## Best Practices

### App Startup

- **Use MCP-enabled scripts**: For auto-claude-ui, always use `dev:mcp` or `start:mcp`
- **Match debug ports**: Ensure `.env` `ELECTRON_DEBUG_PORT` matches app startup flag
- **Wait for ready**: Let the app fully load before running QA validation

### QA Workflow

- **Start fresh**: Restart the Electron app before each QA run to ensure clean state
- **Clear data**: For stateful apps, clear user data between test runs
- **Check logs**: Always review console logs even if UI looks correct
- **Document steps**: QA agents automatically document interactions - review these logs

### Debugging

- **Manual testing**: Use DevTools (Ctrl+Shift+I) to manually reproduce issues
- **Selectors**: Use browser DevTools to find the best CSS selectors
- **Timing**: Add delays for animations and async operations with `eval` command

### Performance

- **Screenshots are compressed**: Screenshots are automatically compressed to stay under token limits
- **Limit interactions**: QA agents focus on critical user flows, not exhaustive testing
- **Parallel testing**: Consider running multiple QA sessions for different features

## Configuration Options

| Variable | Required | Description |
|----------|----------|-------------|
| `ELECTRON_MCP_ENABLED` | Yes | Enable Electron MCP integration (default: false) |
| `ELECTRON_DEBUG_PORT` | No | Chrome DevTools port (default: 9222) |

## Disable Electron MCP Integration

To disable Electron MCP integration after enabling:

```bash
# Remove or comment out in apps/backend/.env
# ELECTRON_MCP_ENABLED=true
```

Auto Claude will continue to work normally with code-based testing only.

## Platform-Specific Notes

### Windows

- Use `.exe` executable path for startup
- Firewalls may prompt for port 9222 access - allow it
- PowerShell may require explicit path execution

### macOS

- Use `.app/Contents/MacOS/AppName` path for startup
- Gatekeeper may prompt for security approval - allow it
- Use `open` command with arguments for some Electron apps

### Linux

- Use direct binary path for startup
- No special firewall configuration usually needed
- For headless CI/CD, use xvfb (see Troubleshooting)

## See Also

- [Linear Integration Guide](./INTEGRATION-LINEAR.md) - Linear issue tracking
- [GitLab Integration Guide](./INTEGRATION-GITLAB.md) - GitLab issues and merge requests
- [CLI Usage Guide](./CLI-USAGE.md) - Terminal-only Auto Claude usage

## External Resources

- [Electron Documentation](https://www.electronjs.org/docs/latest/)
- [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)
- [electron-mcp-server GitHub](https://github.com/anthropics/anthropic-quickstarts/tree/main/mcp-electron-demo)
