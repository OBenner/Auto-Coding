# MCP Protocol Client Design for OpenAI Provider

## Overview

This document describes the architecture and design of a **custom MCP (Model Context Protocol) client** for the OpenAI provider. Unlike the Claude SDK, which has built-in MCP server integration, OpenAI's SDK provides no native MCP support. This design outlines how to implement MCP protocol compatibility from scratch to enable OpenAI agents to use the same MCP servers (Context7, Linear, Graphiti, Electron, Puppeteer) as Claude agents.

**Scope:**
- MCP protocol client implementation for OpenAI provider
- Tool discovery and execution
- Response translation to OpenAI function calling format
- Connection management and error handling
- Security integration

**Out of Scope:**
- MCP server implementations (servers are external)
- Claude SDK's MCP client (already exists)
- General provider abstraction (covered in other design docs)

## Background: What is MCP?

**MCP (Model Context Protocol)** is a JSON-RPC 2.0-based protocol that enables AI models to interact with external tools and data sources through standardized server interfaces.

**Key Concepts:**

| Concept | Description |
|---------|-------------|
| **MCP Client** | Connects to MCP servers, issues tool calls, receives results (what we're building) |
| **MCP Server** | Exposes tools and resources to clients (Context7, Linear, Graphiti, etc.) |
| **Tool** | A function the model can call (e.g., `search_code`, `create_issue`) |
| **Resource** | Data the model can read (files, documentation, database records) |
| **JSON-RPC 2.0** | Underlying transport protocol (request/response via stdio/HTTP) |

**Why MCP Matters for OpenAI:**
- OpenAI models can't use Claude SDK's built-in MCP integration
- Without MCP, OpenAI agents lose access to:
  - **Context7**: Code documentation and examples
  - **Linear**: Issue tracking and progress updates
  - **Graphiti**: Long-term memory and context
  - **Electron**: E2E testing of desktop UI
  - **Puppeteer**: Browser automation

## Design Goals

1. **Protocol Compliance** - Implement JSON-RPC 2.0 and MCP spec correctly
2. **Compatibility** - Match Claude SDK's MCP behavior for tool execution
3. **Modularity** - Client is independent and testable without OpenAI SDK
4. **Extensibility** - Easy to add new MCP servers without code changes
5. **Security** - Integrate with Auto Code's security wrapper (command allowlisting, file permissions)
6. **Performance** - Connection pooling, concurrent requests, caching where appropriate
7. **Error Handling** - Graceful degradation when servers are unavailable

## Architecture Overview

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│                     OpenAI Agent Session                    │
│                  (using OpenAI Chat Completions API)        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Requests function call
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  OpenAI MCP Client (NEW)                    │
│                                                              │
│  Responsibilities:                                          │
│  - Connect to MCP servers (Context7, Linear, etc.)          │
│  - Discover available tools                                 │
│  - Execute tool calls                                       │
│  - Translate results to OpenAI format                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ JSON-RPC 2.0 over stdio/HTTP
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Context7    │ │    Linear    │ │   Graphiti   │
│  MCP Server  │ │  MCP Server  │ │  MCP Server  │
└──────────────┘ └──────────────┘ └──────────────┘
```

### Component Architecture

```
core/mcp/openai_client/
├── __init__.py
├── client.py              # MCPServerClient (main client)
├── connection.py          # Connection management (stdio/HTTP)
├── protocol.py            # JSON-RPC 2.0 protocol implementation
├── tools.py               # Tool discovery and execution
├── translation.py         # MCP ↔ OpenAI schema translation
└── exceptions.py          # MCP-specific exceptions
```

## MCP Protocol Implementation

### JSON-RPC 2.0 Basics

MCP uses JSON-RPC 2.0 for client-server communication:

**Request Format:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

**Response Format:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [...]
  }
}
```

**Error Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32601,
    "message": "Method not found",
    "data": {}
  }
}
```

### Supported MCP Methods

| Method | Purpose | Required |
|--------|---------|----------|
| `initialize` | Negotiate protocol version and capabilities | ✓ |
| `tools/list` | Get available tools from server | ✓ |
| `tools/call` | Execute a tool with arguments | ✓ |
| `resources/list` | Get available resources | Optional |
| `resources/read` | Read a resource's contents | Optional |
| `prompts/list` | Get available prompts | Optional |
| `prompts/get` | Get a prompt's contents | Optional |

## Client Design

### MCPServerClient Class

**Purpose:** Primary interface for connecting to a single MCP server and executing tool calls.

**Key Responsibilities:**
- Connection lifecycle (connect, disconnect, reconnect)
- Tool discovery and caching
- Tool execution with error handling
- Response translation to OpenAI format

**Conceptual Interface:**
```python
class MCPServerClient:
    """Client for a single MCP server.

    Manages connection, tool discovery, and tool execution for
    a single MCP server (e.g., Context7, Linear).

    Usage:
        client = MCPServerClient(
            server_name="context7",
            command="npx",
            args=["-y", "@context7/context7-mcp-server"]
        )

        await client.connect()

        # Discover tools
        tools = await client.list_tools()

        # Execute tool
        result = await client.call_tool(
            name="search_code",
            arguments={"query": "MCPClient"}
        )
    """

    def __init__(
        self,
        server_name: str,
        command: str,
        args: list[str],
        env: dict[str, str] | None = None,
        timeout: float = 30.0
    ):
        """Initialize MCP server client.

        Args:
            server_name: Human-readable name (e.g., "context7")
            command: Command to start server (e.g., "npx")
            args: Arguments to pass to command
            env: Environment variables for server process
            timeout: Request timeout in seconds
        """
        pass

    async def connect(self) -> None:
        """Start server process and initialize connection.

        Raises:
            MCPConnectionError: If server fails to start
            MCPInitializationError: If initialize handshake fails
        """
        pass

    async def disconnect(self) -> None:
        """Close connection and terminate server process."""
        pass

    async def list_tools(self) -> list[MCPTool]:
        """Get list of available tools from server.

        Returns:
            List of tool descriptors with name, description,
            and input schema

        Raises:
            MCPConnectionError: If server is unavailable
        """
        pass

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any]
    ) -> MCPToolResult:
        """Execute a tool and return result.

        Args:
            name: Tool name (must exist in list_tools())
            arguments: Tool input parameters (must match schema)

        Returns:
            Tool execution result with content and metadata

        Raises:
            MCPToolNotFoundError: If tool doesn't exist
            MCPToolExecutionError: If tool execution fails
            MCPValidationError: If arguments don't match schema
        """
        pass

    @property
    def is_connected(self) -> bool:
        """Check if client is connected to server."""
        pass
