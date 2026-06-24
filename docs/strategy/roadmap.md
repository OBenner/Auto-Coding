# Auto Code — план развития (5 целей)

> Источник: стратегическое исследование рынка ИИ-кодинга и конкурентов (2026-06-24) + разведка фактического состояния кода.
> Контекст и конкурентный анализ — см. раздел «Позиционирование» ниже.

## Позиционирование (зачем эти цели)

Рынок ИИ-кодинга растёт (~$12–16 млрд, CAGR 27–37 %), но главная незакрытая боль — **доверие**: лишь ~29 % разработчиков доверяют выводу ИИ, ИИ создаёт в 1,3–1,7× больше критических багов. Пространство «автономных агентов» сжимается сверху (Claude Code/Anthropic, GitHub Copilot agent) и снизу (OpenHands).

**Наш ров — пересечение трёх вещей, которые почти никто не сочетает:**
1. spec-driven дисциплина,
2. замкнутый цикл «автономное исполнение → QA → фиксы» с изоляцией в worktree и явными ревью-гейтами,
3. open-source + self-hosted + мульти-провайдер (данные не покидают периметр).

Позиционирование: **«автономный кодер, которому можно доверять и которого можно запустить на своей инфраструктуре»**, с прицелом на регулируемый self-hosted энтерпрайз.

## Главный вывод разведки: что уже готово

| Цель | Готово в коде | Объём остатка | Ценность | Волна |
|---|---|---|---|---|
| **P3. Мульти-провайдер / автономность** | **~90 %** (уровни off/claude/safe/bold, evidence-gate, runtime-слой, Ollama — есть) | **S** | высокая (снимает зависимость от Anthropic + локальные модели) | **1** |
| **P5. Прозрачность стоимости** | **~70 %** (захват токенов, прайс-база и графики во фронте — есть, не связаны) | **S–M** | высокая (тревога из-за usage-pricing) | **1** |
| **P1. Слой доверия** | бэкенд ~60 %, **UI — 0 %** | **M** | **наивысшая (ров)** | **1** |
| **P2. GitHub App (issue→PR)** | **~75 % переиспользуемо** | **M–L** | высокая (дистрибуция) | **2** |
| **P4. Облако / команды** | каркас FastAPI + auth + agent_runner есть; мультиарендности — 0 | **L** | высокая (выручка/энтерпрайз) | **3** |

Объём: S/M/L — относительный размер работы (не время). По правилу проекта — без оценок в днях.

## Последовательность

- **Волна 1 (параллельно):** P3 (доделать автономность) · P5 (MVP стоимости) · P1 (слой доверия).
- **Волна 2:** P2 (GitHub App) — переиспользует CI/worktree/PR; в комментарий PR кладёт отчёт доверия из P1 (после P1).
- **Волна 3:** P4 (облако/команды) — самый большой объём; модель workspace аддитивна и может стартовать параллельно с Волной 1.
- **Стратегическая связка:** P3 (локальные модели) + P4 (self-hosted мультипользователь) = регулируемый энтерпрайз.

> ⚠️ Номера строк ниже — из автоматической разведки и могут «плыть». Перед правкой подтверждайте место по имени функции (через codegraph), а не по номеру строки.

---

## P1. Слой доверия (Trust Layer) — Волна 1, ров

**Итог:** каждая сборка выдаёт `verification-report.json` и видимый в UI отчёт: вердикт + оценка уверенности + прогнанные/прошедшие тесты + объяснение диффа + список «в чём агент не уверен» + флаг правок вне scope; история итераций QA — на таймлайне.

**Что уже есть:** `qa_signoff` в `implementation_plan.json`, история в `qa_iteration_history[]` (`apps/backend/qa/report.py`), `ArtifactManager` (`apps/backend/cli/artifacts.py`) пишет `artifacts/test-report.json`/`coverage-report.json`, парсер покрытия (`apps/backend/analysis/coverage_reporter.py`). **Нет:** уверенности/неопределённости, детекта out-of-scope и QA-экрана во фронте.

