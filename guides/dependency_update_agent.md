# Dependency Update Agent

Automated dependency management for Python and Node.js projects. Detects outdated packages, assesses update risk, batches compatible updates, and generates automated update specs.

## Overview

The Dependency Update Agent helps you maintain project dependencies safely and efficiently:

- **Detects outdated dependencies** for Python (pip/uv) and Node.js (npm) projects
- **CVE vulnerability detection** via pip-audit and npm audit
- **Risk assessment** for each update (breaking changes vs patch updates)
- **Intelligent batching** of compatible updates to minimize breakage
- **Report generation** in JSON and Markdown formats
- **Spec generation** for automated dependency updates via Auto Code

## When to Use

- **Routine maintenance**: Keep dependencies up-to-date with security patches
- **Security audits**: Identify and fix vulnerable dependencies
- **Pre-release checks**: Ensure no known vulnerabilities before deployment
- **Automated updates**: Generate specs for hands-off dependency updates
- **Risk assessment**: Understand which updates are safe vs risky

## Prerequisites

The agent requires the following tools to be installed:

**For Python projects:**
- `pip` (Python package manager) - usually included with Python
- `pip-audit` for security vulnerability scanning:
  ```bash
  pip install pip-audit
  ```
- `uv` (optional, faster alternative to pip):
  ```bash
  pip install uv
  ```

**For Node.js projects:**
- `npm` (Node Package Manager) - included with Node.js

**Auto Code setup:**
- Python 3.12+
- Auto Code backend configured (see [CLI-USAGE.md](CLI-USAGE.md))

## Installation

The Dependency Update Agent is included with Auto Code. No additional installation required.

To verify it's working:

```bash
cd apps/backend
python runners/dependency_update_runner.py --help
```

## Quick Start

### Basic Scan

Scan the current project for outdated dependencies:

```bash
cd apps/backend
python runners/dependency_update_runner.py --project .
```

This will:
1. Scan for outdated Python and Node.js packages
2. Check for security vulnerabilities (CVEs)
3. Classify updates by risk level
4. Generate update batches
5. Create a markdown report at `.auto-claude/dependency-reports/dependency_report.md`

### Dry Run (Recommended First Step)

Test the scanner without generating reports:

```bash
python runners/dependency_update_runner.py --project . --dry-run
```

### Security-Only Scan

Focus only on vulnerable dependencies:

```bash
python runners/dependency_update_runner.py --project . --security-only
```

### Scan Specific Ecosystems

Scan only Python dependencies:

```bash
python runners/dependency_update_runner.py --project . --ecosystems python
```

Scan only Node.js dependencies:

```bash
python runners/dependency_update_runner.py --project . --ecosystems node
```

### JSON Output

Get machine-readable JSON output:

```bash
python runners/dependency_update_runner.py --project . --format json
```

### Both Formats

Generate both JSON and Markdown reports:

```bash
python runners/dependency_update_runner.py --project . --format both
```

## Report Formats

### Markdown Report

The markdown report (`.auto-claude/dependency-reports/dependency_report.md`) includes:

- **Summary**: Total updates, security updates, ecosystems scanned
- **Security Vulnerabilities**: Grouped by severity (critical, high, medium, low)
- **Update Batches**: Recommended batched updates with risk levels
- **All Available Updates**: Detailed table with clickable package links

Example:

```markdown
# Dependency Update Report

**Generated**: 2026-02-12 16:00:00 UTC
**Project**: `/my-project`

## Summary

- **Total Updates Available**: 27
- **Security Updates**: 3
- **Update Batches**: 3
- **Ecosystems Scanned**: python, node

## 🔒 Security Vulnerabilities

Found **3** package(s) with security vulnerabilities:

### 🚨 Critical
- **requests** (python)
  - Current: `2.25.0` → Latest: `2.32.0`
  - CVEs: CVE-2024-12345

### 🟢 Low
- **axios** (node)
  - Current: `0.21.0` → Latest: `1.7.0`
  - CVEs: CVE-2023-45678

## 📦 Recommended Update Batches

### Batch 1: `security-patch-1`
- **Risk Level**: 🟢 Low
- **Priority**: 20
- **Ecosystem**: python
- **Packages**: 3
- **Notes**: Security patch updates, apply immediately
```

### JSON Report

The JSON report (`.auto-claude/dependency-reports/dependency_report.json`) includes structured data for automation:

