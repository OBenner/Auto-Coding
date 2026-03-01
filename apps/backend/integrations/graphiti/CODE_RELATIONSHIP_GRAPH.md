# Code Relationship Graph

Advanced semantic analysis and querying of code relationships using Graphiti knowledge graphs. Provides deep understanding of function calls, dependencies, inheritance, and architectural patterns.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Core Components](#core-components)
- [API Reference](#api-reference)
- [Use Cases](#use-cases)
- [Advanced Usage](#advanced-usage)
- [Integration with Graphiti Memory](#integration-with-graphiti-memory)
- [Performance Considerations](#performance-considerations)
- [Examples](#examples)

## Overview

The Code Relationship Graph provides **accurate, semantic understanding** of code structure and relationships. Instead of fabricating API relationships like competitors, Auto Claude builds actual knowledge graphs of how your code works.

### What It Does

- **Extracts relationships** from Python source code using AST parsing
- **Stores relationships** in Graphiti's knowledge graph for semantic search
- **Queries relationships** using natural language ("what uses this function?")
- **Impact analysis** - shows what breaks when you change code
- **Semantic search** - finds code by purpose, not just by name
- **Coupling analysis** - identifies tight vs loose coupling

### Key Benefits

✅ **Accurate** - Uses AST parsing, not guessing
✅ **Semantic** - Understands code purpose and intent
✅ **Queryable** - Natural language queries against knowledge graph
✅ **Impact-aware** - Knows what breaks when you change code
✅ **Cross-session** - Builds knowledge over time with Graphiti

## Architecture

The Code Relationship Graph consists of three main components:

```
┌─────────────────────────────────────────────────────────────┐
│                    Code Relationship Graph                  │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Extractor   │───▶│   Queries    │───▶│   Analyzer   │
│              │    │              │    │              │
│ AST Parser   │    │ Storage &    │    │ Impact &     │
│ Finds:       │    │ Retrieval    │    │ Coupling     │
│ • Calls      │    │              │    │ Analysis     │
│ • Imports    │    │ Natural      │    │              │
│ • Inheritance│    │ Language     │    │ Dependency   │
│ • Entities   │    │ Queries      │    │ Traversal    │
└──────────────┘    └──────────────┘    └──────────────┘
        │                    │                    │
        └────────────────────┴────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Graphiti Memory │
                    │  (Knowledge Graph)│
                    └──────────────────┘
```

### 1. CodeRelationshipExtractor

**Purpose:** Extract semantic relationships from Python source code

**Capabilities:**
- Function call detection (who calls whom)
- Import dependency tracking
- Class inheritance hierarchies
- Entity identification (functions, classes, methods)

**Technology:** AST (Abstract Syntax Tree) parsing

### 2. CodeRelationshipQueries

**Purpose:** Store and query code relationships in Graphiti

**Capabilities:**
- Store relationships as Graphiti episodes
- Find callers/callees of functions
- Find parent/child classes
- Natural language relationship queries
- Semantic search by purpose

**Technology:** Graphiti semantic search

### 3. ImpactAnalyzer

**Purpose:** Analyze impact of code changes

**Capabilities:**
- Calculate impact scores for changes
- Traverse dependency graphs recursively
- Identify tight vs loose coupling
- Analyze relationship strength

**Technology:** Graph traversal algorithms

## Quick Start

### Step 1: Extract Relationships from Code

```python
from integrations.graphiti.code_relationship_extractor import CodeRelationshipExtractor

# Create extractor
extractor = CodeRelationshipExtractor()

# Analyze a Python file
result = extractor.analyze_file("path/to/your_module.py")

# See what was found
print(f"Found {result['total_relationships']} relationships:")
print(f"  - {len(result['calls'])} function calls")
print(f"  - {len(result['imports'])} imports")
print(f"  - {len(result['inheritance'])} inheritance relationships")
```

### Step 2: Store Relationships in Graphiti

```python
from integrations.graphiti.queries_pkg import GraphitiMemory

# Initialize Graphiti memory
memory = GraphitiMemory(spec_dir="/path/to/spec", project_dir="/path/to/project")

# Store all relationships from a file
await memory.code_relationships.add_file_relationships(
    file_path="path/to/your_module.py",
    relationships=result
)
```

### Step 3: Query Relationships

```python
# Find all functions that call a specific function
callers = await memory.code_relationships.find_callers("login")
print(f"Functions calling login(): {[c['caller'] for c in callers]}")

# Find what a function calls
callees = await memory.code_relationships.find_callees("process_payment")
print(f"Functions called by process_payment(): {[c['callee'] for c in callees]}")

# Natural language query
results = await memory.code_relationships.query_relationships(
    query="show me all components using UserProfile"
)
```

### Step 4: Analyze Impact

```python
from integrations.graphiti.impact_analyzer import ImpactAnalyzer

# Create analyzer
analyzer = ImpactAnalyzer(
    client=memory.client,
    group_id=memory.group_id,
    spec_context_id=memory.spec_context_id,
    project_dir=memory.project_dir
)

# Calculate impact of changing a function
impact = await analyzer.calculate_impact(
    entity_name="validate_user",
    entity_type="function",
    max_depth=3
)

print(f"Impact score: {impact['impact_score']}")
print(f"Affected entities: {len(impact['affected_entities'])}")
for entity in impact['affected_entities']:
    print(f"  - {entity['name']} ({entity['type']}) at depth {entity['depth']}")
```

## Core Components

### CodeRelationshipExtractor

Extracts relationships from Python source code using AST parsing.

**Key Methods:**

- `analyze_file(file_path)` - Analyze a Python file
- `analyze_source(source)` - Analyze source code string

**Returns:**

```python
{
    "file_path": "path/to/file.py",
    "calls": [
        {
            "caller": "login",
            "callee": "validate_credentials",
            "lineno": 45,
            "call_type": "function",  # or "method"
            "module": "auth"  # if imported
        }
    ],
    "imports": [
        {
            "module": "database",
            "names": ["User", "Database"],
            "alias": None,
            "lineno": 3,
            "is_from_import": True
        }
    ],
    "inheritance": [
        {
            "child": "User",
            "parent": "BaseModel",
            "lineno": 10,
            "parent_module": "database"
        }
    ],
    "total_relationships": 15,
    "entities": ["login", "validate_credentials", "User", ...]
}
```

### CodeRelationshipQueries

Stores and queries code relationships in Graphiti knowledge graph.

**Storage Methods:**

- `add_function_call(caller, callee, file_path, lineno, ...)` - Store a function call
- `add_import_dependency(importing_file, module, ...)` - Store an import
- `add_inheritance_relationship(child, parent, ...)` - Store inheritance
- `add_file_relationships(file_path, relationships)` - Bulk store all relationships
- `add_code_purpose(entity_name, entity_type, purpose, ...)` - Store semantic purpose

**Query Methods:**

- `find_callers(function_name, limit)` - Find who calls this function
- `find_callees(function_name, limit)` - Find what this function calls
- `find_parent_classes(class_name, limit)` - Find parent classes
- `find_child_classes(class_name, limit)` - Find child classes
- `get_inheritance_chain(class_name, max_depth)` - Get full inheritance hierarchy
- `query_relationships(query, limit, include_types)` - Natural language query
- `search_by_purpose(query, limit, entity_type)` - Semantic search by purpose

### ImpactAnalyzer

Analyzes impact of code changes and relationship strength.

**Analysis Methods:**

- `calculate_impact(entity_name, entity_type, max_depth)` - Calculate change impact
- `calculate_coupling_score(entity_name, entity_type)` - Analyze coupling strength

**Impact Result:**

```python
{
    "affected_entities": [
        {
            "name": "handle_login",
            "type": "function",
            "file_path": "api.py",
            "lineno": 12,
            "depth": 1  # How far from the changed entity
        }
    ],
    "impact_score": 45.5,  # 0-100, higher = more impact
    "depth_analysis": {
        "depth_1": ["handle_login"],
        "depth_2": ["process_request", "api_endpoint"]
    }
}
```

**Coupling Result:**

```python
{
    "coupling_score": 65.0,  # 0-100, higher = tighter coupling
    "relationship_strength": "tight",  # "tight", "moderate", or "loose"
    "tight_coupling_indicators": {
        "same_file_callers": 3,
        "cross_file_callers": 1,
        "bidirectional_dependencies": 1,
        "total_references": 5
    },
    "relationships": [...]
}
```

## API Reference

### CodeRelationshipExtractor

#### `analyze_file(file_path: str | Path) -> dict`

Analyze a Python source file to extract relationships.

**Args:**
- `file_path` - Path to Python file to analyze

**Returns:**
- Dictionary with `calls`, `imports`, `inheritance`, `total_relationships`, `entities`

**Raises:**
- `FileNotFoundError` - If file doesn't exist
- `ValueError` - If file can't be parsed

**Example:**

```python
extractor = CodeRelationshipExtractor()
result = extractor.analyze_file("auth.py")
```

#### `analyze_source(source: str) -> dict`

Analyze Python source code string to extract relationships.

**Args:**
- `source` - Python source code as string

**Returns:**
- Same as `analyze_file()`

**Example:**

```python
source = """
def login(username, password):
    return validate_credentials(username, password)
"""
result = extractor.analyze_source(source)
```

### CodeRelationshipQueries

#### `add_function_call(caller, callee, file_path, lineno, call_type, module) -> bool`

Store a function call relationship.

**Args:**
- `caller` (str) - Name of the calling function/method
- `callee` (str) - Name of the called function/method
- `file_path` (str) - Path to the file containing the call
- `lineno` (int) - Line number where call occurs
- `call_type` (str) - Type of call ("function", "method", "builtin")
- `module` (str | None) - Module the callee belongs to (if imported)

**Returns:**
- `True` if saved successfully, `False` otherwise

**Example:**

```python
await queries.add_function_call(
    caller="login",
    callee="validate_credentials",
    file_path="auth.py",
    lineno=45,
    call_type="function"
)
```

#### `add_file_relationships(file_path, relationships) -> bool`

Store all relationships from a single file analysis (bulk operation).

**Args:**
- `file_path` (str) - Path to the analyzed file
- `relationships` (dict) - Result from `CodeRelationshipExtractor.analyze_file()`

**Returns:**
- `True` if all relationships saved successfully

**Example:**

```python
extractor = CodeRelationshipExtractor()
result = extractor.analyze_file("auth.py")

await queries.add_file_relationships(
    file_path="auth.py",
    relationships=result
)
```

#### `find_callers(function_name, limit=50) -> list[dict]`

Find all functions that call the specified function.

**Args:**
- `function_name` (str) - Name of the function to find callers for
- `limit` (int) - Maximum number of results to return (default: 50)

**Returns:**
- List of caller information with `caller`, `file_path`, `lineno`, `call_type`, `module`

**Example:**

```python
callers = await queries.find_callers("validate_credentials")
for caller in callers:
    print(f"{caller['caller']} calls validate_credentials at {caller['file_path']}:{caller['lineno']}")
```

#### `find_callees(function_name, limit=50) -> list[dict]`

Find all functions that the specified function calls.

**Args:**
- `function_name` (str) - Name of the function to find callees for
- `limit` (int) - Maximum number of results to return (default: 50)

**Returns:**
- List of callee information with `callee`, `file_path`, `lineno`, `call_type`, `module`

**Example:**

```python
callees = await queries.find_callees("login")
print(f"login() calls: {[c['callee'] for c in callees]}")
```

#### `get_inheritance_chain(class_name, max_depth=10) -> list[str]`

Get the full inheritance chain from a class to its root ancestors.

**Args:**
- `class_name` (str) - Name of the class to get inheritance chain for
- `max_depth` (int) - Maximum depth to traverse (default: 10)

**Returns:**
- List of class names in inheritance order `[ChildClass, Parent, GrandParent, ...]`

**Example:**

```python
chain = await queries.get_inheritance_chain("User")
print(f"Inheritance: {' -> '.join(chain)}")
# Output: User -> BaseModel -> object
```

#### `query_relationships(query, limit=20, include_types=None) -> list[dict]`

Query code relationships using natural language.

**Args:**
- `query` (str) - Natural language query describing the relationships to find
- `limit` (int) - Maximum number of results to return (default: 20)
- `include_types` (list[str] | None) - Optional list of relationship types to include
  (`["function_call", "import", "inheritance"]`)

**Returns:**
- List of relationship information with `type`, entities, `file_path`, metadata, and `score`

**Example:**

```python
# Find all components using UserProfile
results = await queries.query_relationships(
    query="show me all components using UserProfile"
)

# Filter by type
calls_only = await queries.query_relationships(
    query="what calls the login function",
    include_types=["function_call"]
)
```

#### `add_code_purpose(entity_name, entity_type, purpose, file_path, lineno, docstring, tags) -> bool`

Store semantic information about what code does (its purpose).

**Args:**
- `entity_name` (str) - Name of the code entity (function, class, module)
- `entity_type` (str) - Type of entity ("function", "class", "module", "method")
- `purpose` (str) - Human-readable description of what the code does
- `file_path` (str) - Path to file containing the entity
- `lineno` (int) - Line number where entity is defined (default: 0)
- `docstring` (str | None) - Optional docstring content
- `tags` (list[str] | None) - Optional semantic tags (e.g., `["authentication", "api"]`)

**Returns:**
- `True` if saved successfully

**Example:**

```python
await queries.add_code_purpose(
    entity_name="validate_credentials",
    entity_type="function",
    purpose="Validate user credentials against database",
    file_path="auth.py",
    lineno=20,
    tags=["authentication", "validation", "security"]
)
```

#### `search_by_purpose(query, limit=20, entity_type=None) -> list[dict]`

Search for code entities by their purpose using natural language.

**Args:**
- `query` (str) - Natural language query describing the purpose to search for
- `limit` (int) - Maximum number of results to return (default: 20)
- `entity_type` (str | None) - Optional filter for entity type ("function", "class", etc.)

**Returns:**
- List of entity information with `entity_name`, `entity_type`, `purpose`, `file_path`, `tags`, `score`

**Example:**

```python
# Find authentication functions
auth_funcs = await queries.search_by_purpose(
    query="authentication functions",
    entity_type="function"
)

# Find payment processing code
payment_code = await queries.search_by_purpose(
    query="payment processing"
)
```

### ImpactAnalyzer

#### `calculate_impact(entity_name, entity_type="function", max_depth=3) -> dict`

Calculate the impact of changing a code entity.

**Args:**
- `entity_name` (str) - Name of the entity (function, class, etc.)
- `entity_type` (str) - Type of entity ("function", "class") - default: "function"
- `max_depth` (int) - Maximum depth to traverse (default: 3)

**Returns:**
- Dictionary with `affected_entities`, `impact_score`, `depth_analysis`

**Example:**

```python
impact = await analyzer.calculate_impact(
    entity_name="BaseModel",
    entity_type="class",
    max_depth=3
)

print(f"Impact score: {impact['impact_score']}")
print(f"This change would affect {len(impact['affected_entities'])} entities")
```

#### `calculate_coupling_score(entity_name, entity_type="function") -> dict`

Calculate relationship strength score to identify tight vs loose coupling.

**Args:**
- `entity_name` (str) - Name of the entity to analyze
- `entity_type` (str) - Type of entity ("function", "class") - default: "function"

**Returns:**
- Dictionary with `coupling_score`, `relationship_strength`, `tight_coupling_indicators`, `relationships`

**Example:**

```python
coupling = await analyzer.calculate_coupling_score(
    entity_name="validate_credentials",
    entity_type="function"
)

if coupling['relationship_strength'] == 'tight':
    print(f"⚠️ Tight coupling detected (score: {coupling['coupling_score']})")
    print(f"Same-file callers: {coupling['tight_coupling_indicators']['same_file_callers']}")
```

## Use Cases

### Use Case 1: "What Uses This Function?"

**Problem:** You want to refactor a function but need to know what calls it.

**Solution:**

```python
# Find all callers
callers = await memory.code_relationships.find_callers("process_payment")

print(f"Found {len(callers)} functions calling process_payment():")
for caller in callers:
    print(f"  - {caller['caller']} at {caller['file_path']}:{caller['lineno']}")
```

### Use Case 2: Impact Analysis Before Refactoring

**Problem:** You want to change a class but need to know what would break.

**Solution:**

```python
# Calculate impact
impact = await analyzer.calculate_impact(
    entity_name="BaseModel",
    entity_type="class",
    max_depth=3
)

if impact['impact_score'] > 50:
    print(f"⚠️ HIGH IMPACT: This change affects {len(impact['affected_entities'])} entities")

    # Show what would be affected
    for entity in impact['affected_entities']:
        depth_indicator = "  " * entity['depth']
        print(f"{depth_indicator}└─ {entity['name']} ({entity['type']})")
else:
    print(f"✓ LOW IMPACT: Safe to refactor (score: {impact['impact_score']})")
```

### Use Case 3: Understanding Architectural Layers

**Problem:** You want to visualize dependencies and architectural layers.

**Solution:**

```python
# Get all relationships for a module
relationships = await memory.code_relationships.query_relationships(
    query="relationships in auth module"
)

# Organize by type
layers = {
    "API Layer": [],
    "Service Layer": [],
    "Data Layer": []
}

for rel in relationships:
    if rel['type'] == 'function_call':
        # Analyze file paths to determine layer
        file = rel.get('file_path', '')
        if 'api' in file:
            layers["API Layer"].append(rel)
        elif 'service' in file or 'auth' in file:
            layers["Service Layer"].append(rel)
        elif 'database' in file or 'model' in file:
            layers["Data Layer"].append(rel)

# Display layers
for layer, rels in layers.items():
    print(f"\n{layer}: {len(rels)} relationships")
```

### Use Case 4: Finding Code by Purpose, Not Name

**Problem:** You need to find "authentication logic" but don't know the function names.

**Solution:**

```python
# Search by purpose
auth_entities = await memory.code_relationships.search_by_purpose(
    query="authentication and user validation",
    limit=20
)

print(f"Found {len(auth_entities)} authentication-related entities:")
for entity in auth_entities:
    print(f"  - {entity['entity_name']} ({entity['entity_type']})")
    print(f"    Purpose: {entity['purpose']}")
    print(f"    Tags: {', '.join(entity['tags'])}")
    print()
```

### Use Case 5: Detecting Tight Coupling

**Problem:** You want to identify tightly coupled code that's hard to test.

**Solution:**

```python
# Analyze coupling for all key functions
key_functions = ["login", "validate_credentials", "create_session"]

for func_name in key_functions:
    coupling = await analyzer.calculate_coupling_score(
        entity_name=func_name,
        entity_type="function"
    )

    strength = coupling['relationship_strength']
    score = coupling['coupling_score']

    if strength == 'tight':
        print(f"⚠️ {func_name}: TIGHT COUPLING (score: {score})")
        indicators = coupling['tight_coupling_indicators']
        print(f"   Same-file: {indicators['same_file_callers']}")
        print(f"   Bidirectional: {indicators['bidirectional_dependencies']}")
    elif strength == 'moderate':
        print(f"⚡ {func_name}: Moderate coupling (score: {score})")
    else:
        print(f"✓ {func_name}: Loose coupling (score: {score})")
```

## Advanced Usage

### Building a Complete Codebase Graph

```python
from pathlib import Path
from integrations.graphiti.code_relationship_extractor import CodeRelationshipExtractor
from integrations.graphiti.queries_pkg import GraphitiMemory

# Initialize
extractor = CodeRelationshipExtractor()
memory = GraphitiMemory(spec_dir="/path/to/spec", project_dir="/path/to/project")

# Recursively analyze all Python files
project_path = Path("/path/to/project")

for py_file in project_path.rglob("*.py"):
    if ".venv" in str(py_file) or "node_modules" in str(py_file):
        continue  # Skip virtual environments

    try:
        print(f"Analyzing {py_file.relative_to(project_path)}...")

        # Extract relationships
        result = extractor.analyze_file(py_file)

        # Store in Graphiti
        await memory.code_relationships.add_file_relationships(
            file_path=str(py_file),
            relationships=result
        )

        # Optionally store semantic purposes
        for entity in result['entities']:
            if not entity.startswith('_'):  # Skip private entities
                await memory.code_relationships.add_code_purpose(
                    entity_name=entity,
                    entity_type="function",  # or detect from AST
                    purpose=f"Code entity from {py_file.name}",
                    file_path=str(py_file)
                )

        print(f"  ✓ Stored {result['total_relationships']} relationships")

    except Exception as e:
        print(f"  ✗ Error: {e}")

print("\n✓ Codebase graph complete!")
```

### Recursive Dependency Analysis

```python
async def analyze_full_dependency_tree(function_name, max_depth=5):
    """
    Build a complete dependency tree showing all transitive dependencies.
    """
    visited = set()
    dependency_tree = {}

    async def traverse(func, depth):
        if depth >= max_depth or func in visited:
            return

        visited.add(func)

        # Find what this function calls
        callees = await memory.code_relationships.find_callees(func)

        if callees:
            dependency_tree[func] = {
                'depth': depth,
                'callees': [c['callee'] for c in callees],
                'files': [c['file_path'] for c in callees]
            }

            # Recursively analyze each callee
            for callee in callees:
                await traverse(callee['callee'], depth + 1)

    await traverse(function_name, 0)
    return dependency_tree

# Use it
tree = await analyze_full_dependency_tree("login")

# Print the tree
for func, info in tree.items():
    indent = "  " * info['depth']
    print(f"{indent}{func} calls: {', '.join(info['callees'])}")
```

### Cross-Module Dependency Detection

```python
async def find_cross_module_dependencies(module_name):
    """
    Find all external modules that a module depends on.
    """
    # Find all imports in the module
    results = await memory.code_relationships.query_relationships(
        query=f"imports in {module_name}",
        include_types=["import"]
    )

    external_deps = {}

    for rel in results:
        if rel['type'] == 'import':
            importing_file = rel['importing_file']
            module = rel['module']

            if module_name in importing_file:
                if module not in external_deps:
                    external_deps[module] = []
                external_deps[module].append(importing_file)

    print(f"\nExternal dependencies for {module_name}:")
    for module, files in external_deps.items():
        print(f"  - {module} (used in {len(files)} files)")

    return external_deps

# Use it
deps = await find_cross_module_dependencies("auth")
```

### Identifying Circular Dependencies

```python
async def detect_circular_dependencies(max_depth=5):
    """
    Detect circular dependencies in function call chains.
    """
    circular = []

    async def check_circular(func, path, visited_in_path):
        if func in visited_in_path:
            # Found a cycle
            cycle_start = visited_in_path.index(func)
            cycle = path[cycle_start:] + [func]
            circular.append(cycle)
            return

        if len(path) >= max_depth:
            return

        callees = await memory.code_relationships.find_callees(func)

        for callee in callees:
            callee_name = callee['callee']
            await check_circular(
                callee_name,
                path + [func],
                visited_in_path + [func]
            )

    # Start from all functions
    # (simplified - in practice, you'd get all functions from the graph)
    starting_functions = ["login", "validate_credentials", "handle_request"]

    for func in starting_functions:
        await check_circular(func, [], [])

    if circular:
        print(f"⚠️ Found {len(circular)} circular dependencies:")
        for cycle in circular:
            print(f"  {' -> '.join(cycle)}")
    else:
        print("✓ No circular dependencies found")

    return circular
```

## Integration with Graphiti Memory

The Code Relationship Graph is fully integrated with Graphiti Memory, allowing you to:

### Access via GraphitiMemory

```python
from integrations.graphiti.queries_pkg import GraphitiMemory

memory = GraphitiMemory(spec_dir="/path/to/spec", project_dir="/path/to/project")

# Access code relationships
await memory.code_relationships.find_callers("login")

# Access impact analyzer
from integrations.graphiti.impact_analyzer import ImpactAnalyzer

analyzer = ImpactAnalyzer(
    client=memory.client,
    group_id=memory.group_id,
    spec_context_id=memory.spec_context_id,
    project_dir=memory.project_dir
)
```

### Combine with Other Graphiti Features

```python
# Store session insight about a code relationship
memory.add_session_insight(
    f"The login() function has tight coupling with validate_credentials() "
    f"(same file, bidirectional dependency)"
)

# Get context that includes code relationships
context = memory.get_context_for_session(
    "Refactoring the authentication system"
)
# This will include relevant code relationships from the graph
```

### Cross-Session Knowledge

Code relationships are stored in Graphiti's persistent knowledge graph, so they're available across sessions:

```python
# Session 1: Analyze and store
result = extractor.analyze_file("auth.py")
await memory.code_relationships.add_file_relationships("auth.py", result)

# Session 2 (different day): Query the same data
callers = await memory.code_relationships.find_callers("login")
# Data is still there!
```

## Performance Considerations

### Batch Operations

Use bulk operations when possible:

```python
# ✓ GOOD - Bulk operation
await memory.code_relationships.add_file_relationships(
    file_path="auth.py",
    relationships=result  # All relationships at once
)

# ✗ AVOID - Individual operations
for call in result['calls']:
    await memory.code_relationships.add_function_call(...)
```

### Limit Results

Always specify reasonable limits for queries:

```python
# ✓ GOOD - Limited results
callers = await memory.code_relationships.find_callers("login", limit=50)

# ⚠️ CAREFUL - Could return thousands
callers = await memory.code_relationships.find_callers("login", limit=10000)
```

### Depth Control

Control traversal depth in impact analysis:

```python
# ✓ GOOD - Reasonable depth
impact = await analyzer.calculate_impact("login", max_depth=3)

# ⚠️ CAREFUL - Deep traversal can be slow
impact = await analyzer.calculate_impact("login", max_depth=10)
```

### Caching Strategy

Consider caching frequently accessed relationships:

```python
class CachedCodeRelationships:
    def __init__(self, memory):
        self.memory = memory
        self._caller_cache = {}

    async def get_callers(self, func_name):
        if func_name not in self._caller_cache:
            self._caller_cache[func_name] = \
                await self.memory.code_relationships.find_callers(func_name)
        return self._caller_cache[func_name]
```

## Examples

### Example 1: Full E2E Workflow

```python
#!/usr/bin/env python3
"""
Complete end-to-end example: Analyze a codebase and query relationships.
"""
import asyncio
from pathlib import Path
from integrations.graphiti.code_relationship_extractor import CodeRelationshipExtractor
from integrations.graphiti.queries_pkg import GraphitiMemory
from integrations.graphiti.impact_analyzer import ImpactAnalyzer

async def main():
    # Setup
    extractor = CodeRelationshipExtractor()
    memory = GraphitiMemory(spec_dir=".auto-claude/specs/001", project_dir=".")

    # Step 1: Analyze files
    print("=== Analyzing codebase ===")
    for py_file in Path("src").rglob("*.py"):
        result = extractor.analyze_file(py_file)
        await memory.code_relationships.add_file_relationships(
            file_path=str(py_file),
            relationships=result
        )
        print(f"✓ {py_file}: {result['total_relationships']} relationships")

    # Step 2: Query relationships
    print("\n=== Finding function callers ===")
    callers = await memory.code_relationships.find_callers("process_request")
    for caller in callers:
        print(f"  {caller['caller']} -> process_request ({caller['file_path']})")

    # Step 3: Impact analysis
    print("\n=== Impact analysis ===")
    analyzer = ImpactAnalyzer(
        client=memory.client,
        group_id=memory.group_id,
        spec_context_id=memory.spec_context_id,
        project_dir=Path(".")
    )

    impact = await analyzer.calculate_impact("BaseModel", "class", max_depth=3)
    print(f"Impact score: {impact['impact_score']}")
    print(f"Affected: {[e['name'] for e in impact['affected_entities']]}")

    # Step 4: Semantic search
    print("\n=== Semantic search ===")
    entities = await memory.code_relationships.search_by_purpose(
        query="authentication and authorization",
        limit=10
    )
    for entity in entities:
        print(f"  {entity['entity_name']}: {entity['purpose']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Example 2: Dependency Visualization

```python
async def visualize_dependencies(function_name, max_depth=3):
    """
    Create a tree visualization of function dependencies.
    """
    memory = GraphitiMemory(spec_dir=".auto-claude/specs/001", project_dir=".")

    async def build_tree(func, depth, prefix=""):
        if depth >= max_depth:
            return

        callees = await memory.code_relationships.find_callees(func)

        for i, callee in enumerate(callees):
            is_last = (i == len(callees) - 1)
            connector = "└─" if is_last else "├─"
            extension = "  " if is_last else "│ "

            callee_name = callee['callee']
            print(f"{prefix}{connector} {callee_name}")

            # Recurse
            await build_tree(callee_name, depth + 1, prefix + extension)

    print(f"{function_name}")
    await build_tree(function_name, 0)

# Usage
await visualize_dependencies("login")

# Output:
# login
# ├─ validate_credentials
# │ ├─ find_user
# │ └─ check_password
# └─ create_session
#   ├─ generate_token
#   └─ save_session
```

### Example 3: Refactoring Safety Check

```python
async def check_refactoring_safety(entity_name, entity_type="function"):
    """
    Analyze whether it's safe to refactor an entity.
    """
    memory = GraphitiMemory(spec_dir=".auto-claude/specs/001", project_dir=".")
    analyzer = ImpactAnalyzer(
        client=memory.client,
        group_id=memory.group_id,
        spec_context_id=memory.spec_context_id,
        project_dir=Path(".")
    )

    print(f"\n=== Refactoring Safety Check: {entity_name} ===\n")

    # Check impact
    impact = await analyzer.calculate_impact(entity_name, entity_type, max_depth=3)

    # Check coupling
    coupling = await analyzer.calculate_coupling_score(entity_name, entity_type)

    # Analyze results
    safety_score = 100
    warnings = []

    if impact['impact_score'] > 50:
        safety_score -= 30
        warnings.append(f"HIGH IMPACT: {len(impact['affected_entities'])} entities affected")

    if coupling['relationship_strength'] == 'tight':
        safety_score -= 40
        warnings.append(f"TIGHT COUPLING: score {coupling['coupling_score']}")

    if coupling['tight_coupling_indicators']['bidirectional_dependencies'] > 0:
        safety_score -= 20
        warnings.append("CIRCULAR DEPENDENCIES detected")

    # Print results
    if safety_score >= 70:
        print(f"✅ SAFE TO REFACTOR (safety score: {safety_score}/100)")
    elif safety_score >= 40:
        print(f"⚠️  PROCEED WITH CAUTION (safety score: {safety_score}/100)")
    else:
        print(f"🛑 HIGH RISK (safety score: {safety_score}/100)")

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  - {warning}")

    print(f"\nImpact Details:")
    print(f"  - Impact score: {impact['impact_score']}")
    print(f"  - Affected entities: {len(impact['affected_entities'])}")
    print(f"  - Coupling: {coupling['relationship_strength']} ({coupling['coupling_score']})")

    return safety_score

# Usage
await check_refactoring_safety("BaseModel", "class")
```

## Summary

The Code Relationship Graph provides:

✅ **Accurate analysis** using AST parsing
✅ **Semantic storage** in Graphiti knowledge graph
✅ **Natural language queries** for finding relationships
✅ **Impact analysis** for safe refactoring
✅ **Coupling detection** for code quality
✅ **Purpose-based search** for finding code by intent

Use it to understand your codebase deeply, make informed refactoring decisions, and build better software with Auto Claude.

---

**Next Steps:**

1. See `test_code_graph_integration.py` for complete working examples
2. Check `code_relationship_extractor.py` for AST parsing details
3. Review `queries_pkg/code_relationships.py` for storage/query implementation
4. Explore `impact_analyzer.py` for impact analysis algorithms
