# Security Wrapper Design for OpenAI Provider

## Overview

This document designs a universal security wrapper that applies Auto Code's security model to the OpenAI provider. The wrapper replicates Claude SDK's multi-layered security (sandbox, permissions, hooks) for OpenAI's function calling API.

**Context**: OpenAI SDK lacks built-in security features. This wrapper bridges that gap by porting Claude's security model to OpenAI.

## Current Security Architecture (Claude SDK)

### Security Layers in `core/client.py`

```python
# From apps/backend/core/client.py (lines 650-656)
"""
Security layers (defense in depth):
1. Sandbox - OS-level bash command isolation prevents filesystem escape
2. Permissions - File operations restricted to project_dir only
3. Security hooks - Bash commands validated against an allowlist
   (see security.py for allowed commands)
4. Tool filtering - Each agent type only sees relevant tools (prevents misuse)
"""
```

### Layer 1: Sandbox

**Implementation** (Claude SDK):
```python
# From core/client.py line 770
security_settings = {
    "sandbox": {
        "enabled": True,
        "autoAllowBashIfSandboxed": True
    }
}
```

**Purpose**: OS-level process isolation for Bash commands
- Prevents filesystem escape via shell exploits
- Runs commands in isolated subprocess
- SDK handles this internally

**Feasibility for OpenAI**: **LOW**
- OpenAI SDK has no sandbox concept
- Would require OS-level integration (containers, chroot, namespaces)
- **Recommendation**: Defer to later phase, focus on higher-layer security first

### Layer 2: File Permissions

**Implementation** (Claude SDK):
```python
# From core/client.py lines 771-819
security_settings = {
    "permissions": {
        "defaultMode": "acceptEdits",
        "allow": [
            # Allow all file operations within the project directory
            "Read(./**)",
            "Write(./**)",
            "Edit(./**)",
            "Glob(./**)",
            "Grep(./**)",
            # Also allow absolute paths
            f"Read({project_path_str}/**)",
            f"Write({project_path_str}/**)",
            # Bash permission granted here, but actual commands validated by bash_security_hook
            "Bash(*)",
            # Allow web tools
            "WebFetch(*)",
            "WebSearch(*)",
            # Allow MCP tools
            *[f"{tool}(*)" for tool in CONTEXT7_TOOLS],
            # ... more MCP tools
        ]
    }
}
```

**Purpose**: Restrict file operations to allowed paths
- Uses allowlist pattern: `Operation(path_pattern)`
- Supports relative (`./**`) and absolute paths
- Wildcard matching for subdirectories

**Feasibility for OpenAI**: **HIGH**
- Can implement in wrapper layer
- Intercept file-related function calls
- Validate paths before execution
- **Implementation strategy**: Pre-validation hook for file operations

### Layer 3: Security Hooks (Command Allowlisting)

**Implementation** (Claude SDK):
```python
# From core/client.py lines 972-975
"hooks": {
    "PreToolUse": [
        HookMatcher(matcher="Bash", hooks=[bash_security_hook])
    ]
}
```

**Hook Implementation** (from `security/hooks.py`):
```python
async def bash_security_hook(
    input_data: dict[str, Any],
    tool_use_id: str | None = None,
    context: Any | None = None,
) -> dict[str, Any]:
    """
    Pre-tool-use hook that validates bash commands using dynamic allowlist.

    Returns:
        Empty dict to allow, or {"decision": "block", "reason": "..."} to block
    """
    # 1. Validate tool_input structure
    tool_input = input_data.get("tool_input")
    if not isinstance(tool_input, dict):
        return {"decision": "block", "reason": "Invalid tool_input"}

    # 2. Extract command
    command = tool_input.get("command", "")
    if not command:
        return {}

    # 3. Get security profile for project
    profile = get_security_profile(Path(cwd))

    # 4. Extract all commands from command string
    commands = extract_commands(command)

    # 5. Check each command against allowlist
    for cmd in commands:
        is_allowed, reason = is_command_allowed(cmd, profile)
        if not is_allowed:
            return {"decision": "block", "reason": reason}

        # 6. Additional validation for sensitive commands
        if cmd in VALIDATORS:
            validator = VALIDATORS[cmd]
            validation_ok, validation_reason = validator(cmd_segment)
            if not validation_ok:
                return {"decision": "block", "reason": validation_reason}

    return {}  # Allow
```

