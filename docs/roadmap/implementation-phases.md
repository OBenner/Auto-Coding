# Implementation Roadmap

This document provides a structured roadmap for implementing multi-provider LLM
and CLI runner support in Auto Code, enabling provider APIs, account-backed
coding CLIs, review CLIs, and local/BYOK runners alongside the existing
Claude-first workflow.

## Overview

The implementation is organized into **8 phases** that progress from
foundational architecture through integration, runner support, and validation.
Phases are designed to maximize parallel execution while respecting
dependencies.

**Implementation strategy:**
- Build on existing provider abstraction layer
- Maintain backward compatibility with Claude provider
- Design for extensibility across direct providers and CLI runners
- Prioritize security parity across providers
- Enable provider switching without code changes
- Enable runner switching without weakening workflow isolation, auditability, or QA

## Phase Dependencies

```text
Phase 1 (Provider Abstraction) ────────┐
Phase 2 (Compatibility Analysis) ─────┤
Phase 3 (MCP Integration Design) ─────┤
Phase 5 (Model Mapping) ──────────────┤→ Phase 7 (Roadmap & Testing)
Phase 6 (Configuration & UI) ─────────┤
Phase 8 (CLI Runner Support) ─────────┤
                                        │
Phase 4 (Security Wrapper) ────────────┘
     (depends on Phase 2)
```

**Parallel execution groups:**
- **Group A** (Phases 1, 2, 3, 5, 6, 8): Can execute in parallel once shared runtime contracts are stable
- **Group B** (Phase 4): Requires Phase 2 completion
- **Group C** (Phase 7): Requires all design phases complete

## Phase 1: Provider Abstraction Enhancement

**Status:** ✅ Design Complete (subtask-1-1, subtask-1-2, subtask-1-3)

**Description:**
Extend the existing `AIEngineProvider` interface to support OpenAI models while maintaining compatibility with Claude SDK, LiteLLM, and OpenRouter providers.

**Implementation Tasks:**

1. **Document Existing Patterns** (subtask-1-1)
   - Document `AIEngineProvider` interface
   - Document `AgentSession` lifecycle
   - Document factory pattern usage
   - **Deliverable:** `docs/architecture/provider-abstraction.md`

2. **Design OpenAI Adapter** (subtask-1-2)
   - Define `OpenAIProvider` class structure
   - Design `OpenAISession` for state management
   - Specify async message streaming via `openai.AsyncOpenAI`
   - Define model listing strategy (GPT-5.2, GPT-5, GPT-4o)
   - **Deliverable:** `docs/architecture/openai-adapter-design.md`

3. **Define Feature Detection API** (subtask-1-3)
   - Create `ProviderFeature` enum
   - Design `supports_feature()` method
   - Document feature-gated code patterns
   - Create provider compatibility matrix
   - **Deliverable:** `docs/architecture/feature-detection-api.md`

**Dependencies:** None (foundation phase)

**Effort Level:** Medium

**Risks & Mitigation:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Interface changes break existing providers | High | Design additions-only; no breaking changes to `AIEngineProvider` |
| Feature detection becomes complex | Medium | Keep feature set minimal; start with 8 core features |
| OpenAI adapter design misses edge cases | Medium | Reference existing LiteLLM/OpenRouter adapters; validate against OpenAI API docs |

**Parallelism:** Can execute in parallel with Phases 2, 3, 5, 6

---

## Phase 2: Claude SDK vs OpenAI API Compatibility Analysis

**Status:** ✅ Design Complete (subtask-2-1, subtask-2-2, subtask-2-3)

**Description:**
Identify and document compatibility gaps between Claude SDK and OpenAI API, with mitigation strategies for tool calling, session management, and security model porting.

**Implementation Tasks:**

1. **Tool Calling Analysis** (subtask-2-1)
   - Compare Claude tools vs OpenAI function calling
   - Document schema differences (`input_schema` vs `parameters`)
   - Design bidirectional translation strategy
   - Create compatibility matrix
   - **Deliverable:** `docs/compatibility/tool-calling-analysis.md`

2. **Session Management Analysis** (subtask-2-2)
   - Compare stateful (Claude) vs stateless (OpenAI) sessions
   - Design conversation history handling
   - Define context window management
   - Specify session lifecycle
   - **Deliverable:** `docs/compatibility/session-management-analysis.md`