```json
{
  "updates_available": [
    {
      "name": "requests",
      "current_version": "2.25.0",
      "latest_version": "2.32.0",
      "update_type": "minor",
      "ecosystem": "python",
      "is_security": true,
      "cve_ids": ["CVE-2024-12345"],
      "severity": "critical",
      "changelog_url": "https://pypi.org/project/requests/"
    }
  ],
  "batches": [
    {
      "batch_id": "security-patch-1",
      "update_type": "patch",
      "ecosystem": "python",
      "packages": ["requests", "urllib3", "certifi"],
      "risk_level": "low",
      "is_security_batch": true,
      "priority": 20,
      "notes": "Security patch updates, apply immediately"
    }
  ]
}
```

## Risk Assessment

The agent classifies updates into three risk levels:

### 🟢 Low Risk (Patch Updates)

- **Version change**: `1.2.3` → `1.2.4`
- **Typical impact**: Bug fixes, security patches
- **Breaking changes**: Rare
- **Recommended action**: Update immediately, especially if security-related

**Example:**
```text
requests: 2.32.0 → 2.32.3 (patch) - Low risk
```

### 🟡 Medium Risk (Minor Updates)

- **Version change**: `1.2.3` → `1.3.0`
- **Typical impact**: New features, deprecations
- **Breaking changes**: Possible but uncommon
- **Recommended action**: Review changelog, test before deploying

**Example:**
```text
django: 4.2.0 → 4.3.0 (minor) - Medium risk
```

### 🔴 High Risk (Major Updates)

- **Version change**: `1.2.3` → `2.0.0`
- **Typical impact**: API changes, breaking changes
- **Breaking changes**: Likely
- **Recommended action**: Careful testing, update code as needed

**Example:**
```text
protobuf: 3.20.0 → 4.25.0 (major) - High risk
```

## Update Batching

The agent groups compatible updates together to minimize risk:

### Security Batch

**Highest priority** - Always applied first
- Contains security patches only
- Risk level: Low
- Priority: 20
- Example: `security-patch-python-1`

### Patch Batches

**Low risk** - Safe to apply together
- Contains non-security patch updates
- Risk level: Low
- Priority: 15
- Example: `patch-python-2`

### Minor Batches

**Medium risk** - Grouped by ecosystem
- Contains minor version updates
- Risk level: Medium
- Priority: 10
- Example: `minor-python-3`

### Major Batches

**High risk** - One package per batch
- Each major version gets its own batch
- Risk level: High
- Priority: 5
- Example: `major-python-protobuf-4`

### Batch Recommendation Order

Apply batches in this order for smoothest updates:

1. **Security batches** - Fix critical vulnerabilities first
2. **Patch batches** - Low-risk bug fixes
3. **Minor batches** - Test new features
4. **Major batches** - Careful testing and code updates

## Automated Update Specs

The agent can generate Auto Code specs for automated dependency updates:

### Generate Update Spec

Create a spec for all available updates:

```bash
python runners/dependency_update_runner.py --project . --generate-spec
```

This will:
1. Run dependency scan
2. Generate update batches
3. Create an Auto Code spec at `.auto-claude/specs/XXX-dependency-updates/`
4. Provide instructions to start the automated update

### Generate Security-Only Spec

Create a spec for only security updates:

```bash
python runners/dependency_update_runner.py --project . --generate-spec --security-only
```

### Generate Spec for Specific Batch

Create a spec for a specific batch:

```bash
python runners/dependency_update_runner.py --project . --generate-spec --batch patch-python-2
```

### Run the Generated Spec

After generating a spec, run it with:

```bash
python run.py --spec XXX-dependency-updates
```

The Auto Code agent will:
- Update the specified dependencies
- Run the test suite to verify no regressions
- Rollback if tests fail
- Document changes in the spec

## Command Reference

### Basic Options

```text
--project PATH          Project directory to scan (default: current directory)
--output PATH          Output directory for reports
                        (default: project/.auto-claude/dependency-reports)
```

### Scan Options

```text
--ecosystems python,node
                       Comma-separated list of ecosystems to scan
                       (default: all ecosystems)
--security-only        Only report dependencies with security vulnerabilities
--skip-dev             Skip development dependencies
```

### Output Options

```text
--format json|markdown|both
                       Output format for reports (default: markdown)
--dry-run              Run scan without saving reports
```

### Spec Generation

