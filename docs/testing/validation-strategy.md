# Testing Strategy for Provider Interchangeability

Comprehensive testing strategy for validating that Claude and OpenAI providers are truly interchangeable in the Auto Code multi-provider architecture.

## Overview

The testing strategy ensures that AI providers (Claude SDK, OpenAI, LiteLLM, OpenRouter) are functionally interchangeable, meaning that switching providers should not break existing functionality. Tests validate equivalence at multiple levels: unit, integration, end-to-end, and provider comparison.

**Testing Goals:**
- **Functional Equivalence** - Same tasks produce functionally equivalent results across providers
- **Behavioral Consistency** - Tool calling, error handling, and session management work consistently
- **Security Parity** - All providers enforce the same security model
- **Performance Baselines** - Response times and token usage within acceptable ranges
- **Feature Compatibility** - Feature-gated code gracefully degrades for unsupported capabilities

## Testing Pyramid

```
                    ┌─────────────────────┐
                    │   Provider          │  ← Provider Comparison Tests
                    │   Comparison        │     (Validate interchangeability)
                    │   (E2E)             │
                    ├─────────────────────┤
                    │   Integration       │  ← Integration Tests
                    │   Tests             │     (Provider + MCP + Security)
                    ├─────────────────────┤
                    │   Unit Tests        │  ← Unit Tests
                    │                     │     (Individual components)
                    └─────────────────────┘
```

**Test Distribution:**
- **70% Unit Tests** - Fast, isolated component testing
- **20% Integration Tests** - Provider + MCP + Security integration
- **10% Provider Comparison Tests** - Cross-provider equivalence validation

## Test Organization

```
tests/
├── unit/
│   ├── providers/
│   │   ├── test_claude_provider.py
│   │   ├── test_openai_provider.py
│   │   ├── test_litellm_provider.py
│   │   └── test_openrouter_provider.py
│   ├── adapters/
│   │   ├── test_base_provider.py
│   │   └── test_factory.py
│   ├── security/
│   │   ├── test_security_wrapper.py
│   │   └── test_auth_provider.py
│   ├── mcp/
│   │   ├── test_mcp_client.py
│   │   └── test_tool_translator.py
│   └── tools/
│       └── test_feature_detection.py
├── integration/
│   ├── test_provider_switching.py
│   ├── test_mcp_integration.py
│   ├── test_security_enforcement.py
│   ├── test_session_management.py
│   └── test_error_handling.py
├── provider_comparison/
│   ├── test_code_generation.py
│   ├── test_tool_calling.py
│   ├── test_spec_creation.py
│   └── test_qa_review.py
└── e2e/
    ├── test_full_spec_workflow.py
    └── test_provider_fallback.py
```

## Unit Tests

### Provider Unit Tests

**Purpose:** Validate individual provider implementations in isolation.

**Test Coverage:**

```python
# tests/unit/providers/test_claude_provider.py
class TestClaudeProvider:
    """Test Claude Agent SDK provider implementation."""

    def test_provider_name(self):
        """Provider name is 'claude'."""
        provider = ClaudeAgentProvider(config)
        assert provider.name == "claude"

    def test_create_session(self):
        """Session creation succeeds with valid config."""
        session = provider.create_session(session_config)
        assert session.is_active
        assert session.session_id is not None

    def test_send_message_streaming(self):
        """Message sending returns async iterator."""
        async def test_stream():
            chunks = []
            async for chunk in provider.send_message("Hello"):
                chunks.append(chunk)
            assert len(chunks) > 0
        asyncio.run(test_stream())

    def test_get_supported_models(self):
        """Returns list of Claude models."""
        models = provider.get_supported_models()
        assert "claude-sonnet-4-5-20250929" in models
        assert "claude-haiku-4-20250929" in models

    def test_validate_config_success(self):
        """Valid config returns True."""
        config.anthropic_api_key = "sk-ant-..."
        assert provider.validate_config() is True

    def test_validate_config_missing_key(self):
        """Missing API key returns False."""
        config.anthropic_api_key = ""
        assert provider.validate_config() is False

    def test_health_check(self):
        """Health check passes with valid config."""
        assert provider.health_check() is True
```

