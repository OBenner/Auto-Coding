# Linear Integration Guide

This document covers setting up and using Linear integration with Auto Claude. Linear integration is **optional** - if not configured, Auto Claude continues to work with local tracking only.

## What It Does

Linear integration provides real-time visibility into Auto Claude build progress by syncing implementation subtasks to Linear issues:

- **Subtask → Issue Mapping**: Each subtask in `implementation_plan.json` gets a corresponding Linear issue
- **Status Sync**: Issue status updates automatically as subtasks progress (In Progress, Done, Blocked)
- **Session Comments**: Each agent session adds a comment with approach, success/failure, and git commits
- **Stuck Escalation**: When a subtask fails repeatedly, the issue moves to "Blocked" with detailed context
- **META Issue**: A special issue tracks overall build progress with session summaries

## When to Use Linear

- You're managing a project in Linear and want visibility into AI-assisted development
- You need to track Auto Claude progress alongside your manual Linear issues
- You want team visibility into what AI agents are working on
- You're running long-running builds and want centralized progress tracking

## Prerequisites

- Linear workspace (sign up at https://linear.app)
- Linear Admin or Member role (to create projects/issues)
- Auto Claude backend installed

## Setup

**Step 1:** Get your Linear API key

1. Go to https://linear.app/YOUR-TEAM/settings/api
2. Click "Create API key"
3. Give it a descriptive name (e.g., "Auto Claude")
4. Copy the key (format: `lin_api_xxx...`)

**Step 2:** Configure environment variables

Navigate to the backend directory:

```bash
cd apps/backend
```

Edit `.env` and add your Linear API key:

```bash
# Linear Integration (OPTIONAL)
LINEAR_API_KEY=lin_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Step 3:** (Optional) Pre-configure team and project

If you want Auto Claude to use a specific Linear team/project:

```bash
# Find your team ID in Linear URL: linear.app/team/XXX/...
LINEAR_TEAM_ID=XXX

# Or specify a project ID (will create if not set)
LINEAR_PROJECT_ID=XXX
```

If not set, Auto Claude will auto-detect your team and create a new project during the planner session.

## How It Works

### Planner Session

During the planner session, Auto Claude creates the Linear project and issues:

1. **List Teams**: Agent discovers available Linear teams
   ```
   mcp__linear-server__list_teams
   ```

2. **Create Project**: Creates a new Linear project for the spec
   ```
   mcp__linear-server__create_project(
     team="TEAM-ID",
     name="Feature Name",
     description="Brief summary from spec.md"
   )
   ```

3. **Create Issues**: Creates one issue per subtask
   ```
   mcp__linear-server__create_issue(
     team="TEAM-ID",
     project="PROJECT-ID",
     title="[subtask-1-1] Implement user authentication",
     description="Formatted subtask details with phase context",
     priority=1,  # 1=urgent (early phases) to 4=low (polish)
     labels=["auto-claude", "phase-1", "service-backend"]
   )
   ```

4. **Create META Issue**: Creates a special issue for tracking overall progress
   ```
   mcp__linear-server__create_issue(
     title="[META] Build Progress Tracker",
     description="Session summaries and overall progress tracking"
   )
   ```

### Coder Sessions

During implementation, agents update Linear issues in real-time:

**At session start:**
```
mcp__linear-server__update_issue(id="LIN-123", state="In Progress")
```

**During work:**
```
mcp__linear-server__create_comment(
  issueId="LIN-123",
  body="Refactored the auth service to use OAuth2 flow"
)
```

**On completion:**
```
mcp__linear-server__update_issue(id="LIN-123", state="Done")
```

### QA Sessions

QA agents add validation results as comments:

```
mcp__linear-server__create_comment(
  issueId="LIN-123",
  body="✅ QA PASSED: All acceptance criteria met. Tested login flow."
)
```

### Stuck Subtask Escalation

When a subtask fails repeatedly (3+ attempts):

1. Issue status changes to "Blocked"
2. Adds detailed comment with:
   - Number of failed attempts
   - What was tried each time
   - Error messages
   - Current blocker
3. Labels added: `stuck`, `needs-review`

Example comment:
```markdown
🚨 Subtask Stuck After 3 Attempts

**Attempts:**
1. Tried implementing OAuth2 flow → Error: Invalid redirect URI
2. Fixed redirect URI → Error: Scope not granted
3. Added correct scopes → Error: State parameter mismatch

**Current Blocker:**
State parameter validation failing. OAuth provider requires state param but implementation isn't generating it correctly.

**Recommendation:**
Review OAuth2 RFC 6749 section 4.1.1 for state parameter requirements.
```

## Available Linear MCP Tools

When Linear integration is enabled, agents have access to these MCP tools:

| Tool | Purpose |
|------|---------|
| `mcp__linear-server__list_teams` | List available Linear teams |
| `mcp__linear-server__create_project` | Create a new Linear project |
| `mcp__linear-server__create_issue` | Create issues for subtasks |
| `mcp__linear-server__update_issue` | Update issue status and fields |
| `mcp__linear-server__create_comment` | Add comments to issues |
| `mcp__linear-server__search_issues` | Search for existing issues |

## Troubleshooting

### Issue: Linear integration not working

**Symptoms:** No Linear issues created, no status updates

**Solutions:**

1. Check that `LINEAR_API_KEY` is set in `apps/backend/.env`:
   ```bash
   grep LINEAR_API_KEY apps/backend/.env
   ```

2. Verify the API key is valid:
   - Go to Linear Settings → API
   - Check that the key exists and is active
   - Regenerate if needed

3. Check environment is loaded:
   ```bash
   cd apps/backend
   python -c "import os; print(os.getenv('LINEAR_API_KEY'))"
   ```

### Issue: "Team not found" error

**Symptoms:** Agent can't find or access the specified team

**Solutions:**

1. Verify your team ID:
   - Go to Linear URL: `linear.app/team/XXX/...`
   - Copy the team ID from the URL

2. Check API key permissions:
   - API key must have Member or Admin role
   - Viewer role cannot create projects/issues

3. Don't set `LINEAR_TEAM_ID`:
   - Auto Claude will auto-detect your first available team

### Issue: Issues not created

**Symptoms:** Project created but no subtask issues

**Solutions:**

1. Check that `implementation_plan.json` exists:
   ```bash
   ls .auto-claude/specs/XXX/implementation_plan.json
   ```

2. Verify planner session completed:
   - Check planner logs for Linear operations
   - Look for `.linear_project.json` in spec directory

3. Manually trigger issue creation:
   - Re-run the planner session for the spec
   - Agent will skip existing issues and create missing ones

### Issue: Status not updating

**Symptoms:** Issues created but status never changes

**Solutions:**

1. Check agent session logs for Linear MCP calls
2. Verify agent has MCP tools enabled:
   ```bash
   # In agent session, check available tools
   mcp__linear-server__update_issue should be available
   ```

3. Ensure issue ID mapping exists:
   ```bash
   cat .auto-claude/specs/XXX/.linear_project.json
   ```

### Issue: Comments not appearing

**Symptoms:** Session completes but no comments on issues

**Solutions:**

1. Check agent prompt for Linear instructions
2. Verify `post_session_processing` is running
3. Check for API rate limiting (Linear has rate limits)

## Best Practices

### Project Organization

- **One project per spec**: Each Auto Claude build gets its own Linear project
- **META issue**: Use the META issue as a dashboard for overall progress
- **Labels**: Leverage auto-generated labels for filtering:
  - `auto-claude`: All Auto Claude-created issues
  - `phase-N`: Filter by build phase
  - `service-X`: Filter by service/backend/frontend

### Team Collaboration

- **Visibility**: Share the Linear project URL with your team for transparency
- **Reviews**: Use Linear comments to review agent work before merging
- **Blocked issues**: Monitor `stuck` label to help unblock agents

### Workflow Integration

- **Parallel work**: Auto Claude issues coexist with manual Linear issues
- **Prioritization**: Auto Claude respects Linear priorities (1=urgent for early phases)
- **Transitions**: Use Linear workflows to automate transitions (e.g., Done → Review)

## Configuration Options

| Variable | Required | Description |
|----------|----------|-------------|
| `LINEAR_API_KEY` | Yes | Linear API key from workspace settings |
| `LINEAR_TEAM_ID` | No | Pre-configured team ID (auto-detects if not set) |
| `LINEAR_PROJECT_ID` | No | Pre-configured project ID (creates new if not set) |

## Disable Linear Integration

To disable Linear integration after enabling:

```bash
# Remove or comment out in apps/backend/.env
# LINEAR_API_KEY=lin_api_xxx
```

Auto Claude will continue to work normally with local tracking only.

## See Also

- [GitLab Integration Guide](./INTEGRATION-GITLAB.md) - GitLab issues and merge requests
- [Electron MCP Guide](./INTEGRATION-ELECTRON-MCP.md) - E2E testing for Electron apps
- [CLI Usage Guide](./CLI-USAGE.md) - Terminal-only Auto Claude usage
