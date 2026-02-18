# Tool Schema Translator Design

## Overview

This document describes the design of a **bidirectional schema translator** that converts between MCP (Model Context Protocol) tool schemas and OpenAI function calling schemas. This translator is a critical component for enabling OpenAI providers to use MCP servers (Context7, Linear, Graphiti, Electron, etc.) alongside Claude agents.

**Scope:**
- MCP tool schema → OpenAI function schema translation
- OpenAI function call → MCP tool call translation
- MCP tool result → OpenAI function result translation
- Schema validation and compatibility handling

**Out of Scope:**
- Claude SDK tool schema translation (covered in [tool-calling-analysis.md](../compatibility/tool-calling-analysis.md))
- MCP protocol implementation (covered in [mcp-client-design.md](./mcp-client-design.md))
- Provider abstraction layer (covered in [provider-abstraction.md](./provider-abstraction.md))

## Background

### Why Translation Is Needed

**MCP tools** and **OpenAI function calls** serve the same purpose—allowing AI models to invoke external functions—but use incompatible schema formats:

| Aspect | MCP Tool Schema | OpenAI Function Schema |
|--------|----------------|----------------------|
| **Schema location** | `inputSchema` property | `function.parameters` property |
| **Wrapper structure** | Flat tool object | Nested in `{"type": "function", "function": {...}}` |
| **Result format** | `result.content[]` (array) | `content` (string) |
| **Argument format** | Object (JSON) | String (JSON-serialized) |
| **JSON Schema version** | Draft 2020-12 | Draft 4 (subset) |

**The Problem:**
When an OpenAI agent needs to use an MCP tool:
1. MCP server exposes tool with `inputSchema`
2. OpenAI API expects `function.parameters` format
3. Agent cannot use the tool without translation

**The Solution:**
ToolSchemaTranslator sits between MCP and OpenAI, converting schemas in both directions transparently.

### Architecture Context

```
┌─────────────────────────────────────────────────────────────┐
│                  OpenAI Agent Session                       │
│              (wants to call external tools)                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Requests tools in OpenAI format
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Tool Schema Translator (NEW)                   │
│                                                              │
│  - mcp_to_openai_schema()  - MCP → OpenAI format           │
│  - openai_to_mcp_call()    - OpenAI → MCP format           │
│  - mcp_to_openai_result()  - MCP result → OpenAI format    │
│  - validate_compatibility() - Check schema compatibility    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ JSON-RPC 2.0
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   MCP Server (Context7)                     │
│              Exposes tools with inputSchema                  │
└─────────────────────────────────────────────────────────────┘
```

## Schema Format Comparison

### MCP Tool Schema

MCP tools use **JSON Schema Draft 2020-12** for input validation:

```json
{
  "name": "search_code",
  "description": "Search codebase for matching files",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query string"
      },
      "filePattern": {
        "type": "string",
        "description": "File pattern to match (e.g., '*.py')"
      },
      "caseSensitive": {
        "type": "boolean",
        "default": false
      }
    },
    "required": ["query"]
  }
}
```

**Key characteristics:**
- **Flat structure**: Tool properties at top level
- **`inputSchema`**: Contains full JSON Schema (Draft 2020-12)
- **`default` values**: Supported in property definitions
- **`description`**: At both tool and property levels

### OpenAI Function Schema

OpenAI functions use **JSON Schema Draft 4** (subset):

```json
{
  "type": "function",
  "function": {
    "name": "search_code",
    "description": "Search codebase for matching files",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Search query string"
        },
        "filePattern": {
          "type": "string",
          "description": "File pattern to match (e.g., '*.py')"
        },
        "caseSensitive": {
          "type": "boolean"
        }
      },
      "required": ["query"]
    }
  }
}
```

**Key characteristics:**
- **Nested structure**: Wrapped in `{"type": "function", "function": {...}}`
- **`parameters`**: JSON Schema Draft 4 (subset of Draft 2020-12)
- **No `default` values**: OpenAI doesn't support defaults in schema
- **Discriminator**: `type: "function"` required at top level

## Schema Compatibility Matrix

### Fully Compatible Features

