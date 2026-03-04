# File Templates Plugin

An integration plugin that provides MCP tools for creating files from customizable templates with variable substitution. Helps agents generate consistent boilerplate code for React components, Python modules, API endpoints, tests, and more.

## Overview

This plugin equips agents with the ability to create files from templates during builds, reducing repetitive boilerplate and enforcing consistency across your codebase. It includes built-in templates for common patterns and supports custom user-defined templates.

## What It Does

- **Built-in Templates**: Ready-to-use templates for common file types
  - React components (TypeScript)
  - Python modules with classes
  - TypeScript interfaces
  - Pytest test files
  - FastAPI endpoints
- **Custom Templates**: Load your own templates from a directory
- **Variable Substitution**: Dynamic content with case conversion
  - `{{VariableName}}` → Direct value
  - `{{variable-name}}` → Kebab-case
  - `{{variable_name}}` → Snake-case
- **MCP Tool Integration**: Three tools available to agents
  - `list_templates` - View available templates
  - `get_template_info` - Inspect template details
  - `create_from_template` - Generate files

## Features Demonstrated

### IntegrationPlugin Capabilities

- `create_mcp_tools()` - Provides three MCP tools for agents
- `on_load()` - Loads custom templates from configured directory
- `on_enable()` - Reports available template count
- `on_disable()` - Cleanup
- `on_unload()` - Clears custom templates

### MCP Tools

The plugin creates three tools that agents can use during builds:

1. **list_templates()** - Returns formatted list of all templates
2. **get_template_info(template_id)** - Shows template details and required variables
3. **create_from_template(template_id, file_path, variables)** - Creates a file from template

### Variable Substitution

Smart variable handling with automatic case conversion:
- `{{ComponentName}}` → `"MyButton"`
- `{{component-name}}` → `"my-button"` (kebab-case)
- `{{component_name}}` → `"my_button"` (snake-case)

Automatic variables included in all templates:
- `{{timestamp}}` → Current timestamp
- `{{date}}` → Current date
- `{{year}}` → Current year

## Installation

### From Directory

1. **Copy the plugin directory**:
   ```bash
   cp -r examples/plugins/file-templates ~/.auto-claude/plugins/user/
   ```

2. **(Optional) Configure custom templates directory** in `apps/backend/.env`:
   ```bash
   FILE_TEMPLATES_DIR=/path/to/your/templates
   ```

3. **Using the Electron UI**:
   - Open Auto Code desktop app
   - Navigate to **Plugins** (shortcut: `U`)
   - Click **Install Plugin**
   - Select **Directory** as installation source
   - Browse to `examples/plugins/file-templates`
   - Click **Install**

4. **Enable the plugin**:
   - Find `file-templates` in the plugins list
   - Click **Enable**

## Built-in Templates

### 1. React Component (`react-component`)

Creates a TypeScript React functional component.

**Required Variables:**
- `ComponentName` - Component name (e.g., "UserProfile")
- `author` - Author name

**Example Usage:**
```python
create_from_template(
    template_id="react-component",
    file_path="src/components/UserProfile.tsx",
    variables='{"ComponentName": "UserProfile", "author": "Jane Doe"}'
)
```

**Generated File:**
```tsx
import React from 'react';

interface UserProfileProps {
  // Add your props here
}

/**
 * UserProfile component
 *
 * @author Jane Doe
 * @created 2024-01-15 10:30:00
 */
export const UserProfile: React.FC<UserProfileProps> = (props) => {
  return (
    <div className="user-profile">
      <h1>UserProfile</h1>
    </div>
  );
};
```

### 2. Python Module (`python-module`)

Creates a Python module with class and docstrings.

**Required Variables:**
- `ModuleName` - Module name (e.g., "Authentication")
- `ClassName` - Class name (e.g., "AuthManager")
- `author` - Author name

**Example Usage:**
```python
create_from_template(
    template_id="python-module",
    file_path="src/auth.py",
    variables='{"ModuleName": "Authentication", "ClassName": "AuthManager", "author": "John Smith", "description": "Authentication and authorization manager"}'
)
```

### 3. TypeScript Interface (`typescript-interface`)

