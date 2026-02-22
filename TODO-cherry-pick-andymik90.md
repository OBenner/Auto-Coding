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

## Осталось — Категория 3: Тесты (partially applied)

- [x] **PR #1772** (source fixes) — BuildState.RUNNING→BUILDING bug fix, batch_commands QA status detection, .gitignore updates, GitLab API error class, paginated notes fetching (коммиты `3497b85b`, `0cddf898`). *New test files NOT applied — 13 files, 12,500+ lines require per-test investigation.*
- [x] **PR #1779** (Windows compat + validators) — test_ci_discovery, test_security_scanner, test_service_orchestrator, test_validation_strategy Path.exists mocking, conftest.py new mock modules (коммит `0cddf898`). 3 validator test files added (79 tests, коммит `b6804b92`). *QA fixer/reviewer tests NOT applied — depend on core.error_utils which doesn't exist in our fork.*

## Осталось — Категория 4: Фичи (нужна адаптация)

- [~] **PR #1832** — SKIPPED: our fork lacks DependencyStrategy infrastructure (only has node_modules symlinks)
- [~] **PR #1831** — SKIPPED: no terminal infrastructure in our fork (useXterm.ts, terminal-manager.ts, webgl-context-manager.ts all missing)
- [x] **PR #1821** (backend only) — insights_runner.py image/screenshot support: load_images_from_manifest() with path traversal protection, MIME validation, --images-file CLI arg (коммит `3497b85b`). *Frontend Insights components skipped — not in our fork.*
- [~] **PR #1820** — SKIPPED: XState PR review refactor, not applicable
- [~] **PR #1819** — SKIPPED: no terminal infrastructure or state-machines in our fork
- [x] **PR #1818** — Fix mark as done on task modal: add keepWorktree option to updateTaskStatus, pass from WorkspaceMessages
- [~] **PR #1817** — SKIPPED: no Roadmap.tsx component in our fork
- [~] **PR #1816** — SKIPPED: Remove deprecated TaskStateMachine (XState), not applicable
- [~] **PR #1829** — SKIPPED: no ChatHistorySidebar or Insights components in our fork
- [~] **PR #1815** — SKIPPED: Refactor roadmap tasks → XState, not applicable
- [x] **PR #1814** (backend only) — competitor_analyzer.py manual competitor preservation: dedicated manual_competitors.json, merge-back logic, dedup by ID (коммит `3497b85b`). *Frontend Roadmap components skipped — not in our fork.*
- [~] **PR #1790** — SKIPPED: no GitHub Issues components (GitHubErrorDisplay, IssueList) in our fork
- [~] **PR #1794** — SKIPPED: no profile-scorer.ts or unified-account.ts in our fork

## Осталось — Категория 5: Утилитарные модули и QA тесты (WIP)

Перенос утилитарных модулей из AndyMik90 форка для разблокировки QA тестов.

**Готово (не закоммичено):**
- [x] `apps/backend/core/error_utils.py` — NEW: is_tool_concurrency_error, is_rate_limit_error, is_authentication_error, safe_receive_messages
- [x] `apps/backend/agents/base.py` — MODIFIED: retry constants, pause file constants, sanitize_error_message()
- [x] `apps/backend/security/tool_input_validator.py` — MODIFIED: TOOL_REQUIRED_KEYS, validate_tool_input(), get_safe_tool_input()
- [x] `apps/backend/debug.py` — MODIFIED: comment rename Auto-Code → Auto-Claude
- [x] `apps/backend/core/debug.py` — MODIFIED: comment rename + Python 3.12 compat (isinstance tuple syntax)
- [x] `tests/conftest.py` — MODIFIED: added mock entries for new modules
- [x] `tests/qa_test_helpers.py` — NEW: shared QA test helpers (adapted for our fork — stub qa package to bypass circular imports)

**WIP (тесты не проходят, нужна доработка):**
- [ ] `tests/test_qa_fixer.py` — NEW: 12/14 тестов падают — `patch('qa.fixer.get_iteration_history')` не работает т.к. fixer использует lazy import `from .report import get_iteration_history` внутри функции. Нужно патчить `qa.report.get_iteration_history` или использовать другой подход к мокам.
- [ ] `tests/test_qa_reviewer.py` — NEW: 3/13 тестов падают — memory integration тесты: mock объекты не подхватываются (нужно использовать `patch.object` или патчить реальные модули).

**Резюме проблем с QA тестами:**
1. Наш форк использует `RecoveryManager`, iteration history, coverage validation — которых нет в оригинальных тестах
2. Fixer делает lazy import `from .report import get_iteration_history` внутри `run_qa_fixer_session()` — patch по `qa.fixer.get_iteration_history` не работает
3. Reviewer вызывает `run_coverage_validation()` перед сессией — нужен отдельный мок
4. Оба модуля возвращают 2-tuple (status, text), а не 3-tuple как в оригинале
5. ErrorDetection тесты убраны — наши модули не используют `is_rate_limit_error` напрямую

## Итоговая сводка

**Применено: 16 PRs** (коммиты в ветке `worktree-cherry-pick-andymik90`):
- PR #1834, #1841, #1853, #1844, #1847 — критичные backend баги
- PR #1797+#1806+#1857 — PR review stability chain (combined)
- PR #1813, #1843, #1852, #1836 — fullstack/frontend баги (bulk commit)
- PR #1793 — PR review subprocess path fix
- PR #1818 — keepWorktree option for task done
- PR #1772 (source fixes) — BuildState bug, QA status, GitLab API improvements
- PR #1779 (Windows compat) — test Path.exists mocking, conftest module isolation
- PR #1814 (backend only) — competitor_analyzer manual competitor preservation
- PR #1821 (backend only) — insights_runner image/screenshot support

**Дополнительно перенесено (утилитарные модули):**
- core/error_utils.py, agents/base.py, security/tool_input_validator.py, debug.py, core/debug.py
- Эти модули разблокировали 165 ранее падавших тестов (2710 → 2875)

**Пропущено: 13 PRs** (компоненты отсутствуют в нашем форке):
- 5 PR — зависят от XState/TaskStateManager (#1840, #1833, #1820, #1816, #1815)
- 1 PR — FileWatcher (#1842)
- 1 PR — DependencyStrategy (#1832)
- 3 PR — Terminal infrastructure (#1831, #1819)
- 1 PR — Chat/Insights frontend (#1829)
- 1 PR — GitHub Issues components (#1790)
- 1 PR — Profile scorer (#1794)

**Не перенесено (слишком сильное расхождение или отсутствие зависимостей):**
- PR #1772 — 13 new CLI test files (12,500+ строк) — массовый перенос нецелесообразен
- PR #1817 — Roadmap frontend (нет компонентов)
- Все XState/terminal/Insights PRs (см. список пропусков выше)

## Заметки

- Codebases сильно разошлись: 361 коммитов у них / 423 у нас, общий предок `1e72c8d7`
- Cherry-pick невозможен, нужно читать диффы и применять вручную
- Для PR с удалёнными ветками брать дифф через: `gh api repos/AndyMik90/Auto-Claude/pulls/{номер}/files`
- Remote `andymik90` уже добавлен, доступные ветки уже зафетчены
- Backend-изменения переносятся легче, frontend — может требовать адаптацию из-за XState и другой архитектуры
- Основная причина пропуска: наш форк не имеет terminal infrastructure (xterm), Insights/Chat UI, Roadmap UI, state-machines, которые есть в AndyMik90 форке
