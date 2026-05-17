# Skill Pack Runtime and Rules Steering Compiler Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development before production code and verify each task with focused tests.

**Goal:** Add two built-in analysis-only agent plugins that make portable `SKILL.md` packs and established IDE steering files usable by Auto Code agent sessions without bloating every prompt or granting script execution by default.

**Architecture:** Add `skill-pack-runtime` and `rules-steering-compiler` under `apps/backend/plugins/system/`. Both are agent plugins that augment prompts through the plugin runtime from PR #253. They read project-local files, contribute scoped context by phase/files, and write JSONL traces under `.auto-claude/plugin_traces/`.

**Tech Stack:** Python 3.12, stdlib markdown/frontmatter parsing, pytest.

---

### Task 1: Skill Pack Runtime Contract

**Files:**
- Create: `tests/test_skill_pack_runtime.py`

- [x] **Step 1: Add RED tests**

Cover discovery of `skills/*/SKILL.md`, catalog-only summaries, lazy loading of only the selected skill body, blocked script resources when `execute_commands` is not granted, and activation trace output.

- [x] **Step 2: Verify RED**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_skill_pack_runtime.py -q`

Expected: FAIL because `skill_pack_runtime` does not exist.

### Task 2: Rules Steering Compiler Contract

**Files:**
- Create: `tests/test_rules_steering_compiler.py`

- [x] **Step 1: Add RED tests**

Cover imports for `AGENTS.md`, `.cursor/rules`, `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md`, `.windsurf/rules`, and `.kiro/steering`, including phase and file glob filtering.

- [x] **Step 2: Verify RED**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_rules_steering_compiler.py -q`

Expected: FAIL because `rules_steering_compiler` does not exist.

### Task 3: Implement Built-In Plugins

**Files:**
- Create: `apps/backend/plugins/system/skill-pack-runtime/plugin.json`
- Create: `apps/backend/plugins/system/skill-pack-runtime/plugin.py`
- Create: `apps/backend/plugins/system/skill-pack-runtime/skill_pack_runtime/*.py`
- Create: `apps/backend/plugins/system/rules-steering-compiler/plugin.json`
- Create: `apps/backend/plugins/system/rules-steering-compiler/plugin.py`
- Create: `apps/backend/plugins/system/rules-steering-compiler/rules_steering_compiler/*.py`

- [x] **Step 1: Implement skill catalog and activation**

Parse `SKILL.md` frontmatter, advertise only `name` and `description`, select relevant skills from task/phase/file context, and load full content only for activated skills.

- [x] **Step 2: Implement steering compiler**

Discover supported rules files, parse simple frontmatter, match by phase and file globs, and emit compact compiled context blocks.

- [x] **Step 3: Write traces**

Each plugin writes JSONL trace events with plugin name, phase, selected sources/skills, and activation reason.

### Task 4: Runtime and Health Verification

**Files:**
- Modify only tests and plugin-local files unless the substrate needs a small extension.

- [x] **Step 1: Run focused tests**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_skill_pack_runtime.py tests/test_rules_steering_compiler.py tests/test_plugin_runtime.py -q`

- [x] **Step 2: Run plugin diagnostics**

Run: `apps/backend/.venv/bin/python apps/backend/plugins/cli.py health --json`

- [x] **Step 3: Inspect diff**

Run: `git diff --stat`
