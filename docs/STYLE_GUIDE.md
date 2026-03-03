# Documentation Style Guide

This guide defines writing style, formatting conventions, and best practices for all Auto Code documentation.

## Table of Contents

- [Tone and Voice](#tone-and-voice)
- [Markdown Conventions](#markdown-conventions)
  - [Headings](#headings)
  - [Lists](#lists)
  - [Code Blocks](#code-blocks)
  - [Tables](#tables)
  - [Links](#links)
  - [Emphasis](#emphasis)
- [Code Examples](#code-examples)
- [Documentation Structure](#documentation-structure)
- [Writing Best Practices](#writing-best-practices)
- [Common Patterns](#common-patterns)
- [File Organization](#file-organization)

## Tone and Voice

Auto Code documentation should be **technical but approachable**.

### ✅ DO

- **Be clear and concise** - Get to the point quickly
- **Use active voice** - "The agent creates a plan" (not "A plan is created by the agent")
- **Write for developers** - Assume technical knowledge but explain project-specific concepts
- **Be practical** - Focus on what users need to accomplish
- **Provide examples** - Show, don't just tell

**Good:**
```markdown
The planner agent creates an implementation plan by analyzing the spec and breaking
it into subtasks. Each subtask includes verification commands and file references.
```

**Avoid:**
```markdown
An implementation plan is generated through a process whereby the specification
document undergoes analysis and subsequent decomposition into constituent subtasks.
```

### ❌ DON'T

- **Don't use jargon without explanation** - Define domain-specific terms
- **Don't be overly casual** - Avoid slang, memes, or excessive emoji
- **Don't be verbose** - Shorter is better if it conveys the same information
- **Don't assume context** - Link to related docs rather than assuming knowledge

## Markdown Conventions

### Headings

Use ATX-style headings (`#`) with a space after the hash:

```markdown
# H1 - Document Title (one per file)
## H2 - Major Sections
### H3 - Subsections
#### H4 - Details (use sparingly)
```

**Guidelines:**
- One H1 per document (the title)
- Use hierarchical structure (don't skip levels: H1 → H3)
- Keep headings short and descriptive (under 60 characters)
- Use sentence case, not title case: "Creating a new spec" not "Creating a New Spec"
- No trailing punctuation in headings

### Lists

**Unordered lists** - Use `-` for consistency:

```markdown
- First item
- Second item
  - Nested item (2 spaces indent)
  - Another nested item
- Third item
```

**Ordered lists** - Use `1.` for all items (auto-numbering):

```markdown
1. First step
1. Second step
1. Third step
```

**Task lists** - Use for checklists:

```markdown
- [ ] Incomplete task
- [x] Completed task
```

**Guidelines:**
- Use parallel structure (all items start with verbs, or all are nouns)
- Punctuate consistently (all items with periods, or none)
- Keep list items concise (1-2 lines each)

### Code Blocks

**Fenced code blocks** - Always specify the language:

````markdown
```python
def create_spec(task: str) -> dict:
    """Create a specification from a task description."""
    return spec_agent.run(task)
```
````

**Supported languages:**
- `python` - Python code
- `typescript` or `tsx` - TypeScript/React
- `bash` - Shell commands
- `json` - JSON data
- `markdown` - Markdown examples
- `yaml` - YAML configuration
- `mermaid` - Diagrams

**Inline code** - Use backticks for code within text:

```markdown
Use the `--spec` flag to specify which spec to run.
```

**Guidelines:**
- Always specify language for syntax highlighting
- Include context before code blocks (explain what the code does)
- Keep code examples concise (under 20 lines when possible)
- Use comments to explain complex logic
- Show complete, runnable examples (not fragments without context)

### Tables

Use tables for structured data comparisons:

```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value A  | Value B  | Value C  |
| Value D  | Value E  | Value F  |
```

**Guidelines:**
- Use **bold** for column headers when appropriate
- Keep table width reasonable (under 100 characters total)
- Align text left, numbers right (use `:---` or `---:`)
- Use tables for data, not for layout

**Good table example:**

```markdown
| Command | Description | Example |
|---------|-------------|---------|
| `--spec XXX` | Run specific spec | `python run.py --spec 001` |
| `--list` | List all specs | `python run.py --list` |
```

### Links

**Internal links** (within the repository) - Use relative paths:

```markdown
See [CONTRIBUTING.md](../CONTRIBUTING.md) for setup instructions.
See the [Architecture Overview](#architecture-overview) section below.
```

**External links** - Use full URLs:

```markdown
Get a [Claude Pro subscription](https://claude.ai/upgrade).
```

**Reference-style links** - Use for repeated links:

```markdown
Check out [Claude Code][1] and the [SDK documentation][2].

[1]: https://claude.ai/code
[2]: https://docs.anthropic.com/claude-sdk
```

**Guidelines:**
- Use descriptive link text (not "click here")
- Verify links work (especially internal relative links)
- Use anchor links for same-page navigation
- Prefer relative links for internal docs (survives repo moves)

### Emphasis

- **Bold** - Use `**text**` for important terms, UI elements, file/directory names
- *Italic* - Use `*text*` for emphasis or introducing new terms
- `Code` - Use backticks for code, commands, file paths, technical terms

**Examples:**

```markdown
The **Planner Agent** creates a plan in `implementation_plan.json`.
Set the *GRAPHITI_ENABLED* environment variable to enable memory.
Navigate to the **Settings** page and click the **Create Spec** button.
```

## Code Examples

### Python

Follow [PEP 8](https://peps.python.org/pep-0008/) style guidelines:

```python
def get_next_chunk(spec_dir: Path) -> dict | None:
    """
    Find the next pending chunk in the implementation plan.

    Args:
        spec_dir: Path to the spec directory

    Returns:
        The next chunk dict or None if all chunks are complete
    """
    plan_path = spec_dir / "implementation_plan.json"

    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)

    for chunk in plan["chunks"]:
        if chunk["status"] == "pending":
            return chunk

    return None
```

**Key points:**
- Type hints for function signatures
- Docstrings for public functions (Google-style format)
- Use `encoding="utf-8"` for file operations (Windows compatibility)
- Meaningful variable names (no single-letter variables except loop counters)
- 4-space indentation

### TypeScript/React

Use TypeScript strict mode and functional components:

```typescript
interface TaskCardProps {
  task: Task;
  onEdit: (task: Task) => void;
  onDelete: (id: string) => void;
}

export function TaskCard({ task, onEdit, onDelete }: TaskCardProps) {
  const [isEditing, setIsEditing] = useState(false);

  const handleSave = () => {
    onEdit(task);
    setIsEditing(false);
  };

  return (
    <div className="task-card">
      <h3>{task.title}</h3>
      <p>{task.description}</p>
      <button onClick={() => setIsEditing(true)}>Edit</button>
    </div>
  );
}
```

**Key points:**
- Named exports (not default exports)
- Interface definitions for props
- Functional components with hooks
- 2-space indentation for TypeScript/JSON

### Shell Commands

Show platform-specific commands when necessary:

```markdown
**Windows:**
```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3.12 -m venv .venv
source .venv/bin/activate
```
```

**Guidelines:**
- Indicate which platform the command is for
- Use `bash` language for syntax highlighting
- Include comments to explain complex commands
- Show expected output when helpful

### Configuration Files

Show complete, valid configuration examples:

```json
{
  "name": "my-spec",
  "complexity": "standard",
  "services": ["backend", "frontend"],
  "phases": [
    "discovery",
    "requirements",
    "context",
    "spec"
  ]
}
```

## Documentation Structure

### Template Comments

Use HTML comments for instructions within templates:

```markdown
<!--
INSTRUCTIONS: Provide a brief description of the feature.
Answer: What problem does this solve? What value does it provide?
Delete this instruction block when done.
-->
```

### Section Organization

Organize documentation with a clear hierarchy:

1. **Title (H1)** - What is this document about?
2. **Overview** - Brief summary (2-3 sentences)
3. **Table of Contents** - For documents >3 sections
4. **Main Content** - Organized by H2/H3 sections
5. **Examples** - Practical usage examples
6. **References** - Related documentation links

### Optional Sections

Mark optional sections clearly:

```markdown
## Advanced Configuration

<!-- Optional: Only needed for custom deployments -->

Configure advanced settings in `.env`:
```

## Writing Best Practices

### Be Specific

**Good:**
```markdown
Run `python run.py --spec 001` to start the build.
```

**Avoid:**
```markdown
Use the run command to start the build process.
```

### Use Active Voice

**Good:**
```markdown
The QA agent validates acceptance criteria.
```

**Avoid:**
```markdown
Acceptance criteria are validated by the QA agent.
```

### Front-Load Information

**Good:**
```markdown
Create a spec by running `python spec_runner.py --interactive`.
This launches an interactive session that guides you through requirements gathering.
```

**Avoid:**
```markdown
An interactive session can be launched that will guide you through the process
of gathering requirements if you run the spec runner in interactive mode.
```

### Break Up Long Paragraphs

- Keep paragraphs to 3-4 sentences maximum
- Use headings, lists, and code blocks to break up text
- One idea per paragraph

### Avoid Ambiguity

**Good:**
```markdown
The planner creates a plan in `implementation_plan.json` with status set to "pending".
```

**Avoid:**
```markdown
The planner creates a plan which might be pending.
```

## Common Patterns

### Command Documentation

```markdown
### `command-name`

**Description:** What the command does

**Usage:**
```bash
command-name [options] <required-arg> [optional-arg]
```

**Options:**
- `--flag` - What this flag does
- `--option VALUE` - What this option does

**Example:**
```bash
command-name --flag value
```
```

### API Endpoint Documentation

```markdown
### POST `/api/endpoint`

**Description:** What this endpoint does

**Request:**
```json
{
  "param1": "value",
  "param2": 123
}
```

**Response:**
```json
{
  "status": "success",
  "data": {}
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/endpoint \
  -H "Content-Type: application/json" \
  -d '{"param1": "value"}'
```
```

### Feature Documentation

```markdown
## Feature Name

**Purpose:** One-line description of what this feature does

**Use Cases:**
- Use case 1
- Use case 2

**How It Works:**
1. Step 1
2. Step 2
3. Step 3

**Example:**
```python
# Code example showing usage
```

**See Also:**
- [Related Feature](link)
- [Documentation](link)
```

## File Organization

### File Naming

Follow these conventions:

- **Guides** - `TOPIC.md` (uppercase) or `topic-guide.md` (lowercase with hyphens)
  - Examples: `CLI-USAGE.md`, `developer-guide.md`
- **Templates** - Descriptive lowercase with hyphens
  - Examples: `implementation-guide.md`, `endpoint-documentation.md`
- **Module docs** - `module-name-architecture.md` or `module-name.md`
  - Examples: `backend-architecture.md`, `memory-system.md`

### File Location

- **Root** - Project overview, contributing, changelog
- **`guides/`** - User and developer guides
- **`docs/`** - Templates, architecture docs, this style guide
- **`docs/templates/`** - Reusable templates organized by type
- **`docs/modules/`** - Per-module architecture documentation
- **`.auto-claude/specs/`** - Individual feature specifications

### Directory Structure

Keep documentation close to code when it's implementation-specific:

```
apps/backend/
├── agents/
│   ├── README.md              # Agent system overview
│   ├── planner.py
│   └── coder.py
├── core/
│   └── README.md              # Core module overview
└── prompts/
    └── README.md              # Prompt documentation
```

Use centralized `docs/` for cross-cutting concerns:

```
docs/
├── README.md                  # Documentation index
├── STYLE_GUIDE.md             # This file
├── templates/                 # Reusable templates
└── modules/                   # Architecture docs
```

## Quick Reference

### Documentation Checklist

Before submitting documentation:

- [ ] Headings use proper hierarchy (no skipped levels)
- [ ] Code blocks specify language for syntax highlighting
- [ ] Links are valid and use relative paths for internal docs
- [ ] Examples are complete and runnable
- [ ] Tone is technical but approachable
- [ ] File follows naming conventions
- [ ] Spell check completed
- [ ] Reviewed against this style guide

### Common Mistakes

| ❌ Avoid | ✅ Use Instead |
|---------|---------------|
| `# Heading 1 #` | `# Heading 1` |
| ` ```code``` ` (no language) | ` ```python code``` ` |
| `Click [here](link)` | `[Descriptive text](link)` |
| Absolute paths for internal links | Relative paths (`../file.md`) |
| "Easy", "simple", "just" | Specific, objective descriptions |
| Long paragraphs (>5 sentences) | Break into multiple paragraphs or lists |

### Tools

- **Spell check** - Use editor with spell check enabled
- **Markdown linter** - Use `markdownlint` or similar tools
- **Link checker** - Verify internal links before committing
- **Preview** - View rendered Markdown before submitting

## References

- [Markdown Guide](https://www.markdownguide.org/) - Markdown syntax reference
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Code style and contribution guidelines
- [docs/README.md](README.md) - Documentation index and template overview
- [GitHub Markdown](https://github.github.com/gfm/) - GitHub Flavored Markdown spec

---

**Questions or suggestions?** Open an issue or submit a PR to improve this guide.