**Parallel Tests for OpenAI Provider:**

```python
# tests/unit/providers/test_openai_provider.py
class TestOpenAIProvider:
    """Test OpenAI provider implementation."""

    def test_provider_name(self):
        """Provider name is 'openai'."""
        assert provider.name == "openai"

    def test_create_session_stateful(self):
        """Session maintains conversation history."""
        session = provider.create_session(session_config)
        assert session.history == []

    def test_send_message_with_history(self):
        """Conversation history is maintained."""
        # Send first message
        async for _ in provider.send_message("First message"):
            pass

        # Send second message
        async for _ in provider.send_message("Second message"):
            pass

        # Verify history has 2 entries
        assert len(session.history) == 2
```

### Security Wrapper Unit Tests

```python
# tests/unit/security/test_security_wrapper.py
class TestSecurityWrapper:
    """Test security wrapper enforcement."""

    def test_command_allowlisting(self):
        """Commands not in allowlist are blocked."""
        wrapper = SecurityWrapper(provider, security_config)

        # Allowed command
        assert wrapper.is_command_allowed("ls") is True

        # Blocked command
        assert wrapper.is_command_allowed("rm -rf /") is False

    def test_file_permissions_enforcement(self):
        """File ops outside project dir are blocked."""
        # Inside project dir - allowed
        assert wrapper.is_path_allowed("/project/file.txt") is True

        # Outside project dir - blocked
        assert wrapper.is_path_allowed("/etc/passwd") is False

    def test_pretooluse_hook(self):
        """PreToolUse hook intercepts tool calls."""
        hook_called = False

        def pre_tool_hook(tool_name, tool_input):
            nonlocal hook_called
            hook_called = True
            return True  # Allow execution

        wrapper.register_pre_tool_hook(pre_tool_hook)

        # Execute tool
        wrapper.execute_tool("bash", {"command": "ls"})

        assert hook_called is True
```

### Tool Schema Translator Tests

```python
# tests/unit/mcp/test_tool_translator.py
class TestToolSchemaTranslator:
    """Test bidirectional tool schema translation."""

    def test_claude_to_openai_translation(self):
        """Claude tool schema converts to OpenAI function format."""
        translator = ToolSchemaTranslator()

        claude_tool = {
            "name": "search_files",
            "description": "Search files in project",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                }
            }
        }

        openai_function = translator.claude_to_openai(claude_tool)

        assert openai_function["type"] == "function"
        assert openai_function["function"]["name"] == "search_files"
        assert "parameters" in openai_function["function"]

    def test_openai_to_claude_translation(self):
        """OpenAI function converts to Claude tool use format."""
        openai_function = {
            "name": "write_file",
            "arguments": {"path": "test.txt", "content": "hello"}
        }

        claude_tool_use = translator.openai_to_claude(openai_function)

        assert claude_tool_use["type"] == "tool_use"
        assert claude_tool_use["name"] == "write_file"
        assert claude_tool_use["input"] == {"path": "test.txt", "content": "hello"}
```

### Feature Detection Tests

```python
# tests/unit/tools/test_feature_detection.py
class TestFeatureDetection:
    """Test provider feature detection API."""

    def test_claude_supports_extended_thinking(self):
        """Claude supports extended thinking."""
        provider = ClaudeAgentProvider(config)
        assert provider.supports_feature(ProviderFeature.EXTENDED_THINKING) is True

    def test_openai_does_not_support_extended_thinking(self):
        """OpenAI does not support extended thinking."""
        provider = OpenAIProvider(config)
        assert provider.supports_feature(ProviderFeature.EXTENDED_THINKING) is False

    def test_all_providers_support_streaming(self):
        """All providers support streaming responses."""
        for provider in [claude, openai, litellm]:
            assert provider.supports_feature(ProviderFeature.STREAMING_RESPONSES) is True
```

## Integration Tests

### Provider Switching Tests

**Purpose:** Validate that switching providers at runtime works correctly.