| Feature | MCP | OpenAI | Translation |
|---------|-----|--------|-------------|
| String properties | ✓ | ✓ | Direct mapping |
| Numeric properties | ✓ | ✓ | Direct mapping |
| Boolean properties | ✓ | ✓ | Direct mapping |
| Object properties | ✓ | ✓ | Direct mapping |
| Array properties | ✓ | ✓ | Direct mapping |
| Enum constraints | ✓ | ✓ | Direct mapping |
| Required fields | ✓ | ✓ | Direct mapping |
| Nested objects | ✓ | ✓ | Direct mapping |
| Property descriptions | ✓ | ✓ | Direct mapping |
| Tool descriptions | ✓ | ✓ | Direct mapping |

### Requires Translation or Filtering

| Feature | MCP | OpenAI | Translation Strategy |
|---------|-----|--------|----------------------|
| **Schema location** | `inputSchema` | `function.parameters` | Move to nested property |
| **Function wrapper** | None | `{"type": "function"...}` | Add wrapper for OpenAI |
| **Default values** | ✓ | ✗ | Remove for OpenAI |
| **Examples** | ✓ | ✗ | Remove for OpenAI |
| **Format validation** | ✓ (full) | ✓ (limited) | Remove unsupported formats |
| **Complex array items** | ✓ | ✓ (simple only) | Simplify for OpenAI |
| **OneOf/AnyOf/AllOf** | ✓ | Limited | Test per case, may remove |

### Incompatible (Mitigation Required)

| Feature | MCP | OpenAI | Mitigation |
|---------|-----|--------|------------|
| **Extended JSON Schema keywords** | ✓ | ✗ | Remove in translation |
| **Pattern-based formats** | ✓ | ✗ | Remove, validate in tool impl |
| **Complex validation** | ✓ | ✗ | Simplify or validate in code |

## Translator Design

### ToolSchemaTranslator Class

**Purpose:** Bidirectional translation between MCP tool schemas and OpenAI function schemas.

**Key Responsibilities:**
- Convert MCP tool definitions to OpenAI function format
- Validate schema compatibility
- Remove unsupported features
- Preserve tool semantics during translation
- Provide clear error messages for incompatible schemas

**Conceptual Interface:**

