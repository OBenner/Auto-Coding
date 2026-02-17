# Migration Guide: Claude-Only to Multi-Provider Architecture

This guide documents the migration path from a Claude-only Auto Code installation to the multi-provider architecture that supports OpenAI (GPT-5.2/GPT-5) alongside Claude SDK.

## Overview

The multi-provider architecture is designed to be **backward compatible** by default. Existing Claude-based workflows continue to function without modification. Adding OpenAI support is entirely opt-in.

**Migration strategy:**
- No breaking changes to existing Claude workflows
- New environment variables activate multi-provider features
- Provider selection is configuration-driven, not code-driven
- Agent code (planner, coder, qa_reviewer, qa_fixer) requires no modifications

---

## Breaking Changes

### No Breaking Changes for Claude Users

The multi-provider architecture introduces **zero breaking changes** for users who continue using Claude as their sole provider. All existing behavior is preserved:

| Component | Change | Impact |
|-----------|--------|--------|
| `agents/` directory | No changes | None |
| `core/client.py` | Extended to support multi-provider factory | Backward compatible |
| `core/security.py` | No changes | None |
| `core/auth.py` | Extended to support multiple auth types | Backward compatible |
| `.env` file | New optional variables added | None (existing config still works) |
| CLI commands | Existing commands unchanged | None |
| MCP integration | Claude's native MCP unchanged | None |

### Potential Behavior Changes (Opt-In Only)

The following changes only take effect when explicitly configured:

| Change | Trigger | Mitigation |
|--------|---------|------------|
| Different model responses | Setting `AI_ENGINE_PROVIDER=openai` | Do not set this variable to keep Claude behavior |
| Custom MCP client (OpenAI) | Enabling OpenAI provider | Claude's native MCP is unaffected |
| Security wrapper (OpenAI) | Enabling OpenAI provider | Claude's native security is unaffected |
| API key authentication | Using OpenAI provider | Claude's OAuth continues as-is |

### Deprecation Notices

No current features are deprecated. The following **will not be deprecated**:
- Claude Agent SDK integration
- OAuth-based authentication
- Native MCP server support
- Built-in sandbox and security hooks

---

## Configuration Updates

### Step 1: Verify Existing Claude Configuration

Before enabling multi-provider support, verify your current Claude configuration is intact:

```bash
# Verify current provider (should return 'claude' or nothing)
echo $AI_ENGINE_PROVIDER

# Verify Claude API key is set
echo $ANTHROPIC_API_KEY | head -c 10  # Only show first 10 chars

# Test current Claude configuration
cd apps/backend
python run.py --validate-config
```

### Step 2: Add Provider Selection Variable (Optional)

To make Claude explicit (optional, it remains the default):

```bash
# apps/backend/.env
AI_ENGINE_PROVIDER=claude   # Explicit default (optional)
ANTHROPIC_API_KEY=sk-ant-your-existing-key
```

**Note:** If `AI_ENGINE_PROVIDER` is not set, the system defaults to `claude`. Setting it explicitly is optional.

### Step 3: Add OpenAI Credentials (To Enable OpenAI)

Only required if you want to use OpenAI as a provider:

```bash
# apps/backend/.env - ADD these lines to your existing .env
OPENAI_API_KEY=sk-proj-your-openai-api-key

# Optional: Specify OpenAI model (defaults to gpt-5.2)
OPENAI_MODEL=gpt-5.2

# Optional: Enable custom MCP client for OpenAI
OPENAI_CUSTOM_MCP_ENABLED=true

# Optional: Enable security wrapper for OpenAI
OPENAI_SECURITY_WRAPPER_ENABLED=true
```

### Step 4: Configure Provider Fallback (Optional)

Enable automatic fallback for resilience:

```bash
# apps/backend/.env
FALLBACK_ENABLED=true
FALLBACK_PROVIDER=claude       # Fall back to Claude if OpenAI fails
FALLBACK_ON_RATE_LIMIT=true
FALLBACK_ON_TIMEOUT=true
FALLBACK_ON_FEATURE_UNSUPPORTED=true

# Retry configuration
MAX_RETRIES=3
RETRY_BACKOFF_BASE=1    # seconds
RETRY_BACKOFF_MAX=60    # seconds
```

