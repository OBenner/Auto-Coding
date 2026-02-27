# GitHub/GitLab Integration

**Documentation Date:** 2026-02-12

## Pattern Overview

**Overall:** AI-Powered GitHub Automation with Multi-Stage Workflows

**Key Characteristics:**
- AI-powered PR reviews with multi-pass analysis
- Issue triage with duplicate/spam detection and confidence scoring
- Auto-fix workflow: Issues → Specs → PRs automatically
- Issue batching: Groups similar issues into combined specs
- Bot detection: Prevents infinite loops when reviewing bot-authored PRs
- Permission-based authorization: Auto-fix only triggers for authorized users
- Rate limiting: Respectful GitHub API usage with adaptive throttling
- Follow-up reviews: Rebase-resistant tracking via file blob SHAs

---

## Architecture

The GitHub integration uses a **service-oriented architecture** where the orchestrator delegates to specialized services:

```
┌─────────────────────────────────────────────────────────────┐
│              GitHub Orchestrator                         │
│      (runners/github/orchestrator.py)                   │
│  Coordinates all GitHub automation workflows                  │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ PR Review    │  │   Issue      │  │  Auto-Fix    │
│ Engine      │  │  Triage      │  │  Processor    │
│             │  │  Engine      │  │              │
│ Multi-pass  │  │              │  │ Spec → Build │
│ code review │  │ Duplicate    │  │ → PR         │
└──────────────┘  │ detection   │  └──────────────┘
                 │             │
                 └──────────────┘
                          │
                          ▼
                 ┌──────────────┐
                 │  Batch      │
                 │  Processor  │
                 │             │
                 │ Cluster     │
                 │ similar     │
                 │ issues     │
                 └──────────────┘
```

### Core Services

**Service Layer:** `apps/backend/runners/github/services/`

| Service | Location | Purpose |
|----------|------------|---------|
| **PRReviewEngine** | `pr_review_engine.py` | Multi-pass code review with parallel analysis |
| **TriageEngine** | `triage_engine.py` | Issue classification, duplicate/spam detection |
| **AutoFixProcessor** | `autofix_processor.py` | Issue → Spec → Build → PR workflow |
| **BatchProcessor** | `batch_processor.py` | Issue clustering and batch spec creation |
| **GHClient** | `../gh_client.py` | GitHub API client with rate limiting |
| **BotDetector** | `../bot_detection.py` | Prevents infinite review loops |
| **Permissions** | `../permissions.py` | Authorization for auto-fix triggers |

---

## PR Review Workflow

### Overview

AI-powered pull request review with multi-pass analysis:

**Features:**
- Multi-pass review: Quick scan → Deep analysis → AI comment triage
- Parallel analysis: Reviews multiple files concurrently
- CI status checks: Comprehensive CI workflow validation (including fork approval waiting)
- Merge verdict: Ready to merge / Needs revision / Blocked
- Follow-up reviews: Incremental reviews for updated PRs
- Rebase resistance: File blob SHA tracking survives rebases

### Review Passes

**Pass 1: Quick Scan**
- Identifies critical security issues
- Detects merge conflicts
- Checks CI status
- Flags verification failures (claims without evidence)

**Pass 2: Deep Analysis**
- Comprehensive code review (all files)
- Categorized findings: Security, Performance, bugs, Redundancy, Verification
- Severity levels: Critical, High, Medium, Low
- Structural issue detection: Feature creep, scope creep

**Pass 3: AI Tool Comment Triage**
- Reviews AI-generated comments (Copilot, etc.)
- Categories: Critical, Important, Trivial
- Responds to valid issues, dismisses trivial ones

### Merge Verdicts

| Verdict | Condition | Meaning |
|---------|-----------|---------|
| **READY_TO_MERGE** | No blockers, only low-severity findings | Safe to merge |
| **MERGE_WITH_CHANGES** | Minor suggestions, no blocking issues | Can merge, address suggestions later |
| **NEEDS_REVISION** | High/medium severity findings or branch behind | Fix before merging |
| **BLOCKED** | CI failures, merge conflicts, critical issues | Must fix before merge |

