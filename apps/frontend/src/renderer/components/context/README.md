# Context Component

This directory contains the Context component, which provides project index information and the **Memory System Dashboard** - Auto Code's unique cross-session memory visualization and management system.

---

## Memory System Dashboard

The Memory System Dashboard is a powerful interface for exploring, visualizing, and managing Auto Code's Graphiti-based memory graph. It enables users to see what the AI remembers across sessions, understand relationships between memories, and manage stored knowledge.

### Overview

Auto Code uses Graphiti (graph-based memory system) to retain context across sessions. Unlike other AI assistants that start fresh each time, Auto Code remembers:
- Previous sessions and their insights
- Codebase discoveries and patterns
- Gotchas and pitfalls to avoid
- PR reviews and findings
- Project-specific knowledge

The Memory System Dashboard makes this invisible memory layer **visible and manageable**.

### Features

#### 1. **Graph Visualization** 🕸️

Visual representation of memory nodes and their relationships using an interactive graph.

**How it works:**
- Click the **Network icon** in the view toggle to switch to Graph View
- Memory nodes appear as colored circles:
  - **Blue (Episodic)**: Session insights, discoveries, patterns
  - **Purple (Entity)**: Concrete entities like files, functions, PR numbers
- Edges (lines) show relationships between memories with labeled relationship types
- Interactive controls:
  - **Zoom**: Mouse wheel or zoom controls
  - **Pan**: Click and drag
  - **Reset View**: Button to reset zoom and position
  - **MiniMap**: Small overview map in bottom-right corner

**Use Cases:**
- Understand how different memories connect
- Discover relationships between sessions and code discoveries
- Visual exploration of the knowledge graph

#### 2. **List View** 📋

Traditional list interface with search and filtering capabilities.

**How it works:**
- Click the **List icon** in the view toggle to switch to List View
- **Search**: Type keywords and press Enter to search across all memories
- **Filters**: Click filter pills to show specific memory types:
  - **All**: Show everything
  - **PR Reviews**: Pull request reviews and findings
  - **Sessions**: Session insights and task outcomes
  - **Codebase**: Code discoveries and maps
  - **Patterns**: Learned patterns
  - **Gotchas**: Pitfalls and issues to avoid

**Memory Card Features:**
- **Expand/Collapse**: Click card to see full content
- **Timestamps**: When the memory was created
- **Type Badges**: Color-coded memory type indicators
- **Structured Content**: Parsed JSON with sections for discoveries, patterns, etc.

#### 3. **Delete Memory** 🗑️

Remove outdated or incorrect memories from the system.

**How it works:**
- Click the **trash icon** on any memory card
- Confirmation dialog appears (prevents accidental deletion)
- Click **Delete** to confirm removal
- Memory is removed from database and disappears from UI
- Deletion persists across page refreshes

**Use Cases:**
- Remove outdated information
- Clean up incorrect memories
- Manage memory storage

**Safety:**
- Confirmation dialog prevents accidental deletion
- Cannot be undone (destructive action)
- Only deletes selected memory, not related memories

#### 4. **Export Memory** 💾

Export memories for backup, sharing, or external analysis.

**How it works:**
- Click the **Export** button in the MemoriesTab header
- Select export options:
  - **Format**: JSON (structured data) or CSV (spreadsheet)
  - **Type Filter**: Choose specific memory types to export (or all)
  - **Include Metadata**: Toggle project info and export timestamp
- Preview shows count of memories to be exported
- Click **Export** to download file
- File saved to Downloads folder: `memory-export-{project}-{timestamp}.{json|csv}`

**Export Formats:**

**JSON Format:**
```json
{
  "metadata": {
    "projectId": "my-project",
    "exportDate": "2026-02-05T16:00:00Z",
    "totalMemories": 42,
    "filters": {
      "types": ["session_insight", "codebase_discovery"]
    }
  },
  "memories": [
    {
      "id": "uuid",
      "type": "session_insight",
      "content": "...",
      "timestamp": "2026-02-04T10:00:00Z"
    }
  ]
}
```

**CSV Format:**
```csv
ID,Type,Timestamp,Content
uuid,session_insight,2026-02-04T10:00:00Z,"Session content here"
```

**Use Cases:**
- Backup memories before major changes
- Share memories with team members
- Analyze memories in external tools (Excel, Python, etc.)
- Import into other systems

### Technical Architecture

#### Frontend Components

**MemoriesTab.tsx** - Main orchestrator
- Manages view mode (list/graph)
- Handles search and filtering
- Coordinates data fetching
- Renders MemoryGraph or list of MemoryCard components