```text
--generate-spec        Generate spec file for automated dependency updates
--batch ID             Generate spec for specific batch ID
```

### Advanced Options

```text
--model haiku|sonnet|opus
                       Model to use for AI analysis (default: sonnet)
--thinking-level none|low|medium|high|ultrathink
                       Thinking level for extended reasoning (default: medium)
```

## Examples

### Example 1: Weekly Security Scan

Check for security vulnerabilities weekly:

```bash
cd apps/backend
python runners/dependency_update_runner.py \
  --project /path/to/project \
  --security-only \
  --format markdown
```

Review the report and address critical vulnerabilities immediately.

### Example 2: Pre-Release Check

Before releasing, ensure no known vulnerabilities:

```bash
python runners/dependency_update_runner.py \
  --project . \
  --format both \
  --dry-run
```

### Example 3: Automated Patch Updates

Generate spec for low-risk patch updates:

```bash
python runners/dependency_update_runner.py \
  --project . \
  --generate-spec
```

Then review and run the spec:

```bash
python run.py --spec XXX-dependency-updates
```

### Example 4: Major Version Upgrade Planning

Generate markdown report to plan major upgrades:

```bash
python runners/dependency_update_runner.py \
  --project . \
  --format markdown
```

Review the major version batches and plan migration strategy.

### Example 5: CI/CD Integration

Add to CI/CD pipeline to fail on critical vulnerabilities:

```bash
# Exit with error if critical vulnerabilities found
python runners/dependency_update_runner.py \
  --project . \
  --security-only \
  --format json \
  --dry-run

# Parse JSON for critical severity
# Exit 1 if any critical CVEs found
```

## Best Practices

### 1. Regular Scanning

Scan dependencies regularly (at least monthly):

```bash
# Add to cron or scheduled task
python runners/dependency_update_runner.py --project . --format markdown
```

### 2. Security First

Always address security updates first:

```bash
# Check security updates daily
python runners/dependency_update_runner.py --project . --security-only
```

### 3. Test Before Deploying

For non-security updates:

1. Generate spec: `--generate-spec`
2. Review the spec changes
3. Run in isolated worktree (Auto Code default)
4. Test thoroughly
5. Merge after verification

### 4. Batch Similar Updates

Let the agent batch compatible updates:

- Apply patch batches together (low risk)
- Test minor batches before merging
- Update major versions one at a time

### 5. Keep Documentation Updated

After updating dependencies:

- Update documentation if APIs changed
- Add migration notes for major versions
- Communicate breaking changes to team

### 6. Monitor for Regressions

After automated updates:

- Run full test suite
- Check for deprecation warnings
- Monitor production for issues
- Have rollback plan ready

## Troubleshooting

### "pip not found"

**Problem:** Python package manager not installed or not in PATH.

**Solution:**
- Ensure Python is installed: `python --version`
- Reinstall Python with "Add to PATH" option
- Or use full path: `C:\Python312\Scripts\pip.exe`

### "pip-audit not found"

**Problem:** Security scanner not installed.

**Solution:**
```bash
pip install pip-audit
```

### "npm not found"

**Problem:** Node.js not installed or not in PATH.

**Solution:**
- Install Node.js from https://nodejs.org/
- Restart terminal after installation
- Verify: `npm --version`

### Permission Errors

**Problem:** Cannot install packages due to permissions.

**Solution:**
```bash
# Use user install
pip install --user pip-audit

# Or use virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

### Network Errors

**Problem:** Cannot fetch package information.

**Solution:**
- Check internet connection
- Configure proxy if behind corporate firewall
- Use mirror: `pip install --index-url https://pypi.org/simple`

### Scan Returns No Updates

**Problem:** All dependencies are up-to-date.

**Solution:** This is expected! All dependencies are current.

### JSON Parsing Errors

**Problem:** Package manager output format changed.

**Solution:**
- Update the package manager: `pip install --upgrade pip`
- Report the issue at https://github.com/OBenner/Auto-Coding/issues

## Integration with Auto Code Workflow

The Dependency Update Agent integrates seamlessly with Auto Code's spec-based workflow:

### Step 1: Scan Dependencies

```bash
python runners/dependency_update_runner.py --project . --format both
```

### Step 2: Review Report

Open `.auto-claude/dependency-reports/dependency_report.md` and review:
- Security vulnerabilities (address first)
- Update batches and risk levels
- Packages requiring code changes

### Step 3: Generate Spec (Optional)

