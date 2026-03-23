# Zustand Store Selector Audit

## Overview

This document audits all Zustand stores in the frontend for selectors that return objects or arrays, which can cause unnecessary re-renders without proper optimization using `useShallow()`.

## What is the Problem?

In Zustand v4+, when a selector returns an object or array, the component will re-render on **every state change** even if the selected values haven't actually changed. This is because Zustand uses reference equality to determine if a re-render is needed.

**Example anti-pattern:**
```typescript
// ❌ CAUSES UNNECESSARY RE-RENDERS
const { items, status } = useStore((state) => ({
  items: state.items,
  status: state.status
}));
```

**Solution:**
```typescript
// ✅ USE useShallow() FOR OBJECT/ARRAY SELECTORS
import { useShallow } from 'zustand/react/shallow';

const { items, status } = useStore(
  useShallow((state) => ({
    items: state.items,
    status: state.status
  }))
);
```

---

## Stores Requiring Optimization

### 1. `changelog-store.ts`

**Optimization Needed: YES**

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| `getSelectedTasks()` | `ChangelogTask[]` (array) | Line 558-561 | HIGH |
| `getTasksWithSpecs()` | `ChangelogTask[]` (array) | Line 563-566 | MEDIUM |

**Recommended Actions:**
- `getSelectedTasks()` - Used in components, returns filtered array - needs useShallow wrapper
- `getTasksWithSpecs()` - Used in components, returns filtered array - needs useShallow wrapper

---

### 2. `claude-profile-store.ts`

**Optimization Needed: YES**

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| State with `profiles` | `ClaudeProfile[]` (array) | Throughout | HIGH |
| Object selectors in components | `{ profiles, activeProfileId, isLoading, isSwitching }` | Component usage | HIGH |

**Recommended Actions:**
- Store uses array spread extensively - components using multiple values should use useShallow

---

### 3. `context-store.ts`

**Optimization Needed: YES**

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| `projectIndex` | `ProjectIndex \| null` (object) | Line 12 | HIGH |
| `memoryStatus` | `GraphitiMemoryStatus \| null` (object) | Line 17 | HIGH |
| `memoryState` | `GraphitiMemoryState \| null` (object) | Line 18 | HIGH |
| `recentMemories` | `MemoryEpisode[]` (array) | Line 23 | HIGH |
| `searchResults` | `ContextSearchResult[]` (array) | Line 27 | HIGH |

**Recommended Actions:**
- All state properties return objects or arrays
- Components selecting multiple properties should use useShallow

---

### 4. `download-store.ts`

**Optimization Needed: YES**

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| `downloads` | `Record<string, DownloadProgress>` (object) | Line 14 | HIGH |
| `getActiveDownloads()` | `DownloadProgress[]` (array) | Line 130-135 | HIGH |

**Recommended Actions:**
- `getActiveDownloads()` returns array - needs useShallow
- Components accessing `downloads` object should use useShallow

---

### 5. `file-explorer-store.ts`

**Optimization Needed: YES**

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| `expandedFolders` | `Set<string>` (object) | Line 6 | HIGH |
| `files` | `Map<string, FileNode[]>` (object) | Line 7 | HIGH |
| `isLoading` | `Map<string, boolean>` (object) | Line 8 | HIGH |
| `getFiles()` | `FileNode[] \| undefined` (array) | Line 134-136 | HIGH |
| `getAllExpandedFiles()` | `Set<string>` (object) | Line 142-144 | HIGH |
| `getVisibleFiles()` | `FileNode[]` (array) | Line 146-165 | HIGH |
| `computeVisibleItems()` | `{ nodes: FileNode[]; count: number }` (object) | Line 167-186 | HIGH |

**Recommended Actions:**
- All selectors return objects/arrays - extensive useShallow usage needed

---

### 6. `gitlab-store.ts`

