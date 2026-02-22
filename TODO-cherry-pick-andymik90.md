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
- [ ] **PR #1813** — OOM prevention, orphaned agents при overnight builds. 896+/44-, 11 files. Ветка удалена
- [ ] **PR #1843** — Windows: Claude CLI not found (PATH overwrite, prompt size, cwd). 326+/24-, 8 files. Ветка удалена
- [ ] **PR #1842** — Watch worktree path для implementation_plan.json. 504+/56-, 4 files. Ветка удалена
- [ ] **PR #1833** — Kanban stuck task state sync. 129+/21-, 8 files. Ветка: `fix/kanban-stuck-task`
- [ ] **PR #1836** — Blank terminals после project switch. Ветка: `fix/terminal-blank-project-switch`
- [ ] **PR #1852** — Dismissed PR review findings видны в UI. Ветка удалена
- [ ] **PR #1793** — PR review зависает в bundled app. Ветка удалена

## Осталось — Категория 3: Тесты

- [ ] **PR #1772** — 100% test coverage для backend CLI commands. Ветка: `tests-cli-commands`
- [ ] **PR #1779** — Backend agent test coverage → 94%. Ветка удалена

## Осталось — Категория 4: Фичи (нужна адаптация)

- [ ] **PR #1832** — Symlink Python venvs в worktrees. Ветка: `terminal/improve-worktree-venv`
- [ ] **PR #1831** — WebGL context manager для терминалов. Ветка: `feature/webgl-context-management`
- [ ] **PR #1821** — Screenshot paste в чат. Ветка: `auto-claude/224-add-screenshot-paste-capability-to-chat`
- [ ] **PR #1820** — Refactor PR review → XState. Ветка: `auto-claude/221-refactor-github-pr-review-with-xstate`
- [ ] **PR #1819** — Account-aware terminal sessions. Ветка: `auto-claude/229-implement-account-aware-terminal-session-persisten`
- [ ] **PR #1818** — Fix mark as done on task modal. Ветка: `auto-claude/227-fix-mark-as-done-on-task-modal`
- [ ] **PR #1817** — Archive button для done tasks. Ветка: `auto-claude/226-add-archive-button-to-done-tasks`
- [ ] **PR #1816** — Remove deprecated TaskStateMachine. Ветка: `auto-claude/223-remove-deprecated-taskstatemachine-class`
- [ ] **PR #1829** — Bulk delete/archive chat history. Ветка: `auto-claude/225-bulk-delete-and-archive-chat-history`
- [ ] **PR #1815** — Refactor roadmap tasks → XState. Ветка: `auto-claude/222-refactor-roadmap-tasks-with-xstate`
- [ ] **PR #1814** — Manual competitor в roadmap. Ветка: `auto-claude/220-add-manual-competitor-functionality-in-roadmap`
- [ ] **PR #1790** — User-friendly GitHub API errors. Ветка удалена
- [ ] **PR #1794** — Unified profile swapping. Ветка удалена

## Заметки

- Codebases сильно разошлись: 361 коммитов у них / 423 у нас, общий предок `1e72c8d7`
- Cherry-pick невозможен, нужно читать диффы и применять вручную
- Для PR с удалёнными ветками брать дифф через: `gh api repos/AndyMik90/Auto-Claude/pulls/{номер}/files`
- Remote `andymik90` уже добавлен, доступные ветки уже зафетчены
- Backend-изменения переносятся легче, frontend — может требовать адаптацию из-за XState и другой архитектуры