**MemoryGraph.tsx** - Graph visualization
- Uses `reactflow` library for interactive graphs
- Transforms GraphNode/GraphEdge data to ReactFlow format
- Custom node styling by type (episodic/entity)
- Animated edges with relationship labels
- Interactive controls (zoom, pan, reset)
- MiniMap for navigation
- Legend panel

**MemoryCard.tsx** - Individual memory display
- Expandable/collapsible cards
- Delete button with confirmation dialog
- Type-based color coding
- Structured content parsing
- Timestamp formatting

**MemoryExportDialog.tsx** - Export interface
- Format selection (JSON/CSV)
- Type filtering (11 memory types)
- Metadata toggle
- Preview count
- Client-side file generation using Blob API
- Download via URL.createObjectURL

#### Backend Integration

**query_memory.py** - Python CLI for memory operations
```bash
# Get graph data
python query_memory.py get-graph-data ~/.auto-claude/memories auto_claude_memory --limit 50

# Delete memory
python query_memory.py delete-memory ~/.auto-claude/memories auto_claude_memory --id {uuid}

# Export memories
python query_memory.py export-memories ~/.auto-claude/memories auto_claude_memory --output export.json
```

**IPC Handlers** (memory-data-handlers.ts)
- `CONTEXT_GET_GRAPH_DATA`: Fetch graph nodes and edges
- `CONTEXT_DELETE_MEMORY`: Remove memory by ID
- `CONTEXT_EXPORT_MEMORIES`: Export to file (alternative to client-side export)

**Memory Service** (memory-service.ts)
- `getGraphData(limit)`: Query graph structure
- `deleteMemory(memoryId)`: Remove memory
- `exportMemories(outputPath)`: Backend export (not used by UI, client-side preferred)

#### Data Flow

**Graph View:**
```
User clicks Graph View → MemoriesTab.useEffect
→ window.electronAPI.getGraphData(projectId, limit)
→ IPC handler CONTEXT_GET_GRAPH_DATA
→ memoryService.getGraphData()
→ Python: query_memory.py get-graph-data
→ Returns { nodes: GraphNode[], edges: GraphEdge[] }
→ MemoryGraph renders with reactflow
```

**Delete Memory:**
```
User clicks delete → MemoryCard shows confirmation
→ User confirms → onDelete(memoryId) callback
→ MemoriesTab.handleDeleteMemory
→ window.electronAPI.deleteMemory(projectId, memoryId)
→ IPC handler CONTEXT_DELETE_MEMORY
→ memoryService.deleteMemory()
→ Python: query_memory.py delete-memory
→ Success → Refresh memories list
→ Memory disappears from UI
```

**Export Memory (Client-side):**
```
User clicks Export → MemoryExportDialog opens
→ User selects options (format, types, metadata)
→ Client filters recentMemories array
→ Generate JSON or CSV string
→ Create Blob and download URL
→ Trigger download via <a> element
→ File saved to Downloads
```

### User Guide

#### How to Access

1. Open Auto Code application
2. Select a project from the Kanban board
3. Click the **Context** tab in the top navigation
4. Click the **Memories** sub-tab
5. Memory System Dashboard is now visible

#### How to Use Graph View

1. Click the **Network icon** (next to "Memory Browser" heading)
2. Wait for graph to load (shows loading spinner)
3. Graph displays with:
   - **Blue nodes**: Episodic memories (sessions, insights)
   - **Purple nodes**: Entity memories (files, functions, PR numbers)
   - **Arrows**: Relationships between nodes with labels
4. Interact with graph:
   - **Zoom**: Scroll wheel or zoom controls
   - **Pan**: Click and drag background
   - **Reset**: Click "Reset View" button
   - **Navigate**: Use MiniMap in bottom-right
5. View legend in top-right corner

#### How to Search and Filter

1. In **List View**, use the search box at top
2. Type your search query (e.g., "authentication bug")
3. Press **Enter** to search
4. Results appear below, ranked by relevance
5. Click filter pills to narrow results:
   - **PR Reviews**: Only show PR-related memories
   - **Sessions**: Session insights and task outcomes
   - **Codebase**: Code discoveries
   - **Patterns**: Learned patterns
   - **Gotchas**: Pitfalls and issues

#### How to Delete a Memory

1. Find the memory you want to delete
2. Click the **trash icon** in the memory card header
3. Confirmation dialog appears:
   ```
   Are you sure you want to delete this memory?
   This action cannot be undone.
   ```
4. Click **Delete** to confirm (or **Cancel** to abort)
5. Memory is removed from UI and database

**⚠️ Warning**: Deletion is permanent and cannot be undone.

#### How to Export Memories

1. Click the **Export** button in the top-right (next to view toggle)
2. In the dialog, configure export options:
   - **Format**: Select JSON or CSV
   - **Memory Types**: Choose which types to include (or "All")
   - **Include Metadata**: Check to add project info and timestamp
