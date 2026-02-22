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
- [~] **PR #1831** — SKIPPED: no terminal infrastructure in our fork (useXterm.ts, terminal-manager.ts, webgl-context-manager.ts all missing)
- [~] **PR #1821** — SKIPPED: no Insights/chat components in our fork (Insights.tsx, insights-store.ts, insights/ directory all missing)
- [~] **PR #1820** — SKIPPED: XState PR review refactor, not applicable
- [~] **PR #1819** — SKIPPED: no terminal infrastructure or state-machines in our fork
- [x] **PR #1818** — Fix mark as done on task modal: add keepWorktree option to updateTaskStatus, pass from WorkspaceMessages
- [~] **PR #1817** — SKIPPED: no Roadmap.tsx component in our fork
- [~] **PR #1816** — SKIPPED: Remove deprecated TaskStateMachine (XState), not applicable
- [~] **PR #1829** — SKIPPED: no ChatHistorySidebar or Insights components in our fork
- [~] **PR #1815** — SKIPPED: Refactor roadmap tasks → XState, not applicable
- [~] **PR #1814** — SKIPPED: no Roadmap components or roadmap runner in our fork
- [~] **PR #1790** — SKIPPED: no GitHub Issues components (GitHubErrorDisplay, IssueList) in our fork
- [~] **PR #1794** — SKIPPED: no profile-scorer.ts or unified-account.ts in our fork

## Итоговая сводка

**Применено: 11 PRs** (коммиты в ветке `worktree-cherry-pick-andymik90`):
- PR #1834, #1841, #1853, #1844, #1847 — критичные backend баги
- PR #1797+#1806+#1857 — PR review stability chain (combined)
- PR #1813, #1843, #1852, #1836 — fullstack/frontend баги (bulk commit)
- PR #1793 — PR review subprocess path fix
- PR #1818 — keepWorktree option for task done

**Пропущено: 16 PRs** (компоненты отсутствуют в нашем форке):
- 4 PR — зависят от XState/TaskStateManager (#1840, #1833, #1820, #1816, #1815)
- 1 PR — FileWatcher (#1842)
- 1 PR — DependencyStrategy (#1832)
- 3 PR — Terminal infrastructure (#1831, #1819, #1836-terminal part)
- 2 PR — Insights/Chat (#1821, #1829)
- 2 PR — Roadmap (#1817, #1814)
- 1 PR — GitHub Issues components (#1790)
- 1 PR — Profile scorer (#1794)

**Отложено: 2 PRs** (тесты, требуют ручного анализа):
- PR #1772 — 12,500+ строк тестов CLI commands
- PR #1779 — ~2,800 строк тестов агентов

## Заметки

- Codebases сильно разошлись: 361 коммитов у них / 423 у нас, общий предок `1e72c8d7`
- Cherry-pick невозможен, нужно читать диффы и применять вручную
- Для PR с удалёнными ветками брать дифф через: `gh api repos/AndyMik90/Auto-Claude/pulls/{номер}/files`
- Remote `andymik90` уже добавлен, доступные ветки уже зафетчены
- Backend-изменения переносятся легче, frontend — может требовать адаптацию из-за XState и другой архитектуры
- Основная причина пропуска: наш форк не имеет terminal infrastructure (xterm), Insights/Chat UI, Roadmap UI, state-machines, которые есть в AndyMik90 форке
