# Security Model Porting Analysis

## Executive Summary

This document analyzes Auto Code's multi-layered security model and identifies the requirements for porting these security features to OpenAI's API-based provider.

**Key Finding:** Claude SDK provides built-in security features (sandbox, file permissions, PreToolUse hooks) that must be manually replicated for OpenAI, as OpenAI's API has no native security capabilities.

**Critical Risk:** Porting the full security model to OpenAI requires implementing custom wrappers for every security layer. Full parity may not be achievable without OS-level integration.

## Security Model Overview

Auto Code implements **defense in depth** with three security layers:

```
┌─────────────────────────────────────────────────────────┐
│           Layer 1: OS Sandbox (SDK Managed)             │
│  - Process isolation for bash commands                  │
│  - Filesystem access restrictions                       │
│  - Prevents escape from working directory               │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│        Layer 2: File Permissions (SDK Enforced)          │
│  - Read/Write/Edit restricted to project_dir            │
│  - Worktree permissions for spec access                 │
│  - Explicit allowlist for file operations               │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│      Layer 3: Command Validation (PreToolUse Hook)       │
│  - bash_security_hook validates every command           │
│  - Dynamic allowlist based on project stack             │
│  - Special validators for dangerous commands            │
└─────────────────────────────────────────────────────────┘
```

### Security Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **Sandbox** | Claude SDK core | OS-level process isolation |
| **File Permissions** | `core/client.py:security_settings` | Restrict file operations |
| **PreToolUse Hooks** | `security/hooks.py:bash_security_hook` | Validate commands before execution |
| **Command Allowlist** | `security/` module | Dynamic command filtering |
| **Tool Filtering** | `agents/tools_pkg/` | Agent-specific tool permissions |

## Layer 1: OS Sandbox

### Claude SDK Implementation

**Configuration:** `core/client.py:770`
```python
security_settings = {
    "sandbox": {
        "enabled": True,
        "autoAllowBashIfSandboxed": True
    }
}
```

**How It Works:**
- SDK spawns bash commands in isolated subprocess
- Process cannot access files outside working directory
- Environment variables are scoped to subprocess
- Prevents `cd ../../`, symlinks to system files, etc.

**OpenAI Gap:**
OpenAI API has **no sandbox capability**. It's a stateless HTTP API that receives requests and returns responses. It cannot spawn processes or enforce OS-level isolation.

### Porting Requirements

#### Option 1: Application-Level Sandboxing (High Complexity)

**Implementation:**
```python
class OpenAIProvider:
    def execute_tool(self, tool_name: str, tool_input: dict):
        if tool_name == "Bash":
            # Spawn subprocess with restrictions
            result = subprocess.run(
                tool_input["command"],
                shell=False,
                cwd=self.project_dir,  # Restrict working directory
                env=self.restricted_env,  # Scoped environment
                timeout=30,  # Prevent runaway processes
                # Use OS-specific isolation (chroot, containers)
            )
```

**Challenges:**
- Must implement platform-specific isolation (Windows vs Unix)
- No true sandbox without OS-level features (chroot, containers)
- Agent can still run dangerous commands within allowed directory
- Requires comprehensive process management

**Feasibility:** Medium (possible but complex)

#### Option 2: No Sandbox (Not Recommended)

Accept that OpenAI provider has weaker security and document the limitation.

**Feasibility:** High (but reduces security posture)

### Recommendation

**Phased implementation:**
1. **Phase 1:** Implement working directory restrictions only
2. **Phase 2:** Add environment variable scoping
3. **Phase 3:** Investigate OS-level sandboxing (containers, chroot)

## Layer 2: File Permissions

### Claude SDK Implementation

