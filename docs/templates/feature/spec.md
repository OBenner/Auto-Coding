# Specification: [Feature Name]

<!--
INSTRUCTIONS: This template supports three complexity levels. Choose the appropriate level:
- SIMPLE/IDEATION: Use sections 1-2 only (Overview, Rationale)
- USER STORY: Use sections 1-4 (add User Stories, Acceptance Criteria)
- COMPREHENSIVE: Use all sections for full feature implementation specs
Delete unused sections and this instruction block when done.
-->

## Overview

<!--
Provide a clear, concise description of what this feature does and why it's needed.
Answer: What problem does this solve? What value does it provide?

Example:
"Create a comprehensive documentation structure for Auto Code and establish reusable
templates for documenting features, architecture, and integrations. This spec defines
a standardized approach to documenting the project at multiple levels."
-->

[Describe the feature, its purpose, and the value it provides]

## Workflow Type

<!-- Optional: Include for comprehensive specs -->

**Type**: [feature | bugfix | refactor | enhancement | documentation]

**Rationale**: [Explain why this workflow type was chosen and what it means for implementation]

## Task Scope

<!-- Optional: Include for comprehensive specs with multiple services -->

### Services Involved
- **[service-name]** (primary) - [Why this service is affected]
- **[service-name]** (secondary) - [How this service is involved]

### This Task Will:
- [ ] [Key deliverable 1]
- [ ] [Key deliverable 2]
- [ ] [Key deliverable 3]

### Out of Scope:
- [Item explicitly not included in this spec]
- [Future enhancement or related work deferred]
- [Boundary clarification to prevent scope creep]

## Rationale

<!--
Explain WHY this feature is needed. Focus on:
- The problem it solves
- The impact of not having this feature
- How it fits into the broader product vision

Example:
"Electron apps run with elevated privileges compared to web browsers and have access
to Node.js APIs. Without CSP, a successful XSS attack could lead to arbitrary code
execution on the user's system."
-->

[Explain the motivation and importance of this feature]

## User Stories

<!-- Optional: Include for user-facing features -->

<!-- Format: As a [user type], I want [goal] so that [benefit] -->

- As a [user type], I want to [action/capability] so that I can [benefit/outcome]
- As a [user type], I want to [action/capability] so that I can [benefit/outcome]

## Service Context

<!-- Optional: Include for comprehensive specs -->

### [Service Name] (e.g., Backend Service)

**Tech Stack:**
- Language: [Language and version]
- Framework: [Framework and version]
- Key dependencies: [List critical dependencies]

**Project Type:** [CLI tool | Web app | Desktop app | Library | Monorepo]

**Entry Point:** [Main file, e.g., `run.py`, `src/App.tsx`]

**How to Run:**
```bash
[Commands to run the service]
```

**Port:** [Port number if applicable]

**Key Directories:**
- `directory/` - [Purpose]
- `directory/` - [Purpose]

**Current Implementation:**
[Describe relevant existing code, patterns, or architecture]

## Files to Modify

<!-- Optional: Include for comprehensive specs with implementation details -->

| File | Service | What to Change |
|------|---------|---------------|
| `path/to/file.ext` | [service] | [Specific change to make] |
| `path/to/file.ext` | [service] | [Specific change to make] |

*Note: Use "None" if this spec creates entirely new files*

## Files to Reference

<!-- Optional: Include for comprehensive specs -->

<!-- List existing files that demonstrate patterns to follow -->

| File | Pattern to Copy |
|------|----------------|
| `path/to/example.ext` | [What pattern or style to follow] |
| `path/to/example.ext` | [What pattern or style to follow] |

## Patterns to Follow

<!-- Optional: Include for comprehensive specs with code examples -->

### [Pattern Name] (e.g., "Error Handling Pattern")

From `[source file]`:

```[language]
# Show example code from the codebase
```

**Key Points:**
- [Important aspect of this pattern]
- [Another key consideration]
- [Best practice to follow]

## Requirements

<!-- Optional: Include for comprehensive specs -->

### Functional Requirements

<!-- Format each requirement with clear acceptance criteria -->

1. **[Requirement Name]**
   - Description: [What needs to be implemented]
   - Acceptance: [How to verify this requirement is met]

