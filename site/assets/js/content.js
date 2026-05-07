const REPO_BASE = "https://github.com/OBenner/Auto-Coding/blob/develop/";

window.AUTO_CODE_DOCS = {
  locales: {
    ru: {
      ui: {
        brandOverline: "Product docs",
        brandTitle: "Auto Code",
        languageLabel: "Язык",
        searchLabel: "Поиск",
        searchPlaceholder: "runtime, Codex CLI, QA, настройки...",
        heroEyebrow: "Open-source · Agentic engineering platform",
        heroTitle: "Идею — в ветку.\u00A0Без чёрных ящиков.",
        heroLead:
          "Опишите задачу — Auto Code запускает Planner, Coder и QA в изолированном worktree и отдаёт вам diff, логи и артефакты для review.",
        navEmpty: "Разделы не найдены.",
        sourceLabel: "Источник",
        roadmapUpdated: "Снимок документации проекта: 2026-05-02"
      },
      heroActions: [
        { label: "Quick start", href: `${REPO_BASE}guides/QUICK-START.md` },
        { label: "Runtime docs", href: `${REPO_BASE}docs/architecture/provider-runtime-modes.md` },
        { label: "Библиотека docs", href: "#library" }
      ],
      productSignal: {
        title: "Describe -> Spec -> Agents -> QA -> Review",
        rows: [
          ["Start with intent", "Plain-language task becomes requirements, context and an implementation plan"],
          ["Run controlled agents", "Planner, coder and QA roles execute inside an isolated worktree"],
          ["Choose runtime", "Claude SDK, Codex CLI and limited provider modes are explicit, not hidden"],
          ["Ship with evidence", "Diff, logs, QA report and artifacts are ready for human review"]
        ]
      },
      appMap: {
        title: "Что уже умеет Auto Code",
        subtitle: "Реальные возможности проекта: от постановки задачи до проверенной ветки, артефактов и runtime-выбора.",
        items: [
          {
            label: "Spec pipeline",
            title: "Превращает задачу в понятную спецификацию",
            text: "Интерактивный spec runner собирает требования, контекст проекта, acceptance criteria и планирует сложность работы.",
            source: "apps/backend/spec_runner.py"
          },
          {
            label: "Agent loop",
            title: "Планирует, пишет код и гоняет QA",
            text: "Planner, coder, QA reviewer и QA fixer работают как управляемый pipeline, а не как один непрозрачный prompt.",
            source: "apps/backend/agents"
          },
          {
            label: "Desktop workspace",
            title: "Дает UI для задач, onboarding и настроек",
            text: "Electron app показывает Kanban, task details, terminal output, account setup и provider/runtime настройки.",
            source: "apps/frontend/src/renderer"
          },
          {
            label: "Worktree delivery",
            title: "Держит изменения изолированными до review",
            text: "Каждая реализация живет в отдельном git worktree; пользователь смотрит diff, артефакты и решает merge или PR.",
            source: "apps/backend/cli/worktree.py"
          },
          {
            label: "Runtime matrix",
            title: "Показывает честные режимы providers",
            text: "Runtime matrix разделяет full autonomous runners, Codex CLI path, analysis-only, patch proposal и limited edit режимы.",
            source: "apps/backend/agents/runtime"
          },
          {
            label: "Docs and CI",
            title: "Публикует знания, отчеты и machine-readable output",
            text: "Проект умеет headless CI mode, JSON output, build/QA artifacts и теперь имеет встроенный reader для Markdown-документации.",
            source: "guides/ci-cd-integration.md"
          }
        ]
      },
      pages: [
        {
          id: "product",
          title: "Продукт",
          subtitle: "Что делает Auto Code, какие экраны и флоу реально существуют.",
          blocks: [
            {
              type: "showcase",
              kicker: "Live product story",
              title: "От задачи до проверенной ветки без магии в черном ящике",
              text:
                "Auto Code выглядит как рабочая станция для инженерных команд: пользователь описывает результат, система создает spec, запускает агентов, сохраняет артефакты и оставляет человеку понятный review gate.",
              windowTitle: "auto-code/spec-147",
              metrics: [
                ["4", "agent roles"],
                ["298", "rendered docs"],
                ["Built-in", "multi-runtime engine"]
              ],
              steps: [
                { title: "Spec", text: "requirements.json, context.json and acceptance criteria" },
                { title: "Plan", text: "subtasks, file targets, checks and fallback paths" },
                { title: "Build", text: "runtime-aware coder session in an isolated worktree" },
                { title: "QA", text: "reviewer/fixer loop with logs and artifacts" }
              ],
              terminal: [
                "$ python apps/backend/spec_runner.py --task \"Add provider smoke tests\"",
                "✓ requirements captured",
                "✓ implementation_plan.json generated",
                "$ python apps/backend/run.py --spec 147 --provider codex",
                "✓ worktree ready  ✓ QA artifacts saved  ✓ review handoff"
              ]
            }
          ]
        },
        {
          id: "approach",
          title: "Подход",
          subtitle: "Почему продукт устроен вокруг контроля, артефактов и честных runtime-границ.",
          blocks: [
            {
              type: "principles",
              title: "Почему это интересно",
              text: "Вместо обещания 'AI напишет все сам' Auto Code показывает инженерные свойства продукта: управляемость, наблюдаемость, расширяемость и честные границы runtime.",
              items: [
                {
                  label: "Governed",
                  title: "Контроль перед автономией",
                  text: "Worktrees, command allowlists, permissions и review gate делают агентный флоу пригодным для настоящего репозитория."
                },
                {
                  label: "Observable",
                  title: "Артефакты важнее магии",
                  text: "Spec, plan, logs, QA report и runtime metadata объясняют, что агент сделал и почему."
                },
                {
                  label: "Runtime-aware",
                  title: "Providers без самообмана",
                  text: "Сайт прямо разделяет full autonomous runners, Codex CLI path и limited direct-provider modes."
                },
                {
                  label: "Extensible",
                  title: "Платформа, а не один скрипт",
                  text: "CLI, Electron UI, integrations, memory, CI mode и docs corpus образуют расширяемую систему."
                }
              ]
            }
          ]
        },
        {
          id: "runtime",
          title: "Runtime и providers",
          subtitle: "Multi-runtime engine уже есть в проекте: вот режимы, providers и честные границы возможностей.",
          blocks: [
            {
              type: "matrix",
              title: "Provider compatibility",
              columns: ["Provider", "full_autonomous", "generic_edit", "analysis_only", "patch_proposal"],
              rows: [
                ["claude", "yes", "not needed", "yes", "not needed"],
                ["codex", "CLI runtime", "limited fallback", "yes", "limited"],
                ["openai", "no", "experimental", "limited", "limited"],
                ["google", "no", "experimental", "limited", "limited"],
                ["openrouter", "no", "experimental", "limited", "limited"],
                ["litellm", "no", "experimental", "limited", "limited"],
                ["zhipuai", "no", "experimental", "limited", "limited"],
                ["ollama", "no", "experimental", "limited/local", "limited"]
              ]
            },
            {
              type: "cards",
              title: "Что уже есть в multi-runtime engine",
              items: [
                {
                  title: "Runtime contracts",
                  text: "Capability declarations, requirements, result objects, session engine and fallback artifacts.",
                  meta: "apps/backend/agents/runtime"
                },
                {
                  title: "Codex CLI adapter",
                  text: "codex exec, CODEX_HOME, JSONL events, cancellation path, result artifacts and account/cost metadata where available.",
                  meta: "adapters/codex_cli.py"
                },
                {
                  title: "Limited provider modes",
                  text: "analysis_only, patch_proposal and generic_edit for providers that do not expose full agent tools.",
                  meta: "modes.py, generic_edit.py"
                },
                {
                  title: "Runner routing",
                  text: "Opt-in route from incompatible direct full_autonomous requests to a wired CLI runner.",
                  meta: "runner_router.py"
                }
              ]
            },
            {
              type: "commands",
              title: "Команды runtime диагностики",
              commands: [
                ["Show runtime matrix", "python apps/backend/run.py --runtime-modes"],
                ["JSON matrix", "python apps/backend/run.py --runtime-modes --json"],
                ["Provider smoke check", "python apps/backend/run.py --provider openai --provider-smoke --json"],
                ["Analysis-only pass", "python apps/backend/run.py --spec 001 --provider openai --analyze"]
              ]
            },
            {
              type: "links",
              title: "Источник",
              links: [
                ["Provider runtime modes", `${REPO_BASE}docs/architecture/provider-runtime-modes.md`],
                ["Environment variables", `${REPO_BASE}docs/configuration/environment-vars.md`],
                ["Runtime source", `${REPO_BASE}apps/backend/agents/runtime`],
                ["Provider abstraction", `${REPO_BASE}docs/architecture/provider-abstraction.md`]
              ]
            }
          ]
        },
        {
          id: "desktop",
          title: "Desktop app",
          subtitle: "Настройки, onboarding и то, что пользователь видит в приложении.",
          blocks: [
            {
              type: "surfaceGallery",
              title: "Поверхности приложения",
              text: "Компактная карта экранов, которые пользователь реально встречает: workspace, onboarding, provider settings и agent logs.",
              screens: [
                {
                  label: "Workspace",
                  title: "Kanban and task detail",
                  caption: "Specs проходят путь от intake до review, рядом видны статус, артефакты и agent output.",
                  badge: "Review gate",
                  rail: ["Specs", "Running", "Review", "Artifacts"],
                  cards: [
                    { label: "Spec 147", title: "Provider smoke tests", detail: "QA ready · diff available" },
                    { label: "Coder", title: "Runtime-aware session", detail: "isolated worktree" },
                    { label: "QA", title: "Acceptance criteria", detail: "report saved" }
                  ],
                  source: "apps/frontend/src/renderer"
                },
                {
                  label: "Onboarding",
                  title: "Account and provider setup",
                  caption: "Codex account login и API-key providers разведены как разные credential models.",
                  badge: "Next step",
                  rail: ["Welcome", "Account", "Provider", "Smoke test"],
                  cards: [
                    { label: "Codex", title: "Profile created in main process", detail: "CODEX_HOME path stays backend-readable" },
                    { label: "API key", title: "Provider credentials", detail: "stored separately from account login" },
                    { label: "Save", title: "Visible progression", detail: "settings lead to the next action" }
                  ],
                  source: "CodexOAuthStep.tsx"
                },
                {
                  label: "Settings",
                  title: "Provider runtime matrix",
                  caption: "UI показывает совместимость, warnings, cost preview и smoke checks до запуска spec.",
                  badge: "Capability-aware",
                  rail: ["Claude", "Codex", "OpenAI", "Ollama"],
                  cards: [
                    { label: "Full", title: "Autonomous runner", detail: "Claude SDK / CLI-capable paths" },
                    { label: "Limited", title: "Analysis or patch modes", detail: "direct providers do not pretend" },
                    { label: "Check", title: "Provider smoke test", detail: "fail before long agent runs" }
                  ],
                  source: "ProviderSettingsSection.tsx"
                }
              ]
            },
            {
              type: "cards",
              title: "Ключевые UI флоу",
              items: [
                {
                  title: "Account setup",
                  text: "Codex account flow создает профиль через main process, а API-key path сохраняет provider credentials отдельно.",
                  meta: "CodexOAuthStep.tsx, codex-profile-manager.ts"
                },
                {
                  title: "Auth terminal",
                  text: "Один переиспользуемый терминал принимает loginCommand, env и authProvider, вместо копирования Claude-specific UI.",
                  meta: "AuthTerminal.tsx"
                },
                {
                  title: "Provider/runtime settings",
                  text: "UI показывает runtime warnings, compatibility, cost preview, smoke checks и backend-readable env vars.",
                  meta: "ProviderSettingsSection.tsx"
                },
                {
                  title: "i18n",
                  text: "Frontend обязан держать пользовательский текст в translation files для en/fr и namespaces settings/onboarding/common.",
                  meta: "shared/i18n/locales"
                }
              ]
            },
            {
              type: "workflow",
              title: "Настройка runner/provider в UI",
              steps: [
                ["Choose account path", "Пользователь выбирает Codex account login или API-key provider."],
                ["Validate credentials", "App запускает безопасную проверку и показывает статус."],
                ["Select runtime mode", "UI не дает выбрать incompatible full_autonomous для direct provider без fallback/router."],
                ["Run smoke test", "Проверка provider до запуска spec."],
                ["Persist env", "Settings сохраняются в формате, который backend реально читает."],
                ["Show next step", "После save UI должен явно продвигать пользователя дальше."]
              ]
            },
            {
              type: "links",
              title: "Файлы UI",
              links: [
                ["Provider settings component", `${REPO_BASE}apps/frontend/src/renderer/components/settings/ProviderSettingsSection.tsx`],
                ["Account settings", `${REPO_BASE}apps/frontend/src/renderer/components/settings/AccountSettings.tsx`],
                ["Codex onboarding", `${REPO_BASE}apps/frontend/src/renderer/components/onboarding/CodexOAuthStep.tsx`],
                ["Provider UI docs", `${REPO_BASE}docs/frontend/provider-selection-ui.md`]
              ]
            }
          ]
        },
        {
          id: "architecture",
          title: "Архитектура",
          subtitle: "Как приложение проходит от задачи до review-ready изменений.",
          blocks: [
            {
              type: "architectureMap",
              title: "Как проходит работа",
              text: "Одна задача проходит через спецификацию, план, изолированный worktree, runtime-aware agent session, QA loop и человеческий review gate.",
              nodes: [
                {
                  label: "Intent",
                  title: "Task intake",
                  text: "Пользователь описывает результат на обычном языке.",
                  meta: "spec_runner.py"
                },
                {
                  label: "Spec",
                  title: "Requirements and context",
                  text: "Pipeline собирает acceptance criteria, context и сложность.",
                  meta: "requirements.json"
                },
                {
                  label: "Plan",
                  title: "Subtasks",
                  text: "Planner фиксирует файлы, проверки, fallback и порядок работы.",
                  meta: "implementation_plan.json"
                },
                {
                  label: "Build",
                  title: "Isolated agent session",
                  text: "Coder работает через совместимый runtime внутри git worktree.",
                  meta: "apps/backend/agents"
                },
                {
                  label: "QA",
                  title: "Reviewer and fixer loop",
                  text: "QA проверяет критерии, тесты, artifacts и возвращает точные замечания.",
                  meta: "qa_report.md"
                },
                {
                  label: "Review",
                  title: "Human handoff",
                  text: "Человек видит diff, logs, reports и решает merge/push/PR.",
                  meta: ".worktrees/{spec}"
                }
              ],
              evidence: ["requirements.json", "context.json", "implementation_plan.json", "qa_report.md", "build artifacts", "git diff"]
            },
            {
              type: "workflow",
              title: "Основной пользовательский путь",
              steps: [
                ["Open project", "Desktop app выбирает git repository и определяет стек проекта."],
                ["Create spec", "Пользователь описывает задачу, spec pipeline собирает требования и context."],
                ["Plan work", "Planner разбивает задачу на subtasks с файлами, критериями и проверками."],
                ["Run agents", "Coder выполняет изменения в isolated worktree, runtime выбирается по capability."],
                ["QA loop", "QA reviewer проверяет acceptance criteria, QA fixer чинит конкретные замечания."],
                ["Review handoff", "Пользователь смотрит diff, артефакты и решает merge/push/PR."]
              ]
            },
            {
              type: "workflow",
              title: "Backend pipeline",
              steps: [
                ["Spec runner", "SIMPLE/STANDARD/COMPLEX pipeline собирает требования и context."],
                ["Planner", "Создает implementation_plan.json с subtasks."],
                ["Coder", "Исполняет subtasks через выбранный runtime."],
                ["QA reviewer", "Проверяет acceptance criteria, тесты и artifacts."],
                ["QA fixer", "Исправляет rejected issues и возвращает в review loop."],
                ["Worktree merge", "После approval изменения можно смерджить из isolated worktree."]
              ]
            },
            {
              type: "cards",
              title: "Модули",
              items: [
                {
                  title: "apps/backend/core",
                  text: "Client setup, auth, providers, security, platform helpers.",
                  meta: "core/client.py, core/auth.py, core/security.py"
                },
                {
                  title: "apps/backend/agents",
                  text: "Planner/coder/QA agents, session execution, runtime adapters and recovery.",
                  meta: "agents/planner.py, coder.py, qa_reviewer.py"
                },
                {
                  title: "apps/frontend",
                  text: "Electron main/preload/renderer, IPC, settings, onboarding and task views.",
                  meta: "src/main, src/preload, src/renderer"
                },
                {
                  title: "docs and guides",
                  text: "Architecture docs, feature docs, API references, troubleshooting and deployment guides.",
                  meta: "docs, guides"
                }
              ]
            },
            {
              type: "links",
              title: "Architecture docs",
              links: [
                ["Backend architecture", `${REPO_BASE}docs/modules/backend-architecture.md`],
                ["Frontend architecture", `${REPO_BASE}docs/modules/frontend-architecture.md`],
                ["Provider abstraction", `${REPO_BASE}docs/architecture/provider-abstraction.md`],
                ["Worktree isolation ADR", `${REPO_BASE}docs/architecture/adr/ADR-003-worktree-isolation.md`]
              ]
            }
          ]
        },
        {
          id: "operations",
          title: "Запуск и эксплуатация",
          subtitle: "Команды, CI mode, GitHub Pages и безопасная доставка изменений.",
          blocks: [
            {
              type: "examples",
              title: "Примеры, которые хочется попробовать",
              text: "Короткие входы в продукт помогают понять ценность быстрее, чем длинное описание архитектуры.",
              items: [
                {
                  label: "Create",
                  title: "Создать spec из задачи",
                  text: "Подходит для первой проверки, что Auto Code понимает репозиторий и формирует acceptance criteria.",
                  command: "cd apps/backend\npython spec_runner.py --task \"Add provider smoke tests\"",
                  docPath: "guides/QUICK-START.md"
                },
                {
                  label: "Run",
                  title: "Запустить build в worktree",
                  text: "Агент работает изолированно, а пользователь получает diff и artifacts для review.",
                  command: "cd apps/backend\npython run.py --spec 147 --provider codex",
                  docPath: "guides/CLI-USAGE.md"
                },
                {
                  label: "Inspect",
                  title: "Проверить runtime matrix",
                  text: "Показывает, какие providers дают full autonomous режим, а какие ограничены analysis/patch modes.",
                  command: "python apps/backend/run.py --runtime-modes --json",
                  docPath: "docs/architecture/provider-runtime-modes.md"
                }
              ]
            },
            {
              type: "commands",
              title: "Основные команды",
              commands: [
                ["Install all", "npm run install:all"],
                ["Create spec", "cd apps/backend && python spec_runner.py --task \"Add user authentication\""],
                ["Run build", "cd apps/backend && python run.py --spec 001"],
                ["Review worktree", "cd apps/backend && python run.py --spec 001 --review"],
                ["Run QA", "cd apps/backend && python run.py --spec 001 --qa"],
                ["CI JSON mode", "cd apps/backend && python run.py --spec 001 --ci --json"]
              ]
            },
            {
              type: "cards",
              title: "Операционные принципы",
              items: [
                {
                  title: "No automatic push",
                  text: "Auto Code держит ветки локально до явного решения пользователя.",
                  meta: "worktree strategy"
                },
                {
                  title: "Artifacts first",
                  text: "Build log, test report, QA report and runtime artifacts должны объяснять outcome.",
                  meta: ".auto-Codex/specs"
                },
                {
                  title: "Fail fast by capability",
                  text: "Provider mismatch должен быть понятной диагностикой, а не молчаливой деградацией.",
                  meta: "compatibility.py, fallback.py"
                },
                {
                  title: "GitHub Pages docs",
                  text: "Этот портал деплоится из site/ через workflow docs-site-pages.yml.",
                  meta: ".github/workflows"
                }
              ]
            },
            {
              type: "links",
              title: "Operations docs",
              links: [
                ["CI/CD integration", `${REPO_BASE}guides/ci-cd-integration.md`],
                ["Troubleshooting", `${REPO_BASE}guides/TROUBLESHOOTING.md`],
                ["Advanced usage", `${REPO_BASE}guides/ADVANCED-USAGE.md`],
                ["GitHub Pages workflow", `${REPO_BASE}.github/workflows/docs-site-pages.yml`]
              ]
            }
          ]
        },
        {
          id: "roadmap",
          title: "Roadmap",
          subtitle: "Что уже работает в проекте и что честно остается future work.",
          blocks: [
            {
              type: "timeline",
              title: "Status board",
              items: [
                ["done", "Runtime boundary", "Capability declarations, runtime requirements, result objects and session execution."],
                ["done", "Codex CLI path", "codex exec, CODEX_HOME, JSONL events, cancellation and artifacts."],
                ["done", "Limited modes", "analysis_only, patch_proposal, generic_edit with local action executor."],
                ["done", "Frontend settings", "Provider/runtime matrix, warnings, smoke tests and account/profile flows."],
                ["next", "MCP parity", "Context7, Graphiti, Electron/Puppeteer, Linear and custom MCP bridge parity."],
                ["next", "Runner ecosystem", "Claude Code, Gemini CLI, Aider, Cursor CLI, CodeRabbit and generic runner pool."],
                ["next", "Subagent orchestration", "Production non-Claude child sessions with isolation, merge policy and recovery."],
                ["next", "Cost normalization", "Consistent account, usage and cost reporting across providers and CLIs."]
              ]
            },
            {
              type: "links",
              title: "Roadmap source",
              links: [
                ["Implementation phases", `${REPO_BASE}docs/roadmap/implementation-phases.md`],
                ["CLI runner strategy", `${REPO_BASE}docs/roadmap/cli-runner-strategy.md`],
                ["Migration guide", `${REPO_BASE}docs/roadmap/migration-guide.md`]
              ]
            }
          ]
        },
        {
          id: "library",
          title: "Библиотека docs",
          subtitle: "Полный Markdown-корпус репозитория с поиском, фильтрами и встроенным чтением.",
          blocks: [
            {
              type: "links",
              title: "Реальные документы продукта",
              links: [
                ["Quick Start", `${REPO_BASE}guides/QUICK-START.md`],
                ["CLI Usage", `${REPO_BASE}guides/CLI-USAGE.md`],
                ["Documentation Freshness Audit", `${REPO_BASE}docs/audit/DOCS-FRESHNESS-AUDIT.md`],
                ["Frontend architecture", `${REPO_BASE}docs/modules/frontend-architecture.md`],
                ["Backend architecture", `${REPO_BASE}docs/modules/backend-architecture.md`]
              ]
            },
            {
              type: "links",
              title: "User guides",
              links: [
                ["Quick Start", `${REPO_BASE}guides/QUICK-START.md`],
                ["CLI Usage", `${REPO_BASE}guides/CLI-USAGE.md`],
                ["Documentation Freshness Audit", `${REPO_BASE}docs/audit/DOCS-FRESHNESS-AUDIT.md`],
                ["Spec Creation Pipeline", `${REPO_BASE}guides/SPEC-CREATION-PIPELINE.md`],
                ["Agent customization", `${REPO_BASE}guides/AGENT-CUSTOMIZATION.md`],
                ["Electron MCP integration", `${REPO_BASE}guides/INTEGRATION-ELECTRON-MCP.md`]
              ]
            },
            {
              type: "links",
              title: "Architecture and APIs",
              links: [
                ["CLI API reference", `${REPO_BASE}docs/api/CLI-API-REFERENCE.md`],
                ["IPC API reference", `${REPO_BASE}docs/api/IPC-API-REFERENCE.md`],
                ["Backend API", `${REPO_BASE}docs/api/backend-api.md`],
                ["Web backend API", `${REPO_BASE}docs/api/web-backend-api.md`],
                ["Security model diagram", `${REPO_BASE}docs/diagrams/security-model.mermaid`]
              ]
            },
            {
              type: "links",
              title: "Deployment and enterprise",
              links: [
                ["Self-hosted deployment", `${REPO_BASE}guides/SELF-HOSTED-DEPLOYMENT.md`],
                ["Docker deployment", `${REPO_BASE}guides/DOCKER_DEPLOYMENT.md`],
                ["Kubernetes deployment", `${REPO_BASE}guides/KUBERNETES_DEPLOYMENT.md`],
                ["SOC2 compliance", `${REPO_BASE}docs/compliance/SOC2_COMPLIANCE.md`],
                ["Audit logging", `${REPO_BASE}docs/enterprise/AUDIT_LOGGING.md`]
              ]
            }
          ]
        }
      ]
    },
    en: {
      ui: {
        brandOverline: "Product docs",
        brandTitle: "Auto Code",
        languageLabel: "Language",
        searchLabel: "Search",
        searchPlaceholder: "runtime, Codex CLI, QA, settings...",
        heroEyebrow: "Open-source · Agentic engineering platform",
        heroTitle: "Intent in.\u00A0Review-ready branch out.",
        heroLead:
          "Describe what you need. Auto Code runs Planner, Coder, and QA agents in an isolated worktree — and hands you a diff, logs, and artifacts for review.",
        navEmpty: "No sections found.",
        sourceLabel: "Source",
        roadmapUpdated: "Project documentation snapshot: 2026-05-02"
      },
      heroActions: [
        { label: "Quick start", href: `${REPO_BASE}guides/QUICK-START.md` },
        { label: "Runtime docs", href: `${REPO_BASE}docs/architecture/provider-runtime-modes.md` },
        { label: "Docs library", href: "#library" }
      ],
      productSignal: {
        title: "Describe -> Spec -> Agents -> QA -> Review",
        rows: [
          ["Start with intent", "A plain-language task becomes requirements, context, and an implementation plan"],
          ["Run controlled agents", "Planner, coder, and QA roles execute inside an isolated worktree"],
          ["Choose runtime", "Claude SDK, Codex CLI, and limited provider modes are explicit"],
          ["Ship with evidence", "Diff, logs, QA report, and artifacts are ready for human review"]
        ]
      },
      appMap: {
        title: "What Auto Code already does",
        subtitle: "Real project capabilities: from task intake to reviewed branches, artifacts, and runtime selection.",
        items: [
          {
            label: "Spec pipeline",
            title: "Turns tasks into clear specifications",
            text: "The interactive spec runner captures requirements, project context, acceptance criteria, and task complexity.",
            source: "apps/backend/spec_runner.py"
          },
          {
            label: "Agent loop",
            title: "Plans, codes, and runs QA",
            text: "Planner, coder, QA reviewer, and QA fixer operate as a controlled pipeline rather than a single opaque prompt.",
            source: "apps/backend/agents"
          },
          {
            label: "Desktop workspace",
            title: "Provides UI for tasks, onboarding, and settings",
            text: "The Electron app exposes Kanban, task details, terminal output, account setup, and provider/runtime settings.",
            source: "apps/frontend/src/renderer"
          },
          {
            label: "Worktree delivery",
            title: "Keeps changes isolated until review",
            text: "Each implementation lives in a separate git worktree; the user reviews diff, artifacts, and chooses merge or PR.",
            source: "apps/backend/cli/worktree.py"
          },
          {
            label: "Runtime matrix",
            title: "Shows honest provider modes",
            text: "The runtime matrix separates full autonomous runners, Codex CLI execution, analysis-only, patch proposal, and limited edit modes.",
            source: "apps/backend/agents/runtime"
          },
          {
            label: "Docs and CI",
            title: "Publishes knowledge, reports, and machine output",
            text: "The project supports headless CI mode, JSON output, build/QA artifacts, and an inline reader for Markdown documentation.",
            source: "guides/ci-cd-integration.md"
          }
        ]
      },
      pages: [
        {
          id: "product",
          title: "Product",
          subtitle: "What Auto Code actually does and which app surfaces exist.",
          blocks: [
            {
              type: "showcase",
              kicker: "Live product story",
              title: "From task to reviewed branch without black-box magic",
              text:
                "Auto Code presents itself as an engineering workstation: describe the outcome, create a spec, run agents, preserve artifacts, and keep a clear human review gate.",
              windowTitle: "auto-code/spec-147",
              metrics: [
                ["4", "agent roles"],
                ["298", "rendered docs"],
                ["Built-in", "multi-runtime engine"]
              ],
              steps: [
                { title: "Spec", text: "requirements.json, context.json, and acceptance criteria" },
                { title: "Plan", text: "subtasks, file targets, checks, and fallback paths" },
                { title: "Build", text: "runtime-aware coder session in an isolated worktree" },
                { title: "QA", text: "reviewer/fixer loop with logs and artifacts" }
              ],
              terminal: [
                "$ python apps/backend/spec_runner.py --task \"Add provider smoke tests\"",
                "✓ requirements captured",
                "✓ implementation_plan.json generated",
                "$ python apps/backend/run.py --spec 147 --provider codex",
                "✓ worktree ready  ✓ QA artifacts saved  ✓ review handoff"
              ]
            }
          ]
        },
        {
          id: "approach",
          title: "Approach",
          subtitle: "Why the product centers control, artifacts, and honest runtime boundaries.",
          blocks: [
            {
              type: "principles",
              title: "Why it is interesting",
              text: "Auto Code sells engineering properties, not a vague promise that AI writes everything alone.",
              items: [
                {
                  label: "Governed",
                  title: "Control before autonomy",
                  text: "Worktrees, command allowlists, permissions, and review gates make the agent workflow usable in a real repository."
                },
                {
                  label: "Observable",
                  title: "Artifacts over magic",
                  text: "Spec, plan, logs, QA report, and runtime metadata explain what the agent did and why."
                },
                {
                  label: "Runtime-aware",
                  title: "Providers without pretense",
                  text: "The portal separates full autonomous runners, Codex CLI execution, and limited direct-provider modes."
                },
                {
                  label: "Extensible",
                  title: "A platform, not one script",
                  text: "CLI, Electron UI, integrations, memory, CI mode, and the docs corpus form an extensible system."
                }
              ]
            }
          ]
        },
        {
          id: "runtime",
          title: "Runtime and providers",
          subtitle: "The project already includes a multi-runtime engine; this section shows modes, providers, and compatibility boundaries.",
          blocks: [
            {
              type: "matrix",
              title: "Provider compatibility",
              columns: ["Provider", "full_autonomous", "generic_edit", "analysis_only", "patch_proposal"],
              rows: [
                ["claude", "yes", "not needed", "yes", "not needed"],
                ["codex", "CLI runtime", "limited fallback", "yes", "limited"],
                ["openai", "no", "experimental", "limited", "limited"],
                ["google", "no", "experimental", "limited", "limited"],
                ["openrouter", "no", "experimental", "limited", "limited"],
                ["litellm", "no", "experimental", "limited", "limited"],
                ["zhipuai", "no", "experimental", "limited", "limited"],
                ["ollama", "no", "experimental", "limited/local", "limited"]
              ]
            },
            {
              type: "commands",
              title: "Runtime diagnostics",
              commands: [
                ["Show runtime matrix", "python apps/backend/run.py --runtime-modes"],
                ["JSON matrix", "python apps/backend/run.py --runtime-modes --json"],
                ["Provider smoke check", "python apps/backend/run.py --provider openai --provider-smoke --json"],
                ["Analysis-only pass", "python apps/backend/run.py --spec 001 --provider openai --analyze"]
              ]
            },
            {
              type: "links",
              title: "Sources",
              links: [
                ["Provider runtime modes", `${REPO_BASE}docs/architecture/provider-runtime-modes.md`],
                ["Environment variables", `${REPO_BASE}docs/configuration/environment-vars.md`],
                ["Runtime source", `${REPO_BASE}apps/backend/agents/runtime`],
                ["Provider abstraction", `${REPO_BASE}docs/architecture/provider-abstraction.md`]
              ]
            }
          ]
        },
        {
          id: "desktop",
          title: "Desktop app",
          subtitle: "Settings, onboarding, and user-visible configuration flows.",
          blocks: [
            {
              type: "surfaceGallery",
              title: "Application surfaces",
              text: "A compact map of the screens people actually touch: workspace, onboarding, provider settings, and agent logs.",
              screens: [
                {
                  label: "Workspace",
                  title: "Kanban and task detail",
                  caption: "Specs move from intake to review while status, artifacts, and agent output stay visible.",
                  badge: "Review gate",
                  rail: ["Specs", "Running", "Review", "Artifacts"],
                  cards: [
                    { label: "Spec 147", title: "Provider smoke tests", detail: "QA ready · diff available" },
                    { label: "Coder", title: "Runtime-aware session", detail: "isolated worktree" },
                    { label: "QA", title: "Acceptance criteria", detail: "report saved" }
                  ],
                  source: "apps/frontend/src/renderer"
                },
                {
                  label: "Onboarding",
                  title: "Account and provider setup",
                  caption: "Codex account login and API-key providers remain separate credential models.",
                  badge: "Next step",
                  rail: ["Welcome", "Account", "Provider", "Smoke test"],
                  cards: [
                    { label: "Codex", title: "Profile created in main process", detail: "CODEX_HOME stays backend-readable" },
                    { label: "API key", title: "Provider credentials", detail: "stored separately from account login" },
                    { label: "Save", title: "Visible progression", detail: "settings lead to the next action" }
                  ],
                  source: "CodexOAuthStep.tsx"
                },
                {
                  label: "Settings",
                  title: "Provider runtime matrix",
                  caption: "Compatibility, warnings, cost preview, and smoke checks appear before a spec run.",
                  badge: "Capability-aware",
                  rail: ["Claude", "Codex", "OpenAI", "Ollama"],
                  cards: [
                    { label: "Full", title: "Autonomous runner", detail: "SDK / CLI-capable paths" },
                    { label: "Limited", title: "Analysis or patch modes", detail: "direct providers do not pretend" },
                    { label: "Check", title: "Provider smoke test", detail: "fail before long agent runs" }
                  ],
                  source: "ProviderSettingsSection.tsx"
                }
              ]
            },
            {
              type: "cards",
              title: "Key UI flows",
              items: [
                {
                  title: "Account setup",
                  text: "Codex account login and API-key provider setup are separate paths.",
                  meta: "CodexOAuthStep, AuthChoiceStep"
                },
                {
                  title: "Provider/runtime settings",
                  text: "Compatibility matrix, runtime warnings, cost preview, smoke tests, and backend-readable env settings.",
                  meta: "ProviderSettingsSection"
                },
                {
                  title: "Auth terminal",
                  text: "Reusable login terminal accepts loginCommand, env, and authProvider.",
                  meta: "AuthTerminal"
                }
              ]
            },
            {
              type: "links",
              title: "UI source",
              links: [
                ["Provider settings component", `${REPO_BASE}apps/frontend/src/renderer/components/settings/ProviderSettingsSection.tsx`],
                ["Account settings", `${REPO_BASE}apps/frontend/src/renderer/components/settings/AccountSettings.tsx`],
                ["Codex onboarding", `${REPO_BASE}apps/frontend/src/renderer/components/onboarding/CodexOAuthStep.tsx`],
                ["Provider UI docs", `${REPO_BASE}docs/frontend/provider-selection-ui.md`]
              ]
            }
          ]
        },
        {
          id: "architecture",
          title: "Architecture",
          subtitle: "How work moves from task to review-ready changes.",
          blocks: [
            {
              type: "architectureMap",
              title: "How work moves",
              text: "A task flows through specification, planning, isolated worktree execution, runtime-aware agent sessions, QA, and a human review gate.",
              nodes: [
                {
                  label: "Intent",
                  title: "Task intake",
                  text: "The user describes the outcome in plain language.",
                  meta: "spec_runner.py"
                },
                {
                  label: "Spec",
                  title: "Requirements and context",
                  text: "The pipeline captures acceptance criteria, context, and complexity.",
                  meta: "requirements.json"
                },
                {
                  label: "Plan",
                  title: "Subtasks",
                  text: "Planner records files, checks, fallback paths, and execution order.",
                  meta: "implementation_plan.json"
                },
                {
                  label: "Build",
                  title: "Isolated agent session",
                  text: "Coder works through a compatible runtime inside a git worktree.",
                  meta: "apps/backend/agents"
                },
                {
                  label: "QA",
                  title: "Reviewer and fixer loop",
                  text: "QA checks criteria, tests, artifacts, and returns concrete issues.",
                  meta: "qa_report.md"
                },
                {
                  label: "Review",
                  title: "Human handoff",
                  text: "A human reviews diff, logs, reports, and decides merge, push, or PR.",
                  meta: ".worktrees/{spec}"
                }
              ],
              evidence: ["requirements.json", "context.json", "implementation_plan.json", "qa_report.md", "build artifacts", "git diff"]
            },
            {
              type: "workflow",
              title: "Main user journey",
              steps: [
                ["Open project", "The desktop app opens a git repository and detects the stack."],
                ["Create spec", "The user describes the task; the spec pipeline gathers requirements and context."],
                ["Plan work", "The planner creates subtasks with files, criteria, and validation steps."],
                ["Run agents", "The coder works inside an isolated worktree through a compatible runtime."],
                ["QA loop", "QA reviewer checks acceptance criteria; QA fixer handles concrete failures."],
                ["Review handoff", "The user reviews diff, artifacts, and decides merge, push, or PR."]
              ]
            },
            {
              type: "workflow",
              title: "Backend pipeline",
              steps: [
                ["Spec runner", "Builds requirements and context."],
                ["Planner", "Creates implementation_plan.json."],
                ["Coder", "Executes subtasks through the selected runtime."],
                ["QA reviewer", "Validates acceptance criteria and tests."],
                ["QA fixer", "Fixes rejected issues."],
                ["Worktree merge", "Hands off isolated changes after approval."]
              ]
            },
            {
              type: "links",
              title: "Architecture docs",
              links: [
                ["Backend architecture", `${REPO_BASE}docs/modules/backend-architecture.md`],
                ["Frontend architecture", `${REPO_BASE}docs/modules/frontend-architecture.md`],
                ["Provider abstraction", `${REPO_BASE}docs/architecture/provider-abstraction.md`],
                ["Worktree isolation ADR", `${REPO_BASE}docs/architecture/adr/ADR-003-worktree-isolation.md`]
              ]
            }
          ]
        },
        {
          id: "operations",
          title: "Operations",
          subtitle: "Commands, CI mode, GitHub Pages, and safe delivery.",
          blocks: [
            {
              type: "examples",
              title: "Examples worth trying",
              text: "Short entry points communicate value faster than a long architecture essay.",
              items: [
                {
                  label: "Create",
                  title: "Create a spec from a task",
                  text: "A good first check that Auto Code understands the repository and creates acceptance criteria.",
                  command: "cd apps/backend\npython spec_runner.py --task \"Add provider smoke tests\"",
                  docPath: "guides/QUICK-START.md"
                },
                {
                  label: "Run",
                  title: "Run a build in a worktree",
                  text: "The agent works in isolation and hands the user a diff plus review artifacts.",
                  command: "cd apps/backend\npython run.py --spec 147 --provider codex",
                  docPath: "guides/CLI-USAGE.md"
                },
                {
                  label: "Inspect",
                  title: "Check the runtime matrix",
                  text: "Shows which providers support autonomous execution and which are limited to analysis or patch modes.",
                  command: "python apps/backend/run.py --runtime-modes --json",
                  docPath: "docs/architecture/provider-runtime-modes.md"
                }
              ]
            },
            {
              type: "commands",
              title: "Core commands",
              commands: [
                ["Install all", "npm run install:all"],
                ["Create spec", "cd apps/backend && python spec_runner.py --task \"Add user authentication\""],
                ["Run build", "cd apps/backend && python run.py --spec 001"],
                ["Run QA", "cd apps/backend && python run.py --spec 001 --qa"],
                ["CI JSON mode", "cd apps/backend && python run.py --spec 001 --ci --json"]
              ]
            },
            {
              type: "links",
              title: "Operations docs",
              links: [
                ["CI/CD integration", `${REPO_BASE}guides/ci-cd-integration.md`],
                ["Troubleshooting", `${REPO_BASE}guides/TROUBLESHOOTING.md`],
                ["Advanced usage", `${REPO_BASE}guides/ADVANCED-USAGE.md`],
                ["GitHub Pages workflow", `${REPO_BASE}.github/workflows/docs-site-pages.yml`]
              ]
            }
          ]
        },
        {
          id: "roadmap",
          title: "Roadmap",
          subtitle: "What already works in the project and what honestly remains future work.",
          blocks: [
            {
              type: "timeline",
              title: "Status board",
              items: [
                ["done", "Runtime boundary", "Capability declarations, requirements, results, and session engine."],
                ["done", "Codex CLI path", "codex exec, CODEX_HOME, JSONL events, cancellation, and artifacts."],
                ["done", "Limited modes", "analysis_only, patch_proposal, generic_edit."],
                ["next", "MCP parity", "Context7, Graphiti, Electron/Puppeteer, Linear, and custom MCP bridge parity."],
                ["next", "Runner ecosystem", "Claude Code, Gemini CLI, Aider, Cursor CLI, CodeRabbit, and generic runners."]
              ]
            },
            {
              type: "links",
              title: "Roadmap source",
              links: [
                ["Implementation phases", `${REPO_BASE}docs/roadmap/implementation-phases.md`],
                ["CLI runner strategy", `${REPO_BASE}docs/roadmap/cli-runner-strategy.md`],
                ["Migration guide", `${REPO_BASE}docs/roadmap/migration-guide.md`]
              ]
            }
          ]
        },
        {
          id: "library",
          title: "Docs library",
          subtitle: "The repository Markdown corpus with search, filters, and inline reading.",
          blocks: [
            {
              type: "links",
              title: "Real product docs",
              links: [
                ["Quick Start", `${REPO_BASE}guides/QUICK-START.md`],
                ["CLI Usage", `${REPO_BASE}guides/CLI-USAGE.md`],
                ["Documentation Freshness Audit", `${REPO_BASE}docs/audit/DOCS-FRESHNESS-AUDIT.md`],
                ["Frontend architecture", `${REPO_BASE}docs/modules/frontend-architecture.md`],
                ["Backend architecture", `${REPO_BASE}docs/modules/backend-architecture.md`]
              ]
            },
            {
              type: "links",
              title: "Guides and APIs",
              links: [
                ["Quick Start", `${REPO_BASE}guides/QUICK-START.md`],
                ["Documentation Freshness Audit", `${REPO_BASE}docs/audit/DOCS-FRESHNESS-AUDIT.md`],
                ["CLI API reference", `${REPO_BASE}docs/api/CLI-API-REFERENCE.md`],
                ["IPC API reference", `${REPO_BASE}docs/api/IPC-API-REFERENCE.md`],
                ["Self-hosted deployment", `${REPO_BASE}guides/SELF-HOSTED-DEPLOYMENT.md`],
                ["SOC2 compliance", `${REPO_BASE}docs/compliance/SOC2_COMPLIANCE.md`]
              ]
            }
          ]
        }
      ]
    },
    fr: {
      ui: {
        brandOverline: "Docs produit",
        brandTitle: "Auto Code",
        languageLabel: "Langue",
        searchLabel: "Recherche",
        searchPlaceholder: "runtime, Codex CLI, QA, settings...",
        heroEyebrow: "Open-source · Plateforme d'ingenierie agentique",
        heroTitle: "L'intention entre.\u00A0La branche sort prete.",
        heroLead:
          "Decrivez votre besoin. Auto Code lance Planner, Coder et QA dans un worktree isole — et vous remet un diff, des logs et des artefacts pour revue.",
        navEmpty: "Aucune section trouvee.",
        sourceLabel: "Source",
        roadmapUpdated: "Snapshot documentation projet: 2026-05-02"
      },
      heroActions: [
        { label: "Quick start", href: `${REPO_BASE}guides/QUICK-START.md` },
        { label: "Runtime docs", href: `${REPO_BASE}docs/architecture/provider-runtime-modes.md` },
        { label: "Bibliotheque docs", href: "#library" }
      ],
      productSignal: {
        title: "Describe -> Spec -> Agents -> QA -> Review",
        rows: [
          ["Start with intent", "Une tache en langage naturel devient requirements, contexte et plan"],
          ["Run controlled agents", "Planner, coder et QA travaillent dans un worktree isole"],
          ["Choose runtime", "Claude SDK, Codex CLI et modes limites sont explicites"],
          ["Ship with evidence", "Diff, logs, rapport QA et artefacts restent lisibles pour la revue"]
        ]
      },
      appMap: {
        title: "Ce qu'Auto Code sait deja faire",
        subtitle: "Capacites reelles du projet: de la tache a la branche revue, avec artefacts et choix runtime.",
        items: [
          {
            label: "Spec pipeline",
            title: "Transforme une tache en specification claire",
            text: "Le spec runner collecte requirements, contexte projet, criteres d'acceptation et complexite.",
            source: "apps/backend/spec_runner.py"
          },
          {
            label: "Agent loop",
            title: "Planifie, code et execute la QA",
            text: "Planner, coder, QA reviewer et QA fixer forment un pipeline controle plutot qu'un prompt opaque.",
            source: "apps/backend/agents"
          },
          {
            label: "Desktop workspace",
            title: "Fournit l'UI pour taches, onboarding et settings",
            text: "L'app Electron expose Kanban, task details, terminal output, account setup et settings runtime/provider.",
            source: "apps/frontend/src/renderer"
          },
          {
            label: "Worktree delivery",
            title: "Isole les changements jusqu'a la revue",
            text: "Chaque implementation vit dans un git worktree separe; l'utilisateur examine diff, artefacts et choisit merge ou PR.",
            source: "apps/backend/cli/worktree.py"
          },
          {
            label: "Runtime matrix",
            title: "Affiche les vrais modes providers",
            text: "La matrice runtime separe runners autonomes, Codex CLI, analysis-only, patch proposal et limited edit modes.",
            source: "apps/backend/agents/runtime"
          },
          {
            label: "Docs and CI",
            title: "Publie connaissances, rapports et output machine",
            text: "Le projet supporte CI headless, JSON output, artefacts build/QA et un lecteur inline pour la documentation Markdown.",
            source: "guides/ci-cd-integration.md"
          }
        ]
      },
      pages: [
        {
          id: "product",
          title: "Produit",
          subtitle: "Ce que fait vraiment Auto Code et les surfaces existantes.",
          blocks: [
            {
              type: "showcase",
              kicker: "Live product story",
              title: "De la tache a la branche revue sans magie opaque",
              text:
                "Auto Code se presente comme une station de travail d'ingenierie: decrire le resultat, creer une spec, lancer les agents, garder les artefacts et conserver une vraie revue humaine.",
              windowTitle: "auto-code/spec-147",
              metrics: [
                ["4", "roles agents"],
                ["298", "docs rendues"],
                ["Integre", "multi-runtime engine"]
              ],
              steps: [
                { title: "Spec", text: "requirements.json, context.json et criteres d'acceptation" },
                { title: "Plan", text: "subtasks, fichiers cibles, checks et fallbacks" },
                { title: "Build", text: "session coder runtime-aware dans un worktree isole" },
                { title: "QA", text: "boucle reviewer/fixer avec logs et artefacts" }
              ],
              terminal: [
                "$ python apps/backend/spec_runner.py --task \"Add provider smoke tests\"",
                "✓ requirements captured",
                "✓ implementation_plan.json generated",
                "$ python apps/backend/run.py --spec 147 --provider codex",
                "✓ worktree ready  ✓ QA artifacts saved  ✓ review handoff"
              ]
            }
          ]
        },
        {
          id: "approach",
          title: "Approche",
          subtitle: "Pourquoi le produit met l'accent sur controle, artefacts et limites runtime claires.",
          blocks: [
            {
              type: "principles",
              title: "Pourquoi c'est interessant",
              text: "Auto Code met en avant des proprietes d'ingenierie plutot qu'une promesse vague que l'IA fera tout seule.",
              items: [
                {
                  label: "Governed",
                  title: "Controle avant autonomie",
                  text: "Worktrees, allowlists, permissions et review gates rendent le workflow agentique utilisable dans un vrai depot."
                },
                {
                  label: "Observable",
                  title: "Artefacts plutot que magie",
                  text: "Spec, plan, logs, rapport QA et metadata runtime expliquent ce que l'agent a fait."
                },
                {
                  label: "Runtime-aware",
                  title: "Providers sans pretendre",
                  text: "Le portail separe runners autonomes, Codex CLI et providers directs limites."
                },
                {
                  label: "Extensible",
                  title: "Une plateforme, pas un script",
                  text: "CLI, UI Electron, integrations, memoire, CI mode et corpus docs forment un systeme extensible."
                }
              ]
            }
          ]
        },
        {
          id: "runtime",
          title: "Runtime et providers",
          subtitle: "Le projet inclut deja un multi-runtime engine: modes, providers et limites de compatibilite.",
          blocks: [
            {
              type: "matrix",
              title: "Compatibilite",
              columns: ["Provider", "full_autonomous", "generic_edit", "analysis_only", "patch_proposal"],
              rows: [
                ["claude", "yes", "not needed", "yes", "not needed"],
                ["codex", "CLI runtime", "limited fallback", "yes", "limited"],
                ["openai", "no", "experimental", "limited", "limited"],
                ["google", "no", "experimental", "limited", "limited"],
                ["openrouter", "no", "experimental", "limited", "limited"],
                ["ollama", "no", "experimental", "limited/local", "limited"]
              ]
            },
            {
              type: "links",
              title: "Sources",
              links: [
                ["Provider runtime modes", `${REPO_BASE}docs/architecture/provider-runtime-modes.md`],
                ["Runtime source", `${REPO_BASE}apps/backend/agents/runtime`],
                ["Provider abstraction", `${REPO_BASE}docs/architecture/provider-abstraction.md`]
              ]
            }
          ]
        },
        {
          id: "desktop",
          title: "Desktop app",
          subtitle: "Settings, onboarding et configuration visible.",
          blocks: [
            {
              type: "surfaceGallery",
              title: "Surfaces applicatives",
              text: "Carte compacte des ecrans reels: workspace, onboarding, settings providers et logs agents.",
              screens: [
                {
                  label: "Workspace",
                  title: "Kanban and task detail",
                  caption: "Les specs passent de l'intake a la review avec statuts, artefacts et output agent visibles.",
                  badge: "Review gate",
                  rail: ["Specs", "Running", "Review", "Artifacts"],
                  cards: [
                    { label: "Spec 147", title: "Provider smoke tests", detail: "QA ready · diff available" },
                    { label: "Coder", title: "Session runtime-aware", detail: "worktree isole" },
                    { label: "QA", title: "Criteres d'acceptation", detail: "rapport sauvegarde" }
                  ],
                  source: "apps/frontend/src/renderer"
                },
                {
                  label: "Onboarding",
                  title: "Account and provider setup",
                  caption: "Codex account login et API-key providers restent des modeles de credentials separes.",
                  badge: "Next step",
                  rail: ["Welcome", "Account", "Provider", "Smoke test"],
                  cards: [
                    { label: "Codex", title: "Profil cree dans main process", detail: "CODEX_HOME reste lisible par backend" },
                    { label: "API key", title: "Credentials provider", detail: "stockes separement du login account" },
                    { label: "Save", title: "Progression visible", detail: "settings menent a l'action suivante" }
                  ],
                  source: "CodexOAuthStep.tsx"
                },
                {
                  label: "Settings",
                  title: "Provider runtime matrix",
                  caption: "Compatibilite, warnings, cost preview et smoke checks apparaissent avant le run.",
                  badge: "Capability-aware",
                  rail: ["Claude", "Codex", "OpenAI", "Ollama"],
                  cards: [
                    { label: "Full", title: "Autonomous runner", detail: "chemins SDK / CLI-capable" },
                    { label: "Limited", title: "Analysis or patch modes", detail: "providers directs sans pretendre" },
                    { label: "Check", title: "Provider smoke test", detail: "fail avant les longs runs agents" }
                  ],
                  source: "ProviderSettingsSection.tsx"
                }
              ]
            },
            {
              type: "cards",
              title: "Flux UI",
              items: [
                {
                  title: "Account setup",
                  text: "Codex account login et API-key setup restent separes.",
                  meta: "CodexOAuthStep, AuthChoiceStep"
                },
                {
                  title: "Provider settings",
                  text: "Matrix de compatibilite, warnings runtime, cost preview et smoke tests.",
                  meta: "ProviderSettingsSection"
                }
              ]
            },
            {
              type: "links",
              title: "UI source",
              links: [
                ["Provider settings component", `${REPO_BASE}apps/frontend/src/renderer/components/settings/ProviderSettingsSection.tsx`],
                ["Codex onboarding", `${REPO_BASE}apps/frontend/src/renderer/components/onboarding/CodexOAuthStep.tsx`],
                ["Provider UI docs", `${REPO_BASE}docs/frontend/provider-selection-ui.md`]
              ]
            }
          ]
        },
        {
          id: "architecture",
          title: "Architecture",
          subtitle: "De la tache aux changements prets pour review.",
          blocks: [
            {
              type: "architectureMap",
              title: "Comment le travail circule",
              text: "Une tache traverse specification, plan, worktree isole, session agent runtime-aware, QA et revue humaine.",
              nodes: [
                {
                  label: "Intent",
                  title: "Task intake",
                  text: "L'utilisateur decrit le resultat en langage naturel.",
                  meta: "spec_runner.py"
                },
                {
                  label: "Spec",
                  title: "Requirements and context",
                  text: "Le pipeline capture criteres, contexte et complexite.",
                  meta: "requirements.json"
                },
                {
                  label: "Plan",
                  title: "Subtasks",
                  text: "Le planner fixe fichiers, checks, fallbacks et ordre.",
                  meta: "implementation_plan.json"
                },
                {
                  label: "Build",
                  title: "Isolated agent session",
                  text: "Le coder travaille via un runtime compatible dans un worktree git.",
                  meta: "apps/backend/agents"
                },
                {
                  label: "QA",
                  title: "Reviewer and fixer loop",
                  text: "QA verifie criteres, tests, artefacts et retourne des issues concretes.",
                  meta: "qa_report.md"
                },
                {
                  label: "Review",
                  title: "Human handoff",
                  text: "Un humain examine diff, logs, rapports et decide merge, push ou PR.",
                  meta: ".worktrees/{spec}"
                }
              ],
              evidence: ["requirements.json", "context.json", "implementation_plan.json", "qa_report.md", "build artifacts", "git diff"]
            },
            {
              type: "workflow",
              title: "Parcours principal",
              steps: [
                ["Open project", "L'app desktop ouvre un depot git et detecte la stack."],
                ["Create spec", "L'utilisateur decrit la tache; le pipeline collecte requirements et contexte."],
                ["Plan work", "Le planner cree des subtasks avec criteres et validations."],
                ["Run agents", "Le coder travaille dans un worktree isole via un runtime compatible."],
                ["QA loop", "QA reviewer valide; QA fixer corrige les echecs."],
                ["Review handoff", "L'utilisateur examine diff, artefacts et decide merge/push/PR."]
              ]
            },
            {
              type: "workflow",
              title: "Pipeline backend",
              steps: [
                ["Spec runner", "Requirements et contexte."],
                ["Planner", "implementation_plan.json."],
                ["Coder", "Subtasks via runtime selectionne."],
                ["QA reviewer", "Validation des criteres et tests."],
                ["QA fixer", "Correction des echecs."],
                ["Worktree merge", "Handoff apres approbation."]
              ]
            },
            {
              type: "links",
              title: "Docs architecture",
              links: [
                ["Backend architecture", `${REPO_BASE}docs/modules/backend-architecture.md`],
                ["Frontend architecture", `${REPO_BASE}docs/modules/frontend-architecture.md`],
                ["Provider abstraction", `${REPO_BASE}docs/architecture/provider-abstraction.md`]
              ]
            }
          ]
        },
        {
          id: "operations",
          title: "Operations",
          subtitle: "Commandes, CI mode et livraison.",
          blocks: [
            {
              type: "examples",
              title: "Exemples a essayer",
              text: "Des entrees courtes montrent la valeur plus vite qu'un long texte d'architecture.",
              items: [
                {
                  label: "Create",
                  title: "Creer une spec depuis une tache",
                  text: "Premier test pour verifier qu'Auto Code comprend le depot et cree des criteres.",
                  command: "cd apps/backend\npython spec_runner.py --task \"Add provider smoke tests\"",
                  docPath: "guides/QUICK-START.md"
                },
                {
                  label: "Run",
                  title: "Lancer un build dans un worktree",
                  text: "L'agent travaille isole et remet un diff avec des artefacts de revue.",
                  command: "cd apps/backend\npython run.py --spec 147 --provider codex",
                  docPath: "guides/CLI-USAGE.md"
                },
                {
                  label: "Inspect",
                  title: "Verifier la matrice runtime",
                  text: "Montre les providers autonomes et ceux limites a analysis/patch modes.",
                  command: "python apps/backend/run.py --runtime-modes --json",
                  docPath: "docs/architecture/provider-runtime-modes.md"
                }
              ]
            },
            {
              type: "commands",
              title: "Commandes",
              commands: [
                ["Install all", "npm run install:all"],
                ["Create spec", "cd apps/backend && python spec_runner.py --task \"Add user authentication\""],
                ["Run build", "cd apps/backend && python run.py --spec 001"],
                ["CI JSON mode", "cd apps/backend && python run.py --spec 001 --ci --json"]
              ]
            }
          ]
        },
        {
          id: "roadmap",
          title: "Roadmap",
          subtitle: "Ce qui fonctionne deja dans le projet et ce qui reste future work.",
          blocks: [
            {
              type: "timeline",
              title: "Status",
              items: [
                ["done", "Runtime boundary", "Contracts de capacites, requirements et session engine."],
                ["done", "Codex CLI path", "codex exec, CODEX_HOME, JSONL et artefacts."],
                ["next", "MCP parity", "Context7, Graphiti, Electron/Puppeteer, Linear."],
                ["next", "Runner ecosystem", "Claude Code, Gemini CLI, Aider, Cursor CLI, CodeRabbit."]
              ]
            },
            {
              type: "links",
              title: "Sources roadmap",
              links: [
                ["Implementation phases", `${REPO_BASE}docs/roadmap/implementation-phases.md`],
                ["CLI runner strategy", `${REPO_BASE}docs/roadmap/cli-runner-strategy.md`]
              ]
            }
          ]
        },
        {
          id: "library",
          title: "Bibliotheque",
          subtitle: "Corpus Markdown du depot avec recherche, filtres et lecture integree.",
          blocks: [
            {
              type: "links",
              title: "Docs produit",
              links: [
                ["Quick Start", `${REPO_BASE}guides/QUICK-START.md`],
                ["CLI Usage", `${REPO_BASE}guides/CLI-USAGE.md`],
                ["Documentation Freshness Audit", `${REPO_BASE}docs/audit/DOCS-FRESHNESS-AUDIT.md`],
                ["Frontend architecture", `${REPO_BASE}docs/modules/frontend-architecture.md`],
                ["Backend architecture", `${REPO_BASE}docs/modules/backend-architecture.md`]
              ]
            },
            {
              type: "links",
              title: "Guides et APIs",
              links: [
                ["Quick Start", `${REPO_BASE}guides/QUICK-START.md`],
                ["Documentation Freshness Audit", `${REPO_BASE}docs/audit/DOCS-FRESHNESS-AUDIT.md`],
                ["CLI API reference", `${REPO_BASE}docs/api/CLI-API-REFERENCE.md`],
                ["IPC API reference", `${REPO_BASE}docs/api/IPC-API-REFERENCE.md`],
                ["Self-hosted deployment", `${REPO_BASE}guides/SELF-HOSTED-DEPLOYMENT.md`]
              ]
            }
          ]
        }
      ]
    }
  }
};
