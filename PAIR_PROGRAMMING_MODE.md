# AI Pair Programming Mode - User Guide

**Real-time collaborative AI assistance while you code**

This guide explains how to use Auto-Claude's AI Pair Programming Mode, which provides interactive coding assistance with real-time suggestions, voice interaction, and seamless mode switching.

---

## Overview

AI Pair Programming Mode bridges the gap between copilot-style assistants and fully autonomous agents. Instead of working completely independently, the AI works alongside you in real-time, offering suggestions as you code, explaining best practices, and assisting with complex implementations.

### Key Features

| Feature | Description |
|---------|-------------|
| **Real-Time Suggestions** | Get AI-powered code suggestions as you type |
| **Inline Completions** | Context-aware code completion and refactoring suggestions |
| **Voice Interaction** | Hands-free pair programming with speech-to-text and text-to-speech |
| **Seamless Mode Switching** | Toggle between autonomous and pair programming modes |
| **Live File Watching** | Automatic detection of code changes for instant feedback |

---

## When to Use Pair Programming Mode

Use pair programming mode when:
- **Learning new patterns**: You want AI explanations as you explore unfamiliar code
- **Complex implementations**: You need guidance but want to maintain control
- **Exploratory coding**: You're not sure of the exact approach yet
- **Collaborative problem-solving**: You want to bounce ideas off the AI in real-time

Use autonomous mode when:
- **Well-defined tasks**: The requirements are clear and you want full automation
- **Bulk work**: Multiple similar changes across many files
- **Background tasks**: Work that doesn't require constant oversight

---

## Quick Start

### 1. Start a Pair Programming Session

**Via Web Interface:**
```bash
# Start the web backend (if not already running)
cd apps/web-backend
python -m uvicorn main:app --reload --port 8000

# Navigate to the Pair Programming panel
# http://localhost:3000/pair
```

**Via API:**
```bash
curl -X POST http://localhost:8000/api/agents/pair/start \
  -H "Content-Type: application/json" \
  -d '{
    "project_dir": "/path/to/your/project",
    "spec_id": "optional-spec-id",
    "watch_patterns": ["**/*.py", "**/*.ts", "**/*.tsx"],
    "enable_voice": false
  }'
```

**Via Python:**
```python
from apps.backend.agents.pair_programming import PairProgrammingAgent

agent = PairProgrammingAgent(
    project_dir="/path/to/your/project",
    spec_dir="/path/to/spec/dir"
)

session_id = agent.start_session(
    watch_patterns=["**/*.py", "**/*.ts"],
    enable_voice=False
)
```

### 2. Receive Real-Time Suggestions

Once started, the agent monitors your file changes and provides:
- **Code suggestions**: Inline completions as you type
- **Refactoring ideas**: Improvements to existing code
- **Pattern recommendations**: Best practices from your codebase
- **Explanations**: Context-aware documentation

### 3. Toggle Voice Mode (Optional)

Enable hands-free coding with voice interaction:
```python
agent.toggle_voice_mode(enabled=True)

# Now you can:
# - Speak your intentions ("Add error handling here")
# - Hear AI suggestions read aloud
# - Control the session with voice commands
```

### 4. Switch Between Modes

Seamlessly transition between pair and autonomous modes:

**In Electron App:**
```typescript
// Toggle to pair programming mode
agentManager.setPairMode(true);

// Check current mode
const isPairMode = agentManager.isPairMode();

// Return to autonomous mode
agentManager.setPairMode(false);
```

**In Coder Agent:**
```bash
# Start coder in pair mode
python -m apps.backend.agents.coder --pair-mode

# Agent will pause after each subtask for manual continuation
# instead of auto-proceeding
```

---

## API Reference

### REST Endpoints

#### Start Pair Programming Session
```http
POST /api/agents/pair/start
Content-Type: application/json

{
  "project_dir": "/path/to/project",
  "spec_id": "optional-spec-id",
  "watch_patterns": ["**/*.py", "**/*.ts"],
  "ignore_patterns": ["**/__pycache__/**", "**/node_modules/**"],
  "enable_voice": false,
  "suggestion_confidence_threshold": 0.7
}

Response: 200 OK
{
  "session_id": "uuid-string",
  "status": "active",
  "voice_enabled": false,
  "watch_patterns": ["**/*.py", "**/*.ts"]
}
```

#### Get Session Status
```http
GET /api/agents/pair/status/{session_id}

Response: 200 OK
{
  "session_id": "uuid-string",
  "status": "active",
  "files_watched": 127,
  "suggestions_made": 42,
  "voice_enabled": false,
  "uptime_seconds": 3600
}
```

