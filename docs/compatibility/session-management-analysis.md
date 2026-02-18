# Session Management Analysis: Stateful vs Stateless

## Executive Summary

This document analyzes the fundamental differences between Claude SDK's stateful session management and OpenAI API's stateless model, and provides design recommendations for implementing session management in the OpenAI provider adapter.

**Key Finding:** OpenAI's stateless API requires the adapter to maintain conversation history, while Claude SDK manages this internally. This architectural difference impacts memory usage, token management, and session portability.

## Comparison: Claude SDK vs OpenAI API

### Claude SDK: Stateful Sessions

**Architecture:**
```python
class ClaudeAgentSession(AgentSession):
    def __init__(self, session_id: str, client: ClaudeSDKClient):
        self._client = client  # SDK manages state internally

    async def query(self, message: str) -> None:
        # Send message, SDK maintains history
        await self._client.query(message)

    async def receive_response(self) -> AsyncIterator[Any]:
        # SDK handles context internally
        async for msg in self._client.receive_response():
            yield msg
```

**Characteristics:**
- **Internal State Management**: SDK maintains conversation history
- **Session Isolation**: Each session has independent context
- **Automatic Context Window**: SDK handles token limits internally
- **Tool Execution**: SDK manages tool calls within session
- **Memory Efficient**: No redundant storage of conversation history

**Advantages:**
1. **Simple Integration**: No manual history tracking required
2. **Automatic Context Management**: SDK handles token limits
3. **Built-in Tool State**: Tool results managed transparently
4. **Session Continuity**: Natural conversation flow
5. **Lower Memory**: Single source of truth for history

**Disadvantages:**
1. **Opaque State**: Cannot inspect or modify conversation history
2. **Limited Control**: Cannot implement custom history strategies
3. **Provider Lock-in**: Dependent on SDK's session model
4. **No Portability**: Cannot serialize/deserialize sessions

### OpenAI API: Stateless Model

**Architecture:**
```python
class OpenAIProviderSession(AgentSession):
    def __init__(self, session_id: str, model: str, system_prompt: str):
        self._model = model
        self._messages: list[dict[str, str]] = []
        if system_prompt:
            self._messages.append({"role": "system", "content": system_prompt})

    async def complete(self, message: str) -> AsyncIterator[str]:
        # Add user message to history
        self._messages.append({"role": "user", "content": message})

        # Send entire conversation history
        client = AsyncOpenAI()
        response = await client.chat.completions.create(
            model=self._model,
            messages=self._messages,  # Full history required
            stream=True
        )

        # Process response and add to history
        full_response = ""
        async for chunk in response:
            full_response += chunk.content
            yield chunk.content

        self._messages.append({"role": "assistant", "content": full_response})
```

**Characteristics:**
- **Manual State Management**: Application maintains conversation history
- **Explicit Context**: Full history sent with each request
- **Manual Token Management**: Application handles context window limits
- **Custom Control**: Full visibility and control over conversation
- **Higher Memory**: Duplicate storage of conversation state

**Advantages:**
1. **Full Control**: Complete visibility into conversation history
2. **Custom Strategies**: Implement pruning, summarization, etc.
3. **Portability**: Can serialize/deserialize sessions
4. **Debugging**: Inspect and modify conversation state
5. **Flexibility**: Implement custom history management

**Disadvantages:**
1. **Complexity**: Must implement history management
2. **Token Management**: Manual context window handling
3. **Memory Overhead**: Duplicate storage of conversation
4. **Error Prone**: History synchronization bugs
5. **Tool State**: Must track tool calls and results manually

## Implementation Patterns

### Pattern 1: Simple List-Based History (LiteLLM Approach)

**Implementation:**
```python
class LiteLLMSession(AgentSession):
    def __init__(self, session_id: str, model: str, system_prompt: str):
        super().__init__(session_id, provider_name="litellm")
        self._model = model
        self._messages: list[dict[str, str]] = []

        if system_prompt:
            self._messages.append({"role": "system", "content": system_prompt})

    async def complete(self, message: str) -> AsyncIterator[str]:
        # Add user message
        self._messages.append({"role": "user", "content": message})

        # Send full history
        response = await litellm.acompletion(
            model=self._model,
            messages=self._messages,
            stream=True
        )

        # Process and store assistant response
        full_response = ""
        async for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                yield content

        self._messages.append({"role": "assistant", "content": full_response})
```

**Pros:**
- Simple implementation
- Low complexity
- Sufficient for short conversations

**Cons:**
- Unbounded memory growth
- No context window management
- Entire history sent each request
- High token usage for long sessions