2. **[Requirement Name]**
   - Description: [What needs to be implemented]
   - Acceptance: [How to verify this requirement is met]

### Non-Functional Requirements

<!-- Optional: Include performance, security, accessibility requirements -->

1. **[Performance | Security | Accessibility]**
   - Description: [Specific requirement]
   - Acceptance: [How to measure or verify]

### Edge Cases

<!-- List unusual scenarios or boundary conditions to handle -->

1. **[Edge Case Scenario]** - [How to handle it]
2. **[Edge Case Scenario]** - [How to handle it]

## Implementation Notes

<!-- Optional: Include for comprehensive specs -->

### DO
- [Best practice or approach to follow]
- [Pattern to use]
- [Consideration to keep in mind]

### DON'T
- [Anti-pattern to avoid]
- [Common mistake to prevent]
- [Practice that breaks conventions]

## Development Environment

<!-- Optional: Include for comprehensive specs with setup requirements -->

### Directory Structure to Create

<!-- Show new files/folders to be created -->

```
directory/
├── subdirectory/
│   ├── file.ext                  # Purpose
│   └── file.ext                  # Purpose
└── subdirectory/
    └── file.ext                  # Purpose
```

### Required Environment Variables

<!-- List any new or modified environment variables -->

```bash
VARIABLE_NAME=value  # Purpose and accepted values
```

*Note: Use "None" if no environment changes are needed*

### Dependencies to Add

<!-- List new packages or libraries required -->

**Backend:**
```bash
package-name>=version  # Purpose
```

**Frontend:**
```bash
npm install package-name  # Purpose
```

*Note: Use "None" if no new dependencies are needed*

## Acceptance Criteria

<!--
Simple checklist format for basic specs. For comprehensive specs,
use "Success Criteria" and "QA Acceptance Criteria" sections instead.
-->

- [ ] [Criterion 1: Specific, testable outcome]
- [ ] [Criterion 2: Specific, testable outcome]
- [ ] [Criterion 3: Specific, testable outcome]

## Success Criteria

<!-- Optional: Include for comprehensive specs (use instead of simple Acceptance Criteria) -->

The task is complete when:

1. [ ] [Specific deliverable with measurable outcome]
2. [ ] [Specific deliverable with measurable outcome]
3. [ ] [Specific deliverable with measurable outcome]

## QA Acceptance Criteria

<!-- Optional: Include for comprehensive specs requiring thorough QA validation -->

**CRITICAL**: These criteria must be verified by the QA Agent before sign-off.

### [Category Name] (e.g., "Functional Testing")

| Check | File/Component | What to Verify |
|-------|---------------|----------------|
| [Test name] | `path/to/file` | [Specific verification step] |
| [Test name] | `path/to/file` | [Specific verification step] |

### [Category Name] (e.g., "Integration Testing")

| Integration | Test | Expected |
|-------------|------|----------|
| [System/feature] | [Test scenario] | [Expected outcome] |

### [Category Name] (e.g., "Performance Testing")

| Metric | Target | How to Measure |
|--------|--------|----------------|
| [Metric name] | [Target value] | [Measurement method] |

### QA Sign-off Requirements

- [ ] [Critical requirement that blocks approval if not met]
- [ ] [Critical requirement that blocks approval if not met]
- [ ] [Critical requirement that blocks approval if not met]

---

## Template Usage Notes

**When to use each complexity level:**

1. **SIMPLE/IDEATION** (Overview + Rationale only)
   - Early-stage ideas being explored
   - Specs pending detailed requirements
   - Quick bug fixes with obvious solutions

2. **USER STORY** (+ User Stories + Acceptance Criteria)
   - User-facing features with clear user needs
   - Features requiring stakeholder alignment on value
   - Stories that need user perspective validation

3. **COMPREHENSIVE** (All sections)
   - Complex features touching multiple services
   - Features requiring architectural decisions
   - Implementation specs for multi-phase work
   - Features with significant integration or testing requirements

**Tips:**
- Start with simpler formats and expand as requirements become clear
- Include code examples in Patterns section to guide implementation
- Make Success Criteria specific and measurable
- QA Acceptance Criteria should be testable without ambiguity
- Keep Out of Scope section updated to manage expectations
