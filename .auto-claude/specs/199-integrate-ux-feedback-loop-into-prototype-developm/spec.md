# Specification: Integrate UX Feedback Loop into Prototype Development

## Overview

This feature integrates a visual UX feedback loop into the Auto-Claude Electron application's development workflow. Based on the approach described in the Habr article (agentation-style visual annotation), developers will be able to annotate UI defects and gaps directly on the running prototype, with annotations automatically converted into actionable tasks/specs within the existing Auto-Claude pipeline. This eliminates friction between identifying UI issues and tracking them, accelerating the prototype-to-production workflow.

## Workflow Type

**Type**: feature

**Rationale**: This introduces new functionality—a visual annotation layer integrated with the task creation pipeline—rather than modifying existing behavior. It requires new components, new event handling, and integration with existing MCP infrastructure.

## Task Scope

### Services Involved
- **frontend** (primary) - Electron/React application where visual annotation UI will be rendered
- **backend** (integration) - Spec creation pipeline that will receive annotation-derived tasks

### This Task Will:
- [ ] Install and configure the `agentation` package as a devDependency
- [ ] Create a development-only annotation overlay component
- [ ] Hook annotation submissions into existing MCP server infrastructure
- [ ] Create annotation-to-task transformation logic
- [ ] Store annotations and generate specs/tasks in `.auto-claude/specs/` format
- [ ] Provide UI controls to enable/disable annotation mode

### Out of Scope:
- Production deployment of annotation features (dev-only)
- External task management integration (Jira, Linear, etc.) - handled by existing integrations
- Mobile/touch annotation support
- Multi-user collaborative annotation
- Running separate agentation-mcp server (will use existing MCP infrastructure)

## Service Context

### Frontend (Primary Service)

**Tech Stack:**
- Language: TypeScript
- Framework: React 19.x + Electron 40.6.0
- State Management: Zustand
- Styling: Tailwind CSS
- Build Tool: Vite

**Key Directories:**
- `apps/frontend/src/` - Source code
- `apps/frontend/src/main/` - Electron main process
- `apps/frontend/src/renderer/` - React renderer process
- `apps/frontend/src/main/mcp-manager.ts` - Existing MCP manager
- `apps/frontend/src/main/mcp-server.ts` - Existing MCP server
- `apps/frontend/src/main/ipc-handlers/mcp-handlers.ts` - MCP IPC handlers

**Entry Point:** `apps/frontend/src/main/index.ts`

**How to Run:**
```bash
cd apps/frontend && npm run dev
```

**Port:** 3000 (Vite dev server)

### Backend (Integration)

**Tech Stack:**
- Language: Python 3.12+
- Package Manager: pip/uv

**Key Directories:**
- `apps/backend/spec_agents/` - Spec creation agents
- `apps/backend/specs/` - Spec storage location

**Entry Point:** `apps/backend/spec_runner.py`

**How to Run:**
```bash
cd apps/backend && python spec_runner.py --interactive
```

## Files to Modify

| File | Service | What to Change |
|------|---------|---------------|
| `apps/frontend/package.json` | frontend | Add `agentation` as devDependency |
| `apps/frontend/src/renderer/App.tsx` | frontend | Add conditional Agentation component wrapper |
| `apps/frontend/src/main/mcp-server.ts` | frontend | Add annotation handling tools |
| `apps/frontend/src/main/ipc-handlers/mcp-handlers.ts` | frontend | Add IPC handlers for annotation events |
| `apps/frontend/src/shared/i18n/locales/en/common.json` | frontend | Add i18n keys for annotation UI |
| `apps/frontend/src/shared/i18n/locales/fr/common.json` | frontend | Add i18n keys for annotation UI (French) |

## Files to Reference

These files show patterns to follow:

| File | Pattern to Copy |
|------|----------------|
| `apps/frontend/src/main/mcp-manager.ts` | MCP tool registration pattern |
| `apps/frontend/src/main/mcp-server.ts` | MCP server tool implementation |
| `apps/frontend/src/main/ipc-handlers/mcp-handlers.ts` | IPC handler pattern for MCP |
| `apps/frontend/src/renderer/App.tsx` | Conditional component rendering, environment checks |
| `apps/backend/spec_agents/gatherer.py` | Spec/task creation patterns |
| `apps/frontend/src/shared/stores/` | Zustand store patterns |

## Patterns to Follow

### Development-Only Component Pattern

From existing codebase patterns, conditional rendering for dev-only features:

```tsx
// Only render in development mode
{import.meta.env.DEV && (
  <AnnotationOverlay
    onAnnotationSubmit={handleAnnotationSubmit}
  />
)}
```

**Key Points:**
- Use `import.meta.env.DEV` for Vite-based conditional rendering
- Avoid `process.env.NODE_ENV` direct checks in renderer (use Vite's approach)
- Ensure component tree-shakes out of production builds

### MCP Tool Registration Pattern

From `apps/frontend/src/main/mcp-server.ts`:

```typescript
// Register new tool with MCP server
server.tool(
  'create_annotation_task',
  {
    description: 'Create a task/spec from a UI annotation',
    inputSchema: {
      type: 'object',
      properties: {
        screenshot: { type: 'string', description: 'Base64 screenshot' },
        coordinates: { type: 'object', properties: { x: { type: 'number' }, y: { type: 'number' } } },
        description: { type: 'string', description: 'Issue description' },
        severity: { type: 'string', enum: ['low', 'medium', 'high', 'critical'] }
      },
      required: ['description']
    }
  },
  async (args) => {
    // Implementation
  }
);
```

**Key Points:**
- Follow existing tool registration structure
- Include proper input schema validation
- Return structured responses

### Zustand Store Pattern

From existing stores in the codebase:

```typescript
import { create } from 'zustand';

interface AnnotationStore {
  isAnnotationMode: boolean;
  annotations: Annotation[];
  toggleAnnotationMode: () => void;
  addAnnotation: (annotation: Annotation) => void;
  clearAnnotations: () => void;
}

export const useAnnotationStore = create<AnnotationStore>((set) => ({
  isAnnotationMode: false,
  annotations: [],
  toggleAnnotationMode: () => set((state) => ({ isAnnotationMode: !state.isAnnotationMode })),
  addAnnotation: (annotation) => set((state) => ({ annotations: [...state.annotations, annotation] })),
  clearAnnotations: () => set({ annotations: [] }),
}));
```

**Key Points:**
- Use TypeScript interfaces for store shape
- Keep store actions minimal and focused
- Expose selectors for derived state

### i18n Pattern

From existing translation files:

```json
{
  "annotation": {
    "mode": {
      "enable": "Enable annotation mode",
      "disable": "Disable annotation mode"
    },
    "submit": "Submit annotation",
    "description": "Describe the issue",
    "severity": {
      "label": "Severity",
      "low": "Low",
      "medium": "Medium",
      "high": "High",
      "critical": "Critical"
    }
  }
}
```

**Key Points:**
- Always use translation keys, never hardcoded strings
- Add to both `en` and `fr` locale files
- Use nested structure for organization

## Requirements

### Functional Requirements

1. **Annotation Mode Toggle**
   - Description: Users can enable/disable annotation mode via a toolbar button
   - Acceptance: Toggle button visible in dev mode only, state persists during session

2. **Visual Annotation Drawing**
   - Description: When annotation mode is active, users can click/drag to highlight UI areas
   - Acceptance: Annotations appear as visual overlays with bounding boxes

3. **Annotation Description Input**
   - Description: Users can add text descriptions and severity levels to annotations
   - Acceptance: Form appears after marking an area, captures description + severity

4. **Screenshot Capture**
   - Description: System automatically captures screenshot of annotated area
   - Acceptance: Screenshot stored with annotation data for context

5. **Task Creation from Annotation**
   - Description: Submitted annotations create task entries in spec format
   - Acceptance: New spec folder created in `.auto-claude/specs/` with annotation data

6. **Annotation List View**
   - Description: Users can view all annotations made in current session
   - Acceptance: List shows all annotations with ability to edit/delete

### Non-Functional Requirements

1. **Dev-Only Activation**
   - Description: Feature completely absent from production builds
   - Acceptance: No annotation code in production bundle, verified via bundle analysis

2. **React 19 Compatibility**
   - Description: Agentation package works with React 19.2.3
   - Acceptance: No peer dependency warnings, component renders correctly

3. **Performance**
   - Description: Annotation overlay does not impact app performance
   - Acceptance: No perceptible lag when annotation mode enabled

### Edge Cases

1. **Rapid Annotation Submission** - Queue submissions, process sequentially to avoid race conditions
2. **Large Screenshot Areas** - Compress images if >1MB, warn user about large captures
3. **Missing Description** - Require minimum description length (10 chars) before submission
4. **Electron Window Resize** - Recalculate annotation positions on resize
5. **Network Offline** - Store annotations locally, sync when connection restored

## Implementation Notes

### DO
- Follow the pattern in `apps/frontend/src/main/mcp-server.ts` for MCP tool registration
- Use existing Zustand store patterns from `apps/frontend/src/shared/stores/`
- Use i18n translation keys for ALL user-facing text
- Install agentation with `npm install agentation -D` (devDependency only)
- Use `--legacy-peer-deps` if React 19 peer dependency issues arise
- Leverage existing IPC patterns in `apps/frontend/src/main/ipc-handlers/`

### DON'T
- Create separate agentation-mcp server (use existing MCP infrastructure)
- Add annotation code paths that execute in production
- Hardcode any UI strings (use i18n)
- Store sensitive data in annotations (screenshots may be shared)
- Block main thread during screenshot capture

## Technical Decisions

### Agentation Package Integration

**Decision**: Install `agentation` as devDependency, integrate with existing MCP

**Rationale**:
- Avoids running parallel MCP server
- Leverages existing tested infrastructure
- Ensures consistent tool registration pattern
- Reduces runtime dependencies in production

**License Note**: Agentation uses PolyForm Shield 1.0.0 license. Legal review recommended for compatibility with project's AGPL-3.0 license before proceeding.

### Annotation Data Schema

```typescript
interface Annotation {
  id: string;                    // UUID
  timestamp: string;             // ISO 8601
  screenshot: string;            // Base64 encoded PNG
  coordinates: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  component?: string;            // Auto-detected component name if possible
  route?: string;                // Current route/page
  viewportSize: {
    width: number;
    height: number;
  };
}
```

### Task/Spec Generation

Annotations will generate simplified spec entries:

```
.auto-claude/specs/XXX-annotation-{short-description}/
├── spec.md              # Generated from annotation
├── requirements.json    # Annotation data as requirements
├── context.json         # Auto-detected context
└── screenshot.png       # Captured screenshot
```

## Development Environment

### Start Services

```bash
# Frontend (Electron app with annotation support in dev mode)
cd apps/frontend && npm run dev

# Backend (for spec creation pipeline - optional, only if testing full flow)
cd apps/backend && python spec_runner.py --list
```

### Service URLs
- Frontend Dev Server: http://localhost:3000 (Vite)
- Electron App: Launches automatically in dev mode

### Required Environment Variables
- `NODE_ENV`: Set to `development` automatically by Vite in dev mode
- No additional env vars required for this feature

### Testing Annotation Mode

1. Start frontend in dev mode: `cd apps/frontend && npm run dev`
2. Look for annotation toggle button in toolbar (only visible in dev)
3. Enable annotation mode
4. Click and drag to mark UI area
5. Fill in description and severity
6. Submit annotation
7. Verify spec created in `.auto-claude/specs/`

## Success Criteria

The task is complete when:

1. [ ] `agentation` package installed as devDependency with no peer conflicts
2. [ ] Annotation toggle button visible in dev mode only
3. [ ] Users can mark areas and add descriptions
4. [ ] Screenshot captured with each annotation
5. [ ] Annotations create valid spec entries in `.auto-claude/specs/`
6. [ ] Annotation list view shows all session annotations
7. [ ] Feature completely absent from production builds
8. [ ] No console errors in dev or production
9. [ ] All existing tests still pass
10. [ ] i18n translations added for all annotation UI text

## QA Acceptance Criteria

**CRITICAL**: These criteria must be verified by the QA Agent before sign-off.

### Unit Tests
| Test | File | What to Verify |
|------|------|----------------|
| AnnotationStore toggle | `apps/frontend/src/shared/stores/__tests__/annotation-store.test.ts` | Store toggles annotation mode correctly |
| AnnotationStore add | `apps/frontend/src/shared/stores/__tests__/annotation-store.test.ts` | Annotations added to store state |
| Annotation data validation | `apps/frontend/src/renderer/components/__tests__/annotation-form.test.ts` | Form validates required fields |
| Screenshot capture | `apps/frontend/src/main/__tests__/screenshot.test.ts` | Capture returns valid base64 image |

### Integration Tests
| Test | Services | What to Verify |
|------|----------|----------------|
| MCP tool registration | frontend MCP server | `create_annotation_task` tool registered and callable |
| IPC annotation flow | main ↔ renderer | Annotation data passes correctly through IPC |
| Spec generation | frontend → filesystem | Annotation creates valid spec folder structure |

### End-to-End Tests
| Flow | Steps | Expected Outcome |
|------|-------|------------------|
| Enable annotation mode | 1. Launch app in dev 2. Click annotation toggle | Overlay appears, cursor changes |
| Create annotation | 1. Enable mode 2. Drag to select area 3. Fill form 4. Submit | Spec folder created with correct data |
| View annotations | 1. Create 2+ annotations 2. Open annotation list | All annotations displayed with metadata |
| Production exclusion | 1. Build production 2. Check bundle | No agentation/annotation code in bundle |

### Browser/Electron Verification
| Page/Component | Location | Checks |
|----------------|----------|--------|
| Annotation Toggle | Toolbar area | Visible in dev, hidden in prod |
| Annotation Overlay | Full window overlay | Appears when mode enabled |
| Annotation Form | Popup after selection | Fields render, submit works |
| Annotation List | Sidebar or modal | Shows all annotations |

### Filesystem Verification
| Check | Command | Expected |
|-------|---------|----------|
| Spec folder created | `ls .auto-claude/specs/` | New folder with annotation ID |
| spec.md content | `cat .auto-claude/specs/XXX/spec.md` | Valid markdown with annotation details |
| Screenshot saved | `ls .auto-claude/specs/XXX/` | `screenshot.png` file exists |

### QA Sign-off Requirements
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All E2E tests pass
- [ ] Electron verification complete
- [ ] Filesystem state verified
- [ ] No regressions in existing functionality
- [ ] Code follows established patterns (MCP, Zustand, i18n)
- [ ] No security vulnerabilities introduced
- [ ] Production build verified clean of dev-only code
- [ ] i18n translations complete for EN and FR

## Appendix: Research Findings

### Package Information
- **agentation@^2.2.1**: Visual annotation toolbar, zero runtime deps beyond React
- **agentation-mcp@^1.2.0**: Local HTTP/MCP bridge (NOT needed - use existing infra)
- **@modelcontextprotocol/sdk**: Already installed in project

### Compatibility Notes
- React 19.2.3 vs React 18+ requirement: Likely compatible, use `--legacy-peer-deps` if needed
- Electron 40.6.0: Uses Chromium renderer, treated as desktop browser - compatible

### License Risk (Medium Priority)
Agentation uses PolyForm Shield 1.0.0 license. Recommend legal review for compatibility with project's AGPL-3.0 license before proceeding with implementation.