For automated updates:

```bash
python runners/dependency_update_runner.py \
  --project . \
  --generate-spec \
  --security-only
```

### Step 4: Run Automated Update

```bash
python run.py --spec XXX-dependency-updates
```

The agent will:
- Create isolated worktree (safe from main branch)
- Update dependencies
- Run tests
- Rollback on failure
- Wait for your review

### Step 5: Merge or Discard

After successful update:

```bash
# Review changes in worktree
cd .worktrees/auto-code/XXX-dependency-updates
git diff

# Merge to main if satisfied
cd apps/backend
python run.py --spec XXX-dependency-updates --merge

# Or discard if issues found
python run.py --spec XXX-dependency-updates --discard
```

## GitHub Actions Automation

The Dependency Update Agent includes a GitHub Actions workflow for automated dependency scanning and vulnerability monitoring. This enables continuous security monitoring without manual intervention.

### Workflow Features

- **Scheduled scans**: Runs weekly on Mondays at midnight UTC
- **Manual trigger**: Run on-demand with custom parameters via GitHub UI
- **Security notifications**: Automatically creates GitHub issues for critical/high vulnerabilities
- **Artifact uploads**: Stores scan reports for 30 days
- **Workflow failure**: Fails when critical/high vulnerabilities are detected
- **Customizable options**: Security-only scans, ecosystem filtering, PR creation

### Enable the Workflow

The workflow file is located at `.github/workflows/dependency-updates.yml`.

**Step 1: Verify the workflow exists**

```bash
ls .github/workflows/dependency-updates.yml
```

**Step 2: Grant required permissions**

The workflow is pre-configured with the necessary permissions:
- `contents: read` - Read repository contents
- `actions: read` - Read workflow runs
- `pull-requests: write` - Create pull requests (if using `--create-pr`)
- `issues: write` - Create issues for vulnerabilities

**Step 3: Customize scheduling (optional)**

Edit the workflow file to change the default schedule:

```yaml
schedule:
  - cron: '0 0 * * 1'  # Weekly on Monday at midnight UTC
  # Or daily: '0 0 * * *'
  # Or monthly: '0 0 1 * *'
```

**Step 4: Enable GitHub Actions**

Navigate to **Settings** → **Actions** → **General** in your repository and ensure "Allow all actions and reusable workflows" is selected.

### Manual Workflow Trigger

Run the dependency scan on-demand from the GitHub Actions UI:

1. Navigate to **Actions** tab in your repository
2. Select **"Dependency Updates"** workflow
3. Click **"Run workflow"** button
4. Configure options:
   - **Security only**: Scan for vulnerabilities only (default: false)
   - **Ecosystems**: Comma-separated list (default: "python,node")
   - **Create pull request**: Generate PR with updates (default: false)
   - **Notify**: Create issues for critical vulnerabilities (default: true)
5. Click **"Run workflow"**

### Workflow Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `security-only` | Boolean | `false` | Scan only for security vulnerabilities |
| `ecosystems` | String | `python,node` | Comma-separated ecosystems to scan |
| `create-pr` | Boolean | `false` | Create pull request with dependency updates |
| `notify` | Boolean | `true` | Create GitHub issues for critical/high vulnerabilities |

### Workflow Outputs

The workflow generates several outputs:

**1. Scan Artifacts**

Full scan reports are uploaded as artifacts (retained for 30 days):
- `dependency_report.json` - Machine-readable JSON report
- `dependency_report.md` - Human-readable markdown report

**2. GitHub Actions Summary**

The workflow generates a summary with:
- Total update count
- Security vulnerability count
- Scanned ecosystems
- Severity breakdown (critical, high, medium, low)

**3. GitHub Issues (if enabled)**

For critical/high severity vulnerabilities:
- Issue title: `[Security] <package-name> <severity> vulnerability`
- Issue body includes:
  - CVE IDs and severity
  - Current and latest versions
  - Affected ecosystems
  - Recommended action

**4. Workflow Status**

- ✅ **Success**: No critical/high vulnerabilities found
- ❌ **Failed**: Critical/high vulnerabilities detected (requires attention)

### Example Workflow Runs

**Scheduled Weekly Scan**

Runs automatically every Monday at midnight UTC:

```yaml
schedule:
  - cron: '0 0 * * 1'
```

