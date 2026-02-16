# Frontend UI Design: Provider Selection and Settings

## Overview

This document describes the frontend user interface design for multi-provider LLM support in Auto Code. The UI enables users to configure, switch between, and test AI providers (Claude and OpenAI) through a unified settings interface.

## Design Principles

### Consistency with Existing Patterns

The provider selection UI follows established patterns in the Auto Code frontend:

- **CollapsibleSection** - Expandable sections for each provider
- **ConnectionStatus** - Visual feedback for connection state
- **PasswordInput** - Secure input for API keys
- **Select** components - Dropdown selectors for models and options
- **i18n translations** - All user-facing text in translation files
- **Lucide React icons** - Consistent iconography
- **Tailwind CSS** - Unified styling approach

### User Experience Goals

1. **Clear provider visibility** - Users should immediately see which provider is active
2. **Simple switching** - Change providers with minimal clicks
3. **Secure credential handling** - API keys never exposed in plain text
4. **Instant feedback** - Connection status visible at all times
5. **Graceful degradation** - Clear messaging when features are unsupported

## Component Architecture

### Location in App

**Path:** `apps/frontend/src/renderer/components/project-settings/ProviderSelectionSection.tsx`

**Parent Component:** ProjectSettings page

**Related Components:**
- `ClaudeAuthSection` - Existing Claude authentication UI
- `ProviderConfigSection` - New component for provider configuration
- `ConnectionStatus` - Reused for connection testing
- `CollapsibleSection` - Reused for expandable sections

## UI Design Specifications

### 1. Provider Selection Section (Main Container)

**Component:** `ProviderSelectionSection.tsx`

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  AI Provider Configuration                                  │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Active Provider: [Claude ▼]                                │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ◆ Claude Configuration                    ● Active  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ◆ OpenAI Configuration                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [Test Connection] [Save Configuration]                     │
└─────────────────────────────────────────────────────────────┘
```

**Props Interface:**
```typescript
interface ProviderSelectionSectionProps {
  settings: ProjectSettings;
  onUpdateSettings: (updates: Partial<ProjectSettings>) => void;
}
```

**State Management:**
```typescript
interface ProviderSelectionState {
  activeProvider: 'claude' | 'openai';
  isTestingConnection: boolean;
  connectionStatus: 'idle' | 'testing' | 'connected' | 'failed';
  claudeConfig: ClaudeProviderConfig;
  openaiConfig: OpenAIProviderConfig;
}
```

### 2. Provider Dropdown (Active Provider Selector)

**Component:** `ProviderDropdown.tsx`

**Visual Design:**
```
┌─────────────────────────────────────────────┐
│  Active Provider:  [Claude         ▼]      │
└─────────────────────────────────────────────┘
```

**Dropdown Options:**
- **Claude** (default) - Anthropic Claude via claude-agent-sdk
- **OpenAI** - OpenAI GPT models via openai SDK

**Behavior:**
- Changing the active provider immediately updates the `activeProvider` state
- Shows confirmation dialog if unsaved changes exist
- Displays warning if selected provider is not configured

**Translation Keys (en/settings.json):**
```json
{
  "providerSelection": {
    "title": "AI Provider Configuration",
    "activeProvider": "Active Provider",
    "activeProviderDescription": "Select the AI provider for agent tasks",
    "providers": {
      "claude": "Claude (Anthropic)",
      "openai": "OpenAI"
    },
    "switchWarning": "Switching providers will apply new settings to all future agent sessions.",
    "unsavedChanges": "You have unsaved changes. Save before switching providers?"
  }
}
```

### 3. Claude Provider Configuration Section

**Component:** `ClaudeProviderSection.tsx`

**Expands to show:**
```
┌─────────────────────────────────────────────────────────────┐
│ ◆ Claude Configuration                              ● Active  │
│                                                             │
│  Connection Status                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Claude CLI                         ✓ Connected      │   │
│  │  Authenticated via OAuth                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Authentication Method                                     │
│  ◉ OAuth (Recommended)  ○ API Key                          │
│                                                             │
│  [Setup OAuth] [Re-authenticate]                           │
│                                                             │
│  Model Selection                                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Default Model:  [Claude Sonnet 4.5         ▼]      │   │
│  │  Fast Model:     [Claude Haiku 4             ▼]      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Advanced Settings                                         │
│  [Configure per-agent models]                              │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Reuses existing `ClaudeAuthSection` component
- Adds model selection dropdown
- Link to per-agent model configuration (existing feature)
- Connection status indicator

