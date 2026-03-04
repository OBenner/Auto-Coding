# Migration Assistant Agent

Comprehensive guide for using Auto Code's migration assistant agent to safely perform framework, library, and language migrations with incremental validation and rollback capability.

## Overview

Auto Code's migration assistant is a specialized AI agent designed to handle complex, high-risk code migrations. Unlike generic coding assistants, it focuses on safe, incremental migration strategies with validation checkpoints at every step.

**Key Capabilities:**
- **Automated migration planning** - Analyzes codebase and creates structured migration plans
- **Incremental execution** - Breaks migrations into small, testable phases
- **Validation checkpoints** - Tests and validates at each step before proceeding
- **Rollback capability** - Git-based checkpoints allow reverting any phase
- **Compatibility layers** - Generates bridge code for gradual transitions
- **Test adaptation** - Updates test suites alongside code changes
- **Decision documentation** - Logs all migration decisions and rationale

**Supported Migration Types:**
- React class components → hooks
- Python 2 → Python 3
- Django version upgrades
- JavaScript → TypeScript
- Framework version upgrades
- Library replacements
- Custom migrations

## Why Use the Migration Assistant?

Migrations are complex, high-risk tasks where traditional AI approaches often fail. The migration assistant addresses common migration challenges:

| Challenge | Migration Assistant Solution |
|-----------|------------------------------|
| **Big-bang rewrites fail** | Incremental phases with validation |
| **Breaking production** | Rollback scripts at each checkpoint |
| **Test suite breaks** | Test adaptation alongside code changes |
| **Lost context** | Decision log documents every choice |
| **No safety net** | Git checkpoints allow reverting any phase |
| **Unknown effort** | Complexity estimation and progress tracking |

## Architecture

The migration assistant uses a three-layer architecture for safe, trackable migrations:

```
┌──────────────────┐
│  Migration Plan  │  ← Structured phases with dependencies
│    (Planner)     │     and validation criteria
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│   Agent Session  │  ← Executes one phase at a time
│  (Coder Agent)   │     with checkpoint creation
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│   Checkpoints    │  ← Git-based snapshots with
│    (Manager)     │     rollback scripts
└──────────────────┘
```

**Workflow:**
1. **Analyze** - Planner analyzes codebase and creates migration plan
2. **Execute** - Agent implements one phase at a time
3. **Validate** - Tests run after each phase
4. **Checkpoint** - Git commit + rollback script created
5. **Repeat** - Move to next phase or rollback if validation fails

## Getting Started

### Prerequisites

1. **Git repository** - Your project must be a git repository
2. **Working tests** - Migration relies on test suite for validation
3. **Clean working directory** - Commit or stash changes before migrating

### Step 1: Create a Migration Spec

Describe the migration you want to perform:

```bash
cd apps/backend
python spec_runner.py --task "Migrate React class components to hooks"
```

Or create a spec manually in `.auto-claude/specs/XXX-migration-name/spec.md`:

```markdown
# React Hooks Migration

Migrate all React class components to hooks-based functional components.

## Rationale
React hooks provide better code reuse and simpler component logic.

## Acceptance Criteria
- [ ] All class components converted to functional components with hooks
- [ ] All tests pass
- [ ] No performance regressions
- [ ] Compatibility layer for gradual transition
```

### Step 2: Run the Migration Assistant

```bash
cd apps/backend

# Run migration assistant for a specific spec
python run.py --spec 001-react-hooks-migration --migrate

# Check migration status
python run.py --spec 001-react-hooks-migration --migration-status
```

The agent will:
1. Analyze your codebase
2. Create a detailed migration plan
3. Execute migration phases incrementally
4. Create checkpoints after each phase
5. Generate rollback scripts

### Step 3: Review and Validate

After the migration assistant completes a phase:

1. **Review changes** in your editor
2. **Run tests** to verify functionality
3. **Check migration plan** in `migration_plan.md`
4. **Inspect checkpoint** in `.migration-checkpoints/`

