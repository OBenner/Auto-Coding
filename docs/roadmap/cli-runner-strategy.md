# LLM CLI Runner Strategy

This document explains why Auto Code should support current LLM coding CLIs,
what business value that support creates, and how to approach the work without
turning the product into a loose collection of tool wrappers.

## Executive Summary

Supporting LLM coding CLIs gives Auto Code a stronger product position: it can
become the orchestration layer above the agents developers already use, rather
than competing as another single-agent coding tool.

The goal is not to add logos for every popular CLI. The goal is to let Auto
Code run a governed workflow across multiple execution backends:

- A task is converted into a spec and implementation plan.
- The right runner is selected for the job.
- Work happens in an isolated workspace.
- Tests, review, and QA gates run consistently.
- The final output is a reviewable branch or pull request with an audit trail.

This makes Auto Code more resilient, more useful to teams with existing AI
subscriptions, and more defensible as a self-hostable agentic software
engineering control plane.

## Why This Matters

The AI coding market is fragmenting across terminal agents, IDE agents,
provider-specific CLIs, review CLIs, and open-source local-first tools. Strong
examples include Codex CLI, Claude Code, Gemini CLI, GitHub Copilot CLI, Cursor
CLI, Aider, OpenCode, Goose, Amp, Qwen Code, and CodeRabbit CLI.

Each tool is optimizing for a different workflow:

- Frontier coding agents optimize for implementation and debugging.
- Long-context agents optimize for large-repository analysis and research.
- Git-native tools optimize for controlled file edits and commits.
- GitHub-native tools optimize for issues, pull requests, and repository
  automation.
- Review tools optimize for independent quality gates.
- Open-source tools optimize for BYOK, local models, and provider choice.

Auto Code can benefit from this diversity if it owns the workflow around them:
specs, planning, routing, workspace isolation, policy, QA, artifacts, and final
review.

## Strategic Goals

### 1. Reduce Provider And Tool Lock-In

Auto Code should not depend on one vendor's authentication model, pricing,
rate limits, model quality, or product roadmap. CLI runner support creates
fallback paths when a provider changes behavior or when a team already has
access to another agent.

Target outcome:

- Users can choose the runner that matches their account, policy, budget, and
  task type.
- Auto Code can degrade gracefully when a runner is unavailable.
- The product story becomes "bring your agent" rather than "use our one
  required backend."

### 2. Improve Quality Through Task-Specific Routing

Different CLIs have different strengths. Auto Code should route work based on
capability rather than treating every model or CLI as interchangeable.

Examples:

- Use Codex CLI or Claude Code for complex coding and refactoring tasks.
- Use Gemini CLI for large-context codebase discovery and research-heavy tasks.
- Use Aider for focused, git-native edits where a developer wants explicit
  control over commits.
- Use GitHub Copilot CLI for GitHub-native issue, branch, and pull-request
  workflows.
- Use Cursor CLI when a team already has Cursor Agent, Cursor rules, and
  project-local Cursor configuration.
- Use CodeRabbit CLI as an independent review gate after an implementation
  runner modifies files.

Target outcome:

- Better first-pass implementations.
- Better review coverage.
- Less repeated work caused by using the wrong agent for the task.
- Clear fallback behavior when a runner lacks a needed capability.

### 3. Lower Adoption Friction

Many developers and teams already pay for Claude, ChatGPT, GitHub Copilot,
Cursor, Gemini, or other AI tooling. Auto Code should be able to use existing
local CLIs where possible instead of forcing a separate required provider path.

Target outcome:

- Users can try Auto Code with credentials and tools they already have.
- Teams can adopt Auto Code without immediately changing model procurement.
- The product becomes easier to evaluate in heterogeneous engineering teams.

### 4. Strengthen Enterprise Positioning

Enterprise teams do not only need code generation. They need policy, isolation,
auditability, approval control, repeatability, and cost visibility.

CLI runner support helps Auto Code position itself as the governance layer
around agentic coding:

- Centralized runner policy.
- Consistent worktree isolation.
- Common audit events across tools.
- Approval gates around commands, file scopes, network use, and merges.
- Standard QA and review artifacts regardless of the underlying agent.

Target outcome:

- Auto Code can support organizations that want choice without losing control.
- Teams can standardize the workflow even when individual developers prefer
  different agents.
