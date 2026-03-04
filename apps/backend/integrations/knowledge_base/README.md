# Team Knowledge Base Integration

Connect your team's documentation to Auto Code so agents can reference coding standards, conventions, architecture decisions, and best practices during builds.

## Supported Providers

| Provider | Auth Method | What It Syncs |
|----------|-------------|---------------|
| **Notion** | Integration token | All workspace pages, converted to markdown |
| **Confluence** | API token | All pages in a space, CQL-based filtering |
| **GitHub Wiki** | Personal access token | All markdown files from wiki repo |
| **GitBook** | API token | All pages across accessible spaces |

## Quick Start

### 1. Set Environment Variables

Add one provider's credentials to `apps/backend/.env`:

**Notion:**
```bash
KNOWLEDGE_BASE_NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxx
KNOWLEDGE_BASE_NOTION_WORKSPACE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**Confluence:**
```bash
KNOWLEDGE_BASE_CONFLUENCE_API_KEY=your-atlassian-api-token
KNOWLEDGE_BASE_CONFLUENCE_API_URL=https://your-domain.atlassian.net
KNOWLEDGE_BASE_CONFLUENCE_SPACE_KEY=DOC
```

**GitHub Wiki:**
```bash
KNOWLEDGE_BASE_GITHUB_WIKI_API_KEY=ghp_xxxxxxxxxxxxxxxxxxxxxxxx
KNOWLEDGE_BASE_GITHUB_WIKI_REPOSITORY=owner/repo
```

**GitBook:**
```bash
KNOWLEDGE_BASE_GITBOOK_API_KEY=your-gitbook-api-token
KNOWLEDGE_BASE_GITBOOK_API_URL=https://api.gitbook.com
```

### 2. Optional Settings

```bash
KNOWLEDGE_BASE_SYNC_INTERVAL=3600   # Sync interval in seconds (default: 1 hour, min: 5 min)
KNOWLEDGE_BASE_MAX_DOCS=1000        # Max documents to index (default: 1000)
```

### 3. Run a Build

The knowledge base initializes automatically when agents start. No manual setup needed.

## How It Works

### Architecture

```
KnowledgeBaseManager (orchestrator)
├── KnowledgeBaseConfig (env-based configuration)
├── KnowledgeBaseState (sync tracking, persisted to .knowledge_base.json)
├── BaseConnector (abstract interface)
│   ├── NotionConnector
│   ├── ConfluenceConnector
│   ├── GitHubWikiConnector
│   └── GitBookConnector
└── DocumentationIndexer (keyword search over cached documents)
```

### Sync Flow

1. **Initialization** — `KnowledgeBaseManager` reads environment variables and picks the first provider with valid configuration
2. **Connection** — The connector authenticates with the provider API (or clones the wiki repo for GitHub Wiki)
3. **Full Sync** — Fetches all documents and converts them to markdown
4. **Incremental Sync** — On subsequent runs, only fetches documents modified since the last sync
5. **Indexing** — Documents are cached locally in `.knowledge_base_documents.json` inside the spec directory
6. **Search** — Keyword-based search with title weighting (2x), content matching, and exact phrase bonus (3x)

### Agent Integration

Agents get two tools for accessing team documentation:

- **`search_team_docs`** — Search documentation by query (e.g., "authentication flow", "coding standards")
- **`get_team_docs`** — List all available documentation with source grouping

The `memory_manager.get_team_context()` function is called automatically during builds to provide relevant documentation context for each subtask.

### State Tracking

Sync state is persisted per spec in `.auto-claude/specs/XXX/.knowledge_base.json`:

```json
{
  "initialized": true,
  "provider": "notion",
  "last_sync": "2026-03-04T12:00:00",
  "sync_status": "success",
  "total_docs": 42,
  "indexed_docs": 42,
  "failed_docs": 0,
  "doc_mapping": { "page-id": { "title": "...", "url": "...", "source": "Notion" } }
}
```

Sync statuses: `idle`, `running`, `success`, `partial` (some docs failed), `failed`.

### Frontend IPC Channels

The Electron frontend exposes three IPC channels for knowledge base configuration:

| Channel | Purpose |
|---------|---------|
| `knowledgeBase:getConfig` | Get current KB configuration |
| `knowledgeBase:updateConfig` | Update KB provider settings |
| `knowledgeBase:testConnection` | Test connection to configured provider |

## Module Reference

| File | Purpose |
|------|---------|
| `config.py` | `KnowledgeBaseConfig` (env parsing), `KnowledgeBaseState` (persistence), constants |
| `base.py` | `BaseConnector` abstract class with shared sync state helpers |
| `manager.py` | `KnowledgeBaseManager` — high-level orchestrator for sync, search, status |
| `indexer.py` | `DocumentationIndexer` — document caching and keyword search |
| `connectors/notion.py` | Notion API connector (pagination, block-to-markdown conversion) |
| `connectors/confluence.py` | Confluence REST API connector (CQL search, storage-to-markdown) |
| `connectors/github_wiki.py` | GitHub Wiki connector (git clone/pull, reads .md files) |
| `connectors/gitbook.py` | GitBook API connector (spaces, pages, node-to-markdown) |
| `tools/knowledge_base.py` | Agent SDK tool definitions (`search_team_docs`, `get_team_docs`) |

## Provider-Specific Notes

### Notion
- Create an integration at https://www.notion.so/my-integrations
- Share pages/databases with the integration for access
- API version: `2022-06-28`
- Converts all block types to markdown (paragraphs, headings, lists, code, quotes, callouts, dividers, todos)

### Confluence
- Uses Atlassian REST API v2
- Requires API token from https://id.atlassian.com/manage-profile/security/api-tokens
- Fetches all pages in the configured space via CQL
- Converts Confluence storage format (XHTML) to markdown

### GitHub Wiki
- Clones the wiki repo (`owner/repo.wiki.git`) to a temporary directory
- Reads all `.md` files, derives titles from filenames
- Incremental sync uses `git pull` + file modification timestamps
- Credentials are sanitized in all log output

### GitBook
- Uses GitBook REST API v1
- Fetches all accessible spaces, then all pages per space
- Supports multiple content formats (markdown, nodes, text)
- Converts GitBook content nodes to markdown (paragraphs, headings, lists, code, quotes, callouts)