```python
# tests/integration/test_provider_switching.py
class TestProviderSwitching:
    """Test runtime provider switching."""

    def test_switch_from_claude_to_openai(self):
        """Switch from Claude to OpenAI mid-session."""
        # Start with Claude
        config = ProviderConfig.from_env()
        config.provider = "claude"
        claude_provider = create_engine_provider(config)
        session = claude_provider.create_session(session_config)

        # Send message with Claude
        async for chunk in claude_provider.send_message("Hello"):
            claude_response = chunk

        # Switch to OpenAI
        config.provider = "openai"
        openai_provider = create_engine_provider(config)

        # New session with OpenAI (sessions are provider-specific)
        openai_session = openai_provider.create_session(session_config)

        # Send same message to OpenAI
        async for chunk in openai_provider.send_message("Hello"):
            openai_response = chunk

        # Responses should be different but both valid
        assert claude_response != openai_response
        assert len(claude_response) > 0
        assert len(openai_response) > 0

    def test_environment_based_switching(self):
        """Provider switches via environment variable."""
        # Test with Claude
        os.environ["AI_ENGINE_PROVIDER"] = "claude"
        config = ProviderConfig.from_env()
        provider = create_engine_provider(config)
        assert provider.name == "claude"

        # Test with OpenAI
        os.environ["AI_ENGINE_PROVIDER"] = "openai"
        config = ProviderConfig.from_env()
        provider = create_engine_provider(config)
        assert provider.name == "openai"
```

### MCP Integration Tests

```python
# tests/integration/test_mcp_integration.py
class TestMCPIntegration:
    """Test MCP server integration across providers."""

    def test_claude_mcp_context7(self):
        """Claude uses built-in MCP Context7."""
        provider = ClaudeAgentProvider(config)
        session = provider.create_session(session_config)

        # Context7 should be available as tool
        tools = session.get_available_tools()
        assert "context7" in tools

    def test_openai_custom_mcp_context7(self):
        """OpenAI uses custom MCP client for Context7."""
        provider = OpenAIProvider(config)
        provider.enable_mcp_server("context7")

        session = provider.create_session(session_config)

        # Custom MCP client should translate Context7 to OpenAI function
        tools = session.get_available_tools()
        assert "context7" in tools

    def test_mcp_tool_execution_equivalence(self):
        """Same MCP tool produces equivalent results across providers."""
        # Execute Context7 query with Claude
        claude_provider = ClaudeAgentProvider(config)
        claude_session = claude_provider.create_session(session_config)
        claude_result = claude_session.execute_tool("context7", {"query": "pytest usage"})

        # Execute Context7 query with OpenAI
        openai_provider = OpenAIProvider(config)
        openai_provider.enable_mcp_server("context7")
        openai_session = openai_provider.create_session(session_config)
        openai_result = openai_session.execute_tool("context7", {"query": "pytest usage"})

        # Results should be functionally equivalent (same docs retrieved)
        assert claude_result["source"] == openai_result["source"]
        assert "pytest" in claude_result["content"]
        assert "pytest" in openai_result["content"]
```

### Security Enforcement Tests

```python
# tests/integration/test_security_enforcement.py
class TestSecurityEnforcement:
    """Test security wrapper enforcement across providers."""

    def test_claude_native_security(self):
        """Claude uses built-in security."""
        provider = ClaudeAgentProvider(config)
        session = provider.create_session(session_config)

        # Attempt to access file outside project
        with pytest.raises(PermissionError):
            session.execute_tool("read_file", {"path": "/etc/passwd"})

    def test_openai_security_wrapper(self):
        """OpenAI uses security wrapper."""
        provider = OpenAIProvider(config)
        wrapped_provider = SecurityWrapper(provider, security_config)

        session = wrapped_provider.create_session(session_config)

        # Attempt to access file outside project
        with pytest.raises(PermissionError):
            session.execute_tool("read_file", {"path": "/etc/passwd"})

    def test_command_allowlisting_parity(self):
        """Both providers enforce same command allowlist."""
        security_config = SecurityConfig.from_project("/project")

        # Claude native security
        claude_provider = ClaudeAgentProvider(config)
        assert "ls" in claude_provider.get_allowed_commands()

        # OpenAI security wrapper
        openai_provider = OpenAIProvider(config)
        wrapped = SecurityWrapper(openai_provider, security_config)
        assert "ls" in wrapped.get_allowed_commands()
```