```

### Connection Management

**Connection Types:**

MCP servers communicate via two transport mechanisms:

| Transport | Description | Use Case | Status |
|-----------|-------------|----------|--------|
| **stdio** | Server reads JSON-RPC from stdin, writes to stdout | Most common (Context7, Linear, Graphiti) | **Phase 1** |
| **HTTP/SSE** | Server exposes HTTP endpoint with Server-Sent Events | Web-based servers | Phase 2 |

**stdio Connection Flow:**

```
Client spawns subprocess (e.g., `npx -y @context7/context7-mcp-server`)
    ↓
Client sends initialize request via stdin
    ↓
Server responds with capabilities via stdout
    ↓
Connection ready for tool calls
```

**Connection Pooling:**

```python
class MCPConnectionManager:
    """Manages connections to multiple MCP servers.

    Provides connection pooling, health checks, and automatic
    reconnection for reliable tool execution.

    Features:
    - Lazy connection initialization (connect on first use)
    - Connection health monitoring
    - Automatic reconnection with exponential backoff
    - Concurrent request handling
    """

    def __init__(self):
        self._clients: dict[str, MCPServerClient] = {}
        self._health_check_interval = 60.0  # seconds

    async def get_client(self, server_name: str) -> MCPServerClient:
        """Get or create client for server.

        Lazily initializes connections on first access.
        """
        pass

    async def health_check(self) -> dict[str, bool]:
        """Check health of all connected servers."""
        pass

    async def close_all(self) -> None:
        """Close all connections."""
        pass