#### Stop Pair Programming Session
```http
POST /api/agents/pair/stop/{session_id}

Response: 200 OK
{
  "session_id": "uuid-string",
  "status": "stopped",
  "final_stats": {
    "total_suggestions": 42,
    "accepted_suggestions": 28,
    "rejected_suggestions": 14,
    "session_duration_seconds": 3600
  }
}
```

### WebSocket Events

Subscribe to real-time suggestion events:

```typescript
import { WebSocketClient } from '@/api/websocket';

const ws = new WebSocketClient('ws://localhost:8000/ws');

// Listen for suggestions
ws.on('pair_suggestion', (event: SuggestionEvent) => {
  console.log('New suggestion:', event.suggestion);
  console.log('Confidence:', event.metadata.confidence);
  console.log('Type:', event.metadata.suggestion_type);
});

// Listen for session events
ws.on('pair_session', (event: PairSessionEvent) => {
  console.log('Session event:', event.event_type);
  console.log('Session ID:', event.session_id);
});

// Listen for voice events
ws.on('voice_interaction', (event: VoiceInteractionEvent) => {
  console.log('Voice state:', event.state);
  console.log('Transcript:', event.transcript);
});
```

### Event Types

#### SuggestionEvent
```typescript
interface SuggestionEvent {
  type: 'pair_suggestion';
  session_id: string;
  timestamp: string;
  suggestion: {
    code: string;
    description: string;
    file_path: string;
    line_number: number;
  };
  metadata: {
    confidence: number;        // 0.0 - 1.0
    suggestion_type: 'completion' | 'refactoring' | 'explanation';
    context: {
      surrounding_code: string;
      current_function: string;
      file_type: string;
    };
  };
}
```

#### PairSessionEvent
```typescript
interface PairSessionEvent {
  type: 'pair_session';
  session_id: string;
  timestamp: string;
  event_type: 'session_started' | 'session_paused' | 'session_resumed' | 'session_stopped';
  metadata: {
    project_dir: string;
    watch_patterns: string[];
    voice_enabled: boolean;
  };
}
```

#### VoiceInteractionEvent
```typescript
interface VoiceInteractionEvent {
  type: 'voice_interaction';
  session_id: string;
  timestamp: string;
  state: 'listening' | 'processing' | 'speaking' | 'idle';
  transcript?: string;
  response?: string;
  metadata: {
    language: string;
    confidence: number;
  };
}
```

---

## Frontend Components

### PairProgrammingView (Web UI)

React component for the web interface:

```tsx
import PairProgrammingView from '@/components/PairProgrammingView';

function App() {
  return (
    <div>
      <PairProgrammingView />
    </div>
  );
}
```

**Features:**
- Session start/stop controls
- Real-time suggestion display
- Conversation interface
- Voice mode toggle
- Session statistics

**Location:** `apps/web-frontend/src/components/PairProgrammingView.tsx`

### InlineSuggestion (Electron App)

React component for inline suggestions in the Electron app:

```tsx
import { InlineSuggestion } from '@/renderer/components/InlineSuggestion';

function CodeEditor() {
  const handleAccept = (suggestion: Suggestion) => {
    // Apply suggestion to code
    console.log('Accepted:', suggestion);
  };

  const handleReject = (suggestion: Suggestion) => {
    // Dismiss suggestion
    console.log('Rejected:', suggestion);
  };

  return (
    <InlineSuggestion
      suggestion={{
        code: 'const result = await fetchData();',
        description: 'Add error handling for async operation',
        confidence: 0.85,
        type: 'refactoring'
      }}
      onAccept={handleAccept}
      onReject={handleReject}
    />
  );
}
```

**Features:**
- Inline code display
- Confidence level badges (high/medium/low)
- Accept/reject actions
- Optional context information
- i18n support (English/French)

**Location:** `apps/frontend/src/renderer/components/InlineSuggestion.tsx`

---

## Configuration

### File Watching Patterns

Control which files trigger suggestions:

```python
# Watch only Python files
agent.start_session(watch_patterns=["**/*.py"])

# Watch multiple file types
agent.start_session(watch_patterns=["**/*.py", "**/*.ts", "**/*.tsx", "**/*.jsx"])

# Exclude certain directories
agent.start_session(
    watch_patterns=["**/*"],
    ignore_patterns=["**/node_modules/**", "**/__pycache__/**", "**/.git/**"]
)
```