The workflow will:
1. Scan all Python and Node.js dependencies
2. Generate reports and upload as artifacts
3. Create GitHub issues for critical/high vulnerabilities
4. Fail the workflow if critical/high vulnerabilities found

**Manual Security-Only Scan**

Trigger manually with "Security only" enabled:

- Scans only for security vulnerabilities
- Creates issues for critical/high severity CVEs
- Skips non-security updates
- Fails if critical/high vulnerabilities found

**Manual Full Scan with PR**

Trigger manually with "Create pull request" enabled:

- Scans all dependencies
- Generates Auto Code spec for updates
- Creates pull request with dependency updates
- Runs tests in isolated worktree
- Merges only if tests pass

### Customizing the Workflow

You can customize the workflow by editing `.github/workflows/dependency-updates.yml`:

**Change scan frequency:**

```yaml
schedule:
  - cron: '0 0 * * 0'  # Weekly on Sunday
  # Or daily at 9am UTC: '0 9 * * *'
  # Or every 6 hours: '0 */6 * * *'
```

**Add path filters:**

```yaml
on:
  schedule:
    - cron: '0 0 * * 1'
  pull_request:
    paths:
      - 'requirements.txt'
      - 'package.json'
      - 'pyproject.toml'
```

**Customize notification thresholds:**

```python
# In the workflow file, modify the min_severity parameter
min_severity='critical'  # Only notify on critical
# or
min_severity='medium'     # Notify on medium and above
```

**Change artifact retention:**

```yaml
- name: Upload scan reports
  uses: actions/upload-artifact@v4
  with:
    name: dependency-reports
    path: .auto-claude/dependency-reports/
    retention-days: 90  # Increase from 30 to 90 days
```

### Viewing Results

**From GitHub Actions:**

1. Navigate to **Actions** tab
2. Select **"Dependency Updates"** workflow run
3. View summary in the run page
4. Download artifacts for detailed reports

**From GitHub Issues:**

1. Navigate to **Issues** tab
2. Filter by label: `security`, `critical`, `high`
3. Review vulnerability details and recommended actions

**From Artifacts:**

1. In workflow run, scroll to **Artifacts** section
2. Download `dependency-reports` artifact
3. Extract and view `dependency_report.md` or `dependency_report.json`

### Integration with CI/CD Pipeline

You can integrate dependency scanning into your existing CI/CD pipeline:

**Before deployment:**

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - name: Run tests
        run: npm test

  dependency-check:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v6
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Run dependency scan
        working-directory: apps/backend
        run: |
          pip install -r requirements.txt
          python runners/dependency_update_runner.py \
            --project . \
            --security-only \
            --dry-run \
            --format json
      # Fail deployment if critical vulnerabilities found
      - name: Check for vulnerabilities
        run: |
          if grep -q '"severity": "critical"' .auto-claude/dependency-reports/dependency_report.json; then
            echo "Critical vulnerabilities found!"
            exit 1
          fi
```

**Pull request validation:**

```yaml
name: PR Validation

on:
  pull_request:
    branches: [main, develop]

jobs:
  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Run dependency scan
        working-directory: apps/backend
        run: |
          python runners/dependency_update_runner.py \
            --project . \
            --format json \
            --dry-run
      - name: Comment on PR
        uses: actions/github-script@v8
        with:
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs.readFileSync('.auto-claude/dependency-reports/dependency_report.json', 'utf8'));
            const security = report.security_updates || [];
            if (security.length > 0) {
              github.rest.issues.createComment({
                issue_number: context.issue.number,
                owner: context.repo.owner,
                repo: context.repo.repo,
                body: `⚠️ Found ${security.length} security vulnerabilities. See workflow logs for details.`
              });
            }
```

### Best Practices

**1. Run scheduled scans weekly**

Weekly scans balance staying current with avoiding alert fatigue:

```yaml
schedule:
  - cron: '0 0 * * 1'  # Every Monday
```

**2. Enable notifications for critical/high**

Always create issues for critical and high severity vulnerabilities:

```yaml
# In workflow_dispatch inputs
notify:
  description: 'Create GitHub issues for critical vulnerabilities'
  default: true
```

**3. Review and triage issues weekly**

Assign someone to review and address security issues weekly:

- Critical: Fix within 24 hours
- High: Fix within 1 week
- Medium: Fix within 1 month
- Low: Fix in next update cycle

**4. Keep artifacts for audit trail**

Increase retention if you need historical data:

```yaml
retention-days: 90  # Or 365 for long-term tracking
```

**5. Use security-only in CI/CD**

In CI/CD pipelines, use `--security-only` to avoid noise:

```bash
python runners/dependency_update_runner.py \
  --project . \
  --security-only \
  --dry-run