### Review Workflow

```
GitHub PR webhook/trigger
    ↓
[Context Gathering]
    → Fetch PR data (title, author, commits, files)
    → Get diff (all changes)
    → Fetch related files (codebase context)
    → Check CI status (comprehensive checks including fork workflows)
    ↓
[Bot Detection Check]
    → Is PR authored by bot? → Skip
    → Already reviewed this commit? → Skip
    → In cooling-off period? → Skip
    ↓
[Multi-Pass Review]
    → Pass 1: Quick scan (critical issues only)
    → Pass 2: Full analysis (all categories)
    → Pass 3: AI comment triage
    ↓
[Verdict Generation]
    → Check CI failures (blocker)
    → Check merge conflicts (blocker)
    → Count findings by severity
    → Generate verdict (READY/NEEDS_REVISION/BLOCKED)
    ↓
[Post Review]
    → Save result to .auto-claude/github/reviews/
    → Optionally post to GitHub (--auto-post)
    → Post AI triage replies
    ↓
[Memory Integration]
    → Save learnings to Graphiti (patterns, gotchas)
```

### Follow-Up Reviews

**Purpose:** Re-review PRs after author makes changes

**Rebase-Resistant Tracking:**
```python
# Track file blob SHAs (persist across rebases)
file_blobs = {
    "src/auth.py": "sha123abc...",
    "tests/test_auth.py": "sha456def..."
}

# After rebase/force-push:
# - Commits have new SHAs (commit history rewritten)
# - But file blobs with same content have SAME SHAs
# → Detect which files actually changed
```

**Follow-Up Workflow:**
```
Previous review exists for PR #123
    ↓
[Detect Changes]
    → Check new commits since last review
    → Compare file blob SHAs (rebase-resistant!)
    → Check for new comments
    ↓
[No Changes]
    → Check if CI status improved (e.g., failing → passing)
    → Update verdict if CI recovered
    → Return existing review
    ↓
[Has Changes]
    → Review only changed files (incremental)
    → Check if previous findings are resolved
    → Detect new issues in changed code
    ↓
[Generate Follow-Up Report]
    → Resolved findings (from previous review)
    → Unresolved findings (still present)
    → New findings (introduced in changes)
    → Updated verdict
```

### Bot Detection

**Purpose:** Prevent infinite loops when reviewing bot-authored PRs

**Checks:**
1. **Bot authors:** Skip PRs from bot accounts (e.g., dependabot, renovate)
2. **Already reviewed:** Don't re-review same commit SHA
3. **Cooling-off:** Skip PRs recently reviewed (within 1 hour)
4. **Self-review:** Optionally skip reviewing own PRs (configurable)

**State Storage:** `.auto-claude/github/bot_detection.json`

```python
{
    "reviewed_prs": {
        "123": {
            "commit_sha": "abc123...",
            "timestamp": "2026-02-12T10:30:00Z"
        }
    },
    "cooling_off_until": "2026-02-12T11:30:00Z"
}
```

---

## Issue Triage Workflow

### Overview

AI-powered issue classification with duplicate and spam detection:

**Features:**
- **Category classification:** Bug, feature, documentation, performance, security
- **Duplicate detection:** Semantic similarity to find duplicate issues
- **Spam detection:** Identify low-quality or spam issues
- **Feature creep detection:** Flag issues that expand scope
- **Confidence scoring:** 0-100% confidence in classification
- **Label suggestions:** Auto-suggest labels based on analysis

### Triage Categories

| Category | Description | Typical Labels |
|-----------|-------------|----------------|
| **bug** | Error, unexpected behavior | `bug`, `needs-triage` |
| **feature** | New functionality request | `enhancement`, `feature-request` |
| **documentation** | Docs improvement | `documentation` |
| **performance** | Performance issue | `performance` |
| **security** | Security vulnerability | `security`, `critical` |
| **question** | User question | `question`, `needs-info` |
| **spam** | Low quality, irrelevant | `spam`, `invalid` |
| **duplicate** | Already reported | `duplicate` |
| **feature-creep** | Expanding scope | `feature-creep`, `too-broad` |