**Best For:**
- Short conversations (< 50 messages)
- Low-volume applications
- Prototyping and testing

### Pattern 2: Sliding Window with Pruning

**Implementation:**
```python
class OpenAIProviderSession(AgentSession):
    def __init__(
        self,
        session_id: str,
        model: str,
        system_prompt: str,
        max_messages: int = 100,
        max_tokens: int = 128000,
    ):
        super().__init__(session_id, provider_name="openai")
        self._model = model
        self._system_prompt = system_prompt
        self._messages: list[dict[str, str]] = []
        self._max_messages = max_messages
        self._max_tokens = max_tokens

    def _prune_history(self) -> None:
        """Prune conversation history to fit context window."""
        # Always keep system prompt
        if not self._messages or self._messages[0].get("role") != "system":
            self._messages.insert(0, {"role": "system", "content": self._system_prompt})

        # Prune by message count
        while len(self._messages) > self._max_messages:
            # Remove oldest non-system message
            for i, msg in enumerate(self._messages):
                if msg.get("role") != "system":
                    self._messages.pop(i)
                    break

    def _estimate_tokens(self) -> int:
        """Estimate token count for current history."""
        # Rough estimate: ~4 characters per token
        total_chars = sum(len(m.get("content", "")) for m in self._messages)
        return total_chars // 4

    async def complete(self, message: str) -> AsyncIterator[str]:
        # Add user message
        self._messages.append({"role": "user", "content": message})

        # Prune if needed
        if self._estimate_tokens() > self._max_tokens * 0.8:
            self._prune_history()

        # Send (possibly pruned) history
        response = await openai.ChatCompletion.acreate(
            model=self._model,
            messages=self._messages,
            stream=True
        )

        # Process and store
        full_response = ""
        async for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                yield content

        self._messages.append({"role": "assistant", "content": full_response})
```

**Pros:**
- Bounded memory usage
- Context window management
- Suitable for long-running sessions
- Prevents token limit errors

**Cons:**
- Loses conversation context
- May forget important information
- Complex implementation
- Requires tuning of limits

**Best For:**
- Long-running agent sessions
- Production applications
- High-volume scenarios

### Pattern 3: Hierarchical Context with Summarization

**Implementation:**
```python
class OpenAIProviderSession(AgentSession):
    def __init__(self, session_id: str, model: str, system_prompt: str):
        super().__init__(session_id, provider_name="openai")
        self._model = model
        self._system_prompt = system_prompt
        self._recent_messages: list[dict[str, str]] = []  # Last N messages
        self._summary: str = ""  # Condensed conversation history
        self._max_recent = 20  # Keep last 20 messages verbatim

    async def _summarize_history(self) -> str:
        """Summarize old conversation history."""
        if not self._recent_messages:
            return self._summary

        # Use a fast model to summarize
        summary_prompt = f"""
        Previous context summary: {self._summary}

        Recent conversation to incorporate:
        {format_messages(self._recent_messages)}

        Provide an updated summary that captures the key points, decisions,
        and context from both the previous summary and recent conversation.
        Focus on information that might be relevant for future interactions.
        """

        # Create temporary client for summarization
        summary_response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",  # Use faster/cheaper model
            messages=[{"role": "user", "content": summary_prompt}],
            max_tokens=1000
        )

        return summary_response.choices[0].message.content

    async def complete(self, message: str) -> AsyncIterator[str]:
        # Add user message
        self._recent_messages.append({"role": "user", "content": message})

        # Check if we need to summarize
        if len(self._recent_messages) > self._max_recent:
            # Summarize old messages
            self._summary = await self._summarize_history()
            # Keep only recent messages
            self._recent_messages = self._recent_messages[-10:]

        # Build messages list
        messages = []
        if self._system_prompt:
            messages.append({"role": "system", "content": self._system_prompt})
        if self._summary:
            messages.append({"role": "system", "content": f"Context: {self._summary}"})
        messages.extend(self._recent_messages)

        # Send
        response = await openai.ChatCompletion.acreate(
            model=self._model,
            messages=messages,
            stream=True
        )

        # Process and store
        full_response = ""
        async for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                yield content

        self._recent_messages.append({"role": "assistant", "content": full_response})
```

**Pros:**
- Preserves conversation context
- Bounded token usage
- Retains important information
- Suitable for very long sessions

**Cons:**
- Most complex implementation
- Additional API cost for summarization
- Latency overhead for summarization
- Summarization quality varies

**Best For:**
- Multi-hour coding sessions
- Complex multi-step tasks
- Applications requiring long-term memory

