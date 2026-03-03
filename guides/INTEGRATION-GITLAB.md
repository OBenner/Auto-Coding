# GitLab Integration Guide

This document covers setting up and using GitLab integration with Auto Claude. GitLab integration is **optional** - if not configured, Auto Claude continues to work with local tracking only.

## What It Does

GitLab integration provides AI-powered code review automation for GitLab merge requests:

- **MR Review**: Automated merge request review using Claude AI agents
  - Analyzes code changes for bugs, security issues, and code quality
  - Provides structured findings with severity levels (critical, high, medium, low)
  - Posts review comments directly to the MR
  - Supports approval workflow integration

- **Follow-up Review**: Incremental review after new commits
  - Tracks reviewed commits to avoid duplicate feedback
  - Identifies new issues introduced in follow-up commits
  - Reports resolved findings from previous reviews
  - Reduces review noise by focusing only on new changes

- **Self-Hosted Support**: Works with both GitLab.com and self-hosted GitLab instances

## When to Use GitLab

- Your team uses GitLab for version control
- You want automated code review on merge requests
- You're running long-running branches and need incremental reviews
- You want to catch bugs before they reach main branch
- You're using a self-hosted GitLab instance

## Prerequisites

- GitLab account (GitLab.com or self-hosted)
- GitLab project with merge requests
- Auto Claude backend installed

## Setup

**Step 1:** Choose authentication method

Auto Claude supports two authentication methods for GitLab:

### Option 1: glab CLI OAuth (Recommended)

The glab CLI provides secure OAuth authentication without managing tokens:

**Install glab CLI:**

**macOS:**
```bash
brew install glab
```

**Linux:**
```bash
# Linuxbrew
brew install glab

# Or manual download
curl -L https://github.com/gitlab-org/cli/releases/latest/download/glab_linux_amd64.tar.gz | tar zx
sudo mv glab /usr/local/bin/
```

**Windows:**
```bash
winget install glab
```

**Authenticate:**
```bash
# For GitLab.com
glab auth login

# For self-hosted instances
glab auth login --hostname gitlab.example.com
```

This opens your browser for OAuth authentication. Once complete, Auto Claude automatically uses your glab credentials (no environment variables needed).

**How Auto Claude uses glab:** Auto Claude spawns `glab` as a subprocess to make GitLab API calls. This means:
- `glab` must be available on your `PATH`
- Minimum recommended version: `glab` >= 1.50.0
- Auto Claude does not read glab config files directly -- it invokes `glab` CLI commands
- Verify Auto Claude can find glab: `which glab && glab --version`

### Option 2: Personal Access Token

If you prefer using a Personal Access Token:

1. Go to GitLab User Settings → Access Tokens
   - GitLab.com: https://gitlab.com/-/user_settings/personal_access_tokens
   - Self-hosted: `https://gitlab.example.com/-/user_settings/personal_access_tokens`

2. Create a new token with scopes:
   - `api` (required) - Full API access to issues, MRs, and projects
   - `write_repository` (optional) - Only if creating new GitLab projects from local repos

3. Copy the token (format: `glpat-xxx...`)

**Step 2:** Configure environment variables

Navigate to the backend directory:

```bash
cd apps/backend
```

Edit `.env` and add GitLab configuration:

```bash
# GitLab Integration (OPTIONAL)

# GitLab Instance URL (defaults to gitlab.com)
# For self-hosted instances, set your hostname:
GITLAB_INSTANCE_URL=https://gitlab.example.com

# GitLab Personal Access Token (only if NOT using glab CLI)
# GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx

# GitLab Project (OPTIONAL - format: group/project or numeric ID)
# If not set, Auto Claude will auto-detect from git remote
# GITLAB_PROJECT=mygroup/myproject
```

**Step 3:** Verify configuration

Test your GitLab authentication:

```bash
# If using glab CLI
glab auth status

# If using token
curl -H "PRIVATE-TOKEN: glpat-xxx" https://gitlab.com/api/v4/user
```

## How It Works

### MR Review Workflow

The MR review process analyzes merge requests for code quality issues:

**1. Fetch MR Context**
```bash
# Get MR details, changes, and commits
GET /api/v4/projects/:project/merge_requests/:iid
GET /api/v4/projects/:project/merge_requests/:iid/changes
GET /api/v4/projects/:project/merge_requests/:iid/commits
```

**2. AI Code Review**

Claude agent analyzes the diff for:
- **Bugs** - Logic errors, edge cases, incorrect implementations
- **Security Issues** - Injection vulnerabilities, authentication flaws
- **Code Quality** - Maintainability, readability, best practices
- **Performance** - Inefficient algorithms, resource leaks
- **Testing** - Missing test coverage, test quality

**3. Post Findings**

Results are posted as MR comments:

```markdown
## 🔍 Code Review Results

**Overall Assessment:** ✅ PASS / ⚠️ WARNING / ❌ FAIL

### Critical Issues
1. [CRITICAL] SQL Injection Vulnerability
   File: `src/auth.py:45`
   The user input is directly concatenated into SQL query...

### High Issues
...

### Medium Issues
...

### Low Issues
...
```