### 4. OpenAI Provider Configuration Section

**Component:** `OpenAIProviderSection.tsx`

**Expands to show:**
```
┌─────────────────────────────────────────────────────────────┐
│ ◆ OpenAI Configuration                                       │
│                                                             │
│  Connection Status                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  OpenAI API                         ⚠ Not Connected  │   │
│  │  Enter API key to test connection                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Authentication                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  API Key *                                           │   │
│  │  ┌─────────────────────────────────────────────┐    │   │
│  │  │  •••••••••••••••••••••••••••••••••         │    │   │
│  │  └─────────────────────────────────────────────┘    │   │
│  │  [  Show  ]                                          │   │
│  │                                                      │   │
│  │  Paste your OpenAI API key (sk-proj-...)            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Base URL (Optional)                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  https://api.openai.com/v1                          │   │
│  └─────────────────────────────────────────────────────┘   │
│  For custom endpoints or Azure OpenAI                      │
│                                                             │
│  Model Selection                                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Default Model:  [GPT-5.2                   ▼]      │   │
│  │  Fast Model:     [GPT-5 Turbo               ▼]      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [Test Connection]                                          │
└─────────────────────────────────────────────────────────────┘
```

**Component Structure:**
```typescript
interface OpenAIProviderSectionProps {
  config: OpenAIProviderConfig;
  onUpdateConfig: (config: OpenAIProviderConfig) => void;
  isExpanded: boolean;
  onToggle: () => void;
  isActive: boolean;
}

interface OpenAIProviderConfig {
  apiKey: string;
  baseUrl?: string;  // For Azure or custom endpoints
  defaultModel: string;
  fastModel: string;
  organization?: string;  // Optional OpenAI organization ID
}
```

**Security Features:**
- API key stored in secure credential store (Keychain/Secret Service)
- Never displayed in plain text (toggle visibility)
- Validated on blur (format: `sk-proj-...`)
- Masked in UI after entry

**Connection Testing:**
- Calls `POST /v1/models` to verify API key
- Updates ConnectionStatus component with result
- Shows error message for auth failures
- Displays model list on success

**Translation Keys:**
```json
{
  "openaiProvider": {
    "title": "OpenAI Configuration",
    "description": "Configure OpenAI API settings",
    "apiKey": "API Key",
    "apiKeyRequired": "API Key is required",
    "apiKeyPlaceholder": "sk-proj-...",
    "apiKeyHint": "Paste your OpenAI API key from platform.openai.com",
    "baseUrl": "Base URL (Optional)",
    "baseUrlPlaceholder": "https://api.openai.com/v1",
    "baseUrlHint": "For Azure OpenAI or custom endpoints",
    "organization": "Organization ID (Optional)",
    "organizationHint": "Your OpenAI organization ID",
    "modelSelection": "Model Selection",
    "defaultModel": "Default Model",
    "fastModel": "Fast Model",
    "testConnection": "Test Connection",
    "testing": "Testing...",
    "connectionSuccess": "Connected successfully",
    "connectionFailed": "Connection failed",
    "models": {
      "gpt52": "GPT-5.2 (Premium)",
      "gpt5": "GPT-5 (Standard)",
      "gpt5Turbo": "GPT-5 Turbo (Fast)",
      "gpt4o": "GPT-4o (Legacy)"
    },
    "featureWarning": "Note: Extended thinking is not supported by OpenAI. Tasks requiring this feature will use Claude instead."
  }
}
```

### 5. Model Selector Component

**Component:** `ModelSelector.tsx`