- Security-conscious users can run local, BYOK, or enterprise-approved runners.

### 5. Make QA Independent From Generation

The agent that writes code should not be the only judge of its own output.
Supporting review CLIs and secondary runners lets Auto Code build a stronger
generate-review-fix loop.

Target outcome:

- Implementation runner creates changes.
- Review runner inspects the diff.
- QA runner validates acceptance criteria and test results.
- Fixer runner addresses concrete findings.
- The final summary records which runner did what and which checks passed.

This creates a stronger trust story than a single agent producing code and
self-certifying the result.

## Product Advantages

### Stronger Differentiation

Most CLI agents focus on the local coding session. Auto Code can focus on the
end-to-end delivery workflow:

- Requirements capture.
- Spec generation.
- Implementation planning.
- Agent execution.
- QA review.
- Fix loops.
- Artifacts.
- Branch or pull-request handoff.

The differentiator is not having another chat surface. The differentiator is
governed delegation from task to reviewed change set.

### Better Resilience

If one CLI becomes expensive, rate-limited, degraded, unavailable, or blocked by
policy, Auto Code can route around it. This matters because the agent market is
moving quickly and vendor behavior changes often.

### Better Cost Control

Runner support lets teams match task complexity to cost:

- Use premium agents for architecture-heavy work.
- Use cheaper or local runners for small edits and mechanical changes.
- Use review tools only at meaningful checkpoints.
- Track costs by phase, runner, spec, and outcome.

### Better Fit For Real Teams

Teams rarely standardize instantly on a single AI coding tool. A platform that
works with Codex, Claude, Gemini, Copilot, Cursor, Aider, and review tools can
fit real mixed environments more naturally.

### Better Ecosystem Compatibility

Many modern agents already understand shared conventions such as `AGENTS.md`,
MCP servers, skills, custom commands, and headless execution. Auto Code can
lean into those standards instead of rebuilding every integration from scratch.

## Recommended Support Tiers

### Tier 1: First-Class Runners

These runners should have explicit capability definitions, setup checks,
structured output handling, and regression tests.

| Runner | Role In Auto Code |
| --- | --- |
| Codex CLI | Default modern coding runner and OpenAI-aligned agent path. |
| Claude Code | Compatibility runner for existing Claude Code users and current workflows. |
| Gemini CLI | Long-context research, repository analysis, and cost-sensitive workflows. |
| Aider | Git-native focused editing and BYOK/local-model workflows. |
| CodeRabbit CLI | Independent review and quality gate, not an implementation runner. |

### Tier 2: Strategic Integrations

These should be supported after the runner interface is stable.

| Runner | Role In Auto Code |
| --- | --- |
| GitHub Copilot CLI | GitHub-native issues, PRs, repository automation, and enterprise GitHub workflows. |
| Cursor CLI | Support for teams already standardized on Cursor Agent, Cursor rules, and Cursor-managed project context. |

### Tier 3: Generic CLI Runner Support

These should initially work through a generic runner contract unless user demand
justifies deeper integration.

| Runner | Role In Auto Code |
| --- | --- |
| OpenCode | Open-source multi-provider agent option. |
| Goose | General-purpose local agent and MCP-heavy automation option. |
| Amp | High-quality commercial agent option for teams already using Amp. |
| Qwen Code | Qwen-optimized Gemini CLI derivative; useful through generic CLI support. |
| DeepV Code / Codeep | Emerging open-source alternatives; monitor before deep integration. |

## Capability Model

Each runner should declare what it can safely do. Auto Code should check these
capabilities before assigning work.

Core capabilities:

- `read_files`: can inspect project files.
- `write_files`: can edit project files.
- `run_commands`: can execute shell commands.
- `mcp`: can connect to MCP servers.
- `headless`: can run non-interactively from automation.
- `structured_output`: can emit JSON or machine-readable events.
- `git_aware`: can inspect diffs, commits, branches, or pull requests.
- `review_only`: produces findings but should not implement code.
- `image_input`: can use screenshots or diagrams as input.
- `local_model`: can run against local or self-hosted models.
- `cost_report`: can expose usage or token/cost data.

Runner selection should be based on required capabilities, risk, task type,
available credentials, user policy, and cost preference.

## Architecture Direction

Auto Code should add a runner layer instead of embedding CLI-specific logic in
planner, coder, QA reviewer, or QA fixer modules.

