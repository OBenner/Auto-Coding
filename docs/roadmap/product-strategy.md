# Product Strategy and Development Roadmap

This document summarizes the strategic case for continuing Auto Code and turns it
into a product roadmap. It is intentionally grounded in the current market
direction and in the product shape already present in the repository.

## Executive Summary

Auto Code is worth continuing if it is positioned as a governed, self-hostable
agentic software engineering workflow rather than as another IDE autocomplete or
chat assistant.

The market is moving from inline suggestions toward delegated engineering work:
agents that take issues or task descriptions, work in isolated environments,
produce reviewed branches or pull requests, and leave an audit trail. Auto Code
already has the right product skeleton for this direction:

- Multi-agent workflow: spec creation, planning, coding, QA review, and QA fix.
- Isolated git worktrees for implementation.
- CLI and desktop workflows.
- Memory, integrations, plugin scaffolding, and enterprise/security modules.
- Headless operation for CI/CD-style use cases.

The main strategic risk is not lack of demand. The risk is overclaiming maturity
before the core workflow, runtime abstraction, governance, and operational
observability are reliable enough to earn trust.

## Market Signals

Current market signals support continued investment:

- AI coding tools are broadly adopted, but trust remains weak. Stack Overflow's
  2025 Developer Survey reports that 84% of developers use or plan to use AI
  tools, while 46% do not trust AI tool accuracy and 45% report that debugging
  AI-generated code is time-consuming.
- Gartner predicts that by 2028, 90% of enterprise software engineers will use
  AI code assistants, and that developers will shift from implementation toward
  orchestration, problem solving, system design, and quality control.
- Gartner also predicts that task-specific AI agents will appear in up to 40%
  of enterprise applications by the end of 2026, and that agent ecosystems will
  become a meaningful enterprise software pattern.
- GitHub, OpenAI, and Anthropic are converging on the same product direction:
  asynchronous agents, isolated execution, pull-request workflows, policy
  controls, usage analytics, and compliance visibility.
- Market research estimates the global AI code assistants market at USD 8.5B in
  2025 with projected growth to USD 42.9B by 2033.

These signals point to a market that wants productivity, but will increasingly
buy trust, control, and workflow fit.

## Strategic Positioning

### Recommended Position

Auto Code should be positioned as:

> A self-hostable agentic software engineering control plane that turns tasks
> into reviewed branches through governed multi-agent workflows.

This position avoids direct competition with IDE-first assistants and focuses on
the areas where Auto Code can be meaningfully different:

- Self-hosted and local-first operation.
- Transparent agent sessions and reviewable outputs.
- Explicit spec, plan, implementation, QA, and fix stages.
- Secure worktree isolation.
- Model/provider flexibility where capabilities allow it.
- Enterprise controls: audit logs, policy, approvals, cost visibility, and
  integration with existing engineering systems.

### Primary Users

The strongest early users are:

- Senior developers and small teams that want to delegate scoped engineering
  tasks without losing control of their codebase.
- Engineering managers who want repeatable AI-assisted delivery workflows, not
  one-off prompt sessions.
- Platform and DevEx teams that need a self-hostable agent layer with policy,
  observability, and integration hooks.
- Regulated or security-conscious teams that cannot rely only on opaque hosted
  coding agents.

### What Auto Code Should Not Try To Be

Auto Code should not compete primarily as:

- An IDE autocomplete product.
- A general chatbot.
- A hosted-only replacement for GitHub Copilot, Cursor, Codex, or Claude Code.
- A "fully autonomous developer" that bypasses human review.

The durable wedge is governed delegation, not raw code generation.

## Reality Check

This section separates product claims by maturity level. The categories should
be updated as implementation and validation improve.

### Ready To Emphasize

- Multi-agent software delivery pipeline.
- Git worktree isolation.
- CLI usage for task/spec execution.
- Desktop app workflow.
- QA-oriented loop with reviewer/fixer roles.
- GitHub/GitLab/Linear integration direction.
- Cross-platform intent and CI coverage.

### Experimental Or Needs Stronger Proof