### Suggestion Filtering

Control suggestion quality:

```python
# Only show high-confidence suggestions (70%+)
agent.start_session(suggestion_confidence_threshold=0.7)

# Show all suggestions
agent.start_session(suggestion_confidence_threshold=0.0)

# Only show very high-confidence suggestions (90%+)
agent.start_session(suggestion_confidence_threshold=0.9)
```

### Voice Settings

Configure voice interaction:

```python
from apps.web_backend.services.voice_service import VoiceService

voice_service = VoiceService(
    stt_engine='google',      # Speech-to-text: 'google', 'sphinx', 'whisper'
    tts_engine='pyttsx3',     # Text-to-speech: 'pyttsx3'
    language='en-US',         # Language code
    voice_rate=150,           # Speech rate (words per minute)
    voice_volume=0.9          # Volume (0.0 - 1.0)
)

agent.start_session(voice_service=voice_service)
```

---

## Backend Architecture

### Core Components

#### PairProgrammingAgent
**Location:** `apps/backend/agents/pair_programming.py`

Main orchestrator for pair programming sessions.

**Key Methods:**
- `start_session()`: Initialize pair programming session
- `stop_session()`: End session and cleanup
- `process_file_change()`: Handle file change events
- `get_suggestion()`: Generate AI suggestion for code
- `toggle_voice_mode()`: Enable/disable voice interaction

#### SuggestionEngine
**Location:** `apps/backend/agents/suggestion_engine.py`

AI-powered code analysis and suggestion generation.

**Key Methods:**
- `analyze_code()`: Analyze code context
- `generate_inline_completion()`: Create code completions
- `suggest_refactoring()`: Identify refactoring opportunities
- `explain_code()`: Provide code explanations

#### FileWatcher
**Location:** `apps/web-backend/services/file_watcher.py`

Real-time file system monitoring using the `watchdog` library.

**Key Methods:**
- `start()`: Begin watching files
- `stop()`: Stop watching
- `add_pattern()`: Add file pattern to watch
- `remove_pattern()`: Remove file pattern

**Features:**
- Configurable file patterns
- Ignore patterns for exclusions
- Debouncing to prevent rapid-fire events
- Graceful fallback when watchdog not installed

#### VoiceService
**Location:** `apps/web-backend/services/voice_service.py`

Speech-to-text and text-to-speech capabilities.

**Components:**
- `SpeechToTextService`: Convert audio to text
- `TextToSpeechService`: Convert text to audio
- `VoiceService`: Combined STT/TTS interface

**Supported Engines:**
- STT: Google Speech Recognition, Sphinx, Whisper
- TTS: pyttsx3 (cross-platform)

---

## Troubleshooting

### Session Won't Start

**Symptom:** API returns 500 error when starting session

**Solution:**
```bash
# Check backend logs
tail -f apps/web-backend/logs/app.log

# Verify project directory exists
ls -la /path/to/your/project

# Ensure backend service is running
curl http://localhost:8000/health
```

### No Suggestions Appearing

**Symptom:** Files change but no suggestions received

**Possible Causes:**
1. **File patterns don't match**: Check watch_patterns include your file type
2. **Confidence threshold too high**: Lower the threshold
3. **WebSocket not connected**: Verify WebSocket connection in browser DevTools

**Debug:**
```python
# Check what files are being watched
status = requests.get(f'http://localhost:8000/api/agents/pair/status/{session_id}')
print(status.json()['files_watched'])

# Lower confidence threshold
requests.post('http://localhost:8000/api/agents/pair/start', json={
    'project_dir': '/path/to/project',
    'suggestion_confidence_threshold': 0.5  # Lower threshold
})
```

### Voice Mode Not Working

**Symptom:** Voice commands not recognized

**Solution:**
```bash
# Install voice dependencies
pip install SpeechRecognition pyttsx3

# For Whisper STT (more accurate)
pip install openai-whisper

# Check microphone permissions (macOS)
# System Preferences → Security & Privacy → Microphone

# Test voice service directly
python -c "
from apps.web_backend.services.voice_service import VoiceService
service = VoiceService()
print('Voice service initialized:', service.is_available())
"
```

### High CPU Usage

**Symptom:** Backend consuming excessive CPU

**Possible Causes:**
1. **Too many files watched**: Narrow down watch_patterns
2. **Rapid file changes**: Increase debounce delay
3. **High suggestion frequency**: Increase confidence threshold