```python
class ToolSchemaTranslator:
    """Translates tool schemas between MCP and OpenAI formats.

    This translator enables OpenAI providers to use MCP tools by
    converting schemas bidirectionally.

    Usage:
        translator = ToolSchemaTranslator()

        # MCP → OpenAI
        mcp_tool = {"name": "search", "inputSchema": {...}}
        openai_func = translator.mcp_to_openai(mcp_tool)

        # OpenAI → MCP
        openai_call = {"function": {"name": "search", "arguments": "{...}"}}
        tool_name, args = translator.openai_to_mcp_call(openai_call)

        # MCP result → OpenAI result
        mcp_result = {"content": [{"type": "text", "text": "..."}]}
        openai_result = translator.mcp_to_openai_result(mcp_result)
    """

    def mcp_to_openai(self, mcp_tool: dict) -> dict:
        """Convert MCP tool schema to OpenAI function format.

        Args:
            mcp_tool: MCP tool definition with inputSchema

        Returns:
            OpenAI function definition with parameters

        Raises:
            SchemaTranslationError: If schema contains incompatible features

        Example:
            >>> mcp_tool = {
            ...     "name": "search",
            ...     "description": "Search files",
            ...     "inputSchema": {
            ...         "type": "object",
            ...         "properties": {"query": {"type": "string"}}
            ...     }
            ... }
            >>> translator.mcp_to_openai(mcp_tool)
            {
                "type": "function",
                "function": {
                    "name": "search",
                    "description": "Search files",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}}
                    }
                }
            }
        """
        pass

    def openai_to_mcp_call(
        self,
        openai_function_call: dict
    ) -> tuple[str, dict]:
        """Convert OpenAI function call to MCP tool call format.

        Args:
            openai_function_call: OpenAI function call from model response

        Returns:
            Tuple of (tool_name, arguments_dict)

        Raises:
            InvalidFunctionCallError: If function call is malformed

        Example:
            >>> openai_call = {
            ...     "id": "call_123",
            ...     "function": {
            ...         "name": "search",
            ...         "arguments": '{"query": "*.py"}'
            ...     }
            ... }
            >>> translator.openai_to_mcp_call(openai_call)
            ("search", {"query": "*.py"})
        """
        pass

    def mcp_to_openai_result(
        self,
        mcp_result: dict,
        tool_call_id: str
    ) -> dict:
        """Convert MCP tool result to OpenAI function result format.

        Args:
            mcp_result: MCP tool execution result
            tool_call_id: OpenAI tool call ID to match request/response

        Returns:
            OpenAI tool result message

        Example:
            >>> mcp_result = {
            ...     "content": [
            ...         {"type": "text", "text": "Found 5 files"}
            ...     ],
            ...     "isError": false
            ... }
            >>> translator.mcp_to_openai_result(mcp_result, "call_123")
            {
                "role": "tool",
                "tool_call_id": "call_123",
                "content": "Found 5 files"
            }
        """
        pass

    def validate_compatibility(
        self,
        mcp_tool: dict
    ) -> CompatibilityReport:
        """Validate that MCP tool is compatible with OpenAI.

        Checks for:
        - No unsupported JSON Schema features
        - No required features that will be lost in translation
        - Safe type conversions

        Args:
            mcp_tool: MCP tool definition to validate

        Returns:
            CompatibilityReport with warnings/errors

        Example:
            >>> report = translator.validate_compatibility(mcp_tool)
            >>> if report.has_errors:
            ...     print(f"Incompatible: {report.errors}")
            >>> if report.has_warnings:
            ...     print(f"Warnings: {report.warnings}")
        """
        pass

    def _translate_schema(
        self,
        mcp_schema: dict
    ) -> dict:
        """Translate MCP JSON Schema to OpenAI-compatible format.

        Removes unsupported features:
        - default values
        - examples
        - format constraints (beyond basic types)
        - complex validation keywords

        Returns:
            OpenAI-compatible JSON Schema (Draft 4 subset)
        """
        pass

    def _filter_property(
        self,
        property_def: dict
    ) -> dict:
        """Filter property definition to OpenAI-compatible subset.

        Removes features not supported by OpenAI while preserving
        the core type and validation information.
        """
        pass
```

### Translation Logic

#### MCP → OpenAI Schema Translation

```python
def mcp_to_openai(self, mcp_tool: dict) -> dict:
    """Convert MCP tool to OpenAI function format."""

    # Validate compatibility first
    report = self.validate_compatibility(mcp_tool)
    if report.has_errors:
        raise SchemaTranslationError(
            f"Tool {mcp_tool['name']} has incompatible features: "
            f"{report.errors}"
        )

    # Log warnings if any
    if report.has_warnings:
        logger.warning(
            f"Translating tool {mcp_tool['name']} with warnings: "
            f"{report.warnings}"
        )

    # Extract schema
    input_schema = mcp_tool.get("inputSchema", {})

    # Translate to OpenAI format
    return {
        "type": "function",
        "function": {
            "name": mcp_tool["name"],
            "description": mcp_tool.get("description", ""),
            "parameters": self._translate_schema(input_schema)
        }
    }

def _translate_schema(self, mcp_schema: dict) -> dict:
    """Translate MCP JSON Schema to OpenAI format."""

    openai_schema = {
        "type": mcp_schema.get("type", "object"),
        "properties": {}
    }

    # Translate properties
    for prop_name, prop_def in mcp_schema.get("properties", {}).items():
        openai_schema["properties"][prop_name] = self._filter_property(prop_def)

    # Copy required fields
    if "required" in mcp_schema:
        openai_schema["required"] = mcp_schema["required"]

    return openai_schema

def _filter_property(self, prop_def: dict) -> dict:
    """Filter property to OpenAI-compatible subset."""

    filtered = {}

    # Copy basic fields
    if "type" in prop_def:
        filtered["type"] = prop_def["type"]
    if "description" in prop_def:
        filtered["description"] = prop_def["description"]
    if "enum" in prop_def:
        filtered["enum"] = prop_def["enum"]

    # Recursively handle nested objects
    if prop_def.get("type") == "object" and "properties" in prop_def:
        filtered["properties"] = {
            k: self._filter_property(v)
            for k, v in prop_def["properties"].items()
        }
        if "required" in prop_def:
            filtered["required"] = prop_def["required"]

    # Handle arrays (simplify for OpenAI)
    if prop_def.get("type") == "array" and "items" in prop_def:
        items = prop_def["items"]
        if isinstance(items, dict):
            filtered["items"] = self._filter_property(items)

    # Note: We deliberately skip:
    # - "default" (not supported by OpenAI)
    # - "examples" (not supported by OpenAI)
    # - "format" (limited support, removed for safety)
    # - "pattern" (limited support, removed for safety)

    return filtered
```