**Configuration:** `core/client.py:769-820`
```python
security_settings = {
    "permissions": {
        "defaultMode": "acceptEdits",
        "allow": [
            # Relative paths (./**)
            "Read(./**)",
            "Write(./**)",
            "Edit(./**)",
            "Glob(./**)",
            "Grep(./**)",
            # Absolute paths (project_dir)
            f"Read({project_path_str}/**)",
            f"Write({project_path_str}/**)",
            # Spec directory access
            f"Read({spec_path_str}/**)",
            # Worktree permissions
            *original_project_permissions,
            # Tool permissions
            "Bash(*)",
            "WebFetch(*)",
            "WebSearch(*)",
        ]
    }
}
```

**How It Works:**
- SDK enforces permissions before executing file tools
- Allows both relative (`./src/file.ts`) and absolute paths
- Special handling for worktree mode (grants access to original project's `.auto-claude/`)
- Tools like Bash, WebFetch, WebSearch get wildcard permissions
- MCP tools get tool-specific permissions (`Context7(*)`, `Linear(*)`)

**Key Feature:** SDK checks permissions **before** tool execution and blocks unauthorized access.

### OpenAI Gap

OpenAI API has **no permission system**. When using function calling, the API returns tool calls but doesn't validate if the tool should be allowed.

### Porting Requirements

#### Permission Wrapper Implementation

**Architecture:**
```python
class PermissionWrapper:
    """
    Wraps OpenAI function calling with permission checks.
    Enforces file permissions before executing tools.
    """

    def __init__(self, project_dir: Path, security_settings: dict):
        self.project_dir = project_dir
        self.permissions = security_settings["permissions"]["allow"]

    async def execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        """Execute tool with permission validation."""

        # 1. Check if tool is allowed
        tool_permission = f"{tool_name}(*)"
        if tool_permission not in self.permissions:
            raise PermissionDeniedError(f"Tool {tool_name} not allowed")

        # 2. For file operations, check path permissions
        if tool_name in ["Read", "Write", "Edit", "Glob", "Grep"]:
            path = tool_input.get("file_path") or tool_input.get("path")
            if not self._check_path_permission(path, tool_name):
                raise PermissionDeniedError(
                    f"Path {path} not allowed for {tool_name}"
                )

        # 3. Execute tool
        return await self._execute_tool_unsafe(tool_name, tool_input)

    def _check_path_permission(self, path: str, tool_name: str) -> bool:
        """Check if path is within allowed directories."""
        resolved_path = Path(path).resolve()

        # Check against allowed directories
        allowed_dirs = [
            self.project_dir,
            self.project_dir / ".auto-claude",
            # ... worktree directories
        ]

        return any(
            resolved_path.is_relative_to(allowed_dir)
            for allowed_dir in allowed_dirs
        )
```

**Integration Point:**
```python
class OpenAIProvider:
    def __init__(self, project_dir: Path):
        self.permission_wrapper = PermissionWrapper(
            project_dir,
            security_settings=self._build_security_settings(project_dir)
        )

    async def process_message(self, message: str) -> AsyncIterator[str]:
        # Get function calls from OpenAI
        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=self.history,
            tools=self.function_schemas
        )

        # Process each tool call
        for tool_call in response.tool_calls:
            # Validate permissions BEFORE execution
            try:
                result = await self.permission_wrapper.execute_tool(
                    tool_call.function.name,
                    json.loads(tool_call.function.arguments)
                )
            except PermissionDeniedError as e:
                # Return error to agent
                yield f"Permission denied: {e}"
```

### Permission Schema

**Required Permissions by Agent Type:**

| Agent | File Ops | Bash | Web | MCP Tools |
|-------|----------|------|-----|-----------|
| **planner** | Read/Write | Limited | ✓ | Context7, Graphiti |
| **coder** | Read/Write/Edit/Glob/Grep | Full | ✓ | Context7 |
| **qa_reviewer** | Read | None | ✓ | Context7, Electron, Puppeteer |
| **qa_fixer** | Read/Write/Edit | Full | ✓ | Context7, Electron, Puppeteer |

**Implementation:** Use existing `get_allowed_tools()` and `get_required_mcp_servers()` from `agents/tools_pkg/`.

### Feasibility Assessment

| Component | Complexity | Notes |
|-----------|------------|-------|
| Path validation | Low | Straightforward string/path operations |
| Worktree permissions | Medium | Must detect worktree and grant original project access |
| Tool permissions | Low | Check tool name against allowlist |
| MCP tool permissions | Low | Already have tool lists in agents/tools_pkg/ |

**Overall Feasibility:** High

### Recommendation

**Implement in Phase 1:**
1. Create `PermissionWrapper` class
2. Reuse existing security settings from `core/client.py`
3. Add permission checks before all tool executions
4. Return clear error messages when permissions denied

## Layer 3: Command Validation (PreToolUse Hooks)

### Claude SDK Implementation

**Hook Registration:** `core/client.py:972-976`
```python
"hooks": {
    "PreToolUse": [
        HookMatcher(matcher="Bash", hooks=[bash_security_hook]),
    ],
}
```

**Hook Implementation:** `security/hooks.py:20-129`
```python
async def bash_security_hook(
    input_data: dict[str, Any],
    tool_use_id: str | None = None,
    context: Any | None = None,
) -> dict[str, Any]:
    """
    Pre-tool-use hook that validates bash commands using dynamic allowlist.
    Returns {} to allow, or {"decision": "block", "reason": "..."} to block.
    """
    # 1. Validate tool_input structure
    # 2. Extract command name from command string
    # 3. Check against security profile
    # 4. Run additional validators for sensitive commands
    # 5. Block disallowed commands with clear error
```

**How It Works:**
1. SDK calls `bash_security_hook` before every `Bash` tool use
2. Hook extracts command name from command string (e.g., `npm install` → `npm`)
3. Hook checks if command is in project's security profile (dynamic allowlist)
4. For sensitive commands (git, rm, kill, etc.), run specialized validators
5. Hook returns block decision if command not allowed
6. SDK prevents tool execution if blocked

**Security Profile:** `project_analyzer.py`
```python
class SecurityProfile:
    base_commands: set[str]      # Core shell utilities (ls, cd, cat, etc.)
    stack_commands: set[str]     # Detected from project (npm, python, etc.)
    custom_commands: set[str]    # User-defined in .auto-claude-allowlist

    def get_all_allowed_commands(self) -> set[str]:
        return self.base_commands | self.stack_commands | self.custom_commands
```

**Dynamic Detection:**
- Analyzer scans `package.json` (Node), `requirements.txt` (Python), etc.
- Adds detected tools to `stack_commands`
- Caches profile to `.auto-claude-security.json`
- Profile updates when project dependencies change

**Special Validators:** `security/validator.py`
- `validate_git_command` - Block `git push --force`
- `validate_rm_command` - Block `rm -rf /` or `rm -rf .*`
- `validate_chmod_command` - Block dangerous permission changes
- `validate_pkill_command` - Block killing system processes
- Database validators (psql, mysql, mongosh) - Block DROP DATABASE
- Shell validators (bash, sh, zsh) - Block shell escapes with `-c`

### OpenAI Gap

OpenAI API has **no hook system**. Function calling returns tool calls but doesn't provide interception points for validation.

### Porting Requirements

#### Command Validation Wrapper

**Architecture:**
```python
class CommandValidator:
    """
    Validates bash commands before execution.
    Ports Claude SDK's PreToolUse hook functionality to OpenAI.
    """

    def __init__(self, project_dir: Path):
        from security import get_security_profile
        self.profile = get_security_profile(project_dir)
        from security.validator import VALIDATORS
        self.validators = VALIDATORS

    def validate_command(self, command: str) -> tuple[bool, str]:
        """
        Validate a bash command string.

        Returns:
            (is_allowed, reason) tuple
        """
        # 1. Extract command names
        from security import extract_commands
        commands = extract_commands(command)

        # 2. Check each command against allowlist
        from project_analyzer import is_command_allowed
        for cmd in commands:
            allowed, reason = is_command_allowed(cmd, self.profile)
            if not allowed:
                return False, reason

            # 3. Run specialized validators
            if cmd in self.validators:
                validator = self.validators[cmd]
                is_valid, validation_reason = validator(command)
                if not is_valid:
                    return False, validation_reason

        return True, ""
```

**Integration Point:**
```python
class OpenAIProvider:
    def __init__(self, project_dir: Path):
        self.command_validator = CommandValidator(project_dir)

    async def execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        if tool_name == "Bash":
            command = tool_input["command"]

            # Validate BEFORE execution
            is_allowed, reason = self.command_validator.validate_command(command)
            if not allowed:
                return {
                    "error": f"Command blocked by security policy: {reason}",
                    "command": command
                }

            # Execute if allowed
            return await self._execute_bash_command(command)

        # ... other tools
```

### Specialized Validators

**Existing Validators to Reuse:**

| Validator | Purpose | Location |
|-----------|---------|----------|
| `validate_git_command` | Block `git push --force` | `security/git_validators.py` |
| `validate_rm_command` | Block `rm -rf /`, `rm -rf .*` | `security/filesystem_validators.py` |
| `validate_chmod_command` | Block dangerous permissions | `security/filesystem_validators.py` |
| `validate_pkill_command` | Block killing system processes | `security/process_validators.py` |
| `validate_dropdb_command` | Block `DROP DATABASE` | `security/database_validators.py` |
| `validate_shell_c_command` | Block `bash -c "evil"` | `security/shell_validators.py` |

**Porting Strategy:**
- Import validators from `security` module (no code duplication)
- Call validators directly from `CommandValidator`
- Validators return `(is_allowed, reason)` tuples
- Block command execution if any validator fails

### Dynamic Allowlist Detection

**Reuse Existing System:**
- `project_analyzer.py` detects project stack
- Creates `SecurityProfile` with base + stack commands
- Caches to `.auto-claude-security.json`
- OpenAI provider uses same `get_security_profile()` function

**No Changes Required:**
```python
# This works for both Claude SDK and OpenAI
from security import get_security_profile
profile = get_security_profile(project_dir)
allowed_commands = profile.get_all_allowed_commands()
```

### Feasibility Assessment

| Component | Complexity | Notes |
|-----------|------------|-------|
| Command validation logic | Low | Reuse existing `security` module |
| Specialized validators | Low | Import from `security/validator.py` |
| Dynamic allowlist detection | Low | Reuse `project_analyzer.py` |
| Hook integration point | Medium | Must wrap every tool execution |

**Overall Feasibility:** High

### Recommendation

**Implement in Phase 1:**
1. Create `CommandValidator` class wrapping existing security module
2. Add validation call in `OpenAIProvider.execute_tool()` before bash execution
3. Return clear error messages for blocked commands
4. Reuse all existing validators (no code duplication)

## Tool Filtering by Agent Type

### Claude SDK Implementation

**Agent Configuration:** `agents/tools_pkg/models.py`
```python
AGENT_CONFIGS = {
    "planner": {
        "allowed_tools": [
            "Read", "Write", "Edit", "Glob", "Grep",
            "Bash", "WebSearch", "WebFetch",
            "Task", "AskUserQuestion", "EnterPlanMode"
        ],
        "required_mcp_servers": ["context7", "graphiti"]
    },
    "coder": {
        "allowed_tools": [
            "Read", "Write", "Edit", "Glob", "Grep",
            "Bash", "WebSearch", "WebFetch"
        ],
        "required_mcp_servers": ["context7"]
    },
    "qa_reviewer": {
        "allowed_tools": [
            "Read", "Glob", "Grep",
            "WebSearch", "WebFetch",
            "AskUserQuestion"
        ],
        "required_mcp_servers": ["context7", "electron", "puppeteer"]
    }
}
```

**How It Works:**
- `create_client()` calls `get_allowed_tools(agent_type, ...)`
- Returns filtered list based on agent's role
- SDK only exposes allowed tools to agent
- Prevents misuse (e.g., Coder can't use `Task` to spawn subagents)

### OpenAI Gap

OpenAI API has **no tool filtering**. You provide all function schemas, and the model can call any of them.

### Porting Requirements

#### Tool Filtering Implementation

**Approach 1: Filter Function Schemas**
```python
class OpenAIProvider:
    def __init__(self, agent_type: str):
        # Get allowed tools for this agent
        from agents.tools_pkg import get_allowed_tools
        self.allowed_tools = get_allowed_tools(
            agent_type,
            project_capabilities,
            linear_enabled,
            mcp_config
        )

        # Only convert allowed tools to function schemas
        self.function_schemas = [
            self._tool_to_function_schema(tool)
            for tool in self.allowed_tools
        ]

    async def chat(self, message: str):
        # OpenAI only sees allowed tools
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=self.history,
            tools=self.function_schemas  # Only allowed tools
        )
```

**Approach 2: Validate Tool Calls (Defense in Depth)**
```python
async def execute_tool(self, tool_name: str, tool_input: dict):
    # Double-check tool is allowed (even if schema was filtered)
    if tool_name not in self.allowed_tools:
        raise PermissionDeniedError(
            f"Agent {self.agent_type} not allowed to use tool {tool_name}"
        )

    # Execute tool
    return await self._execute_tool_unsafe(tool_name, tool_input)
```

**Recommendation:** Use both approaches for defense in depth.

### Feasibility Assessment

| Component | Complexity | Notes |
|-----------|------------|-------|
| Tool schema filtering | Low | Use existing `get_allowed_tools()` |
| Tool call validation | Low | Simple allowlist check |
| Agent-specific tool lists | None | Already implemented |

**Overall Feasibility:** High

### Recommendation

**Implement in Phase 1:**
1. Filter function schemas based on agent type
2. Add validation in `execute_tool()` (defense in depth)
3. Reuse existing `AGENT_CONFIGS` from `agents/tools_pkg/models.py`

## Security Settings File

### Claude SDK Implementation

**File:** `project_dir/.claude_settings.json`

**Generation:** `core/client.py:822-827`
```python
settings_file = project_dir / ".claude_settings.json"
with open(settings_file, "w", encoding="utf-8") as f:
    json.dump(security_settings, f, indent=2)
```

**Purpose:**
- SDK reads this file to enforce security
- Contains sandbox, permissions, and hooks configuration
- Generated per-client creation (project-specific)
- Includes worktree permissions when applicable

### OpenAI Gap

OpenAI API doesn't read security settings files.

### Porting Requirements

**Options:**

1. **Generate for documentation** - Create file for reference but not enforced
2. **Implement enforcement** - Read file in `OpenAIProvider.__init__()` and enforce
3. **Skip file** - Keep settings in memory only

**Recommendation:** Option 2 - Generate and enforce to maintain parity with Claude SDK.

**Implementation:**
```python
class OpenAIProvider:
    def __init__(self, project_dir: Path, agent_type: str):
        self.project_dir = project_dir

        # Generate security settings (reuse Claude SDK logic)
        self.security_settings = self._build_security_settings(
            project_dir, agent_type
        )

        # Write to file (for transparency/debugging)
        settings_file = project_dir / ".claude_settings.json"
        with open(settings_file, "w") as f:
            json.dump(self.security_settings, f, indent=2)

        # Enforce settings
        self.permission_wrapper = PermissionWrapper(
            project_dir,
            self.security_settings
        )
        self.command_validator = CommandValidator(project_dir)

    def _build_security_settings(self, project_dir: Path, agent_type: str) -> dict:
        """Reuse security settings generation from core/client.py."""
        # Import from core/client to maintain consistency
        from core.client import _build_security_settings
        return _build_security_settings(project_dir, agent_type)
```

### Feasibility Assessment

| Component | Complexity | Notes |
|-----------|------------|-------|
| Settings generation | Low | Reuse code from `core/client.py` |
| Settings enforcement | Medium | Integrate with wrappers |
| File I/O | Low | Simple JSON write/read |

**Overall Feasibility:** High

### Recommendation

**Implement in Phase 1:**
1. Create `_build_security_settings()` helper (extract from `core/client.py`)
2. Share helper between Claude SDK and OpenAI provider
3. Write `.claude_settings.json` for transparency
4. Enforce settings through `PermissionWrapper` and `CommandValidator`

## Implementation Phases

### Phase 1: Core Security (High Priority)

**Goal:** Implement basic security parity with Claude SDK

**Components:**
1. ✅ **Command Validation** - Reuse `security` module
2. ✅ **File Permissions** - Implement `PermissionWrapper`
3. ✅ **Tool Filtering** - Filter function schemas by agent type
4. ✅ **Settings File** - Generate and enforce `.claude_settings.json`

**Timeline:** 1 week

**Acceptance Criteria:**
- [ ] Commands validated against allowlist before execution
- [ ] File operations restricted to project directory
- [ ] Agents only see allowed tools
- [ ] Security settings file generated and enforced

### Phase 2: Enhanced Permissions (Medium Priority)

**Goal:** Improve worktree and path handling

**Components:**
1. ✅ **Worktree Detection** - Grant original project access
2. ✅ **Path Validation** - Handle relative and absolute paths correctly
3. ✅ **MCP Tool Permissions** - Enforce per-tool permissions

**Timeline:** 3 days

**Acceptance Criteria:**
- [ ] Worktrees can access original project's `.auto-claude/`
- [ ] Both `./src/file.ts` and `/absolute/path/to/file.ts` work
- [ ] MCP tools have correct permissions

### Phase 3: OS Sandboxing (Low Priority, High Complexity)

**Goal:** Implement OS-level isolation for bash commands

**Components:**
1. ⚠️ **Working Directory Restriction** - `cwd` parameter to subprocess
2. ⚠️ **Environment Scoping** - Restricted environment variables
3. ❌ **True Sandbox** - Container/chroot (platform-specific)

**Timeline:** 1-2 weeks (optional)

**Acceptance Criteria:**
- [ ] Bash commands cannot escape working directory
- [ ] Environment variables are scoped
- [ ] Optional: OS-level sandbox for high-security scenarios

**Note:** Full sandbox may not be achievable without significant OS integration.

## Security Parity Matrix

| Security Feature | Claude SDK | OpenAI (Phase 1) | OpenAI (Phase 2) | OpenAI (Phase 3) |
|-----------------|------------|------------------|------------------|------------------|
| **Command Validation** | ✅ Native | ✅ Wrapper | ✅ Wrapper | ✅ Wrapper |
| **File Permissions** | ✅ Native | ✅ Wrapper | ✅ Enhanced | ✅ Enhanced |
| **Tool Filtering** | ✅ Native | ✅ Schema Filter | ✅ Schema Filter | ✅ Schema Filter |
| **Sandbox** | ✅ Native | ❌ None | ❌ None | ⚠️ Partial |
| **PreToolUse Hooks** | ✅ Native | ✅ Manual | ✅ Manual | ✅ Manual |
| **Worktree Support** | ✅ Native | ❌ Basic | ✅ Full | ✅ Full |
| **Settings File** | ✅ Native | ✅ Generated | ✅ Generated | ✅ Generated |

**Legend:**
- ✅ = Implemented
- ❌ = Not implemented
- ⚠️ = Partially implemented

## Risk Assessment

### Technical Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Permission wrapper bugs** | High | Comprehensive testing, security audit |
| **Command validation bypass** | High | Defense in depth (validation + wrapper) |
| **Path traversal attacks** | Medium | Strict path resolution, reject `..` |
| **Worktree permission errors** | Medium | Thorough testing of worktree scenarios |
| **No true sandbox** | Medium | Document limitation, recommend Claude for high-security |

### Security Gaps

**Even with full implementation, OpenAI provider will have:**
1. **No OS-level sandbox** - Commands can theoretically escape (mitigated by path validation)
2. **No SDK-enforced permissions** - Relies on application-layer enforcement
3. **No native hooks** - Manual validation may have edge cases
4. **Higher attack surface** - More code = more potential vulnerabilities

**Recommendation:**
- Document security differences clearly
- Recommend Claude SDK for high-security scenarios
- Use OpenAI provider only for trusted projects/environments

## Testing Requirements

### Unit Tests

**File:** `tests/test_openai_security.py`

```python
def test_command_validation_blocks_disallowed():
    """Verify disallowed commands are blocked."""
    provider = OpenAIProvider(project_dir, agent_type="coder")
    is_allowed, reason = provider.command_validator.validate_command("evil_command")
    assert not is_allowed

def test_file_permissions_block_escape():
    """Verify file operations cannot escape project directory."""
    provider = OpenAIProvider(project_dir, agent_type="coder")
    with pytest.raises(PermissionDeniedError):
        await provider.permission_wrapper.execute_tool(
            "Read",
            {"file_path": "/etc/passwd"}
        )

def test_tool_filtering_by_agent_type():
    """Verify agents only see allowed tools."""
    coder = OpenAIProvider(project_dir, agent_type="coder")
    planner = OpenAIProvider(project_dir, agent_type="planner")

    # Coder should not have Task tool
    assert "Task" not in coder.allowed_tools

    # Planner should have Task tool
    assert "Task" in planner.allowed_tools
```

### Integration Tests

**File:** `tests/test_openai_security_integration.py`

```python
async def test_security_end_to_end():
    """Verify full security stack in realistic scenario."""
    provider = OpenAIProvider(project_dir, agent_type="coder")

    # Agent tries to read file outside project
    response = await provider.process_message(
        "Read the contents of /etc/passwd"
    )

    # Should be blocked
    assert "Permission denied" in response
    assert "/etc/passwd" in response

async def test_command_validation_in_agent_loop():
    """Verify commands validated in realistic agent workflow."""
    provider = OpenAIProvider(project_dir, agent_type="coder")

    # Agent tries to run disallowed command
    response = await provider.process_message(
        "Run 'evil_command --do-something'"
    )

    # Should be blocked
    assert "blocked by security policy" in response
```

### Security Audit

**Before production use:**
1. ✅ Code review by security expert
2. ✅ Penetration testing (path traversal, command injection)
3. ✅ Edge case testing (symlinks, worktrees, unusual paths)
4. ✅ Performance testing (validation overhead)

## Conclusion

### Summary of Porting Requirements

**Must Implement (Phase 1):**
1. ✅ `CommandValidator` class - Wrap existing `security` module
2. ✅ `PermissionWrapper` class - Enforce file permissions
3. ✅ Tool schema filtering - Use `get_allowed_tools()`
4. ✅ Settings generation - Reuse `_build_security_settings()`

**Should Implement (Phase 2):**
1. ✅ Worktree permission detection
2. ✅ Enhanced path validation
3. ✅ MCP tool permissions

**Nice to Have (Phase 3):**
1. ⚠️ Working directory restriction for subprocess
2. ⚠️ Environment variable scoping
3. ❌ OS-level sandbox (container/chroot)

### Feasibility Verdict

**Can we achieve full security parity?** ❌ No

**Can we achieve acceptable security parity?** ✅ Yes

With Phases 1 and 2 implemented, OpenAI provider will have **80% security parity** with Claude SDK:
- ✅ Command validation (100% parity)
- ✅ File permissions (100% parity)
- ✅ Tool filtering (100% parity)
- ❌ OS sandbox (0% parity - not possible without OS integration)

**Recommendation:** Implement Phases 1-2, document Phase 3 as future work, clearly communicate security limitations to users.

### Next Steps

1. ✅ Create `core/providers/openai/security.py` module
2. ✅ Implement `CommandValidator` class
3. ✅ Implement `PermissionWrapper` class
4. ✅ Add integration to `OpenAIProvider`
5. ✅ Write comprehensive tests
6. ✅ Security audit before production use
7. ✅ Document security differences from Claude SDK

---

**Document Status:** Analysis Complete
**Next Phase:** Implementation Planning
**Estimated Effort:** 1-2 weeks for Phase 1-2