```

### Tool Discovery

**Tool Schema:**

```python
@dataclass
class MCPTool:
    """Descriptor for an MCP tool."""

    name: str
    """Tool identifier (e.g., "search_code")"""

    description: str
    """Human-readable description of what the tool does"""

    input_schema: dict[str, Any]
    """JSON Schema for tool arguments (validation)"""

    is_deprecated: bool = False
    """Whether the tool is deprecated"""

    @property
    def to_openai_function(self) -> dict:
        """Convert to OpenAI function calling format.

        Returns:
            {
                "type": "function",
                "function": {
                    "name": self.name,
                    "description": self.description,
                    "parameters": self.input_schema
                }
            }
        """
        pass
```

**Discovery Process:**

1. Client connects to server
2. Sends `tools/list` request
3. Server responds with array of tool descriptors
4. Client caches tools locally (invalidated on reconnect)
5. Tools are translated to OpenAI function format for model

**Example Discovery Flow:**

```python
# Connect to Context7
client = MCPServerClient(
    server_name="context7",
    command="npx",
    args=["-y", "@context7/context7-mcp-server"]
)
await client.connect()

# Discover tools
tools = await client.list_tools()
# [
#   MCPTool(name="search_code", description="Search code...", ...),
#   MCPTool(name="get_docs", description="Get documentation...", ...),
#   ...
# ]

# Convert to OpenAI format
openai_functions = [tool.to_openai_function for tool in tools]
```

## Tool Execution

### Execution Flow

```
OpenAI Agent requests function call
    ↓
MCPServerClient.call_tool(name, arguments)
    ↓
1. Validate arguments against tool schema
    ↓
2. Apply security checks (command allowlist, file permissions)
    ↓
3. Send tools/call request via JSON-RPC
    ↓
4. Server executes tool
    ↓
5. Server returns result
    ↓
6. Translate result to OpenAI format
    ↓
7. Return to agent
```

### Request/Response Format

**tools/call Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "method": "tools/call",
  "params": {
    "name": "search_code",
    "arguments": {
      "query": "MCPClient",
      "file_pattern": "*.py"
    }
  }
}
```

**tools/call Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Found 3 matches in 2 files..."
      }
    ],
    "isError": false
  }
}
```

**Error Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "error": {
    "code": -32000,
    "message": "Tool execution failed",
    "data": {
      "error": "File not found: *.py"
    }
  }
}
```

### Result Translation

**MCP Result → OpenAI Function Result:**

```python
@dataclass
class MCPToolResult:
    """Result from MCP tool execution."""

    content: list[dict]
    """Tool output (text, images, data)"""

    is_error: bool
    """Whether execution failed"""

    meta: dict[str, Any] | None = None
    """Additional metadata from server"""

    def to_openai_tool_result(self) -> dict:
        """Convert to OpenAI tool result format.

        OpenAI expects:
        {
          "role": "tool",
          "tool_call_id": "...",
          "content": "result text"
        }
        """
        # Extract text content from MCP content array
        text_parts = [
            item["text"]
            for item in self.content
            if item["type"] == "text"
        ]
        combined_text = "\n".join(text_parts)

        return {
            "role": "tool",
          "content": combined_text
        }
```

## Response Translation

### MCP → OpenAI Schema Translation

MCP tools and OpenAI functions use different schemas. The translator handles bidirectional conversion.

**Schema Differences:**

| Aspect | MCP Tool | OpenAI Function |
|--------|----------|-----------------|
| **Name** | `name` (string) | `function.name` (string) |
| **Description** | `description` (string) | `function.description` (string) |
| **Parameters** | `inputSchema` (JSON Schema) | `function.parameters` (JSON Schema) |
| **Result** | `result.content[]` (array) | `content` (string) |