**Security Profile** (from `project_analyzer.py`):
```python
class SecurityProfile:
    """Dynamic security profile based on detected project stack"""

    base_commands: set[str]  # Always allowed (ls, cat, cd, etc.)
    stack_commands: set[str]  # Detected from project (npm, python, git)
    custom_commands: set[str]  # User-defined allowlist

    def get_all_allowed_commands(self) -> set[str]:
        """Union of all command sources"""
        return self.base_commands | self.stack_commands | self.custom_commands
```

**Command Validation Flow**:
1. **Base commands**: Core shell utilities (ls, cat, cd, grep, etc.) - always allowed
2. **Stack commands**: Detected from project structure (npm for Node.js, python for Python, etc.)
3. **Custom commands**: User-defined allowlist (`.auto-claude-commands.json`)
4. **Sensitive validators**: Extra validation for dangerous commands (git commit scans for secrets, rm checks paths, etc.)

**Feasibility for OpenAI**: **HIGH**
- Can replicate hook pattern in wrapper
- Reuse existing `bash_security_hook` implementation
- Intercept function calls before execution
- **Implementation strategy**: Wrapper-level validation middleware

### Layer 4: Tool Filtering

**Implementation** (from `agents/tools_pkg/models.py`):
```python
AGENT_CONFIGS = {
    "coder": {
        "allowed_tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep", ...],
        "mcp_servers": ["context7", "auto-claude"]
    },
    "qa_reviewer": {
        "allowed_tools": ["Read", "Bash", ...],  # More restrictive
        "mcp_servers": ["context7", "electron", "puppeteer"]
    },
    # ... per-agent configurations
}
```