**Optimize:**
```python
# Watch only specific directories
agent.start_session(
    watch_patterns=["src/**/*.py"],  # Instead of "**/*.py"
    ignore_patterns=["**/tests/**", "**/migrations/**"]
)

# Reduce suggestion frequency
agent.start_session(
    suggestion_confidence_threshold=0.8  # Higher threshold = fewer suggestions
)
```

### Mode Switching Not Working

**Symptom:** AgentManager doesn't switch modes

**Solution:**
```typescript
// Verify AgentManager initialization
import { agentManager } from '@/main/agent/agent-manager';

// Check current mode
console.log('Is pair mode:', agentManager.isPairMode());

// Listen for mode changes
agentManager.on('mode-changed', (isPairMode) => {
  console.log('Mode changed to:', isPairMode ? 'pair' : 'autonomous');
});

// Toggle mode
agentManager.setPairMode(true);
```

---

## Advanced Usage

### Custom Suggestion Filtering

Filter suggestions based on custom criteria:

```python
from apps.backend.agents.pair_programming import PairProgrammingAgent

class FilteredPairAgent(PairProgrammingAgent):
    def should_show_suggestion(self, suggestion):
        # Only show refactoring suggestions
        if suggestion.metadata.suggestion_type != 'refactoring':
            return False

        # Only for Python files
        if not suggestion.suggestion.file_path.endswith('.py'):
            return False

        # Only high confidence
        if suggestion.metadata.confidence < 0.85:
            return False

        return True

    async def process_file_change(self, file_path):
        suggestion = await super().process_file_change(file_path)
        if suggestion and self.should_show_suggestion(suggestion):
            return suggestion
        return None
```

### Integrating with Your Editor

Create an editor plugin to display inline suggestions:

```python
# Example: VS Code Extension Integration
import requests
import json

class PairProgrammingPlugin:
    def __init__(self, session_id):
        self.session_id = session_id
        self.ws = WebSocketClient('ws://localhost:8000/ws')
        self.ws.on('pair_suggestion', self.on_suggestion)

    def on_suggestion(self, event):
        # Display inline suggestion in editor
        editor = vscode.window.activeTextEditor
        if not editor:
            return

        suggestion = event['suggestion']
        position = vscode.Position(suggestion['line_number'], 0)

        # Show as inline decoration
        decoration = vscode.window.createTextEditorDecorationType({
            'after': {
                'contentText': f" 💡 {suggestion['description']}",
                'color': 'gray'
            }
        })

        editor.setDecorations(decoration, [vscode.Range(position, position)])
```

### Session Analytics

Track suggestion acceptance rates:

```python
from apps.backend.agents.pair_programming import PairProgrammingAgent

class AnalyticsPairAgent(PairProgrammingAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.analytics = {
            'suggestions_made': 0,
            'suggestions_accepted': 0,
            'suggestions_rejected': 0,
            'by_type': {
                'completion': {'made': 0, 'accepted': 0},
                'refactoring': {'made': 0, 'accepted': 0},
                'explanation': {'made': 0, 'accepted': 0}
            }
        }

    async def generate_suggestion(self, context):
        suggestion = await super().generate_suggestion(context)
        if suggestion:
            self.analytics['suggestions_made'] += 1
            suggestion_type = suggestion.metadata.suggestion_type
            self.analytics['by_type'][suggestion_type]['made'] += 1
        return suggestion

    def record_user_action(self, suggestion_id, action):
        # action: 'accepted' | 'rejected'
        self.analytics[f'suggestions_{action}'] += 1

        # Find suggestion type and update
        suggestion = self.get_suggestion_by_id(suggestion_id)
        if suggestion:
            suggestion_type = suggestion.metadata.suggestion_type
            if action == 'accepted':
                self.analytics['by_type'][suggestion_type]['accepted'] += 1

    def get_acceptance_rate(self):
        total = self.analytics['suggestions_made']
        if total == 0:
            return 0.0
        accepted = self.analytics['suggestions_accepted']
        return (accepted / total) * 100
```

---

## Best Practices

### 1. Start with Focused Patterns
Begin with specific file patterns and expand as needed:
```python
# Good: Focused on current work
agent.start_session(watch_patterns=["src/features/auth/**/*.ts"])

# Less optimal: Watching everything
agent.start_session(watch_patterns=["**/*"])
```

### 2. Use Appropriate Confidence Thresholds
- **Exploratory work**: Lower threshold (0.5-0.6) for more ideas
- **Production code**: Higher threshold (0.8-0.9) for quality suggestions
- **Learning**: Medium threshold (0.6-0.7) for balanced feedback