## Context Window Management

### Token Estimation Strategies

**Strategy 1: Character-Based (Simple)**
```python
def estimate_tokens_char(text: str) -> int:
    """Rough estimate: ~4 characters per token."""
    return len(text) // 4
```

**Pros:**
- Fast
- No dependencies
- Reasonable approximation

**Cons:**
- Inaccurate for code
- Doesn't account for tokenization differences
- May underestimate

**Strategy 2: Tiktoken (Accurate)**
```python
import tiktoken

def estimate_tokens_tiktoken(text: str, model: str) -> int:
    """Accurate token count using tiktoken."""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))
```

**Pros:**
- Accurate
- OpenAI's official tokenizer
- Handles code correctly

**Cons:**
- Additional dependency
- Slower than character-based
- Model-specific encodings

**Recommendation:** Use Tiktoken for production accuracy.

### Context Window Budgeting

**Token Allocation Strategy:**
```python
class TokenBudget:
    """Manage token budget for conversation history."""

    def __init__(
        self,
        max_tokens: int = 128000,  # GPT-4-turbo limit
        reserve_ratio: float = 0.2,  # Reserve 20% for response
    ):
        self._max_tokens = max_tokens
        self._reserve = max_tokens * reserve_ratio
        self._available = max_tokens - self._reserve

    def can_fit(self, messages: list[dict]) -> bool:
        """Check if messages fit in budget."""
        total_tokens = sum(
            estimate_tokens_tiktoken(m.get("content", ""), "gpt-4")
            for m in messages
        )
        return total_tokens <= self._available

    def prune_to_fit(self, messages: list[dict]) -> list[dict]:
        """Prune messages to fit in budget."""
        # Always keep system prompt
        system_msgs = [m for m in messages if m.get("role") == "system"]
        other_msgs = [m for m in messages if m.get("role") != "system"]

        # Remove oldest messages until we fit
        while not self.can_fit(system_msgs + other_msgs) and other_msgs:
            other_msgs.pop(0)

        return system_msgs + other_msgs
```

## Tool Execution and State Management

### Challenge: Tool Calls in Stateless API

**Claude SDK (Stateful):**
```python
# SDK handles tool calls internally
# No manual tracking required
await client.query("Use the bash tool to run tests")
# SDK receives tool_use block, executes tool, sends result, continues
```

**OpenAI API (Stateless):**
```python
# Must manually track tool calls
response = await openai.ChatCompletion.acreate(
    model="gpt-4",
    messages=history,
    tools=[...],
    tool_choice="auto"
)

# Check if model wants to call a tool
if response.choices[0].finish_reason == "tool_calls":
    # Add assistant message with tool call
    history.append(response.choices[0].message)

    # Execute each tool call
    for tool_call in response.choices[0].message.tool_calls:
        result = execute_tool(tool_call.function.name, tool_call.function.arguments)

        # Add tool result message
        history.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result)
        })

    # Send another request with tool results
    response = await openai.ChatCompletion.acreate(
        model="gpt-4",
        messages=history,
        tools=[...]
    )
```

**Implications:**
1. **State Tracking**: Must track tool calls and results
2. **Multiple Round-trips**: Each tool call requires a new API request
3. **History Management**: Tool calls and results occupy tokens
4. **Error Handling**: Must handle tool failures gracefully

### Tool State Management Pattern

```python
class OpenAIProviderSession(AgentSession):
    def __init__(self, ...):
        super().__init__(...)
        self._messages: list[dict] = []
        self._pending_tool_calls: list[dict] = []

    async def complete(self, message: str) -> AsyncIterator[str]:
        # Add user message
        self._messages.append({"role": "user", "content": message})

        # Loop until we get a final response (no tool calls)
        while True:
            # Send current history
            response = await openai.ChatCompletion.acreate(
                model=self._model,
                messages=self._messages,
                tools=self._get_tool_schemas(),
                stream=True
            )

            # Collect full response
            full_response = ""
            tool_calls = []

            async for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
                if chunk.choices[0].delta.tool_calls:
                    tool_calls.extend(chunk.choices[0].delta.tool_calls)

            # Add assistant message
            assistant_msg = {"role": "assistant", "content": full_response}
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            self._messages.append(assistant_msg)

            # If no tool calls, we're done
            if not tool_calls:
                break

            # Execute tools and add results
            for tool_call in tool_calls:
                result = await self._execute_tool(tool_call)
                self._messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })

            # Loop again to get final response
```

## Session Persistence and Serialization