3. **Security Model Analysis** (subtask-2-3)
   - Document Claude SDK security features to port
   - Identify security gaps in OpenAI
   - Design sandbox, permissions, and hooks porting strategy
   - Assess feasibility for each security component
   - **Deliverable:** `docs/compatibility/security-model-analysis.md`

**Dependencies:** None

**Effort Level:** Medium

**Risks & Mitigation:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Incompatibilities are more severe than expected | High | Early prototyping to validate assumptions; adjust design if needed |
| Security features cannot be fully ported | High | Prioritize critical security features; accept partial parity |
| Session state management is complex | Medium | Design custom session manager; learn from LiteLLM adapter |

**Parallelism:** Can execute in parallel with Phases 1, 3, 5, 6

**Blocking For:** Phase 4 (Security Wrapper Design)

---

## Phase 3: MCP Integration for OpenAI

**Status:** ✅ Design Complete (subtask-3-1, subtask-3-2)

**Description:**
Design custom MCP (Model Context Protocol) client implementation for OpenAI provider, enabling tool integration with Context7, Linear, Graphiti, and Electron MCP servers.

**Implementation Tasks:**

1. **MCP Client Architecture** (subtask-3-1)
   - Design MCP protocol client implementation
   - Specify server discovery and connection management
   - Define tool discovery and execution protocol
   - Document bidirectional communication flow
   - **Deliverable:** `docs/architecture/mcp-client-design.md`

2. **Tool Schema Translator** (subtask-3-2)
   - Design translator: MCP tools ↔ OpenAI function calling
   - Define schema format conversion
   - Specify parameter mapping strategy
   - Design error handling for translation failures
   - **Deliverable:** `docs/architecture/tool-schema-translator.md`

**Dependencies:** None

**Effort Level:** High

**Risks & Mitigation:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| MCP protocol implementation is complex | High | Use MCP spec as reference; consider existing MCP libraries |
| Tool schema translation is lossy | Medium | Document translation limitations; provide escape hatch |
| MCP servers have protocol differences | Medium | Design for protocol versioning; test with all servers |
| Performance overhead is high | Medium | Cache tool schemas; optimize connection pooling |

**Parallelism:** Can execute in parallel with Phases 1, 2, 5, 6

---

## Phase 4: Security Wrapper Layer

**Status:** ✅ Design Complete (subtask-4-1, subtask-4-2)

**Description:**
Design universal security wrapper to apply Claude's security model (sandbox, file permissions, command allowlisting, hooks) to OpenAI provider.

**Implementation Tasks:**

1. **Security Wrapper Design** (subtask-4-1)
   - Design wrapper applying sandbox, permissions, and hooks
   - Specify integration with `core/security.py`
   - Define PreToolUse and PostToolUse hook interception
   - Document command allowlisting enforcement
   - **Deliverable:** `docs/architecture/security-wrapper-design.md`

2. **Authentication Abstraction** (subtask-4-2)
   - Design unified auth provider
   - Support OAuth tokens (Claude) and API keys (OpenAI)
   - Define credential storage and retrieval
   - Specify token/key validation
   - **Deliverable:** `docs/architecture/auth-abstraction-design.md`

**Dependencies:** Phase 2 (Compatibility Analysis)

**Effort Level:** High

**Risks & Mitigation:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Full security parity is not achievable | High | Document which features are ported; accept partial parity |
| Security wrapper has performance overhead | Medium | Optimize hot paths; cache allowlists; benchmark |
| Hook integration breaks tool execution | High | Extensive testing; fail-safe mechanisms |
| API key exposure risk | High | Follow security best practices; never log keys; use env vars |

**Parallelism:** Must execute after Phase 2; can overlap with Phase 7

---

## Phase 5: Model Mapping Strategy

**Status:** ✅ Design Complete (subtask-5-1, subtask-5-2)

**Description:**
Design model mapping between OpenAI models (GPT-5.2, GPT-5) and Claude equivalents (Opus, Sonnet, Haiku) for task-specific routing and fallback strategies.

**Implementation Tasks:**

1. **Model Mapping Table** (subtask-5-1)
   - Create mapping: GPT-5.2 → Claude Opus, GPT-5 → Claude Sonnet
   - Define agent-specific model selection
   - Document model capabilities comparison
   - Design fallback strategy (intra-provider and cross-provider)
   - **Deliverable:** `docs/architecture/model-mapping-table.md`

