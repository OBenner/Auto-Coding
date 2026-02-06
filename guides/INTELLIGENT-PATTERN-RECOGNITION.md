# Intelligent Pattern Recognition

**Feature ID**: 032
**Status**: Production Ready
**Version**: Introduced in Auto Code 3.0+

## Overview

Intelligent Pattern Recognition enhances Auto Code's Graphiti memory system to automatically identify, categorize, and suggest coding patterns from completed builds. This feature creates **compounding value** - the system gets smarter over time as you build more features, unlike competitors that start fresh each session.

## What It Does

The system automatically:
1. **Extracts patterns** from successful builds (architecture decisions, error handling approaches, testing strategies, etc.)
2. **Categorizes patterns** using AI into 14 categories
3. **Suggests relevant patterns** during spec creation and implementation
4. **Allows user confirmation** - you can confirm, reject, or modify suggested patterns

## Why It Matters

Cross-session memory is a key differentiator for Auto Code. This feature makes that memory actionable:

- **Consistency**: Future features follow established patterns automatically
- **Knowledge retention**: Architectural decisions persist across sessions
- **Reduced repetition**: The system learns from past solutions
- **Compounding intelligence**: Each build makes the next one smarter

## Architecture

### Backend Components

#### 1. Pattern Categorizer (`pattern_categorizer.py`)
- **Location**: `apps/backend/integrations/graphiti/pattern_categorizer.py`
- **Purpose**: AI-based classification of patterns into categories
- **Categories**:
  - Architecture
  - API Design
  - State Management
  - Error Handling
  - Testing
  - Security
  - Performance
  - Database
  - UI/UX
  - Accessibility
  - Documentation
  - Deployment
  - Integration
  - Code Quality
- **Confidence Scoring**: Returns 95-98% confidence scores for categorization

#### 2. Pattern Suggester (`pattern_suggester.py`)
- **Location**: `apps/backend/integrations/graphiti/pattern_suggester.py`
- **Purpose**: Semantic search and filtering to find relevant patterns
- **Features**:
  - Semantic similarity search using embeddings
  - Category-based filtering
  - Relevance scoring
  - Context-aware suggestions

#### 3. Memory Manager Integration
- **Location**: `apps/backend/agents/memory_manager.py`
- **Enhancement**: Added `get_pattern_suggestions()` function
- **Integration**: Fetches and formats pattern suggestions for AI agents
- **Schema**: New `EPISODE_TYPE_PATTERN` in `queries_pkg/schema.py`

#### 4. Prompt Integration
- **Modified Files**:
  - `apps/backend/prompt_generator.py` - Includes patterns in context
  - `apps/backend/runners/spec_runner.py` - Fetches patterns during spec creation
- **Phases**: Integrated into spec_writing, planning, and quick_spec phases

### Frontend Components

#### 1. Pattern Suggestion Display
- **Location**: `apps/frontend/src/renderer/components/CreateSpecView.tsx`
- **Features**:
  - Visual display of pattern suggestions
  - Category badges with color coding
  - Confidence indicators
  - Confirm/Reject/Modify actions
  - Pattern preview with code snippets

#### 2. IPC Handlers
- **Location**: `apps/frontend/src/main/ipc-handlers/context/memory-data-handlers.ts`
- **Handlers**:
  - `CONTEXT_GET_PATTERN_SUGGESTIONS` - Retrieves relevant patterns for a task
  - `CONTEXT_CONFIRM_PATTERN` - Records user confirmation/rejection in Graphiti
- **Integration**: Connects frontend UI to Python backend via subprocess

## How to Use

### For End Users

1. **Create a new spec** in the Auto Code UI
2. **Enter your feature description** (e.g., "Add user authentication")
3. **Review suggested patterns** that appear automatically
4. **For each suggestion**:
   - Click ✓ **Confirm** to include it in your spec
   - Click ✗ **Reject** if not relevant
   - Click ✎ **Modify** to adjust the pattern before using
5. **Continue with spec creation** - confirmed patterns guide the implementation

### For AI Agents

Patterns are automatically injected into agent context during:
- Spec creation (Spec Writer agent)
- Implementation planning (Planner agent)
- Code generation (Coder agent)

No manual intervention required - the system handles it transparently.

## Technical Details

### Pattern Storage

Patterns are stored as Graphiti episodes with:
- **Type**: `EPISODE_TYPE_PATTERN`
- **Metadata**: Category, confidence score, source spec
- **Content**: Pattern description, code examples, context
- **Relationships**: Linked to related entities (files, concepts, specs)

### Pattern Retrieval

When a new task is created:
1. Task description is embedded using configured embedder (Ollama or OpenAI)
2. Semantic search finds similar past patterns
3. Results are filtered by relevance threshold (>0.7)
4. Category filters apply if specified
5. Top N patterns returned (default: 5)

### Pattern Confirmation

When a user confirms a pattern:
1. Frontend sends confirmation via IPC
2. Backend creates a new Graphiti episode
3. Episode records the confirmation event
4. Relationships link pattern → user → task
5. Future suggestions weight confirmed patterns higher