| # | Задача | Файлы | Критерий приёмки |
|---|---|---|---|
| T1 | `save_verification_report()` + сборка артефакта из уже известного (вердикт, тесты, дифф, итерация) | `cli/artifacts.py`; вызов из `run_qa_agent_session()` в `qa/reviewer.py` и `run_qa_fixer_session()` в `qa/fixer.py` | После каждой QA-сессии есть `artifacts/verification-report.json` с вердиктом и тестами |
| T2 | Детект правок вне scope: дифф изменённых файлов против `phases[].subtasks[].files_to_modify[]` | новый `qa/scope_check.py`, вызов в `qa/loop.py` | Правка файла не из плана попадает в `out_of_scope_edits` |
| T3 | Уверенность + неопределённость: маркеры `[CONFIDENCE: x]`/`[UNCERTAIN: …]` в `prompts/qa_reviewer.md` и `qa_fixer.md`, парсинг + привязка к пробелам покрытия | reviewer/fixer + схема отчёта | В отчёте есть confidence и пункты неопределённости из ответа агента и покрытия |
| T4 | **Первый QA-экран:** IPC-хендлер + React-компонент (датчик уверенности, разбивка тестов, неопределённость, out-of-scope, таймлайн итераций) + i18n (en+fr) | новый `apps/frontend/src/main/ipc-handlers/qa-handlers.ts`, новый `…/renderer/components/VerificationReportView.tsx`, локали | Открыв собранную спеку, вижу отчёт верификации |

**🚀 Начать с:** T1 в минимальной схеме (`verdict + tests_run + timestamp`).
**Риск:** confidence — самооценка модели; калибровать против покрытия/тестов, в UI показывать как «сигнал + доказательства».

---

## P5. Прозрачность стоимости — Волна 1, быстрый выигрыш

**Итог:** на спеку видно «сколько стоила сборка» (по фазам и ролям), работает лимит бюджета на спеку, простые подзадачи можно роутить на дешёвую модель.

**Что уже есть:** захват токенов по фазам (`apps/backend/core/token_stats.py`) + извлечение usage из SDK (`apps/backend/agents/session.py`); во фронте — прайс-база `shared/constants/model-costs.ts`, `CostComparison.tsx`, `CostBreakdownChart.tsx`, `ContextViewer.tsx`. Классы агрегации `apps/backend/analysis/model_usage_analytics.py` написаны, но не подключены.

| # | Задача | Файлы | Критерий приёмки |
|---|---|---|---|
| T1 | Надёжный захват usage + запись модели/провайдера в статистику | `agents/session.py`, `core/token_stats.py` (поля `model`, `provider`) | `token_stats.json` содержит токены + модель + провайдер по фазам |
| T2 | Подключить агрегацию: per-spec и проектный `.auto-claude/model_usage_summary.json` | `analysis/model_usage_analytics.py`, вызов после `save_token_stats()` | Считается стоимость по ролям и фазам |
| T3 | Дашборд: посчитать $ через `model-costs.ts`, показать (переиспользуя графики) + строку «Cost» в `ContextViewer.tsx` | `apps/frontend/src/main/ipc-handlers/token-stats-handler.ts` + компоненты | «Сборка стоила $X — планирование/код/QA …» |
| T4 | Бюджет-гард: лимит на спеку, останов/предупреждение при превышении | проверка в `qa/loop.py` и цикле сессий | Низкий лимит останавливает прогон с понятным сообщением |
| T5 *(позже)* | Роутинг дешёвой модели на тривиальные подзадачи | `phase_config.py` (`get_model_for_agent`/`lock_agent_model`) | Простые подзадачи идут на haiku, записано в статистике |

**🚀 Начать с:** T1.

---

## P3. Доделать мульти-провайдерную автономность — Волна 1, почти бесплатно