### Duplicate Detection

**Method:** Semantic similarity using embeddings

```python
# For each new issue:
similarity_scores = []

for existing_issue in all_issues:
    # Compare embeddings
    similarity = cosine_similarity(
        new_issue.embedding,
        existing_issue.embedding
    )

    if similarity > SIMILAR_THRESHOLD:  # 0.85
        similarity_scores.append({
            "issue_number": existing_issue.number,
            "similarity": similarity,
            "title": existing_issue.title
        })

# Flag as duplicate if high similarity found
if similarity_scores:
    is_duplicate = True
    duplicate_of = max(similarity_scores, key=lambda x: x["similarity"])
```

### Triage Workflow

```
Fetch all open issues (or specific issues)
    ↓
[For Each Issue]
    ↓
[Generate Embedding]
    → Embed issue title + body
    → Store for duplicate detection
    ↓
[Check for Duplicates]
    → Compare with all other issues
    → Flag if similarity > 85%
    → Find most similar existing issue
    ↓
[Classify Category]
    → AI analyzes issue content
    → Assigns category (bug/feature/etc)
    → Confidence score (0-100%)
    ↓
[Detect Spam]
    → AI checks for low-quality signals
    → Short/vague title
    → No useful information
    → Test/placeholder content
    ↓
[Detect Feature Creep]
    → AI checks for scope expansion
    → Multiple unrelated features
    → Vague "do everything" requests
    ↓
[Generate Labels]
    → Suggest labels based on analysis
    → Include category, priority, area labels
    ↓
[Save Results]
    → Store triage result
    → Optionally apply to GitHub (--apply-labels)
```

---

## Auto-Fix Workflow

### Overview

Automatically fix issues by creating specs and running the build pipeline:

**Features:**
- **Trigger-based:** Auto-fix triggers when authorized user adds label
- **Permission checking:** Only authorized roles can trigger auto-fix
- **Full pipeline:** Issue → Spec → Implementation → QA → PR
- **State tracking:** Track progress through all stages
- **Error recovery:** Handle build failures and retries

### Auto-Fix States

| State | Description |
|-------|-------------|
| **pending** | Issue queued, not yet analyzed |
| **analyzing** | AI is analyzing issue for requirements |
| **creating_spec** | Spec agent is creating specification |
| **building** | Build pipeline is implementing feature |
| **qa_review** | QA agent is validating implementation |
| **pr_created** | PR created, awaiting review |
| **completed** | PR merged, issue closed |
| **failed** | Error occurred, manual intervention needed |

### Authorization

**Permission Model:** Role-based access control

```python
# Configuration
AUTO_FIX_ALLOWED_ROLES = ["admin", "maintainer", "triager"]
AUTO_FIX_LABELS = ["auto-fix", "autofix"]

# Permission check
permission_checker = GitHubPermissionChecker(
    gh_client=gh_client,
    repo="owner/repo",
    allowed_roles=ALLOWED_ROLES,
    allow_external_contributors=False  # Require org members
)

# When label added:
user_authorized = await permission_checker.can_user_trigger_autofix(
    username=label_added_by,
    trigger_label="auto-fix"
)
```

**Roles:**
- **admin:** Repository admin (full access)
- **maintainer:** Write access + triage role
- **triager:** Triage team (can trigger auto-fix)
- **external:** Outside collaborators (blocked by default)

### Auto-Fix Workflow