### Follow-up Review Workflow

Follow-up reviews track changes across multiple iterations:

**1. Load Previous Review State**
```bash
# Read .auto-claude/gitlab/reviews/!123/last_review.json
{
  "reviewed_commits": ["abc123", "def456"],
  "findings": [...],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**2. Identify New Commits**
```bash
# Get commits since last review
new_commits = [c for c in current_commits if c not in reviewed_commits]
```

**3. Analyze Only New Changes**
- Skip already-reviewed commits
- Focus on new diffs only
- Reduce review noise and token usage

**4. Update State**
```bash
# Save updated review state
{
  "reviewed_commits": ["abc123", "def456", "ghi789"],  # Added new commit
  "findings": [...],  # Updated findings
  "resolved_findings": [...],  # Fixed issues
  "new_findings": [...]  # New issues
}
```

## Usage

### Command Line Interface

Run GitLab automation from the backend directory:

```bash
cd apps/backend

# Review a merge request
python runners/gitlab/runner.py review-mr 123

# Follow-up review (after new commits)
python runners/gitlab/runner.py followup-review-mr 123

# Specify project explicitly
python runners/gitlab/runner.py review-mr 123 --project mygroup/myproject

# Use with self-hosted instance
python runners/gitlab/runner.py review-mr 123 --instance https://gitlab.example.com

# Use specific model
python runners/gitlab/runner.py review-mr 123 --model claude-sonnet-4-5-20250929
```

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--project-dir` | Project directory | Current directory |
| `--token` | GitLab token (overrides GITLAB_TOKEN) | - |
| `--project` | GitLab project (namespace/name) | Auto-detect |
| `--instance` | GitLab instance URL | https://gitlab.com |
| `--model` | AI model to use | claude-sonnet-4-5-20250929 |
| `--thinking-level` | Extended reasoning level | medium |

### Output Example

```
[MR !123] [  0%] Fetching MR details...
[MR !123] [ 20%] Analyzing code changes...
[MR !123] [ 80%] Generating review findings...
[MR !123] [100%] Posting review to GitLab...

============================================================
MR !123 Review Complete
============================================================
Status: completed
Verdict: NEEDS_CHANGES
Findings: 7

Findings by severity:
  ! [CRITICAL] SQL Injection Vulnerability
    File: src/auth.py:45
  * [HIGH] Missing Error Handling
    File: src/api.py:78
  - [MEDIUM] Unused Import
    File: src/utils.py:12
  . [LOW] Inconsistent Naming
    File: src/models.py:34
```

## Available GitLab Features

| Feature | Description |
|---------|-------------|
| `review-mr` | Full AI code review of a merge request |
| `followup-review-mr` | Incremental review of new commits only |
| Auto-detection | Automatic GitLab project detection from git remote |
| Rate limiting | Built-in retry with exponential backoff |
| Self-hosted support | Works with GitLab Community/Enterprise Edition |

## State Management

GitLab integration stores review state locally:

```
.auto-claude/gitlab/
├── config.json              # GitLab configuration (token, project, instance)
└── reviews/
    └── !123/                # Per-MR review state
        ├── last_review.json # Review state for follow-up tracking
        └── findings.json    # Detailed findings history
```

This enables:
- **Incremental reviews** - Only review new commits
- **Historical tracking** - See review history over time
- **State persistence** - Survive process restarts

## Troubleshooting

### Issue: Authentication Failed

**Symptoms:** `Error: No GitLab token found`

**Solutions:**

1. **If using glab CLI:**
   ```bash
   # Check authentication status
   glab auth status

   # Re-authenticate if needed
   glab auth login
   ```

2. **If using token:**
   ```bash
   # Verify GITLAB_TOKEN is set
   grep GITLAB_TOKEN apps/backend/.env

   # Test token manually
   curl -H "PRIVATE-TOKEN: your-token" https://gitlab.com/api/v4/user
   ```

3. **For self-hosted instances:**
   ```bash
   # Verify instance URL is correct
   grep GITLAB_INSTANCE_URL apps/backend/.env

   # Test connectivity
   curl https://gitlab.example.com/api/v4/user
   ```

### Issue: Project Not Found

**Symptoms:** `Error: No GitLab project found` or `404 Project Not Found`

**Solutions:**

1. **Auto-detect from git remote:**
   ```bash
   # Check git remote
   git remote -v

   # Should show GitLab remote like:
   # origin  git@gitlab.com:group/project.git (fetch)
   ```

2. **Set explicitly:**
   ```bash
   # In apps/backend/.env
   GITLAB_PROJECT=mygroup/myproject

   # Or via CLI
   python runners/gitlab/runner.py review-mr 123 --project mygroup/myproject
   ```

3. **Verify project exists:**
   ```bash
   # For GitLab.com
   curl https://gitlab.com/api/v4/projects/mygroup%2Fproject

   # For self-hosted
   curl https://gitlab.example.com/api/v4/projects/mygroup%2Fproject
   ```

### Issue: Rate Limited

**Symptoms:** `GitLab API error 429` or `Rate limited`

**Solutions:**

