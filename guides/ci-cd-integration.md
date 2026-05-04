# CI/CD Pipeline Integration

This guide covers using Auto Code in CI/CD pipelines for autonomous AI-powered builds. It explains how to run headless builds with exit codes, JSON output, artifact generation, and explicit runtime configuration.

> **Documentation status:** This guide has been updated for the current
> multi-runtime model. Older `AUTO_CLAUDE_*` environment variables are
> still shown where the CLI currently supports legacy names, but new examples
> should prefer the `AUTO_CODE_*` runtime controls documented in
> [Provider Runtime Modes](../docs/architecture/provider-runtime-modes.md).

## Overview

Auto Code's CI/CD mode enables fully automated builds without interactive prompts. This is ideal for:

- **Automated PR Reviews** - Run AI agents to validate changes before merge
- **Continuous Integration** - Trigger builds on push/PR with automated testing
- **Scheduled Maintenance** - Run autonomous tasks via cron or scheduled workflows
- **DevOps Automation** - Integrate AI-powered development into your pipeline

**Key Features:**
- **Non-interactive mode** - No prompts, fully automated
- **Standard exit codes** - Build status via exit codes (0, 1, 2, 3)
- **JSON output** - Machine-readable build results
- **Artifact generation** - Build logs, test reports, coverage data
- **Environment-based config** - Configure via environment variables

---

## Quick Start

### Basic CI Mode Usage

```bash
cd apps/backend

# Run in CI mode (non-interactive)
python run.py --spec 001 --ci

# Run with JSON output
python run.py --spec 001 --ci --json

# Using environment variables
export AUTO_CLAUDE_CI=true
export AUTO_CLAUDE_JSON_OUTPUT=true
python run.py --spec 001
```

> **JSON purity note:** When `--json` is used, all machine-readable output goes to
> stdout and all human-readable status messages go to stderr. Ensure your scripts
> capture stdout only (e.g. `python run.py --spec 001 --ci --json 2>/dev/null`).

### Exit Codes

Auto Code uses standard exit codes to indicate build results:

| Exit Code | Status | Description |
|-----------|--------|-------------|
| **0** | Success | Build completed successfully, QA approved |
| **1** | Build Failed | Implementation errors, agent couldn't complete task |
| **2** | QA Failed | Validation rejected, acceptance criteria not met |
| **3** | System Error | Configuration, authentication, or runtime errors |
| **130** | Interrupted | Build was paused or interrupted by the user (SIGINT) |

**GitHub Actions Integration:**
```yaml
- name: Run Auto Code
  working-directory: apps/backend
  run: python run.py --spec 001 --ci
  # Exit codes are automatically handled by GitHub Actions
```

---

## GitHub Actions Workflow

### Example Workflow

A complete GitHub Actions workflow is provided at `.github/workflows/auto-claude-build.yml`. Copy this to your repository and customize as needed.

**Key Features:**
- Manual `workflow_dispatch` trigger with custom inputs (spec number, task description)
- Spec-based and task-based build modes
- Automatic artifact uploads
- PR comments with build results
- Runs on `ubuntu-latest` runner

### Workflow Triggers

```yaml
on:
  # Automatic triggers
  pull_request:
    branches: [main, develop]
    paths:
      - 'apps/**'
      - 'tests/**'
  push:
    branches: [main, develop]

  # Manual trigger
  workflow_dispatch:
    inputs:
      spec_number:
        description: 'Spec number to build (e.g., 001)'
        required: false
        default: '001'
      task_description:
        description: 'Task description (alternative to spec)'
        required: false
        default: ''
```

### Environment Configuration

Configure Auto Code in CI via environment variables:

```yaml
env:
  # Required: Enable CI mode
  AUTO_CLAUDE_CI: 'true'
  AUTO_CLAUDE_JSON_OUTPUT: 'true'

  # Full SDK runtime authentication: Claude OAuth token (NOT ANTHROPIC_API_KEY)
  # Generate with: claude setup-token --print
  CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}

  # Codex CLI runner authentication: preconfigured Codex profile path
  # CODEX_HOME: ${{ github.workspace }}/.codex-ci

  # Optional: Model selection
  # CLAUDE_MODEL: 'claude-sonnet-4-5-20250929'

  # Optional: Graphiti memory
  # GRAPHITI_ENABLED: 'true'
  # GRAPHITI_LLM_PROVIDER: 'openai'
  # OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

**Setup Secrets:**
1. Go to repository **Settings** → **Secrets and variables** → **Actions**
2. Run `claude setup-token --print` locally to obtain your Claude OAuth token
3. Add `CLAUDE_CODE_OAUTH_TOKEN` when using the Claude full SDK runtime.
4. Add `CODEX_HOME` setup when using the Codex CLI runner path.
5. Add optional API keys (`OPENAI_API_KEY`, `LINEAR_API_KEY`, etc.) only for
   integrations, memory, or compatible limited runtime modes.

> **Important:** `ANTHROPIC_API_KEY` is not the main Auto Code runtime auth
> path. Use Claude Code OAuth for the Claude full runtime, Codex CLI account
> auth for the Codex CLI runner, and provider API keys only where the selected
> runtime mode supports them.

### Spec-Based Build

Run builds from an existing spec:

```yaml
- name: Run Auto Code build
  working-directory: apps/backend
  run: |
    source .venv/bin/activate
    python run.py --spec 001 --ci --json
```

### Task-Based Build

Run builds from a task description (creates spec first):

```yaml
- name: Run Auto Code with task
  working-directory: apps/backend
  run: |
    source .venv/bin/activate
    python run.py --task "Fix login bug" --ci --json
```

### Artifact Uploads

Automatically upload build artifacts:

```yaml
- name: Upload build artifacts
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: auto-claude-artifacts
    path: |
      .auto-claude/specs/**/artifacts/
      .auto-claude/specs/**/build-log.json
      .auto-claude/specs/**/test-report.json
      .auto-claude/specs/**/qa-report.md
    retention-days: 30
```

### PR Comments

Post build results as PR comments:

```yaml
- name: Comment PR with results
  if: always() && github.event_name == 'pull_request'
  uses: actions/github-script@v7
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    script: |
      // Read build log
      const buildLog = JSON.parse(fs.readFileSync('.auto-claude/specs/001/artifacts/build-log.json', 'utf8'));

      // Build comment
      let comment = '## 🤖 Auto Code Build Results\n\n';
      comment += `**Status:** ${buildLog.status}\n`;
      comment += `**Exit Code:** ${buildLog.exit_code}\n`;
      comment += `**Duration:** ${buildLog.duration}\n`;

      // Post comment
      await github.rest.issues.createComment({
        owner: context.repo.owner,
        repo: context.repo.repo,
        issue_number: context.issue.number,
        body: comment
      });
```

---

## JSON Output Format

When using `--json` flag or `AUTO_CLAUDE_JSON_OUTPUT=true`, Auto Code outputs machine-readable JSON:

### Build Result Structure

```json
{
  "status": "success",
  "exit_code": 0,
  "spec_id": "001",
  "duration": "15m 32s",
  "timestamp": "2026-02-06T19:30:00Z",
  "metadata": {
    "model": "claude-sonnet-4-5-20250929",
    "complexity": "standard",
    "phases": 6
  },
  "artifacts": {
    "build_log": ".auto-claude/specs/001/artifacts/build-log.json",
    "test_report": ".auto-claude/specs/001/artifacts/test-report.json",
    "qa_report": ".auto-claude/specs/001/qa_report.md"
  },
  "changed_files": [
    "apps/backend/auth.py",
    "apps/frontend/src/components/Login.tsx"
  ],
  "error": null
}
```

### Parsing JSON Output

```bash
# Run and capture JSON output
RESULT=$(python run.py --spec 001 --ci --json)

# Parse with jq
STATUS=$(echo "$RESULT" | jq -r '.status')
EXIT_CODE=$(echo "$RESULT" | jq -r '.exit_code')

# Check status
if [ "$EXIT_CODE" -eq 0 ]; then
  echo "Build succeeded!"
else
  echo "Build failed with code $EXIT_CODE"
fi
```

**Python Example:**
```python
import json
import subprocess

# Run Auto Code
result = subprocess.run(
    ['python', 'run.py', '--spec', '001', '--ci', '--json'],
    capture_output=True,
    text=True
)

# Parse JSON
data = json.loads(result.stdout)

# Check exit code
if result.returncode == 0:
    print(f"Build succeeded: {data['status']}")