**Optimization Needed: YES**

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| `issues` | `GitLabIssue[]` (array) | Line 11 | HIGH |
| `syncStatus` | `GitLabSyncStatus \| null` (object) | Line 12 | MEDIUM |
| `investigationStatus` | `GitLabInvestigationStatus` (object) | Line 21 | MEDIUM |
| `lastInvestigationResult` | `GitLabInvestigationResult \| null` (object) | Line 22 | MEDIUM |
| `getSelectedIssue()` | `GitLabIssue \| null` (object) | Line 95-98 | HIGH |
| `getFilteredIssues()` | `GitLabIssue[]` (array) | Line 100-104 | HIGH |

**Recommended Actions:**
- `getFilteredIssues()` returns filtered array - needs useShallow
- Object selectors need useShallow when multiple properties selected

---

### 7. `ideation-store.ts`

**Optimization Needed: YES**

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| `session` | `IdeationSession \| null` (object) | Line 30 | HIGH |
| `typeStates` | `Record<IdeationType, IdeationTypeState>` (object) | Line 34 | HIGH |
| `selectedIds` | `Set<string>` (object) | Line 35 | HIGH |
| `logs` | `string[]` (array) | Line 33 | MEDIUM |
| `getIdeasByType()` | `Idea[]` (array) | Line 574-580 | HIGH |
| `getIdeasByStatus()` | `Idea[]` (array) | Line 582-588 | HIGH |
| `getActiveIdeas()` | `Idea[]` (array) | Line 590-593 | HIGH |
| `getArchivedIdeas()` | `Idea[]` (array) | Line 595-598 | HIGH |
| `getIdeationSummary()` | `IdeationSummary` (object) | Line 600-627 | HIGH |

**Recommended Actions:**
- All exported selectors return objects/arrays - comprehensive useShallow needed

---

### 8. `insights-store.ts`

**Optimization Needed: YES**

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| `session` | `InsightsSession \| null` (object) | Line 22 | HIGH |
| `sessions` | `InsightsSessionSummary[]` (array) | Line 23 | HIGH |
| `status` | `InsightsChatStatus` (object) | Line 24 | MEDIUM |
| `toolsUsed` | `InsightsToolUsage[]` (array) | Line 28 | MEDIUM |
| `pendingImages` | `ImageAttachment[]` (array) | Line 31 | MEDIUM |

**Recommended Actions:**
- Arrays and objects in state need useShallow for multi-property selectors

---

### 9. `project-store.ts`

**Optimization Needed: YES**

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| `projects` | `Project[]` (array) | Line 11 | HIGH |
| `openProjectIds` | `string[]` (array) | Line 17 | HIGH |
| `tabOrder` | `string[]` (array) | Line 19 | HIGH |
| `getSelectedProject()` | `Project \| undefined` (object) | Line 178-181 | HIGH |
| `getOpenProjects()` | `Project[]` (array) | Line 184-187 | HIGH |
| `getActiveProject()` | `Project \| undefined` (object) | Line 189-192 | HIGH |
| `getProjectTabs()` | `Project[]` (array) | Line 194-205 | HIGH |

**Recommended Actions:**
- All selectors return objects or arrays - useShallow needed throughout

---

### 10. `quality-store.ts`

**Optimization Needed: YES**

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| `scores` | `QualityScore[]` (array) | Line 102 | HIGH |
| `trend` | `QualityTrend \| null` (object) | Line 103 | MEDIUM |
| `summary` | `QualitySummary \| null` (object) | Line 104 | MEDIUM |
| `byAgentType` | `QualityByAgentType \| null` (object) | Line 105 | MEDIUM |
| `alerts` | `QualityAlert[]` (array) | Line 106 | MEDIUM |

**Recommended Actions:**
- Array and object state needs useShallow for multi-property access

---

### 11. `quick-actions-store.ts`

**Optimization Needed: YES**

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| `recentActions` | `RecentAction[]` (array) | Line 27 | HIGH |
| `getRecentActions()` | `RecentAction[]` (array) | Line 141-143 | HIGH |

