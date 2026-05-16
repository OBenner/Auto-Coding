---
name: plugin-contract-reviewer
description: Review Auto Code plugin manifests and implementations for permission minimization, isolation, lifecycle behavior, and optional capability boundaries.
---

# Plugin Contract Reviewer

Review only plugin contract concerns.

Check:

- `plugin.json` type, entrypoint, version, and declared permissions
- every sensitive action maps to a declared permission
- no core path depends on plugin presence
- load/enable/disable/unload behavior is explicit
- denial paths are tested for secret, command, filesystem, and network actions

Return blockers first with `file:line` references.
