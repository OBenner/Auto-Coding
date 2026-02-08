"""
CRUD API Template
=================

Template for creating RESTful CRUD API endpoints.
"""

from typing import Any, Dict

from ..registry import Template


class CrudApiTemplate(Template):
    """Template for CRUD API implementation."""

    def __init__(self):
        """Initialize the CRUD API template."""
        super().__init__(
            name="crud_api",
            description="Create RESTful CRUD API endpoints for a resource",
            category="api",
            parameters={
                "resource_name": {
                    "type": str,
                    "required": True,
                    "description": "Name of the resource (e.g., 'User', 'Product')",
                },
                "resource_name_plural": {
                    "type": str,
                    "required": True,
                    "description": "Plural form of resource name (e.g., 'Users', 'Products')",
                },
                "fields": {
                    "type": list,
                    "required": True,
                    "description": "List of resource fields (e.g., ['name', 'email', 'age'])",
                },
                "authentication_required": {
                    "type": bool,
                    "required": False,
                    "default": True,
                    "description": "Whether endpoints require authentication",
                },
                "pagination": {
                    "type": bool,
                    "required": False,
                    "default": True,
                    "description": "Whether list endpoint should support pagination",
                },
            },
        )

    def generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate CRUD API spec from parameters."""
        resource = params["resource_name"]
        resource_plural = params["resource_name_plural"]
        fields = params["fields"]
        auth_required = params.get("authentication_required", True)
        pagination = params.get("pagination", True)

        fields_str = ", ".join(fields)

        return {
            "title": f"{resource} CRUD API",
            "description": f"RESTful API endpoints for managing {resource_plural} with full CRUD operations.",
            "rationale": f"Provide a standard interface for creating, reading, updating, and deleting {resource_plural}. This enables frontend applications and third-party integrations to manage {resource_plural} programmatically.",
            "user_stories": [
                f"As a developer, I want to create new {resource_plural} via API",
                f"As a developer, I want to retrieve {resource_plural} with filtering and search",
                f"As a developer, I want to update existing {resource_plural}",
                f"As a developer, I want to delete {resource_plural}",
            ],
            "acceptance_criteria": [
                f"POST /{resource_plural.lower()} creates a new {resource}",
                f"GET /{resource_plural.lower()} returns list of {resource_plural}" + (" with pagination" if pagination else ""),
                f"GET /{resource_plural.lower()}/{{id}} returns a single {resource}",
                f"PUT/PATCH /{resource_plural.lower()}/{{id}} updates a {resource}",
                f"DELETE /{resource_plural.lower()}/{{id}} removes a {resource}",
                "All endpoints return appropriate HTTP status codes (200, 201, 400, 404, 500)",
                "Request validation with clear error messages",
                "Response includes all resource fields: " + fields_str,
            ] + (["Authentication required for all endpoints"] if auth_required else []),
            "technical_details": f"""
### Endpoints

**Create {resource}**
- Method: POST
- Path: /{resource_plural.lower()}
- Body: {{{', '.join([f'"{f}": "..."' for f in fields])}}}
- Response: 201 Created with {resource} object

**List {resource_plural}**
- Method: GET
- Path: /{resource_plural.lower()}
{f"- Query Params: page, limit, sort, filter" if pagination else ""}
- Response: 200 OK with array of {resource_plural}

**Get {resource}**
- Method: GET
- Path: /{resource_plural.lower()}/{{id}}
- Response: 200 OK with {resource} object or 404 Not Found

**Update {resource}**
- Method: PUT/PATCH
- Path: /{resource_plural.lower()}/{{id}}
- Body: Partial or complete {resource} fields
- Response: 200 OK with updated {resource} object

**Delete {resource}**
- Method: DELETE
- Path: /{resource_plural.lower()}/{{id}}
- Response: 204 No Content or 200 OK

### Data Model

{resource} fields:
{chr(10).join([f"- {field}" for field in fields])}

### Error Handling

- 400 Bad Request: Invalid input data
- 401 Unauthorized: Missing or invalid authentication{" (if auth_required)" if auth_required else ""}
- 404 Not Found: {resource} not found
- 500 Internal Server Error: Server-side errors
""",
            "test_coverage": [
                f"Unit tests for {resource} creation with valid data",
                f"Unit tests for {resource} creation with invalid data (validation errors)",
                f"Integration tests for retrieving {resource_plural}",
                f"Integration tests for updating {resource}",
                f"Integration tests for deleting {resource}",
                "Tests for error handling (404, 400, 500)",
            ] + (["Tests for authentication/authorization"] if auth_required else []),
        }
