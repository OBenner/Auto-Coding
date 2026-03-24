# ADR-003: Git Worktree Isolation for Autonomous Build Sessions

**Date:** 2024-02-10
**Status:** Accepted
**Deciders:** Auto Code Core Team
**Tags:** git, worktree, isolation, workspace, security

---

## Context

Auto Code runs autonomous multi-agent sessions that make sweeping changes to a codebase — creating files, modifying existing code, running tests, and committing intermediate work. A critical design question is: **where do these changes happen?**

Several approaches are possible:

1. **In-place on the current branch** — Agents modify the working tree directly where the user is working.
2. **A separate clone** — A full copy of the repository on disk, separate from the user's working copy.
3. **Git worktrees** — A first-class Git feature that creates an additional linked working directory attached to the same repository object store but checked out on a separate branch.

Key requirements that drove this decision:

- **User safety** — A runaway or buggy agent must not corrupt the user's active working state (uncommitted changes, current branch, etc.).
- **Reviewability** — The user must be able to inspect, run, and test agent-produced changes before accepting them.
- **No data duplication** — Full repository clones waste disk space and diverge from the upstream object store.
- **Parallel builds** — Multiple specs should be buildable concurrently without interference.
- **Clean rollback** — The user must be able to discard an agent's work without affecting anything else.
- **Git history integrity** — Agent commits must appear on an identifiable branch, not pollute `main`.

## Decision

We will use **Git worktrees** to isolate every autonomous build session. Each spec gets its own worktree on a dedicated branch following the naming convention `auto-code/{spec-name}`.

Worktrees are created in `.worktrees/{spec-name}/` relative to the project root and are managed by `apps/backend/cli/worktree.py`.

```
project-root/                  ← user's working copy (main branch)
└── .worktrees/
    └── my-feature/            ← git worktree for spec "my-feature"
        ├── apps/
        ├── tests/
        └── ...                (full working tree, branch: auto-code/my-feature)
```

The lifecycle is:
1. **Create** — `python run.py --spec 001` creates a worktree on a new `auto-code/{spec-name}` branch.
2. **Build** — All agent activity (file edits, commands, commits) occurs exclusively inside the worktree.
3. **Review** — The user enters the worktree directory to inspect and test changes.
4. **Merge or Discard** — `--merge` fast-forwards `main`, `--discard` deletes the worktree and branch.

All branches remain **local** until the user explicitly pushes. Auto Code never pushes to a remote.

## Rationale

Git worktrees were chosen because they satisfy all requirements with minimal overhead and leverage a built-in Git primitive rather than custom infrastructure.

### Key factors

- **Atomic isolation at zero cost** — A worktree shares the `.git` object store with the main clone. No files are duplicated; only a working tree and a branch pointer are added. This is far lighter than a full repository clone.
- **Branch-per-build traceability** — Every spec maps to a named branch (`auto-code/{spec-name}`). This means the diff between `main` and the spec branch always precisely represents the agent's work, making review straightforward.
- **User working tree is untouched** — Because the agent writes exclusively to the worktree directory, the user's current branch, index, and unstaged changes are never disturbed.
- **Native Git tooling works** — Because the worktree is a proper Git checkout, the user can run `git log`, `git diff`, `git stash`, IDE diff tools, etc. inside it without any special tooling.
- **Parallel spec support** — Multiple worktrees can coexist simultaneously, enabling concurrent builds of independent specs.
- **Clean discard** — `git worktree remove --force` followed by `git branch -D` atomically removes all agent work. There are no stray files to clean up.
- **CI/CD compatibility** — In headless CI mode, worktrees are created programmatically in the same way and cleaned up after the build completes.

### Alternatives considered

