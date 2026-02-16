## ELECTRON APP VALIDATION

For Electron/desktop applications, use the Electron MCP tools to validate the UI.

**Prerequisites:**
- `ELECTRON_MCP_ENABLED=true` in environment
- Two modes supported with DIFFERENT tool names:
  - **CDP mode** (default): External CDP-based server via `@iflow-mcp/electron-mcp-server`
  - **Embedded mode** (recommended): MCP server runs inside Electron process
- Mode selected via `ELECTRON_MCP_MODE` environment variable (cdp/embedded)

### Available Tools by Mode

**IMPORTANT:** Tool names differ between CDP and embedded modes. Use the correct tool names based on the active mode.

#### CDP Mode Tools (Legacy)

| Tool | Purpose |
|------|---------|
| `mcp__electron__get_electron_window_info` | Get info about running Electron windows |
| `mcp__electron__take_screenshot` | Capture screenshot of Electron window |
| `mcp__electron__send_command_to_electron` | Send commands (click, fill, evaluate JS) |
| `mcp__electron__read_electron_logs` | Read console logs from Electron app |

**Prerequisites for CDP Mode:**
- Electron app running with `--remote-debugging-port=9222`
- Start with: `pnpm run dev:mcp` or `pnpm run start:mcp`

#### Embedded Mode Tools (Recommended)

| Tool | Purpose |
|------|---------|
| `mcp__auto-claude-electron__get_window_info` | Get info about running Electron windows |
| `mcp__auto-claude-electron__take_screenshot` | Capture screenshot of window (JPEG compressed, max 1MB) |
| `mcp__auto-claude-electron__send_command` | Send commands (click, fill, navigate, evaluate JS) |
| `mcp__auto-claude-electron__read_logs` | Read console logs (filtered for sensitive data) |
| `mcp__auto-claude-electron__health_check` | Get MCP server health metrics |

**Prerequisites for Embedded Mode:**
- Electron app built: `pnpm run build`
- Backend spawns Electron app automatically via `npm start`
- No debugging port required (more secure)

### Validation Flow

**IMPORTANT:** Before using tools, check which mode is active by trying the health check tool (embedded mode only).

#### Step 0: Detect Mode

Try the embedded mode health check first:
```
Tool: mcp__auto-claude-electron__health_check
```

- **If successful:** Use embedded mode tools (server name: `auto-claude-electron`)
- **If tool not found:** Fall back to CDP mode tools (server name: `electron`)

#### Step 1: Connect to Electron App

**Embedded Mode:**
```
Tool: mcp__auto-claude-electron__get_window_info
```

**CDP Mode:**
```
Tool: mcp__electron__get_electron_window_info
```

Verify the app is running and get window information. If no app found, document that Electron validation was skipped.

#### Step 2: Capture Screenshot

**Embedded Mode:**
```
Tool: mcp__auto-claude-electron__take_screenshot
Args: {"quality": 80}  # Optional: JPEG quality 1-100, default 60
```

**CDP Mode:**
```
Tool: mcp__electron__take_screenshot
```

Take a screenshot to visually verify the current state of the application.

#### Step 3: Analyze Page Structure

**Embedded Mode:**
```
Tool: mcp__auto-claude-electron__send_command
Args: {"command": "get_page_structure"}
```

**CDP Mode:**
```
Tool: mcp__electron__send_command_to_electron
Args: {"command": "get_page_structure"}
```

Get an organized overview of all interactive elements (buttons, inputs, selects, links).

#### Step 4: Verify UI Elements

**Embedded Mode:**
```
Tool: mcp__auto-claude-electron__send_command
```

**CDP Mode:**
```
Tool: mcp__electron__send_command_to_electron
```

Use with different commands:

**Click elements by text:**
```
Args: {"command": "click_by_text", "text": "Button Text"}
```

**Click elements by selector:**
```
Args: {"command": "click_by_selector", "selector": "button.submit-btn"}
```

**Fill input fields:**
```
Args: {"command": "fill_input", "selector": "#email", "value": "test@example.com"}
# Or by placeholder:
Args: {"command": "fill_input", "placeholder": "Enter email", "value": "test@example.com"}
```

**Select dropdown option:**
```
Args: {"command": "select_option", "selector": "#country", "value": "USA"}
```

**Send keyboard shortcuts:**
```
Args: {"command": "send_keyboard_shortcut", "text": "Enter"}
# Or: {"text": "Ctrl+N"}, {"text": "Meta+N"}, {"text": "Escape"}
```

**Navigate to hash route:**
```
Args: {"command": "navigate_to_hash", "hash": "#settings"}
```

**Execute JavaScript:**
```
Args: {"command": "eval", "code": "document.title"}
```

**Note:** Embedded mode has additional commands like `select_option` and `navigate_to_hash` not available in CDP mode.

#### Step 5: Check Console Logs

**Embedded Mode:**
```
Tool: mcp__auto-claude-electron__read_logs
Args: {"logType": "console", "lines": 50}
```

**CDP Mode:**
```
Tool: mcp__electron__read_electron_logs
Args: {"logType": "console", "lines": 50}
```

Check for JavaScript errors, warnings, or failed operations.

### Document Findings

```
ELECTRON VALIDATION:
- MCP Mode: [embedded/cdp] (auto-detected)
- App Connection: PASS/FAIL
  - MCP server accessible: YES/NO
  - Connected to correct window: YES/NO
- UI Verification: PASS/FAIL
  - Screenshots captured: [list]
  - Visual elements correct: PASS/FAIL
  - Interactions working: PASS/FAIL
- Console Errors: [list or "None"]
- Electron-Specific Features: PASS/FAIL
  - [Feature]: PASS/FAIL
- Issues: [list or "None"]
```

### Handling Common Issues

**App Not Running (Embedded Mode):**
If Electron app is not running when in embedded mode:
1. Check if app built: `ls apps/frontend/out/`
2. Document that embedded mode requires built app
3. Note: Backend should spawn app automatically via `npm start`
4. If spawn fails, check `ELECTRON_MCP_ENABLED=true` and `ELECTRON_MCP_MODE=embedded`

**App Not Running (CDP Mode):**
If Electron app is not running or debug port is not accessible:
1. Document that Electron validation was skipped
2. Note reason: "App not running with --remote-debugging-port=9222"
3. Add to QA report as "Manual verification required"

**Headless Environment (CI/CD):**
If running in headless environment without display:
1. Skip interactive Electron validation
2. Document: "Electron UI validation skipped - headless environment"
3. Rely on unit/integration tests for validation

**Tool Not Found Errors:**
If you get "tool not found" errors:
1. You may be using tool names for the wrong mode
2. Try embedded mode tools first: `mcp__auto-claude-electron__*`
3. Fall back to CDP mode tools: `mcp__electron__*`
4. Check `ELECTRON_MCP_MODE` environment variable if unsure