**Reusable for both providers:**
```typescript
interface ModelSelectorProps {
  provider: 'claude' | 'openai';
  selectedModel: string;
  onModelChange: (model: string) => void;
  label: string;
  models: ModelOption[];
}

interface ModelOption {
  value: string;        // Model ID (e.g., "claude-sonnet-4.5-20250929")
  label: string;        // Display name (e.g., "Claude Sonnet 4.5")
  tier: 'premium' | 'standard' | 'fast' | 'legacy';
  features?: string[];  // e.g., ['extended_thinking', 'vision']
}
```

**Visual Design:**
```
┌─────────────────────────────────────────────┐
│  Default Model                               │
│  ┌─────────────────────────────────────┐    │
│  │  GPT-5.2 (Premium)              ▼  │    │
│  └─────────────────────────────────────┘    │
│  For complex reasoning and architecture      │
└─────────────────────────────────────────────┘
```

**Model Options by Provider:**

**Claude Models:**
- `claude-opus-4-20250514` - Claude Opus (Premium)
- `claude-sonnet-4.5-20250929` - Claude Sonnet 4.5 (Standard)
- `claude-haiku-4-20250929` - Claude Haiku 4 (Fast)

**OpenAI Models:**
- `gpt-5.2` - GPT-5.2 (Premium)
- `gpt-5` - GPT-5 (Standard)
- `gpt-5-turbo` - GPT-5 Turbo (Fast)
- `gpt-4o` - GPT-4o (Legacy)

**Behavior:**
- Models grouped by tier (premium, standard, fast)
- Visual indicators for feature support
- Search/filter for models
- Shows context window and pricing info on hover

### 6. Test Connection Component

**Component:** `TestConnectionButton.tsx`

**States:**
1. **Idle** - "Test Connection" button enabled
2. **Testing** - Spinner with "Testing..." text
3. **Success** - Green checkmark with success message
4. **Failure** - Red X with error details

**Implementation:**
```typescript
interface TestConnectionButtonProps {
  provider: 'claude' | 'openai';
  config: ProviderConfig;
  onTestComplete: (result: ConnectionTestResult) => void;
}

interface ConnectionTestResult {
  success: boolean;
  error?: string;
  models?: string[];  // Available models list
  features?: string[];  // Supported features
}
```

**Connection Test Flow:**

**For Claude:**
```typescript
async function testClaudeConnection(): Promise<ConnectionTestResult> {
  // 1. Check OAuth token validity
  // 2. Call claude-agent-sdk to list models
  // 3. Return available models and features
}
```

**For OpenAI:**
```typescript
async function testOpenAIConnection(config: OpenAIConfig): Promise<ConnectionTestResult> {
  // 1. Validate API key format
  // 2. Call POST /v1/models to verify credentials
  // 3. Return available models and capabilities
}
```

**Error Handling:**
- Invalid API key → "Invalid API key. Please check your credentials."
- Network error → "Network error. Please check your internet connection."
- Rate limit → "Rate limit exceeded. Please try again later."
- Timeout → "Connection timed out. Please try again."

### 7. Per-Agent Provider Configuration

**Component:** `AgentProviderConfig.tsx` (New section in existing agent config)

**Purpose:** Allow different agents to use different providers

**UI Design:**
```
┌─────────────────────────────────────────────────────────────┐
│  Agent Provider Routing                                     │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Use different providers for different agent types:        │
│                                                             │
│  Planner Agent:      [Claude           ▼]                  │
│  Coder Agent:        [OpenAI           ▼]                  │
│  QA Reviewer Agent:  [Claude           ▼]                  │
│  QA Fixer Agent:     [Claude           ▼]                  │
│                                                             │
│  [Reset to Default]                                         │
└─────────────────────────────────────────────────────────────┘
```

**Translation Keys:**
```json
{
  "agentProviderRouting": {
    "title": "Agent Provider Routing",
    "description": "Use different providers for different agent types",
    "agents": {
      "planner": "Planner Agent",
      "coder": "Coder Agent",
      "qaReviewer": "QA Reviewer Agent",
      "qaFixer": "QA Fixer Agent"
    },
    "useDefault": "Use Default Provider",
    "resetToDefault": "Reset to Default",
    "hint": "Planner and QA agents recommend Claude for extended thinking. Coder agent can use OpenAI for cost optimization."
  }
}
```

## State Management

### Redux Store Structure