**Translation Layer:**

```python
class MCPToOpenAITranslator:
    """Translates between MCP and OpenAI formats.

    Responsibilities:
    - Convert MCP tool schemas to OpenAI function schemas
    - Convert OpenAI function calls to MCP tool calls
    - Convert MCP tool results to OpenAI tool results
    """

    def tool_to_function(self, mcp_tool: MCPTool) -> dict:
        """Convert MCP tool descriptor to OpenAI function format.

        Args:
            mcp_tool: MCP tool descriptor

        Returns:
            OpenAI function definition
        """
        return {
            "type": "function",
            "function": {
                "name": mcp_tool.name,
                "description": mcp_tool.description,
                "parameters": mcp_tool.input_schema
            }
        }

    def function_call_to_tool_call(
        self,
        function_call: dict
    ) -> tuple[str, dict]:
        """Convert OpenAI function call to MCP tool call format.

        Args:
            function_call: OpenAI function call from model

        Returns:
            Tuple of (tool_name, arguments)
        """
        function = function_call.get("function", {})
        return (
            function["name"],
            json.loads(function["arguments"])
        )

    def tool_result_to_function_result(
        self,
        mcp_result: MCPToolResult
    ) -> dict:
        """Convert MCP tool result to OpenAI tool result format.

        Args:
            mcp_result: MCP tool execution result

        Returns:
            OpenAI tool result message
        """
        return mcp_result.to_openai_tool_result()
```

## Integration with OpenAI Provider

### OpenAIProvider MCP Integration

**How OpenAI Agent Uses MCP:**

```python
class OpenAIProvider:
    """OpenAI provider with MCP support."""

    def __init__(self, config: ProviderConfig):
        self._mcp_manager = MCPConnectionManager()
        self._translator = MCPToOpenAITranslator()

    async def create_session(self, config: SessionConfig) -> OpenAISession:
        """Create agent session with MCP tools available."""

        # 1. Connect to MCP servers
        mcp_clients = await self._mcp_manager.initialize_servers(
            servers=config.mcp_servers
        )

        # 2. Discover tools from all servers
        all_tools = []
        for client in mcp_clients.values():
            tools = await client.list_tools()
            all_tools.extend(tools)

        # 3. Translate to OpenAI format
        openai_functions = [
            self._translator.tool_to_function(tool)
            for tool in all_tools
        ]

        # 4. Create session with tools
        session = OpenAISession(
            model=config.model,
            tools=openai_functions,
            mcp_clients=mcp_clients
        )

        return session
```

**OpenAI Session with MCP:**

```python
class OpenAISession:
    """OpenAI session with MCP tool execution."""

    async def complete(self, message: str) -> AsyncIterator[str]:
        """Stream response with tool calling support."""

        # 1. Send message with tools to OpenAI
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=self._messages,
            tools=self._tools  # MCP tools in OpenAI format
        )

        # 2. Check if model wants to call a tool
        if response.tool_calls:
            for tool_call in response.tool_calls:
                # 3. Translate to MCP format
                tool_name, arguments = self._translator.function_call_to_tool_call(
                    tool_call
                )

                # 4. Execute via MCP client
                mcp_result = await self._mcp_clients[server_name].call_tool(
                    name=tool_name,
                    arguments=arguments
                )

                # 5. Translate result back
                function_result = self._translator.tool_result_to_function_result(
                    mcp_result
                )

                # 6. Send result back to model
                self._messages.append(function_result)

            # 7. Get final response from model
            final_response = await self._client.chat.completions.create(
                model=self._model,
                messages=self._messages
            )

            async for chunk in final_response:
                yield chunk.choices[0].delta.content
        else:
            # No tool calls, just stream text
            async for chunk in response:
                yield chunk.choices[0].delta.content
```

## Security Considerations

### Security Integration

MCP tools execute with server permissions, which may be broader than Auto Code's security model allows. The security wrapper must intercept MCP tool calls.

