---
name: plugin-building
description: Build Auto Code optional plugins and extension examples. Use when creating or updating plugins under examples/plugins, apps/backend/plugins, plugin manifests, plugin SDK helpers, UI extensions, integration plugins, or agent plugins.
---

# Plugin Building

Treat plugins as optional capabilities outside the core path. Start with the manifest contract, then wire only the surfaces the plugin actually needs.

## Workflow

1. Pick plugin type:
   - `agent`
   - `integration`
   - `ui`
2. Read matching examples under `examples/plugins/`.
3. Define `plugin.json` first:
   - name, version, author, description
   - plugin type
   - entrypoint/module
   - minimum permissions
4. Implement the plugin using `apps/backend/plugins/sdk/` or the nearest existing example.
5. Add load/permission tests when backend behavior changes.
6. Keep UI extensions isolated from core app routes unless explicitly enabled.
7. Document enablement and rollback.

## Permission Discipline

Use the smallest set from `PluginPermission`:

- `read_files`
- `write_files`
- `network_access`
- `execute_commands`
- `access_secrets`
- `create_mcp_tools`

Never request `access_secrets` or `execute_commands` unless the plugin cannot function without it.

## Done Criteria

- Manifest is valid and minimal.
- Plugin can load or fail with a clear error.
- Permissions match implementation.
- Tests cover denial paths for sensitive actions.
- Core behavior is unchanged when the plugin is absent.