**New Slice:** `providerSlice.ts`

```typescript
interface ProviderState {
  activeProvider: 'claude' | 'openai';
  providerConfigs: {
    claude: ClaudeProviderConfig;
    openai: OpenAIProviderConfig;
  };
  agentRouting: {
    planner: 'claude' | 'openai' | 'default';
    coder: 'claude' | 'openai' | 'default';
    qa_reviewer: 'claude' | 'openai' | 'default';
    qa_fixer: 'claude' | 'openai' | 'default';
  };
  connectionStatus: {
    claude: ConnectionStatus;
    openai: ConnectionStatus;
  };
}

interface ConnectionStatus {
  status: 'idle' | 'testing' | 'connected' | 'failed';
  lastTested?: Date;
  error?: string;
  availableModels?: string[];
}
```

### IPC Handlers

**Backend → Frontend:**

```typescript
// providers.ts - IPC handlers
ipcMain.handle('provider:get-config', () => {
  return loadProviderConfig();
});

ipcMain.handle('provider:test-connection', async (_event, provider, config) => {
  return testProviderConnection(provider, config);
});

ipcMain.handle('provider:save-config', async (_event, provider, config) => {
  return saveProviderConfig(provider, config);
});
```

**Frontend → Backend:**

```typescript
// providers-api.ts
export async function getProviderConfig(): Promise<ProviderState> {
  return ipcRenderer.invoke('provider:get-config');
}

export async function testConnection(
  provider: 'claude' | 'openai',
  config: ProviderConfig
): Promise<ConnectionTestResult> {
  return ipcRenderer.invoke('provider:test-connection', provider, config);
}

export async function saveProviderConfig(
  provider: 'claude' | 'openai',
  config: ProviderConfig
): Promise<void> {
  return ipcRenderer.invoke('provider:save-config', provider, config);
}
```

## Error Handling

### Validation Errors

**API Key Validation:**
- Format check: `sk-proj-...` for OpenAI
- Empty check: Required field
- Length check: Minimum 20 characters

**Base URL Validation:**
- URL format check: Must be valid HTTPS URL
- Reachability check: DNS lookup and ping
- API compatibility: Check for OpenAI-compatible endpoint

### Connection Errors

**User-Friendly Messages:**

| Error Type | Message | Action |
|------------|---------|--------|
| Invalid API Key | "Invalid API key. Please check your credentials." | Link to OpenAI platform |
| Network Error | "Network error. Please check your internet connection." | Retry button |
| Timeout | "Connection timed out. The server took too long to respond." | Retry with increased timeout |
| Rate Limit | "Rate limit exceeded. Please wait a moment before trying again." | Disable button for 60s |
| Invalid Endpoint | "The specified endpoint is not a valid OpenAI-compatible API." | Show endpoint validation errors |

**Error Display:**
- Inline error below input field
- Red border on invalid fields
- Toast notification for connection failures
- Detailed error in collapsible details section

## Feature Detection UI

### Unsupported Feature Warning

**When OpenAI is selected and feature requires extended thinking:**

```
┌─────────────────────────────────────────────────────────────┐
│  ⚠ Feature Incompatibility                                  │
│                                                             │
│  The following features are not supported by OpenAI:        │
│  • Extended thinking                                        │
│  • Native MCP integration                                   │
│                                                             │
│  These tasks will automatically use Claude instead.         │
│  [Configure fallback] [Dismiss]                             │
└─────────────────────────────────────────────────────────────┘
```

**Translation Keys:**
```json
{
  "featureCompatibility": {
    "warningTitle": "Feature Incompatibility",
    "unsupportedFeatures": "The following features are not supported by {{provider}}:",
    "extendedThinking": "Extended thinking",
    "nativeMcp": "Native MCP integration",
    "autoFallback": "These tasks will automatically use {{fallbackProvider}} instead.",
    "configureFallback": "Configure Fallback",
    "dismiss": "Dismiss"
  }
}
```

### Feature Badge in Model Selector

```
┌─────────────────────────────────────────────┐
│  GPT-5.2 (Premium)                         │
│  ✓ Function calling  ✗ Extended thinking   │
└─────────────────────────────────────────────┘
```