#### OpenAI → MCP Call Translation

```python
def openai_to_mcp_call(
    self,
    openai_function_call: dict
) -> tuple[str, dict]:
    """Convert OpenAI function call to MCP tool call."""

    function = openai_function_call.get("function", {})

    # Extract tool name
    tool_name = function.get("name")
    if not tool_name:
        raise InvalidFunctionCallError("Function call missing 'name'")

    # Parse arguments
    arguments_str = function.get("arguments", "{}")
    try:
        arguments = json.loads(arguments_str)
    except json.JSONDecodeError as e:
        raise InvalidFunctionCallError(
            f"Invalid arguments JSON: {e}"
        )

    return tool_name, arguments
```

#### MCP → OpenAI Result Translation

```python
def mcp_to_openai_result(
    self,
    mcp_result: dict,
    tool_call_id: str
) -> dict:
    """Convert MCP tool result to OpenAI format."""

    # Extract text content from MCP result
    content_parts = mcp_result.get("content", [])
    text_parts = [
        part.get("text", "")
        for part in content_parts
        if part.get("type") == "text"
    ]

    # Join text parts
    combined_text = "\n".join(text_parts)

    # Handle error case
    if mcp_result.get("isError", False):
        combined_text = f"Error: {combined_text}"

    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": combined_text
    }
```

## Compatibility Validation

### CompatibilityReport Class

```python
@dataclass
class CompatibilityReport:
    """Result of schema compatibility validation."""

    tool_name: str
    """Name of the tool being validated"""

    is_compatible: bool
    """Whether tool can be translated without errors"""

    errors: list[str]
    """Critical incompatibilities that prevent translation"""

    warnings: list[str]
    """Features that will be removed or modified in translation"""

    removed_features: dict[str, list[str]]
    """Features that will be removed, grouped by property"""

    @property
    def has_errors(self) -> bool:
        """Whether validation found errors."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Whether validation found warnings."""
        return len(self.warnings) > 0
```

### Validation Rules

**Critical Errors (block translation):**

| Error | Condition | Message |
|-------|-----------|---------|
| **Missing name** | `name` not present | "Tool missing required 'name' field" |
| **Missing schema** | `inputSchema` not present | "Tool missing required 'inputSchema' field" |
| **Invalid type** | Property type not in allowed types | "Property '{prop}' has invalid type: {type}" |
| **Complex items** | Array items use oneOf/anyOf | "Array '{prop}' has complex items (not supported)" |

**Warnings (feature will be removed):**

| Warning | Condition | Message |
|---------|-----------|---------|
| **Default value** | Property has `default` | "Property '{prop}' default value will be removed" |
| **Examples** | Property has `examples` | "Property '{prop}' examples will be removed" |
| **Format constraint** | Property has unsupported `format` | "Property '{prop}' format '{fmt}' will be removed" |
| **Pattern** | Property has `pattern` | "Property '{prop}' pattern will be removed" |

**Validation Example:**

