---
name: plugin-review
description: Review Auto Code plugin manifests, plugin SDK changes, examples, UI extensions, permissions, isolation, install/update behavior, and optional capability boundaries. Use for plugin PRs, plugin architecture work, and extension security review.
---

# Plugin Review

Review plugins as untrusted optional extensions.

## Checklist

1. Inspect `plugin.json` and verify type, entrypoint, version, and declared permissions.
2. Read the implementation and map every sensitive action to a declared permission.
3. Check that plugin absence does not break the core path.
4. Check isolation boundaries:
   - no undeclared filesystem writes
   - no secret access without explicit permission
   - no shell execution without permission
   - no network calls hidden in load-time side effects
5. Check lifecycle behavior: load, enable, disable, unload, failure reporting.
6. Check tests or examples show the expected enablement path.

## Findings

Use:

- **Blocker:** undeclared sensitive action, core path dependency, unsafe load-time side effect.
- **Warning:** broad permissions, missing denial tests, unclear rollback.
- **Suggestion:** manifest/docs clarity or example polish.

## Output

Lead with findings and file:line references. If clean, state what was inspected and which plugin paths still lack automated coverage.