## Accessibility

### Keyboard Navigation

- **Tab** - Navigate between form fields
- **Enter/Space** - Toggle collapsible sections
- **Escape** - Close dropdowns or modals
- **Arrow Keys** - Navigate dropdown options

### Screen Reader Support

- Aria labels on all form inputs
- Aria-expanded on collapsible sections
- Aria-live for connection status updates
- Role="status" for error messages

### Focus Management

- Focus moves to first input when section expands
- Focus returns to trigger when section collapses
- Focus trap in modal dialogs
- Visual focus indicators (Tailwind `ring` classes)

## Responsive Design

### Breakpoints

- **Desktop** (≥1024px) - Two-column layout (Claude | OpenAI)
- **Tablet** (768px - 1023px) - Stacked sections
- **Mobile** (<768px) - Full-width cards with collapsible sections

### Mobile Adaptations

```tsx
{/* Desktop Layout */}
<div className="grid grid-cols-2 gap-4">
  <ClaudeProviderSection />
  <OpenAIProviderSection />
</div>

{/* Mobile Layout */}
<div className="space-y-4">
  <ClaudeProviderSection />
  <OpenAIProviderSection />
</div>
```

## Testing Strategy

### Unit Tests

**Component Tests:**
- Provider dropdown renders correctly
- API key input masks and unmasks
- Connection test button shows loading state
- Error messages display correctly
- Model selector filters options

**Integration Tests:**
- Provider switching updates state
- Saving config persists to backend
- Connection test calls correct endpoint
- Fallback configuration saves correctly

### E2E Tests

**User Flows:**
1. Configure OpenAI provider
2. Test OpenAI connection
3. Switch active provider
4. Configure per-agent routing
5. Verify settings persist across app restarts

## Migration Path

### Phase 1: Backend Integration
1. Add provider config to backend
2. Create IPC handlers
3. Implement connection testing

### Phase 2: Frontend Components
1. Create ProviderSelectionSection
2. Create OpenAIProviderSection
3. Create ModelSelector component
4. Add translation keys

### Phase 3: Integration
1. Wire up Redux store
2. Connect to backend IPC
3. Add to Project Settings page
4. Test end-to-end flow

### Phase 4: Polish
1. Add loading states
2. Improve error messages
3. Add keyboard shortcuts
4. Optimize performance

## Design Mockups

