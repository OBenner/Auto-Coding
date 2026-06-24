# @auto-code/ui

Shared Auto Code design system and UI components, consumed by both the Electron
desktop app (`apps/frontend`) and the web app (`apps/web-frontend`). Presentational
and transport-agnostic: components take props/callbacks; data is injected per app
(IPC on desktop, REST/WS on web) via the planned `AutoCodeClient` ports-and-adapters
pattern (introduced at the Kanban pilot — see `docs/strategy/roadmap.md`, Track D).

Source of design truth: `.lazyweb/mockups/` (`_desktop-tokens.css` + screen mockups).

## Current contents (U0 foundation)

- `src/tokens/tokens.css` — design tokens (light + `[data-theme="dark"]`). Import once
  per app: `import '@auto-code/ui/tokens.css'`. Variables only — non-breaking.
- `src/theme/ThemeProvider.tsx` — `ThemeProvider` + `useTheme()`; sets `data-theme`
  on `<html>`, resolves `system` from `prefers-color-scheme`, persists the override.
- `src/shell/AppShell.tsx` — layout primitive (sidebar / topbar / main / statusbar slots).

## Usage

```tsx
import '@auto-code/ui/tokens.css';
import { ThemeProvider, AppShell } from '@auto-code/ui';

<ThemeProvider>
  <AppShell sidebar={<Sidebar />} topbar={<TopBar />} main={<Page />} />
</ThemeProvider>
```

## Roadmap (Track D)

U0 foundation (this) → U0.4 Sidebar → U0.5 Storybook → U1 Kanban pilot (introduces
`AutoCodeClient`) → canonical screens → chrome → states → remaining views.