### Step 5: Configure Per-Agent Provider Routing (Optional)

Optionally route different agents to different providers:

```bash
# apps/backend/.env
# Use Claude for complex reasoning agents
PLANNER_PROVIDER=claude
QA_REVIEWER_PROVIDER=claude

# Use OpenAI for implementation agents (if desired)
CODER_PROVIDER=openai
QA_FIXER_PROVIDER=openai
```

### Complete .env Example

```bash
# apps/backend/.env (after migration)

# ── Core Provider Selection ──────────────────────────────────────────
AI_ENGINE_PROVIDER=claude   # Primary provider (claude | openai | litellm | openrouter)

# ── Claude Agent SDK ─────────────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-your-existing-key
CLAUDE_MODEL=claude-sonnet-4-5-20250929

# ── OpenAI (optional, for multi-provider) ────────────────────────────
OPENAI_API_KEY=sk-proj-your-openai-key
OPENAI_MODEL=gpt-5.2
OPENAI_CUSTOM_MCP_ENABLED=true
OPENAI_SECURITY_WRAPPER_ENABLED=true

# ── Fallback Configuration (optional) ────────────────────────────────
FALLBACK_ENABLED=true
FALLBACK_PROVIDER=claude
FALLBACK_ON_RATE_LIMIT=true
FALLBACK_ON_TIMEOUT=true
FALLBACK_ON_FEATURE_UNSUPPORTED=true

# ── Retry Configuration ───────────────────────────────────────────────
MAX_RETRIES=3
RETRY_BACKOFF_BASE=1
RETRY_BACKOFF_MAX=60

# ── Existing Configuration (unchanged) ───────────────────────────────
GRAPHITI_ENABLED=true
ELECTRON_MCP_ENABLED=false
```

---

## Model Mapping Reference

When switching to or from OpenAI, use this mapping to select equivalent models:

| Task | Claude Model | OpenAI Model | Notes |
|------|-------------|--------------|-------|
| Spec creation (Planner) | `claude-sonnet-4-5-20250929` | `gpt-5.2` | Complex reasoning capability tier |
| Code implementation (Coder) | `claude-sonnet-4-5-20250929` | `gpt-5.2` | Code generation capability tier |
| Quick tasks (fast agents) | `claude-haiku-4-20250929` | `gpt-5` | Cost/latency optimization tier |
| Complex architecture | `claude-sonnet-4-5-20250929` | `gpt-5.2` | Deep reasoning required |
| QA review | `claude-sonnet-4-5-20250929` | `gpt-5.2` | Issue detection capability |

**Important:** Model mappings are by capability tier, not exact functional parity. Expect different (but functionally equivalent) outputs when switching providers.

### Feature Availability by Provider

| Feature | Claude | OpenAI | Action Required |
|---------|--------|--------|-----------------|
| Native MCP support | ✅ Built-in | ⚠️ Custom client | Enable `OPENAI_CUSTOM_MCP_ENABLED=true` |
| Security sandbox | ✅ Built-in | ⚠️ Security wrapper | Enable `OPENAI_SECURITY_WRAPPER_ENABLED=true` |
| Extended thinking | ✅ Native | ❌ Not supported | Use Claude for extended thinking tasks |
| Agent orchestration | ✅ Built-in | ⚠️ Custom layer | Handled automatically by OpenAI provider |
| Streaming responses | ✅ | ✅ | No action required |
| Function/tool calling | ✅ | ✅ (translated) | Handled by tool schema translator |
| Session management | ✅ Built-in | ⚠️ Custom | Handled automatically by OpenAI provider |
| OAuth authentication | ✅ | ❌ | Use API key for OpenAI |
| API key authentication | ❌ | ✅ | Use `OPENAI_API_KEY` env var |

---

## Testing Checklist

Use this checklist to validate your migration at each stage.