Recommended abstractions:

- `AgentRunner`: executes implementation or analysis work.
- `ReviewRunner`: reviews diffs and produces findings.
- `RunnerCapabilities`: declares supported actions and constraints.
- `RunnerPolicy`: defines allowed commands, file scopes, network access, and
  approval requirements.
- `RunnerResult`: normalizes final message, changed files, commands, errors,
  usage, artifacts, and review findings.
- `RunnerRegistry`: discovers configured runners and selects candidates.

This keeps the existing workflow intact while making execution backends
replaceable.

## Application Experience

CLI runner support should be visible in the desktop app as configured execution
capacity, not as a hidden backend detail. Users should be able to see which
agents are installed, which are authenticated, which are usable for the current
project, and what Auto Code will do when the preferred runner is unavailable.

### Runner Status Model

Each supported CLI should have a status card similar to the existing Claude Code
installation status pattern.

Recommended states:

| State | Meaning | Primary Action |
| --- | --- | --- |
| `ready` | CLI is installed, version is supported, and auth works. | Select as preferred runner. |
| `installed_not_authenticated` | CLI binary exists, but login or token validation failed. | Authenticate or open CLI login flow. |
| `key_available_not_installed` | Auto Code detects a usable key or account configuration, but the CLI is missing. | Offer install. |
| `not_installed` | CLI is not found and no credential signal is available. | Show install instructions. |
| `unsupported_version` | CLI exists, but version is too old or incompatible. | Offer update. |
| `blocked_by_policy` | Project or organization policy disallows this runner. | Show policy reason. |
| `unavailable` | Detection failed, command timed out, or runner cannot be used. | Retry detection or choose fallback. |

This state model is more useful than a simple provider dropdown because it
separates "available on this machine" from "allowed for this task."

### Detection And Setup Flow

The app should run a non-destructive detection pass for known runners:

1. Locate the CLI binary by configured path, common package manager locations,
   and system `PATH`.
2. Read the CLI version with a safe version command.
3. Check authentication with the least invasive available command.
4. Detect credential signals, such as known environment variables or local
   config files, without exposing secret values.
5. Match the runner against project policy and required capabilities.
6. Store only redacted status metadata in settings and logs.

If a credential signal exists but the CLI is not installed, the app should
explain that Auto Code can use the runner after installation. For example:

- OpenAI credentials are present, but Codex CLI is missing.
- Google authentication or API configuration is present, but Gemini CLI is
  missing.
- GitHub Copilot access appears available, but Copilot CLI is missing.
- Cursor installation, account state, or project rules are detected, but the
  Cursor CLI is missing from the configured execution path.
- Claude Code auth exists, but the active Claude binary is missing or outdated.

Installation should always be an explicit user action. The app can open a
terminal with the install command or show copyable instructions, but it should
not silently install or update external agents.

### Preferred Runner And Fallback UX

Users should be able to configure a preferred runner and fallback order.

Recommended controls:

- Default implementation runner.
- Default research/discovery runner.
- Default review runner.
- Per-agent overrides for planner, coder, QA reviewer, and QA fixer.
- Fallback order when the preferred runner is unavailable.
- Per-runner policy: allowed, disabled, review-only, or requires approval.

Example fallback policy:

```text
Implementation:
1. Codex CLI
2. Claude Code
3. Cursor CLI
4. Gemini CLI
5. Aider

Review:
1. CodeRabbit CLI
2. Codex CLI review mode
3. Claude Code review prompt
```

Fallback should not be silent. Before running a task, Auto Code should show a
compact execution plan:

```text
Planner: Claude Code
Coder: Codex CLI
Review: CodeRabbit CLI
Fallback: Gemini CLI if Codex CLI is unavailable
```

If fallback happens during a run, the final artifact should record why:

```text
Codex CLI unavailable: authentication expired.
Fallback runner used: Gemini CLI.
```

### Task-Time Runner Selection

The app should distinguish runner preference from task suitability. A preferred
runner can be skipped when it lacks a required capability.

Examples:

- If a task requires image input and the preferred runner lacks image support,
  choose the next compatible runner.
- If a task requires MCP tools and a runner has MCP disabled, choose another
  runner or ask the user to enable MCP.