**Итог:** один тумблер `AUTO_CODE_AUTONOMY` (off/claude/safe/bold) реально управляет всеми агентами; не-Claude провайдеры доходят до паритета через evidence-gate; локальные модели (Ollama) — задокументированный «приватный» режим.

**Что уже есть (≈90 %):** `apps/backend/core/autonomy_level.py` (`resolve_autonomy_settings()`), `apps/backend/core/autonomy_policy.py` + gate `apps/backend/agents/runtime/direct_api_autonomy.py`, runtime-слой (capabilities/modes/adapters), реальный Ollama-адаптер. **Разрыв — три «проводки» + UX/доки.**

| # | Задача | Файлы | Критерий приёмки |
|---|---|---|---|
| T1 | ✅ **Уже реализовано.** Coder уважает уровень автономности | `agents/coder.py:1282–1296` + `agents/runtime/direct_api_autonomy.py:124` | `AUTO_CODE_AUTONOMY=claude` блокирует автономный direct-API coder; `safe` — через gate; `bold` — мимо gate (хардкод `=True` остался только в смоук-тесте `cli/provider_smoke_commands.py`) |
| T2 | Гейт для planner на не-Claude провайдерах | `agents/planner.py` | При `off` не-Claude planner блокируется |
| T3 | Фабрика принимает `autonomy_settings` и логирует уровень | `agents/runtime/adapters/__init__.py` (`create_runtime_session`) | Уровень автономности виден в логе сессии |
| T4 | Один тумблер в UI + вывод уровня в JSON | `cli/runtime_commands.py`, настройки фронта | UI показывает и задаёт один селектор автономности |
| T5 | Доки: вести с `AUTO_CODE_AUTONOMY`, 30+ переменных — в приложение | `guides/QUICK-START.md`, `docs/` | Quickstart: «поставь `safe` — готово» |
| T6 | Рецепт «данные не покидают периметр»: `safe` + `provider=ollama` | доки + проверка | Рабочий локальный рецепт задокументирован |

**🚀 Начать с:** T1 уже сделан — оставшийся разрыв это UX/наблюдаемость: T4 (один тумблер в UI + уровень в JSON) и T5 (доки ведут с `AUTO_CODE_AUTONOMY`).

---

## P2. GitHub App: issue → автономный PR — Волна 2, дистрибуция

**Итог:** назначаешь issue на Auto Code → он прогоняет спека→план→код→QA и открывает PR с приложенным отчётом доверия (P1).

**Что уже есть (~75 % переиспользуемо):** `runners/github/gh_client.py`, создание ветки/PR в `core/worktree.py` (`push_and_create_pr`), полный билд `handle_build_command()` в `cli/build_commands.py`, режим CI+JSON, проверка прав, каркас приёма вебхуков `integrations/webhooks/server.py`, `AutoFixProcessor` (issue→state).

| # | Задача | Файлы | Критерий приёмки |
|---|---|---|---|
| T1 | Auth GitHub App: installation-токены + проверка подписи вебхука | новый `integrations/github_app/auth.py` | Минтим installation-токен, верифицируем HMAC |
| T2 | Хендлер вебхука `issues.assigned` | новый `integrations/webhooks/handlers/github_app.py` | Назначение issue запускает обработчик |
| T3 | Issue→spec: из issue+контекста собрать спека-директорию | новый `runners/github/services/issue_to_spec.py` | Issue даёт валидные `spec.md` + план |
| T4 | Оркестрация билда (переиспользование) | `cli/build_commands.handle_build_command` + `core/worktree.push_and_create_pr` | Сквозняк issue→ветка→билд→PR |
| T5 | Комментарий-отчёт в PR (**зависит от P1**) + status check | новый `runners/github/services/pr_reporter.py` | В PR есть отчёт верификации и pass/fail-статус |
| T6 *(опц.)* | Эндпоинт-триггер билда | `apps/web-backend/api/routes/builds.py` | Внешний триггер работает |