### Pre-Migration Validation

Before starting migration, confirm your current Claude setup works:

- [ ] **Existing tests pass:** `apps/backend/.venv/bin/pytest tests/ -v`
- [ ] **Claude provider validates:** `python apps/backend/run.py --validate-config`
- [ ] **A spec can be created:** `python apps/backend/spec_runner.py --task "Test task"`
- [ ] **A spec run completes:** `python apps/backend/run.py --spec <existing-spec-id>`
- [ ] **Git history captured:** Commit current state before migrating

### Phase 1: Configuration Validation

After adding new environment variables:

- [ ] **Config validates:** `python apps/backend/run.py --validate-config`
- [ ] **Providers list correctly:** `python apps/backend/run.py --list-providers`
- [ ] **No new warnings in logs** related to provider configuration
- [ ] **Existing spec runs unaffected** with `AI_ENGINE_PROVIDER=claude`

### Phase 2: Claude Provider Regression Test

Verify Claude functionality is unchanged after provider abstraction layer is installed:

- [ ] **Unit tests pass (Claude):** `pytest tests/unit/providers/test_claude_provider.py -v`
- [ ] **Spec creation succeeds:** Create and validate a new spec with Claude
- [ ] **Code implementation succeeds:** Run `python apps/backend/run.py --spec <id>`
- [ ] **QA review functions:** Run `python apps/backend/run.py --spec <id> --qa`
- [ ] **MCP integration works:** Verify Context7, Linear, Graphiti tools available
- [ ] **Security enforcement works:** Verify restricted commands are blocked
- [ ] **Extended thinking functions:** Test with spec requiring `max_thinking_tokens`

### Phase 3: OpenAI Provider Validation

After enabling OpenAI provider:

- [ ] **OpenAI API key accepted:** `python apps/backend/run.py --test-provider --provider openai`
- [ ] **OpenAI models listed:** `python apps/backend/run.py --list-models --provider openai`
- [ ] **Unit tests pass (OpenAI):** `pytest tests/unit/providers/test_openai_provider.py -v`
- [ ] **Simple spec creation works:** Create a simple spec using OpenAI provider
- [ ] **Tool calling works:** Verify OpenAI function calling translates correctly
- [ ] **Custom MCP connects:** Verify Context7 accessible via custom MCP client
- [ ] **Security wrapper active:** Verify restricted commands blocked via security wrapper
- [ ] **Session management works:** Verify conversation history maintained

### Phase 4: Provider Switching Tests

Validate switching between providers works correctly:

- [ ] **Switch via env var:** `AI_ENGINE_PROVIDER=openai python apps/backend/run.py --spec <id>`
- [ ] **Switch via CLI flag:** `python apps/backend/run.py --spec <id> --provider openai`
- [ ] **Sessions are provider-specific:** Verify no session state bleeds between providers
- [ ] **Fallback triggers on rate limit:** Simulate rate limit and verify fallback to Claude
- [ ] **Fallback triggers on timeout:** Simulate timeout and verify fallback behavior
- [ ] **Fallback logs warning:** Verify fallback events appear in logs

### Phase 5: Full Workflow Tests

End-to-end validation with both providers:

- [ ] **Claude full workflow:** Create spec → implement → QA review → QA fix (if needed)
- [ ] **OpenAI full workflow:** Same workflow with OpenAI provider
- [ ] **Provider comparison:** Same task produces functionally equivalent results
- [ ] **Per-agent routing works:** Planner uses Claude, Coder uses OpenAI (if configured)
- [ ] **Error handling consistent:** Both providers surface errors via same exception types
- [ ] **Logs are informative:** Provider name visible in log output per operation

### Phase 6: Security Validation

Confirm security parity between providers:

- [ ] **Command allowlist enforced (Claude):** Blocked commands are rejected
- [ ] **Command allowlist enforced (OpenAI):** Same commands blocked via security wrapper
- [ ] **File permissions enforced (Claude):** Cannot read/write outside project directory
- [ ] **File permissions enforced (OpenAI):** Cannot read/write outside project directory via security wrapper
- [ ] **API key not logged:** Verify `OPENAI_API_KEY` does not appear in any log output
- [ ] **PreToolUse hooks fire (OpenAI):** Security wrapper intercepts tool calls before execution