### Session Management Tests

```python
# tests/integration/test_session_management.py
class TestSessionManagement:
    """Test session management across providers."""

    def test_claude_stateful_session(self):
        """Claude maintains session state."""
        provider = ClaudeAgentProvider(config)
        session = provider.create_session(session_config)

        # Send multiple messages
        async for _ in provider.send_message("First"):
            pass
        async for _ in provider.send_message("Second"):
            pass

        # Claude SDK maintains history internally
        assert session.message_count == 2

    def test_openai_custom_session_state(self):
        """OpenAI provider maintains custom session state."""
        provider = OpenAIProvider(config)
        session = provider.create_session(session_config)

        # Send multiple messages
        async for _ in provider.send_message("First"):
            pass
        async for _ in provider.send_message("Second"):
            pass

        # Custom session maintains history
        assert len(session.history) == 2

    def test_session_timeout(self):
        """Sessions timeout after inactivity."""
        provider = OpenAIProvider(config)
        session = provider.create_session(session_config)

        # Session is active
        assert session.is_active is True

        # Simulate timeout (1 hour inactivity)
        session._last_activity = time.time() - 3601
        assert session.is_active is False
```

### Error Handling Tests

```python
# tests/integration/test_error_handling.py
class TestErrorHandling:
    """Test error handling consistency across providers."""

    def test_authentication_error_claude(self):
        """Claude raises AuthenticationError for invalid token."""
        config.anthropic_api_key = "invalid"
        provider = ClaudeAgentProvider(config)

        with pytest.raises(AuthenticationError):
            provider.create_session(session_config)

    def test_authentication_error_openai(self):
        """OpenAI raises AuthenticationError for invalid key."""
        config.openai_api_key = "invalid"
        provider = OpenAIProvider(config)

        with pytest.raises(AuthenticationError):
            provider.create_session(session_config)

    def test_rate_limit_error_translation(self):
        """Both providers translate rate limit errors."""
        # Mock 429 response
        with pytest.raises(RateLimitError):
            # Claude rate limit
            pass

        with pytest.raises(RateLimitError):
            # OpenAI rate limit
            pass

    def test_feature_not_supported_error(self):
        """OpenAI raises FeatureNotSupportedError for extended thinking."""
        provider = OpenAIProvider(config)

        with pytest.raises(FeatureNotSupportedError):
            provider.create_session(
                session_config,
                max_thinking_tokens=10000  # Not supported by OpenAI
            )
```

## Provider Comparison Tests

### Code Generation Comparison

**Purpose:** Validate that code generation is functionally equivalent across providers.

```python
# tests/provider_comparison/test_code_generation.py
class TestCodeGenerationComparison:
    """Compare code generation quality across providers."""

    @pytest.mark.parametrize("provider_name", ["claude", "openai"])
    def test_hello_world_generation(self, provider_name):
        """Both providers generate valid hello world function."""
        provider = create_provider(provider_name)

        task = "Write a Python hello_world function"
        response = provider.send_message(task)

        # Extract code from response
        code = extract_code(response)

        # Verify code is valid Python
        assert "def hello_world" in code
        assert "print" in code or "return" in code

        # Verify code executes
        exec(code)  # Should not raise

    @pytest.mark.parametrize("provider_name", ["claude", "openai"])
    def test_function_with_docstring(self, provider_name):
        """Both providers generate functions with docstrings."""
        provider = create_provider(provider_name)

        task = "Write a function to calculate factorial with docstring"
        response = provider.send_message(task)
        code = extract_code(response)

        # Verify docstring present
        assert '"""' in code or "'''" in code

        # Verify function works
        namespace = {}
        exec(code, namespace)
        assert namespace["factorial"](5) == 120

    def test_functional_equivalence(self):
        """Same task produces functionally equivalent code."""
        claude_provider = create_provider("claude")
        openai_provider = create_provider("openai")

        task = "Write a function to reverse a string"
        claude_code = extract_code(claude_provider.send_message(task))
        openai_code = extract_code(openai_provider.send_message(task))

        # Both should work correctly
        claude_namespace = {}
        exec(claude_code, claude_namespace)
        assert claude_namespace["reverse_string"]("hello") == "olleh"

        openai_namespace = {}
        exec(openai_code, openai_namespace)
        assert openai_namespace["reverse_string"]("hello") == "olleh"
```

