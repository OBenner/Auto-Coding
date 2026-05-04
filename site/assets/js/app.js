(function initDocsPortal() {
  const RAW_REPO_BASE = "https://raw.githubusercontent.com/OBenner/Auto-Coding/develop/";
  const model = window.AUTO_CODE_DOCS;
  const docsModel = window.AUTO_CODE_MARKDOWN_DOCS || { docs: [], categories: [] };
  const markdownDocs = Array.isArray(docsModel.docs) ? docsModel.docs : [];
  const docsByPath = new Map(markdownDocs.map((doc) => [doc.path, doc]));

  if (!model || !model.locales) {
    return;
  }

  const localeKeys = Object.keys(model.locales);
  const localeMeta = {
    en: { flag: "🇺🇸", label: "English" },
    ru: { flag: "🇷🇺", label: "Русский" },
    fr: { flag: "🇫🇷", label: "Français" }
  };
  const storedLocale = window.localStorage.getItem("auto-code-docs-locale");
  const storedDocPath = window.localStorage.getItem("auto-code-docs-selected-doc");
  const state = {
    locale: localeKeys.includes(storedLocale) ? storedLocale : "ru",
    pageId: window.location.hash.replace("#", "") || "product",
    query: "",
    docsQuery: "",
    docsCategory: "all",
    selectedDocPath: docsByPath.has(storedDocPath) ? storedDocPath : findPreferredDocPath()
  };

  const readerCopy = {
    ru: {
      kicker: "Markdown corpus",
      title: "Документация репозитория, встроенная в сайт",
      intro:
        "Читатель собирает Markdown-файлы из репозитория во время Pages build: можно искать, фильтровать по области продукта, читать исходные документы и переходить по внутренним ссылкам без ухода из портала.",
      search: "Поиск по Markdown",
      searchPlaceholder: "worktree, provider, Graphiti, OAuth, CI...",
      category: "Область",
      all: "Все области",
      documents: "документов",
      words: "слов",
      rendered: "рендерится inline",
      index: "Индекс документов",
      noResults: "Markdown-документы не найдены.",
      source: "Источник",
      openSource: "Открыть на GitHub",
      toc: "Оглавление",
      noToc: "В документе нет заголовков.",
      related: "Рекомендуемые документы",
      readHere: "Читать здесь",
      readerAction: "Docs reader",
      selectedFallback: "Выберите документ в индексе слева.",
      generated: "Индекс обновляется workflow перед публикацией."
    },
    en: {
      kicker: "Markdown corpus",
      title: "Repository documentation rendered inside the site",
      intro:
        "The reader indexes repository Markdown during the Pages build, so visitors can search, filter by product area, read source documents, and follow internal documentation links without leaving the portal.",
      search: "Search Markdown",
      searchPlaceholder: "worktree, provider, Graphiti, OAuth, CI...",
      category: "Area",
      all: "All areas",
      documents: "documents",
      words: "words",
      rendered: "rendered inline",
      index: "Document index",
      noResults: "No Markdown documents found.",
      source: "Source",
      openSource: "Open on GitHub",
      toc: "Contents",
      noToc: "This document has no headings.",
      related: "Recommended documents",
      readHere: "Read here",
      readerAction: "Docs reader",
      selectedFallback: "Choose a document from the index.",
      generated: "The index is rebuilt by the workflow before publishing."
    },
    fr: {
      kicker: "Corpus Markdown",
      title: "Documentation du depot rendue dans le site",
      intro:
        "Le lecteur indexe les fichiers Markdown pendant le build Pages: recherche, filtres par zone produit, lecture des documents source et navigation interne sans quitter le portail.",
      search: "Recherche Markdown",
      searchPlaceholder: "worktree, provider, Graphiti, OAuth, CI...",
      category: "Zone",
      all: "Toutes les zones",
      documents: "documents",
      words: "mots",
      rendered: "rendu inline",
      index: "Index des documents",
      noResults: "Aucun document Markdown trouve.",
      source: "Source",
      openSource: "Ouvrir sur GitHub",
      toc: "Sommaire",
      noToc: "Ce document n'a pas de titres.",
      related: "Documents recommandes",
      readHere: "Lire ici",
      readerAction: "Lecteur docs",
      selectedFallback: "Choisissez un document dans l'index.",
      generated: "L'index est reconstruit par le workflow avant publication."
    }
  };

  const elements = {
    hero: document.querySelector(".hero"),
    brandOverline: document.getElementById("brand-overline"),
    brandTitle: document.getElementById("brand-title"),
    languageLabel: document.getElementById("language-label"),
    languageSwitcher: document.getElementById("language-switcher"),
    languageTrigger: document.getElementById("language-trigger"),
    languageCurrentFlag: document.getElementById("language-current-flag"),
    languageOptions: document.getElementById("language-options"),
    searchLabel: document.getElementById("search-label"),
    searchInput: document.getElementById("search-input"),
    nav: document.getElementById("doc-nav"),
    heroEyebrow: document.getElementById("hero-eyebrow"),
    heroTitle: document.getElementById("hero-title"),
    heroLead: document.getElementById("hero-lead"),
    heroActions: document.getElementById("hero-actions"),
    productSignal: document.getElementById("product-signal"),
    appMap: document.getElementById("app-map"),
    content: document.getElementById("doc-content")
  };

  elements.languageSwitcher.value = state.locale;

  function locale() {
    return model.locales[state.locale];
  }

  function copy() {
    return readerCopy[state.locale] || readerCopy.en;
  }

  function ensurePage() {
    const ids = locale().pages.map((page) => page.id);
    if (!ids.includes(state.pageId)) {
      state.pageId = ids[0];
    }
  }

  function renderChrome() {
    const data = locale();
    const ui = data.ui;
    const showHero = state.pageId === "product";

    document.documentElement.lang = state.locale;
    elements.hero.hidden = !showHero;
    elements.brandOverline.textContent = ui.brandOverline;
    elements.brandTitle.textContent = ui.brandTitle;
    elements.languageLabel.textContent = ui.languageLabel;
    elements.searchLabel.textContent = ui.searchLabel;
    elements.searchInput.placeholder = ui.searchPlaceholder;
    elements.heroEyebrow.textContent = ui.heroEyebrow;
    elements.heroTitle.textContent = ui.heroTitle;
    elements.heroLead.textContent = ui.heroLead;

    elements.heroActions.innerHTML = data.heroActions.map(renderHeroAction).join("");
    renderLanguageMenu();

    elements.productSignal.innerHTML = `
      <div class="signal-header">
        <span class="signal-dot"></span>
        <strong>${escapeHtml(data.productSignal.title)}</strong>
      </div>
      <div class="signal-rows">
        ${data.productSignal.rows
          .map(
            ([label, value]) => `
            <div class="signal-row">
              <span>${escapeHtml(label)}</span>
              <p>${escapeHtml(value)}</p>
            </div>
          `
          )
          .join("")}
      </div>
    `;
  }

  function renderLanguageMenu() {
    const current = localeMeta[state.locale] || localeMeta.en;
    elements.languageSwitcher.value = state.locale;
    elements.languageCurrentFlag.textContent = current.flag;
    elements.languageTrigger.setAttribute("aria-label", current.label);
    elements.languageOptions.innerHTML = localeKeys
      .filter((key) => key !== state.locale)
      .map((key) => {
        const meta = localeMeta[key] || { flag: key.toUpperCase(), label: key };
        return `
          <button type="button" data-locale="${escapeAttribute(key)}" role="menuitem" aria-label="${escapeAttribute(meta.label)}">
            <span aria-hidden="true">${escapeHtml(meta.flag)}</span>
          </button>
        `;
      })
      .join("");
  }

  function setLocale(nextLocale) {
    if (!model.locales[nextLocale] || nextLocale === state.locale) {
      return;
    }

    state.locale = nextLocale;
    window.localStorage.setItem("auto-code-docs-locale", nextLocale);
    render();
  }

  function renderHeroAction(action) {
    const docPath = repoMarkdownPath(action.href);
    if (docPath && docsByPath.has(docPath)) {
      return `<button class="hero-action" type="button" data-doc-path="${escapeAttribute(docPath)}">${escapeHtml(action.label)}</button>`;
    }

    if (action.href.startsWith("#")) {
      return `<a class="hero-action" href="${escapeAttribute(action.href)}">${escapeHtml(action.label)}</a>`;
    }

    return `<a class="hero-action" href="${escapeAttribute(action.href)}" target="_blank" rel="noreferrer">${escapeHtml(
      action.label
    )}</a>`;
  }

  function pageMatchesQuery(page) {
    if (!state.query) {
      return true;
    }

    const text = [page.title, page.subtitle, ...page.blocks.map((block) => JSON.stringify(block))]
      .join(" ")
      .toLowerCase();

    return text.includes(state.query.toLowerCase());
  }

  function renderNavigation() {
    const data = locale();
    const pages = data.pages.filter(pageMatchesQuery);

    if (pages.length === 0) {
      elements.nav.innerHTML = `<div class="empty-state">${escapeHtml(data.ui.navEmpty)}</div>`;
      return;
    }

    if (!pages.some((page) => page.id === state.pageId)) {
      state.pageId = pages[0].id;
      window.location.hash = state.pageId;
    }

    elements.nav.innerHTML = pages
      .map(
        (page) => `
          <button
            type="button"
            class="nav-item ${page.id === state.pageId ? "active" : ""}"
            data-page-id="${escapeAttribute(page.id)}"
          >
            <span>${escapeHtml(page.title)}</span>
            <small>${escapeHtml(page.subtitle)}</small>
          </button>
        `
      )
      .join("");

    elements.nav.querySelectorAll(".nav-item").forEach((button) => {
      button.addEventListener("click", () => {
        state.pageId = button.dataset.pageId;
        window.location.hash = state.pageId;
        render();
      });
    });
  }

  function renderAppMap() {
    const data = locale();
    if (state.pageId !== "product") {
      elements.appMap.hidden = true;
      elements.appMap.innerHTML = "";
      return;
    }

    elements.appMap.hidden = false;
    elements.appMap.innerHTML = `
      <div class="section-heading">
        <h3>${escapeHtml(data.appMap.title)}</h3>
        <p>${escapeHtml(data.appMap.subtitle || data.ui.roadmapUpdated)}</p>
      </div>
      <div class="app-map-grid">
        ${data.appMap.items
          .map(
            (item) => `
            <article class="surface-card">
              <span>${escapeHtml(item.label)}</span>
              <h4>${escapeHtml(item.title)}</h4>
              <p>${escapeHtml(item.text)}</p>
              <code>${escapeHtml(item.source)}</code>
            </article>
          `
          )
          .join("")}
      </div>
    `;
  }

  function renderContent() {
    const data = locale();
    const activePage = data.pages.find((page) => page.id === state.pageId);
    if (!activePage) {
      elements.content.innerHTML = "";
      return;
    }

    const showPageHead = activePage.id !== "product" && activePage.id !== "library";
    const blocks = activePage.blocks.map(renderBlock).join("");
    const reader = activePage.id === "library" ? renderDocsWorkbench() : "";
    const body = activePage.id === "library" ? `${reader}${blocks}` : `${blocks}${reader}`;

    elements.content.innerHTML = `
      ${
        showPageHead
          ? `<section class="page-head">
              <p>${escapeHtml(data.ui.sourceLabel)}</p>
              <h3>${escapeHtml(activePage.title)}</h3>
              <span>${escapeHtml(activePage.subtitle)}</span>
            </section>`
          : ""
      }
      ${body}
    `;

    wireDocsWorkbench();
  }

  function renderBlock(block) {
    switch (block.type) {
      case "notice":
        return renderNotice(block);
      case "workflow":
        return renderWorkflow(block);
      case "cards":
        return renderCards(block);
      case "matrix":
        return renderMatrix(block);
      case "commands":
        return renderCommands(block);
      case "links":
        return renderLinks(block);
      case "timeline":
        return renderTimeline(block);
      case "principles":
        return renderPrinciples(block);
      case "showcase":
        return renderShowcase(block);
      case "examples":
        return renderExamples(block);
      case "architectureMap":
        return renderArchitectureMap(block);
      case "surfaceGallery":
        return renderSurfaceGallery(block);
      default:
        return "";
    }
  }

  function renderNotice(block) {
    return `
      <article class="notice-block">
        <span></span>
        <div>
          <h4>${escapeHtml(block.title)}</h4>
          <p>${escapeHtml(block.text)}</p>
        </div>
      </article>
    `;
  }

  function renderWorkflow(block) {
    return `
      <section class="doc-block">
        <h4>${escapeHtml(block.title)}</h4>
        <div class="workflow">
          ${block.steps
            .map(
              ([title, text], index) => `
              <article class="workflow-step">
                <b>${String(index + 1).padStart(2, "0")}</b>
                <h5>${escapeHtml(title)}</h5>
                <p>${escapeHtml(text)}</p>
              </article>
            `
            )
            .join("")}
        </div>
      </section>
    `;
  }

  function renderCards(block) {
    return `
      <section class="doc-block">
        <h4>${escapeHtml(block.title)}</h4>
        <div class="card-grid">
          ${block.items
            .map(
              (item) => `
              <article class="info-card">
                <h5>${escapeHtml(item.title)}</h5>
                <p>${escapeHtml(item.text)}</p>
                <code>${escapeHtml(item.meta || "")}</code>
              </article>
            `
            )
            .join("")}
        </div>
      </section>
    `;
  }

  function renderMatrix(block) {
    return `
      <section class="doc-block">
        <h4>${escapeHtml(block.title)}</h4>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>${block.columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("")}</tr>
            </thead>
            <tbody>
              ${block.rows
                .map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`)
                .join("")}
            </tbody>
          </table>
        </div>
      </section>
    `;
  }

  function renderCommands(block) {
    return `
      <section class="doc-block">
        <h4>${escapeHtml(block.title)}</h4>
        <div class="command-list">
          ${block.commands
            .map(
              ([label, command]) => `
              <article class="command-card">
                <span>${escapeHtml(label)}</span>
                <pre><code>${escapeHtml(command)}</code></pre>
              </article>
            `
            )
            .join("")}
        </div>
      </section>
    `;
  }

  function renderLinks(block) {
    return `
      <section class="doc-block">
        <h4>${escapeHtml(block.title)}</h4>
        <div class="link-grid">
          ${block.links.map(renderLinkTile).join("")}
        </div>
      </section>
    `;
  }

  function renderLinkTile([label, href]) {
    const docPath = repoMarkdownPath(href);
    if (docPath && docsByPath.has(docPath)) {
      const doc = docsByPath.get(docPath);
      return `
        <button class="doc-link-button" type="button" data-doc-path="${escapeAttribute(docPath)}">
          <span>${escapeHtml(label)}</span>
          <small>${escapeHtml(doc.path)}</small>
          <em>${escapeHtml(copy().readHere)}</em>
        </button>
      `;
    }

    return `
      <a href="${escapeAttribute(href)}" target="_blank" rel="noreferrer">
        <span>${escapeHtml(label)}</span>
        <small>${escapeHtml(shortenUrl(href))}</small>
      </a>
    `;
  }

  function renderTimeline(block) {
    return `
      <section class="doc-block">
        <h4>${escapeHtml(block.title)}</h4>
        <div class="timeline">
          ${block.items
            .map(
              ([status, title, text]) => `
              <article class="timeline-item ${escapeAttribute(status)}">
                <span>${escapeHtml(status)}</span>
                <h5>${escapeHtml(title)}</h5>
                <p>${escapeHtml(text)}</p>
              </article>
            `
            )
            .join("")}
        </div>
      </section>
    `;
  }

  function renderPrinciples(block) {
    return `
      <section class="principles-band">
        <div class="section-heading">
          <h4>${escapeHtml(block.title)}</h4>
          <p>${escapeHtml(block.text || "")}</p>
        </div>
        <div class="principles-grid">
          ${block.items
            .map(
              (item) => `
              <article class="principle-card">
                <span>${escapeHtml(item.label)}</span>
                <h5>${escapeHtml(item.title)}</h5>
                <p>${escapeHtml(item.text)}</p>
              </article>
            `
            )
            .join("")}
        </div>
      </section>
    `;
  }

  function renderShowcase(block) {
    return `
      <section class="showcase-band">
        <div class="showcase-copy">
          <p>${escapeHtml(block.kicker || "")}</p>
          <h4>${escapeHtml(block.title)}</h4>
          <span>${escapeHtml(block.text)}</span>
          <div class="showcase-metrics">
            ${(block.metrics || [])
              .map(
                ([value, label]) => `
                <div>
                  <strong>${escapeHtml(value)}</strong>
                  <small>${escapeHtml(label)}</small>
                </div>
              `
              )
              .join("")}
          </div>
        </div>
        <div class="showcase-console" aria-label="${escapeAttribute(block.title)}">
          <div class="console-topbar">
            <span></span><span></span><span></span>
            <strong>${escapeHtml(block.windowTitle || "agent session")}</strong>
          </div>
          <div class="console-body">
            ${(block.steps || [])
              .map(
                (step, index) => `
                <div class="console-step">
                  <b>${String(index + 1).padStart(2, "0")}</b>
                  <div>
                    <strong>${escapeHtml(step.title)}</strong>
                    <p>${escapeHtml(step.text)}</p>
                  </div>
                </div>
              `
              )
              .join("")}
          </div>
          <pre><code>${escapeHtml((block.terminal || []).join("\n"))}</code></pre>
        </div>
      </section>
    `;
  }

  function renderExamples(block) {
    return `
      <section class="examples-band">
        <div class="section-heading">
          <h4>${escapeHtml(block.title)}</h4>
          <p>${escapeHtml(block.text || "")}</p>
        </div>
        <div class="example-grid">
          ${block.items
            .map(
              (item) => `
              <article class="example-card">
                <div>
                  <span>${escapeHtml(item.label)}</span>
                  <h5>${escapeHtml(item.title)}</h5>
                  <p>${escapeHtml(item.text)}</p>
                </div>
                <pre><code>${escapeHtml(item.command)}</code></pre>
                ${
                  item.docPath && docsByPath.has(item.docPath)
                    ? `<button type="button" data-doc-path="${escapeAttribute(item.docPath)}">${escapeHtml(copy().readHere)}</button>`
                    : ""
                }
              </article>
            `
            )
            .join("")}
        </div>
      </section>
    `;
  }

  function renderArchitectureMap(block) {
    return `
      <section class="architecture-map-band">
        <div class="section-heading">
          <h4>${escapeHtml(block.title)}</h4>
          <p>${escapeHtml(block.text || "")}</p>
        </div>
        <div class="architecture-flow">
          ${(block.nodes || [])
            .map(
              (node, index) => `
              <article class="architecture-node">
                <b>${String(index + 1).padStart(2, "0")}</b>
                <span>${escapeHtml(node.label)}</span>
                <h5>${escapeHtml(node.title)}</h5>
                <p>${escapeHtml(node.text)}</p>
                <code>${escapeHtml(node.meta || "")}</code>
              </article>
            `
            )
            .join("")}
        </div>
        <div class="architecture-evidence">
          ${(block.evidence || []).map((item) => `<span>${escapeHtml(item)}</span>`).join("")}
        </div>
      </section>
    `;
  }

  function renderSurfaceGallery(block) {
    return `
      <section class="surface-gallery-band">
        <div class="section-heading">
          <h4>${escapeHtml(block.title)}</h4>
          <p>${escapeHtml(block.text || "")}</p>
        </div>
        <div class="surface-preview-grid">
          ${(block.screens || []).map(renderSurfacePreview).join("")}
        </div>
      </section>
    `;
  }

  function renderSurfacePreview(screen) {
    return `
      <article class="product-screen">
        <div class="screen-topbar">
          <span></span><span></span><span></span>
          <strong>${escapeHtml(screen.label)}</strong>
        </div>
        <div class="screen-stage">
          <aside>
            ${(screen.rail || []).map((item) => `<span>${escapeHtml(item)}</span>`).join("")}
          </aside>
          <div class="screen-main">
            <div class="screen-title-row">
              <div>
                <h5>${escapeHtml(screen.title)}</h5>
                <p>${escapeHtml(screen.caption || "")}</p>
              </div>
              <em>${escapeHtml(screen.badge || "")}</em>
            </div>
            <div class="screen-card-list">
              ${(screen.cards || [])
                .map(
                  (card) => `
                  <div class="screen-card">
                    <span>${escapeHtml(card.label)}</span>
                    <strong>${escapeHtml(card.title)}</strong>
                    <small>${escapeHtml(card.detail)}</small>
                  </div>
                `
                )
                .join("")}
            </div>
            <code>${escapeHtml(screen.source || "")}</code>
          </div>
        </div>
      </article>
    `;
  }

  function renderRelatedDocs(pageId) {
    if (markdownDocs.length === 0) {
      return "";
    }

    const selected = pickRelatedDocs(pageId);
    if (selected.length === 0) {
      return "";
    }

    return `
      <section class="doc-block related-docs">
        <div class="section-heading">
          <h4>${escapeHtml(copy().related)}</h4>
          <p>${escapeHtml(copy().generated)}</p>
        </div>
        <div class="related-doc-grid">
          ${selected
            .map(
              (doc) => `
              <button class="related-doc" type="button" data-doc-path="${escapeAttribute(doc.path)}">
                <span>${escapeHtml(doc.category)}</span>
                <strong>${escapeHtml(doc.title)}</strong>
                <small>${escapeHtml(doc.path)}</small>
              </button>
            `
            )
            .join("")}
        </div>
      </section>
    `;
  }

  function pickRelatedDocs(pageId) {
    const preferredPaths = {
      product: ["README.md", "guides/QUICK-START.md", "docs/audit/DOCS-FRESHNESS-AUDIT.md", "docs/README.md"],
      runtime: [
        "docs/architecture/provider-runtime-modes.md",
        "docs/architecture/provider-abstraction.md",
        "docs/configuration/environment-vars.md",
        "docs/architecture/adr/ADR-004-multi-provider-support.md"
      ],
      desktop: [
        "docs/frontend/provider-selection-ui.md",
        "docs/modules/frontend-architecture.md",
        "apps/frontend/README.md",
        "guides/INTEGRATION-ELECTRON-MCP.md"
      ],
      architecture: [
        "docs/modules/backend-architecture.md",
        "docs/modules/frontend-architecture.md",
        "docs/architecture/adr/ADR-003-worktree-isolation.md",
        "docs/architecture/mcp-client-design.md"
      ],
      operations: [
        "guides/CLI-USAGE.md",
        "guides/ci-cd-integration.md",
        "guides/TROUBLESHOOTING.md",
        "RELEASE.md"
      ],
      roadmap: [
        "docs/roadmap/README.md",
        "docs/roadmap/implementation-phases.md",
        "docs/roadmap/cli-runner-strategy.md",
        "docs/roadmap/migration-guide.md"
      ]
    };

    return (preferredPaths[pageId] || []).map((pathName) => docsByPath.get(pathName)).filter(Boolean);
  }

  function renderDocsWorkbench() {
    const docs = filteredDocs();
    const selectedDoc = selectedDocForList(docs);
    const stats = [
      [formatNumber(docsModel.totalDocuments || markdownDocs.length), copy().documents],
      [formatNumber(docsModel.totalWords || 0), copy().words],
      [copy().rendered, "file:// + GitHub Pages"]
    ];

    return `
      <section class="docs-workbench" id="docs-reader">
        <header class="reader-hero">
          <div>
            <p class="reader-kicker">${escapeHtml(copy().kicker)}</p>
            <h4>${escapeHtml(copy().title)}</h4>
            <p>${escapeHtml(copy().intro)}</p>
          </div>
          <div class="reader-stats">
            ${stats
              .map(
                ([value, label]) => `
                <div>
                  <strong>${escapeHtml(value)}</strong>
                  <span>${escapeHtml(label)}</span>
                </div>
              `
              )
              .join("")}
          </div>
        </header>

        <div class="reader-toolbar">
          <label>
            <span>${escapeHtml(copy().search)}</span>
            <input id="docs-search-input" type="search" value="${escapeAttribute(state.docsQuery)}" placeholder="${escapeAttribute(
              copy().searchPlaceholder
            )}" />
          </label>
          <label>
            <span>${escapeHtml(copy().category)}</span>
            <select id="docs-category-select">
              <option value="all">${escapeHtml(copy().all)}</option>
              ${(docsModel.categories || [])
                .map(
                  (category) =>
                    `<option value="${escapeAttribute(category)}" ${
                      state.docsCategory === category ? "selected" : ""
                    }>${escapeHtml(category)}</option>`
                )
                .join("")}
            </select>
          </label>
        </div>

        <div class="reader-layout">
          <aside class="doc-index" aria-label="${escapeAttribute(copy().index)}">
            <div class="doc-index-heading">
              <strong>${escapeHtml(copy().index)}</strong>
              <span>${formatNumber(docs.length)} ${escapeHtml(copy().documents)}</span>
            </div>
            <div class="doc-list">
              ${docs.length === 0 ? `<p class="empty-docs">${escapeHtml(copy().noResults)}</p>` : docs.map(renderDocListItem).join("")}
            </div>
          </aside>
          ${selectedDoc ? renderMarkdownPanel(selectedDoc) : renderEmptyMarkdownPanel()}
          ${selectedDoc ? renderDocToc(selectedDoc) : ""}
        </div>
      </section>
    `;
  }

  function renderDocListItem(doc) {
    return `
      <button
        class="doc-list-item ${doc.path === state.selectedDocPath ? "active" : ""}"
        type="button"
        data-doc-path="${escapeAttribute(doc.path)}"
      >
        <span>${escapeHtml(doc.category)}</span>
        <strong>${escapeHtml(doc.title)}</strong>
        <small>${escapeHtml(doc.path)}</small>
      </button>
    `;
  }

  function renderMarkdownPanel(doc) {
    return `
      <article class="markdown-panel">
        <header class="reader-titlebar">
          <p>${escapeHtml(copy().source)} / ${escapeHtml(doc.category)}</p>
          <h4>${escapeHtml(doc.title)}</h4>
          <span>${escapeHtml(doc.description)}</span>
          <div class="doc-actions">
            <code>${escapeHtml(doc.path)}</code>
            <a href="${escapeAttribute(sourceUrl(doc.path))}" target="_blank" rel="noreferrer">${escapeHtml(copy().openSource)}</a>
          </div>
        </header>
        <div class="markdown-body">
          ${renderMarkdown(doc.content, doc.path)}
        </div>
      </article>
    `;
  }

  function renderEmptyMarkdownPanel() {
    return `
      <article class="markdown-panel empty-reader">
        <p>${escapeHtml(copy().selectedFallback)}</p>
      </article>
    `;
  }

  function renderDocToc(doc) {
    const headings = doc.headings || [];
    return `
      <aside class="doc-toc">
        <strong>${escapeHtml(copy().toc)}</strong>
        ${
          headings.length === 0
            ? `<p>${escapeHtml(copy().noToc)}</p>`
            : headings
                .map(
                  (heading) => `
                  <button
                    type="button"
                    class="toc-item level-${Number(heading.level)}"
                    data-scroll-target="${escapeAttribute(heading.id)}"
                  >
                    ${escapeHtml(heading.title)}
                  </button>
                `
                )
                .join("")
        }
      </aside>
    `;
  }

  function filteredDocs() {
    const query = state.docsQuery.trim().toLowerCase();
    return markdownDocs.filter((doc) => {
      if (state.docsCategory !== "all" && doc.category !== state.docsCategory) {
        return false;
      }

      if (!query) {
        return true;
      }

      const haystack = [doc.title, doc.path, doc.description, doc.category, doc.content].join(" ").toLowerCase();
      return haystack.includes(query);
    });
  }

  function selectedDocForList(docs) {
    if (docsByPath.has(state.selectedDocPath) && docs.some((doc) => doc.path === state.selectedDocPath)) {
      return docsByPath.get(state.selectedDocPath);
    }

    const first = docs[0] || docsByPath.get(state.selectedDocPath) || markdownDocs[0];
    if (first) {
      state.selectedDocPath = first.path;
      window.localStorage.setItem("auto-code-docs-selected-doc", first.path);
    }
    return first;
  }

  function wireDocsWorkbench() {
    const docsSearch = document.getElementById("docs-search-input");
    if (docsSearch) {
      docsSearch.addEventListener("input", (event) => {
        state.docsQuery = event.target.value;
        renderContent();
      });
    }

    const docsCategory = document.getElementById("docs-category-select");
    if (docsCategory) {
      docsCategory.addEventListener("change", (event) => {
        state.docsCategory = event.target.value;
        renderContent();
      });
    }
  }

  function openDoc(docPath) {
    if (!docsByPath.has(docPath)) {
      return;
    }

    state.selectedDocPath = docPath;
    state.pageId = "library";
    window.localStorage.setItem("auto-code-docs-selected-doc", docPath);
    if (window.location.hash !== "#library") {
      window.location.hash = "library";
    } else {
      render();
    }
    requestAnimationFrame(() => {
      document.getElementById("docs-reader")?.scrollIntoView({ block: "start" });
    });
  }

  function scrollToMarkdownHeading(id) {
    document.getElementById(id)?.scrollIntoView({ block: "start", behavior: "smooth" });
  }

  function renderMarkdown(markdown, docPath) {
    const lines = normalizeMarkdownInput(markdown).replaceAll("\r\n", "\n").replaceAll("\r", "\n").split("\n");
    const html = [];
    const headingUsage = new Map();
    let paragraph = [];
    let listType = null;
    let codeLanguage = "";
    let codeLines = null;

    function closeParagraph() {
      if (paragraph.length > 0) {
        html.push(`<p>${paragraph.map((line) => renderInline(line, docPath)).join(" ")}</p>`);
        paragraph = [];
      }
    }

    function closeList() {
      if (listType) {
        html.push(`</${listType}>`);
        listType = null;
      }
    }

    function openList(nextType) {
      if (listType !== nextType) {
        closeParagraph();
        closeList();
        listType = nextType;
        html.push(`<${listType}>`);
      }
    }

    for (let index = 0; index < lines.length; index += 1) {
      const rawLine = lines[index];
      const trimmed = rawLine.trim();

      if (codeLines) {
        if (trimmed.startsWith("```")) {
          html.push(
            `<pre><code class="${escapeAttribute(codeLanguage ? `language-${codeLanguage}` : "")}">${escapeHtml(
              codeLines.join("\n")
            )}</code></pre>`
          );
          codeLines = null;
          codeLanguage = "";
        } else {
          codeLines.push(rawLine);
        }
        continue;
      }

      if (trimmed.startsWith("```")) {
        closeParagraph();
        closeList();
        codeLanguage = trimmed.slice(3).trim();
        codeLines = [];
        continue;
      }

      if (!trimmed) {
        closeParagraph();
        closeList();
        continue;
      }

      const tableRows = collectTable(lines, index);
      if (tableRows) {
        closeParagraph();
        closeList();
        html.push(renderMarkdownTable(tableRows, docPath));
        index += tableRows.length;
        continue;
      }

      const heading = parseHeading(trimmed);
      if (heading) {
        closeParagraph();
        closeList();
        const level = Math.min(heading.level, 4);
        const title = heading.title;
        const id = slugifyHeading(title, headingUsage);
        html.push(`<h${level} id="${escapeAttribute(id)}">${renderInline(title, docPath)}</h${level}>`);
        continue;
      }

      if (isHorizontalRule(trimmed)) {
        closeParagraph();
        closeList();
        html.push("<hr />");
        continue;
      }

      const unordered = parseUnorderedListItem(trimmed);
      if (unordered) {
        openList("ul");
        html.push(`<li>${renderInline(unordered, docPath)}</li>`);
        continue;
      }

      const ordered = parseOrderedListItem(trimmed);
      if (ordered) {
        openList("ol");
        html.push(`<li>${renderInline(ordered, docPath)}</li>`);
        continue;
      }

      if (trimmed.startsWith(">")) {
        closeParagraph();
        closeList();
        const quote = trimmed.startsWith("> ") ? trimmed.slice(2) : trimmed.slice(1);
        html.push(`<blockquote>${renderInline(quote, docPath)}</blockquote>`);
        continue;
      }

      paragraph.push(trimmed);
    }

    if (codeLines) {
      html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
    }
    closeParagraph();
    closeList();
    return html.join("");
  }

  function parseHeading(value) {
    let level = 0;
    while (level < value.length && value[level] === "#") {
      level += 1;
    }
    if (level < 1 || level > 6 || !isWhitespace(value[level])) {
      return null;
    }
    const title = value.slice(level).trim();
    return title ? { level, title } : null;
  }

  function isHorizontalRule(value) {
    return value.length >= 3 && (everyChar(value, "-") || everyChar(value, "*"));
  }

  function parseUnorderedListItem(value) {
    if (value.length < 3 || !"-*+".includes(value[0]) || !isWhitespace(value[1])) {
      return null;
    }
    return value.slice(2).trim();
  }

  function parseOrderedListItem(value) {
    let cursor = 0;
    while (cursor < value.length && isDigit(value[cursor])) {
      cursor += 1;
    }
    if (cursor === 0 || value[cursor] !== "." || !isWhitespace(value[cursor + 1])) {
      return null;
    }
    return value.slice(cursor + 2).trim();
  }

  function collectTable(lines, index) {
    const header = lines[index]?.trim();
    const separator = lines[index + 1]?.trim();
    if (!header || !separator || !header.includes("|") || !isTableSeparator(separator)) {
      return null;
    }

    const rows = [header];
    let cursor = index + 2;
    while (cursor < lines.length && lines[cursor].trim().includes("|") && lines[cursor].trim()) {
      rows.push(lines[cursor].trim());
      cursor += 1;
    }
    return rows;
  }

  function isTableSeparator(value) {
    const cells = parseTableRow(value);
    return cells.length > 1 && cells.every((cell) => {
      const compact = cell.trim();
      const core = compact.startsWith(":") ? compact.slice(1) : compact;
      const normalized = core.endsWith(":") ? core.slice(0, -1) : core;
      return normalized.length >= 3 && everyChar(normalized, "-");
    });
  }

  function parseTableRow(value) {
    let row = String(value);
    if (row.startsWith("|")) {
      row = row.slice(1);
    }
    if (row.endsWith("|")) {
      row = row.slice(0, -1);
    }
    return row.split("|").map((cell) => cell.trim());
  }

  function renderMarkdownTable(rows, docPath) {
    const header = parseTableRow(rows[0]);
    const body = rows.slice(1).map(parseTableRow);
    return `
      <div class="markdown-table">
        <table>
          <thead><tr>${header.map((cell) => `<th>${renderInline(cell, docPath)}</th>`).join("")}</tr></thead>
          <tbody>
            ${body
              .map((row) => `<tr>${row.map((cell) => `<td>${renderInline(cell, docPath)}</td>`).join("")}</tr>`)
              .join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  function renderInline(value, docPath) {
    const source = String(value);
    let html = "";
    let cursor = 0;

    function appendText(nextCursor) {
      if (nextCursor > cursor) {
        html += escapeHtml(source.slice(cursor, nextCursor));
      }
      cursor = nextCursor;
    }

    while (cursor < source.length) {
      const linkedImage = readLinkedImage(source, cursor);
      if (linkedImage) {
        const image = renderInlineImage(linkedImage.alt, linkedImage.imageHref, docPath);
        html += linkedImage.linkHref
          ? `<a href="${escapeAttribute(resolveHref(docPath, linkedImage.linkHref))}" target="_blank" rel="noreferrer">${image}</a>`
          : image;
        cursor = linkedImage.end;
        continue;
      }

      const image = readMarkdownTarget(source, cursor, "![");
      if (image) {
        html += renderInlineImage(image.label, image.href, docPath);
        cursor = image.end;
        continue;
      }

      if (source.startsWith("**", cursor)) {
        const end = source.indexOf("**", cursor + 2);
        if (end > cursor + 2) {
          html += `<strong>${escapeHtml(source.slice(cursor + 2, end))}</strong>`;
          cursor = end + 2;
          continue;
        }
      }

      if (source[cursor] === "`") {
        const end = source.indexOf("`", cursor + 1);
        if (end > cursor + 1) {
          html += `<code>${escapeHtml(source.slice(cursor + 1, end))}</code>`;
          cursor = end + 1;
          continue;
        }
      }

      if (source[cursor] === "*" && canStartEmphasis(source, cursor)) {
        const end = source.indexOf("*", cursor + 1);
        if (end > cursor + 1 && !source.slice(cursor + 1, end).includes("\n")) {
          html += `<em>${escapeHtml(source.slice(cursor + 1, end))}</em>`;
          cursor = end + 1;
          continue;
        }
      }

      const link = readMarkdownTarget(source, cursor, "[");
      if (link) {
        html += renderInlineLink(escapeHtml(link.label), link.href, docPath);
        cursor = link.end;
        continue;
      }

      appendText(cursor + 1);
    }

    return html;
  }

  function renderInlineImage(alt, href, docPath) {
    const rawHref = unescapeHtml(href);
    return `<img class="markdown-image" src="${escapeAttribute(resolveAssetHref(docPath, rawHref))}" alt="${escapeAttribute(
      unescapeHtml(alt)
    )}" loading="lazy" />`;
  }

  function renderInlineLink(label, href, docPath) {
    const rawHref = unescapeHtml(href);
    if (rawHref.startsWith("#")) {
      return `<a href="${escapeAttribute(rawHref)}">${label}</a>`;
    }

    const internalDocPath = resolveInternalDocPath(docPath, rawHref);
    if (internalDocPath && docsByPath.has(internalDocPath)) {
      return `<button type="button" class="inline-doc-link" data-doc-path="${escapeAttribute(internalDocPath)}">${label}</button>`;
    }

    return `<a href="${escapeAttribute(resolveHref(docPath, rawHref))}" target="_blank" rel="noreferrer">${label}</a>`;
  }

  function readLinkedImage(source, cursor) {
    if (!source.startsWith("[![", cursor)) {
      return null;
    }
    const image = readMarkdownTarget(source, cursor + 1, "![");
    if (!image || !source.startsWith("](", image.end)) {
      return null;
    }
    const linkStart = image.end + 2;
    const linkEnd = source.indexOf(")", linkStart);
    if (linkEnd < linkStart) {
      return null;
    }
    return {
      alt: image.label,
      imageHref: image.href,
      linkHref: source.slice(linkStart, linkEnd).trim(),
      end: linkEnd + 1
    };
  }

  function readMarkdownTarget(source, cursor, prefix) {
    if (!source.startsWith(prefix, cursor)) {
      return null;
    }
    const labelStart = cursor + prefix.length;
    const labelEnd = source.indexOf("](", labelStart);
    if (labelEnd < labelStart) {
      return null;
    }
    const hrefStart = labelEnd + 2;
    const hrefEnd = source.indexOf(")", hrefStart);
    if (hrefEnd < hrefStart) {
      return null;
    }
    return {
      label: source.slice(labelStart, labelEnd),
      href: source.slice(hrefStart, hrefEnd).trim(),
      end: hrefEnd + 1
    };
  }

  function canStartEmphasis(source, cursor) {
    if (source.startsWith("**", cursor)) {
      return false;
    }
    if (cursor === 0) {
      return true;
    }
    return isWhitespace(source[cursor - 1]) || source[cursor - 1] === "(";
  }

  function render() {
    ensurePage();
    renderNavigation();
    renderChrome();
    renderAppMap();
    renderContent();
  }

  elements.languageSwitcher.addEventListener("change", (event) => {
    setLocale(event.target.value);
  });

  elements.languageTrigger.addEventListener("click", (event) => {
    event.stopPropagation();
    const expanded = elements.languageTrigger.getAttribute("aria-expanded") === "true";
    elements.languageTrigger.setAttribute("aria-expanded", String(!expanded));
    document.getElementById("language-menu")?.classList.toggle("is-open", !expanded);
  });

  elements.languageOptions.addEventListener("click", (event) => {
    event.stopPropagation();
    const button = event.target.closest("[data-locale]");
    if (!button) {
      return;
    }

    document.getElementById("language-menu")?.classList.remove("is-open");
    elements.languageTrigger.setAttribute("aria-expanded", "false");
    setLocale(button.dataset.locale);
  });

  document.addEventListener("click", (event) => {
    if (event.target.closest("#language-menu")) {
      return;
    }

    document.getElementById("language-menu")?.classList.remove("is-open");
    elements.languageTrigger.setAttribute("aria-expanded", "false");
  });

  elements.searchInput.addEventListener("input", (event) => {
    state.query = event.target.value.trim();
    render();
  });

  elements.content.addEventListener("click", (event) => {
    const docButton = event.target.closest("[data-doc-path]");
    if (docButton) {
      openDoc(docButton.dataset.docPath);
      return;
    }

    const tocButton = event.target.closest("[data-scroll-target]");
    if (tocButton) {
      scrollToMarkdownHeading(tocButton.dataset.scrollTarget);
    }
  });

  elements.heroActions.addEventListener("click", (event) => {
    const docButton = event.target.closest("[data-doc-path]");
    if (docButton) {
      openDoc(docButton.dataset.docPath);
    }
  });

  window.addEventListener("hashchange", () => {
    state.pageId = window.location.hash.replace("#", "") || "product";
    render();
  });

  render();

  function findPreferredDocPath() {
    const preferred = [
      "README.md",
      "guides/QUICK-START.md",
      "docs/audit/DOCS-FRESHNESS-AUDIT.md",
      "docs/architecture/provider-runtime-modes.md"
    ];
    return preferred.find((pathName) => docsByPath.has(pathName)) || markdownDocs[0]?.path || "";
  }

  function repoMarkdownPath(href) {
    if (!href || !href.startsWith(REPO_BASE)) {
      return null;
    }
    const withoutBase = href.slice(REPO_BASE.length).split("#")[0].split("?")[0];
    return withoutBase.endsWith(".md") ? withoutBase : null;
  }

  function resolveInternalDocPath(basePath, href) {
    if (!href || href.startsWith("http://") || href.startsWith("https://") || href.startsWith("#")) {
      return repoMarkdownPath(href);
    }

    const cleanHref = href.split("#")[0].split("?")[0];
    if (!cleanHref.endsWith(".md")) {
      return null;
    }

    if (cleanHref.startsWith("/")) {
      return normalizeDocPath(cleanHref.slice(1));
    }

    const baseDirectory = basePath.includes("/") ? basePath.slice(0, basePath.lastIndexOf("/") + 1) : "";
    return normalizeDocPath(`${baseDirectory}${cleanHref}`);
  }

  function normalizeDocPath(value) {
    const parts = [];
    for (const part of value.split("/")) {
      if (!part || part === ".") {
        continue;
      }
      if (part === "..") {
        parts.pop();
      } else {
        parts.push(part);
      }
    }
    return parts.join("/");
  }

  function resolveHref(basePath, href) {
    if (!href || href.startsWith("#")) {
      return sourceUrl(basePath);
    }
    if (href.startsWith("http://") || href.startsWith("https://") || href.startsWith("mailto:")) {
      return href;
    }
    const internalDocPath = resolveInternalDocPath(basePath, href);
    if (internalDocPath) {
      return sourceUrl(internalDocPath);
    }
    const baseDirectory = basePath.includes("/") ? basePath.slice(0, basePath.lastIndexOf("/") + 1) : "";
    return `${REPO_BASE}${normalizeDocPath(`${baseDirectory}${href}`)}`;
  }

  function resolveAssetHref(basePath, href) {
    if (!href) {
      return "";
    }
    if (href.startsWith("http://") || href.startsWith("https://") || href.startsWith("data:")) {
      return href;
    }
    if (href.startsWith("/")) {
      return `${RAW_REPO_BASE}${normalizeDocPath(href.slice(1))}`;
    }
    const baseDirectory = basePath.includes("/") ? basePath.slice(0, basePath.lastIndexOf("/") + 1) : "";
    return `${RAW_REPO_BASE}${normalizeDocPath(`${baseDirectory}${href}`)}`;
  }

  function sourceUrl(pathName) {
    return `${REPO_BASE}${pathName}`;
  }

  function shortenUrl(value) {
    return value.replace(REPO_BASE, "");
  }

  function slugifyHeading(text, used) {
    const base = slugBase(stripMarkdown(text)) || "section";
    const currentCount = used.get(base) || 0;
    used.set(base, currentCount + 1);
    return currentCount === 0 ? base : `${base}-${currentCount + 1}`;
  }

  function stripMarkdown(value) {
    const source = String(value);
    let output = "";
    let cursor = 0;
    while (cursor < source.length) {
      const image = readMarkdownTarget(source, cursor, "![");
      if (image) {
        output += ` ${image.label} `;
        cursor = image.end;
        continue;
      }
      const link = readMarkdownTarget(source, cursor, "[");
      if (link) {
        output += ` ${link.label} `;
        cursor = link.end;
        continue;
      }
      if (source[cursor] === "`") {
        const end = source.indexOf("`", cursor + 1);
        if (end > cursor + 1) {
          output += ` ${source.slice(cursor + 1, end)} `;
          cursor = end + 1;
          continue;
        }
      }
      output += "#>*_~|`-".includes(source[cursor]) ? " " : source[cursor];
      cursor += 1;
    }
    return collapseWhitespace(output);
  }

  function normalizeMarkdownInput(value) {
    const withoutComments = removeHtmlComments(String(value || ""));
    const withImages = convertHtmlImages(withoutComments);
    return withImages
      .split("\n")
      .map((line) => (isStandaloneWrapperTag(line.trim()) ? "" : replaceBreakTags(line)))
      .join("\n");
  }

  function slugBase(value) {
    let slug = "";
    let pendingDash = false;
    for (const char of stripCombiningMarks(value).toLowerCase()) {
      if (isSlugCharacter(char)) {
        if (pendingDash && slug) {
          slug += "-";
        }
        slug += char;
        pendingDash = false;
      } else {
        pendingDash = true;
      }
    }
    return slug;
  }

  function stripCombiningMarks(value) {
    let output = "";
    for (const char of String(value).normalize("NFKD")) {
      const code = char.codePointAt(0);
      if (code >= 0x0300 && code <= 0x036f) {
        continue;
      }
      output += char;
    }
    return output;
  }

  function removeHtmlComments(value) {
    let output = "";
    let cursor = 0;
    while (cursor < value.length) {
      const start = value.indexOf("<!--", cursor);
      if (start === -1) {
        output += value.slice(cursor);
        break;
      }
      output += value.slice(cursor, start);
      const end = value.indexOf("-->", start + 4);
      cursor = end === -1 ? value.length : end + 3;
    }
    return output;
  }

  function convertHtmlImages(value) {
    let output = "";
    let cursor = 0;
    const lower = value.toLowerCase();
    while (cursor < value.length) {
      const start = lower.indexOf("<img", cursor);
      if (start === -1) {
        output += value.slice(cursor);
        break;
      }
      output += value.slice(cursor, start);
      const end = value.indexOf(">", start + 4);
      if (end === -1) {
        output += value.slice(start);
        break;
      }
      const tag = value.slice(start, end + 1);
      const src = readHtmlAttribute(tag, "src");
      const alt = readHtmlAttribute(tag, "alt") || "";
      output += src ? `![${alt}](${src})` : "";
      cursor = end + 1;
    }
    return output;
  }

  function readHtmlAttribute(tag, name) {
    const lower = tag.toLowerCase();
    const needle = `${name.toLowerCase()}=`;
    const start = lower.indexOf(needle);
    if (start === -1) {
      return "";
    }
    const valueStart = start + needle.length;
    const quote = tag[valueStart];
    if (quote !== "\"" && quote !== "'") {
      return "";
    }
    const valueEnd = tag.indexOf(quote, valueStart + 1);
    return valueEnd === -1 ? "" : tag.slice(valueStart + 1, valueEnd);
  }

  function isStandaloneWrapperTag(value) {
    if (!value.startsWith("<") || !value.endsWith(">")) {
      return false;
    }
    const lower = value.toLowerCase();
    return ["<div", "</div", "<p", "</p", "<center", "</center"].some((prefix) => lower.startsWith(prefix));
  }

  function replaceBreakTags(value) {
    return value
      .replaceAll("<br>", "\n")
      .replaceAll("<br/>", "\n")
      .replaceAll("<br />", "\n")
      .replaceAll("<BR>", "\n")
      .replaceAll("<BR/>", "\n")
      .replaceAll("<BR />", "\n");
  }

  function collapseWhitespace(value) {
    let output = "";
    let pendingSpace = false;
    for (const char of String(value)) {
      if (isWhitespace(char)) {
        pendingSpace = output.length > 0;
      } else {
        if (pendingSpace) {
          output += " ";
          pendingSpace = false;
        }
        output += char;
      }
    }
    return output.trim();
  }

  function isSlugCharacter(char) {
    const code = char.codePointAt(0);
    return (
      (code >= 48 && code <= 57) ||
      (code >= 97 && code <= 122) ||
      (code >= 1072 && code <= 1103) ||
      char === "ё"
    );
  }

  function isDigit(char) {
    return char >= "0" && char <= "9";
  }

  function isWhitespace(char) {
    return char === " " || char === "\t" || char === "\n" || char === "\r";
  }

  function everyChar(value, expected) {
    if (!value) {
      return false;
    }
    for (const char of value) {
      if (char !== expected) {
        return false;
      }
    }
    return true;
  }

  function formatNumber(value) {
    return new Intl.NumberFormat(state.locale === "ru" ? "ru-RU" : state.locale).format(Number(value) || 0);
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll("\"", "&quot;")
      .replaceAll("'", "&#39;");
  }

  function escapeAttribute(value) {
    return escapeHtml(value).replaceAll("`", "&#96;");
  }

  function unescapeHtml(value) {
    return String(value)
      .replaceAll("&amp;", "&")
      .replaceAll("&lt;", "<")
      .replaceAll("&gt;", ">")
      .replaceAll("&quot;", "\"")
      .replaceAll("&#39;", "'");
  }
})();
