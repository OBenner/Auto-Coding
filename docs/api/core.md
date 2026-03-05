# Core API Reference

Complete reference for Auto Code's core infrastructure, including Claude SDK client configuration and security validation system.

## Overview

The core module provides foundational services used across all agents and sessions. It handles authentication, client creation, security validation, and command allowlisting.

**Key Components:**
1. **Client Module** - Claude SDK client factory with security hooks and MCP configuration
2. **Security Module** - Dynamic command allowlisting based on project stack detection
3. **Authentication** - OAuth token management for Claude SDK
4. **Platform Utilities** - Cross-platform compatibility layer

**Key Features:**
- Agent-specific tool permissions and MCP server configuration
- Three-layer security model (base, stack, custom commands)
- Project index caching for performance
- Windows system prompt limits handling
- Audit logging for security events

---

## Claude SDK Client

### Client Factory

Creates and configures Claude Agent SDK client instances with proper security hooks, tool permissions, and MCP server integration.

::: apps.backend.core.client
    options:
      show_root_heading: true
      show_source: false
      members:
        - create_client
        - invalidate_project_cache

**Usage Example:**
```python
from pathlib import Path
from core.client import create_client

# Create SDK client for coder agent
client = create_client(
    project_dir=Path("/path/to/project"),
    spec_dir=Path(".auto-claude/specs/001-feature"),
    model="claude-sonnet-4-5-20250929",
    agent_type="coder",
    max_thinking_tokens=10000
)

# Run agent session
response = client.create_agent_session(
    name="coder-agent-session",
    starting_message="Implement authentication feature"
)
```

**Agent Types:**
- `planner` - Planning agent with read-only access
- `coder` - Implementation agent with write access
- `qa_reviewer` - QA reviewer with test execution
- `qa_fixer` - QA fixer with write and test access

### Authentication

OAuth token management for Claude SDK authentication.

::: apps.backend.core.auth
    options:
      show_root_heading: true
      show_source: false
      members:
        - require_auth_token
        - get_sdk_env_vars
        - validate_token_not_encrypted

**Usage Example:**
```python
from core.auth import require_auth_token, get_sdk_env_vars

# Ensure valid auth token
token_valid = require_auth_token()

# Get environment variables for SDK
env_vars = get_sdk_env_vars()
```

### Platform Utilities

Cross-platform compatibility helpers.

::: apps.backend.core.platform
    options:
      show_root_heading: true
      show_source: false
      members:
        - is_windows
        - validate_cli_path

---

## Security System

### Overview

Auto Code uses a three-layer security model to validate bash commands dynamically based on project stack:

1. **Base Commands** - Core shell utilities (always allowed)
2. **Stack Commands** - Framework/language tools detected from project
3. **Custom Commands** - User-defined allowlist

**Modules:**
- `hooks.py` - Main security hook for command validation
- `profile.py` - Security profile management and caching
- `parser.py` - Command parsing and extraction
- `validator.py` - Command-specific validation logic
- `audit_logger.py` - Security event logging

### Security Hooks

Main pre-tool-use hook for bash command validation.

::: apps.backend.security.hooks
    options:
      show_root_heading: true
      show_source: false
      members:
        - bash_security_hook
        - validate_command

**Usage Example:**
```python
from security import bash_security_hook
from claude_agent_sdk.types import HookMatcher

# Register security hook with Claude SDK
client = ClaudeSDKClient(
    security_hooks=[
        HookMatcher(matcher="Bash", hooks=[bash_security_hook])
    ]
)
```

### Security Profile Management

Manages security profiles with project-specific command allowlists.

::: apps.backend.security.profile
    options:
      show_root_heading: true
      show_source: false
      members:
        - get_security_profile
        - reset_profile_cache

**Usage Example:**
```python
from pathlib import Path
from security import get_security_profile

# Get security profile for project
profile = get_security_profile(
    project_dir=Path("/path/to/project"),
    spec_dir=Path(".auto-claude/specs/001-feature")
)

# Check if command is allowed
if profile.is_command_allowed("npm"):
    print("npm is allowed")
```

### Command Parsing

Extracts and parses commands from shell strings.

::: apps.backend.security.parser
    options:
      show_root_heading: true
      show_source: false
      members:
        - extract_commands
        - split_command_segments
        - get_command_for_validation

**Usage Example:**
```python
from security import extract_commands

# Parse complex shell command
commands = extract_commands("npm install && npm test")
# Returns: ['npm', 'npm']
```