2. **Feature Detection Strategy** (subtask-5-2)
   - Design capability detection for unsupported features
   - Define extended thinking fallback
   - Specify graceful degradation patterns
   - Document feature flags and configuration
   - **Deliverable:** `docs/architecture/feature-detection-strategy.md`

**Dependencies:** None

**Effort Level:** Medium

**Risks & Mitigation:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Model mappings are not functionally equivalent | Medium | Clear documentation that mappings are by capability tier, not exact parity |
| Fallback strategy causes infinite loops | Low | Max fallback depth; fail-fast after N attempts |
| OpenAI model pricing changes significantly | Low | Design is flexible; mappings can be updated via config |
| Feature detection is inaccurate | Medium | Conservative defaults; user-configurable feature flags |

**Parallelism:** Can execute in parallel with Phases 1, 2, 3, 6

---

## Phase 6: Configuration and User Experience

**Status:** ✅ Design Complete (subtask-6-1, subtask-6-2)

**Description:**
Design configuration strategy and frontend UI for provider selection, API key management, and per-agent routing configuration.

**Implementation Tasks:**

1. **Environment Variable Configuration** (subtask-6-1)
   - Define environment variable schema
   - Specify `AI_ENGINE_PROVIDER`, `OPENAI_API_KEY` usage
   - Design model selection configuration
   - Document fallback strategy configuration
   - **Deliverable:** `docs/configuration/environment-vars.md`

2. **Frontend UI Design** (subtask-6-2)
   - Design provider selection UI components
   - Specify API key input with masking
   - Design model selector with tier grouping
   - Define connection testing and status indicators
   - **Deliverable:** `docs/frontend/provider-selection-ui.md`

**Dependencies:** None

**Effort Level:** Medium

**Risks & Mitigation:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Configuration becomes too complex | Medium | Provide sensible defaults; document common patterns |
| UI changes break existing workflows | Medium | Keep Claude as default; make OpenAI opt-in |
| API key storage has security issues | High | Use system credential store; never localStorage |
| Provider switching is confusing | Low | Clear documentation; visual indicators; test connection feature |

**Parallelism:** Can execute in parallel with Phases 1, 2, 3, 5

---

## Phase 7: Implementation Roadmap & Testing Strategy

**Status:** 🚧 In Progress (subtask-7-1, subtask-7-2, subtask-7-3)

**Description:**
Create comprehensive implementation roadmap, testing strategy, and migration guide for transitioning from Claude-only to multi-provider architecture.

**Implementation Tasks:**

1. **Implementation Roadmap** (subtask-7-1)
   - Create ordered phase implementation guide
   - Document dependencies and parallel execution
   - Define effort levels and risk mitigation
   - Specify rollout strategy
   - **Deliverable:** `docs/roadmap/implementation-phases.md` (this document)

2. **Testing Strategy** (subtask-7-2)
   - Design unit tests for each provider
   - Define integration test scenarios
   - Specify E2E tests for provider switching
   - Create provider comparison test plan
   - **Deliverable:** `docs/testing/validation-strategy.md`

3. **Migration Guide** (subtask-7-3)
   - Document breaking changes (none expected)
   - Specify configuration updates required
   - Provide testing checklist
   - Define rollback strategy
   - **Deliverable:** `docs/roadmap/migration-guide.md`

**Dependencies:** All design phases (1-6) must be complete

**Effort Level:** Medium

**Risks & Mitigation:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Roadmap is not actionable | Medium | Review with stakeholders; validate phase ordering |
| Testing strategy misses edge cases | Medium | Peer review; test-driven approach during implementation |
| Migration guide is unclear | Low | User testing of guide; iterate based on feedback |
| Rollback strategy is not tested | Low | Document rollback steps; test in staging environment |

**Parallelism:** Must execute after all design phases complete

---

## Phase 8: Multi-CLI Runner Support

**Status:** 🚧 In Progress (runner strategy documented; runtime contracts started)

**Description:**
Extend the multi-provider runtime engine so Auto Code can orchestrate external
LLM coding CLIs and review CLIs through a common runner contract instead of
adding ad hoc integrations in planner, coder, QA reviewer, or QA fixer modules.

This phase is based on `docs/roadmap/cli-runner-strategy.md` and covers both
first-class runner integrations and generic CLI fallback support.

**Implementation Tasks:**