### Tool Calling Comparison

```python
# tests/provider_comparison/test_tool_calling.py
class TestToolCallingComparison:
    """Compare tool calling behavior across providers."""

    @pytest.mark.parametrize("provider_name", ["claude", "openai"])
    def test_file_search_tool(self, provider_name):
        """Both providers use file search tool correctly."""
        provider = create_provider(provider_name)
        session = provider.create_session(session_config)

        # Request file search
        response = session.send_message("Find all Python files in src/")

        # Verify tool was called
        tool_calls = session.get_tool_calls()
        assert any(call["tool"] == "search_files" for call in tool_calls)

    def test_tool_execution_equivalence(self):
        """Same tool produces equivalent results."""
        claude_provider = create_provider("claude")
        openai_provider = create_provider("openai")

        # Execute bash command with both providers
        claude_session = claude_provider.create_session(session_config)
        claude_result = claude_session.execute_tool("bash", {"command": "echo hello"})

        openai_session = openai_provider.create_session(session_config)
        openai_result = openai_session.execute_tool("bash", {"command": "echo hello"})

        # Results should match
        assert claude_result["output"] == "hello\n"
        assert openai_result["output"] == "hello\n"
```

### Spec Creation Comparison

```python
# tests/provider_comparison/test_spec_creation.py
class TestSpecCreationComparison:
    """Compare spec creation quality across providers."""

    @pytest.mark.parametrize("provider_name", ["claude", "openai"])
    def test_spec_completeness(self, provider_name):
        """Both providers create complete specs."""
        provider = create_provider(provider_name)

        task = "Add user authentication feature"
        spec = provider.create_spec(task)

        # Verify required sections present
        assert "Overview" in spec
        assert "Task Scope" in spec
        assert "Services Involved" in spec
        assert "Success Criteria" in spec

    def test_spec_quality_metrics(self):
        """Compare spec quality metrics."""
        claude_provider = create_provider("claude")
        openai_provider = create_provider("openai")

        task = "Add database connection pooling"

        claude_spec = claude_provider.create_spec(task)
        openai_spec = openai_provider.create_spec(task)

        # Both should have similar section counts
        assert abs(count_sections(claude_spec) - count_sections(openai_spec)) <= 2

        # Both should identify services
        assert "backend" in claude_spec["Services Involved"]
        assert "backend" in openai_spec["Services Involved"]
```

### QA Review Comparison

```python
# tests/provider_comparison/test_qa_review.py
class TestQAReviewComparison:
    """Compare QA review effectiveness across providers."""

    @pytest.mark.parametrize("provider_name", ["claude", "openai"])
    def test_bug_detection(self, provider_name):
        """Both providers detect bugs in code."""
        provider = create_provider(provider_name)

        code = """
def divide(a, b):
    return a / b
"""

        bugs = provider.qa_review(code)

        # Both should detect division by zero risk
        assert any("division by zero" in bug.lower() for bug in bugs)

    def test_issue_detection_rate(self):
        """Compare issue detection rates."""
        code_with_bugs = """
def calculate(data):
    result = []
    for item in data:
        result.append(item * 2)
    # Missing return statement
"""

        claude_provider = create_provider("claude")
        openai_provider = create_provider("openai")

        claude_issues = claude_provider.qa_review(code_with_bugs)
        openai_issues = openai_provider.qa_review(code_with_bugs)

        # Both should detect issues
        assert len(claude_issues) > 0
        assert len(openai_issues) > 0

        # Detection rates should be similar (within 50%)
        assert abs(len(claude_issues) - len(openai_issues)) <= max(len(claude_issues), len(openai_issues)) * 0.5
```