If a phase fails validation:
```bash
# Rollback to previous checkpoint
.migration-checkpoints/rollback/checkpoint-N.sh
```

### Step 4: Continue or Rollback

Based on validation results:

**If successful:**
```bash
# Continue to next phase
python run.py --spec 001-react-hooks-migration --migrate
```

**If issues found:**
```bash
# Rollback using checkpoint script
.migration-checkpoints/rollback/checkpoint-2.sh

# Or manually revert to previous commit
git reset --hard $(cat .migration-checkpoints/checkpoint-1-commit.txt)
```

## Migration Plan Structure

The migration assistant creates a structured plan in `migration_plan.md`:

```markdown
# Migration Plan: React Class Components → Hooks

## Overview
**Migration Type:** react_class_to_hooks
**Estimated Changes:** 65 files
**Complexity:** MEDIUM

## Phases

### Phase 1: Foundation Setup
**Complexity:** LOW | **Dependencies:** None | **Est. Changes:** 5

**Description:** Set up hooks infrastructure and compatibility layer

**Validation Criteria:**
- [ ] All existing tests pass
- [ ] No ESLint errors
- [ ] Builds successfully

**Rollback:** Git reset to baseline checkpoint

---

### Phase 2: Migrate Leaf Components
**Complexity:** MEDIUM | **Dependencies:** Phase 1 | **Est. Changes:** 20

**Description:** Convert components with no dependencies to hooks

**Files to Migrate:**
- `src/components/Button.jsx`
- `src/components/Input.jsx`
- ...

**Validation Criteria:**
- [ ] Component tests pass
- [ ] No prop-types warnings
- [ ] Renders correctly

**Rollback:** Restore files from checkpoint-1

---

### Phase 3: Migrate Parent Components
...

## Checkpoints

### Checkpoint 1: After Foundation Setup
**Validation Steps:**
1. Run test suite
2. Check for build errors
3. Verify no regressions

**Success Criteria:**
- All tests pass
- No linting errors

**Rollback Command:**
`.migration-checkpoints/rollback/checkpoint-1.sh`

---

## Rollback Strategy
Each phase creates a git checkpoint with rollback script.
To rollback, run the checkpoint script from `.migration-checkpoints/rollback/`.
All checkpoints are ordered and can be rolled back sequentially.
```

## Checkpoint System

### Checkpoint Directory Structure

```
.migration-checkpoints/
├── checkpoint-0-baseline.txt       # Pre-migration state
├── checkpoint-1-commit.txt         # Phase 1 commit hash
├── checkpoint-2-commit.txt         # Phase 2 commit hash
├── checkpoint-N-commit.txt         # Phase N commit hash
└── rollback/
    ├── checkpoint-1.sh             # Rollback to baseline
    ├── checkpoint-2.sh             # Rollback to phase 1
    └── checkpoint-N.sh             # Rollback to phase N-1
```

### Checkpoint Contents

Each checkpoint includes:

1. **Commit Hash** - Git commit SHA for exact rollback
2. **Rollback Script** - Executable script to revert changes
3. **Validation Results** - Test results and verification status

### Using Rollback Scripts

Rollback scripts are automatically generated and executable:

```bash
# Rollback from checkpoint 3 to checkpoint 2
cd .migration-checkpoints/rollback
./checkpoint-3.sh

# Output:
# Rolling back to checkpoint 2...
# Commit: abc1234def5678
# Files restored: 12
# Tests: PASS
```

## Common Migration Patterns

### React Class Components → Hooks

**Before:**
```javascript
class UserProfile extends React.Component {
  state = { user: null };

  componentDidMount() {
    fetchUser(this.props.userId).then(user => this.setState({ user }));
  }

  render() {
    return <div>{this.state.user?.name}</div>;
  }
}
```

**After:**
```javascript
function UserProfile({ userId }) {
  const [user, setUser] = useState(null);

  useEffect(() => {
    fetchUser(userId).then(setUser);
  }, [userId]);

  return <div>{user?.name}</div>;
}
```