### Portability Considerations

**Claude SDK:**
- Sessions not serializable (SDK internal state)
- Cannot save/restore sessions
- Provider lock-in

**OpenAI API:**
- Sessions fully serializable (just message list)
- Can save/restore sessions
- Provider portable

**Serialization Pattern:**
```python
class OpenAIProviderSession(AgentSession):
    def to_dict(self) -> dict:
        """Serialize session to dict."""
        return {
            "session_id": self.session_id,
            "model": self._model,
            "messages": self._messages,
            "created_at": self._created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OpenAIProviderSession":
        """Deserialize session from dict."""
        session = cls(
            session_id=data["session_id"],
            model=data["model"],
            system_prompt="",  # System prompt in first message
        )
        session._messages = data["messages"]
        return session
```

**Use Cases:**
- Session checkpointing
- Resume interrupted sessions
- Debug conversation history
- Transfer between providers

## Recommendations for OpenAI Provider Implementation

### Recommended Approach: Hybrid State Management

**Architecture:**
```python
class OpenAIProviderSession(AgentSession):
    """OpenAI session with intelligent history management."""

    def __init__(
        self,
        session_id: str,
        model: str,
        system_prompt: str,
        history_strategy: str = "sliding_window",  # or "summarization"
        max_tokens: int = 128000,
        max_messages: int = 100,
    ):
        super().__init__(session_id, provider_name="openai")
        self._model = model
        self._system_prompt = system_prompt
        self._history_strategy = history_strategy
        self._max_tokens = max_tokens
        self._max_messages = max_messages

        # Message storage
        self._messages: list[dict[str, Any]] = []

        # Add system prompt
        if system_prompt:
            self._messages.append({
                "role": "system",
                "content": system_prompt
            })

        # Token budget
        self._token_budget = TokenBudget(max_tokens)

        # Optional: Summarization for long sessions
        self._summary: str = ""

    async def complete(self, message: str) -> AsyncIterator[str]:
        """Send message and stream response."""
        # Add user message
        self._messages.append({
            "role": "user",
            "content": message
        })

        # Prune/summarize if needed
        await self._manage_history()

        # Send request
        response = await openai.ChatCompletion.acreate(
            model=self._model,
            messages=self._messages,
            stream=True
        )

        # Process response
        full_response = ""
        async for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                yield content

        # Store assistant response
        self._messages.append({
            "role": "assistant",
            "content": full_response
        })

    async def _manage_history(self) -> None:
        """Manage conversation history based on strategy."""
        if self._history_strategy == "sliding_window":
            self._prune_to_fit()
        elif self._history_strategy == "summarization":
            await self._summarize_if_needed()

    def _prune_to_fit(self) -> None:
        """Prune messages to fit token budget."""
        # Keep system prompt
        system_msgs = [m for m in self._messages if m.get("role") == "system"]
        other_msgs = [m for m in self._messages if m.get("role") != "system"]

        # Prune oldest until fits
        while not self._token_budget.can_fit(system_msgs + other_msgs):
            if not other_msgs:
                break
            other_msgs.pop(0)

        self._messages = system_msgs + other_msgs
```

### Key Implementation Decisions

**1. History Management Strategy**

| Strategy | Complexity | Memory Usage | Context Loss | Best For |
|----------|-----------|--------------|--------------|----------|
| Simple List | Low | High | None | Short sessions |
| Sliding Window | Medium | Low | High | Long sessions |
| Summarization | High | Low | Low | Very long sessions |

**Recommendation:** Start with sliding window, add summarization as optimization.

**2. Token Estimation**

```python
# Use tiktoken for accuracy
import tiktoken

def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))
```

**3. Context Window Budgeting**

```python
# Reserve 20% for response
MAX_TOKENS = 128000  # GPT-4-turbo
RESERVE_RATIO = 0.2
AVAILABLE_TOKENS = MAX_TOKENS * (1 - RESERVE_RATIO)
```

**4. Tool Call Tracking**

- Maintain tool call history in messages list
- Execute tools and append results
- Loop until final response (no more tool calls)

**5. Session Serialization**

- Implement `to_dict()` / `from_dict()` methods
- Save to JSON for persistence
- Enable session checkpointing

## Migration Path: From Claude to OpenAI

### Compatibility Layer