- If the user chooses a review-only runner for implementation, block the
  selection and explain that it can only be used as a QA gate.
- If policy requires local-only execution, prefer Aider, Ollama-backed flows, or
  another approved local runner.

The UI should phrase this as capability matching, not as a mysterious automatic
override.

### Cursor CLI Experience

Cursor CLI should be treated as a strategic integration rather than a generic
unknown command because many users already maintain useful Cursor-specific
project context.

Cursor-specific detection should check:

- Whether the `cursor-agent` or equivalent Cursor CLI command is available.
- Whether a supported Cursor version is installed.
- Whether the user has an active Cursor account or CLI authentication state.
- Whether the project contains Cursor rules or configuration that should be
  surfaced as runner context.
- Whether the runner supports the required task mode: headless execution,
  file editing, command execution, review, or MCP.

Recommended UI states:

- `ready`: Cursor CLI is installed and authenticated.
- `installed_not_authenticated`: Cursor CLI exists, but the user needs to log in.
- `key_available_not_installed`: Cursor app/account signals exist, but the CLI is
  not available from Auto Code.
- `blocked_by_policy`: the project allows other runners but disallows Cursor for
  this workspace.

Cursor CLI should be offered as:

- An implementation runner for teams that prefer Cursor Agent.
- A fallback runner after Codex CLI or Claude Code when Cursor is configured.
- A project-context-aware runner when Cursor rules are present.
- A non-default strategic integration until the runner interface and output
  normalization are stable.

## Workflow Fit

The intended workflow is:

1. Auto Code receives a task or issue.
2. Spec and implementation plan are created.
3. Runner registry selects an implementation runner.
4. Work happens in an isolated worktree.
5. Tests and validation commands run through policy-controlled execution.
6. A review runner checks the diff.
7. QA reviewer validates acceptance criteria.
8. Fixer loop runs if review or QA rejects the change.
9. Auto Code produces final artifacts and a branch or pull request.

The user should experience one coherent Auto Code workflow, even when multiple
underlying CLIs participate.

## Risks And Guardrails

| Risk | Why It Matters | Guardrail |
| --- | --- | --- |
| Thin wrapper trap | A list of CLI launch buttons does not create durable product value. | Keep Auto Code responsible for specs, routing, QA, policy, artifacts, and final handoff. |
| Security drift | Different CLIs have different command and file access models. | Enforce Auto Code-level worktree, approval, and audit policy around every runner. |
| Inconsistent output | CLIs emit different logs, summaries, and error formats. | Normalize through `RunnerResult` and require structured adapters for first-class runners. |
| False provider-agnostic claims | Some runners cannot support the same tools, MCP behavior, or sandbox semantics. | Use capability checks and clear degradation messages. |
| Maintenance burden | Deep integration with every CLI can become expensive. | Use support tiers and keep most tools behind generic CLI support until demand is proven. |
| Credential complexity | Each CLI has its own auth flow and storage assumptions. | Add setup checks, redacted diagnostics, and per-runner credential status. |

## Success Criteria

CLI runner support is successful when Auto Code can:

- Run the same spec workflow through at least two implementation runners.
- Use an independent review runner after implementation.
- Produce consistent artifacts regardless of runner choice.
- Clearly explain why a runner was selected or rejected.
- Preserve worktree isolation and approval policy across runners.
- Recover when a runner fails and try another compatible runner when policy
  allows it.
- Report changed files, commands, tests, review findings, and final status in a
  common schema.

## Recommended Next Steps

1. Define the `AgentRunner`, `ReviewRunner`, `RunnerCapabilities`, and
   `RunnerResult` interfaces.
2. Implement first-class adapters for Codex CLI and CodeRabbit CLI.
3. Add Gemini CLI and Aider adapters once the interface proves stable.
4. Keep Claude Code compatibility while removing assumptions that every runtime
   behaves like the current SDK path.
5. Add runner selection policy to the implementation plan stage.
6. Add documentation and UI/CLI setup checks for configured runners.
7. Add regression tests for runner selection, failure handling, review gating,
   and artifact normalization.

## Bottom Line

Supporting LLM CLIs is valuable because it turns Auto Code into the workflow
controller for agentic development. The product benefit is not "we support many
tools." The product benefit is that Auto Code can coordinate the right tool for
each phase while preserving governance, isolation, review, and repeatability.