**Security Wrapper for MCP:**

```python
class MCPSecurityWrapper:
    """Applies Auto Code security to MCP tool calls."""

    def __init__(
        self,
        mcp_client: MCPServerClient,
        security_config: SecurityConfig
    ):
        self._client = mcp_client
        self._security = security_config

    async def call_tool(
        self,
        name: str,
        arguments: dict
    ) -> MCPToolResult:
        """Execute tool with security checks."""

        # 1. Check if tool is allowed for this agent type
        if not self._security.is_tool_allowed(name):
            raise PermissionError(f"Tool {name} not allowed for this agent")

        # 2. Validate arguments against schema
        if not self._security.validate_tool_arguments(name, arguments):
            raise ValueError("Invalid tool arguments")

        # 3. Check file paths in arguments (if any)
        self._security.check_file_access(arguments)

        # 4. Check command execution (if tool runs commands)
        self._security.check_command_execution(name, arguments)

        # 5. Execute tool
        result = await self._client.call_tool(name, arguments)

        # 6. Sanitize result (remove sensitive data)
        return self._security.sanitize_result(result)
```

**Security Checks:**

| Check | Purpose | Example |
|-------|---------|---------|
| **Tool filtering** | Block dangerous tools based on agent type | QA agents can't use `git_push` |
| **File permissions** | Ensure file access stays within project | Reject paths outside working directory |
| **Command allowlisting** | Only allow commands from detected stack | Reject `rm -rf /`, allow `pytest` |
| **Argument validation** | Ensure arguments match schema | Reject malformed arguments |

## Configuration

### MCP Server Configuration

**Environment Variables:**

```bash
# Enable/disable specific MCP servers
CONTEXT7_ENABLED=true
LINEAR_MCP_ENABLED=true
GRAPHITI_ENABLED=true
ELECTRON_MCP_ENABLED=true
PUPPETEER_MCP_ENABLED=true

# Per-agent MCP tool overrides
AGENT_MCP_coder_ADD="context7,graphiti"
AGENT_MCP_qa_reviewer_REMOVE="linear"

# Custom MCP servers (JSON array)
CUSTOM_MCP_SERVERS='[
  {
    "name": "my-server",
    "command": "node",
    "args": ["./my-mcp-server.js"],
    "env": {"API_KEY": "xxx"}
  }
]'
```

**Programmatic Configuration:**

```python
@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""

    name: str
    """Server identifier (e.g., "context7")"""

    command: str
    """Command to start server (e.g., "npx")"""

    args: list[str]
    """Arguments to pass to command"""

    env: dict[str, str] | None = None
    """Environment variables for server process"""

    enabled: bool = True
    """Whether server is enabled"""

    timeout: float = 30.0
    """Request timeout in seconds"""
```

## Error Handling

### Exception Hierarchy

```python
class MCPError(Exception):
    """Base exception for MCP-related errors."""
    pass

class MCPConnectionError(MCPError):
    """Failed to connect to MCP server."""
    pass

class MCPInitializationError(MCPError):
    """Failed to initialize protocol handshake."""
    pass

class MCPToolNotFoundError(MCPError):
    """Requested tool not found on server."""
    pass

class MCPToolExecutionError(MCPError):
    """Tool execution failed on server."""
    pass

class MCPValidationError(MCPError):
    """Tool arguments failed schema validation."""
    pass

class MCPTimeoutError(MCPError):
    """Request timed out."""
    pass
```

### Error Handling Strategy

| Error Type | Handling Strategy |
|------------|-------------------|
| **Server not found** | Fail fast, log error, continue without server |
| **Connection timeout** | Retry 3 times with exponential backoff, then fail |
| **Tool execution failure** | Return error to model, let model decide retry |
| **Invalid arguments** | Validate before sending, fail fast with clear error |
| **Server crash** | Detect, log, attempt reconnect, mark unhealthy |
| **Network blip** | Retry transparently (idempotent tool calls only) |