```
[Trigger: Label Added]
    ↓
[Permission Check]
    → Who added the label?
    → Is user in allowed roles?
    → If not authorized: Remove label, post comment
    ↓
[Issue Analysis]
    → Read issue title and body
    → Extract requirements
    → Identify affected components
    ↓
[Spec Creation]
    → Call spec_runner.py with issue content
    → Interactive agent gathers requirements (non-interactive mode)
    → Generate spec.md with acceptance criteria
    ↓
[Implementation]
    → Call run.py with spec
    → Planner breaks into subtasks
    → Coder implements features
    → QA validates acceptance criteria
    ↓
[PR Creation]
    → Create PR from implementation branch
    → Link PR to issue
    → Post comment with status
    ↓
[Completion]
    → Mark state as "completed"
    → Remove auto-fix label
    → Add "completed" label
    ↓
[Error Handler]
    → If any stage fails: state = "failed"
    → Post error comment to issue
    → Remove auto-fix label
```

### State Tracking

**Storage:** `.auto-claude/github/autofix/queue.json`

```python
[
    {
        "issue_number": 456,
        "status": "building",
        "spec_id": "001-fix-login-bug",
        "pr_number": 123,
        "triggered_by": "maintainer-user",
        "triggered_at": "2026-02-12T10:00:00Z",
        "error": null
    }
]
```

---

## Issue Batching Workflow

### Overview

Group similar issues together and create combined specs:

**Features:**
- **Semantic clustering:** Group issues by similarity
- **Batch validation:** Human review before execution
- **Proactive workflow:** Preview batches without executing
- **Theme extraction:** AI identifies common theme
- **Confidence scoring:** Trust score for batch quality

### Batching Strategies

**1. Similarity-Based Batching (Default)**

```python
# Calculate pairwise similarities
for issue_a, issue_b in all_issues:
    similarity = cosine_similarity(
        issue_a.embedding,
        issue_b.embedding
    )

    if similarity > CLUSTER_THRESHOLD:  # 0.75
        add_to_cluster(issue_a, issue_b)
```

**2. Claude-Based Intelligent Batching**

```python
# Single Claude call analyzes all issues
analyzer = ClaudeBatchAnalyzer(project_dir)

batches = await analyzer.analyze_and_batch_issues(
    issues=all_issues,
    max_batch_size=5
)

# Claude returns:
# [
#     {
#         "issue_numbers": [123, 124, 125],
#         "theme": "Fix authentication token handling",
#         "reasoning": "All issues relate to JWT token expiry",
#         "confidence": 0.92
#     },
#     ...
# ]
```

### Batch Validation

**Purpose:** Human review before execution

**Workflow:**
```bash
# Step 1: Preview proposed batches
python runner.py analyze-preview --json > proposed_batches.json

# Step 2: Human reviews JSON
cat proposed_batches.json
# → Remove bad batches
# → Adjust issue groupings
# → Add manual notes

# Step 3: Execute approved batches
python runner.py approve-batches proposed_batches.json
```

### Batch Workflow

```
[Fetch Open Issues]
    ↓
[Generate Embeddings]
    → Embed all issue titles + bodies
    → Store for clustering
    ↓
[Cluster Issues]
    → Calculate pairwise similarities
    → Group issues above threshold (75%)
    → Limit batch size (max 5 issues)
    ↓
[Generate Batch Themes]
    → AI analyzes each cluster
    → Extracts common theme/pattern
    → Generates combined description
    ↓
[Validation (Proactive Mode)]
    → Output proposed batches as JSON
    → Human reviews and approves
    → Execute only approved batches
    ↓
[Create Batch Specs]
    → For each batch:
        → Create combined spec.md
        → Include all issues in scope
        → Generate unified acceptance criteria
    ↓
[Execute Build Pipeline]
    → Run implementation for each batch spec
    → Create PRs
    → Link to all issues in batch
```

### Batch Status

**Storage:** `.auto-claude/github/batches/`

```json
{
    "batch_001": {
        "batch_id": "batch_001",
        "theme": "Fix authentication token handling",
        "status": "completed",
        "issues": [123, 124, 125],
        "spec_id": "batch-auth-tokens",
        "pr_number": 456
    }
}
```