else:
    print(f"Build failed: {data.get('error', 'Unknown error')}")
```

---

## Environment Variables

Configure CI mode via environment variables instead of CLI flags:

### Core Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AUTO_CLAUDE_CI` | Enable CI mode (non-interactive) | `false` |
| `AUTO_CLAUDE_JSON_OUTPUT` | Enable JSON output | `false` |
| `CLAUDE_MODEL` | Override model | System default |
| `DEBUG` | Enable debug logging | `false` |

### Usage Examples

```bash
# Enable CI mode via environment
export AUTO_CLAUDE_CI=true
python run.py --spec 001

# Enable both CI and JSON
export AUTO_CLAUDE_CI=true
export AUTO_CLAUDE_JSON_OUTPUT=true
python run.py --spec 001

# Disable interactive prompts
export AUTO_CLAUDE_CI=true
python run.py --qa  # Skips QA approval prompt
```

**GitHub Actions Example:**
```yaml
- name: Run Auto Code
  env:
    AUTO_CLAUDE_CI: 'true'
    AUTO_CLAUDE_JSON_OUTPUT: 'true'
  run: python run.py --spec 001
```

---

## Artifact Generation

Auto Code generates artifacts in CI mode for debugging and reporting.

### Artifact Types

**Build Log** (`build-log.json`)
```json
{
  "status": "success",
  "exit_code": 0,
  "duration": "15m 32s",
  "timestamp": "2026-02-06T19:30:00Z",
  "error_message": null,
  "changed_files": ["apps/backend/auth.py"],
  "metadata": {
    "spec_id": "001",
    "model": "claude-sonnet-4-5-20250929",
    "complexity": "standard"
  }
}
```

**Test Report** (`test-report.json`)
```json
{
  "qa_status": "approved",
  "qa_iterations": 2,
  "issues_found": 3,
  "issues_fixed": 3,
  "tests_generated": 5,
  "duration": "5m 15s",
  "timestamp": "2026-02-06T19:25:00Z"
}
```

**QA Report** (`qa-report.md`)
```markdown
# QA Validation Report

## Status: ✅ APPROVED

## Issues Found
1. Missing error handling in auth.py - FIXED
2. Test coverage insufficient - FIXED
3. Documentation outdated - FIXED

## Acceptance Criteria
- [x] User can login with OAuth
- [x] Existing sessions preserved
- [x] Tests pass
```

### Artifact Location

Artifacts are stored in the spec directory:

```
.auto-claude/specs/001-feature/
├── artifacts/
│   ├── build-log.json
│   └── test-report.json
├── qa_report.md
├── spec.md
└── implementation_plan.json
```

### Accessing Artifacts

**Local:**
```bash
# View build log
cat .auto-claude/specs/001/artifacts/build-log.json

# View test report
cat .auto-claude/specs/001/artifacts/test-report.json

# View QA report
cat .auto-claude/specs/001/qa_report.md
```

**GitHub Actions:**
```yaml
- name: Download artifacts
  uses: actions/download-artifact@v4
  with:
    name: auto-claude-artifacts
    path: ./artifacts
```

---

## Use Cases

### 1. Automated PR Validation

Validate every PR with AI-powered code review:

```yaml
name: PR Validation

on:
  pull_request:
    branches: [main]

jobs:
  auto-code-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Auto Code
        run: |
          cd apps/backend
          uv venv
          source .venv/bin/activate
          uv pip install -r requirements.txt

      - name: Run AI review
        env:
          AUTO_CLAUDE_CI: 'true'
          CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
        run: |
          cd apps/backend
          source .venv/bin/activate
          python run.py --task "Review this PR for bugs and issues" --ci

      - name: Comment results
        if: always()
        uses: actions/github-script@v7
        with:
          script: |
            // Post build results as PR comment
```

### 2. Scheduled Maintenance

Run autonomous maintenance tasks on schedule:

```yaml
name: Nightly Maintenance

on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM daily

jobs:
  maintenance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Update dependencies
        env:
          AUTO_CLAUDE_CI: 'true'
        run: |
          cd apps/backend
          python run.py --task "Update all dependencies and fix breaking changes" --ci

      - name: Run security audit
        env:
          AUTO_CLAUDE_CI: 'true'
        run: |
          cd apps/backend
          python run.py --task "Run security audit and fix vulnerabilities" --ci
```

