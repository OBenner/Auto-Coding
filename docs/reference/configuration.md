# Configuration Reference

This document provides a complete reference for all environment variables supported by Auto Code. These variables control authentication, AI providers, integrations, memory systems, and more.

## Quick Start

1. Copy `apps/backend/.env.example` to `apps/backend/.env`
2. Configure required authentication variables
3. Add optional integrations as needed
4. Restart the backend to apply changes

## Table of Contents

- [Authentication (Required)](#authentication-required)
- [Custom API Endpoint](#custom-api-endpoint)
- [Multi-Provider Configuration](#multi-provider-configuration)
- [Per-Agent Provider Configuration](#per-agent-provider-configuration)
- [Agent-Specific Model Configuration](#agent-specific-model-configuration)
- [Git/Worktree Settings](#gitworktree-settings)
- [Debug Mode](#debug-mode)
- [Linear Integration](#linear-integration)
- [GitLab Integration](#gitlab-integration)
- [Knowledge Base Integration](#knowledge-base-integration)
- [UI Settings](#ui-settings)
- [Electron MCP Server](#electron-mcp-server)
- [Actor-Critic MCP Server](#actor-critic-mcp-server)
- [Graphiti Memory Integration](#graphiti-memory-integration)
- [Webhook Integration](#webhook-integration)
- [Configuration Examples](#configuration-examples)

---

## Authentication (Required)

Auto Code uses Claude Code OAuth authentication. Direct API keys (ANTHROPIC_API_KEY) are NOT supported to prevent silent billing.

### Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `CLAUDE_CODE_OAUTH_TOKEN` | OAuth token for Claude Code | Yes* | None |
| `ANTHROPIC_AUTH_TOKEN` | Enterprise/proxy token (CCR) | Yes* | None |

*One authentication method required

### Setup Options

**Option 1: Keychain Storage (Recommended)**

```bash
claude setup-token
```

Saves token to system keychain:
- macOS: Keychain
- Windows: Credential Manager
- Linux: secret-service

**Option 2: Environment Variable**

```bash
# In .env file
CLAUDE_CODE_OAUTH_TOKEN=your-oauth-token-here
```

**Option 3: Enterprise/Proxy (CCR)**

```bash
# In .env file
ANTHROPIC_AUTH_TOKEN=sk-zcf-x-ccr
```

### Example

```bash
# .env
CLAUDE_CODE_OAUTH_TOKEN=your-oauth-token-here
```

---

## Custom API Endpoint

Override the default Anthropic API endpoint for local proxies, API gateways, or self-hosted Claude instances.

### Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ANTHROPIC_BASE_URL` | Custom API endpoint URL | No | `https://api.anthropic.com` |
| `NO_PROXY` | Disable proxy for endpoint | No | None |
| `DISABLE_TELEMETRY` | Disable telemetry | No | `false` |
| `DISABLE_COST_WARNINGS` | Disable cost warnings | No | `false` |
| `API_TIMEOUT_MS` | API request timeout (ms) | No | `120000` |
| `AUTO_BUILD_MODEL` | Model override | No | `claude-opus-4-5-20251101` |

### Use Cases

- Local proxies (ccr, litellm)
- API gateways
- Self-hosted Claude instances

### Example

```bash
# .env
ANTHROPIC_BASE_URL=http://127.0.0.1:3456
NO_PROXY=127.0.0.1
DISABLE_TELEMETRY=true
DISABLE_COST_WARNINGS=true
API_TIMEOUT_MS=600000
```

---

## Multi-Provider Configuration

Auto Code supports multiple AI providers beyond Claude. Choose providers based on cost, privacy requirements, or model preferences.

### Supported Providers

- `claude` - Anthropic Claude (default)
- `litellm` - OpenAI GPT, Google Gemini, Ollama via LiteLLM proxy
- `openrouter` - OpenRouter proxy for multiple providers

### Global Provider Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `AI_ENGINE_PROVIDER` | Default provider for all agents | No | `claude` |

### Provider-Specific API Keys

| Variable | Description | Provider |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key | LiteLLM |
| `GOOGLE_API_KEY` | Google Gemini API key | LiteLLM |
| `ZHIPU_API_KEY` | Zhipu AI GLM API key | LiteLLM |
| `OPENROUTER_API_KEY` | OpenRouter API key | OpenRouter |
| `OLLAMA_BASE_URL` | Ollama server URL | LiteLLM |

### LiteLLM Model Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `LITELLM_MODEL` | Model identifier | `gpt-4`, `gpt-4o`, `gemini/gemini-1.5-pro` |

### Supported LiteLLM Models

- **OpenAI**: `gpt-4`, `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo`
- **Google Gemini**: `gemini/gemini-1.5-pro`, `gemini/gemini-1.5-flash`, `gemini/gemini-2.0-flash`
- **Zhipu AI GLM**: `glm-4.7`, `glm-4-plus`, `glm-4`, `glm-4-air`, `glm-4-flash`
- **Ollama**: `ollama/llama3`, `ollama/codellama`, `ollama/mistral`

### Examples

**OpenAI GPT-4:**
```bash
AI_ENGINE_PROVIDER=litellm
LITELLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...
```

**Google Gemini:**
```bash
AI_ENGINE_PROVIDER=litellm
LITELLM_MODEL=gemini/gemini-1.5-pro
GOOGLE_API_KEY=...
```

**Local Ollama:**
```bash
AI_ENGINE_PROVIDER=litellm
LITELLM_MODEL=ollama/llama3
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Per-Agent Provider Configuration

Configure different providers for different agent types to optimize cost and quality.

### Provider Priority

1. Environment variable (`AGENT_PROVIDER_<TYPE>`)
2. Global `AI_ENGINE_PROVIDER`
3. `AGENT_DEFAULT_PROVIDERS` in `phase_config.py`

### Agent Types

| Variable | Description |
|----------|-------------|
| `AGENT_PROVIDER_PLANNER` | Creates implementation plans |
| `AGENT_PROVIDER_CODER` | Implements code changes |
| `AGENT_PROVIDER_QA_REVIEWER` | Reviews and validates implementations |
| `AGENT_PROVIDER_QA_FIXER` | Fixes issues found during QA |
| `AGENT_PROVIDER_SPEC_GATHERER` | Gathers requirements for spec creation |
| `AGENT_PROVIDER_SPEC_WRITER` | Writes specification documents |
| `AGENT_PROVIDER_PR_CREATOR` | Creates pull requests |
| `AGENT_PROVIDER_ISSUE_ANALYZER` | Analyzes GitHub issues |

### Strategy Examples

**Privacy-First (Local Models):**
```bash
AI_ENGINE_PROVIDER=litellm
LITELLM_MODEL=ollama/llama3
OLLAMA_BASE_URL=http://localhost:11434
```

**Cost Optimization:**
```bash
AGENT_PROVIDER_PLANNER=claude
AGENT_MODEL_PLANNER=opus
AGENT_PROVIDER_CODER=litellm
AGENT_MODEL_CODER=gpt-4o
AGENT_PROVIDER_QA_REVIEWER=litellm
AGENT_MODEL_QA_REVIEWER=gpt-4o
OPENAI_API_KEY=sk-...
```

**Hybrid (Premium Planning, Local Implementation):**
```bash
AGENT_PROVIDER_PLANNER=claude
AGENT_MODEL_PLANNER=opus
AGENT_PROVIDER_CODER=litellm
AGENT_MODEL_CODER=ollama/codellama
AGENT_PROVIDER_QA_REVIEWER=litellm
AGENT_MODEL_QA_REVIEWER=ollama/llama3
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Agent-Specific Model Configuration

Configure different models for different agent types to optimize cost and quality.

### Model Priority

1. CLI argument (`--model`)
2. Environment variable (`AGENT_MODEL_<TYPE>`)
3. `task_metadata.json` agentModels field
4. `AGENT_DEFAULT_MODELS` in `phase_config.py`
5. Fallback to `sonnet`

### Available Claude Models

**Claude 4.5 Series (Latest):**
- `opus` (`claude-opus-4-5-20251101`) - Most capable, highest cost ($15 in / $75 out per 1M)
- `sonnet` (`claude-sonnet-4-5-20250929`) - Balanced capability and cost ($3 in / $15 out per 1M)
- `haiku` (`claude-haiku-4-5-20251001`) - Fast, low cost ($0.80 in / $4 out per 1M)

**Claude 3.5 Series:**
- `claude-3-5-sonnet-20241022` - Previous gen balanced ($3 in / $15 out per 1M)
- `claude-3-5-sonnet-20240620` - Older 3.5 Sonnet version

**Claude 3 Series:**
- `claude-3-opus-20240229` - Previous gen high capability ($15 in / $75 out per 1M)
- `claude-3-sonnet-20240229` - Previous gen balanced ($3 in / $15 out per 1M)
- `claude-3-haiku-20240307` - Previous gen fast ($0.25 in / $1.25 out per 1M)

### Available OpenAI Models (via LiteLLM)

- `gpt-4o` - Latest GPT-4 optimized model
- `gpt-4` - Original GPT-4
- `gpt-4-turbo` - Faster GPT-4 variant
- `gpt-3.5-turbo` - Fast, cost-effective

### Available Google Gemini Models (via LiteLLM)

- `gemini/gemini-1.5-pro` - Most capable Gemini model
- `gemini/gemini-1.5-flash` - Fast, cost-effective Gemini
- `gemini/gemini-2.0-flash` - Latest Gemini model

### Available Ollama Models (Local, Zero Cost)

- `ollama/llama3` - Meta's Llama 3
- `ollama/llama3.1` - Meta's Llama 3.1
- `ollama/codellama` - Meta's CodeLlama (optimized for code)
- `ollama/mistral` - Mistral AI's model
- `ollama/mixtral` - Mistral AI's mixture-of-experts model
- `ollama/gemma` - Google's Gemma
- `ollama/qwen` - Alibaba's Qwen
- `ollama/phi` - Microsoft's Phi

### Available Zhipu AI GLM Models (via LiteLLM)

- `glm-4.7` - Latest model ($0.40 in / $1.50 out per 1M, 203K context)
- `glm-4.5` - Previous generation ($0.35 in / $1.55 out per 1M)
- `glm-4-plus` - High capability variant ($0.50 in / $2.00 out per 1M)
- `glm-4` - Standard model ($0.10 in / $0.10 out per 1M)
- `glm-4-air` - Lightweight, cost-effective ($0.001 in / $0.001 out per 1M)
- `glm-4-flash` - Fast inference ($0.001 in / $0.001 out per 1M)

### Agent Types

| Variable | Description |
|----------|-------------|
| `AGENT_MODEL_PLANNER` | Creates implementation plans |
| `AGENT_MODEL_CODER` | Implements code changes |
| `AGENT_MODEL_QA_REVIEWER` | Reviews and validates implementations |
| `AGENT_MODEL_QA_FIXER` | Fixes issues found during QA |
| `AGENT_MODEL_SPEC_GATHERER` | Gathers requirements for spec creation |
| `AGENT_MODEL_SPEC_WRITER` | Writes specification documents |
| `AGENT_MODEL_PR_CREATOR` | Creates pull requests |
| `AGENT_MODEL_ISSUE_ANALYZER` | Analyzes GitHub issues |

### Strategy Examples

**Claude Cost Optimization:**
```bash
AGENT_MODEL_PLANNER=opus
AGENT_MODEL_CODER=sonnet
AGENT_MODEL_QA_REVIEWER=sonnet
AGENT_MODEL_QA_FIXER=haiku
AGENT_MODEL_SPEC_GATHERER=haiku
AGENT_MODEL_SPEC_WRITER=sonnet
```

**Quality-First:**
```bash
AGENT_MODEL_PLANNER=opus
AGENT_MODEL_CODER=opus
AGENT_MODEL_QA_REVIEWER=opus
```

**Budget:**
```bash
AGENT_MODEL_PLANNER=haiku
AGENT_MODEL_CODER=haiku
AGENT_MODEL_QA_REVIEWER=haiku
AGENT_MODEL_QA_FIXER=haiku
```

### Cost Tracking

- Cost data logged to `.auto-claude/specs/<spec>/cost_report.json`
- View costs: `python apps/backend/core/cost_tracking.py --spec <spec-id>`
- Supports Claude, OpenAI, Google Gemini, Zhipu GLM, and Ollama (zero cost)

### Model Fallback

If a model is unavailable or rate-limited, Auto Code automatically falls back:
- `opus → sonnet → haiku` (for Claude)
- Fallback behavior is logged for debugging and cost analysis

---

## Git/Worktree Settings

Configure how Auto Code handles git worktrees for isolated builds.

### Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DEFAULT_BRANCH` | Base branch for worktree creation | No | Auto-detected (`main`/`master`) |

### Example

```bash
# .env
DEFAULT_BRANCH=main
```

### Behavior

If not set, Auto Code will:
1. Auto-detect `main`/`master`
2. Fall back to current branch

Common values: `main`, `master`, `develop`

---

## Debug Mode

Enable debug logging for development and troubleshooting.

### Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DEBUG` | Enable debug mode | No | `false` |
| `DEBUG_LEVEL` | Debug log level (1-3) | No | `1` |
| `DEBUG_LOG_FILE` | Log to file instead of stdout | No | None |

### Debug Levels

- **1**: Basic - Essential debug information
- **2**: Detailed - Includes agent calls and file operations
- **3**: Verbose - Full execution traces

### Example

```bash
# .env
DEBUG=true
DEBUG_LEVEL=2
DEBUG_LOG_FILE=auto-claude/debug.log
```

### Output

Shows detailed information about:
- Runner execution
- Agent calls
- File operations
- API requests/responses

---

## Linear Integration

Enable Linear integration for real-time progress tracking.

### Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `LINEAR_API_KEY` | Linear API key | Yes* | None |
| `LINEAR_TEAM_ID` | Pre-configured team ID | No | Auto-detected |
| `LINEAR_PROJECT_ID` | Pre-configured project ID | No | Auto-created |

*Required to enable Linear integration

### Setup

1. Get API key from: `https://linear.app/YOUR-TEAM/settings/api`
2. Add to `.env` file
3. Restart backend

### Example

```bash
# .env
LINEAR_API_KEY=lin_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LINEAR_TEAM_ID=your-team-id
LINEAR_PROJECT_ID=your-project-id
```

### Behavior

- If `LINEAR_TEAM_ID` not set: Auto-detects from your Linear workspace
- If `LINEAR_PROJECT_ID` not set: Creates a new project for spec tracking

---

## GitLab Integration

Enable GitLab integration for issue tracking and merge requests. Supports both GitLab.com and self-hosted instances.

### Authentication Options

**Option 1: glab CLI OAuth (Recommended)**

```bash
# Install glab CLI
# https://gitlab.com/gitlab-org/cli#installation

# Authenticate
glab auth login

# For self-hosted
glab auth login --hostname gitlab.example.com
```

Auto Code automatically uses glab credentials (no env vars needed).

**Option 2: Personal Access Token**

Set `GITLAB_TOKEN` below. Token auth is used if set, otherwise falls back to glab CLI.

### Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GITLAB_INSTANCE_URL` | GitLab instance URL | No | `https://gitlab.com` |
| `GITLAB_TOKEN` | Personal access token | No* | None |
| `GITLAB_PROJECT` | Project (group/project or ID) | No | Auto-detected from git remote |

*Required if not using glab CLI

### Token Scopes

- **Required**: `api` (covers issues, merge requests, releases, project info)
- **Optional**: `write_repository` (only if creating new GitLab projects from local repos)

Get token from: `https://gitlab.com/-/user_settings/personal_access_tokens`

### Examples

**GitLab.com with glab CLI:**
```bash
# No env vars needed - just run:
glab auth login
```

**Self-hosted with token:**
```bash
# .env
GITLAB_INSTANCE_URL=https://gitlab.example.com
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
GITLAB_PROJECT=mygroup/myproject
```

---

## Knowledge Base Integration

Enable knowledge base integration for team documentation access. Supports Notion, Confluence, GitHub Wiki, and GitBook.

### Overview

Agents can query team documentation (coding standards, conventions, patterns) to automatically follow team processes during builds.

**Note:** Only one provider can be active at a time.

### Common Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `KNOWLEDGE_BASE_SYNC_INTERVAL` | Sync interval in seconds | `3600` (1 hour) |
| `KNOWLEDGE_BASE_MAX_DOCS` | Maximum documents to index | `1000` |

### Provider: Notion

| Variable | Description | Required |
|----------|-------------|----------|
| `KNOWLEDGE_BASE_NOTION_API_KEY` | Notion integration token | Yes |
| `KNOWLEDGE_BASE_NOTION_WORKSPACE_ID` | Workspace ID | Yes |

**Setup:**
1. Create integration: `https://www.notion.so/my-integrations`
2. Share workspace docs with integration
3. Add credentials to `.env`

**Example:**
```bash
# .env
KNOWLEDGE_BASE_NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxx
KNOWLEDGE_BASE_NOTION_WORKSPACE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### Provider: Confluence

| Variable | Description | Required |
|----------|-------------|----------|
| `KNOWLEDGE_BASE_CONFLUENCE_API_KEY` | Atlassian API token | Yes |
| `KNOWLEDGE_BASE_CONFLUENCE_API_URL` | Confluence URL | Yes |
| `KNOWLEDGE_BASE_CONFLUENCE_SPACE_KEY` | Space key | Yes |

**Setup:**
1. Get API token: `https://id.atlassian.com/manage-profile/security/api-tokens`
2. For Data Center: Use personal access token
3. Add credentials to `.env`

**Example:**
```bash
# .env
KNOWLEDGE_BASE_CONFLUENCE_API_KEY=your-atlassian-api-token
KNOWLEDGE_BASE_CONFLUENCE_API_URL=https://your-domain.atlassian.net
KNOWLEDGE_BASE_CONFLUENCE_SPACE_KEY=DOC
```

### Provider: GitHub Wiki

| Variable | Description | Required |
|----------|-------------|----------|
| `KNOWLEDGE_BASE_GITHUB_WIKI_API_KEY` | GitHub personal access token | Yes |
| `KNOWLEDGE_BASE_GITHUB_WIKI_REPOSITORY` | Repository (owner/repo) | Yes |

**Setup:**
1. Create token with `repo` scope
2. Add credentials to `.env`

**Example:**
```bash
# .env
KNOWLEDGE_BASE_GITHUB_WIKI_API_KEY=ghp_xxxxxxxxxxxxxxxxxxxxxxxx
KNOWLEDGE_BASE_GITHUB_WIKI_REPOSITORY=owner/repo
```

### Provider: GitBook

| Variable | Description | Required |
|----------|-------------|----------|
| `KNOWLEDGE_BASE_GITBOOK_API_KEY` | GitBook API token | Yes |
| `KNOWLEDGE_BASE_GITBOOK_API_URL` | GitBook API URL | No |

**Setup:**
1. Get API token: `https://app.gitbook.com/settings/developer`
2. Add credentials to `.env`

**Example:**
```bash
# .env
KNOWLEDGE_BASE_GITBOOK_API_KEY=your-gitbook-api-token
KNOWLEDGE_BASE_GITBOOK_API_URL=https://api.gitbook.com/v1
```

---

## UI Settings

Configure terminal UI appearance and behavior.

### Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ENABLE_FANCY_UI` | Enable fancy terminal UI | No | `true` |

### Features

**When enabled (`true`):**
- Icons and colors
- Interactive menus
- Progress bars
- Formatted output

**When disabled (`false`):**
- Plain text output
- Useful for CI/CD
- Better for log files

### Example

```bash
# .env
ENABLE_FANCY_UI=false
```

---

## Electron MCP Server

Enable Electron MCP server for AI agents to interact with and validate Electron desktop applications.

### Overview

This allows QA agents to:
- Capture screenshots
- Inspect windows
- Validate Electron apps during review
- Perform E2E testing

**Note:** Only QA agents (qa_reviewer, qa_fixer) receive Electron MCP tools.

### Modes

**1. CDP Mode (Default)**

Uses external `electron-mcp-server` package connecting via Chrome DevTools Protocol.

**Prerequisites:**
- Electron app running with `--remote-debugging-port=9222`
- For this project: `npm run start:mcp` (production) or `npm run dev:mcp` (dev)

**Pros:**
- ✅ Simple to test (Electron app runs separately)

**Cons:**
- ❌ Requires debugging port (security risk in production)
- ❌ External dependency (electron-mcp-server package)
- ❌ Limited to CDP capabilities

**2. Embedded Mode (Recommended for Production)**

MCP server runs inside the Electron main process with stdio transport.

**Prerequisites:**
- Electron app must be built: `npm run build`
- Backend spawns Electron app automatically via `npm start`

**Pros:**
- ✅ No debugging port required (better security)
- ✅ Direct control over MCP server implementation
- ✅ Uses official @modelcontextprotocol/sdk
- ✅ Full access to Electron APIs

**Cons:**
- ⚠️ Requires Electron app to be built

### Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ELECTRON_MCP_ENABLED` | Enable Electron MCP integration | `false` |
| `ELECTRON_MCP_MODE` | Server mode (`cdp` or `embedded`) | `cdp` |
| `ELECTRON_DEBUG_PORT` | CDP debugging port | `9222` |
| `ELECTRON_MCP_LOG_LEVEL` | Log verbosity (debug/info/warn/error) | `info` |
| `ELECTRON_MCP_TIMEOUT` | Server startup timeout (ms) | `5000` |

### Examples

**CDP Mode:**
```bash
# .env
ELECTRON_MCP_ENABLED=true
ELECTRON_MCP_MODE=cdp
ELECTRON_DEBUG_PORT=9222

# Terminal 1: Start Electron app with debugging
npm run start:mcp

# Terminal 2: Run Auto Code
python run.py --spec 001
```

**Embedded Mode:**
```bash
# .env
ELECTRON_MCP_ENABLED=true
ELECTRON_MCP_MODE=embedded
ELECTRON_MCP_LOG_LEVEL=debug

# Build Electron app
npm run build

# Run Auto Code (spawns Electron automatically)
python run.py --spec 001
```

### Documentation

See `TRANSPORT_LAYER_ARCHITECTURE_2.3.md` for detailed architecture.

---

## Actor-Critic MCP Server

Enable Actor-Critic Thinking MCP server for structured dual-perspective analysis.

### Overview

Implements the actor-critic reinforcement learning pattern for reasoning, helping agents catch edge cases and improve output quality.

The server provides a single tool (`actor_critic_thinking`) that supports:
- Creative "actor" perspective
- Analytical "critic" perspective
- Multi-round dialogue patterns (actor → critic → actor → critic ...)

**Note:** Only the `spec_critic` agent receives this tool by default.

### Prerequisites

1. Install Node.js and npm (for npx command)
2. MCP server automatically fetched via npx

### Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ACTOR_CRITIC_MCP_ENABLED` | Enable Actor-Critic MCP integration | `false` |

### Example

```bash
# .env
ACTOR_CRITIC_MCP_ENABLED=true
```

### Token Usage

Multi-round dialogue patterns can improve reasoning quality but may increase token usage. Monitor token usage during testing to ensure it stays within acceptable bounds.

### Documentation

- GitHub: `https://github.com/aquarius-wing/actor-critic-thinking-mcp`

---

## Graphiti Memory Integration

Graphiti-based persistent memory layer for cross-session context retention. Uses LadybugDB as the embedded graph database.

### Requirements

- Python 3.12 or higher
- Install: `pip install real_ladybug graphiti-core`

### Supported Providers

**LLM Providers:**
- OpenAI (default)
- Anthropic (LLM only, use with Voyage for embeddings)
- Azure OpenAI
- Ollama (local, fully offline)
- Google AI (Gemini)
- OpenRouter

**Embedder Providers:**
- OpenAI (default)
- Voyage AI
- Azure OpenAI
- Ollama (local, fully offline)
- Google AI (Gemini)
- OpenRouter

### Core Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `GRAPHITI_ENABLED` | Enable Graphiti memory | `true` |
| `GRAPHITI_DATABASE` | Database name | `auto_claude_memory` |
| `GRAPHITI_DB_PATH` | Database storage path | `~/.auto-claude/memories` |
| `GRAPHITI_LLM_PROVIDER` | LLM provider | `openai` |
| `GRAPHITI_EMBEDDER_PROVIDER` | Embedder provider | `openai` |

### Provider: OpenAI (Default)

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `OPENAI_MODEL` | LLM model | `gpt-4o-mini` |
| `OPENAI_EMBEDDING_MODEL` | Embedding model | `text-embedding-3-small` |

**Available Embedding Models:**
- `text-embedding-3-small` (1536 dim)
- `text-embedding-3-large` (3072 dim)

**Example:**
```bash
# .env
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=openai
GRAPHITI_EMBEDDER_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxxxxx
```

### Provider: Anthropic (LLM Only)

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | Required |
| `GRAPHITI_ANTHROPIC_MODEL` | LLM model | `claude-sonnet-4-5-latest` |

**Note:** Anthropic doesn't provide embeddings. Use with Voyage or OpenAI for embeddings.

**Example:**
```bash
# .env
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=anthropic
GRAPHITI_EMBEDDER_PROVIDER=voyage
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
VOYAGE_API_KEY=pa-xxxxxxxx
```

### Provider: Voyage AI (Embeddings Only)

| Variable | Description | Default |
|----------|-------------|---------|
| `VOYAGE_API_KEY` | Voyage AI API key | Required |
| `VOYAGE_EMBEDDING_MODEL` | Embedding model | `voyage-3` |

**Available Embedding Models:**
- `voyage-3` (1024 dim)
- `voyage-3-lite` (512 dim)

Get API key from: `https://www.voyageai.com/`

**Example:**
```bash
# .env
GRAPHITI_LLM_PROVIDER=anthropic
GRAPHITI_EMBEDDER_PROVIDER=voyage
VOYAGE_API_KEY=pa-xxxxxxxx
```

### Provider: Google AI (Gemini)

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google AI API key | Required |
| `GOOGLE_LLM_MODEL` | LLM model | `gemini-2.0-flash` |
| `GOOGLE_EMBEDDING_MODEL` | Embedding model | `text-embedding-004` |

Get API key from: `https://aistudio.google.com/apikey`

**Example:**
```bash
# .env
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=google
GRAPHITI_EMBEDDER_PROVIDER=google
GOOGLE_API_KEY=AIzaSyxxxxxxxx
```

### Provider: OpenRouter (Multi-Provider Aggregator)

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | OpenRouter API key | Required |
| `OPENROUTER_BASE_URL` | API base URL | `https://openrouter.ai/api/v1` |
| `OPENROUTER_LLM_MODEL` | LLM model | `anthropic/claude-sonnet-4` |
| `OPENROUTER_EMBEDDING_MODEL` | Embedding model | `openai/text-embedding-3-small` |

Get API key from: `https://openrouter.ai/keys`

**Popular Model Choices:**
- `anthropic/claude-sonnet-4`
- `openai/gpt-4o`
- `google/gemini-2.0-flash`

**Example:**
```bash
# .env
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=openrouter
GRAPHITI_EMBEDDER_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-xxxxxxxx
OPENROUTER_LLM_MODEL=anthropic/claude-sonnet-4
OPENROUTER_EMBEDDING_MODEL=openai/text-embedding-3-small
```

### Provider: Azure OpenAI

| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | Yes |
| `AZURE_OPENAI_BASE_URL` | Azure endpoint URL | Yes |
| `AZURE_OPENAI_LLM_DEPLOYMENT` | LLM deployment name | No |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding deployment name | No |

**Example:**
```bash
# .env
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=azure_openai
GRAPHITI_EMBEDDER_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=xxxxxxxx
AZURE_OPENAI_BASE_URL=https://your-resource.openai.azure.com/openai/deployments/your-deployment
AZURE_OPENAI_LLM_DEPLOYMENT=gpt-4
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
```

### Provider: Ollama (Local/Offline)

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_LLM_MODEL` | LLM model | Required |
| `OLLAMA_EMBEDDING_MODEL` | Embedding model | Required |
| `OLLAMA_EMBEDDING_DIM` | Embedding dimension | Required |

**Prerequisites:**
1. Install Ollama: `https://ollama.ai/`
2. Pull models: `ollama pull deepseek-r1:7b && ollama pull nomic-embed-text`
3. Start Ollama server (usually auto-starts)

**Popular LLM Models:**
- `deepseek-r1:7b`
- `llama3.2:3b`
- `mistral:7b`
- `phi3:medium`

**Popular Embedding Models:**
- `nomic-embed-text` (768 dim)
- `mxbai-embed-large` (1024 dim)
- `all-minilm` (384 dim)

**Example:**
```bash
# .env
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=ollama
GRAPHITI_EMBEDDER_PROVIDER=ollama
OLLAMA_LLM_MODEL=deepseek-r1:7b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIM=768
```

### Configuration Examples

**Example 1: OpenAI (Simplest)**
```bash
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=openai
GRAPHITI_EMBEDDER_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxxxxx
```

**Example 2: Anthropic + Voyage (High Quality)**
```bash
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=anthropic
GRAPHITI_EMBEDDER_PROVIDER=voyage
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
VOYAGE_API_KEY=pa-xxxxxxxx
```

**Example 3: Ollama (Fully Offline)**
```bash
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=ollama
GRAPHITI_EMBEDDER_PROVIDER=ollama
OLLAMA_LLM_MODEL=deepseek-r1:7b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIM=768
```

**Example 4: Azure OpenAI (Enterprise)**
```bash
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=azure_openai
GRAPHITI_EMBEDDER_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=xxxxxxxx
AZURE_OPENAI_BASE_URL=https://your-resource.openai.azure.com/...
AZURE_OPENAI_LLM_DEPLOYMENT=gpt-4
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
```

**Example 5: Google AI (Gemini)**
```bash
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=google
GRAPHITI_EMBEDDER_PROVIDER=google
GOOGLE_API_KEY=AIzaSyxxxxxxxx
```

**Example 6: OpenRouter (Multi-Provider)**
```bash
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=openrouter
GRAPHITI_EMBEDDER_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-xxxxxxxx
OPENROUTER_LLM_MODEL=anthropic/claude-sonnet-4
OPENROUTER_EMBEDDING_MODEL=openai/text-embedding-3-small
```

---

## Webhook Integration

Enable webhook integrations for external services to trigger builds and send notifications.

### Overview

Supports:
- **Incoming webhooks** - Trigger builds from external services
- **Outgoing webhooks** - Send build lifecycle events (start, complete, failure)

### Slack Integration

Send build notifications to Slack channels via incoming webhooks.

| Variable | Description | Required |
|----------|-------------|----------|
| `SLACK_WEBHOOK_URL` | Slack incoming webhook URL | Yes* |
| `SLACK_BOT_TOKEN` | Slack bot token for advanced API features | No |
| `SLACK_CHANNEL` | Default Slack channel | No |

*Required to enable Slack integration

**Setup:**
1. Get webhook URL: `https://api.slack.com/messaging/webhooks`
2. Add to `.env` file
3. Restart backend

**Example:**
```bash
# .env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL="#build-notifications"
```

### Discord Integration

Send build notifications to Discord channels via incoming webhooks.

| Variable | Description | Required |
|----------|-------------|----------|
| `DISCORD_WEBHOOK_URL` | Discord incoming webhook URL | Yes* |

*Required to enable Discord integration

**Setup:**
1. Server Settings → Integrations → Webhooks → New Webhook
2. Copy webhook URL
3. Add to `.env` file
4. Restart backend

**Example:**
```bash
# .env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/000000000000000000/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

### Microsoft Teams Integration

Send build notifications to Microsoft Teams channels via incoming webhooks.

| Variable | Description | Required |
|----------|-------------|----------|
| `TEAMS_WEBHOOK_URL` | Teams incoming webhook URL | Yes* |

*Required to enable Teams integration

**Setup:**
1. Teams Channel → Connectors → Incoming Webhook
2. Copy webhook URL
3. Add to `.env` file
4. Restart backend

**Example:**
```bash
# .env
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx@xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/IncomingWebhook/xxxxxxxxxxxxxxxxxxxxxxxx/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### Jira Integration

Sync build status with Jira issues. Adds comments to Jira tickets with build progress, results, and links to specs/PRs.

| Variable | Description | Required |
|----------|-------------|----------|
| `JIRA_API_URL` | Jira instance URL | Yes* |
| `JIRA_API_EMAIL` | Jira account email | Yes* |
| `JIRA_API_TOKEN` | Jira API token | Yes* |
| `JIRA_PROJECT_KEY` | Default project key | No |
| `JIRA_ISSUE_KEY` | Default issue key for notifications | No |

*Required to enable Jira integration

**Setup:**
1. Get API token: `https://id.atlassian.com/manage-profile/security/api-tokens`
2. Add credentials to `.env`
3. Restart backend

**Example:**
```bash
# .env
JIRA_API_URL=https://your-domain.atlassian.net
JIRA_API_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token-here
JIRA_PROJECT_KEY=PROJ
JIRA_ISSUE_KEY=PROJ-123
```

---

## Configuration Examples

### Development Environment

```bash
# Use Claude with fast model for development
AI_ENGINE_PROVIDER=claude
CLAUDE_CODE_OAUTH_TOKEN=your-token-here
AGENT_MODEL_CODER=haiku
AGENT_MODEL_QA_REVIEWER=haiku

# Enable debug mode
DEBUG=true
DEBUG_LEVEL=2

# Enable Graphiti with OpenAI
GRAPHITI_ENABLED=true
OPENAI_API_KEY=sk-xxxxxxxx
```

### Production Environment

```bash
# Use Claude with premium models
AI_ENGINE_PROVIDER=claude
CLAUDE_CODE_OAUTH_TOKEN=your-production-token

AGENT_MODEL_PLANNER=opus
AGENT_MODEL_CODER=sonnet
AGENT_MODEL_QA_REVIEWER=sonnet

# Enable Graphiti with Anthropic + Voyage
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=anthropic
GRAPHITI_EMBEDDER_PROVIDER=voyage
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
VOYAGE_API_KEY=pa-xxxxxxxx

# Enable Linear integration
LINEAR_API_KEY=lin_api_xxxxxxxx

# Enable Slack notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

### Cost-Optimized Environment

```bash
# Use local Ollama for everything
AI_ENGINE_PROVIDER=litellm
LITELLM_MODEL=ollama/codellama
OLLAMA_BASE_URL=http://localhost:11434

# Graphiti with Ollama (fully offline)
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=ollama
GRAPHITI_EMBEDDER_PROVIDER=ollama
OLLAMA_LLM_MODEL=deepseek-r1:7b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIM=768
```

### Privacy-First Environment

```bash
# All local models, no cloud services
AI_ENGINE_PROVIDER=litellm
LITELLM_MODEL=ollama/llama3
OLLAMA_BASE_URL=http://localhost:11434

# Local Graphiti
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=ollama
GRAPHITI_EMBEDDER_PROVIDER=ollama
OLLAMA_LLM_MODEL=llama3.2:3b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIM=768

# No external integrations
LINEAR_API_KEY=
SLACK_WEBHOOK_URL=
```

### Hybrid Environment (Cloud Planning, Local Implementation)

```bash
# Use Claude for planning, Ollama for implementation
AGENT_PROVIDER_PLANNER=claude
AGENT_MODEL_PLANNER=opus
AGENT_PROVIDER_CODER=litellm
AGENT_MODEL_CODER=ollama/codellama
AGENT_PROVIDER_QA_REVIEWER=litellm
AGENT_MODEL_QA_REVIEWER=ollama/llama3

# Authentication
CLAUDE_CODE_OAUTH_TOKEN=your-token-here

# Ollama
OLLAMA_BASE_URL=http://localhost:11434

# Graphiti with Anthropic + Voyage
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=anthropic
GRAPHITI_EMBEDDER_PROVIDER=voyage
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
VOYAGE_API_KEY=pa-xxxxxxxx
```

---

## Best Practices

### Security

✅ **DO:**
- Store API keys in environment variables
- Use `.env` file (gitignored)
- Rotate keys regularly
- Use different keys for development/production
- Use keychain storage for OAuth tokens

❌ **DON'T:**
- Hardcode API keys in source code
- Commit `.env` to version control
- Share keys via chat/email
- Use production keys in development

### Performance

- Use faster/cheaper models for simple tasks (QA fixer, spec gatherer)
- Use premium models for complex tasks (planner, spec writer)
- Enable Graphiti memory for cross-session context
- Monitor cost tracking reports

### Reliability

- Enable fallback providers for production
- Set appropriate timeouts for API requests
- Monitor webhook delivery failures
- Use embedded Electron MCP mode for production

### Privacy

- Use local Ollama models for sensitive code
- Disable telemetry when using proxies
- Use self-hosted GitLab for private repositories
- Review knowledge base access permissions

---

## Troubleshooting

### Authentication Issues

**Problem:** "Authentication failed"

**Solution:**
```bash
# Check token is set
echo $CLAUDE_CODE_OAUTH_TOKEN

# Re-run setup
claude setup-token

# Or set explicitly
export CLAUDE_CODE_OAUTH_TOKEN=your-token-here
```

### Provider Issues

**Problem:** "Provider not found"

**Solution:**
```bash
# Use valid provider name
AI_ENGINE_PROVIDER=claude  # NOT "anthropic" or "claude-sdk"
```

**Problem:** "Model not supported"

**Solution:**
```bash
# Check available models for provider
# Claude: opus, sonnet, haiku
# OpenAI (via LiteLLM): gpt-4o, gpt-4, gpt-3.5-turbo
# Gemini (via LiteLLM): gemini/gemini-1.5-pro
```

### Graphiti Issues

**Problem:** "Graphiti initialization failed"

**Solution:**
```bash
# Check provider credentials
echo $OPENAI_API_KEY  # For OpenAI
echo $ANTHROPIC_API_KEY  # For Anthropic

# Check embedding dimensions for Ollama
OLLAMA_EMBEDDING_DIM=768  # Must match model
```

### Integration Issues

**Problem:** "Linear/GitLab/Slack not working"

**Solution:**
```bash
# Verify API keys are set
echo $LINEAR_API_KEY
echo $GITLAB_TOKEN
echo $SLACK_WEBHOOK_URL

# Check API URLs are correct
echo $GITLAB_INSTANCE_URL
echo $JIRA_API_URL

# Restart backend after changes
```

---

## See Also

- [Environment Variable Schema](../configuration/environment-vars.md) - Detailed schema documentation
- [Multi-Provider Guide](../guides/multi-provider.md) - Provider selection strategies
- [Graphiti Integration](../integrations/graphiti.md) - Memory system configuration
- [MCP Servers](../mcp-servers/README.md) - MCP server integrations

---

**Last Updated:** 2026-03-05