### Command Validators

Specialized validators for dangerous commands that require additional checks.

::: apps.backend.security.validator
    options:
      show_root_heading: true
      show_source: false
      members:
        - VALIDATORS
        - validate_bash_command
        - validate_git_command
        - validate_rm_command
        - validate_chmod_command
        - validate_kill_command

**Usage Example:**
```python
from security import validate_rm_command, validate_git_command

# Validate rm command (rejects dangerous patterns)
result = validate_rm_command("rm -f temp.txt")  # Allowed
result = validate_rm_command("rm -rf /")  # Blocked

# Validate git command (prevents destructive operations)
result = validate_git_command("git status")  # Allowed
result = validate_git_command("git push --force origin main")  # Blocked
```

### Git Validators

Specialized validators for Git operations.

::: apps.backend.security.git_validators
    options:
      show_root_heading: true
      show_source: false
      members:
        - validate_git_commit
        - validate_git_config

### Filesystem Validators

Validators for filesystem operations.

::: apps.backend.security.filesystem_validators
    options:
      show_root_heading: true
      show_source: false
      members:
        - validate_rm_command
        - validate_chmod_command

### Process Validators

Validators for process management commands.

::: apps.backend.security.process_validators
    options:
      show_root_heading: true
      show_source: false
      members:
        - validate_kill_command
        - validate_killall_command
        - validate_pkill_command

### Database Validators

Validators for database operations (prevents destructive actions).

::: apps.backend.security.database_validators
    options:
      show_root_heading: true
      show_source: false
      members:
        - validate_dropdb_command
        - validate_dropuser_command
        - validate_psql_command
        - validate_mysql_command
        - validate_mysqladmin_command
        - validate_redis_cli_command
        - validate_mongosh_command

### Shell Validators

Validators for shell interpreter commands.

::: apps.backend.security.shell_validators
    options:
      show_root_heading: true
      show_source: false
      members:
        - validate_shell_c_command
        - validate_init_script

### Tool Input Validation

Validates and sanitizes tool inputs for security.

::: apps.backend.security.tool_input_validator
    options:
      show_root_heading: true
      show_source: false
      members:
        - validate_tool_input
        - get_safe_tool_input

### Audit Logging

Security event logging for compliance and debugging.

::: apps.backend.security.audit_logger
    options:
      show_root_heading: true
      show_source: false
      members:
        - log_security_event
        - get_audit_logs
        - clear_audit_logs
        - export_audit_logs
        - get_audit_log_path

**Usage Example:**
```python
from security import log_security_event, get_audit_logs

# Log security event
log_security_event(
    event_type="command_blocked",
    command="rm -rf /",
    reason="Dangerous pattern detected",
    metadata={"severity": "critical"}
)

# Retrieve audit logs
logs = get_audit_logs(
    event_type="command_blocked",
    limit=100
)
```

---

## Project Context

### Project Analyzer

Analyzes project structure to detect tech stack and build security profiles.

::: apps.backend.project_analyzer
    options:
      show_root_heading: true
      show_source: false
      members:
        - SecurityProfile
        - is_command_allowed
        - needs_validation
        - BASE_COMMANDS

---

## Environment Variables

### Client Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `CLAUDE_CODE_OAUTH_TOKEN` | OAuth token for Claude SDK | Required |
| `ANTHROPIC_API_KEY` | Legacy API key (not recommended) | None |
| `AUTO_BUILD_MODEL` | Default model for agents | `claude-sonnet-4-5-20250929` |
| `MAX_THINKING_TOKENS` | Extended thinking budget | None |
| `DEBUG` | Enable debug output | `false` |

### Security Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `CUSTOM_ALLOWLIST_PATH` | Path to custom command allowlist | None |
| `SECURITY_PROFILE_CACHE_TTL` | Cache TTL in seconds | `300` |
| `ENABLE_AUDIT_LOGGING` | Enable security audit logs | `true` |

### MCP Server Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `CONTEXT7_ENABLED` | Enable Context7 MCP server | Detected |
| `LINEAR_ENABLED` | Enable Linear MCP server | `false` |
| `GRAPHITI_ENABLED` | Enable Graphiti memory | `true` |
| `ELECTRON_MCP_ENABLED` | Enable Electron testing | `false` |
| `PUPPETEER_MCP_ENABLED` | Enable Puppeteer testing | `false` |

---

## Security Model

### Three-Layer Defense