| Option | Pros | Cons |
|--------|------|------|
| **Git worktrees** (chosen) | Lightweight; shares object store; native Git tooling; per-spec branch traceability; easy discard | Requires Git 2.5+; cannot have two worktrees on the same branch simultaneously |
| **In-place on current branch** | No setup needed | Agents corrupt user's working state; impossible to safely discard without losing user work; no isolation |
| **Full repository clone** | Complete isolation; familiar model | Doubles disk usage; clones diverge from upstream (fetch needed before merge); slower to create; no native link to main repo |
| **Stash + restore** | Uses existing working tree | Stash conflicts are common; no separate branch means no clean diff; not suitable for long-running sessions |
| **Docker/VM sandbox** | Strongest isolation | Heavy infrastructure; file sync latency; complex setup; out of scope for a local-first tool |

## Consequences

### Positive

- Agent activity is completely isolated — the user can continue working on `main` while a build runs in a worktree.
- Each spec's changes are captured on a dedicated branch, making `git diff main..auto-code/{spec-name}` a precise audit trail.
- Merge is a simple fast-forward or squash merge, preserving clean history.
- Discard is instant and leaves no residue in the main working tree or Git history.
- Multiple specs can be built in parallel without any branch conflicts.
- The `.worktrees/` directory is `.gitignore`d, so worktree directories never accidentally appear as untracked files in the main working copy.

### Negative

- Git 2.5 or later is required. Very old Git installations will not support worktrees, though this is rarely a practical constraint.
- A branch may not be checked out in more than one worktree at a time. If a user manually checks out `auto-code/my-feature` in the main working tree, the worktree creation for that spec will fail.
- Worktree directories can accumulate on disk if builds are abandoned without running `--discard`. The `--list` command shows all specs and their worktree status to help with housekeeping.
- On Windows, paths inside `.worktrees/` can become long. Auto Code enforces a short spec-name convention and places worktrees close to the repository root to mitigate MAX_PATH issues.

### Neutral

- The `.worktrees/` directory must be added to `.gitignore` for new projects. Auto Code's setup routines handle this automatically.
- Merge strategy (fast-forward vs. squash) is the user's choice at `--merge` time. The default is a merge commit to preserve the full agent build history as a distinct unit.
- The `auto-code/` branch prefix is a namespace convention enforced by `worktree.py`. It is not a Git feature but makes spec branches easy to identify and bulk-delete if needed.

## Implementation notes

The worktree lifecycle is implemented in `apps/backend/cli/worktree.py`:

- **`create_worktree(spec_name, project_dir)`** — Creates `.worktrees/{spec-name}/` on branch `auto-code/{spec-name}`.
- **`remove_worktree(spec_name, project_dir)`** — Runs `git worktree remove --force` and deletes the branch.
- **`merge_worktree(spec_name, project_dir, strategy)`** — Merges the spec branch into the current branch using the selected strategy, then removes the worktree.
- **`list_worktrees(project_dir)`** — Returns all active worktrees and their associated spec metadata.

All agent file operations and shell commands in `apps/backend/agents/` use the worktree path as their working directory. The security layer (`core/security.py`) enforces that filesystem operations stay within the worktree root, providing a second line of defence against path traversal.

```python
# Worktree path is passed through the full agent pipeline
worktree_path = create_worktree(spec_name, project_dir)

client = create_client(
    project_dir=worktree_path,  # agents operate inside the worktree
    spec_dir=spec_dir,
    agent_type="coder",
)
```

## References

- `apps/backend/cli/worktree.py` — Worktree lifecycle implementation
- `apps/backend/core/security.py` — Filesystem restriction enforcement
- `apps/backend/run.py` — `--merge`, `--discard`, `--review` CLI integration
- [ADR-001: Adopt Claude Agent SDK](./ADR-001-claude-agent-sdk.md) — Agent session architecture
- [ADR-002: Graphiti Memory System](./ADR-002-graphiti-memory.md) — Memory stored per-spec alongside worktrees
- [CLAUDE.md](../../../CLAUDE.md) — Branching and worktree strategy overview
- [Git worktree documentation](https://git-scm.com/docs/git-worktree)

---

*This ADR follows the [Auto Code ADR format](./template.md). See the [ADR index](./README.md) for all decisions.*
