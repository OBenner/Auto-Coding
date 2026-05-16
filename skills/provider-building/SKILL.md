---
name: provider-building
description: Build or update Auto Code AI providers, runtime adapters, provider setup flows, and readiness checks. Use for adding model providers, changing provider auth/config, editing runtime adapters, or improving provider onboarding.
---

# Provider Building

Build providers by capability and runtime surface, not by brand label.

## Workflow

1. Classify the requested provider path:
   - API provider config/adapter in `apps/backend/core/providers/`
   - runtime adapter in `apps/backend/agents/runtime/`
   - setup/onboarding UI in `apps/frontend/src/`
   - CLI readiness in `apps/backend/cli/provider_smoke_commands.py`
2. Read similar providers and runtime adapters before editing.
3. Decide the supported runtime modes:
   - `analysis_only`
   - `generic_edit`
   - `mini_pipeline`
   - full agent/MCP bridge only when tool calls and tool results are actually supported
4. Keep account-login flows and API-key flows separate in UI and docs.
5. Add or update tests for config validation, model resolution, capability reporting, and smoke routing.
6. Run `test-enforcement` and `verification`.

## Files To Check

- `apps/backend/core/providers/base.py`
- `apps/backend/core/providers/factory.py`
- `apps/backend/core/providers/adapters/`
- `apps/backend/agents/runtime/compatibility.py`
- `apps/backend/agents/runtime/adapters/`
- `apps/backend/cli/provider_smoke_commands.py`
- `apps/frontend/src/main/ipc-handlers/provider-smoke-runtime.ts`
- `apps/frontend/src/main/ipc-handlers/settings-handlers.ts`

## Readiness Ladder

Do not overload a cheap connection test. Keep the ladder explicit:

1. Connection/config test: credentials and endpoint are reachable.
2. Runtime smoke: provider can respond in the selected runtime mode.
3. Generic edit smoke: provider can drive a tiny file edit.
4. Mini-pipeline readiness: planner, coder, verifier style flow works on a tiny project.

## Done Criteria

- Provider config errors are actionable.
- Capability limits are visible rather than hidden.
- Runtime fallback is explicit.
- Tests cover unsupported and supported paths.
- Docs/UI do not imply a provider supports full autonomous execution unless verified.