**Layer 1: Base Commands**
- Core shell utilities (ls, cat, grep, etc.)
- Always allowed across all projects
- Defined in `security.BASE_COMMANDS`

**Layer 2: Stack Commands**
- Framework/language tools (npm, pip, cargo, etc.)
- Detected from project analysis
- Added to profile automatically

**Layer 3: Custom Commands**
- User-defined allowlist
- Optional custom commands
- Loaded from `CUSTOM_ALLOWLIST_PATH`

### Command Validation Flow

```
1. Parse command → extract_commands()
2. Check if allowed → is_command_allowed()
3. Run specialized validator if needed → VALIDATORS[cmd]()
4. Log event → log_security_event()
5. Allow or block
```

### Security Profile Caching

Security profiles are cached for 5 minutes by default to improve performance:
- Cache key: Absolute path to project directory
- TTL: 300 seconds (configurable via `SECURITY_PROFILE_CACHE_TTL`)
- Invalidation: Automatic on TTL expiry or manual via `reset_profile_cache()`

### Dangerous Command Patterns

The following patterns are ALWAYS blocked:
- `rm -rf /` - Deletes entire filesystem
- `chmod 777 -R /` - Opens entire filesystem
- `kill -9 -1` - Kills all processes
- `git push --force origin main` - Destructive git operation
- `DROP DATABASE *` - Database destruction
- Shell metacharacters in untrusted input

---

## Error Handling

### Common Client Errors

**Authentication Failed:**
```
Error: Failed to authenticate with Claude SDK
```
**Solution:** Run `claude` CLI and login with `/login` command.

**Token Encrypted:**
```
Error: OAuth token is encrypted and cannot be read
```
**Solution:** Run `claude setup-token --print` and set `CLAUDE_CODE_OAUTH_TOKEN` env var.

**Model Not Available:**
```
Error: Model not available in region
```
**Solution:** Check data residency configuration or use different model.

### Common Security Errors

**Command Blocked:**
```
Error: Command 'rm -rf /' blocked by security policy
```
**Solution:** Review security profile and ensure command is safe. Add to custom allowlist if needed.

**Validator Failed:**
```
Error: Git command validation failed: force push to main branch
```
**Solution:** Use safer git operation (e.g., create feature branch instead of force push).

**Audit Log Error:**
```
Error: Failed to write security audit log
```
**Solution:** Check permissions on `.auto-claude/audit/` directory.

---

## Best Practices

### Client Usage

1. **Always use agent-specific client creation:**
   ```python
   # ✅ CORRECT - Agent-specific permissions
   client = create_client(agent_type="coder", ...)

   # ❌ WRONG - Generic client
   client = ClaudeSDKClient(...)
   ```

2. **Invalidate cache when project changes significantly:**
   ```python
   # After adding new dependencies
   invalidate_project_cache(project_dir)
   client = create_client(...)  # Will reload fresh index
   ```

3. **Use extended thinking for complex tasks:**
   ```python
   # Enable extended thinking for planner
   client = create_client(
       agent_type="planner",
       max_thinking_tokens=16000  # Max budget
   )
   ```

### Security Best Practices

1. **Always validate user input before shell execution:**
   ```python
   from security import validate_command

   if validate_command(user_input, project_dir):
       result = run_bash(user_input)
   ```

2. **Use security profiles instead of hardcoded allowlists:**
   ```python
   # ✅ CORRECT - Dynamic allowlist
   profile = get_security_profile(project_dir, spec_dir)

   # ❌ WRONG - Hardcoded allowlist
   ALLOWED = ["npm", "pip", "cargo"]
   ```

3. **Enable audit logging in production:**
   ```python
   # Set in environment
   export ENABLE_AUDIT_LOGGING=true

   # Review logs periodically
   logs = get_audit_logs(event_type="command_blocked")
   ```

4. **Never disable security hooks:**
   ```python
   # ❌ WRONG - Disabling security
   client = create_client(security_hooks=[])

   # ✅ CORRECT - Full security enabled
   client = create_client(agent_type="coder")
   ```

---

## See Also

- [Agents API Reference](./agents.md) - Agent system documentation
- [Memory API Reference](./memory.md) - Graphiti memory system
- [Backend API Reference](./backend-api.md) - Core module documentation
- [Security Model Diagram](../diagrams/security-model.mermaid) - Visual architecture
- [Authentication Guide](../guides/authentication.md) - OAuth setup instructions

---

**Version:** 2.8.0
**Last Updated:** 2026-03-05
**Maintained By:** Auto Code Team