### Phase 7: Regression Test Suite

Run the complete test suite to confirm no regressions:

```bash
# Full test suite
apps/backend/.venv/bin/pytest tests/ -v

# Provider-specific tests
apps/backend/.venv/bin/pytest tests/unit/providers/ -v

# Integration tests
apps/backend/.venv/bin/pytest tests/integration/ -v

# Provider comparison tests (requires both API keys)
apps/backend/.venv/bin/pytest tests/provider_comparison/ -v

# Security tests
apps/backend/.venv/bin/pytest tests/unit/security/ -v
```

**Expected results:**
- All unit tests: 90%+ pass rate
- All integration tests: 100% pass rate
- Provider comparison tests: 90%+ functional equivalence
- Security tests: 100% pass rate (security is non-negotiable)

---

## Rollback Strategy

If the migration causes issues, use this rollback procedure to restore Claude-only operation.

### Immediate Rollback (Configuration Only)

For issues caused by configuration changes:

```bash
# Option 1: Remove provider selection (reverts to Claude default)
unset AI_ENGINE_PROVIDER

# Option 2: Explicitly set Claude in .env
sed -i 's/^AI_ENGINE_PROVIDER=.*/AI_ENGINE_PROVIDER=claude/' apps/backend/.env

# Option 3: Remove OpenAI variables from .env
# Comment out or delete these lines from apps/backend/.env:
# OPENAI_API_KEY=...
# OPENAI_MODEL=...
# OPENAI_CUSTOM_MCP_ENABLED=...
# OPENAI_SECURITY_WRAPPER_ENABLED=...
```

**Verify rollback:**
```bash
python apps/backend/run.py --validate-config
python apps/backend/run.py --show-config
```

### Code Rollback (Git-Based)

If code changes caused issues:

```bash
# View recent commits
git log --oneline -10

# Identify the last known good commit
git log --oneline --all | grep "before multi-provider"

# Create rollback branch from last known good state
git checkout -b rollback/pre-multi-provider <commit-hash>

# Or revert specific commits
git revert <bad-commit-hash>

# Verify rollback is clean
apps/backend/.venv/bin/pytest tests/ -v
```

### Partial Rollback (Disable OpenAI, Keep Abstraction Layer)

If the provider abstraction layer is stable but OpenAI provider has issues:

```bash
# apps/backend/.env
AI_ENGINE_PROVIDER=claude    # Force Claude (safe)
# OPENAI_API_KEY=...         # Comment out to disable OpenAI

# Disable fallback to OpenAI
FALLBACK_ENABLED=false
# FALLBACK_PROVIDER=claude   # Or keep claude as only fallback
```

### Rollback Verification Checklist

After any rollback:

- [ ] **Config validates:** `python apps/backend/run.py --validate-config`
- [ ] **Active provider is Claude:** `python apps/backend/run.py --show-config`
- [ ] **All tests pass:** `apps/backend/.venv/bin/pytest tests/ -v`
- [ ] **A full spec run completes** successfully with Claude
- [ ] **No OpenAI errors in logs** after rollback

---

## Common Migration Issues

### Issue: "Provider not found: openai"

**Cause:** OpenAI provider implementation not yet installed.

**Solution:**
```bash
# Verify OpenAI provider module exists
ls apps/backend/core/providers/

# If missing, check if implementation phase is complete
# The openai provider requires: core/providers/openai.py
```

### Issue: "OPENAI_API_KEY not found"

**Cause:** `OPENAI_API_KEY` not set in environment or `.env` file.

**Solution:**
```bash
# Add to .env file
echo "OPENAI_API_KEY=sk-proj-your-key-here" >> apps/backend/.env

# Verify it's set
python -c "import os; print(os.getenv('OPENAI_API_KEY', 'NOT SET')[:10])"
```

