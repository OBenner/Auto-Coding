# Visual Build Timeline

The Visual Build Timeline is an interactive visualization component in the Auto Code desktop UI that displays agent execution phases, subtasks, and their relationships in real-time.

## Overview

When viewing a task's details, the **Timeline** tab shows a horizontal timeline with:

- **Phase swim lanes** — color-coded rows for each execution phase (Planning, Coding, QA Review, QA Fix)
- **Subtask blocks** — individual work items positioned within their phase lane
- **Dependency connectors** — SVG bezier curves showing relationships between phases and subtasks
- **Real-time progress** — live updates as agents execute, with pulsing indicators for active items

## Features

### Zoom & Pan

- **Ctrl/Cmd + scroll wheel** — zoom in/out centered on cursor position
- **Middle mouse button drag** — pan the viewport
- **Zoom controls** (top-right) — buttons for zoom in, zoom out, and reset to 100%
- Zoom range: 50%–200%

### Phase Color Coding

Each phase is color-coded by agent type:

| Agent Type | Color |
|-----------|-------|
| Planner | Amber |
| Coder | Blue |
| QA | Purple |
| Inactive | Gray |
| Error | Red |

### Subtask Status Indicators

Subtask blocks display their current status with:

- **Left border color** — matches status (active, completed, failed, pending)
- **Status icon** — spinner for in-progress, checkmark for completed, alert for failed, hourglass for pending
- **Time tracking** — estimated vs actual time with over/under variance indicators
- **Expandable details** — click to expand and see full description, file lists, verification steps, and notes

### Export

- **Export as PNG** — captures the timeline visualization as a high-DPI image
- **Copy to clipboard** — copies the timeline image directly to clipboard (when supported)
- Export automatically excludes UI controls (zoom buttons, pan controls)

### Internationalization

The timeline fully supports internationalization:

- All user-facing text uses `react-i18next` translation keys
- English and French translations included (`timeline` namespace)
- No hardcoded English strings

## Architecture

### Component Structure

```text
timeline/
├── BuildTimeline.tsx          # Main container with zoom/pan state
├── PhaseSwimLane.tsx          # Phase row with color coding
├── SubtaskBlock.tsx           # Subtask card with status/time
├── DependencyConnector.tsx    # SVG dependency lines
├── TimelineControls.tsx       # Zoom/pan/export buttons
├── types.ts                   # TypeScript interfaces
├── hooks/
│   ├── useTimelineData.ts     # Data loading & transformation
│   ├── useTimelineExport.ts   # Export/download/clipboard
│   └── useTimelineLayout.ts   # Reusable zoom/pan state
└── utils/
    ├── timeline-layout.ts     # Layout geometry calculations
    └── export-as-image.ts     # html2canvas PNG export
```

### Data Flow

1. `useTimelineData` loads the implementation plan via `window.electronAPI.getImplementationPlan(taskId)`
2. Plan phases and subtasks are transformed into `TimelinePhase[]` and `TimelineSubtask[]`
3. Layout calculations compute positions at base zoom (1x), CSS `transform: scale()` handles visual zoom
4. `DependencyConnector` renders SVG paths between dependent phases/subtasks
5. Real-time updates flow through the `executionProgress` prop

### Zoom Strategy

Layout math runs at **zoom = 1** (base coordinates). The container element uses CSS `transform: scale(zoom)` with `transformOrigin: top left` to visually scale the content. This avoids double-counting zoom in both layout calculations and CSS transforms.

## Usage

The timeline is integrated into the task detail modal as a tab:

```tsx
import { BuildTimeline } from '../timeline/BuildTimeline';

<BuildTimeline
  taskId={task.id}
  executionProgress={executionProgress}
  config={{ enableAnimations: true }}
/>
```

### Configuration

The `TimelineConfig` interface allows customization:

| Option | Default | Description |
|--------|---------|-------------|
| `defaultZoom` | 1 | Initial zoom level |
| `minZoom` | 0.5 | Minimum zoom (50%) |
| `maxZoom` | 2 | Maximum zoom (200%) |
| `phaseHeight` | 120 | Phase lane height in pixels |
| `subtaskHeight` | 60 | Subtask block height |
| `minSubtaskWidth` | 150 | Minimum subtask width |
| `subtaskSpacing` | 8 | Gap between subtasks |
| `enableAnimations` | true | Enable/disable animations |
| `showDependencies` | true | Show dependency lines |
| `showTimeEstimates` | true | Show time tracking |