- Multi-provider runtime beyond the primary agent SDK path.
- Plugin marketplace and third-party plugin contracts.
- Enterprise mode as a consistently enforced product surface.
- Prediction/risk intelligence as an orchestrator-level decision engine.
- Cloud-hosted multi-user deployment.
- Long-running autonomous CI/CD operation.

### Claims To Avoid Until Hardened

- "Production-ready cloud-hosted option" unless deployment, auth, tenancy,
  observability, and upgrade paths are validated.
- "Provider-agnostic full agent runtime" unless non-primary providers support
  the required tool, MCP, security, and session semantics.
- "Agents learn from every run" unless memory retrieval measurably changes
  future planning or implementation behavior.
- "Enterprise-ready" unless policy enforcement, audit, RBAC, and admin controls
  are active in the main runtime path.

## Product Principles

1. Trust before autonomy.
   Every autonomous action should be inspectable, explainable, and reversible.

2. Branches and pull requests are the product boundary.
   The best output is not a chat transcript; it is a small, reviewed, tested
   change set.

3. Human approval is a feature.
   High-quality agentic development keeps humans in control of risk, scope, and
   merge decisions.

4. Capabilities should be explicit.
   Providers, tools, MCP servers, and plugins should declare what they can and
   cannot safely do.

5. Self-hosting must be boring.
   A self-hosted product wins only when installation, upgrades, logs, secrets,
   and backups are predictable.

6. Observability is part of the agent loop.
   A failed run should create useful data for the next run, not just a support
   problem.

## Roadmap

### Phase 1: Core Workflow Truth

Goal: make the main task-to-branch flow reliable, demoable, and honestly
documented.

Key outcomes:

- One canonical happy path: task description to spec, implementation, tests, QA,
  and reviewable branch.
- Product documentation marks each major capability as ready, experimental, or
  planned.
- Agent run artifacts are standardized: spec, implementation plan, changed
  files, commands, test results, QA report, and final review summary.
- Failure states are explicit and recoverable.
- The README and guides stop implying maturity for capabilities that are still
  scaffolding.

Recommended work:

- Add a product capability matrix.
- Add a run artifact schema.
- Add smoke tests for the canonical task-to-branch flow.
- Add sample demo tasks that are stable across platforms.
- Add acceptance criteria for when a feature can be advertised as ready.

### Phase 2: Trust, Security, And Auditability

Goal: make agent behavior inspectable and policy-controlled.

Key outcomes:

- Every agent session has an audit trail: prompt, context, tools, commands,
  file edits, test output, and approvals.
- Command execution policy is visible and configurable.
- Worktree isolation is surfaced as a product feature, not just an internal
  implementation detail.
- Risky actions require approval gates.
- Security failures are reported in a format that is useful to humans and CI.

Recommended work:

- Build a unified audit event model.
- Add policy profiles for local, team, and restricted environments.
- Add approval gates for shell commands, network access, file scopes, and CI
  execution.
- Add a security dashboard or CLI report.
- Add regression tests for policy enforcement.

### Phase 3: Runtime And Provider Architecture

Goal: make provider support honest, capability-aware, and safe.

Key outcomes:

- The primary full-agent runtime is separated from generic text/tool provider
  runtimes.
- Provider capabilities are declared and checked before use.
- Model routing is driven by task type, risk, capability, and cost.
- Unsupported features degrade clearly instead of silently pretending to work.
- Provider-specific security gaps are documented and guarded.

Recommended work:

- Define a runtime/session interface for agents.
- Introduce provider capability declarations.
- Implement fallback behavior with clear limits.
- Add tests for provider/model mismatch, unsupported capability paths, and
  explicit model precedence.
- Keep full MCP/tool execution only where the runtime can enforce the required
  security model.

### Phase 4: Self-Hosted Team Product

Goal: turn Auto Code from a powerful local tool into a manageable team system.

Key outcomes:

- Single-node self-hosted deployment is reliable before broader Kubernetes
  positioning.
- Authentication, secrets, project access, and retention policies are explicit.
- Team administrators can view usage, costs, run status, failures, and risky
  actions.
- GitHub/GitLab issue-to-PR workflows are repeatable.
- Upgrade and backup paths are documented.

