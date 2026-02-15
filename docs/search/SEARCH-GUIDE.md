# Documentation Search Guide

Learn how to efficiently find information in Auto Code's documentation using the search index and other tools.

## Table of Contents

- [Quick Search Methods](#quick-search-methods)
- [Using the Search Index](#using-the-search-index)
- [Search Strategies](#search-strategies)
- [Finding Specific Types of Information](#finding-specific-types-of-information)
- [Advanced Search Techniques](#advanced-search-techniques)
- [Browser Search Tips](#browser-search-tips)
- [When to Use Different Resources](#when-to-use-different-resources)

---

## Quick Search Methods

### Method 1: Use the Search Index (Recommended)

**Best for:** Comprehensive searches, browsing by category, finding related docs

1. Open [docs/search/INDEX.md](INDEX.md)
2. Press `Ctrl+F` (Windows/Linux) or `Cmd+F` (macOS)
3. Type your keyword
4. Click the document link to jump directly

**Example:**
```
Search for: "memory"
Found: Memory System, Graphiti, embeddings, vector-search
```

### Method 2: Use GitHub Search

**Best for:** Searching across all files, including code

1. Go to the [GitHub repository](https://github.com/OBenner/Auto-Coding)
2. Use the search bar at the top
3. Type your search term
4. Filter by "Code" or "Wikis" if needed

**Example:**
```
Search: "graphiti memory"
Filter: In this repository
```

### Method 3: Use IDE Search

**Best for:** Quick searches while working in code

**VS Code:**
1. Press `Ctrl+Shift+F` (Windows/Linux) or `Cmd+Shift+F` (macOS)
2. Type your search term
3. Review results in the search panel

**Example:**
```
Search: "graphiti
Files to include: *.md
```

### Method 4: Command Line Search

**Best for:** Power users, terminal workflows

**Using grep:**
```bash
# Search in all markdown files
grep -r "keyword" docs/ guides/ --include="*.md"

# Case-insensitive search
grep -ri "memory" docs/

# Show line numbers
grep -rn "agent" docs/
```

**Using ripgrep (faster):**
```bash
# Install: cargo install ripgrep
rg "keyword" docs/ guides/ --type md
```

---

## Using the Search Index

The [Search Index](INDEX.md) is organized for quick navigation:

### Browse by Section

Each section focuses on a specific area:

| Section | Contains | Use When... |
|---------|----------|-------------|
| **Getting Started** | Quick Start, CLI Usage | You're new to Auto Code |
| **Architecture** | System design, modules | You need to understand how it works |
| **Features** | Memory, QA, Parallel Execution | You want to learn about specific features |
| **Development** | Contributing, customization | You're developing or extending |
| **Cloud** | Setup, deployment | You're deploying to the cloud |
| **Platform** | Windows, Linux guides | You have platform-specific questions |
| **API** | Backend, CLI, IPC APIs | You're integrating with APIs |

### Use Keywords

Keywords are **bolded** for easy scanning:

```markdown
| Document | Keywords |
|----------|----------|
| Quick Start | **beginner**, **tutorial**, **setup**, **installation** |
```

**Tips:**
- Scan the keywords column first
- Look for terms that match your need
- Multiple keywords per document = broader coverage

### Follow the Links

Each document title is a clickable link:

```markdown
**[Quick Start Guide](../../guides/QUICK-START.md)**
```

Click the link to jump directly to that document.

---

## Search Strategies

### Strategy 1: Start Broad, Then Narrow

1. **Start with a general term**
   - Search: "agent"
   - Results: 10+ documents about agents

2. **Add specificity if needed**
   - Search: "agent customization"
   - Results: Agent Customization guide

3. **Use exact phrases**
   - Search: "multi-agent pipeline"
   - Results: Multi-Agent Pipeline feature doc

### Strategy 2: Use Synonyms

If one term doesn't work, try related terms:

| Looking For | Try These Terms |
|-------------|-----------------|
| Command line | cli, terminal, command-line, headless |
| Memory | graphiti, knowledge-graph, embeddings, vector |
| Testing | qa, validation, testing, e2e |
| Customization | customize, extend, modify, plugins |
| Architecture | structure, design, system, modules |

### Strategy 3: Search by Category

Instead of searching, navigate directly to the relevant section:

1. **I'm having trouble with setup**
   - Go to: Getting Started section

2. **I want to understand how it works**
   - Go to: Architecture & Design section

3. **I'm developing a feature**
   - Go to: Development Guides section

4. **I need API documentation**
   - Go to: API Documentation section

---

## Finding Specific Types of Information

### Finding How-To Guides

**Look in:** `guides/` directory

| You want to... | Look here |
|----------------|-----------|
| Get started | [QUICK-START.md](../../guides/QUICK-START.md) |
| Use CLI | [CLI-USAGE.md](../../guides/CLI-USAGE.md) |
| Customize agents | [AGENT-CUSTOMIZATION.md](../../guides/AGENT-CUSTOMIZATION.md) |
| Deploy to cloud | [CLOUD_SETUP.md](../../guides/CLOUD_SETUP.md) |

### Finding Architecture Information

**Look in:** `docs/modules/` and root `CLAUDE.md`

| You want to... | Look here |
|----------------|-----------|
| Understand system design | [CLAUDE.md](../../CLAUDE.md) |
| Learn about backend | [backend-architecture.md](../modules/backend-architecture.md) |
| Learn about frontend | [frontend-architecture.md](../modules/frontend-architecture.md) |

### Finding Feature Documentation

**Look in:** `docs/features/`

| Feature | Document |
|---------|----------|
| Memory system | [MEMORY-SYSTEM.md](../features/MEMORY-SYSTEM.md) |
| QA loop | [QA-LOOP.md](../features/QA-LOOP.md) |
| Parallel execution | [PARALLEL-EXECUTION.md](../features/PARALLEL-EXECUTION.md) |

### Finding API Documentation

**Look in:** `docs/api/`

| API | Document |
|-----|----------|
| Backend | [backend-api.md](../api/backend-api.md) |
| CLI | [CLI-API-REFERENCE.md](../api/CLI-API-REFERENCE.md) |
| IPC | [IPC-API-REFERENCE.md](../api/IPC-API-REFERENCE.md) |

### Finding Templates

**Look in:** `docs/templates/`

| Template Type | Location |
|---------------|----------|
| Feature specs | `templates/feature/` |
| Architecture | `templates/architecture/` |
| API docs | `templates/api/` |
| Guides | `templates/guides/` |

---

## Advanced Search Techniques

### Boolean Search

**GitHub search supports Boolean operators:**

```bash
# AND (default)
agent pipeline

# OR
agent OR pipeline

# NOT
agent -pipeline

# Exact phrase
"multi-agent pipeline"

# Wildcard
agent*
```

### File-Specific Search

**Limit search to specific file types:**

```bash
# Search only in markdown files
grep -r "keyword" --include="*.md"

# Search in Python files
grep -r "keyword" --include="*.py"

# Search in TypeScript files
grep -r "keyword" --include="*.ts" --include="*.tsx"
```

### Location-Specific Search

**Search in specific directories:**

```bash
# Search only in guides
grep -r "keyword" guides/

# Search only in docs
grep -r "keyword" docs/

# Search only in backend
grep -r "keyword" apps/backend/
```

### Regular Expressions

**For advanced users:**

```bash
# Find all TODO comments
grep -r "TODO:" docs/

# Find email addresses
grep -r "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" docs/

# Find issue references
grep -r "#[0-9]+" docs/
```

---

## Browser Search Tips

### Browser Shortcuts

| Action | Windows/Linux | macOS |
|--------|---------------|-------|
| Find in page | `Ctrl+F` | `Cmd+F` |
| Find next | `Enter` or `F3` | `Enter` or `G` |
| Find previous | `Shift+Enter` | `Shift+Enter` |
| Close find | `Esc` | `Esc` |

### Search Operators (GitHub)

| Operator | Purpose | Example |
|----------|---------|---------|
| `in:file` | Search file content | `memory in:file` |
| `in:path` | Search file path | `cli in:path` |
| `filename:md` | File extension | `filename:md agent` |
| `user:username` | Search by user | `user:username` |
| `org:orgname` | Search by org | `org:OBenner` |

---

## When to Use Different Resources

### Use the Search Index When...

- ✅ You want to browse by category
- ✅ You need an overview of available docs
- ✅ You're not sure what document to look for
- ✅ You want to see related documents
- ✅ You prefer a curated, organized view

### Use GitHub Search When...

- ✅ You need to search code as well as docs
- ✅ You want to search the entire repository
- ✅ You need advanced search operators
- ✅ You're looking for specific terms in files
- ✅ You want to search commit history

### Use IDE Search When...

- ✅ You're already working in the code
- ✅ You need to search while developing
- ✅ You want quick results without leaving your editor
- ✅ You need to search across open files

### Use Command Line Search When...

- ✅ You're working in a terminal
- ✅ You need to script searches
- ✅ You want to use grep/ripgrep features
- ✅ You're doing batch processing

---

## Quick Search Examples

### Example 1: Finding How to Use Memory

**Approach 1: Search Index**
1. Open [INDEX.md](INDEX.md)
2. Search for "memory"
3. Find: "Memory System" in Features section
4. Click link to [MEMORY-SYSTEM.md](../features/MEMORY-SYSTEM.md)

**Approach 2: Direct Navigation**
1. Go to Features section
2. Find "Memory System" row
3. Click link

### Example 2: Finding CLI Commands

**Approach 1: Search Index**
1. Open [INDEX.md](INDEX.md)
2. Search for "cli" or "command"
3. Find: "CLI Usage" in Getting Started
4. Click link to [CLI-USAGE.md](../../guides/CLI-USAGE.md)

**Approach 2: GitHub Search**
1. Go to GitHub repo
2. Search: "cli commands"
3. Filter to "Code"
4. Open `guides/CLI-USAGE.md`

### Example 3: Finding Architecture Info

**Approach 1: Search Index**
1. Open [INDEX.md](INDEX.md)
2. Go to Architecture & Design section
3. Browse available architecture docs
4. Click relevant link

**Approach 2: grep**
```bash
grep -rn "architecture" docs/ --include="*.md"
```

---

## Troubleshooting Search

### Can't Find What You're Looking For?

**1. Try different keywords**
- "agent" vs "agents" vs "planner"
- "cli" vs "command-line" vs "terminal"
- "memory" vs "graphiti" vs "knowledge-graph"

**2. Check related sections**
- If not in "Getting Started", try "Architecture"
- If not in "Features", try "Development"

**3. Use broader searches**
- Instead of "how to customize agents", search for "customization"
- Instead of "graphiti memory setup", search for "memory"

**4. Check the main docs**
- [docs/README.md](../README.md) - Documentation index
- [guides/README.md](../../guides/README.md) - Guides index
- [CLAUDE.md](../../CLAUDE.md) - Main architecture doc

**5. Look at templates**
- [docs/templates/README.md](../templates/README.md) - Template overview

---

## Best Practices

### For New Users

1. **Start with Quick Start** - [QUICK-START.md](../../guides/QUICK-START.md)
2. **Use the Search Index** - Browse by category
3. **Read main docs first** - [CLAUDE.md](../../CLAUDE.md), [README.md](../../README.md)

### For Developers

1. **Bookmark key docs** - CLAUDE.md, CONTRIBUTING.md
2. **Use IDE search** - Quick searches while coding
3. **Check templates** - When writing new docs

### For Contributors

1. **Follow style guide** - [STYLE_GUIDE.md](../STYLE_GUIDE.md)
2. **Use templates** - [docs/templates/](../templates/)
3. **Update index** - When adding new docs

---

## Additional Resources

- [Main Documentation Index](../README.md) - Docs overview
- [Style Guide](../STYLE_GUIDE.md) - Writing documentation
- [Contributing Guide](../../CONTRIBUTING.md) - Contributing to Auto Code
- [Troubleshooting Guide](../../guides/TROUBLESHOOTING.md) - Common issues

---

## Quick Reference Card

Print or bookmark this for quick access:

| I want to... | Search term | Location |
|--------------|-------------|----------|
| Get started | "quick start" or "beginner" | guides/QUICK-START.md |
| Use CLI | "cli" or "command-line" | guides/CLI-USAGE.md |
| Customize | "customization" or "customize" | guides/AGENT-CUSTOMIZATION.md |
| Understand architecture | "architecture" or "design" | CLAUDE.md, docs/modules/ |
| Learn about memory | "memory" or "graphiti" | docs/features/MEMORY-SYSTEM.md |
| Deploy to cloud | "cloud" or "deployment" | guides/CLOUD_*.md |
| Write docs | "style" or "template" | docs/STYLE_GUIDE.md |
| Fix issues | "troubleshooting" or "debug" | guides/TROUBLESHOOTING.md |
| API reference | "api" or "endpoint" | docs/api/ |
| Contribute | "contributing" or "development" | CONTRIBUTING.md |

---

**Last Updated:** 2025-02-12

**Related Documentation:**
- [Search Index](INDEX.md) - Comprehensive documentation index
- [docs/README.md](../README.md) - Documentation hub
- [guides/README.md](../../guides/README.md) - Guides hub