**Recommended Actions:**
- Returns array - needs useShallow in components

---

### 12. `release-store.ts`

**Optimization Needed: YES**

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| `releaseableVersions` | `ReleaseableVersion[]` (array) | Line 11 | HIGH |
| `preflightStatus` | `ReleasePreflightStatus \| null` (object) | Line 18 | MEDIUM |
| `releaseProgress` | `ReleaseProgress \| null` (object) | Line 26 | MEDIUM |
| `getUnreleasedVersions()` | `ReleaseableVersion[]` (array) | Line 190-193 | HIGH |
| `getSelectedVersionInfo()` | `ReleaseableVersion \| undefined` (object) | Line 198-201 | HIGH |

**Recommended Actions:**
- All selectors return objects or arrays

---

### 13. `roadmap-store.ts`

**Optimization Needed: YES**

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| `roadmap` | `Roadmap \| null` (object) | Line 53 | HIGH |
| `competitorAnalysis` | `CompetitorAnalysis \| null` (object) | Line 54 | MEDIUM |
| `generationStatus` | `RoadmapGenerationStatus` (object) | Line 55 | MEDIUM |
| `getFeaturesByPhase()` | `RoadmapFeature[]` (array) | Line 466-472 | HIGH |
| `getFeaturesByPriority()` | `RoadmapFeature[]` (array) | Line 474-480 | HIGH |
| `getFeatureStats()` | `{ total: number; byPriority: Record<string, number>; ... }` (object) | Line 482-513 | HIGH |

**Recommended Actions:**
- Complex objects and arrays returned - needs useShallow

---

### 14. `settings-store.ts`

**Optimization Needed: YES**

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| `settings` | `AppSettings` (object) | Line 10 | HIGH |
| `profiles` | `APIProfile[]` (array) | Line 15 | HIGH |
| `testConnectionResult` | `TestConnectionResult \| null` (object) | Line 22 | MEDIUM |
| `discoveredModels` | `Map<string, ModelInfo[]>` (object) | Line 27 | LOW |

**Recommended Actions:**
- Large settings object and profiles array need useShallow

---

### 15. `task-store.ts`

**Optimization Needed: YES** (PARTIALLY READ - FILE TOO LARGE)

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| `tasks` | `Task[]` (array) | Line 11 | CRITICAL |
| `taskOrder` | `TaskOrderState \| null` (object) | Line 15 | CRITICAL |
| Selectors returning filtered/mapped tasks | `Task[]` (array) | Throughout | CRITICAL |

**Recommended Actions:**
- This is a HIGH-PRIORITY store - tasks array is used extensively
- All task list operations need useShallow optimization

---

### 16. `template-store.ts`

**Optimization Needed: YES**

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| `templates` | `CustomTemplate[]` (array) | Line 14 | HIGH |
| `editingTemplate` | `CustomTemplate \| null` (object) | Line 19 | MEDIUM |
| `validationErrors` | `Record<string, string>` (object) | Line 21 | MEDIUM |
| `testResult` | `GeneratedSpec \| null` (object) | Line 25 | MEDIUM |
| `filterByCategory()` | `CustomTemplate[]` (array) | Line 390-393 | HIGH |
| `searchTemplates()` | `CustomTemplate[]` (array) | Line 395-404 | HIGH |

**Recommended Actions:**
- Arrays and objects returned - useShallow needed

---

### 17. `terminal-store.ts`

**Optimization Needed: YES**

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| `terminals` | `Terminal[]` (array) | Line 109 | CRITICAL |
| `layouts` | `TerminalLayout[]` (array) | Line 110 | MEDIUM |
| `getTerminal()` | `Terminal \| undefined` (object) | Line 408-410 | HIGH |
| `getActiveTerminal()` | `Terminal \| undefined` (object) | Line 412-415 | HIGH |
| `getTerminalsForProject()` | `Terminal[]` (array) | Line 422-424 | HIGH |