### 3. Continuous Integration

Run automated builds on every push:

```yaml
name: CI Build

on:
  push:
    branches: [main, develop]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Auto Code
        env:
          AUTO_CLAUDE_CI: 'true'
          AUTO_CLAUDE_JSON_OUTPUT: 'true'
        run: |
          cd apps/backend
          python run.py --spec 001 --ci --json

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: build-results
          path: .auto-claude/specs/**/artifacts/
```

### 4. Multi-Platform Testing

Test across platforms with matrix strategy:

```yaml
name: Multi-Platform Build

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    steps:
      - uses: actions/checkout@v4

      - name: Run Auto Code
        env:
          AUTO_CLAUDE_CI: 'true'
        run: |
          cd apps/backend
          python run.py --spec 001 --ci
```

---

## Troubleshooting

### Build Exits with Code 1 (Build Failed)

**Symptoms:** Exit code 1, no artifacts generated

**Common Causes:**
1. **Agent couldn't complete task** - Task too complex or unclear
2. **File not found** - Specified files don't exist
3. **Permission errors** - Can't write to project directory
4. **Token limit exceeded** - Task too large for context window

**Solutions:**
- Check build log for error details: `cat .auto-claude/specs/001/artifacts/build-log.json`
- Simplify task description or break into smaller specs
- Verify file paths are correct
- Check available disk space and permissions

### Build Exits with Code 2 (QA Failed)

**Symptoms:** Exit code 2, QA report shows rejected status

**Common Causes:**
1. **Acceptance criteria not met** - Agent missed requirements
2. **Tests failing** - Generated tests don't pass
3. **Code quality issues** - QA reviewer found bugs

**Solutions:**
- Review QA report: `cat .auto-claude/specs/001/qa_report.md`
- Check `QA_FIX_REQUEST.md` for specific issues
- Improve spec requirements and acceptance criteria
- Increase QA iteration limit (default: 50)

### Build Exits with Code 3 (System Error)

**Symptoms:** Exit code 3, build log shows system error

**Common Causes:**
1. **Missing runtime authentication** - no Claude OAuth token, Codex profile, or compatible provider key
2. **Network issues** - the selected provider or CLI runner cannot connect
3. **Configuration errors** - Invalid settings in `.env`
4. **Python errors** - Missing dependencies or version conflicts

**Solutions:**
```bash
# Check full-runtime authentication
test -n "$CLAUDE_CODE_OAUTH_TOKEN" && echo "Claude OAuth token configured"
test -n "$CODEX_HOME" && test -d "$CODEX_HOME" && echo "Codex profile directory exists"

# Check configured provider/runtime matrix
python run.py --runtime-modes

# Verify dependencies
cd apps/backend
pip list

# Check configuration
cat apps/backend/.env
```

### JSON Parse Errors

**Symptoms:** Can't parse JSON output

**Common Causes:**
1. **Mixed output** - JSON mixed with console logs
2. **Truncated JSON** - Output too large, got cut off
3. **Invalid JSON** - Malformed JSON structure

**Solutions:**
```bash
# Capture only JSON (filter out logs)
python run.py --spec 001 --ci --json 2>/dev/null

# Use jq to validate
python run.py --spec 001 --ci --json | jq .

# Increase output buffer
export PYTHONUNBUFFERED=1
python run.py --spec 001 --ci --json
```

### Artifacts Not Generated

**Symptoms:** Build succeeds but no artifacts in spec directory

**Common Causes:**
1. **CI mode disabled** - `--ci` flag not set
2. **Wrong spec directory** - Looking in wrong location
3. **Permission errors** - Can't write to artifacts directory

**Solutions:**
```bash
# Verify CI mode is enabled
python run.py --spec 001 --ci --json

# Find artifact location
find .auto-claude/specs -name "build-log.json"

# Check directory permissions
ls -la .auto-claude/specs/001/
```

### Workflow Permissions Errors

**Symptoms:** GitHub Actions fails with permission errors

**Common Causes:**
1. **Missing permissions** - Workflow lacks `pull-requests: write`
2. **Secret not configured** - runtime auth secret is missing
3. **Token expired** - OAuth token needs refresh

**Solutions:**
```yaml
# Add required permissions
permissions:
  contents: read
  actions: read
  pull-requests: write  # Required for PR comments
```

