# Claude Skills for Auto-Claude

This guide documents Claude skills that enhance Auto-Claude's autonomous development capabilities.

## What Are Claude Skills?

Skills are modular packages that extend Claude's capabilities with specialized knowledge, workflows, and tool integrations. They transform Claude from a general-purpose agent into a specialized agent equipped with domain-specific procedural knowledge.

Skills are stored in `.claude/skills/` directory (project-local) or `~/.claude/skills/` (global).

## Skill Sources

### Official (Anthropic)
- **Repository**: [anthropics/courses/skills](https://github.com/anthropics/courses)
- **Count**: ~16 skills
- **Quality**: Production-ready, well-documented

### Community (ComposioHQ)
- **Repository**: [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills)
- **Count**: ~60 skills
- **Quality**: Varies, community-maintained

## Recommended Skills for Auto-Claude

### HIGH PRIORITY - Core to Auto-Claude Mission

| Skill | Source | Why Relevant | Install Status |
|-------|--------|--------------|----------------|
| **mcp-builder** | Anthropic | Auto-Claude heavily relies on MCP servers - this helps build new ones | Installed |
| **skill-creator** | Anthropic | Enable creating custom skills for the framework | Installed |
| **subagent-driven-development** | Awesome | Core to what Auto-Claude does - dispatch independent subagents | Not installed |
| **test-driven-development** | Awesome | Aligns with QA workflow (qa_reviewer, qa_fixer agents) | Not installed |
| **test-fixing** | Awesome | Directly supports qa_fixer agent functionality | Not installed |

### MEDIUM PRIORITY - Enhances Existing Workflows

| Skill | Source | Why Relevant |
|-------|--------|--------------|
| **using-git-worktrees** | Awesome | Already using worktrees! Skill provides safety checks |
| **software-architecture** | Awesome | Useful for spec creation and planner agent |
| **review-implementing** | Awesome | Supports code review workflow |
| **finishing-a-development-branch** | Awesome | Useful for merge workflow completion |
| **webapp-testing** | Anthropic | Electron frontend testing (already have Playwright MCP) |
| **prompt-engineering** | Awesome | Improve agent prompts quality |

### NICE TO HAVE - Additional Utilities

| Skill | Source | Why Relevant |
|-------|--------|--------------|
| **git-pushing** | Awesome | Git automation utilities |
| **Skill Seekers** | Awesome | Auto-convert docs into skills |
| **deep-research** | Awesome | Enhanced research for spec creation |
| **root-cause-tracing** | Awesome | Debug execution errors |

## Installed Skills

### mcp-builder

**Purpose**: Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools.

**Use When**: Building MCP servers to integrate external APIs or services, whether in Python (FastMCP) or Node/TypeScript (MCP SDK).

**Contents**:
- `SKILL.md` - Main skill definition with comprehensive MCP development guide
- `reference/` - Best practices docs for Python and Node MCP servers
- `scripts/` - Evaluation and connection testing utilities

**Invoke**: `/mcp-builder` in Claude

### skill-creator

**Purpose**: Guide for creating effective skills that extend Claude's capabilities with specialized knowledge, workflows, or tool integrations.

**Use When**: Creating a new skill or updating an existing skill.

**Contents**:
- `SKILL.md` - Main skill definition with skill creation guidelines
- `references/` - Output patterns and workflow documentation
- `scripts/` - Init, package, and validation utilities

**Invoke**: `/skill-creator` in Claude

## Installation

### Installing a Skill

From the official Anthropic repository:
```bash
# Using Claude CLI
claude /install-skill anthropics/skills/mcp-builder
claude /install-skill anthropics/skills/skill-creator
```

From a GitHub URL:
```bash
claude /install-skill https://github.com/owner/repo/path/to/skill
```

### Listing Installed Skills

```bash
# In Claude session
/skills
```

### Skill Directory Structure

```
.claude/skills/
├── mcp-builder/
│   ├── SKILL.md          # Required: Skill definition
│   ├── LICENSE.txt       # License file
│   ├── reference/        # Reference documentation
│   │   ├── evaluation.md
│   │   ├── mcp_best_practices.md
│   │   ├── node_mcp_server.md
│   │   └── python_mcp_server.md
│   └── scripts/          # Utility scripts
│       ├── connections.py
│       ├── evaluation.py
│       └── requirements.txt
└── skill-creator/
    ├── SKILL.md
    ├── LICENSE.txt
    ├── references/
    │   ├── output-patterns.md
    │   └── workflows.md
    └── scripts/
        ├── init_skill.py
        ├── package_skill.py
        └── quick_validate.py
```

## Creating Custom Skills for Auto-Claude

Using the installed `skill-creator` skill, you can create custom skills tailored to Auto-Claude workflows:

### Potential Custom Skills

1. **auto-claude-spec-writer**: Guide for writing comprehensive specs
2. **auto-claude-qa-reviewer**: Standardized QA review process
3. **auto-claude-planner**: Implementation planning patterns
4. **auto-claude-merger**: Safe branch merging procedures

### Skill Creation Process

1. Invoke `/skill-creator` in Claude
2. Follow the guided workflow to create `SKILL.md`
3. Add reference materials and scripts as needed
4. Test the skill with `/skills` and invocation

## Notes

- The `.claude/` directory is gitignored by Claude Code's design
- Skills installed locally won't be committed to version control
- For team-wide skills, consider using global installation (`~/.claude/skills/`) or documenting installation instructions
- Some community skills may require adaptation for Auto-Claude's specific workflows

## Related Documentation

- [CLI-USAGE.md](CLI-USAGE.md) - Terminal-only usage including skill management
- [SPEC-CREATION-PIPELINE.md](SPEC-CREATION-PIPELINE.md) - How specs work (could benefit from spec-writer skill)
