# Auto Claude Documentation Templates

Reusable templates for creating consistent, high-quality documentation across the Auto Claude project.

## Overview

This directory contains markdown templates that provide structured formats for documenting features, architecture, and APIs. Each template includes inline instructions, examples, and best practices to guide documentation creation.

## Available Templates

### Feature Documentation

| Template | Purpose |
|----------|---------|
| **[spec.md](feature/spec.md)** | Comprehensive feature specifications with three complexity levels (SIMPLE, USER STORY, COMPREHENSIVE) |
| **[feature-overview.md](feature/feature-overview.md)** | High-level feature summaries for stakeholders and new team members |
| **[implementation-guide.md](feature/implementation-guide.md)** | Step-by-step implementation guides for developers |

### Architecture Documentation

| Template | Purpose |
|----------|---------|
| **[system-overview.md](architecture/system-overview.md)** | High-level system architecture, technology stack, and design decisions |
| **[module-architecture.md](architecture/module-architecture.md)** | Detailed module/component architecture and internal design |
| **[integration-guide.md](architecture/integration-guide.md)** | Integration patterns, external dependencies, and API contracts |

### API Documentation

| Template | Purpose |
|----------|---------|
| **[endpoint-documentation.md](api/endpoint-documentation.md)** | REST/GraphQL endpoint documentation with examples |
| **[component-api.md](api/component-api.md)** | Component-level API documentation (functions, classes, interfaces) |

## Usage Guide

### Choosing the Right Template

**For new features:**
1. Start with `feature/spec.md` to define requirements
2. Add `feature/feature-overview.md` for stakeholder communication
3. Create `feature/implementation-guide.md` when ready to implement

**For architecture decisions:**
1. Use `architecture/system-overview.md` for high-level system documentation
2. Use `architecture/module-architecture.md` for detailed component design
3. Use `architecture/integration-guide.md` for external system integrations

**For API documentation:**
1. Use `api/endpoint-documentation.md` for HTTP endpoints
2. Use `api/component-api.md` for code-level APIs (libraries, SDKs)

### Template Complexity Levels

The **spec.md** template supports three complexity levels:

| Level | Sections | Use When |
|-------|----------|----------|
| **SIMPLE/IDEATION** | Overview + Rationale | Early-stage ideas, quick bug fixes |
| **USER STORY** | + User Stories + Acceptance Criteria | User-facing features requiring validation |
| **COMPREHENSIVE** | All sections | Complex features, multi-service changes |

### Best Practices

**DO:**
- Replace all `[placeholder text]` with project-specific information
- Remove unused sections and instruction blocks when done
- Include code examples and diagrams where helpful
- Keep documentation updated as implementation evolves
- Follow existing project patterns shown in the templates

**DON'T:**
- Leave placeholder text in final documentation
- Skip acceptance criteria or success metrics
- Include time estimates for roadmap items
- Copy templates without customization

## Creating Documentation

### Step 1: Copy the Template

```bash
# Copy template to your documentation location
cp docs/templates/feature/spec.md .auto-claude/specs/001-my-feature/spec.md
```

### Step 2: Fill in the Template

1. Read the template instructions carefully
2. Replace all `[placeholders]` with your content
3. Delete unused sections based on complexity level
4. Remove instruction blocks (HTML comments)

### Step 3: Review and Refine

- Ensure all acceptance criteria are testable
- Verify code examples match project conventions
- Check that diagrams are clear and accurate
- Have another developer review for clarity

## Examples

### Good Documentation

✅ **Clear, specific, testable:**
```markdown
## Success Criteria

1. [ ] User can authenticate via OAuth 2.0 with GitHub
2. [ ] Access tokens are stored securely in system keychain
3. [ ] Failed auth attempts are logged with error details
```

### Poor Documentation

❌ **Vague, untestable, placeholder-filled:**
```markdown
## Success Criteria

1. [ ] [Add criterion here]
2. [ ] User can login somehow
3. [ ] It should work properly
```

## Integration with Auto Claude

These templates align with Auto Claude's spec creation pipeline:

- **spec.md** → Used by spec creation agents to generate feature specifications
- **implementation-guide.md** → Referenced during implementation phase
- **Architecture templates** → Used for documenting system design decisions

For more information on the spec creation process, see [Spec Creation Pipeline Guide](../../guides/SPEC-CREATION-PIPELINE.md).

## Quick Links

- [Main README](../../README.md) - Project overview and getting started
- [Contributing Guide](../../CONTRIBUTING.md) - How to contribute
- [Style Guide](../style-guide.md) - Documentation style conventions
- [All Guides](../../guides/README.md) - Additional documentation

---

**Need help choosing a template?**

| You want to... | Use template |
|---------------|-------------|
| Define a new feature | `feature/spec.md` |
| Explain how a feature works | `feature/feature-overview.md` |
| Guide developers through implementation | `feature/implementation-guide.md` |
| Document system architecture | `architecture/system-overview.md` |
| Explain a module's internal design | `architecture/module-architecture.md` |
| Document an integration | `architecture/integration-guide.md` |
| Document REST/GraphQL APIs | `api/endpoint-documentation.md` |
| Document code-level APIs | `api/component-api.md` |
