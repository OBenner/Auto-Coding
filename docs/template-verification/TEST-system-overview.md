# Auto Claude System Architecture

## Executive Summary

Auto Claude is a multi-agent autonomous coding framework that builds software through coordinated AI agent sessions. The system uses the Claude Agent SDK to run agents in isolated workspaces with comprehensive security controls.

**Key Facts:**

| Property | Value |
|----------|-------|
| **Architecture Pattern** | Multi-agent pipeline with isolated worktrees |
| **Primary Language** | Python 3.12+ (backend), TypeScript (frontend) |
| **Agent Framework** | Claude Agent SDK |
| **Memory System** | Graphiti (graph database) |
| **UI** | Electron + React desktop app |
| **Security Model** | 3-layer defense (sandbox, permissions, allowlist) |

## System Context

### Business Context

Auto Claude enables developers to delegate complex coding tasks to AI agents that work autonomously in isolated environments. The system creates detailed specifications, generates implementation plans, writes code, and validates results through QA cycles.

### System Boundaries

**In Scope:**
- Spec creation and validation
- Implementation planning and execution
- Code generation and modification
- QA validation and fixing
- Memory and context management

**Out of Scope:**
- Code hosting (uses git)
- CI/CD execution (integrates with existing)
- Production deployment
- Runtime monitoring

### External Dependencies

| Dependency | Type | Purpose |
|------------|------|---------|
| **Claude API** | AI Service | LLM inference for agents |
| **Graphiti** | Memory | Knowledge graph and context storage |
| **Git** | Version Control | Worktree isolation and code management |
| **Linear** (optional) | Project Management | Progress tracking |
| **GitHub** (optional) | Code Hosting | Issue and PR integration |

## High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Electron Desktop UI                │
│          (Task Management, Settings, Logs)          │
└────────────────────┬────────────────────────────────┘
                     │ IPC
┌────────────────────▼────────────────────────────────┐
│               Python Backend (CLI)                  │
│  ┌──────────────────────────────────────────────┐  │
│  │         Spec Creation Pipeline               │  │
│  │  Gatherer → Researcher → Writer → Critic    │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │       Implementation Pipeline                │  │
│  │  Planner → Coder → QA Reviewer → QA Fixer   │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
   ┌────▼───┐  ┌────▼────┐  ┌───▼────┐
   │ Claude │  │Graphiti │  │  Git   │
   │   SDK  │  │ Memory  │  │Worktree│
   └────────┘  └─────────┘  └────────┘
```

### Pattern: Multi-Agent Pipeline

Auto Claude uses a pipeline pattern where specialized agents handle different phases:

1. **Spec Phase**: Create detailed specifications
2. **Plan Phase**: Generate implementation plan with subtasks
3. **Code Phase**: Implement subtasks (can spawn parallel subagents)
4. **QA Phase**: Validate and fix issues

### Core Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **Agent Runner** | `apps/backend/agents/` | Agent orchestration and execution |
| **Security System** | `apps/backend/core/security.py` | Command validation and sandboxing |
| **Memory Manager** | `apps/backend/integrations/graphiti/` | Context and knowledge graph |
| **Worktree Manager** | `apps/backend/cli/worktree.py` | Git isolation for builds |
| **Desktop UI** | `apps/frontend/` | User interface and task management |

## Technology Stack

### Languages & Frameworks

| Component | Technology | Version |
|-----------|-----------|---------|
| **Backend** | Python | 3.12+ |
| **Frontend** | TypeScript + React | 18.x |
| **Desktop** | Electron | Latest |
| **AI SDK** | Claude Agent SDK | Latest |

### Infrastructure

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Version Control** | Git | Code management and worktree isolation |
| **Package Manager** | uv (Python), npm (Node) | Dependency management |
| **Build Tools** | electron-builder | Desktop app packaging |

### Data Storage

| Store | Technology | Purpose |
|-------|-----------|---------|
| **Memory Graph** | Graphiti + LadybugDB | Knowledge graph and semantic search |
| **Config Storage** | JSON files | Specs, plans, QA reports |
| **User Preferences** | System Keychain | API tokens and settings |

## Data Flow

### Request Flow

1. User creates task via desktop UI
2. Spec creation pipeline generates specification
3. Implementation pipeline creates plan
4. Coder agent implements in isolated worktree
5. QA agent validates and reports issues
6. QA fixer resolves issues
7. User reviews and merges changes

### Data Persistence

- **Specs**: `.auto-claude/specs/XXX/spec.md`
- **Plans**: `.auto-claude/specs/XXX/implementation_plan.json`
- **Memory**: `.auto-claude/specs/XXX/graphiti/`
- **Code**: `.auto-claude/worktrees/tasks/XXX/`

## Security Architecture

### Three-Layer Defense

1. **OS Sandbox**: Bash command isolation
2. **Filesystem Permissions**: Restricted to project directory
3. **Command Allowlist**: Dynamic allowlist from project analysis

### Authentication

- **Claude API**: OAuth token stored in system keychain
- **Linear API**: Optional API key in environment
- **GitHub API**: gh CLI authentication

## Deployment Architecture

### Environments

| Environment | Purpose | Deployment |
|------------|---------|------------|
| **Development** | Local development | `npm run dev` |
| **Production** | End users | Desktop app installers |

### Scaling Strategy

Auto Claude runs locally on user machines. Scaling is handled by:
- Parallel subagent execution for independent tasks
- Efficient memory caching
- Worktree isolation for concurrent builds

## Performance Characteristics

- **Spec Creation**: 2-5 minutes (depends on complexity)
- **Implementation**: Varies by feature size
- **Memory Overhead**: ~200MB baseline + agent sessions
- **Disk Usage**: ~500MB + project size

## Key Architectural Decisions

### Decision 1: Git Worktrees for Isolation

**Choice**: Use git worktrees instead of branches
**Rationale**: Allows multiple builds in parallel without switching branches
**Trade-offs**: Slightly more disk space, but better isolation
**Alternatives**: Branches (requires switching), Docker (heavy)

### Decision 2: Graphiti for Memory

**Choice**: Use Graphiti graph database for agent memory
**Rationale**: Knowledge graphs better represent code relationships
**Trade-offs**: Additional setup, but richer context
**Alternatives**: Vector DB only (less relational), No memory (no learning)

### Decision 3: Multi-Agent Pipeline

**Choice**: Specialized agents for different phases
**Rationale**: Clear separation of concerns, easier to debug
**Trade-offs**: More agents, but better maintainability
**Alternatives**: Single agent (less modular), Manual workflow (slower)

## Future Roadmap

**High Priority:**
- System theme detection for dark mode
- Custom MCP server integration
- Enhanced error recovery

**Medium Priority:**
- Multi-language documentation
- Cloud memory sync
- Team collaboration features

## Appendix

### Glossary

- **Spec**: Feature specification document
- **Worktree**: Isolated git working directory
- **MCP**: Model Context Protocol (for tool integration)
- **Agent**: AI-powered autonomous task executor

### Related Documentation

- [Core Architecture](./backend-architecture.md)
- [Memory System](./memory-system.md)
- [Security Model](./security-model.md)