1. **Runner Contract and Registry**
   - Define `AgentRunner`, `ReviewRunner`, `RunnerCapabilities`,
     `RunnerPolicy`, `RunnerResult`, and `RunnerRegistry`.
   - Normalize lifecycle operations: detect, authenticate, start, stream events,
     cancel, resume, collect artifacts, and close.
   - Map runner capabilities to runtime requirements without claiming Claude SDK
     parity where it does not exist.
   - **Deliverable:** backend runner contract under `apps/backend/agents/runtime/`
     or a sibling `runners/cli/` package.

2. **First-Class CLI Runners**
   - Codex CLI: keep as the default account-backed coding runner and finish
     event/cost/resume reporting.
   - Claude Code: keep as the compatibility runner for current full autonomous
     workflows.
   - Gemini CLI: support large-context discovery, repository analysis, and
     research-heavy phases.
   - Aider: support focused git-native edits, BYOK/local-model flows, and
     explicit patch/change review.
   - CodeRabbit CLI: support independent review and quality gate workflows,
     not implementation work.
   - **Deliverable:** explicit runner adapters, smoke checks, and capability
     rows for each first-class CLI.

3. **Strategic CLI Integrations**
   - GitHub Copilot CLI: support GitHub-native issue, branch, PR, and enterprise
     repository workflows.
   - Cursor CLI: support teams standardized on Cursor Agent, Cursor rules, and
     Cursor-managed project context.
   - Z.AI via Claude Code: support GLM models through Z.AI's
     Anthropic-compatible endpoint as a Claude Code-compatible runner profile,
     separate from the direct ZhipuAI/Z.AI provider adapter.
   - **Deliverable:** detection, setup guidance, capability policy, and fallback
     integration for strategic runners.

4. **Generic CLI Runner Contract**
   - Support OpenCode, Goose, Amp, Qwen Code, DeepV Code / Codeep, and similar
     emerging CLIs through a conservative generic runner adapter.
   - Require explicit capability declarations for file edits, command execution,
     MCP, headless mode, structured output, review-only mode, local model use,
     image input, and cost reporting.
   - Start with analysis/review/patch proposal flows unless a runner has a
     proven edit/runtime contract.
   - **Deliverable:** generic CLI config schema and compatibility tests.

5. **Runner Selection and Fallback**
   - Extend runtime-aware fallback so it can choose among direct providers and
     CLI runners by capability, policy, account state, cost preference, and task
     type.
   - Prevent unsafe fallback, such as replacing Claude full autonomous with a
     CLI that lacks filesystem edits, MCP, or subagent support.
   - Record selected runner, skipped candidates, capability gaps, and fallback
     reason in task artifacts.
   - **Deliverable:** runner-aware fallback decisions and artifacts.

6. **Frontend Runner Settings**
   - Add runner status cards for installed, authenticated, unsupported version,
     blocked by policy, missing but credential-signal present, and unavailable.
   - Let users set default implementation, research/discovery, review, QA, and
     fallback runners.
   - Surface runner cost, account, policy, and compatibility warnings next to
     runtime settings.
   - **Deliverable:** provider and runner settings UI backed by runtime
     compatibility payloads.

**Dependencies:** Shared runtime capability contracts from Phases 1, 2, 4, and
6. Codex CLI work can continue immediately; the generic runner adapter depends
on stable policy and artifact contracts.

**Risks & Mitigation:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| CLI output is inconsistent across tools | High | Prefer structured modes where available; add parser fixtures and conservative fallback |
| A runner cannot run headlessly or safely edit files | High | Gate by capabilities; allow analysis/review-only use until edit contract is proven |
| Authentication flows differ by vendor | Medium | Keep auth detection separate from execution; surface setup state in UI |
| Generic runner becomes too permissive | High | Require explicit capability declarations and block unknown mutating behavior |
| Review-only tools are accidentally used for implementation | Medium | Add `review_only` capability and fail-fast assignment checks |

**Parallelism:** Runner detection, UI design, and parser fixtures can progress in
parallel with direct provider runtime work. Mutating runner execution should wait
for the security/policy wrapper to be stable.

---

## Implementation Execution Strategy

### Recommended Execution Order

**Step 1: Parallel Design And Runner Contract Phases**
- Execute Phases 1, 2, 3, 5, 6, and the non-mutating parts of Phase 8 in
  parallel where ownership is clear.