## End-to-End Tests

### Full Spec Workflow Tests

```python
# tests/e2e/test_full_spec_workflow.py
class TestFullSpecWorkflow:
    """Test complete spec creation and implementation workflow."""

    @pytest.mark.parametrize("provider_name", ["claude", "openai"])
    def test_full_workflow(self, provider_name):
        """Complete workflow: spec → implementation → QA."""
        provider = create_provider(provider_name)

        # 1. Create spec
        task = "Add user authentication"
        spec = provider.create_spec(task)
        assert spec is not None

        # 2. Implement feature
        implementation = provider.implement_spec(spec)
        assert implementation["success"] is True

        # 3. QA review
        qa_result = provider.qa_review(implementation["code"])
        assert qa_result["passed"] is True

    def test_workflow_equivalence(self):
        """Same workflow produces equivalent results with different providers."""
        # Run workflow with Claude
        claude_result = run_full_workflow("claude", "Add login page")

        # Run workflow with OpenAI
        openai_result = run_full_workflow("openai", "Add login page")

        # Both should succeed
        assert claude_result["success"] is True
        assert openai_result["success"] is True

        # Both should implement same core features
        assert set(claude_result["features"]) == set(openai_result["features"])
```

### Provider Fallback Tests

```python
# tests/e2e/test_provider_fallback.py
class TestProviderFallback:
    """Test provider fallback mechanism."""

    def test_fallback_on_rate_limit(self):
        """Fallback to secondary provider on rate limit."""
        config = ProviderConfig.from_env()
        config.primary_provider = "claude"
        config.fallback_provider = "openai"
        config.enable_fallback = True

        router = ProviderRouter(config)

        # Simulate Claude rate limit
        with mock.patch.object(claude_provider, "send_message", side_effect=RateLimitError):
            response = router.send_message("Hello")

            # Should fallback to OpenAI
            assert router.current_provider == "openai"
            assert len(response) > 0

    def test_fallback_on_auth_error(self):
        """Fallback to secondary provider on auth error."""
        config = ProviderConfig.from_env()
        config.primary_provider = "openai"
        config.fallback_provider = "claude"
        config.enable_fallback = True

        router = ProviderRouter(config)

        # Simulate OpenAI auth error
        with mock.patch.object(openai_provider, "create_session", side_effect=AuthenticationError):
            session = router.create_session(session_config)

            # Should fallback to Claude
            assert router.current_provider == "claude"
            assert session.is_active is True
```

## Test Execution

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run unit tests only
pytest tests/unit/ -v

# Run specific provider tests
pytest tests/unit/providers/test_claude_provider.py -v

# Run integration tests
pytest tests/integration/ -v

# Run provider comparison tests
pytest tests/provider_comparison/ -v

# Run with coverage
pytest tests/ --cov=apps/backend/core/providers --cov-report=html

# Run specific test
pytest tests/unit/providers/test_claude_provider.py::TestClaudeProvider::test_provider_name -v
```

### Test Configuration

```python
# tests/conftest.py
import pytest
from core.providers import create_engine_provider
from core.providers.config import ProviderConfig

@pytest.fixture
def claude_config():
    """Claude provider config for testing."""
    return ProviderConfig(
        provider="claude",
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        claude_model="claude-sonnet-4-5-20250929"
    )

@pytest.fixture
def openai_config():
    """OpenAI provider config for testing."""
    return ProviderConfig(
        provider="openai",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model="gpt-4"
    )

@pytest.fixture
def session_config():
    """Default session config for testing."""
    return SessionConfig(
        name="test-session",
        system_prompt="You are a helpful assistant.",
        model="test-model",
        temperature=0.7
    )

def create_provider(provider_name: str) -> AIEngineProvider:
    """Helper to create provider for testing."""
    configs = {
        "claude": claude_config(),
        "openai": openai_config()
    }
    return create_engine_provider(configs[provider_name])