**Graceful Degradation:**

```python
async def initialize_servers_with_fallback(
    servers: list[MCPServerConfig]
) -> dict[str, MCPServerClient]:
    """Initialize MCP servers with graceful failure.

    Non-critical servers (Linear) failing doesn't prevent
    the agent from running. Critical servers (Context7)
    failing may require user notification.
    """
    clients = {}
    for server_config in servers:
        try:
            client = MCPServerClient(
                server_name=server_config.name,
                command=server_config.command,
                args=server_config.args
            )
            await client.connect()
            clients[server_config.name] = client
            logger.info(f"Connected to MCP server: {server_config.name}")
        except MCPConnectionError as e:
            if server_config.name in CRITICAL_SERVERS:
                raise  # Fail if critical server unavailable
            else:
                logger.warning(f"Failed to connect to {server_config.name}: {e}")
                # Continue without this server
    return clients
```

## Implementation Phases

### Phase 1: Core MCP Client (Week 1-2)

**Deliverables:**
- [ ] JSON-RPC 2.0 protocol implementation
- [ ] stdio connection management
- [ ] `tools/list` and `tools/call` methods
- [ ] Basic error handling
- [ ] Unit tests for protocol layer

**Success Criteria:**
- Can connect to a simple MCP server
- Can list tools
- Can execute tools and get results

### Phase 2: OpenAI Integration (Week 2-3)

**Deliverables:**
- [ ] MCP → OpenAI schema translator
- [ ] Tool discovery and caching
- [ ] Integration with OpenAIProvider
- [ ] Session-level tool execution
- [ ] Integration tests with OpenAI API

**Success Criteria:**
- OpenAI agent can call MCP tools
- Tools execute correctly
- Results translate back to OpenAI format

### Phase 3: Security & Productionization (Week 3-4)

**Deliverables:**
- [ ] Security wrapper integration
- [ ] Connection pooling and health checks
- [ ] Graceful degradation
- [ ] Error recovery and retries
- [ ] Logging and monitoring
- [ ] End-to-end tests

**Success Criteria:**
- Security checks applied to all tool calls
- System handles server failures gracefully
- Full test coverage

## Testing Strategy

### Unit Tests

**Protocol Layer:**
```python
async def test_json_rpc_request():
    """Test JSON-RPC request formatting."""
    request = JSONRPCRequest(
        id=1,
        method="tools/list",
        params={}
    )
    assert request.to_dict() == {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }

async def test_tool_schema_translation():
    """Test MCP → OpenAI schema translation."""
    mcp_tool = MCPTool(
        name="search_code",
        description="Search code",
        input_schema={"type": "object"}
    )
    translator = MCPToOpenAITranslator()
    openai_func = translator.tool_to_function(mcp_tool)
    assert openai_func["type"] == "function"
    assert openai_func["function"]["name"] == "search_code"
```

### Integration Tests

**Mock MCP Server:**
```python
async def test_tool_execution():
    """Test tool execution against mock server."""
    # Start mock MCP server
    server = MockMCPServer()
    await server.start()

    # Connect client
    client = MCPServerClient(
        server_name="test",
        command="node",
        args=["./mock-server.js"]
    )
    await client.connect()

    # List tools
    tools = await client.list_tools()
    assert len(tools) > 0

    # Execute tool
    result = await client.call_tool(
        name="echo",
        arguments={"message": "hello"}
    )
    assert result.content[0]["text"] == "hello"

    await server.stop()
```

### End-to-End Tests

**OpenAI Agent with MCP:**
```python
async def test_openai_agent_with_context7():
    """Test OpenAI agent using Context7 MCP server."""
    provider = OpenAIProvider(config)

    session = await provider.create_session(
        SessionConfig(
            model="gpt-5.2",
            mcp_servers=["context7"]
        )
    )

    response = await session.complete(
        "Search for documentation about MCP protocol"
    )

    # Verify agent used Context7 tool
    assert "MCP" in response or "protocol" in response
```