**🚀 Начать с:** T1+T2 (единственный реально отсутствующий примитив).

---

## P4. Облако / команды — Волна 3, выручка/энтерпрайз

**Итог:** браузерный многопользовательский доступ с изоляцией по workspace и ролями (owner/editor/viewer), историей запусков и командными процессами.

**Что уже есть:** FastAPI `apps/web-backend/main.py` (specs/tasks/agents/auth/users/git/files/usage/websocket); реальные регистрация/логин (JWT, bcrypt), `agent_runner` реально зовёт `run_autonomous_agent`, websocket-броадкаст, ORM `User`/`GitRepository`, миграции, web-frontend. **Нет:** мультиарендности, изоляции по пользователю, персистентности запусков, использования OAuth.

| # | Задача | Файлы | Критерий приёмки |
|---|---|---|---|
| T1 | Модель Workspace + роли + проверка доступа | новый `api/models/workspace.py`, миграции 003–004, новый `core/permissions.py` | Пользователи входят в workspace с ролями |
| T2 | Изоляция исполнения по пользователю/workspace | `services/agent_runner.py`, новый `services/workspace_service.py` | Пользователь A не видит/не запускает спеки B |
| T3 | Персистентность запусков | новый `api/models/agent_execution.py` + миграция | После рестарта история сохранена |
| T4 | Спеки: ФС — источник истины + ORM как кэш/аудит | `api/models/spec.py` + миграция 005 | Правки спек аудируются, web читает через API |
| T5 | Реалтайм + терминал в браузере | `api/websocket.py` + web-компонент терминала | Живой вывод агента в браузере |
| T6 | OAuth-привязка репозиториев | `core/oauth.py` + коллбэки | Подключил репо → агент в нём работает |
| T7 | Командные процессы: инвайты/участники, общие спеки/ревью | новый `api/routes/workspaces.py` | Можно пригласить коллегу в workspace |

**🚀 Начать с:** T1 (аддитивно, разблокирует остальное).
**Риск:** миграция спек ФС→БД; смягчение — на первом этапе ФС остаётся источником истины.

---

## Прогресс ([PR #361](https://github.com/OBenner/Auto-Coding/pull/361))

**Волна 1 — закрыта** (бэкенд: 28 юнит-тестов зелёные; фронтенд: `tsc --noEmit` зелёный):

- ✅ **P3·T1** — coder уважает `AUTO_CODE_AUTONOMY` (оказался уже реализован).
- ✅ **P1·T1 / T1-wire** — контракт `verification-report.json` + запись на каждой сборке (`cli/artifacts.py`, `cli/build_commands.py`).
- ✅ **P1·T2** — детект правок вне scope (`qa/scope_check.py`) → `out_of_scope_edits`.
- ✅ **P1·T3** — `confidence` + `uncertainty` через SDK- и runtime-путь (`qa/reviewer.py`, промпт, merge-санитайзинг).
- ✅ **P5·T1** — модель/провайдер по фазам в `token_stats.json` (`core/token_stats.py`, `agents/session.py`).
- ✅ **P3·T5** — доки ведут с `AUTO_CODE_AUTONOMY` (`guides/CLI-USAGE.md`, ADR-006 → Accepted).
- ✅ **P1·T4** — QA-экран отчёта доверия в task overview (reader + IPC + `VerificationReportPanel`, i18n en/fr).
- ✅ **P3·T4** — тумблер автономности в настройках → инжектит `AUTO_CODE_AUTONOMY` в окружение сборки (явный env приоритетнее).

Отчёт доверия теперь несёт: **вердикт · тесты · дифф · out-of-scope · confidence · uncertainty** — и виден в UI.

**Дальше отдельными PR:** P2 (GitHub App), P4 (облако/команды).

Каждая задача shippable отдельно и тянет тесты (`apps/backend/.venv/bin/pytest tests/<файл>` — точечно).