- Keep direct-provider work and CLI-runner work behind the same capability,
  policy, artifact, and fallback contracts.

**Step 2: Security Wrapper Design**
- Execute Phase 4 after Phase 2 completes
- Apply the same policy model to direct providers and mutating CLI runners.

**Step 3: Roadmap & Testing**
- Execute Phase 7 after all design phases complete
- Synthesize validation coverage for providers, runners, UI, fallback, and
  migration.

### Parallel Execution Group Summary

```text
┌─────────────────────────────────────────────────────────────┐
│ Group A: Parallel Design And Runner Contract Phases        │
├─────────────────────────────────────────────────────────────┤
│ Phase 1: Provider Abstraction Enhancement                  │
│ Phase 2: Compatibility Analysis                           │
│ Phase 3: MCP Integration Design                           │
│ Phase 5: Model Mapping Strategy                           │
│ Phase 6: Configuration & UX                               │
│ Phase 8: CLI Runner Support                               │
└─────────────────────────────────────────────────────────────┘
                           ↓ (completes)
┌─────────────────────────────────────────────────────────────┐
│ Group B: Security Design (depends on Phase 2)              │
├─────────────────────────────────────────────────────────────┤
│ Phase 4: Security Wrapper Layer                           │
└─────────────────────────────────────────────────────────────┘
                           ↓ (completes)
┌─────────────────────────────────────────────────────────────┐
│ Group C: Roadmap & Testing (depends on design phases)      │
├─────────────────────────────────────────────────────────────┤
│ Phase 7: Implementation Roadmap & Testing Strategy        │
└─────────────────────────────────────────────────────────────┘
```

### Risk Mitigation by Phase

**High-Risk Phases** (require extra attention):
- **Phase 3 (MCP Integration):** High complexity - consider prototyping early
- **Phase 4 (Security Wrapper):** High security impact - requires thorough testing
- **Phase 8 (CLI Runner Support):** High variance across runner output,
  authentication, and safe edit behavior

**Medium-Risk Phases:**
- **Phase 2 (Compatibility Analysis):** Foundation for security wrapper
- **Phase 5 (Model Mapping):** Mappings may not be functionally equivalent
- **Phase 8 non-mutating runners:** Detection, analysis, and review-only use are
  lower risk than mutating runner execution

**Low-Risk Phases:**
- **Phase 1 (Provider Abstraction):** Builds on existing patterns
- **Phase 6 (Configuration & UX):** UI changes are opt-in

### Success Criteria

The implementation roadmap is complete when:

- [ ] All 8 phases have detailed implementation tasks
- [ ] Dependencies between phases are clearly documented
- [ ] Parallel execution strategy is defined
- [ ] Risk mitigation strategies exist for each phase
- [ ] Testing strategy covers all providers and features
- [ ] Testing strategy covers first-class, strategic, and generic CLI runners
- [ ] Migration guide provides clear upgrade path
- [ ] CLI runner strategy is linked to runtime capability and policy contracts
- [ ] Rollback strategy is documented
- [ ] Stakeholder review confirms roadmap is actionable

## Next Steps

After roadmap completion:

1. **Stakeholder Review** - Present roadmap to team for feedback
2. **Ownership Planning** - Assign clear ownership for direct providers,
   runner contracts, UI, docs, and validation
3. **Prototype Validation** - Build proof-of-concept for high-risk phases
4. **Implementation Kickoff** - Begin with Group A parallel phases
5. **Progress Tracking** - Use implementation_plan.json for status tracking
6. **Runner Contract Validation** - Verify Codex CLI, Claude Code, Gemini CLI,
   Aider, CodeRabbit CLI, GitHub Copilot CLI, Cursor CLI, and generic CLI
   adapters against the same capability checks
7. **Integration Testing** - Validate provider and runner switching after Group C

## References

- **Specification:** `./.auto-claude/specs/171-codex-openai-integration-concept/spec.md`
- **Implementation Plan:** `./.auto-claude/specs/171-codex-openai-integration-concept/implementation_plan.json`
- **Architecture Documents:** `./docs/architecture/*.md`
- **Compatibility Analysis:** `./docs/compatibility/*.md`
- **Configuration:** `./docs/configuration/*.md`
- **CLI Runner Strategy:** `./docs/roadmap/cli-runner-strategy.md`

---

**Document Status:** Implementation Roadmap (Design Phase)
**Next Phase:** Implementation Execution (upon approval)