```python
def validate_compatibility(
    self,
    mcp_tool: dict
) -> CompatibilityReport:
    """Validate MCP tool compatibility with OpenAI."""

    errors = []
    warnings = []
    removed_features = {}

    # Check required fields
    if "name" not in mcp_tool:
        errors.append("Tool missing required 'name' field")

    if "inputSchema" not in mcp_tool:
        errors.append("Tool missing required 'inputSchema' field")
        return CompatibilityReport(
            tool_name=mcp_tool.get("name", "<unknown>"),
            is_compatible=False,
            errors=errors,
            warnings=warnings,
            removed_features=removed_features
        )

    # Validate schema
    schema = mcp_tool["inputSchema"]
    self._validate_schema(schema, errors, warnings, removed_features)

    return CompatibilityReport(
        tool_name=mcp_tool["name"],
        is_compatible=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        removed_features=removed_features
    )

def _validate_schema(
    self,
    schema: dict,
    errors: list[str],
    warnings: list[str],
    removed_features: dict[str, list[str]]
) -> None:
    """Recursively validate schema."""

    # Check each property
    for prop_name, prop_def in schema.get("properties", {}).items():
        # Check type
        if "type" not in prop_def:
            errors.append(f"Property '{prop_name}' missing type")
            continue

        prop_type = prop_def["type"]

        # Check for unsupported features
        if "default" in prop_def:
            warnings.append(
                f"Property '{prop_name}' default value will be removed"
            )
            removed_features.setdefault(prop_name, []).append("default")

        if "examples" in prop_def:
            warnings.append(
                f"Property '{prop_name}' examples will be removed"
            )
            removed_features.setdefault(prop_name, []).append("examples")

        if "format" in prop_def:
            fmt = prop_def["format"]
            if fmt not in ALLOWED_FORMATS:
                warnings.append(
                    f"Property '{prop_name}' format '{fmt}' will be removed"
                )
                removed_features.setdefault(prop_name, []).append("format")

        if "pattern" in prop_def:
            warnings.append(
                f"Property '{prop_name}' pattern will be removed"
            )
            removed_features.setdefault(prop_name, []).append("pattern")

        # Recursively validate nested objects
        if prop_type == "object" and "properties" in prop_def:
            self._validate_schema(
                prop_def, errors, warnings, removed_features
            )

        # Validate array items
        if prop_type == "array" and "items" in prop_def:
            items = prop_def["items"]
            if isinstance(items, dict):
                if "oneOf" in items or "anyOf" in items:
                    errors.append(
                        f"Array '{prop_name}' has complex items "
                        "(oneOf/anyOf not supported)"
                    )
                else:
                    self._validate_property(
                        items, f"{prop_name}[]", errors, warnings
                    )
```

## Translation Examples

### Example 1: Simple Tool (Full Compatibility)

**MCP Tool:**
```json
{
  "name": "get_weather",
  "description": "Get current weather for a location",
  "inputSchema": {
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

**→ OpenAI Function:**
```json
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

**Compatibility:** ✓ Fully compatible (no warnings)

### Example 2: Tool with Defaults (Warning)

**MCP Tool:**
```json
{
  "name": "read_file",
  "description": "Read file contents",
  "inputSchema": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "File path"
      },
      "encoding": {
        "type": "string",
        "default": "utf-8",
        "description": "File encoding"
      }
    },
    "required": ["path"]
  }
}
```

**→ OpenAI Function (defaults removed):**
```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "Read file contents",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {
          "type": "string",
          "description": "File path"
        },
        "encoding": {
          "type": "string",
          "description": "File encoding"
        }
      },
      "required": ["path"]
    }
  }
}
```

**Compatibility:** ⚠ Warning - "Property 'encoding' default value will be removed"

**Mitigation:** Tool implementation should handle default encoding logic.

### Example 3: Complex Nested Schema

**MCP Tool:**
```json
{
  "name": "create_issue",
  "description": "Create a Linear issue",
  "inputSchema": {
    "type": "object",
    "properties": {
      "title": {
        "type": "string",
        "description": "Issue title"
      },
      "description": {
        "type": "string",
        "description": "Issue description"
      },
      "priority": {
        "type": "object",
        "description": "Issue priority",
        "properties": {
          "level": {
            "type": "string",
            "enum": ["urgent", "high", "medium", "low"]
          }
        }
      }
    },
    "required": ["title"]
  }
}
```