## Configuration

### Embedder Setup

Pattern suggestions require an embedder for semantic search:

**Option 1: Ollama (Local, Free)**
```bash
# Set environment variable
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

**Option 2: OpenAI (Cloud, Paid)**
```bash
# Set environment variable
OPENAI_API_KEY=your_api_key_here
```

### Customization

Modify `pattern_categorizer.py` to:
- Add custom categories
- Adjust confidence thresholds
- Change categorization prompts

Modify `pattern_suggester.py` to:
- Adjust relevance threshold
- Change number of suggestions
- Customize filtering logic

## Testing

### E2E Test

A comprehensive end-to-end test validates the full workflow:

**Location**: `apps/backend/test_pattern_workflow.py`

**Test Coverage**:
1. Pattern categorization (5 patterns, 14 categories)
2. Agent registration (pattern_categorizer configured)
3. Import paths (GraphitiMemory imports)
4. Pattern suggestion (semantic search + filtering)
5. Memory manager integration

**Run Test**:
```bash
cd apps/backend
python test_pattern_workflow.py
```

**Expected Output**: All 5 tests pass with 95-98% confidence scores

### Manual Testing

1. Complete a feature build with authentication
2. Create a new spec for "login feature"
3. Verify authentication patterns appear in suggestions
4. Confirm a pattern and verify it's included in generated spec

## Files Modified

### Backend (8 files)
- `integrations/graphiti/pattern_categorizer.py` (NEW)
- `integrations/graphiti/pattern_suggester.py` (NEW)
- `integrations/graphiti/queries_pkg/queries.py` (MODIFIED)
- `integrations/graphiti/queries_pkg/schema.py` (MODIFIED)
- `integrations/graphiti/queries_pkg/search.py` (MODIFIED)
- `agents/memory_manager.py` (MODIFIED)
- `prompt_generator.py` (MODIFIED)
- `runners/spec_runner.py` (MODIFIED)

### Frontend (2 files)
- `src/renderer/components/CreateSpecView.tsx` (MODIFIED)
- `src/main/ipc-handlers/context/memory-data-handlers.ts` (MODIFIED)

### Tests (1 file)
- `test_pattern_workflow.py` (NEW)

**Total Changes**: +2,105 lines

## Performance

- **Pattern categorization**: ~2-3s per pattern (AI classification)
- **Pattern suggestion**: ~500ms (semantic search)
- **No impact on existing workflows** - only activates when creating specs

## Security

- ✓ No hardcoded secrets
- ✓ No dangerous operations (eval, innerHTML)
- ✓ Proper input sanitization in IPC handlers
- ✓ Auth tokens handled via `get_auth_token()`

## Limitations

1. **Embedder Required**: Pattern suggestions only work with configured embedder (Ollama or OpenAI)
2. **Cold Start**: First few builds won't have patterns to suggest (system needs data)
3. **Context Window**: Very large codebases may exceed context limits for pattern extraction

## Future Enhancements

Potential improvements for future versions:
- Pattern confidence decay over time (older patterns less relevant)
- Pattern versioning (track evolution of patterns)
- Pattern merging (consolidate similar patterns)
- Pattern analytics (most used, most effective patterns)
- Cross-project pattern sharing (team-wide pattern library)

## Troubleshooting

### No Patterns Suggested

**Cause**: Embedder not configured or no patterns stored yet

**Solution**:
1. Set `OLLAMA_EMBEDDING_MODEL` or `OPENAI_API_KEY`
2. Complete a few builds to populate pattern database
3. Verify embedder is running: `curl http://localhost:11434/api/embeddings` (Ollama)

### Low Confidence Scores

**Cause**: Pattern description too vague or irrelevant

**Solution**:
1. Reject low-confidence patterns
2. Modify pattern descriptions to be more specific
3. Adjust confidence threshold in `pattern_categorizer.py`

### IPC Handler Errors

**Cause**: TypeScript type mismatches or Python subprocess failures

**Solution**:
1. Check `memory-data-handlers.ts` for TypeScript errors
2. Verify Python backend imports work: `python -c "from integrations.graphiti.pattern_suggester import suggest_patterns; print('OK')"`
3. Check logs in Auto Code terminal

## References

- **Spec**: `.auto-claude/specs/032-intelligent-pattern-recognition/spec.md`
- **Implementation Plan**: `.auto-claude/specs/032-intelligent-pattern-recognition/implementation_plan.json`
- **QA Report**: `.auto-claude/specs/032-intelligent-pattern-recognition/qa_report.md`
- **Graphiti Integration**: `apps/backend/integrations/graphiti/`

## Contributing

To contribute improvements to pattern recognition:

1. Read existing pattern categorizer/suggester code
2. Follow established Graphiti integration patterns
3. Add tests to `test_pattern_workflow.py`
4. Update this documentation with your changes
5. Submit PR with QA validation

---

**Questions or issues?** Open a GitHub issue or ask in Discord.