**Purpose**: Each agent type only sees relevant tools
- Prevents misuse (e.g., Coder agent shouldn't use Electron MCP tools)
- Reduces context window bloat
- Phase-aware tool configuration

**Feasibility for OpenAI**: **HIGH**
- Can implement in wrapper
- Filter function definitions passed to OpenAI
- Reuse existing `AGENT_CONFIGS` logic
- **Implementation strategy**: Function filtering at API call time

## Proposed Security Wrapper for OpenAI

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Agent Layer                               │
│  (agents/planner.py, agents/coder.py, agents/qa_reviewer.py)     │
└────────────────────────────┬────────────────────────────────────┘
                             │ calls create_client(provider="openai")
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Security Wrapper Layer                         │
│  (NEW: core/providers/openai/security_wrapper.py)               │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Pre-Execution Hook (openai_function_guard)               │ │
│  │  - Validates function inputs before calling OpenAI         │ │
│  │  - Checks file permissions                                │ │
│  │  - Validates bash commands                                │ │
│  │  - Enforces tool allowlist                                │ │
│  └────────────────────────────────────────────────────────────┘ │
│                             │                                   │
│                             ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Post-Execution Hook (openai_result_filter)               │ │
│  │  - Validates function outputs                             │ │
│  │  - Sanitizes file paths                                   │ │
│  │  - Checks for blocked operations                          │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      OpenAI SDK                                  │
│  (openai Python package - chat completions API)                 │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Design

#### File 1: `core/providers/openai/security_wrapper.py`

```python
"""
Security Wrapper for OpenAI Provider
====================================

Applies Auto Code's security model to OpenAI's function calling API.
Replicates Claude SDK's security layers (permissions, hooks, filtering).

This wrapper:
1. Intercepts function calls before OpenAI execution
2. Validates inputs against security policies
3. Enforces file permissions
4. Validates bash commands via allowlist
5. Filters tools based on agent type
"""

from pathlib import Path
from typing import Any, Callable

from security import (
    SecurityProfile,
    bash_security_hook,
    get_security_profile,
)
from agents.tools_pkg import get_allowed_tools


class OpenAI SecurityWrapper:
    """
    Wraps OpenAI client with security validation.

    This class provides pre/post execution hooks that replicate
    Claude SDK's security model for OpenAI's function calling API.
    """

    def __init__(
        self,
        project_dir: Path,
        spec_dir: Path,
        agent_type: str = "coder",
    ):
        """
        Initialize security wrapper.

        Args:
            project_dir: Project root directory (for permissions)
            spec_dir: Spec directory (for settings)
            agent_type: Agent type for tool filtering
        """
        self.project_dir = project_dir.resolve()
        self.spec_dir = spec_dir.resolve()
        self.agent_type = agent_type

        # Get security profile for command allowlisting
        self.security_profile = get_security_profile(project_dir)

        # Get allowed tools for this agent type
        self.allowed_tools = get_allowed_tools(
            agent_type,
            project_capabilities={},  # From project_analyzer
            linear_enabled=False,
            mcp_config={},
        )

    async def validate_function_call(
        self,
        function_name: str,
        function_arguments: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """
        Pre-execution validation for OpenAI function calls.

        This replicates Claude SDK's PreToolUse hook behavior.

        Args:
            function_name: Name of the function being called
            function_arguments: Arguments passed to the function

        Returns:
            (is_allowed, error_message) tuple
            - (True, None) if allowed
            - (False, reason) if blocked
        """
        # 1. Tool filtering - check if function is in allowed list
        if function_name not in self.allowed_tools:
            return False, f"Tool '{function_name}' not allowed for {self.agent_type} agent"

        # 2. File permissions - validate file operations
        if function_name in ("Read", "Write", "Edit", "Glob", "Grep"):
            is_allowed, reason = self._validate_file_operation(
                function_name, function_arguments
            )
            if not is_allowed:
                return False, reason

        # 3. Command allowlisting - validate bash commands
        if function_name == "Bash":
            is_allowed, reason = await self._validate_bash_command(
                function_arguments
            )
            if not is_allowed:
                return False, reason

        # 4. Web tools - no additional validation needed
        # (Claude SDK allows WebFetch/WebSearch without restrictions)
        if function_name in ("WebFetch", "WebSearch"):
            return True, None

        # 5. MCP tools - validate server is allowed
        # (MCP tools are prefixed with server name, e.g., "context7_query")
        if function_name.startswith(("context7_", "linear_", "graphiti_")):
            return True, None  # Already filtered by allowed_tools

        return True, None

    def _validate_file_operation(
        self,
        operation: str,
        arguments: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """
        Validate file operation paths against security policy.

        Ensures file paths are within the allowed project directory.

        Args:
            operation: File operation type (Read, Write, Edit, Glob, Grep)
            arguments: Function arguments containing file paths

        Returns:
            (is_allowed, error_message) tuple
        """
        # Extract file path from arguments
        # Path may be in 'file_path', 'path', 'pattern', etc.
        file_path = arguments.get("file_path") or arguments.get("path")

        if not file_path:
            return True, None  # No path to validate

        # Convert to Path object
        path_obj = Path(file_path)

        # Resolve to absolute path
        try:
            absolute_path = path_obj.resolve()
        except Exception:
            return False, f"Invalid file path: {file_path}"

        # Check if path is within allowed directories
        # Allow: project_dir, spec_dir, and worktree parent directories
        allowed_dirs = [self.project_dir, self.spec_dir]

        # Check if path starts with any allowed directory
        is_allowed = any(
            str(absolute_path).startswith(str(allowed_dir.resolve()))
            for allowed_dir in allowed_dirs
        )

        if not is_allowed:
            return False, (
                f"File access denied: {file_path} is outside allowed directories. "
                f"Filesystem access is restricted to the project directory."
            )

        return True, None

    async def _validate_bash_command(
        self,
        arguments: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """
        Validate bash command against security allowlist.

        Reuses the existing bash_security_hook from security.py.

        Args:
            arguments: Bash function arguments (must contain 'command')

        Returns:
            (is_allowed, error_message) tuple
        """
        command = arguments.get("command", "")
        if not command:
            return True, None  # Empty command, nothing to validate

        # Build input_data for bash_security_hook
        input_data = {
            "tool_name": "Bash",
            "tool_input": arguments,
            "cwd": str(self.project_dir),
        }

        # Call existing security hook
        result = await bash_security_hook(input_data)

        # bash_security_hook returns {} to allow, or {"decision": "block", "reason": "..."}
        if result.get("decision") == "block":
            return False, result.get("reason", "Command blocked by security policy")

        return True, None

    def filter_function_definitions(
        self,
        functions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Filter function definitions to only include allowed tools.

        This replicates Claude SDK's tool filtering at the provider level.

        Args:
            functions: All available function definitions

        Returns:
            Filtered list of function definitions
        """
        return [
            func for func in functions
            if func.get("name") in self.allowed_tools
        ]
```

#### File 2: `core/providers/openai/client.py` (Modified)

```python
"""
OpenAI Provider with Security Wrapper
=====================================

Wraps OpenAI SDK with security validation layer.
"""

from openai import AsyncOpenAI

from .security_wrapper import OpenAI SecurityWrapper


class OpenAIProvider:
    """
    OpenAI provider with security wrapper.

    This class wraps the OpenAI SDK to provide:
    - Agent session management
    - Tool/function calling with security validation
    - Message streaming
    """

    def __init__(
        self,
        api_key: str,
        project_dir: Path,
        spec_dir: Path,
        agent_type: str = "coder",
        model: str = "gpt-5.2",
    ):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            project_dir: Project root directory
            spec_dir: Spec directory
            agent_type: Agent type for tool filtering
            model: Model to use
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.project_dir = project_dir
        self.spec_dir = spec_dir

        # Initialize security wrapper
        self.security = OpenAI SecurityWrapper(
            project_dir=project_dir,
            spec_dir=spec_dir,
            agent_type=agent_type,
        )

    async def create_agent_session(
        self,
        name: str,
        starting_message: str,
    ) -> str:
        """Create an agent session (returns session_id)"""
        # OpenAI is stateless, so we manage session state manually
        session_id = f"openai_{name}_{int(time.time())}"
        # Store session context (messages, history)
        return session_id

    async def send_message(
        self,
        session_id: str,
        message: str,
    ) -> AsyncIterator[dict]:
        """
        Send message and stream response.

        This method:
        1. Calls OpenAI API with function definitions
        2. When model requests a function call, validates it via security wrapper
        3. Executes validated function calls
        4. Returns results to model
        5. Streams final response
        """
        while True:
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=session_history[session_id],
                functions=self._get_function_definitions(),
                function_call="auto",  # Let model decide when to call functions
            )

            # Check if model requested a function call
            if response.choices[0].finish_reason == "function_call":
                function_call = response.choices[0].message.function_call

                # SECURITY: Validate function call before execution
                is_allowed, error_msg = await self.security.validate_function_call(
                    function_name=function_call.name,
                    function_arguments=json.loads(function_call.arguments),
                )

                if not is_allowed:
                    # Block the function call and inform model
                    yield {
                        "type": "error",
                        "content": f"Function call blocked: {error_msg}",
                    }
                    break

                # Execute the validated function call
                result = await self._execute_function(
                    function_call.name,
                    json.loads(function_call.arguments),
                )

                # Add function result to conversation
                session_history[session_id].append({
                    "role": "assistant",
                    "content": None,
                    "function_call": function_call,
                })
                session_history[session_id].append({
                    "role": "function",
                    "name": function_call.name,
                    "content": json.dumps(result),
                })

                # Continue loop to get next response from model
                continue

            # Stream final response
            yield {
                "type": "text",
                "content": response.choices[0].message.content,
            }
            break

    def _get_function_definitions(self) -> list[dict]:
        """
        Get function definitions for OpenAI API.

        Filters functions to only include allowed tools.
        """
        all_functions = [
            # File operations
            {"name": "Read", "description": "...", "parameters": {...}},
            {"name": "Write", "description": "...", "parameters": {...}},
            # Bash
            {"name": "Bash", "description": "...", "parameters": {...}},
            # Web tools
            {"name": "WebSearch", "description": "...", "parameters": {...}},
            # MCP tools
            {"name": "context7_query", "description": "...", "parameters": {...}},
            # ... more tools
        ]

        # SECURITY: Filter to only allowed tools for this agent type
        return self.security.filter_function_definitions(all_functions)
```

### Security Wrapper API

#### `OpenAI SecurityWrapper.validate_function_call()`

**Purpose**: Pre-execution validation for all function calls

**Validation flow**:
1. **Tool filtering**: Check if function is in `allowed_tools` for agent type
2. **File permissions**: Validate file paths are within `project_dir` and `spec_dir`
3. **Command allowlisting**: Validate bash commands via `bash_security_hook()`
4. **Return**: `(True, None)` to allow, `(False, reason)` to block

**Reuses existing components**:
- `bash_security_hook()` from `security/hooks.py`
- `get_security_profile()` from `security/profile.py`
- `get_allowed_tools()` from `agents/tools_pkg/models.py`

#### `OpenAI SecurityWrapper._validate_file_operation()`

**Purpose**: Enforce file permissions

**Validation logic**:
1. Extract file path from function arguments
2. Resolve to absolute path
3. Check if path starts with allowed directories:
   - `project_dir` (main project directory)
   - `spec_dir` (spec directory)
   - Original project's `.auto-claude/` (for worktree support)
4. Block with error message if outside allowed directories

**Replica of**: Claude SDK's `permissions.allow` configuration

#### `OpenAI SecurityWrapper._validate_bash_command()`

**Purpose**: Validate bash commands against allowlist

**Validation logic**:
1. Extract command from arguments
2. Build `input_data` dict for `bash_security_hook()`
3. Call existing `bash_security_hook()` function
4. Parse result (empty dict = allow, block dict = block)

**Reuses**: `bash_security_hook()` from `security/hooks.py`

**This is the key integration point** - the wrapper bridges OpenAI's function calling to Auto Code's existing security system.

#### `OpenAI SecurityWrapper.filter_function_definitions()`

**Purpose**: Filter tools at API call time

**Validation logic**:
1. Receive all available function definitions
2. Filter to only include functions in `allowed_tools`
3. Return filtered list to OpenAI API

**Replica of**: Claude SDK's `allowed_tools` parameter in `create_client()`

## Integration Points

### 1. Existing Security Module (No Changes Required)

The wrapper **reuses** existing security components:

- `security/bash_security_hook` - Command validation logic
- `security/profile.py` - Security profile caching
- `project_analyzer.py` - Stack detection and allowlist generation
- `agents/tools_pkg/models.py` - Agent tool configurations

**No modifications needed** - the wrapper calls these as-is.

### 2. Client Factory (`core/client.py`)

**Current code** (Claude-only):
```python
def create_client(
    project_dir: Path,
    spec_dir: Path,
    model: str,
    agent_type: str = "coder",
    ...
) -> ClaudeSDKClient:
    # Create Claude SDK client with security
    return ClaudeSDKClient(options=ClaudeAgentOptions(...))
```

**Enhanced code** (Multi-provider):
```python
def create_client(
    project_dir: Path,
    spec_dir: Path,
    model: str,
    agent_type: str = "coder",
    provider: str = "claude",  # NEW parameter
    ...
) -> ClaudeSDKClient | OpenAIProvider:
    """
    Create AI client with security.

    Args:
        provider: "claude" or "openai"
        ...
    """
    if provider == "claude":
        # Existing logic - Claude SDK has native security
        return ClaudeSDKClient(options=ClaudeAgentOptions(...))
    elif provider == "openai":
        # NEW - OpenAI provider with security wrapper
        from core.providers.openai import OpenAIProvider
        return OpenAIProvider(
            api_key=os.environ.get("OPENAI_API_KEY"),
            project_dir=project_dir,
            spec_dir=spec_dir,
            agent_type=agent_type,
            model=model,
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")
```

### 3. Agent Layer (No Changes Required)

Agents continue to use the same interface:

```python
# In agents/coder.py, agents/planner.py, etc.
from core.client import create_client

client = create_client(
    project_dir=project_dir,
    spec_dir=spec_dir,
    model="gpt-5.2",  # or "claude-sonnet-4.5-20250929"
    agent_type="coder",
    provider=os.environ.get("DEFAULT_PROVIDER", "claude"),  # NEW
)

# Agent code unchanged - client abstraction handles provider differences
response = await client.create_agent_session(...)
```

## Security Parity Matrix

| Security Feature | Claude SDK | OpenAI with Wrapper | Status |
|-----------------|------------|---------------------|--------|
| **File Permissions** | ✅ Native (permissions.allow) | ✅ Wrapper (_validate_file_operation) | **Full parity** |
| **Command Allowlisting** | ✅ Native (PreToolUse hook) | ✅ Wrapper (_validate_bash_command) | **Full parity** |
| **Tool Filtering** | ✅ Native (allowed_tools) | ✅ Wrapper (filter_function_definitions) | **Full parity** |
| **Sandbox** | ✅ Native (sandbox.enabled) | ❌ Not implemented | **Deferred** |
| **Bash Isolation** | ✅ OS-level subprocess isolation | ⚠️ Depends on Python subprocess | **Partial parity** |
| **PreToolUse Hooks** | ✅ Native (hooks.PreToolUse) | ✅ Wrapper (validate_function_call) | **Full parity** |
| **PostToolUse Hooks** | ✅ Native (hooks.PostToolUse) | ⚠️ Can be added | **Implementable** |

## Feasibility Assessment

### ✅ High Feasibility (Immediate Implementation)

1. **File Permissions** - Fully implementable in wrapper
   - Path validation logic is straightforward
   - Reuses existing project directory detection
   - **Estimated effort**: 1-2 days

2. **Command Allowlisting** - Fully implementable via wrapper
   - Reuses existing `bash_security_hook` function
   - No changes to security module needed
   - **Estimated effort**: 1 day

3. **Tool Filtering** - Fully implementable
   - Reuses existing `AGENT_CONFIGS` logic
   - Simple list filtering
   - **Estimated effort**: 0.5 day

### ⚠️ Medium Feasibility (Requires Additional Work)

4. **Sandbox** - Requires OS-level integration
   - Would need containerization (Docker, Firecracker)
   - Or OS namespaces (Linux only)
   - **Recommendation**: Defer to later phase, document as limitation
   - **Estimated effort**: 1-2 weeks (if implemented)

### ❌ Low Feasibility (Platform-Specific Limitations)

5. **Bash Process Isolation** - Limited by Python's subprocess module
   - Python subprocess provides some isolation but not OS-level sandbox
   - Windows: No equivalent to Linux's chroot/namespaces
   - **Recommendation**: Accept as limitation, rely on allowlist for security
   - **Estimated effort**: Not feasible without OS-level changes

## Implementation Phases

### Phase 1: Core Security Wrapper (Week 1)

**Goal**: Implement high-feasibility security features

**Tasks**:
1. Create `core/providers/openai/security_wrapper.py`
2. Implement `OpenAI SecurityWrapper` class
3. Implement `_validate_file_operation()`
4. Implement `_validate_bash_command()` (reusing `bash_security_hook`)
5. Implement `filter_function_definitions()`
6. Create unit tests for validation logic

**Deliverable**: Security wrapper with file permissions, command allowlisting, and tool filtering

### Phase 2: OpenAI Provider Integration (Week 2)

**Goal**: Integrate wrapper with OpenAI SDK

**Tasks**:
1. Create `core/providers/openai/client.py`
2. Implement `OpenAIProvider` class
3. Integrate `validate_function_call()` into function calling loop
4. Implement session management (stateless API)
5. Create integration tests

**Deliverable**: Working OpenAI provider with security wrapper

### Phase 3: Client Factory Enhancement (Week 2)

**Goal**: Multi-provider support in `create_client()`

**Tasks**:
1. Modify `core/client.py` to support `provider` parameter
2. Route to Claude or OpenAI based on provider
3. Backward compatibility testing (Claude-only workflows)
4. Update documentation

**Deliverable**: Unified `create_client()` supporting both providers

### Phase 4: Sandbox (Optional, Deferred)

**Goal**: OS-level process isolation for OpenAI

**Tasks**:
1. Research sandboxing options (Docker, Firecracker, namespaces)
2. Design sandbox architecture
3. Implement sandbox wrapper
4. Platform-specific handling (Windows, macOS, Linux)

**Deliverable**: Optional sandbox feature for OpenAI provider

## Testing Strategy

### Unit Tests

```python
# tests/providers/openai/test_security_wrapper.py

async def test_file_permission_validation():
    """Test file path validation"""
    wrapper = OpenAI SecurityWrapper(project_dir, spec_dir)

    # Should allow: project directory
    is_allowed, _ = wrapper._validate_file_operation(
        "Read",
        {"file_path": "./src/main.py"}
    )
    assert is_allowed is True

    # Should block: outside project directory
    is_allowed, reason = wrapper._validate_file_operation(
        "Read",
        {"file_path": "/etc/passwd"}
    )
    assert is_allowed is False
    assert "outside allowed directories" in reason


async def test_bash_command_validation():
    """Test bash command validation via security hook"""
    wrapper = OpenAI SecurityWrapper(project_dir, spec_dir)

    # Should allow: base command (ls)
    is_allowed, _ = await wrapper._validate_bash_command(
        {"command": "ls -la"}
    )
    assert is_allowed is True

    # Should block: disallowed command (rm /)
    is_allowed, reason = await wrapper._validate_bash_command(
        {"command": "rm -rf /"}
    )
    assert is_allowed is False


async def test_tool_filtering():
    """Test function definition filtering"""
    wrapper = OpenAI SecurityWrapper(project_dir, spec_dir, agent_type="coder")

    all_functions = [
        {"name": "Read", ...},
        {"name": "Write", ...},
        {"name": "Bash", ...},
        {"name": "ElectronTakeScreenshot", ...},  # Not allowed for coder
    ]

    filtered = wrapper.filter_function_definitions(all_functions)

    assert len(filtered) == 3  # Electron tool filtered out
    assert all(f["name"] in wrapper.allowed_tools for f in filtered)
```

### Integration Tests

```python
# tests/providers/openai/test_openai_provider_integration.py

async def test_openai_provider_blocks_disallowed_commands():
    """Test that OpenAI provider blocks disallowed bash commands"""
    provider = OpenAIProvider(
        api_key="test-key",
        project_dir=test_project_dir,
        spec_dir=test_spec_dir,
        agent_type="coder",
    )

    # Simulate agent requesting a disallowed command
    session_id = await provider.create_agent_session("test", "Run rm -rf /")

    responses = []
    async for response in provider.send_message(
        session_id,
        "Delete everything using rm -rf /"
    ):
        responses.append(response)

    # Should receive error, not execute command
    assert any("blocked" in r.get("content", "").lower() for r in responses)


async def test_openai_provider_allows_allowed_commands():
    """Test that OpenAI provider allows allowed bash commands"""
    provider = OpenAIProvider(...)

    session_id = await provider.create_agent_session("test", "List files")

    responses = []
    async for response in provider.send_message(
        session_id,
        "List files using ls -la"
    ):
        responses.append(response)

    # Should execute command and return results
    assert any("total" in r.get("content", "") for r in responses)
```

### Security Tests

```python
# tests/security/test_openai_wrapper_security.py

async def test_cannot_escape_project_directory():
    """Test that file operations cannot escape project directory"""
    wrapper = OpenAI SecurityWrapper(project_dir, spec_dir)

    # Try to read file outside project
    is_allowed, _ = wrapper._validate_file_operation(
        "Read",
        {"file_path": "../../../etc/passwd"}
    )
    assert is_allowed is False


async def test_cannot_execute_disallowed_commands():
    """Test that disallowed commands are blocked"""
    wrapper = OpenAI SecurityWrapper(project_dir, spec_dir)

    # Try to execute disallowed command (assuming stack doesn't include docker)
    is_allowed, _ = await wrapper._validate_bash_command(
        {"command": "docker run -it alpine sh"}
    )
    assert is_allowed is False


async def test_agent_type_tool_filtering():
    """Test that agent types only see their allowed tools"""
    coder_wrapper = OpenAI SecurityWrapper(project_dir, spec_dir, agent_type="coder")
    qa_wrapper = OpenAI SecurityWrapper(project_dir, spec_dir, agent_type="qa_reviewer")

    # Coder should not have Electron tools
    assert "electron_take_screenshot" not in coder_wrapper.allowed_tools

    # QA reviewer should have Electron tools (if Electron project detected)
    # (assuming project has Electron capabilities)
    assert "electron_take_screenshot" in qa_wrapper.allowed_tools
```

## Limitations and Risks

### Limitations

1. **No OS-level Sandbox**
   - OpenAI wrapper cannot provide OS-level process isolation
   - **Mitigation**: Rely on defense-in-depth (allowlist + permissions + validation)
   - **Risk**: Sophisticated exploits might bypass Python-level validation

2. **Stateless API**
   - OpenAI API is stateless (unlike Claude SDK's agent sessions)
   - **Mitigation**: Manual session management in wrapper
   - **Risk**: More complex session handling, potential for state bugs

3. **Function Calling Overhead**
   - Pre-validation adds latency to every function call
   - **Mitigation**: Cache security profiles, optimize validation logic
   - **Risk**: Slower execution compared to Claude SDK

### Risks

1. **Security Wrapper Bugs**
   - Bugs in wrapper logic could allow unauthorized operations
   - **Mitigation**: Comprehensive testing, security audit, defense-in-depth
   - **Severity**: HIGH

2. **Incomplete Parity**
   - Wrapper might miss edge cases that Claude SDK handles
   - **Mitigation**: Extensive testing, real-world validation, phased rollout
   - **Severity**: MEDIUM

3. **Performance Degradation**
   - Additional validation layers slow down OpenAI provider
   - **Mitigation**: Profile and optimize, set performance budgets
   - **Severity**: LOW

## Success Criteria

The security wrapper is complete when:

1. ✅ **File permissions enforced** - All file operations restricted to project directory
2. ✅ **Command allowlisting working** - Bash commands validated against security profile
3. ✅ **Tool filtering implemented** - Agent types only see allowed tools
4. ✅ **Existing components reused** - No changes to `security/` module required
5. ✅ **Unit tests passing** - All validation logic tested
6. ✅ **Integration tests passing** - OpenAI provider blocks disallowed operations
7. ✅ **Backward compatibility maintained** - Existing Claude-only workflows unaffected
8. ⚠️ **Sandbox optional** - Documented as limitation (can be added later)

## Next Steps

1. **Review this design** with security architect
2. **Approve implementation phases** with stakeholders
3. **Create implementation tasks** in project tracker
4. **Begin Phase 1** - Core security wrapper implementation
5. **Security audit** before production use

---

**Document Status**: Design Complete
**Next Phase**: Implementation (pending approval)
**Estimated Effort**: 2-3 weeks for Phases 1-3 (excluding optional sandbox)