**→ OpenAI Function:**
```json
{
  "type": "function",
  "function": {
    "name": "create_issue",
    "description": "Create a Linear issue",
    "parameters": {
      "type": "object",
      "properties": {
        "title": {
          "type": "string",
          "description": "Issue title"
        },
        "description": {
          "type": "string",
          "description": "Issue description"
        },
        "priority": {
          "type": "object",
          "description": "Issue priority",
          "properties": {
            "level": {
              "type": "string",
              "enum": ["urgent", "high", "medium", "low"]
            }
          }
        }
      },
      "required": ["title"]
    }
  }
}
```

**Compatibility:** ✓ Fully compatible

### Example 4: Function Call Translation

**OpenAI Function Call:**
```json
{
  "id": "call_abc123",
  "type": "function",
  "function": {
    "name": "search_code",
    "arguments": "{\"query\": \"MCPClient\", \"filePattern\": \"*.py\"}"
  }
}
```

**→ MCP Tool Call:**
```python
(
    "search_code",
    {"query": "MCPClient", "filePattern": "*.py"}
)
```

### Example 5: Tool Result Translation

**MCP Tool Result:**
```json
{
  "content": [
    {
      "type": "text",
      "text": "Found 3 matching files:\n- src/mcp/client.py\n- src/mcp/protocol.py\n- tests/test_client.py"
    }
  ],
  "isError": false
}
```

**→ OpenAI Tool Result:**
```json
{
  "role": "tool",
  "tool_call_id": "call_abc123",
  "content": "Found 3 matching files:\n- src/mcp/client.py\n- src/mcp/protocol.py\n- tests/test_client.py"
}
```

## Error Handling

### Exception Hierarchy

```python
class ToolTranslationError(Exception):
    """Base exception for translation errors."""
    pass

class SchemaTranslationError(ToolTranslationError):
    """Schema contains incompatible features."""
    pass

class InvalidFunctionCallError(ToolTranslationError):
    """Function call is malformed or missing required fields."""
    pass

class InvalidToolResultError(ToolTranslationError):
    """Tool result is malformed."""
    pass
```

### Error Messages

**Clear, actionable error messages:**

```python
# Bad: Generic error
raise SchemaTranslationError("Translation failed")

# Good: Specific error with guidance
raise SchemaTranslationError(
    f"Tool 'search' has incompatible features:\n"
    f"  - Property 'filePattern' has unsupported format: 'glob'\n"
    f"  - Property 'caseSensitive' has default value (will be removed)\n"
    f"\n"
    f"Recommendations:\n"
    f"  1. Remove format constraint from 'filePattern'\n"
    f"  2. Handle default for 'caseSensitive' in tool implementation"
)
```

## Testing Strategy

### Unit Tests

```python
# test_tool_translator.py

def test_simple_tool_translation():
    """Test translation of simple, compatible tool."""
    mcp_tool = {
        "name": "echo",
        "description": "Echo input",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string"}
            }
        }
    }

    openai_func = translator.mcp_to_openai(mcp_tool)

    assert openai_func["type"] == "function"
    assert openai_func["function"]["name"] == "echo"
    assert "parameters" in openai_func["function"]

def test_default_value_removal():
    """Test that default values are removed with warning."""
    mcp_tool = {
        "name": "test",
        "inputSchema": {
            "type": "object",
            "properties": {
                "arg": {
                    "type": "string",
                    "default": "value"
                }
            }
        }
    }

    report = translator.validate_compatibility(mcp_tool)
    assert report.has_warnings
    assert "default" in report.removed_features.get("arg", [])

    openai_func = translator.mcp_to_openai(mcp_tool)
    assert "default" not in openai_func["function"]["parameters"]["properties"]["arg"]

def test_function_call_parsing():
    """Test OpenAI function call to MCP call conversion."""
    openai_call = {
        "id": "call_123",
        "function": {
            "name": "search",
            "arguments": '{"query": "test"}'
        }
    }

    tool_name, args = translator.openai_to_mcp_call(openai_call)

    assert tool_name == "search"
    assert args == {"query": "test"}

def test_invalid_function_call():
    """Test error handling for malformed function call."""
    openai_call = {
        "id": "call_123",
        "function": {
            "arguments": "invalid json"
        }
    }

    with pytest.raises(InvalidFunctionCallError):
        translator.openai_to_mcp_call(openai_call)

def test_result_translation():
    """Test MCP result to OpenAI result conversion."""
    mcp_result = {
        "content": [
            {"type": "text", "text": "Success"}
        ],
        "isError": False
    }

    openai_result = translator.mcp_to_openai_result(mcp_result, "call_123")

    assert openai_result["role"] == "tool"
    assert openai_result["tool_call_id"] == "call_123"
    assert openai_result["content"] == "Success"
```