### Full Settings Page Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  Project Settings                                                │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  General                                                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  AI Provider Configuration                                │  │
│  │  ───────────────────────────────────────────────────────  │  │
│  │                                                           │  │
│  │  Active Provider: [Claude                    ▼]         │  │
│  │                                                           │  │
│  │  ┌─ Claude Configuration ──────────────────────── ● ─────┐  │
│  │  │  ✓ Connected                                        │  │
│  │  │  Model: Claude Sonnet 4.5                           │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │                                                           │  │
│  │  ┌─ OpenAI Configuration ────────────────────────────────┐  │
│  │  │  ⚠ Not configured                                    │  │
│  │  │  [Configure OpenAI]                                   │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Agent Provider Routing                                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Claude Auth                                              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  [Save Settings]                            [Discard Changes]  │
└──────────────────────────────────────────────────────────────────┘
```

### OpenAI Configuration Expanded

```
┌──────────────────────────────────────────────────────────────────┐
│  ◆ OpenAI Configuration                                         │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  Connection Status                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  OpenAI API                         ⚠ Not Connected      │   │
│  │  Enter API key and test connection                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Authentication                                                 │
│  API Key *                                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  •••••••••••••••••••••••••••••••••                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│  [  Show  ]                                                      │
│  Paste your OpenAI API key (sk-proj-...)                       │
│                                                                  │
│  Base URL (Optional)                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  https://api.openai.com/v1                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│  For Azure OpenAI or custom endpoints                          │
│                                                                  │
│  Model Selection                                                │
│  Default Model              Fast Model                         │
│  ┌────────────────────┐  ┌────────────────────┐              │
│  │ GPT-5.2 (Premium)│  │ GPT-5 Turbo  ▼   │              │
│  └────────────────────┘  └────────────────────┘              │
│                                                                  │
│  [Test Connection]                                              │
│                                                                  │
│  ⚠ Note: Extended thinking is not supported by OpenAI.         │
│  Planner and QA agents will use Claude instead.                │
└──────────────────────────────────────────────────────────────────┘
```

## File Structure

```
apps/frontend/src/
├── renderer/
│   ├── components/
│   │   ├── project-settings/
│   │   │   ├── ProviderSelectionSection.tsx        (NEW)
│   │   │   ├── OpenAIProviderSection.tsx           (NEW)
│   │   │   ├── ProviderDropdown.tsx                (NEW)
│   │   │   ├── ModelSelector.tsx                   (NEW)
│   │   │   ├── TestConnectionButton.tsx            (NEW)
│   │   │   ├── AgentProviderConfig.tsx             (NEW)
│   │   │   ├── ClaudeAuthSection.tsx               (EXISTING)
│   │   │   ├── ConnectionStatus.tsx                (EXISTING)
│   │   │   ├── CollapsibleSection.tsx              (EXISTING)
│   │   │   └── PasswordInput.tsx                   (EXISTING)
│   │   └── ui/
│   │       ├── select.tsx                          (EXISTING)
│   │       ├── button.tsx                          (EXISTING)
│   │       └── label.tsx                           (EXISTING)
│   ├── redux/
│   │   └── slices/
│   │       └── providerSlice.ts                    (NEW)
│   ├── preload/
│   │   └── api/
│   │       └── providers-api.ts                    (NEW)
│   └── shared/
│       └── i18n/
│           └── locales/
│               ├── en/
│               │   └── settings.json               (UPDATE)
│               └── fr/
│                   └── settings.json               (UPDATE)
└── main/
    └── ipc-handlers/
        └── providers.ts                             (NEW)
```

## Translation Keys Summary

### New Keys to Add

**settings.json:**
```json
{
  "providerSelection": { ... },
  "openaiProvider": { ... },
  "agentProviderRouting": { ... },
  "featureCompatibility": { ... },
  "testConnection": { ... }
}
```

**Keys to Update:**
- `settings.sections` - Add "provider" section
- `settings.projectSections` - Add provider reference

## Performance Considerations

### Lazy Loading
- Load provider configs on demand
- Lazy load model lists (only when expanded)
- Debounce connection test calls (500ms)

### Caching
- Cache available models per provider
- Cache connection test results (5-minute expiry)
- Cache feature detection results

### Optimization
- Virtualize long model lists (100+ options)
- Debounce input validation
- Optimize re-renders with React.memo

## Security Best Practices

### API Key Storage
- Never store in localStorage
- Use system credential store (Keychain/Secret Service)
- Encrypt in transit (HTTPS)
- Never log API keys

### API Key Validation
- Validate format on client
- Verify on backend before saving
- Mask in UI after entry
- Clear from memory after use

### Connection Testing
- Rate limit test requests (max 1 per 30s)
- Timeout after 10 seconds
- Don't expose full API errors to UI
- Sanitize error messages

## Future Enhancements

### Planned Features
1. **Provider Profiles** - Save multiple OpenAI configurations
2. **Cost Estimation** - Show token cost estimates per provider
3. **Usage Analytics** - Track usage per provider
4. **Auto-Failover** - Automatically switch on rate limits
5. **Custom Endpoints** - Support for Azure OpenAI, custom proxies

### Experimental Features
1. **Hybrid Mode** - Use Claude for planning, OpenAI for coding
2. **Performance Benchmarking** - Compare provider speeds
3. **A/B Testing** - Run same task on both providers
4. **Provider Chaining** - Chain multiple providers for single task

## Conclusion

This UI design provides a comprehensive, user-friendly interface for multi-provider LLM support in Auto Code. By following existing patterns and prioritizing security and accessibility, the design ensures a seamless experience for users configuring and switching between AI providers.

### Key Success Metrics
- Users can configure OpenAI in under 2 minutes
- Provider switching takes 3 clicks or less
- Connection test completes in under 5 seconds
- Zero API key exposure incidents
- 95% user satisfaction in usability testing