Auto Claude automatically handles rate limiting with exponential backoff. If you see persistent rate limiting:

1. **Check rate limits:**
   ```bash
   # View remaining rate limit
   curl -I -H "PRIVATE-TOKEN: your-token" https://gitlab.com/api/v4/user
   # Look for: RateLimit-Remaining, RateLimit-Reset
   ```

2. **Reduce concurrent requests:** Run reviews sequentially instead of parallel

3. **Use self-hosted instance:** Self-hosted GitLab has higher or unlimited rate limits

### Issue: Review Not Posted

**Symptoms:** Review completes but no comment appears on MR

**Solutions:**

1. **Check permissions:**
   - Verify token has `api` scope
   - Ensure user has permission to comment on MRs

2. **Check logs:**
   ```bash
   # Run with debug mode
   DEBUG=true python runners/gitlab/runner.py review-mr 123
   ```

3. **Manual verification:**
   ```bash
   # List MR notes to verify
   curl -H "PRIVATE-TOKEN: your-token" \
     https://gitlab.com/api/v4/projects/:project/merge_requests/123/notes
   ```

### Issue: Follow-up Review Shows Old Findings

**Symptoms:** Follow-up review reports issues from previous reviews

**Solutions:**

1. **Check state file:**
   ```bash
   cat .auto-claude/gitlab/reviews/!123/last_review.json
   ```

2. **Verify commit tracking:**
   ```bash
   # Check if commits are being tracked
   jq '.reviewed_commits' .auto-claude/gitlab/reviews/!123/last_review.json
   ```

3. **Clear state (if needed):**
   ```bash
   # WARNING: This will reset review history
   rm -rf .auto-claude/gitlab/reviews/!123/
   ```

## Best Practices

### Workflow Integration

- **Pre-merge reviews**: Run `review-mr` before merging to catch issues early
- **Incremental reviews**: Use `followup-review-mr` after each new commit to reduce noise
- **CI/CD integration**: Add review step to GitLab CI pipeline
  ```yaml
  # .gitlab-ci.yml
  code_review:
    stage: test
    script:
      - python apps/backend/runners/gitlab/runner.py review-mr $CI_MERGE_REQUEST_IID
    rules:
      - if: $CI_PIPELINE_SOURCE == 'merge_request_event'
  ```

### Team Collaboration

- **Review notifications**: Team members get notified when review comments are posted
- **Review assignments**: Auto-assign MRs to reviewers for accountability
- **Approval workflow**: Configure Auto Claude to approve MRs that pass review

### Performance Optimization

- **Use follow-up reviews**: Reduces token usage by 50-80% compared to full reviews
- **Model selection**: Use `haiku` for quick reviews, `sonnet` for thorough reviews
- **Batch reviews**: Review multiple MRs sequentially during quiet hours

### Security

- **Token rotation**: Rotate Personal Access Tokens periodically
- **Minimum scopes**: Only grant `api` scope (avoid `write_repository` unless needed)
- **OAuth preference**: Use glab CLI OAuth for better security (no token storage)

### Self-Hosted GitLab

For self-hosted GitLab instances:

1. **Set instance URL:**
   ```bash
   GITLAB_INSTANCE_URL=https://gitlab.example.com
   ```

2. **Configure glab CLI:**
   ```bash
   glab auth login --hostname gitlab.example.com
   ```

3. **Verify connectivity:**
   ```bash
   curl https://gitlab.example.com/api/v4/user
   ```

## Configuration Options

| Variable | Required | Description |
|----------|----------|-------------|
| `GITLAB_TOKEN` | No* | Personal Access Token (not needed if using glab CLI) |
| `GITLAB_INSTANCE_URL` | No | GitLab instance URL (default: https://gitlab.com) |
| `GITLAB_PROJECT` | No | GitLab project path (auto-detects from git remote) |

*Required if not using glab CLI OAuth

## Disable GitLab Integration

To disable GitLab integration after enabling:

```bash
# Remove or comment out in apps/backend/.env
# GITLAB_TOKEN=glpat_xxx
# GITLAB_INSTANCE_URL=https://gitlab.com
# GITLAB_PROJECT=mygroup/myproject
```

Auto Claude will continue to work normally without GitLab features.

## Secret & Environment Variable Safety

- **Never commit `.env` files** or tokens to source control -- `.env` is gitignored by default
- **Use placeholder values** in documentation and examples (e.g., `GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx`)
- **Prefer secret managers** for shared environments (OS keychain, CI masked variables, HashiCorp Vault, cloud secret managers)
- **Rotate tokens** periodically (every 60-90 days recommended)
- **Use least-privilege tokens** -- only grant `api` scope, avoid `write_repository` unless needed
- **Prefer glab OAuth** over Personal Access Tokens for better security (no token storage)

## See Also

- [Linear Integration Guide](./INTEGRATION-LINEAR.md) - Linear issues and task tracking
- [Electron MCP Guide](./INTEGRATION-ELECTRON-MCP.md) - E2E testing for Electron apps
- [CLI Usage Guide](./CLI-USAGE.md) - Terminal-only Auto Claude usage
