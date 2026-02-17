# Tool Calling Compatibility Analysis

This document analyzes the differences between Claude SDK tool calling and OpenAI function calling, and provides a design for bidirectional translation to enable provider interchangeability.

## Overview

**Tool calling** (Claude) and **function calling** (OpenAI) serve the same purpose: allowing AI models to invoke external tools/functions during conversations. However, they use different schemas, protocols, and response formats that must be translated to support both providers interchangeably.

**Key differences:**
- **Schema format**: Claude uses `input_schema` (JSON Schema), OpenAI uses `parameters` (JSON Schema Draft 4)
- **Response structure**: Claude returns `tool_use` blocks, OpenAI returns `tool_calls` arrays
- **Tool identification**: Claude uses string names, OpenAI uses function objects with names
- **Argument passing**: Claude uses `input` object, OpenAI uses `arguments` JSON string
- **Parallel execution**: Claude supports native parallel tools, OpenAI requires explicit array handling

## Architecture

The translation layer sits between the provider abstraction and the underlying SDK:

```
┌─────────────────────────────────────────────────────────────┐
│                  Provider Abstraction Layer                  │
│              (AIEngineProvider interface)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ uses tools in unified format
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Tool Schema Translator (NEW)                    │
│                                                              │
│  - claude_to_openai()  - Claude → OpenAI format             │
│  - openai_to_claude()  - OpenAI → Claude format             │
│  - normalize_tool()    - Convert to unified intermediate    │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌─────────────────────┐         ┌─────────────────────┐
│   Claude Provider   │         │   OpenAI Provider   │
│                     │         │                     │
│  - Claude tools     │         │  - Function calls   │
│  - input_schema     │         │  - parameters       │
│  - tool_use blocks  │         │  - tool_calls       │
└─────────────────────┘         └─────────────────────┘
```

## Schema Format Comparison

### Claude Tool Schema

Claude SDK defines tools using a **simplified JSON Schema** format:

```python
# Claude tool definition
claude_tool = {
    "name": "search_files",
    "description": "Search for files matching a pattern",
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "File pattern to search for (e.g., '*.py')"
            },
            "path": {
                "type": "string",
                "description": "Directory to search in"
            }
        },
        "required": ["pattern"]
    }
}
```

**Key characteristics:**
- **Flat structure**: Tool definition at top level
- **`input_schema`**: JSON Schema Draft 2020-12 compatible
- **`description`**: Top-level field for tool description
- **`properties`**: Direct child of `input_schema`
- **No `function` wrapper**: Schema is not nested in a function object

### OpenAI Function Schema

OpenAI API defines functions using a **nested JSON Schema** format:

```python
# OpenAI function definition
openai_function = {
    "type": "function",
    "function": {
        "name": "search_files",
        "description": "Search for files matching a pattern",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "File pattern to search for (e.g., '*.py')"
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in"
                }
            },
            "required": ["pattern"]
        }
    }
}
```