```

### Troubleshooting GitHub Actions

**Workflow not running on schedule:**

- Check if GitHub Actions is enabled in repository settings
- Verify the cron expression is valid
- Check the workflow file is in the correct location: `.github/workflows/dependency-updates.yml`
- Review Actions tab for recent workflow runs and error messages

**Permissions errors:**

- Verify the workflow has the required permissions:
  ```yaml
  permissions:
    contents: read
    actions: read
    pull-requests: write
    issues: write
  ```
- Check repository settings → Actions → General → Workflow permissions

**Scan fails in CI but works locally:**

- Ensure all dependencies are installed in the workflow
- Check that `PYTHONPATH` is set correctly
- Verify the runner has access to the project directory
- Review workflow logs for specific error messages

**Issues not being created:**

- Verify `issues: write` permission is granted
- Check if `notify` parameter is set to `true`
- Ensure vulnerabilities meet severity threshold (critical/high)
- Review workflow logs for notification errors

**Artifacts not uploading:**

- Check that the report directory exists: `.auto-claude/dependency-reports/`
- Verify the scan completed successfully
- Check artifact retention period (default: 30 days)
- Ensure sufficient storage quota in GitHub

## Comparison with Manual Updates

| Manual Updates | Dependency Update Agent |
|----------------|-------------------------|
| `pip list --outdated` (Python only) | Scans both Python and Node.js |
| No CVE detection | Automatic security vulnerability scanning |
| No risk assessment | Semver-based risk classification |
| Update one-by-one | Intelligent batching of compatible updates |
| Manual changelog research | Clickable links to package repositories |
| Manual testing | Automated spec generation with test verification |
| No rollback plan | Auto Code worktree isolation (safe rollback) |

## FAQ

### Q: Does the agent automatically update dependencies?

**A:** No. The agent only scans and reports. To automate updates, use `--generate-spec` to create an Auto Code spec, then run the spec. This keeps you in control.

### Q: How often should I scan dependencies?

**A:**
- **Security scans**: Weekly or daily for critical projects
- **Full scans**: Monthly or before each release
- **CI/CD**: On every pull request or build

### Q: What if the scan misses an update?

**A:** The agent uses `pip list --outdated` and `npm outdated`, which report the latest versions. If a version isn't showing:
- Check if it's a pre-release: `pip list --outdated --include-pre`
- Verify the package exists: `pip show package-name`

### Q: Can I scan projects without requirements.txt?

**A:** The agent detects:
- **Python**: `requirements.txt`, `pyproject.toml`, `setup.py`
- **Node.js**: `package.json`

If none found, the scan will skip that ecosystem.

### Q: How does the agent determine risk levels?

**A:** Based on Semantic Versioning (SemVer):
- **Patch** (1.2.3 → 1.2.4): Low risk (bug fixes)
- **Minor** (1.2.3 → 1.3.0): Medium risk (new features)
- **Major** (1.2.3 → 2.0.0): High risk (breaking changes)

### Q: Can I customize batch priorities?

**A:** Not currently. Batches are auto-generated based on risk levels and security status. Feature request welcome!

### Q: What happens if an automated update fails?

**A:** Auto Code will:
1. Stop the update process
2. Keep the worktree isolated (your main branch is safe)
3. Report the failure
4. You can review and retry or discard

### Q: Does this work with monorepos?

**A:** Yes! Scan each subproject separately:
```bash
python runners/dependency_update_runner.py --project packages/frontend
python runners/dependency_update_runner.py --project packages/backend
```

## Further Reading

- [CLI-USAGE.md](CLI-USAGE.md) - General Auto Code CLI usage
- [SPEC-CREATION-PIPELINE.md](SPEC-CREATION-PIPELINE.md) - How spec creation works
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions

## Support

For issues, feature requests, or questions:
- GitHub: https://github.com/OBenner/Auto-Coding/issues
- Documentation: https://github.com/OBenner/Auto-Coding

## Changelog

### v1.0.0 (2026-02-12)
- Initial release
- Python (pip/uv) and Node.js (npm) support
- CVE vulnerability detection
- Risk assessment and batching
- JSON and Markdown reports
- Spec generation for automated updates
