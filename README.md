# Auto Code

**Autonomous multi-agent coding framework that plans, builds, and validates software for you.**

![Auto Code Kanban Board](.github/assets/Auto-Coding-Kanban.png)

[![License](https://img.shields.io/badge/license-AGPL--3.0-green?style=flat-square)](./agpl-3.0.txt)

[![CI](https://img.shields.io/github/actions/workflow/status/OBenner/Auto-Coding/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/OBenner/Auto-Coding/actions)

---

> **🔱 This is a fork of [AndyMik90/Auto-Code](https://github.com/AndyMik90/Auto-Code)**
>
> This repository contains custom modifications and enhancements on top of the original project.
> I aim to keep it in sync with upstream changes while maintaining my own features.
>
> **Fork repository:** [OBenner/Auto-Coding](https://github.com/OBenner/Auto-Coding)

---

## Fork Enhancements

### Completed Features

| Feature | Description |
|---------|-------------|
| **Memory System Dashboard** | Graph visualization of memories, delete/export functionality |
| **Resource Monitoring** | Enhanced progress tracking with resource usage display |
| **Ollama Integration** | Local model support via Ollama service |
| **Platform Abstraction** | Complete cross-platform support (Windows, macOS, Linux) |
| **Automated Test Generation** | AI-generated tests in QA validation loop |
| **Token Statistics** | Per-phase token usage tracking and visualization |
| **Skeleton Loading States** | Improved UX with loading skeletons for data-heavy components |
| **QA Status Tool** | Read tool for checking QA validation status |
| **Spec Statistics Tool** | Analytics for spec creation and completion |
| **Troubleshooting Guide** | Comprehensive FAQ for common issues |
| **Web Interface** | Browser-based access option |
| **Research Improvements** | Enhanced web search guidance in spec creation |

### Roadmap

| Feature | Description |
|---------|-------------|
| **Multi-Model Provider Support** | OpenAI GPT, Google Gemini, local models via Ollama |
| **Code Review Agent** | Specialized agent for security/performance code review |
| **AI Pair Programming Mode** | Real-time interactive coding assistance |
| **Multi-Codebase Orchestration** | Manage multiple repos from single instance |
| **Intelligent Pattern Recognition** | Auto-extract and suggest coding patterns from memory |

---

## Download

### Stable Release


## Requirements

- **Claude Pro/Max subscription** - [Get one here](https://claude.ai/upgrade)
- **Claude Code CLI** - `npm install -g @anthropic-ai/claude-code`
- **Git repository** - Your project must be initialized as a git repo

---

## Quick Start

1. **Download and install** the app for your platform
2. **Open your project** - Select a git repository folder
3. **Connect Claude** - The app will guide you through OAuth setup
4. **Create a task** - Describe what you want to build
5. **Watch it work** - Agents plan, code, and validate autonomously

---

## Features

| Feature | Description |
|---------|-------------|
| **Autonomous Tasks** | Describe your goal; agents handle planning, implementation, and validation |
| **Parallel Execution** | Run multiple builds simultaneously with up to 12 agent terminals |
| **Isolated Workspaces** | All changes happen in git worktrees - your main branch stays safe |
| **Self-Validating QA** | Built-in quality assurance loop catches issues before you review |
| **AI-Powered Merge** | Automatic conflict resolution when integrating back to main |
| **Memory Layer** | Agents retain insights across sessions for smarter builds |
| **GitHub/GitLab Integration** | Import issues, investigate with AI, create merge requests |
| **Linear Integration** | Sync tasks with Linear for team progress tracking |
| **Cloud-Hosted Option** | Fully managed cloud deployment - no local installation required |
| **Cross-Platform** | Native desktop apps for Windows, macOS, and Linux |
| **Auto-Updates** | App updates automatically when new versions are released |

---

## Interface

### Kanban Board
Visual task management from planning through completion. Create tasks and monitor agent progress in real-time.

### Agent Terminals
AI-powered terminals with one-click task context injection. Spawn multiple agents for parallel work.

![Agent Terminals](.github/assets/Auto-Coding-Agents-terminals.png)

### Roadmap
AI-assisted feature planning with competitor analysis and audience targeting.

![Roadmap](.github/assets/Auto-Coding-roadmap.png)

### Additional Features
- **Insights** - Chat interface for exploring your codebase
- **Ideation** - Discover improvements, performance issues, and vulnerabilities
- **Changelog** - Generate release notes from completed tasks

---

## Project Structure

```
Auto-Code/
├── apps/
│   ├── backend/     # Python agents, specs, QA pipeline
│   └── frontend/    # Electron desktop application
├── guides/          # Additional documentation
├── tests/           # Test suite
└── scripts/         # Build utilities
```

---

## CLI Usage

For headless operation, CI/CD integration, or terminal-only workflows:

```bash
cd apps/backend

# Create a spec interactively
python spec_runner.py --interactive

# Run autonomous build
python run.py --spec 001

# Review and merge
python run.py --spec 001 --review
python run.py --spec 001 --merge
```

See [guides/CLI-USAGE.md](guides/CLI-USAGE.md) for complete CLI documentation.

---

## Deployment Options

Auto Code can be deployed in multiple ways to suit your needs:

### 🖥️ Local Desktop (Recommended for Individual Developers)

Download and run the native desktop application on Windows, macOS, or Linux. All processing happens locally on your machine.

**Best for:** Individual developers, small teams, full control over execution environment

### ☁️ Cloud-Hosted (Recommended for Teams & Enterprise)

Deploy Auto Code to cloud infrastructure for centralized access without local installation. Users access via web interface with OAuth authentication.

**Best for:** Teams, enterprises, users who want instant access without setup

**Features:**
- Multi-user authentication and authorization
- Centralized usage tracking and rate limiting
- Git repository integration (GitHub/GitLab OAuth)
- Scalable infrastructure with Kubernetes support
- No local installation required

**Documentation:**
- **[Cloud Overview](guides/CLOUD_README.md)** - Understanding the cloud-hosted architecture
- **[Cloud Setup Guide](guides/CLOUD_SETUP.md)** - Initial deployment and configuration
- **[Cloud Deployment Guide](guides/CLOUD_DEPLOYMENT.md)** - Production operations and scaling

---

## Development

Want to build from source or contribute? See [CONTRIBUTING.md](CONTRIBUTING.md) for complete development setup instructions.

For Linux-specific builds (Flatpak, AppImage), see [guides/linux.md](guides/linux.md).

---

## Security

Auto Code uses a three-layer security model:

1. **OS Sandbox** - Bash commands run in isolation
2. **Filesystem Restrictions** - Operations limited to project directory
3. **Dynamic Command Allowlist** - Only approved commands based on detected project stack

All releases are:
- Scanned with VirusTotal before publishing
- Include SHA256 checksums for verification
- Code-signed where applicable (macOS)

---

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run install:all` | Install backend and frontend dependencies |
| `npm start` | Build and run the desktop app |
| `npm run dev` | Run in development mode with hot reload |
| `npm run package` | Package for current platform |
| `npm run package:mac` | Package for macOS |
| `npm run package:win` | Package for Windows |
| `npm run package:linux` | Package for Linux |
| `npm run package:flatpak` | Package as Flatpak (see [guides/linux.md](guides/linux.md)) |
| `npm run lint` | Run linter |
| `npm test` | Run frontend tests |
| `npm run test:backend` | Run backend tests |

---

## Contributing

We welcome contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup instructions
- Code style guidelines
- Testing requirements
- Pull request process

---

## Community

- **Discord** - [Join our community](https://discord.gg/KCXaPBr4Dj)
- **Issues** - [Report bugs or request features](https://github.com/OBenner/Auto-Coding/issues)
- **Discussions** - [Ask questions](https://github.com/OBenner/Auto-Coding/discussions)

---

## License

**AGPL-3.0** - GNU Affero General Public License v3.0

Auto Code is free to use. If you modify and distribute it, or run it as a service, your code must also be open source under AGPL-3.0.

Commercial licensing available for closed-source use cases.

---

## Star History

[![GitHub Repo stars](https://img.shields.io/github/stars/OBenner/Auto-Coding?style=social)](https://github.com/OBenner/Auto-Coding/stargazers)

[![Star History Chart](https://api.star-history.com/svg?repos=OBenner/Auto-Coding&type=Date)](https://star-history.com/#OBenner/Auto-Coding&Date)