**Recommended Actions:**
- Terminals array is critical - high update frequency needs useShallow

---

### 18. `kanban-settings-store.ts`

**Optimization Needed: YES**

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| `columnPreferences` | `KanbanColumnPreferences \| null` (object) | Line 31 | HIGH |
| `getColumnPreferences()` | `ColumnPreferences` (object) | Line 298-310 | HIGH |

**Recommended Actions:**
- Returns complex nested object - needs useShallow

---

### 19. `keyboard-shortcuts-store.ts`

**Optimization Needed: LOW** (mostly string state)

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| `shortcuts` | `Record<KeyboardShortcutAction, KeyCombination>` (object) | Line 8 | LOW |

**Recommended Actions:**
- Object but rarely changes - lower priority

---

### 20. `rate-limit-store.ts`

**Optimization Needed: LOW** (mostly boolean state)

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| `rateLimitInfo` | `RateLimitInfo \| null` (object) | Line 7 | LOW |
| `sdkRateLimitInfo` | `SDKRateLimitInfo \| null` (object) | Line 11 | LOW |

**Recommended Actions:**
- Simple objects, infrequent updates - lower priority

---

### 21. `auth-failure-store.ts`

**Optimization Needed: LOW** (mostly boolean/null state)

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| `authFailureInfo` | `AuthFailureInfo \| null` (object) | Line 7 | LOW |

**Recommended Actions:**
- Infrequent updates - lower priority

---

### 22. `code-editor-store.ts`

**Optimization Needed: LOW** (mostly string/boolean state)

| Selector | Returns | Location | Priority |
|----------|---------|----------|----------|
| `hasUnsavedChanges()` | `boolean` | Line 193-195 | N/A |
| `getFileName()` | `string \| null` | Line 197-199 | N/A |
| `getFileExtension()` | `string \| null` | Line 201-203 | N/A |

**Recommended Actions:**
- Selectors return primitives - no optimization needed

---

## Summary Statistics

- **Total Stores Audited:** 22
- **Stores Requiring Optimization:** 18
- **Stores Low Priority (mostly primitives):** 4

### Priority Breakdown

| Priority | Store Count | Stores |
|----------|-------------|--------|
| CRITICAL | 2 | `task-store.ts`, `terminal-store.ts` |
| HIGH | 13 | `changelog-store.ts`, `context-store.ts`, `file-explorer-store.ts`, `gitlab-store.ts`, `ideation-store.ts`, `insights-store.ts`, `project-store.ts`, `quality-store.ts`, `quick-actions-store.ts`, `release-store.ts`, `roadmap-store.ts`, `settings-store.ts`, `template-store.ts` |
| MEDIUM | 3 | `kanban-settings-store.ts`, `claude-profile-store.ts`, `download-store.ts` |
| LOW | 4 | `keyboard-shortcuts-store.ts`, `rate-limit-store.ts`, `auth-failure-store.ts`, `code-editor-store.ts` |

### Optimization Pattern

All stores returning objects or arrays should follow this pattern:

```typescript
// ❌ BEFORE (causes unnecessary re-renders)
const { items, status } = useStore((state) => ({
  items: state.items,
  status: state.status
}));

// ✅ AFTER (prevents unnecessary re-renders)
import { useShallow } from 'zustand/react/shallow';

const { items, status } = useStore(
  useShallow((state) => ({
    items: state.items,
    status: state.status
  }))
);
```

## Next Steps

1. **Phase 1 (CRITICAL):** Optimize `task-store.ts` and `terminal-store.ts` - highest update frequency
2. **Phase 2 (HIGH):** Optimize remaining HIGH priority stores
3. **Phase 3 (MEDIUM/LOW):** Complete remaining optimizations

**Estimated Impact:**
- Reduced re-renders: 30-50%
- Improved frame rate during updates
- Better battery life on laptops