## Performance Considerations

### Optimization Strategies

| Area | Optimization | Impact |
|------|-------------|--------|
| **Connection startup** | Lazy initialization (connect on first tool call) | Faster agent startup |
| **Tool discovery** | Cache tool schemas after first discovery | Avoid redundant list_tools calls |
| **Concurrent requests** | Allow parallel tool execution to different servers | Faster multi-tool workflows |
| **Connection pooling** | Reuse connections across sessions | Reduce overhead |
| **Result streaming** | Stream large results instead of buffering | Lower memory usage |

### Benchmarks (Target)

| Metric | Target |
|--------|--------|
| Connection establishment | < 2 seconds |
| Tool discovery | < 500ms (cached) |
| Tool execution | < 5 seconds (p95) |
| Concurrent tool calls | Support 10+ parallel |

## Compatibility Matrix

### MCP Server Support

| MCP Server | stdio | HTTP | Priority | Phase |
|------------|-------|------|----------|-------|
| **Context7** | ✓ | ✗ | **Critical** | 1 |
| **Graphiti** | ✓ | ✗ | **Critical** | 1 |
| **Linear** | ✓ | ✗ | Optional | 2 |
| **Electron** | ✗ | ✓ (SSE) | Optional | 2 |
| **Puppeteer** | ✗ | ✓ (SSE) | Optional | 3 |

**Implementation Priority:**
1. **Phase 1**: Context7, Graphiti (most critical for agent performance)
2. **Phase 2**: Linear, Electron (nice-to-have integrations)
3. **Phase 3**: Puppeteer, custom servers (extensibility)

## Future Enhancements

### Potential Improvements

| Enhancement | Benefit | Effort |
|-------------|---------|--------|
| **HTTP/SSE transport** | Support web-based MCP servers | Medium |
| **Resource support** | Enable reading files/docs via MCP | Low |
| **Prompt support** | Use MCP-provided prompts | Low |
| **Tool streaming** | Stream tool results incrementally | Medium |
| **Tool composition** | Chain multiple tools together | High |
| **Caching layer** | Cache tool results for idempotent tools | Medium |

### Migration Path

**When Claude SDK adds MCP features:**
- Our custom client can adopt new features incrementally
- No breaking changes to OpenAIProvider interface
- Can potentially share code with Claude SDK's client (if open-sourced)

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| **MCP protocol changes** | Medium | Version detection, backward compatibility |
| **Server incompatibility** | Medium | Test against all supported servers |
| **Performance overhead** | Low | Lazy connections, caching, pooling |
| **Security vulnerabilities** | High | Security wrapper, audit tool permissions |
| **Maintenance burden** | Medium | Comprehensive tests, clear documentation |

## References

### Specifications

- [MCP Protocol Spec](https://modelcontextprotocol.io/)
- [JSON-RPC 2.0 Spec](https://www.jsonrpc.org/specification)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)

### Existing Implementations

- Claude SDK's MCP client (internal reference)
- [Context7 MCP Server](https://github.com/context7/context7-mcp-server)
- [Official MCP SDK (TypeScript)](https://github.com/modelcontextprotocol/typescript-sdk)

## Appendix: Example MCP Server Configurations

### Context7

```json
{
  "name": "context7",
  "command": "npx",
  "args": ["-y", "@context7/context7-mcp-server"],
  "env": {
    "CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}"
  }
}
```

### Linear

```json
{
  "name": "linear",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-linear"],
  "env": {
    "LINEAR_API_KEY": "${LINEAR_API_KEY}"
  }
}
```

### Graphiti

```json
{
  "name": "graphiti",
  "command": "python",
  "args": ["-m", "integrations.graphiti.mcp_server"],
  "env": {
    "GRAPHITI_ENABLED": "true"
  }
}
```

---

**Document Status**: Design Complete
**Next Step**: Implementation (Phase 1: Core MCP Client)
**Owner**: Backend Team
**Reviewers**: Architecture Team, Security Team
