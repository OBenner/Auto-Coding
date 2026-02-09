# {{MODULE_NAME}} API Reference

<!--
AUTO-GENERATED DOCUMENTATION TEMPLATE
This template is designed for automated API documentation generation tools.
It uses {{PLACEHOLDER}} syntax for automated substitution.

USAGE:
- Use code introspection tools (e.g., AST parsing, docstring extraction)
- Replace all {{PLACEHOLDER}} values with extracted code information
- Generate multiple files (one per module/class) using this template
- Update timestamps and version info automatically

SUPPORTED LANGUAGES:
- Python (using ast, inspect modules)
- TypeScript/JavaScript (using ts-morph, JSDoc)
-->

**Module:** `{{MODULE_PATH}}`
**Version:** `{{VERSION}}`
**Last Generated:** `{{TIMESTAMP}}`
**Language:** `{{LANGUAGE}}`
**Status:** `{{STATUS}}` <!-- Stable / Experimental / Deprecated -->

---

## Overview

{{MODULE_DESCRIPTION}}

**Category:** `{{CATEGORY}}` <!-- Service / Utility / Integration / Component / Model -->
**Exports:** {{EXPORT_COUNT}} functions, {{CLASS_COUNT}} classes

### Quick Links

- [Functions](#functions)
- [Classes](#classes)
- [Type Definitions](#type-definitions)
- [Constants](#constants)
- [Examples](#usage-examples)

---

## Installation / Import

### Import Statement

```{{LANGUAGE}}
{{IMPORT_STATEMENT}}
```

**Example:**

```{{LANGUAGE}}
{{IMPORT_EXAMPLE}}
```

### Dependencies

{{#DEPENDENCIES}}
**Required:**
{{#REQUIRED_DEPS}}
- `{{DEP_NAME}}` ({{DEP_VERSION}}) - {{DEP_PURPOSE}}
{{/REQUIRED_DEPS}}

**Optional:**
{{#OPTIONAL_DEPS}}
- `{{DEP_NAME}}` ({{DEP_VERSION}}) - {{DEP_PURPOSE}}
{{/OPTIONAL_DEPS}}
{{/DEPENDENCIES}}

---

## Functions

{{#FUNCTIONS}}
### `{{FUNCTION_NAME}}`

**Signature:**

```{{LANGUAGE}}
{{FUNCTION_SIGNATURE}}
```

**Description:**

{{FUNCTION_DESCRIPTION}}

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
{{#PARAMETERS}}
| `{{PARAM_NAME}}` | `{{PARAM_TYPE}}` | {{PARAM_REQUIRED}} | {{PARAM_DEFAULT}} | {{PARAM_DESCRIPTION}} |
{{/PARAMETERS}}

**Returns:**

| Type | Description |
|------|-------------|
| `{{RETURN_TYPE}}` | {{RETURN_DESCRIPTION}} |

{{#HAS_EXCEPTIONS}}
**Raises/Throws:**

| Exception | Condition |
|-----------|-----------|
{{#EXCEPTIONS}}
| `{{EXCEPTION_TYPE}}` | {{EXCEPTION_CONDITION}} |
{{/EXCEPTIONS}}
{{/HAS_EXCEPTIONS}}

**Example:**

```{{LANGUAGE}}
{{FUNCTION_EXAMPLE}}
```

{{#HAS_NOTES}}
**Notes:**
{{#NOTES}}
- {{NOTE_TEXT}}
{{/NOTES}}
{{/HAS_NOTES}}

**Source:** [`{{SOURCE_FILE}}#L{{LINE_NUMBER}}`]({{SOURCE_URL}})

---

{{/FUNCTIONS}}

## Classes

{{#CLASSES}}
### `{{CLASS_NAME}}`

**Type:** `{{CLASS_TYPE}}` <!-- Class / Abstract Class / Interface / Type -->

**Description:**

{{CLASS_DESCRIPTION}}

{{#HAS_INHERITANCE}}
**Inheritance:**

```{{LANGUAGE}}
{{INHERITANCE_CHAIN}}
```
{{/HAS_INHERITANCE}}

{{#HAS_IMPLEMENTS}}
**Implements:**

{{#IMPLEMENTS}}
- `{{INTERFACE_NAME}}`
{{/IMPLEMENTS}}
{{/HAS_IMPLEMENTS}}

#### Constructor

**Signature:**

```{{LANGUAGE}}
{{CONSTRUCTOR_SIGNATURE}}
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
{{#CONSTRUCTOR_PARAMS}}
| `{{PARAM_NAME}}` | `{{PARAM_TYPE}}` | {{PARAM_REQUIRED}} | {{PARAM_DEFAULT}} | {{PARAM_DESCRIPTION}} |
{{/CONSTRUCTOR_PARAMS}}

**Example:**

```{{LANGUAGE}}
{{CONSTRUCTOR_EXAMPLE}}
```

{{#HAS_PROPERTIES}}
#### Properties

| Property | Type | Access | Description |
|----------|------|--------|-------------|
{{#PROPERTIES}}
| `{{PROPERTY_NAME}}` | `{{PROPERTY_TYPE}}` | {{PROPERTY_ACCESS}} | {{PROPERTY_DESCRIPTION}} |
{{/PROPERTIES}}
{{/HAS_PROPERTIES}}

{{#HAS_METHODS}}
#### Methods

{{#METHODS}}
##### `{{METHOD_NAME}}`

**Signature:**

```{{LANGUAGE}}
{{METHOD_SIGNATURE}}
```

**Description:**

{{METHOD_DESCRIPTION}}

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
{{#METHOD_PARAMS}}
| `{{PARAM_NAME}}` | `{{PARAM_TYPE}}` | {{PARAM_REQUIRED}} | {{PARAM_DEFAULT}} | {{PARAM_DESCRIPTION}} |
{{/METHOD_PARAMS}}

**Returns:**

| Type | Description |
|------|-------------|
| `{{METHOD_RETURN_TYPE}}` | {{METHOD_RETURN_DESCRIPTION}} |

{{#HAS_METHOD_EXCEPTIONS}}
**Raises/Throws:**

| Exception | Condition |
|-----------|-----------|
{{#METHOD_EXCEPTIONS}}
| `{{EXCEPTION_TYPE}}` | {{EXCEPTION_CONDITION}} |
{{/METHOD_EXCEPTIONS}}
{{/HAS_METHOD_EXCEPTIONS}}

**Example:**

```{{LANGUAGE}}
{{METHOD_EXAMPLE}}
```

**Access:** `{{METHOD_ACCESS}}` <!-- public / private / protected -->
**Static:** `{{IS_STATIC}}`
**Async:** `{{IS_ASYNC}}`

---

{{/METHODS}}
{{/HAS_METHODS}}

**Source:** [`{{CLASS_SOURCE_FILE}}#L{{CLASS_LINE_NUMBER}}`]({{CLASS_SOURCE_URL}})

---

{{/CLASSES}}

## Type Definitions

{{#TYPE_DEFINITIONS}}
### `{{TYPE_NAME}}`

**Kind:** `{{TYPE_KIND}}` <!-- Interface / Type / Enum / Union / Intersection -->

**Definition:**

```{{LANGUAGE}}
{{TYPE_DEFINITION}}
```

**Description:**

{{TYPE_DESCRIPTION}}

{{#HAS_TYPE_FIELDS}}
**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
{{#TYPE_FIELDS}}
| `{{FIELD_NAME}}` | `{{FIELD_TYPE}}` | {{FIELD_REQUIRED}} | {{FIELD_DESCRIPTION}} |
{{/TYPE_FIELDS}}
{{/HAS_TYPE_FIELDS}}

{{#HAS_TYPE_VALUES}}
**Values:**

| Value | Description |
|-------|-------------|
{{#TYPE_VALUES}}
| `{{VALUE_NAME}}` | {{VALUE_DESCRIPTION}} |
{{/TYPE_VALUES}}
{{/HAS_TYPE_VALUES}}

**Example:**

```{{LANGUAGE}}
{{TYPE_EXAMPLE}}
```

**Source:** [`{{TYPE_SOURCE_FILE}}#L{{TYPE_LINE_NUMBER}}`]({{TYPE_SOURCE_URL}})

---

{{/TYPE_DEFINITIONS}}

## Constants

{{#CONSTANTS}}
### `{{CONSTANT_NAME}}`

**Type:** `{{CONSTANT_TYPE}}`
**Value:** `{{CONSTANT_VALUE}}`

**Description:**

{{CONSTANT_DESCRIPTION}}

**Source:** [`{{CONSTANT_SOURCE_FILE}}#L{{CONSTANT_LINE_NUMBER}}`]({{CONSTANT_SOURCE_URL}})

---

{{/CONSTANTS}}

## Usage Examples

### Basic Usage

```{{LANGUAGE}}
{{BASIC_USAGE_EXAMPLE}}
```

### Advanced Usage

```{{LANGUAGE}}
{{ADVANCED_USAGE_EXAMPLE}}
```

{{#HAS_INTEGRATION_EXAMPLES}}
### Integration Examples

{{#INTEGRATION_EXAMPLES}}
#### {{INTEGRATION_TITLE}}

```{{LANGUAGE}}
{{INTEGRATION_CODE}}
```

**Description:** {{INTEGRATION_DESCRIPTION}}

---

{{/INTEGRATION_EXAMPLES}}
{{/HAS_INTEGRATION_EXAMPLES}}

---

## Testing

### Unit Tests

**Test Location:** `{{TEST_FILE_PATH}}`

**Test Coverage:**
- **Lines:** {{COVERAGE_LINES}}%
- **Functions:** {{COVERAGE_FUNCTIONS}}%
- **Branches:** {{COVERAGE_BRANCHES}}%

**Example Test:**

```{{LANGUAGE}}
{{TEST_EXAMPLE}}
```

**Run Tests:**

```bash
{{TEST_COMMAND}}
```

---

## Performance

{{#HAS_PERFORMANCE_METRICS}}
### Performance Metrics

| Metric | Value | Context |
|--------|-------|---------|
{{#PERFORMANCE_METRICS}}
| {{METRIC_NAME}} | {{METRIC_VALUE}} | {{METRIC_CONTEXT}} |
{{/PERFORMANCE_METRICS}}

### Optimization Tips

{{#OPTIMIZATION_TIPS}}
- **{{TIP_TITLE}}:** {{TIP_DESCRIPTION}}
{{/OPTIMIZATION_TIPS}}
{{/HAS_PERFORMANCE_METRICS}}

---

## Error Handling

{{#ERROR_TYPES}}
### `{{ERROR_NAME}}`

**Base Class:** `{{ERROR_BASE}}`

**Description:** {{ERROR_DESCRIPTION}}

**When Thrown:** {{ERROR_CONDITION}}

**Example:**

```{{LANGUAGE}}
{{ERROR_EXAMPLE}}
```

---

{{/ERROR_TYPES}}

---

## Related Modules

{{#RELATED_MODULES}}
- [`{{RELATED_MODULE_NAME}}`]({{RELATED_MODULE_LINK}}) - {{RELATED_MODULE_DESCRIPTION}}
{{/RELATED_MODULES}}

---

## Changelog

{{#CHANGELOG_ENTRIES}}
### Version {{CHANGE_VERSION}} - {{CHANGE_DATE}}

{{#CHANGE_ADDED}}
**Added:**
{{#ADDED_ITEMS}}
- {{ADDED_ITEM}}
{{/ADDED_ITEMS}}
{{/CHANGE_ADDED}}

{{#CHANGE_CHANGED}}
**Changed:**
{{#CHANGED_ITEMS}}
- {{CHANGED_ITEM}}
{{/CHANGED_ITEMS}}
{{/CHANGE_CHANGED}}

{{#CHANGE_DEPRECATED}}
**Deprecated:**
{{#DEPRECATED_ITEMS}}
- {{DEPRECATED_ITEM}}
{{/DEPRECATED_ITEMS}}
{{/CHANGE_DEPRECATED}}

{{#CHANGE_REMOVED}}
**Removed:**
{{#REMOVED_ITEMS}}
- {{REMOVED_ITEM}}
{{/REMOVED_ITEMS}}
{{/CHANGE_REMOVED}}

{{#CHANGE_FIXED}}
**Fixed:**
{{#FIXED_ITEMS}}
- {{FIXED_ITEM}}
{{/FIXED_ITEMS}}
{{/CHANGE_FIXED}}

---

{{/CHANGELOG_ENTRIES}}

---

## Automation Guide

### Generating Documentation from Code

This template can be populated using the following tools:

#### Python (AST-based generation)

```python
import ast
import inspect
from pathlib import Path

def generate_docs(module_path: str) -> dict:
    """
    Extract API documentation from Python module.

    Returns:
        Dictionary with all {{PLACEHOLDER}} values filled
    """
    with open(module_path, 'r') as f:
        tree = ast.parse(f.read())

    functions = []
    classes = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append({
                'FUNCTION_NAME': node.name,
                'FUNCTION_SIGNATURE': ast.unparse(node),
                'FUNCTION_DESCRIPTION': ast.get_docstring(node) or '',
                'LINE_NUMBER': node.lineno,
                # Extract parameters from node.args
                'PARAMETERS': extract_parameters(node.args),
                # Extract return type from node.returns
                'RETURN_TYPE': ast.unparse(node.returns) if node.returns else 'None',
            })
        elif isinstance(node, ast.ClassDef):
            classes.append({
                'CLASS_NAME': node.name,
                'CLASS_DESCRIPTION': ast.get_docstring(node) or '',
                'CLASS_LINE_NUMBER': node.lineno,
                # Extract methods, properties, etc.
            })

    return {
        'MODULE_NAME': Path(module_path).stem,
        'MODULE_PATH': module_path,
        'FUNCTIONS': functions,
        'CLASSES': classes,
        'TIMESTAMP': datetime.now().isoformat(),
        'VERSION': get_module_version(module_path),
    }

# Usage:
# data = generate_docs('apps/backend/core/client.py')
# render_template('auto_generated_template.md', data)
```

#### TypeScript (ts-morph generation)

```typescript
import { Project } from 'ts-morph';

function generateDocs(filePath: string): object {
  const project = new Project();
  const sourceFile = project.addSourceFileAtPath(filePath);

  const functions = sourceFile.getFunctions().map(fn => ({
    FUNCTION_NAME: fn.getName(),
    FUNCTION_SIGNATURE: fn.getText(),
    FUNCTION_DESCRIPTION: fn.getJsDocs()[0]?.getDescription() || '',
    PARAMETERS: fn.getParameters().map(param => ({
      PARAM_NAME: param.getName(),
      PARAM_TYPE: param.getType().getText(),
      PARAM_REQUIRED: !param.isOptional(),
      PARAM_DEFAULT: param.getInitializer()?.getText() || 'N/A',
    })),
    RETURN_TYPE: fn.getReturnType().getText(),
    LINE_NUMBER: fn.getStartLineNumber(),
  }));

  const classes = sourceFile.getClasses().map(cls => ({
    CLASS_NAME: cls.getName(),
    CLASS_DESCRIPTION: cls.getJsDocs()[0]?.getDescription() || '',
    METHODS: cls.getMethods().map(method => ({
      METHOD_NAME: method.getName(),
      METHOD_SIGNATURE: method.getText(),
      // ... extract method details
    })),
  }));

  return {
    MODULE_NAME: sourceFile.getBaseNameWithoutExtension(),
    FUNCTIONS: functions,
    CLASSES: classes,
    TIMESTAMP: new Date().toISOString(),
  };
}

// Usage:
// const data = generateDocs('apps/frontend/src/services/api.ts');
// renderTemplate('auto_generated_template.md', data);
```

### Template Rendering

Use a templating engine like Mustache, Handlebars, or Jinja2:

```python
# Python with Jinja2
from jinja2 import Template

template = Template(Path('auto_generated_template.md').read_text())
output = template.render(data)
Path('generated_docs/module_name.md').write_text(output)
```

```javascript
// JavaScript with Handlebars
import Handlebars from 'handlebars';
import fs from 'fs';

const template = Handlebars.compile(
  fs.readFileSync('auto_generated_template.md', 'utf8')
);
const output = template(data);
fs.writeFileSync('generated_docs/module_name.md', output);
```

### Placeholder Reference

| Placeholder | Type | Description | Example |
|-------------|------|-------------|---------|
| `{{MODULE_NAME}}` | string | Module/file name | `client` |
| `{{MODULE_PATH}}` | string | Relative path to module | `apps/backend/core/client.py` |
| `{{VERSION}}` | string | Module version | `2.8.0` |
| `{{TIMESTAMP}}` | string | ISO 8601 timestamp | `2024-01-15T10:30:00Z` |
| `{{LANGUAGE}}` | string | Programming language | `python` or `typescript` |
| `{{FUNCTION_NAME}}` | string | Function name | `create_client` |
| `{{FUNCTION_SIGNATURE}}` | string | Full function signature | `def create_client(project_dir: str) -> ClaudeSDKClient` |
| `{{FUNCTION_DESCRIPTION}}` | string | Function docstring/JSDoc | `Creates a configured Claude SDK client` |
| `{{PARAM_NAME}}` | string | Parameter name | `project_dir` |
| `{{PARAM_TYPE}}` | string | Parameter type | `str` or `string` |
| `{{PARAM_REQUIRED}}` | boolean | Is parameter required | `Yes` or `No` |
| `{{PARAM_DEFAULT}}` | string | Default value | `None` or `N/A` |
| `{{RETURN_TYPE}}` | string | Return type | `ClaudeSDKClient` |
| `{{CLASS_NAME}}` | string | Class name | `GraphitiMemory` |
| `{{METHOD_NAME}}` | string | Method name | `get_context_for_session` |
| `{{METHOD_ACCESS}}` | string | Access modifier | `public` / `private` / `protected` |
| `{{IS_STATIC}}` | boolean | Is static method | `Yes` or `No` |
| `{{IS_ASYNC}}` | boolean | Is async method | `Yes` or `No` |
| `{{TYPE_NAME}}` | string | Type/interface name | `ComponentProps` |
| `{{TYPE_KIND}}` | string | Type category | `Interface` / `Type` / `Enum` |
| `{{LINE_NUMBER}}` | integer | Source line number | `42` |
| `{{SOURCE_URL}}` | string | Link to source code | `https://github.com/.../file.py#L42` |

---

**Document Information:**
- **Template Version:** 1.0.0
- **Compatible With:** Python 3.12+, TypeScript 5.0+, Node.js 18+
- **Last Updated:** {{TIMESTAMP}}
- **Automation Status:** Fully automated
- **Rendering Engines:** Mustache, Handlebars, Jinja2