### 3. Leverage Voice for Specific Tasks
Voice mode works best for:
- Reviewing code while away from keyboard
- Explaining code to team members
- Hands-free exploration sessions

Avoid voice mode for:
- Rapid coding sessions (typing is faster)
- Noisy environments
- Tasks requiring precise syntax

### 4. Switch Modes Based on Task Phase
- **Planning phase**: Use pair mode for exploration and discussion
- **Implementation phase**: Use autonomous mode for bulk work
- **Review phase**: Use pair mode for iterative improvements

### 5. Review Suggestions Critically
AI suggestions are helpful but not perfect:
- Verify suggestions match your coding standards
- Check for edge cases and error handling
- Ensure suggestions fit your architecture
- Use suggestions as starting points, not final solutions

---

## Integration Examples

### Django Project
```python
# Watch Django app files
agent.start_session(
    watch_patterns=[
        "myapp/models/**/*.py",
        "myapp/views/**/*.py",
        "myapp/templates/**/*.html"
    ],
    ignore_patterns=[
        "**/migrations/**",
        "**/__pycache__/**"
    ]
)
```

### React/TypeScript Project
```python
# Watch React components and hooks
agent.start_session(
    watch_patterns=[
        "src/components/**/*.tsx",
        "src/hooks/**/*.ts",
        "src/utils/**/*.ts"
    ],
    ignore_patterns=[
        "**/node_modules/**",
        "**/*.test.tsx",
        "**/*.test.ts"
    ]
)
```

### Full-Stack Monorepo
```python
# Watch both frontend and backend
agent.start_session(
    watch_patterns=[
        "apps/frontend/src/**/*.tsx",
        "apps/backend/api/**/*.py",
        "shared/types/**/*.ts"
    ],
    ignore_patterns=[
        "**/node_modules/**",
        "**/__pycache__/**",
        "**/dist/**",
        "**/build/**"
    ]
)
```

---

## Performance Considerations

### File Watching Overhead
- Each watched file adds minimal CPU overhead (~0.01%)
- Watching 1000+ files is generally fine
- Use ignore_patterns to exclude large directories (node_modules, .git, etc.)

### Suggestion Generation Cost
- Each suggestion requires an LLM API call
- Cost: ~$0.001-0.01 per suggestion (depending on context size)
- Optimize by:
  - Using higher confidence thresholds
  - Watching fewer file types
  - Implementing custom filtering logic

### WebSocket Bandwidth
- Each suggestion event: ~1-5KB
- Typical session: <1MB/hour
- Negligible impact on network performance

---

## FAQ

**Q: Can I run multiple pair programming sessions simultaneously?**

A: Yes, each session has a unique session_id. You can run sessions for different projects or different file patterns in the same project.

**Q: Do suggestions work offline?**

A: No, suggestions require API access to Claude's LLM. However, file watching works offline - suggestions will resume when connectivity returns.

**Q: Can I customize the AI's behavior?**

A: Yes, you can subclass `PairProgrammingAgent` or `SuggestionEngine` to customize suggestion logic, filtering, and presentation.

**Q: How do I stop all active sessions?**

```bash
# List active sessions
curl http://localhost:8000/api/agents/pair/sessions

# Stop each session
for session_id in $(curl -s http://localhost:8000/api/agents/pair/sessions | jq -r '.[]'); do
  curl -X POST http://localhost:8000/api/agents/pair/stop/$session_id
done
```

**Q: Can I use pair programming mode with autonomous mode?**

A: Yes! Use `agentManager.setPairMode(true)` to enable pair mode, which causes the autonomous coder agent to pause after each subtask for manual continuation instead of auto-proceeding.

**Q: Does voice mode support languages other than English?**

A: Yes, the voice service supports multiple languages. Configure with:
```python
VoiceService(language='fr-FR')  # French
VoiceService(language='es-ES')  # Spanish
VoiceService(language='de-DE')  # German
```

---

## Additional Resources

- **Implementation Details**: See `implementation_plan.json` in the spec directory
- **E2E Tests**: `apps/backend/tests/test_e2e_integration.py`
- **API Tests**: `apps/web-backend/tests/test_pair_routes.py`
- **Component Tests**: `apps/frontend/src/renderer/components/InlineSuggestion.tsx`

---

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review logs in `apps/web-backend/logs/`
3. Join the [Discord community](https://discord.gg/KCXaPBr4Dj)
4. Open an issue on [GitHub](https://github.com/AndyMik90/Auto-Claude/issues)

---

**Happy Pair Programming! 🚀**