**Checkpoint Criteria:**
- All component tests pass
- No ESLint warnings
- Builds successfully

### Python 2 → Python 3

**Before:**
```python
print "Hello", name
items = data.iteritems()
result = map(lambda x: x * 2, range(10))
```

**After:**
```python
print("Hello", name)
items = data.items()
result = list(map(lambda x: x * 2, range(10)))
```

**Checkpoint Criteria:**
- All tests pass on Python 3
- `2to3` reports no issues
- Type hints added

### Django Version Upgrade

**Migration Phases:**
1. **Update Dependencies** - Update Django and related packages (checkpoint)
2. **Settings and Middleware** - Update configuration (checkpoint)
3. **URL Patterns** - Migrate to new syntax (checkpoint)
4. **Models and Migrations** - Update models and run migrations (checkpoint)
5. **Views and Templates** - Update deprecated patterns (checkpoint)

Each phase must validate before proceeding.

### JavaScript → TypeScript

**Migration Phases:**
1. **TypeScript Setup** - Configure tsconfig.json and type definitions (checkpoint)
2. **Migrate Utilities** - Convert utility files to .ts (checkpoint)
3. **Migrate Components** - Convert components to .tsx (checkpoint)
4. **Add Type Definitions** - Add comprehensive types (checkpoint)
5. **Remove `any` Types** - Strengthen type safety (checkpoint)

## Advanced Usage

### Custom Migration Types

For migrations not covered by built-in types:

```bash
# Create a custom migration spec
python spec_runner.py --task "Migrate from MobX to Redux state management"
```

The agent will:
1. Analyze your codebase
2. Detect patterns to migrate
3. Create a custom migration plan
4. Execute incrementally with checkpoints

### Parallel Migrations

For large codebases with independent modules:

```bash
# Create separate migration specs for independent modules
python spec_runner.py --task "Migrate auth module to hooks"
python spec_runner.py --task "Migrate dashboard module to hooks"

# Run migrations in parallel (different git worktrees)
python run.py --spec 001-auth-hooks-migration --migrate
python run.py --spec 002-dashboard-hooks-migration --migrate
```

The agent uses compatibility layers to isolate changes.

### Migration with External Dependencies

For migrations involving external services or APIs:

```bash
# Spec should include external integration details
python spec_runner.py --task "Migrate from Stripe v2 to v3 API"
```

The agent will:
1. Research API changes (using web search if available)
2. Create compatibility wrapper
3. Migrate endpoint by endpoint
4. Update tests to mock new API

## CLI Reference

### Migration Commands

| Command | Description | Example |
|---------|-------------|---------|
| `--migrate` | Run migration assistant | `python run.py --spec 001 --migrate` |
| `--migration-status` | Check migration status | `python run.py --spec 001 --migration-status` |

### Migration Status Output

```
Migration Status:

Latest checkpoint:    checkpoint-2-commit.txt
Commit:              abc1234def56
Rollback scripts:    3
Migration plan:      migration_plan.md

✅ Checkpoints are valid.
```

## Integration with Other Agents

The migration assistant integrates seamlessly with other Auto Code agents:

| Agent | How It Helps |
|-------|-------------|
| **QA Reviewer** | Validates each checkpoint against acceptance criteria |
| **Test Generator** | Creates tests for new patterns during migration |
| **Memory System** | Learns migration patterns for future use |

## Best Practices

### Before Starting

- [ ] **Clean git state** - Commit or stash all changes
- [ ] **Review existing tests** - Ensure tests are comprehensive
- [ ] **Backup important data** - Create a git tag or branch
- [ ] **Read migration plan** - Understand phases before starting
- [ ] **Check dependencies** - Update dependencies if needed

### During Migration