```bash
# Refresh token locally
claude setup-token

# Update GitHub secret
# Go to: Settings -> Secrets -> Actions -> CLAUDE_CODE_OAUTH_TOKEN
```

---

## Best Practices

### 1. Use Environment Variables

Prefer environment variables over CLI flags in CI:

```yaml
# Good
env:
  AUTO_CLAUDE_CI: 'true'
  AUTO_CLAUDE_JSON_OUTPUT: 'true'
run: python run.py --spec 001

# Avoid (harder to maintain)
run: python run.py --spec 001 --ci --json
```

### 2. Always Upload Artifacts

Upload artifacts even when build fails:

```yaml
- name: Upload artifacts
  if: always()  # Upload on success and failure
  uses: actions/upload-artifact@v4
```

### 3. Use Concurrency Control

Prevent duplicate builds on same PR:

```yaml
concurrency:
  group: auto-claude-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true
```

### 4. Set Reasonable Timeouts

Prevent runaway builds:

```yaml
- name: Run Auto Code
  timeout-minutes: 60  # 1 hour max
  run: python run.py --spec 001 --ci
```

### 5. Monitor Exit Codes

Handle different exit codes appropriately:

```yaml
- name: Handle build result
  run: |
    if [ ${{ job.status }} == 'success' ]; then
      echo "✅ Build succeeded"
    else
      echo "❌ Build failed"
      # Check artifacts for details
    fi
```

### 6. Comment PRs with Results

Keep developers informed with PR comments:

```yaml
- name: Comment PR
  if: always() && github.event_name == 'pull_request'
  uses: actions/github-script@v7
  with:
    script: |
      // Build and post comment
```

### 7. Use Matrix for Multi-Platform

Test across platforms:

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python-version: ['3.12', '3.13']
```

---

## Advanced Topics

### Custom Exit Code Handling

Handle exit codes in scripts:

```bash
#!/bin/bash
set -e  # Exit on error

python run.py --spec 001 --ci
EXIT_CODE=$?

case $EXIT_CODE in
  0) echo "✅ Success" ;;
  1) echo "❌ Build failed" ;;
  2) echo "⚠️ QA failed" ;;
  3) echo "🔥 System error" ;;
  *) echo "❓ Unknown exit code: $EXIT_CODE" ;;
esac

exit $EXIT_CODE
```

### Conditional Workflow Steps

Run steps based on build result:

```yaml
- name: Run Auto Code
  id: build
  run: python run.py --spec 001 --ci
  continue-on-error: true

- name: Handle success
  if: steps.build.outcome == 'success'
  run: echo "Build succeeded!"

- name: Handle failure
  if: steps.build.outcome == 'failure'
  run: echo "Build failed, check logs"
```

### Combining with Other CI Tools

Use alongside existing CI tools:

```yaml
jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - run: npm test

  auto-claude-build:
    needs: unit-tests  # Run after tests pass
    runs-on: ubuntu-latest
    steps:
      - run: python run.py --spec 001 --ci

  integration-tests:
    needs: auto-claude-build  # Run after Auto Code
    runs-on: ubuntu-latest
    steps:
      - run: npm run integration-test
```

---

## Related Documentation

- **[CLI-USAGE.md](CLI-USAGE.md)** - Terminal usage and commands
- **[.github/workflows/auto-claude-build.yml](../.github/workflows/auto-claude-build.yml)** - Example workflow
- **[CLAUDE.md](../CLAUDE.md)** - Main project documentation

---

## Summary

Auto Code's CI/CD integration provides:

1. **Non-interactive mode** - Fully automated builds with `--ci` flag
2. **Standard exit codes** - Build status via exit codes (0, 1, 2, 3)
3. **JSON output** - Machine-readable results with `--json` flag
4. **Environment config** - Configure via `AUTO_CLAUDE_CI` and `AUTO_CLAUDE_JSON_OUTPUT`
5. **Artifact generation** - Build logs, test reports, QA reports
6. **GitHub Actions workflow** - Ready-to-use workflow template
7. **Exit code handling** - Proper error handling in CI/CD pipelines

**Quick Start:**
```bash
# Local CI mode
python run.py --spec 001 --ci --json

# GitHub Actions
- run: python run.py --spec 001 --ci
```

For questions or issues, check the troubleshooting section or refer to the main documentation.