### Issue: "Feature not supported: EXTENDED_THINKING"

**Cause:** Code requests extended thinking from OpenAI provider, which doesn't support it.

**Solution:**
```bash
# Option 1: Switch back to Claude for this task
AI_ENGINE_PROVIDER=claude python apps/backend/run.py --spec <id>

# Option 2: Configure agent-specific provider routing
# apps/backend/.env
PLANNER_PROVIDER=claude    # Planner uses extended thinking - keep on Claude
CODER_PROVIDER=openai      # Coder doesn't need extended thinking
```

### Issue: "MCP server context7 not available with OpenAI"

**Cause:** Custom MCP client for OpenAI not yet implemented or not enabled.

**Solution:**
```bash
# Verify custom MCP is enabled
grep OPENAI_CUSTOM_MCP_ENABLED apps/backend/.env

# If not enabled, add it:
echo "OPENAI_CUSTOM_MCP_ENABLED=true" >> apps/backend/.env

# If custom MCP client is not implemented yet, use Claude for MCP-dependent tasks
AI_ENGINE_PROVIDER=claude python apps/backend/run.py --spec <id>
```

### Issue: "Security wrapper not blocking restricted commands"

**Cause:** Security wrapper not enabled for OpenAI provider.

**Solution:**
```bash
# Enable security wrapper (required for OpenAI provider in production)
echo "OPENAI_SECURITY_WRAPPER_ENABLED=true" >> apps/backend/.env

# Verify security is working
apps/backend/.venv/bin/pytest tests/unit/security/test_security_wrapper.py -v
```

### Issue: "Session state lost when switching providers mid-spec"

**Cause:** Sessions are provider-specific and cannot be transferred.

**Solution:**
Sessions are intentionally provider-scoped. To switch providers, start a new spec run:
```bash
# Run with OpenAI
AI_ENGINE_PROVIDER=openai python apps/backend/run.py --spec <id>

# If OpenAI run fails, start a new Claude run (not a resume)
AI_ENGINE_PROVIDER=claude python apps/backend/run.py --spec <id>
```

---

## Migration Timeline Reference

This is a priority-ordered migration sequence (no time estimates, as AI-assisted development timelines vary):

**Priority 1: Foundation (Complete before any other changes)**
1. Verify current Claude setup is stable (run test suite)
2. Create git branch for migration work
3. Add `AI_ENGINE_PROVIDER=claude` to `.env` (explicit default)

**Priority 2: Low-Risk Configuration**
4. Install provider abstraction layer (no behavior change)
5. Run regression tests to verify Claude is unaffected
6. Document current baseline metrics

**Priority 3: OpenAI Integration (After abstraction layer stable)**
7. Add `OPENAI_API_KEY` to `.env`
8. Enable OpenAI provider: `AI_ENGINE_PROVIDER=openai`
9. Test simple tasks with OpenAI
10. Enable custom MCP client for OpenAI
11. Enable security wrapper for OpenAI

**Priority 4: Production Hardening**
12. Configure fallback strategy
13. Set up per-agent provider routing
14. Run full provider comparison test suite
15. Document provider-specific limitations for team

---

## Related Documentation

- [Implementation Phases](./implementation-phases.md) - Phase-by-phase roadmap
- [Testing Strategy](../testing/validation-strategy.md) - Comprehensive test plans
- [Environment Variable Configuration](../configuration/environment-vars.md) - Full variable reference
- [Provider Abstraction Layer](../architecture/provider-abstraction.md) - Architecture design
- [Security Wrapper Design](../architecture/security-wrapper-design.md) - Security model
- [MCP Client Design](../architecture/mcp-client-design.md) - Custom MCP for OpenAI
- [Model Mapping Table](../architecture/model-mapping-table.md) - Claude ↔ OpenAI model equivalents
- [Feature Detection API](../architecture/feature-detection-api.md) - Provider capability detection

---

**Document Version:** 1.0
**Last Updated:** 2026-02-17
**Status:** Concept (Migration Guide for Design Phase)