- [ ] **One phase at a time** - Don't rush through multiple phases
- [ ] **Validate thoroughly** - Run full test suite after each checkpoint
- [ ] **Review diffs** - Understand what changed in each phase
- [ ] **Document decisions** - Add notes to migration plan
- [ ] **Test manually** - Automated tests may not catch everything

### After Migration

- [ ] **Remove compatibility layers** - Clean up temporary bridge code
- [ ] **Update documentation** - Reflect new patterns in docs
- [ ] **Share learnings** - Document migration insights
- [ ] **Performance check** - Ensure no regressions
- [ ] **Clean up checkpoints** - Archive or remove checkpoint directory

## Troubleshooting

### Migration Assistant Won't Start

**Problem:** Agent fails to start migration session

**Solutions:**
1. Verify spec directory exists
2. Check for required files (spec.md, implementation_plan.json)
3. Ensure clean git working directory
4. Review logs in `.auto-claude/specs/XXX/build-progress.txt`

### Checkpoint Validation Fails

**Problem:** Tests fail after a checkpoint

**Solutions:**
1. Review test output for specific failures
2. Check if test expectations need updating
3. Verify compatibility layer is working
4. Rollback and re-attempt with fixes:
   ```bash
   .migration-checkpoints/rollback/checkpoint-N.sh
   ```

### Rollback Script Doesn't Work

**Problem:** Rollback script fails to restore previous state

**Solutions:**
1. Manually revert using git:
   ```bash
   git reset --hard $(cat .migration-checkpoints/checkpoint-N-commit.txt)
   ```
2. Check for uncommitted changes
3. Verify checkpoint file exists and has valid commit hash

### Migration Plan Too Complex

**Problem:** Generated migration plan has too many phases

**Solutions:**
1. Break migration into smaller specs
2. Use custom migration type for better control
3. Manually adjust migration plan before running
4. Focus on high-impact areas first

### Compatibility Layer Conflicts

**Problem:** Compatibility layer causes unexpected behavior

**Solutions:**
1. Review compatibility layer implementation
2. Add tests specifically for compatibility layer
3. Consider alternative compatibility approach
4. Document compatibility layer limitations

## Examples

### Example 1: React Hooks Migration

**Scenario:** Migrate 50 React class components to hooks

```bash
# 1. Create migration spec
python spec_runner.py --task "Migrate all React components from class-based to hooks"

# 2. Run migration assistant
python run.py --spec 001-react-hooks --migrate

# 3. Agent creates plan with 4 phases:
#    - Phase 1: Setup hooks infrastructure (5 files)
#    - Phase 2: Migrate leaf components (15 files)
#    - Phase 3: Migrate parent components (20 files)
#    - Phase 4: Remove compatibility layer (10 files)

# 4. Review after each phase
cat migration_plan.md
npm test

# 5. Continue to next phase or rollback if issues
python run.py --spec 001-react-hooks --migrate
```

**Result:** Safe, incremental migration with 4 validation checkpoints

### Example 2: Python 2 to 3 Migration

**Scenario:** Migrate legacy Python 2 codebase to Python 3

```bash
# 1. Create migration spec
python spec_runner.py --task "Migrate Python 2 codebase to Python 3"

# 2. Run migration assistant
python run.py --spec 002-python3-migration --migrate

# 3. Agent creates plan with 5 phases:
#    - Phase 1: Print statements (50 changes)
#    - Phase 2: Import changes (30 changes)
#    - Phase 3: String/unicode handling (40 changes)
#    - Phase 4: Dict methods (25 changes)
#    - Phase 5: Type hints (60 changes)

# 4. Validate each phase with Python 3
python3 -m pytest tests/ -v

# 5. Rollback if validation fails
.migration-checkpoints/rollback/checkpoint-N.sh
```

**Result:** Complete Python 3 migration with rollback capability

### Example 3: Custom API Migration

**Scenario:** Migrate from deprecated API to new version