### Integration Tests

```python
# test_translator_integration.py

async def test_end_to_end_tool_execution():
    """Test full tool execution flow with translation."""

    # 1. Discover tool from MCP server
    mcp_tool = await mcp_client.list_tools()[0]  # e.g., Context7 search

    # 2. Translate to OpenAI format
    openai_func = translator.mcp_to_openai(mcp_tool)

    # 3. Send to OpenAI model
    response = await openai_client.chat(
        model="gpt-5.2",
        messages=[{"role": "user", "content": "Search for MCP"}],
        tools=[openai_func]
    )

    # 4. Translate function call back to MCP
    if response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name, args = translator.openai_to_mcp_call(tool_call)

            # 5. Execute via MCP
            mcp_result = await mcp_client.call_tool(tool_name, args)

            # 6. Translate result back to OpenAI
            openai_result = translator.mcp_to_openai_result(
                mcp_result,
                tool_call.id
            )

            # 7. Send result back to model
            # ... (continue conversation)
```

## Edge Cases and Considerations

### 1. Default Values

**Problem:** OpenAI doesn't support defaults, but MCP tools may rely on them.

**Strategy:**
- **Translation:** Remove default values from schema
- **Validation:** Warn user about removed defaults
- **Best Practice:** Handle defaults in tool implementation code

**Example:**
```python
# MCP (with default)
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
        "encoding": {"type": "string"}
    }
}

# Handle default in implementation
def read_file(path: str, encoding: str = "utf-8") -> str:
    # Default applied here, not in schema
    ...
```

### 2. Format Constraints

**Problem:** OpenAI has limited format support, MCP supports full JSON Schema formats.

**Strategy:**
- **Translation:** Remove unsupported format constraints
- **Validation:** Warn about removed formats
- **Best Practice:** Validate formats in tool implementation

**Unsupported formats to remove:**
- `format: "email"`
- `format: "uri"`
- `format: "date-time"`
- `format: "uuid"`
- `format: "binary"`

**Supported formats (safe to keep):**
- `format: "date"`
- `format: "time"`

### 3. Complex Array Items

**Problem:** OpenAI only supports simple array item schemas.

**Strategy:**
- **Translation:** Simplify complex items to basic types
- **Validation:** Error if items use oneOf/anyOf
- **Best Practice:** Use object properties instead of complex arrays

**Example:**
```python
# MCP (complex items)
{
    "type": "array",
    "items": {
        "oneOf": [
            {"type": "string"},
            {"type": "number"}
        ]
    }
}

# This will cause validation error
# Recommendation: Restructure as object
```

### 4. Mixed Content Results

**Problem:** MCP results can have mixed content types (text, images, data).

**Strategy:**
- **Translation:** Extract and concatenate text content
- **Other types:** Log warning, skip non-text content
- **Best Practice:** Keep results text-only for OpenAI

**Example:**
```python
# MCP result (mixed)
{
    "content": [
        {"type": "text", "text": "Found 3 files"},
        {"type": "image", "data": "..."},  # Will be skipped
        {"type": "text", "text": "Processing complete"}
    ]
}

# OpenAI result (text only)
{
    "content": "Found 3 files\nProcessing complete"
}
```

### 5. Error Propagation

**Problem:** MCP tools return errors in result, OpenAI expects string content.

**Strategy:**
- **Translation:** Prefix error messages with "Error:"
- **Validation:** Check `isError` flag in MCP result
- **Best Practice:** Let model decide retry strategy

