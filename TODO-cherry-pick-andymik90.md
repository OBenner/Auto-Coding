# Cherry-pick from AndyMik90/Auto-Claude (с 12 февраля 2026)

Источник: https://github.com/AndyMik90/Auto-Claude/commits/develop/
Remote: `andymik90` (уже добавлен в этом worktree)

## Выполнено

- [x] **PR #1834** — FalkorDB → LadybugDB migration (коммит `2f59d196`)
- [x] **PR #1841** — Greenfield project spec creation crash (коммит `1889f145`)
- [x] **PR #1853** — QA validation deadlock fix (коммит `5dc52b0a`)
- [x] **PR #1844** — Planning crash + resume recovery (коммит `7a61e863`)
- [x] **PR #1847** — Self-healing file paths in coder pipeline (коммит `0896bca4`)
- [~] **PR #1840** — SKIPPED: не применим, наш форк не имеет TaskStateManager/XState

## Осталось — Категория 1: Критичные баг-фиксы бэкенда
- [x] **PR #1797 + #1806 + #1857** — PR review stability chain: three-tier recovery, Pydantic schema normalization, file/line preservation in recovery. Applied as combined changeset. All 2605 tests pass.

## Осталось — Категория 2: Баг-фиксы fullstack/frontend
- [x] **PR #1813** — OOM prevention, orphaned agents: LadybugDB lock retry, recovery time-window, attempt trimming, OOM log caps, circuit breaker, agent cleanup on close. All 2631 tests pass.
- [x] **PR #1843** — Windows: Claude CLI not found — backend only: CLAUDE.md system prompt truncation for Windows CreateProcessW limit. Frontend PATH normalization already handled differently in our fork.
- [x] **PR #1852** — Dismissed PR review findings visible in UI: active vs dismissed separation in orchestrator, verdict from active only, UI with disputed badges/section, i18n keys.
- [x] **PR #1836** — Blank terminals after project switch: force SIGWINCH on same-dimension resize, skip buffer replay for Claude-mode terminals on remount.
- [~] **PR #1842** — SKIPPED: FileWatcher class does not exist in our fork
- [~] **PR #1833** — SKIPPED: depends on taskStateManager/XState which our fork does not have
- [x] **PR #1793** — PR review hangs in bundled app: use getEffectiveSourcePath() and managed Python env in subprocess-runner.ts

## Осталось — Категория 3: Тесты (deferred — require extensive per-test investigation due to codebase divergence)

- [ ] **PR #1772** — 100% test coverage для backend CLI commands. 12,500+ lines, 13 new test files. Source also includes small bug fixes (BuildState enum, QA status detection). Ветка: `tests-cli-commands`
- [ ] **PR #1779** — Backend agent test coverage → 94%. ~2,800 lines, QA fixer/reviewer tests, spec validator tests. Ветка удалена

## Осталось — Категория 4: Фичи (нужна адаптация)

- [~] **PR #1832** — SKIPPED: our fork lacks DependencyStrategy infrastructure (only has node_modules symlinks)
- [ ] **PR #1831** — WebGL context manager для терминалов. 20 files, +774/-131. Ветка: `feature/webgl-context-management`
- [ ] **PR #1821** — Screenshot paste в чат. 14 files, +598/-94. Ветка: `auto-claude/224-add-screenshot-paste-capability-to-chat`
- [~] **PR #1820** — SKIPPED: XState PR review refactor, not applicable
- [ ] **PR #1819** — Account-aware terminal sessions. Ветка: `auto-claude/229-implement-account-aware-terminal-session-persisten`
- [x] **PR #1818** — Fix mark as done on task modal: add keepWorktree option to updateTaskStatus, pass from WorkspaceMessages
- [ ] **PR #1817** — Archive button для done tasks. 11 files, +301/-84. Ветка: `auto-claude/226-add-archive-button-to-done-tasks`
- [~] **PR #1816** — SKIPPED: Remove deprecated TaskStateMachine (XState), not applicable
- [ ] **PR #1829** — Bulk delete/archive chat history. 15 files, +909/-110. Ветка: `auto-claude/225-bulk-delete-and-archive-chat-history`
- [~] **PR #1815** — SKIPPED: Refactor roadmap tasks → XState, not applicable
- [ ] **PR #1814** — Manual competitor в roadmap. 18 files, +1037/-152. Ветка: `auto-claude/220-add-manual-competitor-functionality-in-roadmap`
- [ ] **PR #1790** — User-friendly GitHub API errors. 11 files, +2182/-15. Ветка удалена
- [ ] **PR #1794** — Unified profile swapping. 10 files, +638/-6. Ветка удалена

## Заметки

- Codebases сильно разошлись: 361 коммитов у них / 423 у нас, общий предок `1e72c8d7`
- Cherry-pick невозможен, нужно читать диффы и применять вручную
- Для PR с удалёнными ветками брать дифф через: `gh api repos/AndyMik90/Auto-Claude/pulls/{номер}/files`
- Remote `andymik90` уже добавлен, доступные ветки уже зафетчены
- Backend-изменения переносятся легче, frontend — может требовать адаптацию из-за XState и другой архитектуры