```bash
# 1. Create migration spec with details
python spec_runner.py --task "Migrate from Stripe API v2 to v3"

# 2. Run migration assistant
python run.py --spec 003-stripe-api-migration --migrate

# 3. Agent researches API changes and creates plan:
#    - Phase 1: Create v3 API compatibility wrapper
#    - Phase 2: Migrate payment endpoints
#    - Phase 3: Migrate subscription endpoints
#    - Phase 4: Remove v2 compatibility layer

# 4. Test integration with Stripe test mode
npm run test:integration

# 5. Deploy incrementally to production
```

**Result:** Safe API migration with compatibility layer during transition

## Performance Considerations

### Migration Speed

| Codebase Size | Estimated Time | Checkpoints |
|--------------|----------------|-------------|
| Small (< 50 files) | 1-2 hours | 3-4 |
| Medium (50-200 files) | 4-8 hours | 6-8 |
| Large (200-500 files) | 1-2 days | 10-15 |
| Very Large (> 500 files) | 2-5 days | 15-20 |

**Note:** Time estimates assume working test suite and minimal conflicts.

### Resource Usage

- **CPU:** Moderate during analysis, low during execution
- **Memory:** Scales with codebase size (typically < 2GB)
- **Disk:** Checkpoint files add ~10-50MB per checkpoint
- **Network:** Minimal (only for research phase if enabled)

## Security Considerations

The migration assistant follows Auto Code's three-layer security model:

1. **OS Sandbox** - All commands run in isolated environment
2. **Filesystem Restrictions** - Limited to project directory
3. **Command Allowlist** - Only approved commands based on project stack

**Additional Migration Security:**
- **Git-based rollback** - All changes tracked in version control
- **No automatic pushes** - Changes stay local until user reviews
- **Checkpoint validation** - Tests must pass before proceeding
- **Manual approval** - User controls when to continue or rollback

## FAQ

### Q: Can I pause a migration?

**A:** Yes. Press Ctrl+C to pause. Resume with:
```bash
python run.py --spec 001-migration --migrate
```

The agent will continue from the last checkpoint.

### Q: What happens if tests fail during migration?

**A:** The agent will:
1. Detect test failure
2. Attempt to fix issues
3. If unfixable, pause and request user intervention
4. User can rollback using checkpoint script

### Q: Can I customize the migration plan?

**A:** Yes. Edit `migration_plan.md` before running the agent. The agent will follow your custom plan structure.

### Q: How do I migrate a monorepo?

**A:** Create separate migration specs for each package:
```bash
python spec_runner.py --task "Migrate @myorg/package-a to hooks"
python spec_runner.py --task "Migrate @myorg/package-b to hooks"
```

Run migrations sequentially or in parallel (using compatibility layers).

### Q: What if the migration assistant gets stuck?

**A:** Check `build-progress.txt` for details. Common fixes:
1. Verify tests are passing before migration
2. Check for syntax errors in codebase
3. Ensure git working directory is clean
4. Review spec for unclear requirements
5. Use `--verbose` flag for detailed logging

### Q: Can I use migration assistant without tests?

**A:** Not recommended. The migration assistant relies on tests for validation. Without tests, checkpoints cannot be validated automatically, increasing risk of breaking changes.

## Related Documentation

- [Agent Architecture](../CLAUDE.md#agent-architecture) - How agents work
- [CLI Usage](../guides/CLI-USAGE.md) - Complete CLI reference
- [Security Model](../CLAUDE.md#security-model) - Security features
- [QA Validation](../CLAUDE.md#qa-validation) - How QA agents validate changes

## Contributing

Found a migration pattern that should be built-in? Submit a PR to add it to `apps/backend/migrations/planner.py`:

```python
def _plan_my_custom_migration(self) -> None:
    """Plan my custom migration type."""
    self.phases = [
        MigrationPhase(
            id="phase-1",
            name="Phase Name",
            description="What this phase does",
            complexity=MigrationComplexity.MEDIUM,
            ...
        ),
        # More phases...
    ]
```

See [CONTRIBUTING.md](../CONTRIBUTING.md) for details.