---

## Rate Limiting

### Overview

Respectful GitHub API usage with adaptive throttling:

**Features:**
- **Token-aware:** Uses authenticated rate limits (5000/hour)
- **Adaptive throttling:** Slows down when approaching limit
- **Priority queuing:** Important requests go first
- **Wait time calculation:** Dynamic wait based on remaining quota

### Rate Limit States

| State | Remaining | Action |
|-------|-----------|--------|
| **Healthy** | > 2000 | Normal speed |
| **Throttling** | 500-2000 | Add delays between requests |
| **Critical** | < 500 | Slow down significantly |
| **Exhausted** | 0 | Wait for reset |

### Rate Limiter Implementation

**Location:** `apps/backend/runners/github/rate_limiter.py`

```python
class RateLimiter:
    """GitHub API rate limiter with adaptive throttling."""

    async def acquire(self, cost: int = 1) -> None:
        """
        Acquire rate limit quota.

        Args:
            cost: Request cost (default: 1)

        Waits if quota is low, raises if exhausted.
        """

    async def wait_for_reset(self) -> None:
        """Wait until rate limit resets."""

    @property
    def remaining(self) -> int:
        """Get remaining requests (from headers)."""

    @property
    def reset_time(self) -> datetime:
        """Get when rate limit resets."""
```

### Wait Time Calculation

```python
# Dynamic wait based on remaining quota
if remaining > 2000:
    wait_time = 0  # No throttling
elif remaining > 500:
    wait_time = 1  # 1 second between requests
else:
    wait_time = 60  # 1 minute between requests

# Progressive backoff as quota decreases
wait_time = int((2000 - remaining) / 100)
```

---

## CI/CD Integration

### CI Status Checks

**Comprehensive CI Validation:**

The integration performs comprehensive CI status checks that account for GitHub Actions workflows from forks:

**Checks:**
- **Passing workflows:** Count of successful workflow runs
- **Failing workflows:** Count and names of failed checks
- **Pending workflows:** Count of runs in progress
- **Awaiting approval:** Fork PRs that require maintainer approval to run workflows

**Workflow Status from Forks:**

When a PR comes from a fork, GitHub requires maintainer approval before running workflows. This integration detects this state:

```python
ci_status = await gh_client.get_pr_checks_comprehensive(pr_number)

# Result:
{
    "passing": 5,        # Successful workflow runs
    "failing": 1,         # Failed workflow runs
    "pending": 2,         # In-progress runs
    "awaiting_approval": 3, # Fork PRs waiting for approval
    "failed_checks": ["tests", "lint"],  # Names of failed checks
}
```

**Impact on Merge Verdict:**

- **Failing CI** → BLOCKED (must fix before merge)
- **Awaiting approval** → BLOCKED (maintainer must approve workflows)
- **All passing** → Can proceed with code review findings

### Merge Verdict with CI

**Blocker Hierarchy:**
1. **Merge conflicts** (highest priority)
2. **Failing CI checks**
3. **Workflows awaiting approval** (fork PRs)
4. **Critical code findings**
5. **Verification failures** (claims without evidence)
6. **High-severity redundancy**
7. **Branch behind base** (soft blocker)

**CI Recovery Detection:**

In follow-up reviews, if CI was failing but now passes:
```python
# Previous review: CI failing → BLOCKED
# Follow-up review: CI now passing
if previous_was_blocked_by_ci and ci_now_passing:
    # Update verdict to reflect CI recovery
    # Check for remaining non-CI blockers
    if no_other_blockers:
        verdict = MergeVerdict.READY_TO_MERGE
```

---

## Data Storage

### Directory Structure