Creates a TypeScript interface with utility functions.

**Required Variables:**
- `InterfaceName` - Interface name (e.g., "User")
- `author` - Author name

**Example Usage:**
```python
create_from_template(
    template_id="typescript-interface",
    file_path="src/types/user.ts",
    variables='{"InterfaceName": "User", "author": "Jane Doe", "description": "User account information"}'
)
```

### 4. Pytest Test File (`pytest-test`)

Creates a pytest test file with fixtures and test methods.

**Required Variables:**
- `ModuleName` - Module being tested (e.g., "Authentication")
- `author` - Author name

**Example Usage:**
```python
create_from_template(
    template_id="pytest-test",
    file_path="tests/test_auth.py",
    variables='{"ModuleName": "Authentication", "author": "John Smith"}'
)
```

### 5. FastAPI Endpoint (`api-endpoint`)

Creates a FastAPI endpoint with request/response models and CRUD operations.

**Required Variables:**
- `ResourceName` - Resource name (e.g., "Product")
- `author` - Author name

**Example Usage:**
```python
create_from_template(
    template_id="api-endpoint",
    file_path="src/api/products.py",
    variables='{"ResourceName": "Product", "author": "Jane Doe"}'
)
```

**Generated File:**
```python
"""
Product API Endpoint

Author: Jane Doe
Created: 2024-01-15 10:30:00
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/product", tags=["product"])

class ProductRequest(BaseModel):
    """Request model for Product."""
    name: str
    description: str

class ProductResponse(BaseModel):
    """Response model for Product."""
    id: str
    name: str
    description: str
    created_at: str

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(request: ProductRequest) -> ProductResponse:
    """Create a new product."""
    # Implementation here
    ...
```

## Custom Templates

You can add your own templates by creating JSON files in a custom templates directory.

### Custom Template Format

```json
{
  "name": "My Custom Template",
  "description": "Description of what this template creates",
  "extension": ".js",
  "variables": ["ClassName", "author"],
  "template": "// {{ClassName}} - Created by {{author}}\n\nclass {{ClassName}} {\n  constructor() {\n    // Implementation\n  }\n}\n\nexport default {{ClassName}};"
}
```

### Setting Up Custom Templates

1. **Create a templates directory**:
   ```bash
   mkdir -p ~/.auto-claude/templates
   ```

2. **Add template files** (e.g., `vue-component.json`):
   ```json
   {
     "name": "Vue 3 Component",
     "description": "Vue 3 component with Composition API",
     "extension": ".vue",
     "variables": ["ComponentName", "author"],
     "template": "<template>\n  <div class=\"{{component-name}}\">\n    <h1>{{ComponentName}}</h1>\n  </div>\n</template>\n\n<script setup lang=\"ts\">\nimport { ref } from 'vue';\n\n/**\n * {{ComponentName}} component\n * @author {{author}}\n * @created {{timestamp}}\n */\n</script>\n\n<style scoped>\n.{{component-name}} {\n  /* Add your styles */\n}\n</style>"
   }
   ```

3. **Configure the plugin** in `apps/backend/.env`:
   ```bash
   FILE_TEMPLATES_DIR=~/.auto-claude/templates
   ```

4. **Restart and enable** the plugin

Your custom templates will now be available alongside built-in templates.

## Usage by Agents

Once enabled, agents can use these tools during builds:

### List Available Templates

```python
# Agent calls this to see what's available
list_templates()
```

**Output:**
```
Available File Templates:
========================================

• react-component (.tsx)
  React Functional Component
  React functional component with TypeScript

• python-module (.py)
  Python Module
  Python module with class and docstrings

• typescript-interface (.ts)
  TypeScript Interface
  TypeScript interface definition

• pytest-test (.py)
  Pytest Test File
  Python test file using pytest

• api-endpoint (.py)
  FastAPI Endpoint
  FastAPI endpoint with request/response models
```

### Get Template Details

```python
# Agent checks what variables are needed
get_template_info("react-component")
```