```python
class SessionAdapter:
    """Adapt between Claude SDK sessions and OpenAI sessions."""

    @staticmethod
    def claude_to_openai(claude_session: ClaudeAgentSession) -> OpenAIProviderSession:
        """Convert Claude session to OpenAI session."""
        # Create new OpenAI session
        openai_session = OpenAIProviderSession(
            session_id=claude_session.session_id.replace("claude", "openai"),
            model="gpt-4",  # Map model
            system_prompt=extract_system_prompt(claude_session),
        )

        # Note: Cannot directly export Claude conversation history
        # SDK doesn't expose it. Must rebuild from application state.

        return openai_session
```

**Important:** Cannot directly transfer conversation history from Claude to OpenAI due to SDK's opaque state management. Application must rebuild context.

### Migration Considerations

**Breaking Changes:**
1. **Session Loss**: Cannot continue Claude sessions in OpenAI
2. **History Access**: Claude SDK doesn't expose conversation history
3. **Tool State**: Tool execution state not portable
4. **Behavior Differences**: Response quality, token usage, etc.

**Migration Strategy:**
1. **Feature Detection**: Check `provider.supports_feature(Feature.SESSION_PORTABILITY)`
2. **Graceful Degradation**: Warn user about session loss
3. **Rebuild Context**: Extract key information from application state
4. **Start Fresh**: Create new session with similar configuration

## Testing Strategy

### Unit Tests

```python
def test_session_history_pruning():
    """Test that history pruning works correctly."""
    session = OpenAIProviderSession(
        session_id="test",
        model="gpt-4",
        system_prompt="You are a helpful assistant.",
        max_messages=5,
    )

    # Add 10 messages
    for i in range(10):
        session._messages.append({"role": "user", "content": f"Message {i}"})
        session._prune_to_fit()

    # Should only have system + 4 messages (total 5)
    assert len(session._messages) == 5
    assert session._messages[0]["role"] == "system"

def test_token_budget():
    """Test token budget management."""
    budget = TokenBudget(max_tokens=1000, reserve_ratio=0.2)
    assert budget._available == 800

    messages = [{"role": "user", "content": "x" * 4000}]  # ~1000 tokens
    assert not budget.can_fit(messages)

    pruned = budget.prune_to_fit(messages)
    assert budget.can_fit(pruned)
```

### Integration Tests

```python
async def test_openai_session_complete_flow():
    """Test complete OpenAI session flow."""
    provider = OpenAIProvider(config)

    session = provider.create_session(
        SessionConfig(
            name="test-session",
            system_prompt="You are a helpful assistant.",
            model="gpt-4",
        )
    )

    # Send message
    response_chunks = []
    async for chunk in session.complete("Hello!"):
        response_chunks.append(chunk)

    response = "".join(response_chunks)
    assert len(response) > 0

    # Check history
    assert len(session.messages) == 3  # system, user, assistant
```

### Comparison Tests

```python
async def test_provider_parity():
    """Test that both providers handle same task."""
    claude_provider = ClaudeAgentProvider(claude_config)
    openai_provider = OpenAIProvider(openai_config)

    # Create sessions
    claude_session = claude_provider.create_session(...)
    openai_session = openai_provider.create_session(...)

    # Send same message
    message = "Write a Python function to add two numbers."

    claude_response = await collect_stream(claude_session.query(message))
    openai_response = await collect_stream(openai_session.complete(message))

    # Both should produce working code
    assert "def" in claude_response
    assert "def" in openai_response
```

## Conclusion

### Key Takeaways

1. **Fundamental Difference**: Claude SDK is stateful, OpenAI API is stateless
2. **Manual History Management**: OpenAI adapter must maintain conversation history
3. **Token Budgeting**: Critical for long-running sessions
4. **Tool Call Tracking**: More complex in stateless model
5. **Serialization Advantage**: OpenAI sessions are portable

### Implementation Priority

**Phase 1: Basic State Management**
- Implement simple list-based history
- Basic token estimation
- Tool call tracking
- Session serialization

**Phase 2: Context Window Management**
- Accurate token counting (tiktoken)
- Sliding window pruning
- Token budgeting
- Context limit warnings

**Phase 3: Advanced Features**
- Summarization for very long sessions
- History compression
- Session checkpointing
- Migration tools

### Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Unbounded memory growth | High | Implement pruning strategies |
| Context window overflow | High | Token budgeting + monitoring |
| Tool call state errors | Medium | Comprehensive testing |
| Session portability confusion | Low | Clear documentation |

### Recommended Starting Point

For initial implementation, use **Pattern 2 (Sliding Window)** with:
- Tiktoken for accurate token counting
- Token budget with 20% reserve
- Simple message count limit (e.g., 100 messages)
- Tool call tracking in message history
- Session serialization for debugging

This provides a balance of simplicity and production readiness.