```
.auto-claude/github/
├── reviews/                    # PR review results
│   ├── pr_123.json            # Review data for PR #123
│   └── pr_456.json
├── triage/                     # Issue triage results
│   ├── issue_789.json         # Triage data for issue #789
│   └── issue_012.json
├── autofix/                     # Auto-fix state
│   ├── queue.json              # Active auto-fix queue
│   └── state/                 # Per-issue state files
│       ├── issue_456.json
│       └── issue_789.json
├── batches/                     # Batch state
│   ├── batch_001.json          # Batch metadata
│   └── batch_002.json
├── bot_detection.json           # Bot detection state
└── rate_limit.json            # Rate limit state
```

### State Models

**PRReviewResult:**
```python
@dataclass
class PRReviewResult:
    pr_number: int
    repo: str
    success: bool
    findings: list[PRReviewFinding]
    summary: str
    overall_status: str  # approve/request_changes/comment
    verdict: MergeVerdict
    verdict_reasoning: str
    blockers: list[str]
    risk_assessment: dict
    structural_issues: list[StructuralIssue]
    ai_comment_triages: list[AICommentTriage]
    reviewed_commit_sha: str  # For follow-up reviews
    reviewed_file_blobs: dict[str, str]  # Rebase-resistant
    is_followup_review: bool = False
    resolved_findings: list[str] = field(default_factory=list)
    unresolved_findings: list[str] = field(default_factory=list)
    new_findings_since_last_review: list[PRReviewFinding] = field(default_factory=list)
```

**TriageResult:**
```python
@dataclass
class TriageResult:
    issue_number: int
    category: TriageCategory
    confidence: float  # 0.0-1.0
    is_duplicate: bool
    duplicate_of: int | None
    is_spam: bool
    is_feature_creep: bool
    labels_to_add: list[str]
    labels_to_remove: list[str]
    reasoning: str
```

**AutoFixState:**
```python
@dataclass
class AutoFixState:
    issue_number: int
    status: AutoFixStatus  # pending/analyzing/creating_spec/etc
    spec_id: str | None
    pr_number: int | None
    triggered_by: str
    triggered_at: datetime
    error: str | None
```

---

## CLI Usage

### Basic Commands

**Review a PR:**
```bash
cd apps/backend

# Review specific PR
python runners/github/runner.py review-pr 123

# Auto-post review to GitHub
python runners/github/runner.py review-pr 123 --auto-post

# Force re-review (skip "already reviewed" check)
python runners/github/runner.py review-pr 123 --force
```

**Follow-up Review:**
```bash
# Re-review PR after changes
python runners/github/runner.py followup-review-pr 123
```

**Triage Issues:**
```bash
# Triage all open issues
python runners/github/runner.py triage

# Triage specific issues
python runners/github/runner.py triage 1 2 3

# Apply labels automatically
python runners/github/runner.py triage --apply-labels
```

**Auto-Fix Issues:**
```bash
# Start auto-fix for issue
python runners/github/runner.py auto-fix 456

# Check for issues with auto-fix labels
python runners/github/runner.py check-auto-fix-labels

# Check for new issues
python runners/github/runner.py check-new

# Show auto-fix queue
python runners/github/runner.py queue
```

**Batch Issues:**
```bash
# Batch all open issues
python runners/github/runner.py batch-issues

# Batch specific issues
python runners/github/runner.py batch-issues 1 2 3 4 5

# Show batch status
python runners/github/runner.py batch-status

# Preview proposed batches (proactive workflow)
python runners/github/runner.py analyze-preview --json > batches.json

# Approve and execute batches
python runners/github/runner.py approve-batches batches.json
```

### Configuration

**Environment Variables:**

| Variable | Purpose | Default |
|-----------|-------------|----------|
| `GITHUB_TOKEN` | GitHub API token | `gh auth token` |
| `GITHUB_BOT_TOKEN` | Bot account token (for comments) | None |
| `GITHUB_REPO` | Repository (owner/name) | Auto-detect |
| `AUTO_FIX_ALLOWED_ROLES` | Roles that can trigger auto-fix | `admin,maintainer` |
| `AUTO_FIX_LABELS` | Labels that trigger auto-fix | `auto-fix` |
| `REVIEW_OWN_PRS` | Review own PRs | `false` |
| `USE_PARALLEL_ORCHESTRATOR` | Use SDK subagents for reviews | `false` |