**Output:**
```
Template: react-component
========================================
Name: React Functional Component
Description: React functional component with TypeScript
Extension: .tsx

Required Variables:
  • ComponentName
  • author

Automatic Variables:
  • timestamp - Current timestamp
  • date - Current date
  • year - Current year

Note: Variables support auto-conversion:
  {{VarName}} → direct value
  {{var-name}} → kebab-case
  {{var_name}} → snake-case
```

### Create File from Template

```python
# Agent creates a file
create_from_template(
    template_id="react-component",
    file_path="src/components/LoginButton.tsx",
    variables='{"ComponentName": "LoginButton", "author": "Auto Code Agent"}'
)
```

**Output:**
```
Success: Created src/components/LoginButton.tsx from template 'react-component'
```

## Real-World Example

**Scenario:** Agent is implementing a feature that needs a new React component, API endpoint, and tests.

```python
# 1. Create React component
create_from_template(
    template_id="react-component",
    file_path="src/components/ProductCard.tsx",
    variables='{"ComponentName": "ProductCard", "author": "Auto Code"}'
)

# 2. Create API endpoint
create_from_template(
    template_id="api-endpoint",
    file_path="src/api/products.py",
    variables='{"ResourceName": "Product", "author": "Auto Code"}'
)

# 3. Create test file
create_from_template(
    template_id="pytest-test",
    file_path="tests/test_products.py",
    variables='{"ModuleName": "Products", "author": "Auto Code"}'
)
```

The agent now has consistent boilerplate for all three files and can focus on implementing the business logic.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FILE_TEMPLATES_DIR` | Directory containing custom template JSON files | None (built-in only) |

### Custom Template Location

```bash
# User templates (recommended)
FILE_TEMPLATES_DIR=~/.auto-claude/templates

# Project-specific templates
FILE_TEMPLATES_DIR=./templates

# Shared team templates
FILE_TEMPLATES_DIR=/shared/auto-code-templates
```

## Permissions

This plugin requires:

- **read_files**: To load custom template files from disk
- **write_files**: To create files from templates in the project directory

## Troubleshooting

### Template not found

- Check template ID spelling: `list_templates()` to see available
- Verify custom templates directory exists and has `.json` files
- Restart plugin after adding custom templates

### Missing required variables error

```
Error: Missing required variables: ComponentName, author
```

- Use `get_template_info(template_id)` to see required variables
- Ensure variables JSON is valid: `'{"key": "value"}'`
- All required variables must be provided

### File creation fails

```
Error: Failed to create file: Permission denied
```

- Check file path is relative to project directory
- Verify parent directories exist (plugin creates them automatically)
- Ensure write permissions on target location

### Variable substitution not working

- Use exact variable names from template (case-sensitive)
- For auto-conversions, use the naming pattern:
  - `{{VarName}}` for direct value
  - `{{var-name}}` for kebab-case
  - `{{var_name}}` for snake-case

### Custom templates not loading

- Verify `FILE_TEMPLATES_DIR` is set correctly
- Check template JSON files are valid JSON
- Look for error messages in logs on plugin load
- Ensure template files have `.json` extension

## Extending Templates

### Adding More Variables

Templates can include any variables you need:

```json
{
  "variables": ["ComponentName", "author", "license", "version", "description"],
  "template": "..."
}
```

### Using Conditional Content

While templates don't support conditionals directly, you can:
1. Create multiple template variants
2. Use placeholder comments for agents to fill
3. Implement logic in custom template post-processing

### Template Organization

Organize custom templates by category:

```
~/.auto-claude/templates/
├── react/
│   ├── functional-component.json
│   ├── class-component.json
│   └── hook.json
├── python/
│   ├── class-module.json
│   ├── function-module.json
│   └── test-module.json
└── api/
    ├── fastapi-endpoint.json
    ├── flask-route.json
    └── graphql-resolver.json
```

Note: Plugin loads from a single directory, not recursively.

## Learn More

- [Integration Plugin Development Guide](../../../guides/plugins/integration-plugins.md)
- [MCP Tools Documentation](../../../docs/mcp-tools.md)
- [Plugin SDK Reference](../../../apps/backend/plugins/sdk/integration.py)
- [Template Variables Guide](../../../guides/template-variables.md)

## License

MIT - See LICENSE file for details