**Key characteristics:**
- **Nested structure**: Function definition wrapped in `function` object
- **`type: "function"`**: Required discriminator field
- **`parameters`**: JSON Schema Draft 4 compatible (subset of Claude's schema)
- **`function.name`**: Nested inside function object
- **`function.description`**: Nested inside function object

## Schema Format Differences

| Aspect | Claude SDK | OpenAI API | Compatibility |
|--------|-----------|------------|---------------|
| **Schema location** | `input_schema` | `function.parameters` | **Translation needed** |
| **JSON Schema version** | Draft 2020-12 | Draft 4 | **Subset compatible** |
| **Top-level wrapper** | None | `{"type": "function", "function": {...}}` | **Add/remove wrapper** |
| **Required properties** | `input_schema.required` | `parameters.required` | **Direct mapping** |
| **Description location** | Tool level | Function level | **Direct mapping** |
| **Property types** | Full JSON Schema | JSON Schema Draft 4 subset | **Filter unsupported types** |
| **Enum support** | ✓ | ✓ | **Direct mapping** |
| **Array items** | Full schema | Simple types only | **May need simplification** |
| **Nested objects** | ✓ | ✓ | **Direct mapping** |
| **OneOf/AnyOf/AllOf** | ✓ | Limited support | **Test compatibility** |
| **Format validation** | ✓ | Limited | **Remove format constraints** |
| **Default values** | ✓ | ✗ | **Remove defaults** |
| **Examples** | ✓ | ✗ | **Remove examples** |

## Response Format Comparison

### Claude Tool Use Response

Claude SDK returns tool calls as `tool_use` content blocks:

```python
# Claude response with tool use
claude_response = {
    "id": "msg_12345",
    "role": "assistant",
    "content": [
        {
            "type": "tool_use",
            "id": "toolu_12345",
            "name": "search_files",
            "input": {
                "pattern": "*.py",
                "path": "/src"
            }
        }
    ]
}
```

**Key characteristics:**
- **Array of blocks**: `content` is an array of content blocks
- **`type: "tool_use"`**: Discriminator for tool use blocks
- **`id`**: Unique identifier for this tool use
- **`name`**: Tool name to invoke
- **`input`**: Arguments as object (not JSON string)

### OpenAI Tool Call Response

OpenAI API returns tool calls in a `tool_calls` array:

```python
# OpenAI response with tool call
openai_response = {
    "id": "chatcmpl-12345",
    "object": "chat.completion",
    "choices": [{
        "message": {
            "role": "assistant",
            "tool_calls": [{
                "id": "call_12345",
                "type": "function",
                "function": {
                    "name": "search_files",
                    "arguments": '{"pattern": "*.py", "path": "/src"}'
                }
            }]
        }
    }]
}
```

**Key characteristics:**
- **`tool_calls` array**: Separate from `content`
- **`type: "function"`**: Discriminator for function calls
- **`id`**: Unique identifier for this tool call
- **`function.name`**: Nested inside function object
- **`function.arguments`**: JSON string (not object)

## Response Format Differences

| Aspect | Claude SDK | OpenAI API | Translation Strategy |
|--------|-----------|------------|---------------------|
| **Location** | `content[]` array | `tool_calls[]` array | **Move to/from array** |
| **Type discriminator** | `type: "tool_use"` | `type: "function"` | **Map type values** |
| **Tool ID** | `id` (string) | `id` (string) | **Direct mapping** |
| **Tool name** | `name` (top-level) | `function.name` | **Nest/unnest name** |
| **Arguments** | `input` (object) | `function.arguments` (JSON string) | **Parse/stringify JSON** |
| **Parallel calls** | Multiple content blocks | Multiple tool_calls items | **Array iteration** |
| **Text + tools** | Mixed content array | Separate content + tool_calls | **Split/join content** |

## Bidirectional Translation Design

### Translator Architecture

```python
# Conceptual translator (not implementation)

class ToolSchemaTranslator:
    """Translates tool schemas between Claude and OpenAI formats."""

    def claude_to_openai(self, claude_tool: dict) -> dict:
        """Convert Claude tool schema to OpenAI function calling format.

        Args:
            claude_tool: Claude tool definition with input_schema

        Returns:
            OpenAI function definition with parameters

        Example:
            >>> claude_tool = {
            ...     "name": "search",
            ...     "description": "Search files",
            ...     "input_schema": {...}
            ... }
            >>> translator.claude_to_openai(claude_tool)
            {
                "type": "function",
                "function": {
                    "name": "search",
                    "description": "Search files",
                    "parameters": {...}
                }
            }
        """
        return {
            "type": "function",
            "function": {
                "name": claude_tool["name"],
                "description": claude_tool["description"],
                "parameters": self._translate_schema_to_openai(
                    claude_tool["input_schema"]
                )
            }
        }

    def openai_to_claude(self, openai_function: dict) -> dict:
        """Convert OpenAI function calling to Claude tool format.

        Args:
            openai_function: OpenAI function definition

        Returns:
            Claude tool definition with input_schema

        Example:
            >>> openai_func = {
            ...     "type": "function",
            ...     "function": {...}
            ... }
            >>> translator.openai_to_claude(openai_func)
            {
                "name": "search",
                "description": "Search files",
                "input_schema": {...}
            }
        """
        func = openai_function["function"]
        return {
            "name": func["name"],
            "description": func["description"],
            "input_schema": self._translate_schema_to_claude(
                func["parameters"]
            )
        }

    def _translate_schema_to_openai(self, claude_schema: dict) -> dict:
        """Translate Claude JSON Schema to OpenAI-compatible format.

        Removes OpenAI-unsupported features:
        - default values
        - examples
        - format constraints (beyond basic types)
        - complex oneOf/anyOf/allOf
        """
        openai_schema = {
            "type": claude_schema.get("type", "object"),
            "properties": {}
        }

        # Copy properties with filtering
        for prop_name, prop_def in claude_schema.get("properties", {}).items():
            openai_schema["properties"][prop_name] = self._filter_openai_props(prop_def)

        # Copy required array
        if "required" in claude_schema:
            openai_schema["required"] = claude_schema["required"]

        return openai_schema

    def _translate_schema_to_claude(self, openai_schema: dict) -> dict:
        """Translate OpenAI JSON Schema to Claude format.

        OpenAI schemas are already Claude-compatible (subset),
        so this is mostly a pass-through.
        """
        # OpenAI Draft 4 is subset of Claude's Draft 2020-12
        return openai_schema.copy()

    def _filter_openai_props(self, prop_def: dict) -> dict:
        """Filter property definition to OpenAI-compatible subset.

        Removes:
        - default
        - examples
        - format (except for known types)
        - complex validation keywords
        """
        filtered = {}

        # Copy basic type fields
        if "type" in prop_def:
            filtered["type"] = prop_def["type"]
        if "description" in prop_def:
            filtered["description"] = prop_def["description"]
        if "enum" in prop_def:
            filtered["enum"] = prop_def["enum"]

        # Recursively handle nested objects
        if prop_def.get("type") == "object" and "properties" in prop_def:
            filtered["properties"] = {
                k: self._filter_openai_props(v)
                for k, v in prop_def["properties"].items()
            }
            if "required" in prop_def:
                filtered["required"] = prop_def["required"]

        # Handle arrays (simplify for OpenAI)
        if prop_def.get("type") == "array" and "items" in prop_def:
            items = prop_def["items"]
            if isinstance(items, dict):
                # OpenAI only supports simple item schemas
                filtered["items"] = self._filter_openai_props(items)

        return filtered

    def translate_response_claude_to_openai(self, claude_response: dict) -> dict:
        """Translate Claude response with tool_use to OpenAI format.

        Args:
            claude_response: Claude response with content blocks

        Returns:
            OpenAI-formatted response with tool_calls
        """
        tool_calls = []

        for block in claude_response.get("content", []):
            if block.get("type") == "tool_use":
                tool_calls.append({
                    "id": block["id"],
                    "type": "function",
                    "function": {
                        "name": block["name"],
                        "arguments": json.dumps(block["input"])
                    }
                })

        return {
            "id": claude_response.get("id"),
            "choices": [{
                "message": {
                    "role": "assistant",
                    "tool_calls": tool_calls
                }
            }]
        }

    def translate_response_openai_to_claude(self, openai_response: dict) -> dict:
        """Translate OpenAI response with tool_calls to Claude format.

        Args:
            openai_response: OpenAI response with tool_calls array

        Returns:
            Claude-formatted response with content blocks
        """
        content_blocks = []

        for tool_call in openai_response.get("choices", [{}])[0] \
                .get("message", {}) \
                .get("tool_calls", []):
            if tool_call.get("type") == "function":
                content_blocks.append({
                    "type": "tool_use",
                    "id": tool_call["id"],
                    "name": tool_call["function"]["name"],
                    "input": json.loads(tool_call["function"]["arguments"])
                })

        return {
            "id": openai_response.get("id"),
            "role": "assistant",
            "content": content_blocks
        }
```

## Translation Examples

### Example 1: Simple Tool

**Claude format:**
```python
{
    "name": "get_weather",
    "description": "Get current weather for a location",
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City name or zip code"
            },
            "unit": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "description": "Temperature unit"
            }
        },
        "required": ["location"]
    }
}
```

**→ OpenAI format:**
```python
{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or zip code"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Temperature unit"
                }
            },
            "required": ["location"]
        }
    }
}
```

### Example 2: Complex Nested Schema

**Claude format:**
```python
{
    "name": "create_file",
    "description": "Create a file with content",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path"
            },
            "content": {
                "type": "string",
                "description": "File content"
            },
            "options": {
                "type": "object",
                "description": "File creation options",
                "properties": {
                    "overwrite": {
                        "type": "boolean",
                        "default": false
                    },
                    "encoding": {
                        "type": "string",
                        "default": "utf-8"
                    }
                }
            }
        },
        "required": ["path", "content"]
    }
}
```

**→ OpenAI format (defaults removed):**
```python
{
    "type": "function",
    "function": {
        "name": "create_file",
        "description": "Create a file with content",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path"
                },
                "content": {
                    "type": "string",
                    "description": "File content"
                },
                "options": {
                    "type": "object",
                    "description": "File creation options",
                    "properties": {
                        "overwrite": {
                            "type": "boolean"
                        },
                        "encoding": {
                            "type": "string"
                        }
                    }
                }
            },
            "required": ["path", "content"]
        }
    }
}
```

### Example 3: Response Translation

**Claude response:**
```python
{
    "id": "msg_abc123",
    "role": "assistant",
    "content": [
        {
            "type": "text",
            "text": "I'll search for Python files."
        },
        {
            "type": "tool_use",
            "id": "toolu_xyz789",
            "name": "search_files",
            "input": {
                "pattern": "*.py",
                "path": "/src"
            }
        }
    ]
}
```

**→ OpenAI response:**
```python
{
    "id": "msg_abc123",
    "choices": [{
        "message": {
            "role": "assistant",
            "content": "I'll search for Python files.",
            "tool_calls": [{
                "id": "toolu_xyz789",
                "type": "function",
                "function": {
                    "name": "search_files",
                    "arguments": '{"pattern": "*.py", "path": "/src"}'
                }
            }]
        }
    }]
}
```

## Compatibility Matrix

### Fully Compatible Features

| Feature | Claude | OpenAI | Translation |
|---------|--------|--------|-------------|
| String parameters | ✓ | ✓ | Direct |
| Numeric parameters | ✓ | ✓ | Direct |
| Boolean parameters | ✓ | ✓ | Direct |
| Object parameters | ✓ | ✓ | Direct |
| Array parameters | ✓ | ✓ | Direct (with simplification) |
| Enum constraints | ✓ | ✓ | Direct |
| Required fields | ✓ | ✓ | Direct |
| Descriptions | ✓ | ✓ | Direct |
| Nested objects | ✓ | ✓ | Direct |
| Multiple tools | ✓ | ✓ | Direct |
| Parallel execution | ✓ | ✓ | Direct |

### Requires Translation

| Feature | Claude | OpenAI | Translation Strategy |
|---------|--------|--------|---------------------|
| Tool schema location | `input_schema` | `function.parameters` | Move to nested location |
| Function wrapper | None | `{"type": "function"...}` | Add/remove wrapper |
| Response location | `content[]` | `tool_calls[]` | Separate/join arrays |
| Arguments format | Object | JSON string | Parse/stringify |
| Default values | ✓ | ✗ | Remove (Claude→OpenAI) |
| Examples | ✓ | ✗ | Remove (Claude→OpenAI) |
| Format validation | ✓ | Limited | Remove unsupported formats |

### Not Compatible

| Feature | Claude | OpenAI | Mitigation |
|---------|--------|--------|------------|
| OneOf/AnyOf/AllOf | ✓ | Limited | Test per-provider, remove if unsupported |
| Complex validation | ✓ | Limited | Simplify to basic types |
| Extended thinking | ✓ | ✗ | Fallback to prompt engineering |
| Tool permissions | ✓ | ✗ | Implement custom layer |
| Pre/post hooks | ✓ | ✗ | Implement wrapper layer |

## Implementation Strategy

### Phase 1: Schema Translation (High Priority)

Implement `ToolSchemaTranslator` class with:

1. **`claude_to_openai()`** - Convert Claude tools to OpenAI functions
2. **`openai_to_claude()`** - Convert OpenAI functions to Claude tools
3. **`_filter_openai_props()`** - Remove unsupported features

**Validation:**
- Test with real Auto Code tools (Bash, Read, Write, Grep, etc.)
- Verify schema validation passes for both providers
- Check that translations are reversible (round-trip)

### Phase 2: Response Translation (High Priority)

Implement response format conversion:

1. **`translate_response_claude_to_openai()`** - Convert tool_use to tool_calls
2. **`translate_response_openai_to_claude()`** - Convert tool_calls to tool_use
3. **Handle mixed content** - Text + tools in same response

**Validation:**
- Test parallel tool execution
- Verify argument parsing/stringifying preserves data
- Check ID mapping for tool responses

### Phase 3: Provider Integration (High Priority)

Integrate translator into provider adapters:

1. **ClaudeAdapter** - Use Claude format natively (no translation)
2. **OpenAIAdapter** - Translate on tool registration and response handling
3. **Unified interface** - `AIEngineProvider` uses neutral format

**Implementation:**
```python
# In OpenAIAdapter
class OpenAIAdapter(AIEngineProvider):
    def __init__(self, config: ProviderConfig):
        self._translator = ToolSchemaTranslator()

    def register_tools(self, tools: list[dict]) -> None:
        """Register tools (unified format → OpenAI format)."""
        openai_tools = [
            self._translator.claude_to_openai(tool)
            for tool in tools
        ]
        self._client.tools = openai_tools

    async def send_message(self, message: str) -> AsyncIterator[str]:
        """Send message and translate responses."""
        response = await self._client.chat(message)

        # Translate tool_calls to tool_use blocks
        if "tool_calls" in response:
            response = self._translator.translate_response_openai_to_claude(response)

        yield from self._stream_response(response)
```

### Phase 4: Testing (Medium Priority)

Create comprehensive test suite:

1. **Schema translation tests** - Verify round-trip conversion
2. **Response translation tests** - Check tool call preservation
3. **Integration tests** - End-to-end tool execution with both providers
4. **Edge case tests** - Complex schemas, parallel calls, error handling

### Phase 5: Documentation (Low Priority)

Document translation behavior:

1. **Translation rules** - What gets converted and how
2. **Limitations** - Features that don't translate
3. **Best practices** - Writing provider-agnostic tool schemas
4. **Troubleshooting** - Common translation issues

## Edge Cases and Considerations

### 1. Default Values

**Problem:** OpenAI doesn't support `default` in schema, Claude does.

**Strategy:**
- **Claude → OpenAI**: Remove `default` values from schema
- **OpenAI → Claude**: Add default values in tool implementation layer
- **Best practice**: Don't rely on schema defaults for business logic

**Example:**
```python
# Claude (with default)
{
    "properties": {
        "encoding": {
            "type": "string",
            "default": "utf-8"
        }
    }
}

# OpenAI (default removed)
{
    "properties": {
        "encoding": {
            "type": "string"
        }
    }
}

# Handle default in tool implementation
def read_file(path: str, encoding: str = "utf-8") -> str:
    # Default handled here, not in schema
    ...
```

### 2. Format Validation

**Problem:** OpenAI has limited `format` support, Claude supports full JSON Schema formats.

**Strategy:**
- **Claude → OpenAI**: Remove unsupported format constraints (email, uri, date-time, etc.)
- **OpenAI → Claude**: Add formats if needed (not required)
- **Best practice**: Validate formats in tool implementation, not schema

**Unsupported formats to remove:**
- `format: "email"`
- `format: "uri"`
- `format: "date-time"`
- `format: "uuid"`
- `format: "binary"`

**Supported formats to keep:**
- `format: "date"`
- `format: "time"`

### 3. Complex Array Items

**Problem:** OpenAI only supports simple array item schemas.

**Strategy:**
- **Claude → OpenAI**: Simplify complex item schemas to basic types
- **OpenAI → Claude**: Keep simple schemas (already compatible)
- **Best practice**: Use object properties instead of complex arrays

**Example:**
```python
# Claude (complex items)
{
    "type": "array",
    "items": {
        "oneOf": [
            {"type": "string"},
            {"type": "number"}
        ]
    }
}

# OpenAI (simplified to string)
{
    "type": "array",
    "items": {
        "type": "string"
    }
}

# Handle validation in tool implementation
def process_items(items: list) -> None:
    for item in items:
        if not isinstance(item, (str, int, float)):
            raise ValueError(f"Invalid item type: {type(item)}")
```

### 4. Parallel Tool Execution

**Problem:** Both providers support parallel calls, but with different syntax.

**Strategy:**
- Maintain parallel execution semantics at abstraction layer
- Translate array formats correctly
- Preserve tool call IDs for response matching

**Claude parallel:**
```python
"content": [
    {"type": "tool_use", "id": "1", "name": "search", "input": {...}},
    {"type": "tool_use", "id": "2", "name": "read", "input": {...}}
]
```

**OpenAI parallel:**
```python
"tool_calls": [
    {"id": "1", "function": {"name": "search", "arguments": "{...}"}},
    {"id": "2", "function": {"name": "read", "arguments": "{...}"}}
]
```

### 5. Mixed Text and Tool Content

**Problem:** Claude mixes text and tools in `content` array, OpenAI separates them.

**Strategy:**
- **Claude → OpenAI**: Split content array into `content` string + `tool_calls` array
- **OpenAI → Claude**: Join `content` string + `tool_calls` into unified `content` array
- Preserve ordering of text and tool calls

**Example:**
```python
# Claude (mixed)
{
    "content": [
        {"type": "text", "text": "Searching..."},
        {"type": "tool_use", "name": "search", "input": {...}},
        {"type": "text", "text": "Done."}
    ]
}

# OpenAI (separated)
{
    "content": "Searching...\n\nDone.",
    "tool_calls": [
        {"function": {"name": "search", "arguments": "{...}"}}
    ]
}
```

## Testing Strategy

### Unit Tests

```python
# test_tool_translator.py

def test_claude_to_openai_simple_tool():
    """Test translation of simple tool schema."""
    claude_tool = {
        "name": "test",
        "description": "Test tool",
        "input_schema": {
            "type": "object",
            "properties": {
                "arg": {"type": "string"}
            }
        }
    }

    openai_func = translator.claude_to_openai(claude_tool)

    assert openai_func["type"] == "function"
    assert openai_func["function"]["name"] == "test"
    assert "parameters" in openai_func["function"]
    assert openai_func["function"]["parameters"]["properties"]["arg"]["type"] == "string"

def test_openai_to_claude_simple_tool():
    """Test reverse translation."""
    openai_func = {
        "type": "function",
        "function": {
            "name": "test",
            "description": "Test tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "arg": {"type": "string"}
                }
            }
        }
    }

    claude_tool = translator.openai_to_claude(openai_func)

    assert claude_tool["name"] == "test"
    assert "input_schema" in claude_tool
    assert claude_tool["input_schema"]["properties"]["arg"]["type"] == "string"

def test_roundtrip_translation():
    """Test that translation is reversible."""
    original = {
        "name": "test",
        "description": "Test",
        "input_schema": {
            "type": "object",
            "properties": {
                "str": {"type": "string"},
                "num": {"type": "number"},
                "bool": {"type": "boolean"}
            },
            "required": ["str"]
        }
    }

    # Claude → OpenAI → Claude
    openai = translator.claude_to_openai(original)
    back_to_claude = translator.openai_to_claude(openai)

    assert back_to_claude["name"] == original["name"]
    assert back_to_claude["input_schema"]["properties"]["str"]["type"] == "string"
    assert "required" in back_to_claude["input_schema"]

def test_default_value_removal():
    """Test that default values are removed for OpenAI."""
    claude_tool = {
        "name": "test",
        "input_schema": {
            "type": "object",
            "properties": {
                "arg": {
                    "type": "string",
                    "default": "value"
                }
            }
        }
    }

    openai_func = translator.claude_to_openai(claude_tool)

    # Default should be removed
    assert "default" not in openai_func["function"]["parameters"]["properties"]["arg"]

def test_response_translation():
    """Test response format conversion."""
    claude_resp = {
        "id": "msg123",
        "content": [
            {
                "type": "tool_use",
                "id": "tool1",
                "name": "search",
                "input": {"pattern": "*.py"}
            }
        ]
    }

    openai_resp = translator.translate_response_claude_to_openai(claude_resp)

    assert "tool_calls" in openai_resp["choices"][0]["message"]
    assert openai_resp["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "search"
    assert json.loads(openai_resp["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"]) == {"pattern": "*.py"}
```

### Integration Tests

```python
# test_provider_tools.py

async def test_openai_tool_execution():
    """Test that tools work with OpenAI provider."""
    provider = OpenAIAdapter(config)

    # Register tool in Claude format (should be translated)
    tools = [{
        "name": "echo",
        "description": "Echo input",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string"}
            },
            "required": ["message"]
        }
    }]

    session = provider.create_session(SessionConfig(tools=tools))

    # Send message that should trigger tool
    response = await session.send_message("Say hello")

    # Verify tool was called correctly
    assert "tool_calls" in response or "tool_use" in response

async def test_provider_parity():
    """Test that both providers handle tools identically."""
    tools = [/* same tools */]

    claude_provider = ClaudeAdapter(config)
    openai_provider = OpenAIAdapter(config)

    # Run same task with both providers
    claude_session = claude_provider.create_session(SessionConfig(tools=tools))
    openai_session = openai_provider.create_session(SessionConfig(tools=tools))

    claude_result = await claude_session.send_message("Search for *.py files")
    openai_result = await openai_session.send_message("Search for *.py files")

    # Both should invoke search tool with same arguments
    # (response formats differ, but tool calls should be equivalent)
```

## Recommendations

### For Tool Schema Authors

**DO:**
- Use JSON Schema Draft 4 compatible features (both providers support)
- Use simple types: string, number, boolean, object, array
- Use `enum` for constrained values
- Use `required` for mandatory parameters
- Use `description` for all parameters
- Keep schemas simple and flat (avoid deep nesting)

**DON'T:**
- Don't rely on `default` values (handle in implementation)
- Don't use complex validation (oneOf, anyOf, allOf)
- Don't use format constraints beyond basic types
- Don't use examples in schema (document separately)
- Don't assume provider-specific features

### For Provider Implementation

**DO:**
- Translate tools at provider boundary (not in agent code)
- Preserve tool call IDs for response matching
- Handle parallel tool execution correctly
- Validate translated schemas before use
- Log translation warnings for unsupported features
- Test round-trip conversion for all tools

**DON'T:**
- Don't modify original tool definitions (create copies)
- Don't silently drop features without logging
- Don't assume all schemas are valid
- Don't hardcode provider-specific logic in agents

## Related Documentation

- [Provider Abstraction Layer](../architecture/provider-abstraction.md)
- [OpenAI Adapter Design](../architecture/openai-adapter-design.md)
- [MCP Client Design](../architecture/mcp-client-design.md)
- [Tool Schema Translator](../architecture/tool-schema-translator.md)
- [Multi-Provider LLM Support Spec](../../.auto-claude/specs/171-codex-openai-integration-concept/spec.md)

## Future Work

- [ ] Implement ToolSchemaTranslator class
- [ ] Add comprehensive test coverage
- [ ] Document translation rules and limitations
- [ ] Create tool schema validation utilities
- [ ] Build migration guide for provider-specific tools
- [ ] Add tool schema linting for provider compatibility
- [ ] Performance optimization for bulk tool translation
- [ ] Support for provider-extended tool features

---

**Document Version:** 1.0
**Last Updated:** 2026-02-16
**Status:** Design Document (Concept Phase)
**Maintainer:** Auto Code Core Team