3. Review the preview count (e.g., "42 memories will be exported")
4. Click **Export**
5. File downloads to your Downloads folder
6. File naming: `memory-export-my-project-2026-02-05T16-00-00.json`

**Tip**: Export before major memory cleanup to create a backup.

### Memory Types

The system recognizes 11 memory types:

| Type | Description | Category |
|------|-------------|----------|
| `session_insight` | Insights from coding sessions | Sessions |
| `task_outcome` | Results of completed tasks | Sessions |
| `codebase_discovery` | New findings about the codebase | Codebase |
| `codebase_map` | Structural understanding | Codebase |
| `pattern` | Learned code patterns | Patterns |
| `pr_pattern` | Patterns from PR reviews | Patterns |
| `gotcha` | Pitfalls to avoid | Gotchas |
| `pr_gotcha` | Issues found in PRs | Gotchas |
| `pr_review` | Full PR review | PR Reviews |
| `pr_finding` | Specific PR issues | PR Reviews |
| `entity` | Concrete entities (files, functions) | Entity |

### Internationalization

UI text supports English and French:

**English:**
- "Graph View"
- "Export Memories"
- Delete confirmation: "Are you sure you want to delete this memory?"

**French:**
- "Vue graphique"
- "Exporter les mémoires"
- Delete confirmation: "Êtes-vous sûr de vouloir supprimer cette mémoire?"

**Note**: Some AlertDialog text uses hardcoded English (acceptable for internal UI).

---

## Context Component Refactoring

This directory contains the refactored Context component, broken down into logical, maintainable modules.

## Structure

```
context/
├── Context.tsx                 # Main component - entry point (2.3KB, down from 35KB)
├── types.ts                    # TypeScript type definitions
├── constants.ts                # Icon mappings and color schemes
├── hooks.ts                    # Custom React hooks for data fetching
├── utils.ts                    # Utility functions (date formatting, etc.)
├── InfoItem.tsx                # Reusable info display component
├── MemoryCard.tsx              # Memory episode card component
├── ServiceCard.tsx             # Service card component with all service details
├── ProjectIndexTab.tsx         # Project index tab content
├── MemoriesTab.tsx             # Memories tab content
├── service-sections/           # Collapsible service detail sections
│   ├── EnvironmentSection.tsx
│   ├── APIRoutesSection.tsx
│   ├── DatabaseSection.tsx
│   ├── ExternalServicesSection.tsx
│   ├── MonitoringSection.tsx
│   ├── DependenciesSection.tsx
│   └── index.ts
└── index.ts                    # Module exports

../Context.tsx                  # Re-export wrapper for backward compatibility
```

## Architecture

### Main Component (`Context.tsx`)
- Orchestrates the two main tabs (Project Index and Memories)
- Uses custom hooks for data fetching and state management
- Delegates rendering to specialized tab components
- Clean, readable entry point (~70 lines)

### Tab Components
- **ProjectIndexTab**: Displays project structure, services, infrastructure, and conventions
- **MemoriesTab**: Shows memory status, search interface, and recent memories

### Service Sections
Each service detail section (environment, API routes, database, etc.) is a separate component:
- Self-contained with its own expand/collapse state
- Consistent UI patterns
- Easy to test and modify independently

### Shared Components
- **ServiceCard**: Comprehensive service display with all collapsible sections
- **MemoryCard**: Memory episode display with expand/collapse
- **InfoItem**: Simple label/value pair display

### Utilities
- **hooks.ts**: Custom hooks for project context loading, refresh, and search
- **constants.ts**: Icon and color mappings for service types and memory types
- **utils.ts**: Date formatting and other utility functions

## Benefits

1. **Maintainability**: Each component has a single responsibility
2. **Testability**: Small, focused components are easier to test
3. **Reusability**: Components like InfoItem and section components can be reused
4. **Readability**: Clear file organization and naming conventions
5. **Type Safety**: Proper TypeScript types for all props and data
6. **Scalability**: Easy to add new service sections or features

## Backward Compatibility

The original `Context.tsx` file now acts as a re-export wrapper, ensuring all existing imports continue to work:

```typescript
import { Context } from './components/Context'; // Still works!
```

## File Size Reduction

- **Before**: 854 lines in a single file (35KB)
- **After**: Main component is 70 lines (2.3KB), with logic distributed across 14 focused modules
- **Reduction**: ~95% reduction in main file size

## Usage

```typescript
import { Context } from '@/components/context';
// or
import { Context } from '@/components/Context'; // Backward compatible

function App() {
  return <Context projectId="my-project-id" />;
}
```