**GitHub CLI Integration:**

```bash
# Authenticate with GitHub CLI
gh auth login

# Auto-detect repo from git remote
cd /path/to/repo
python runners/github/runner.py review-pr 123
# → Uses gh to detect: owner/repo
```

---

## Architecture Patterns

### Service Layer Pattern

**Purpose:** Separation of concerns with specialized services

**Implementation:**

```python
# Orchestrator delegates to services
class GitHubOrchestrator:
    def __init__(self, project_dir, config):
        # Initialize services
        self.pr_review_engine = PRReviewEngine(...)
        self.triage_engine = TriageEngine(...)
        self.autofix_processor = AutoFixProcessor(...)
        self.batch_processor = BatchProcessor(...)

    async def review_pr(self, pr_number):
        # Delegate to PR review service
        return await self.pr_review_engine.review(pr_context)

    async def triage_issues(self, issues):
        # Delegate to triage service
        return await self.triage_engine.triage_all(issues)
```

### Progress Callbacks

**Purpose:** Real-time progress reporting

```python
@dataclass
class ProgressCallback:
    phase: str  # "gathering_context", "analyzing", etc.
    progress: int  # 0-100
    message: str
    issue_number: int | None
    pr_number: int | None

# Usage
def print_progress(callback: ProgressCallback):
    prefix = f"[PR #{callback.pr_number}] "
    print(f"{prefix}[{callback.progress:3d}%] {callback.message}")

orchestrator = GitHubOrchestrator(
    project_dir=project_dir,
    config=config,
    progress_callback=print_progress
)
```

### State Machine Pattern

**Auto-Fix States:**

```python
class AutoFixStatus(Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    CREATING_SPEC = "creating_spec"
    BUILDING = "building"
    QA_REVIEW = "qa_review"
    PR_CREATED = "pr_created"
    COMPLETED = "completed"
    FAILED = "failed"

# State transitions
PENDING → ANALYZING → CREATING_SPEC → BUILDING → QA_REVIEW → PR_CREATED → COMPLETED
                                                ↓
                                            FAILED
```

---

## Best Practices

### PR Reviews

**DO:**
- Use multi-pass reviews for comprehensive analysis
- Check CI status before reviewing code
- Use follow-up reviews for updated PRs
- Trust bot detection (skip bot PRs)
- Post actionable feedback with specific line references
- Check for merge conflicts (highest priority blocker)

**DON'T:**
- Review same commit twice (bot detection prevents this)
- Ignore CI failures (always blocker)
- Skip merge conflict checks
- Post reviews without file context
- Review PRs in cooling-off period

### Issue Triage

**DO:**
- Use semantic similarity for duplicate detection
- Provide confidence scores with classifications
- Suggest specific labels based on analysis
- Detect spam and feature creep early
- Store triage results for learning

**DON'T:**
- Rely solely on keyword matching (use embeddings)
- Ignore low-confidence classifications (human review)
- Skip permission checks for auto-fix
- Assume all issues are valid (check for spam)

### Auto-Fix

**DO:**
- Require authorization before triggering
- Track state through entire pipeline
- Post status updates to issues
- Handle errors gracefully with human escalation
- Create specs with clear acceptance criteria

**DON'T:**
- Trigger auto-fix for unauthorized users
- Create specs without issue analysis
- Hide errors (always report to issue)
- Skip QA validation

### Rate Limiting

**DO:**
- Respect GitHub rate limits (5000/hour authenticated)
- Use adaptive throttling when quota is low
- Calculate dynamic wait times based on remaining quota
- Prioritize important requests

