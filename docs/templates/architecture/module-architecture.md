# [Module Name] Module

<!--
INSTRUCTIONS: Replace [Module Name] with your module name (e.g., "Agents", "Core Security", "Memory System")
This template helps you document module architecture following Auto Code's documentation patterns.
Fill in each section below, removing placeholder comments when done.
-->

[One-sentence description of what this module does and why it exists]

## Architecture

<!--
INSTRUCTIONS: Describe how the module is organized by concern.
If you refactored from a monolithic file, mention the original size and motivation.
-->

[Brief explanation of the module's organization philosophy]

```
module-name/
├── __init__.py          # [Purpose - e.g., Public API exports]
├── base.py              # [Purpose - e.g., Shared constants and imports]
├── core.py              # [Purpose - e.g., Core functionality]
├── utils.py             # [Purpose - e.g., Helper functions]
└── submodule/           # [Purpose - e.g., Specialized functionality]
    ├── __init__.py
    └── implementation.py
```

## Modules

<!--
INSTRUCTIONS: List each module file with size and purpose.
Include key functions/classes for each module.
-->

### `base.py` (XXX bytes/KB)
- [Description of what this module provides]
- Key exports:
  - `CONSTANT_NAME` - [Purpose]
  - `function_name()` - [Purpose]

### `core.py` (XXX KB)
- [Description of core functionality]
- Key functions:
  - `primary_function()` - [Purpose and usage]
  - `secondary_function()` - [Purpose and usage]

### `utils.py` (XXX KB)
- [Description of utility functions]
- Key utilities:
  - `helper_function()` - [Purpose]
  - `validation_function()` - [Purpose]

<!-- Add more module sections as needed -->

## Public API

<!--
INSTRUCTIONS: Show the clean public API that users should import.
Use real code examples showing the recommended import pattern.
-->

The `[module-name]` module exports a clean public API:

```python
from [module_name] import (
    # Main functions
    primary_function,
    secondary_function,

    # Utilities
    helper_function,
    validation_function,

    # Constants
    IMPORTANT_CONSTANT,
)
```

## Backwards Compatibility

<!--
INSTRUCTIONS: If you refactored existing code, explain how backwards compatibility is maintained.
If this is a new module, you can remove this section or note "N/A - New module"
-->

[Explanation of how old imports continue to work, or note if this is a new module]

**Example:**
```python
# Old code still works
from [old_module] import primary_function

# New code can use modular imports
from [module_name].core import primary_function
```

All existing imports continue to work without changes.

## Benefits

<!--
INSTRUCTIONS: List the key benefits of this module's design.
Focus on maintainability, testability, clarity, and scalability.
-->

1. **Separation of Concerns**: [How responsibilities are divided]
2. **Maintainability**: [Why it's easier to maintain]
3. **Testability**: [How it improves testing]
4. **Backwards Compatible**: [If applicable - how old code continues to work]
5. **Scalability**: [How it supports future growth]

## Module Dependencies

<!--
INSTRUCTIONS: Show how modules depend on each other using a tree structure.
This helps understand the dependency hierarchy and prevents circular dependencies.
-->

```
core.py
  ├── utils.py (helper functions)
  └── base.py (constants, logging)

submodule/implementation.py
  ├── core.py (main functionality)
  └── utils.py (validation)
```

## Usage Examples

<!--
INSTRUCTIONS: Provide practical code examples showing how to use the module.
Include common use cases and patterns.
-->

### Basic Usage

```python
from [module_name] import primary_function

# Example usage
result = primary_function(arg1, arg2)
```

### Advanced Usage

```python
from [module_name].core import CoreClass
from [module_name].utils import helper_function

# Example of advanced usage
instance = CoreClass(config)
processed = helper_function(instance.data)
```

## Testing

<!--
INSTRUCTIONS: Explain how to test the module.
Include test commands and what they verify.
-->

Run the test suite to verify the module:

```bash
# Run all module tests
pytest tests/test_[module_name].py -v

# Run specific test
pytest tests/test_[module_name].py::test_function_name -v
```

This verifies:
- [What aspect is tested]
- [What aspect is tested]
- [What aspect is tested]

## Migration Guide

<!--
INSTRUCTIONS: If this is a refactored module, provide migration steps.
For new modules, provide integration steps instead.
-->

### For new code:
```python
# Use focused imports for clarity
from [module_name].core import primary_function
from [module_name].utils import helper_function
```

### For existing code:
```python
# Old imports continue to work (if backwards compatible)
from [old_module] import primary_function
```

## Configuration

<!--
INSTRUCTIONS: Document any configuration options, environment variables, or settings.
Remove this section if the module doesn't require configuration.
-->

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CONFIG_VAR` | Yes | - | [Purpose] |
| `OPTIONAL_VAR` | No | `value` | [Purpose] |

**Example `.env`:**
```bash
CONFIG_VAR=value
OPTIONAL_VAR=custom_value
```

## Related Documentation

<!--
INSTRUCTIONS: Link to related documentation that users might need.
Include guides, API docs, or architecture overviews.
-->

- [Related Module Documentation](../path/to/doc.md)
- [Integration Guide](../integration-guide.md)
- [API Reference](../api/endpoint-documentation.md)

## Future Enhancements

<!--
INSTRUCTIONS: Document planned improvements or known limitations.
This helps future contributors understand the roadmap.
OPTIONAL: Remove if not applicable.
-->

- [ ] [Planned enhancement 1]
- [ ] [Planned enhancement 2]
- [ ] [Known limitation to address]

## Troubleshooting

<!--
INSTRUCTIONS: Document common issues and solutions.
OPTIONAL: Remove if not applicable.
-->

### Issue: [Common problem]

**Symptom:** [What users see]

**Solution:**
```python
# How to fix it
```

---

**Template Version:** 1.0
**Last Updated:** [YYYY-MM-DD]
**Maintainer:** [Team/Person responsible for this module]