Recommended work:

- Harden Docker Compose deployment before expanding cloud claims.
- Add org/project/user concepts where needed.
- Add OIDC/SSO path after the basic auth model is stable.
- Add usage and cost reporting per project and user.
- Add admin-visible retention controls for prompts, logs, artifacts, and memory.

### Phase 5: Extensibility And Integrations

Goal: make extensions useful without weakening security or reliability.

Key outcomes:

- Plugin lifecycle, permissions, and compatibility contracts are enforced.
- Built-in integrations are treated as examples of the public extension model.
- Third-party plugins can be tested and verified before being trusted.
- UI extensions are constrained enough to keep the desktop app stable.

Recommended work:

- Add plugin smoke tests.
- Add plugin permission validation to the main runtime path.
- Add plugin version compatibility checks.
- Create reference plugins for issue trackers, observability tools, and custom
  review policies.
- Document the difference between project plugins, user plugins, and trusted
  built-ins.

### Phase 6: Learning And Risk Intelligence

Goal: make memory and prediction influence real orchestration decisions.

Key outcomes:

- Memory retrieval changes future planning in measurable ways.
- Risk prediction influences QA depth, test selection, and approval gates.
- Repeated failures become actionable project knowledge.
- The system can explain why it chose a plan, model, provider, or QA strategy.

Recommended work:

- Add metrics for memory hit rate and usefulness.
- Connect prediction outputs to orchestrator decisions.
- Store rejected QA patterns and use them in future planning.
- Add risk-based test recommendations.
- Add "why this plan" explanations to implementation plans.

## Success Metrics

Track metrics that reflect trust and delivery quality:

- Task-to-reviewable-branch success rate.
- QA rejection rate and top rejection categories.
- Test pass rate before and after QA fixer loops.
- Human intervention count per task.
- Average number of changed files per task.
- Rollback/discard rate.
- Cost per completed task.
- Provider fallback rate.
- Policy violation rate.
- Repeat failure rate by project and task type.

Avoid vanity metrics as primary success indicators:

- Generated lines of code.
- Number of agents spawned.
- Number of model calls.
- Number of plugins listed but not used.

## Continue, Pivot, Or Stop Criteria

Continue when:

- The canonical workflow reliably produces reviewable branches.
- Users trust the generated pull requests enough to review them seriously.
- Audit logs make failures easier to debug.
- Self-hosted users can run the product without bespoke support.

Pivot when:

- Users like the UI but do not trust autonomous changes.
- The core value is mostly task planning, not implementation.
- Enterprise users only want audit/policy around existing agents.
- Provider differences make full multi-runtime support too expensive to
  maintain.

Stop or narrow scope when:

- Most agent runs require more manual repair than they save.
- Security and policy enforcement cannot be made reliable.
- The product cannot produce a clear advantage over hosted agents for any
  specific user segment.
- Documentation and implementation remain materially out of sync.

## References

- Stack Overflow 2025 Developer Survey:
  https://stackoverflow.co/company/press/archive/stack-overflow-2025-developer-survey/
- Gartner, Top Strategic Trends in Software Engineering for 2025 and Beyond:
  https://www.gartner.com/en/newsroom/press-releases/2025-07-01-gartner-identifies-the-top-strategic-trends-in-software-engineering-for-2025-and-beyond
- Gartner, Task-Specific AI Agents in Enterprise Applications:
  https://www.gartner.com/en/newsroom/press-releases/2025-08-26-gartner-predicts-40-percent-of-enterprise-apps-will-feature-task-specific-ai-agents-by-2026-up-from-less-than-5-percent-in-2025
- Grand View Research, AI Code Assistants Market:
  https://www.grandviewresearch.com/industry-analysis/ai-code-assistants-market-report
- GitHub Copilot Coding Agent:
  https://github.com/newsroom/press-releases/coding-agent-for-github-copilot
- OpenAI Codex:
  https://openai.com/index/introducing-codex/
- Anthropic Claude Code for Team and Enterprise:
  https://www.anthropic.com/news/claude-code-on-team-and-enterprise
