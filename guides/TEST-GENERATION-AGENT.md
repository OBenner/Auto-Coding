# Automated Test Generation Agent

The Automated Test Generation Agent analyzes code and generates comprehensive test suites with high coverage. It extends the existing QA loop with specialized capabilities for unit tests, integration tests, fixture generation, and coverage enforcement.

## Overview

The test generation system consists of four key components:

1. **Edge-Case Detection** — AST-based analysis to identify error handling, boundary conditions, type validation, and assertions in source code
2. **Fixture Generator** — Creates reusable pytest fixtures with validation and organized placement across `conftest.py` and fixture modules
3. **Integration Test Generator** — Generates tests for API endpoints, services, database operations, and external dependencies
4. **Coverage Enforcement** — Enforces an 80% minimum coverage threshold with detailed gap analysis and prioritized recommendations

## Components

### Edge-Case Detection

**Module:** `apps/backend/agents/test_generator.py`

Analyzes Python source code via AST to detect patterns that should have corresponding test cases:

| Pattern Type | Detection Method | Example |
|---|---|---|
| Error Handling | `try/except` blocks | `except ValueError as e:` |
| Boundary Conditions | Comparisons with `None`, `0`, `len()` | `if x is None`, `if len(items) == 0` |
| Type Validation | `isinstance()` calls | `isinstance(val, str)` |
| Error Raising | `raise` statements | `raise ValueError("...")` |
| Assertions | `assert` statements | `assert result is not None` |

**Usage:**

Edge-case detection runs automatically during test generation. Results are passed to the test generator agent to ensure generated tests cover error paths and boundary conditions.

```python
from agents.test_generator import detect_edge_cases_from_analysis

edge_cases = detect_edge_cases_from_analysis(analysis_results, project_dir)
# Returns list of dicts with type, pattern, lineno, description, file
```

### Fixture Generator

**Module:** `apps/backend/agents/fixture_generator.py`
**Prompt:** `apps/backend/prompts/fixture_generator.md`

Generates pytest fixtures based on code analysis results. The agent creates:

- **Simple data fixtures** — Basic test data instances
- **Factory fixtures** — Customizable test instance creation
- **Mock fixtures** — Mocks for external dependencies (APIs, databases, file system)
- **Parametrized fixtures** — Support for multiple test scenarios
- **Setup/teardown fixtures** — Test isolation and cleanup

**File organization:**

| Location | Purpose |
|---|---|
| `tests/conftest.py` | Shared fixtures used across test files |
| `tests/fixtures/<category>.py` | Organized fixture sets by domain |
| `tests/test_<module>.py` | Test-specific fixtures |

**Usage:**

```python
from agents.fixture_generator import generate_fixtures

result = await generate_fixtures(
    project_dir=project_dir,
    spec_dir=spec_dir,
    analysis_results=analysis_results,
    model="claude-sonnet-4-5-20250929",
)
# result: {"generated_files": [...], "success": bool, "error": str|None, "framework": "pytest-fixtures"}
```

Generated fixtures are validated for syntax correctness before returning.

### Integration Test Generator

**Module:** `apps/backend/agents/test_generator.py` (function `generate_integration_tests`)
**Analyzer:** `apps/backend/analysis/integration_test_analyzer.py`

The integration test analyzer performs AST analysis to detect:

- **API Endpoints** — FastAPI, Flask, and Django route decorators with HTTP methods and paths
- **Service Classes** — Classes with dependency injection or business logic
- **Database Operations** — ORM calls (SQLAlchemy, Django ORM) classified as SELECT/INSERT/UPDATE/UPSERT/DELETE
- **External Service Calls** — HTTP client calls (requests, httpx, aiohttp) including async patterns

**Usage:**

```python
from analysis.integration_test_analyzer import IntegrationTestAnalyzer

analyzer = IntegrationTestAnalyzer()
result = analyzer.analyze_file("path/to/api.py")

print(f"Endpoints: {len(result['endpoints'])}")
print(f"Services: {len(result['services'])}")
print(f"DB Operations: {len(result['database_operations'])}")
print(f"External Calls: {len(result['external_services'])}")
```

Generated integration tests are placed in `tests/integration/test_integration_*.py`.

### Coverage Enforcement

**Module:** `apps/backend/qa/loop.py`

The QA loop now enforces a minimum 80% code coverage threshold:

1. After test generation runs, coverage data is collected
2. If overall coverage is below 80%, the build is **rejected**
3. A `QA_FIX_REQUEST.md` is generated with:
   - Current vs required coverage percentages
   - Top 10 files needing additional coverage (sorted lowest first)
   - Per-file line counts and missed line ranges
4. The QA fixer agent receives this report and generates additional tests

**Coverage gap analysis** categorizes uncovered code into:

- **Critical gaps** — Core business logic without tests
- **High priority** — Error handling and validation paths
- **Medium priority** — Utility functions and helpers

## Integration with QA Loop

The test generation agent integrates into the existing QA validation pipeline:

```
Planner → Coder → QA Reviewer → [Test Generator] → Coverage Check → QA Fixer (if needed)
```

When the QA loop runs:

1. Code analysis identifies testable components
2. Edge cases are detected from source AST
3. Fixtures are generated for test data
4. Unit tests are generated for detected functions/classes
5. Integration tests are generated for API endpoints and services
6. Coverage is measured against the 80% threshold
7. If below threshold, QA fixer receives a detailed fix request

## Configuration

No additional configuration is required. The test generation agent uses the same Claude SDK client and model settings as other agents.

The coverage threshold is defined as `MINIMUM_COVERAGE_THRESHOLD = 80.0` in `apps/backend/qa/loop.py`.
