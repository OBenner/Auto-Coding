# Adaptive Agent Personality System

Agents adapt their approach based on project context and user preferences.
The system learns whether to be cautious vs aggressive, detailed vs concise,
based on feedback and success patterns.

## Architecture

```text
Frontend (Settings UI)          Backend (Agent Runtime)
┌─────────────────────┐        ┌─────────────────────────┐
│ AgentPreferences.tsx │───────>│ preferences.py          │
│ (OptionButtonGroup)  │  IPC   │ (PreferenceProfile)     │
│                      │        │ (app_settings_to_profile)│
│ settings-store.ts    │        │ (modify_prompt_for_preferences)│
│ (migration + persist)│        │                         │
└─────────────────────┘        └────────────┬────────────┘
                                            │
┌─────────────────────┐                     │
│ feedback-api.ts     │        ┌────────────▼────────────┐
│ (preload validation)│───────>│ feedback_recorder.py    │
│                      │  IPC   │ (record to Graphiti)    │
│ feedback-handlers.ts │        │                         │
│ (subprocess spawn)   │        └─────────────────────────┘
└─────────────────────┘
```

## Components

### Backend

| File | Purpose |
|------|---------|
| `agents/preferences.py` | Data models (enums, dataclasses), prompt modification, settings adapter |
| `feedback_recorder.py` | CLI script to record feedback via Graphiti memory |
| `integrations/graphiti/queries_pkg/queries.py` | `save_preference_profile()` / `get_preference_profile()` |
| `tests/verify_preferences.py` | 14 pytest tests covering models, adapter, integration |

### Frontend

| File | Purpose |
|------|---------|
| `renderer/components/settings/AgentPreferences.tsx` | Settings UI with `OptionButtonGroup` |
| `renderer/stores/settings-store.ts` | Migration + persistence of agent prefs |
| `preload/api/feedback-api.ts` | Preload-safe feedback API with validation |
| `main/ipc-handlers/feedback-handlers.ts` | IPC handler, subprocess spawn, env guard |
| `shared/types/ipc.ts` | `FeedbackResult` type with `reason` field |

## Preference Fields

| Setting | Values | Default | Backend Enum |
|---------|--------|---------|--------------|
| Verbosity | minimal, concise, normal, detailed, verbose | normal | `VerbosityLevel` |
| Risk Tolerance | cautious, balanced, aggressive | balanced | `RiskTolerance` |
| Project Type | greenfield, established, legacy | established | `ProjectType` |
| Coding Style | indentation, quotes, line length, naming, comments, type hints | auto | `CodingStylePreferences` |
| User Instructions | free-text list | [] | `list[str]` |

## How It Works

1. **Settings UI** — User configures preferences in `AgentPreferences.tsx`
2. **Migration** — `migrateAgentPreferences()` populates defaults for existing users, persisted to disk
3. **Conversion** — `app_settings_to_profile()` safely converts frontend settings to `PreferenceProfile` (invalid enum values fall back to defaults)
4. **Prompt Injection** — `modify_prompt_for_preferences()` inserts an "Adaptive Behavior Instructions" section into agent prompts
5. **Feedback Loop** — User feedback (accept/reject/modify) is recorded via `feedback_recorder.py` → Graphiti memory
6. **Learning** — Preference profiles evolve based on accumulated feedback patterns

## Safety

- **Enum validation**: `_safe_enum()` catches `ValueError`/`TypeError` from invalid frontend values
- **Type coercion**: `feedback-api.ts` coerces values to strings before `.trim()`
- **Env guard**: Feedback handler checks `pythonEnvManager.isEnvReady()` before spawning
- **Subprocess timeout**: 30s timeout with SIGTERM → SIGKILL fallback
- **Field-by-field migration**: New preference fields are populated individually, not skipped by short-circuit