```

## Validation Criteria

### Success Metrics

**Unit Tests:**
- [ ] 90%+ code coverage for provider implementations
- [ ] All provider methods have unit tests
- [ ] Security wrapper fully covered
- [ ] Tool translator fully covered

**Integration Tests:**
- [ ] Provider switching works in both directions
- [ ] MCP integration works for all providers
- [ ] Security enforcement is equivalent
- [ ] Session management is consistent
- [ ] Error handling is uniform

**Provider Comparison Tests:**
- [ ] Code generation is functionally equivalent (90%+ pass rate)
- [ ] Tool calling produces equivalent results (95%+ match rate)
- [ ] Spec creation has similar completeness (section count variance ≤ 2)
- [ ] QA review detects similar issues (detection rate variance ≤ 50%)

**E2E Tests:**
- [ ] Full workflow completes successfully with all providers
- [ ] Provider fallback mechanism works correctly
- [ ] No regressions in existing Claude functionality

### Performance Benchmarks

**Response Time:**
- Claude: < 5s for simple tasks
- OpenAI: < 5s for simple tasks
- Variance between providers: < 50%

**Token Usage:**
- Code generation tasks: Within 2x variance
- Spec creation: Within 2x variance
- QA review: Within 2x variance

### Regression Testing

Before each release, run:

```bash
# Full test suite
pytest tests/ -v --cov

# Provider comparison suite
pytest tests/provider_comparison/ -v

# E2E workflow tests
pytest tests/e2e/ -v
```

## Continuous Integration

### CI Pipeline

```yaml
# .github/workflows/provider-tests.yml
name: Provider Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r apps/backend/requirements.txt
          pip install pytest pytest-cov
      - name: Run unit tests
        run: pytest tests/unit/ -v --cov

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - name: Run integration tests
        run: pytest tests/integration/ -v

  provider-comparison:
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests]
    steps:
      - name: Run provider comparison tests
        run: pytest tests/provider_comparison/ -v
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

## Troubleshooting

### Test Failures

**Issue:** Provider comparison test fails due to output variance

**Solution:**
- Tests should validate functional equivalence, not exact text match
- Use semantic comparison (e.g., code execution result, not code text)
- Increase tolerance thresholds for acceptable variance

**Issue:** Integration test fails due to MCP server unavailability

**Solution:**
- Mock MCP servers for integration tests
- Use test fixtures that provide fake MCP responses
- Skip MCP tests if servers are unavailable

**Issue:** E2E test fails due to timing issues

**Solution:**
- Add explicit waits for async operations
- Increase timeout values for slow providers
- Use retries for transient failures

### Missing Credentials

**Issue:** Tests fail due to missing API keys

**Solution:**
```bash
# Set credentials in test environment
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-proj-...

# Or use .env.test file
echo "ANTHROPIC_API_KEY=sk-ant-..." > apps/backend/.env.test
echo "OPENAI_API_KEY=sk-proj-..." >> apps/backend/.env.test
```

## Related Documentation

- [Provider Abstraction Layer](../architecture/provider-abstraction.md)
- [OpenAI Adapter Design](../architecture/openai-adapter-design.md)
- [Security Wrapper Design](../architecture/security-wrapper-design.md)
- [MCP Client Design](../architecture/mcp-client-design.md)
- [Implementation Phases](../roadmap/implementation-phases.md)

## Summary

The testing strategy validates provider interchangeability through:

✅ **Unit Tests** - Individual component testing (70% of tests)
✅ **Integration Tests** - Provider + MCP + Security integration (20% of tests)
✅ **Provider Comparison Tests** - Cross-provider equivalence validation (10% of tests)
✅ **E2E Tests** - Full workflow validation with provider switching

**Key Principles:**
1. Test functional equivalence, not exact text matching
2. Validate behavior consistency across providers
3. Ensure security parity for all providers
4. Use mocking for external dependencies (MCP servers)
5. Continuous integration to catch regressions early

**Success Criteria:**
- 90%+ code coverage for provider implementations
- 95%+ tool calling result match rate
- 50% or less variance in issue detection rates
- All providers pass full E2E workflow tests

---

**Document Version:** 1.0
**Last Updated:** 2025-02-16
**Maintainer:** Auto Code Core Team