**DON'T:**
- Ignore rate limit headers
- Spam requests without delays
- Assume unlimited quota
- Bypass rate limiter checks

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|---------|----------|
| **"Already reviewed" error** | Bot detection cached previous review | Use `--force` flag to bypass |
| **"No GitHub token found"** | GITHUB_TOKEN not set | Set environment variable or run `gh auth login` |
| **"Cannot detect repo"** | Not in git repo or no remote | Set GITHUB_REPO=owner/name explicitly |
| **"Rate limit exceeded"** | Too many requests | Wait for reset (check rate_limit.json) |
| **"Auto-fix not authorized"** | User lacks required role | Check AUTO_FIX_ALLOWED_ROLES configuration |
| **"CI status unknown"** | GitHub Actions not configured | Set up workflow files in repo |
| **"Embedding dimension mismatch"** | Changed embedder provider | Run migration script or clear cache |
| **"Workflows awaiting approval"** | Fork PR requires approval | Approve workflows on GitHub (Settings → Actions) |
| **"Infinite review loop"** | Bot detection not working | Check bot_detection.json, add bot accounts |

---

## Performance Characteristics

### PR Review Performance

| Metric | Typical Value |
|--------|--------------|
| Quick scan pass | 10-30 seconds |
| Deep analysis pass | 1-3 minutes |
| AI triage pass | 30-60 seconds |
| Total review time | 2-5 minutes |
| Review with 50 files | 5-10 minutes |
| Follow-up review (changed files only) | 30-120 seconds |

### Issue Triage Performance

| Metric | Typical Value |
|--------|--------------|
| Single issue triage | 2-5 seconds |
| Batch triage (100 issues) | 2-5 minutes |
| Duplicate detection (pairwise) | O(n²) but cached |
| Embedding generation | ~1 second per issue |

### Auto-Fix Performance

| Metric | Typical Value |
|--------|--------------|
| Spec creation from issue | 3-8 minutes |
| Implementation (varies by complexity) | 10-60 minutes |
| QA validation | 2-10 minutes |
| PR creation | < 10 seconds |
| Total end-to-end | 20-90 minutes |

### Batching Performance

| Metric | Typical Value |
|--------|--------------|
| Clustering analysis (100 issues) | 10-30 seconds |
| Batch preview generation | 30-60 seconds |
| Spec creation per batch | 5-10 minutes |
| Implementation per batch | 30-120 minutes |

---

## GitLab Support

### Current Status

**GitHub Integration:** ✅ Fully supported

**GitLab Integration:** 🚧 Planned (architecture supports GitLab)

### GitLab Adaptation

The GitHub integration is designed to be adaptable to GitLab:

**Similar Concepts:**
- GitHub PRs → GitLab Merge Requests
- GitHub Issues → GitLab Issues
- GitHub Actions → GitLab CI/CD
- GraphQL API → GitLab GraphQL API

**Required Changes:**
1. **API Client:** Replace `gh` CLI with GitLab API (`python-gitlab` or `gitlab` CLI)
2. **Webhooks:** GitLab webhook events instead of GitHub
3. **Rate Limiting:** GitLab has different limits
4. **CI Status:** GitLab pipeline status API

**Architecture Compatibility:**
- Orchestrator: ✅ Compatible (workflow-agnostic)
- Services: ✅ Compatible (need GitLab API client)
- State storage: ✅ Compatible (same format)
- Permissions: ✅ Compatible (GitLab roles/members)

---

## References

- **GitHub Runner:** `apps/backend/runners/github/runner.py` - CLI entry point
- **Orchestrator:** `apps/backend/runners/github/orchestrator.py` - Main coordinator
- **Services:** `apps/backend/runners/github/services/` - Service implementations
- **Models:** `apps/backend/runners/github/models.py` - Data models
- **GitHub Client:** `apps/backend/runners/github/gh_client.py` - API wrapper
- **Bot Detection:** `apps/backend/runners/github/bot_detection.py` - Loop prevention
- **Permissions:** `apps/backend/runners/github/permissions.py` - Authorization
- **Rate Limiter:** `apps/backend/runners/github/rate_limiter.py` - Throttling

---

*Documentation generated: 2026-02-12*