**Example:**
```python
# MCP error result
{
    "content": [{"text": "File not found"}],
    "isError": true
}

# OpenAI error result
{
    "content": "Error: File not found"
}
```

## Performance Considerations

### Optimization Strategies

| Area | Optimization | Impact |
|------|-------------|--------|
| **Schema translation** | Cache translated schemas | Avoid redundant translation |
| **Validation** | Skip validation for trusted tools | Faster translation |
| **Result parsing** | Stream large text results | Lower memory usage |
| **Error handling** | Batch validation for multiple tools | Faster initialization |

### Caching Strategy

```python
class CachedToolSchemaTranslator:
    """Translator with schema caching."""

    def __init__(self):
        self._cache: dict[str, dict] = {}

    def mcp_to_openai(self, mcp_tool: dict) -> dict:
        """Translate with caching."""

        tool_name = mcp_tool["name"]

        # Check cache
        if tool_name in self._cache:
            return self._cache[tool_name]

        # Translate and cache
        openai_func = self._translate(mcp_tool)
        self._cache[tool_name] = openai_func

        return openai_func
```

## Configuration

### Translation Options

```python
@dataclass
class TranslationConfig:
    """Configuration for schema translation."""

    strict_validation: bool = True
    """Fail on incompatible features (if True) or remove with warning (if False)"""

    preserve_defaults: bool = False
    """Attempt to preserve defaults (not supported by OpenAI, will be removed)"""

    log_warnings: bool = True
    """Log warnings about removed features"""

    cache_schemas: bool = True
    """Cache translated schemas for performance"""

    allowed_formats: set[str] = frozenset(["date", "time"])
    """JSON Schema formats that are safe to keep"""
```

## Related Documentation

- [MCP Client Design](./mcp-client-design.md) - Custom MCP client for OpenAI
- [Tool Calling Analysis](../compatibility/tool-calling-analysis.md) - Claude vs OpenAI tool calling
- [OpenAI Adapter Design](./openai-adapter-design.md) - OpenAI provider implementation
- [Provider Abstraction](./provider-abstraction.md) - Multi-provider architecture

## Future Enhancements

### Potential Improvements

| Enhancement | Benefit | Effort |
|-------------|---------|--------|
| **Schema normalization** | Normalize all schemas to common format | Medium |
| **Custom type mappings** | Support provider-specific type extensions | High |
| **Validation framework** | Pluggable validation rules | Medium |
| **Translation metrics** | Track translation statistics | Low |
| **Auto-fixing** | Automatically fix common incompatibilities | High |

### Migration Path

**When OpenAI adds schema support:**
- Translator can adopt new features incrementally
- No breaking changes to public API
- Backward compatibility maintained via feature detection

**When MCP spec changes:**
- Version detection in translator
- Backward-compatible translation for older schemas
- Clear deprecation path for unsupported versions

## Appendix: Translation Reference

### Quick Reference: MCP → OpenAI

| MCP Field | OpenAI Field | Notes |
|-----------|-------------|-------|
| `name` | `function.name` | Direct mapping |
| `description` | `function.description` | Direct mapping |
| `inputSchema` | `function.parameters` | Move location |
| `inputSchema.properties` | `parameters.properties` | Direct mapping |
| `inputSchema.required` | `parameters.required` | Direct mapping |
| `property.default` | *(removed)* | Not supported |
| `property.examples` | *(removed)* | Not supported |
| `property.format` | *(removed if unsupported)* | Limited support |
| `property.pattern` | *(removed)* | Limited support |

### Quick Reference: OpenAI → MCP

| OpenAI Field | MCP Field | Notes |
|-------------|-----------|-------|
| `function.name` | `name` | Direct mapping |
| `function.description` | `description` | Direct mapping |
| `function.parameters` | `inputSchema` | Move location |
| `function.arguments` | *(parsed JSON)* | String → Object |

---

**Document Version:** 1.0
**Last Updated:** 2026-02-16
**Status:** Design Document (Concept Phase)
**Maintainer:** Auto Code Core Team
