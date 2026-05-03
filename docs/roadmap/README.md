# Roadmap Documents

This directory contains planning documents for Auto Code product and technical
development.

## Documents

| Document | Purpose |
| --- | --- |
| [Product Strategy and Development Roadmap](./product-strategy.md) | Market-informed product positioning, maturity reality check, and development roadmap. |
| [Implementation Roadmap](./implementation-phases.md) | Technical roadmap for multi-provider LLM support. |
| [LLM CLI Runner Strategy](./cli-runner-strategy.md) | Strategic case, goals, benefits, application experience, and support tiers for integrating external LLM coding CLIs, including Cursor CLI. |
| [Migration Guide](./migration-guide.md) | Migration path from Claude-only usage to the multi-provider architecture. |

## How To Use This Directory

- Use the CLI runner strategy when deciding which external coding agents,
  review CLIs, or headless runners Auto Code should support.
- Use the implementation roadmap when working specifically on provider/runtime
  architecture, CLI runner contracts, fallback behavior, and validation.
- Use the migration guide when validating compatibility for existing users.
