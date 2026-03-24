#!/usr/bin/env python3
"""
Tests for Integration Test Generation
======================================

Tests the integration test analyzer functionality including:
- API endpoint detection (FastAPI, Flask, Django)
- Service boundary detection
- Database operation detection
- External service call detection
"""

from pathlib import Path

import pytest

from analysis.integration_test_analyzer import (
    DatabaseOperationInfo,
    EndpointInfo,
    ExternalServiceInfo,
    IntegrationAnalysisResult,
    IntegrationTestAnalyzer,
    ServiceInfo,
)


# =============================================================================
# SAMPLE CODE FIXTURES
# =============================================================================


@pytest.fixture
def fastapi_sample(temp_dir: Path) -> Path:
    """Create a sample FastAPI application file."""
    content = '''"""
FastAPI Sample Application
==========================
"""

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel

app = FastAPI()


class UserRequest(BaseModel):
    """User request model."""
    name: str
    email: str


class UserResponse(BaseModel):
    """User response model."""
    id: int
    name: str
    email: str


@app.get("/users", response_model=UserResponse)
def list_users():
    """List all users."""
    return {"id": 1, "name": "Test", "email": "test@example.com"}


@app.post("/users", response_model=UserResponse)
def create_user(user: UserRequest):
    """Create a new user."""
    return {"id": 2, "name": user.name, "email": user.email}


@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user: UserRequest):
    """Update a user."""
    return {"id": user_id, "name": user.name, "email": user.email}


@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    """Delete a user."""
    return {"message": f"User {user_id} deleted"}


@app.get("/users/{user_id}/items/{item_id}")
def get_user_item(user_id: int, item_id: int):
    """Get a specific item for a user."""
    return {"user_id": user_id, "item_id": item_id}
'''

    file_path = temp_dir / "fastapi_app.py"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def flask_sample(temp_dir: Path) -> Path:
    """Create a sample Flask application file."""
    content = '''"""
Flask Sample Application
========================
"""

from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/users", methods=["GET"])
def list_users():
    """List all users."""
    return jsonify({"users": []})


@app.route("/users", methods=["POST"])
def create_user():
    """Create a new user."""
    data = request.get_json()
    return jsonify({"id": 1, "name": data.get("name")})


@app.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    """Update a user."""
    return jsonify({"id": user_id, "updated": True})


@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    """Delete a user."""
    return jsonify({"deleted": True})
'''

    file_path = temp_dir / "flask_app.py"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def service_sample(temp_dir: Path) -> Path:
    """Create a sample service class file."""
    content = '''"""
Service Classes Sample
======================
"""

from typing import Optional


class UserService:
    """Service for managing users."""

    def __init__(self, db_client, cache_client):
        """Initialize service with dependencies."""
        self.db_client = db_client
        self.cache_client = cache_client

    def create_user(self, name: str, email: str) -> dict:
        """Create a new user."""
        user = {"name": name, "email": email}
        self.db_client.insert("users", user)
        return user

    def get_user(self, user_id: int) -> Optional[dict]:
        """Get a user by ID."""
        return self.db_client.query("users", user_id)

    def update_user(self, user_id: int, data: dict) -> dict:
        """Update a user."""
        self.db_client.update("users", user_id, data)
        return {"id": user_id, **data}

    def delete_user(self, user_id: int) -> bool:
        """Delete a user."""
        return self.db_client.delete("users", user_id)


class EmailService:
    """Service for sending emails."""

    def __init__(self, smtp_client):
        """Initialize email service."""
        self.smtp_client = smtp_client

    def send_email(self, to: str, subject: str, body: str) -> bool:
        """Send an email."""
        return self.smtp_client.send(to, subject, body)
'''

    file_path = temp_dir / "services.py"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def database_operations_sample(temp_dir: Path) -> Path:
    """Create a sample file with database operations."""
    content = '''"""
Database Operations Sample
==========================
"""

from sqlalchemy import select, insert, update, delete


def get_user(db, user_id: int):
    """Get user by ID."""
    query = select(User).where(User.id == user_id)
    result = db.execute(query)
    return result.first()


def create_user(db, user_data: dict):
    """Create a new user."""
    query = insert(User).values(**user_data)
    result = db.execute(query)
    db.commit()
    return result


def update_user(db, user_id: int, data: dict):
    """Update a user."""
    query = update(User).where(User.id == user_id).values(**data)
    db.execute(query)
    db.commit()


def delete_user(db, user_id: int):
    """Delete a user."""
    query = delete(User).where(User.id == user_id)
    db.execute(query)
    db.commit()


def list_users(db):
    """List all users."""
    query = select(User)
    result = db.execute(query)
    return result.all()
'''

    file_path = temp_dir / "db_operations.py"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def external_service_sample(temp_dir: Path) -> Path:
    """Create a sample file with external service calls."""
    content = '''"""
External Service Calls Sample
==============================
"""

import requests
import httpx


def get_user_from_api(user_id: int):
    """Get user from external API."""
    response = requests.get(f"https://api.example.com/users/{user_id}")
    return response.json()


def create_user_in_api(user_data: dict):
    """Create user via external API."""
    response = requests.post(
        "https://api.example.com/users",
        json=user_data
    )
    return response.json()


async def fetch_user_async(user_id: int):
    """Fetch user asynchronously."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.external.com/users/{user_id}")
        return response.json()


def delete_user_from_api(user_id: int):
    """Delete user via external API."""
    response = requests.delete(f"https://api.example.com/users/{user_id}")
    return response.status_code == 204
'''

    file_path = temp_dir / "external_services.py"
    file_path.write_text(content)
    return file_path


# =============================================================================
# INTEGRATION TEST ANALYZER TESTS
# =============================================================================


class TestIntegrationTestAnalyzer:
    """Tests for IntegrationTestAnalyzer class."""

    def test_analyzer_initialization(self):
        """IntegrationTestAnalyzer initializes correctly."""
        analyzer = IntegrationTestAnalyzer()
        assert analyzer is not None

    # -------------------------------------------------------------------------
    # FastAPI Endpoint Detection
    # -------------------------------------------------------------------------

    def test_detect_fastapi_endpoints(self, fastapi_sample: Path):
        """Analyzer detects FastAPI endpoints correctly."""
        analyzer = IntegrationTestAnalyzer()
        result = analyzer.analyze_file(fastapi_sample)

        assert "endpoints" in result
        assert len(result["endpoints"]) >= 5

        # Check for specific endpoints
        endpoint_paths = [ep["path"] for ep in result["endpoints"]]
        assert "/users" in endpoint_paths
        assert "/users/{user_id}" in endpoint_paths
        assert "/users/{user_id}/items/{item_id}" in endpoint_paths

        # Check methods
        endpoints_by_path = {ep["path"]: ep for ep in result["endpoints"]}
        assert endpoints_by_path["/users"]["method"] in ["GET", "POST"]  # First defined

    def test_detect_fastapi_http_methods(self, fastapi_sample: Path):
        """Analyzer detects HTTP methods for FastAPI endpoints."""
        analyzer = IntegrationTestAnalyzer()
        result = analyzer.analyze_file(fastapi_sample)

        methods = [ep["method"] for ep in result["endpoints"]]
        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "DELETE" in methods

    def test_detect_fastapi_request_response_models(self, fastapi_sample: Path):
        """Analyzer detects request and response models."""
        analyzer = IntegrationTestAnalyzer()
        result = analyzer.analyze_file(fastapi_sample)

        # Find endpoints with models
        create_endpoint = next(
            (ep for ep in result["endpoints"] if ep["function_name"] == "create_user"),
            None
        )
        assert create_endpoint is not None
        assert create_endpoint["request_model"] == "UserRequest"
        assert create_endpoint["response_model"] == "UserResponse"

    # -------------------------------------------------------------------------
    # Flask Endpoint Detection
    # -------------------------------------------------------------------------

    def test_detect_flask_endpoints(self, flask_sample: Path):
        """Analyzer detects Flask endpoints correctly."""
        analyzer = IntegrationTestAnalyzer()
        result = analyzer.analyze_file(flask_sample)

        assert "endpoints" in result
        assert len(result["endpoints"]) >= 3

        # Check for specific endpoints
        endpoint_paths = [ep["path"] for ep in result["endpoints"]]
        assert "/users" in endpoint_paths
        assert "/users/<int:user_id>" in endpoint_paths

    def test_detect_flask_methods(self, flask_sample: Path):
        """Analyzer detects HTTP methods for Flask endpoints."""
        analyzer = IntegrationTestAnalyzer()
        result = analyzer.analyze_file(flask_sample)

        methods = [ep["method"] for ep in result["endpoints"]]
        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "DELETE" in methods

    # -------------------------------------------------------------------------
    # Framework Detection
    # -------------------------------------------------------------------------

    def test_detect_fastapi_framework(self, fastapi_sample: Path):
        """Analyzer detects FastAPI framework."""
        analyzer = IntegrationTestAnalyzer()
        result = analyzer.analyze_file(fastapi_sample)

        assert result["framework"] == "fastapi"

    def test_detect_flask_framework(self, flask_sample: Path):
        """Analyzer detects Flask framework."""
        analyzer = IntegrationTestAnalyzer()
        result = analyzer.analyze_file(flask_sample)

        assert result["framework"] == "flask"

    def test_detect_no_framework(self, service_sample: Path):
        """Analyzer returns None when no framework detected."""
        analyzer = IntegrationTestAnalyzer()
        result = analyzer.analyze_file(service_sample)

        assert result["framework"] is None

    # -------------------------------------------------------------------------
    # Service Detection
    # -------------------------------------------------------------------------

    def test_detect_service_classes(self, service_sample: Path):
        """Analyzer detects service classes correctly."""
        analyzer = IntegrationTestAnalyzer()
        result = analyzer.analyze_file(service_sample)

        assert "services" in result
        assert len(result["services"]) >= 2

        # Check for specific services
        service_names = [svc["name"] for svc in result["services"]]
        assert "UserService" in service_names
        assert "EmailService" in service_names

    def test_detect_service_methods(self, service_sample: Path):
        """Analyzer extracts public methods from service classes."""
        analyzer = IntegrationTestAnalyzer()
        result = analyzer.analyze_file(service_sample)

        user_service = next(
            (svc for svc in result["services"] if svc["name"] == "UserService"),
            None
        )
        assert user_service is not None
        assert len(user_service["methods"]) >= 4

        method_names = user_service["methods"]
        assert "create_user" in method_names
        assert "get_user" in method_names
        assert "update_user" in method_names
        assert "delete_user" in method_names

    def test_detect_service_dependencies(self, service_sample: Path):
        """Analyzer extracts dependencies from service __init__."""
        analyzer = IntegrationTestAnalyzer()
        result = analyzer.analyze_file(service_sample)

        user_service = next(
            (svc for svc in result["services"] if svc["name"] == "UserService"),
            None
        )
        assert user_service is not None
        assert len(user_service["dependencies"]) >= 2

        dep_names = user_service["dependencies"]
        assert "db_client" in dep_names
        assert "cache_client" in dep_names

    def test_detect_async_service_methods(self, service_sample: Path):
        """Analyzer detects async methods in services."""
        # This tests the is_async flag detection
        analyzer = IntegrationTestAnalyzer()
        result = analyzer.analyze_file(service_sample)

        # Our sample doesn't have async methods, but the field should exist
        for service in result["services"]:
            assert "is_async" in service
            assert isinstance(service["is_async"], bool)

    # -------------------------------------------------------------------------
    # Database Operation Detection
    # -------------------------------------------------------------------------

    def test_detect_database_operations(self, database_operations_sample: Path):
        """Analyzer detects database operations."""
        analyzer = IntegrationTestAnalyzer()
        result = analyzer.analyze_file(database_operations_sample)

        assert "database_operations" in result
        assert len(result["database_operations"]) >= 4

        # Check for different operation types
        operation_types = [op["operation_type"] for op in result["database_operations"]]
        assert "SELECT" in operation_types
        assert "INSERT" in operation_types
        assert "UPDATE" in operation_types
        assert "DELETE" in operation_types

    def test_classify_database_operations(self, database_operations_sample: Path):
        """Analyzer correctly classifies database operation types."""
        analyzer = IntegrationTestAnalyzer()
        result = analyzer.analyze_file(database_operations_sample)

        # Find operations by function name
        get_op = next(
            (op for op in result["database_operations"] if op["function_name"] == "get_user"),
            None
        )
        assert get_op is not None
        assert get_op["operation_type"] == "SELECT"

        create_op = next(
            (op for op in result["database_operations"] if op["function_name"] == "create_user"),
            None
        )
        assert create_op is not None
        assert create_op["operation_type"] == "INSERT"

    # -------------------------------------------------------------------------
    # External Service Detection
    # -------------------------------------------------------------------------

    def test_detect_external_service_calls(self, external_service_sample: Path):
        """Analyzer detects external HTTP service calls."""
        analyzer = IntegrationTestAnalyzer()
        result = analyzer.analyze_file(external_service_sample)

        assert "external_services" in result
        assert len(result["external_services"]) >= 3

        # Check for service names
        service_names = [svc["service_name"] for svc in result["external_services"]]
        assert len(service_names) > 0

    def test_detect_http_methods_in_external_calls(self, external_service_sample: Path):
        """Analyzer detects HTTP methods in external service calls."""
        analyzer = IntegrationTestAnalyzer()
        result = analyzer.analyze_file(external_service_sample)

        methods = [svc["method"] for svc in result["external_services"] if svc["method"]]
        assert "GET" in methods
        assert "POST" in methods
        assert "DELETE" in methods

    def test_detect_async_external_calls(self, external_service_sample: Path):
        """Analyzer detects async external service calls."""
        analyzer = IntegrationTestAnalyzer()
        result = analyzer.analyze_file(external_service_sample)

        # Find async calls
        async_calls = [svc for svc in result["external_services"] if svc["is_async"]]
        assert len(async_calls) > 0

        # Check for fetch_user_async
        fetch_async = next(
            (svc for svc in result["external_services"] if svc["function_name"] == "fetch_user_async"),
            None
        )
        assert fetch_async is not None
        assert fetch_async["is_async"] is True

    # -------------------------------------------------------------------------
    # Authentication Detection
    # -------------------------------------------------------------------------

    def test_detect_auth_in_fastapi(self, fastapi_sample: Path):
        """Analyzer detects authentication patterns."""
        analyzer = IntegrationTestAnalyzer()
        result = analyzer.analyze_file(fastapi_sample)

        # Check has_auth flag exists
        assert "has_auth" in result
        assert isinstance(result["has_auth"], bool)

    # -------------------------------------------------------------------------
    # File Analysis
    # -------------------------------------------------------------------------

    def test_analyze_file_includes_path(self, fastapi_sample: Path):
        """Analyzer includes file path in results."""
        analyzer = IntegrationTestAnalyzer()
        result = analyzer.analyze_file(fastapi_sample)

        assert "file_path" in result
        assert result["file_path"] == str(fastapi_sample)

    def test_analyze_file_includes_line_count(self, fastapi_sample: Path):
        """Analyzer counts total lines in file."""
        analyzer = IntegrationTestAnalyzer()
        result = analyzer.analyze_file(fastapi_sample)

        assert "total_lines" in result
        assert result["total_lines"] > 0

    def test_analyze_file_handles_missing_file(self, temp_dir: Path):
        """Analyzer handles missing file gracefully."""
        analyzer = IntegrationTestAnalyzer()
        missing_file = temp_dir / "nonexistent.py"

        with pytest.raises(FileNotFoundError):
            analyzer.analyze_file(missing_file)

    def test_analyze_file_handles_syntax_error(self, temp_dir: Path):
        """Analyzer handles syntax errors gracefully."""
        analyzer = IntegrationTestAnalyzer()
        invalid_file = temp_dir / "invalid.py"
        invalid_file.write_text("def broken(\n  pass")  # Syntax error

        with pytest.raises(ValueError, match="Syntax error"):
            analyzer.analyze_file(invalid_file)

    def test_analyze_source_string(self):
        """Analyzer can analyze source code strings."""
        analyzer = IntegrationTestAnalyzer()

        source = """
from fastapi import FastAPI

app = FastAPI()

@app.get("/test")
def test_endpoint():
    return {"message": "test"}
"""

        result = analyzer.analyze_source(source)

        assert "endpoints" in result
        assert len(result["endpoints"]) == 1
        assert result["endpoints"][0]["path"] == "/test"


# =============================================================================
# DATA CLASS TESTS
# =============================================================================


class TestDataClasses:
    """Tests for dataclass structures."""

    def test_endpoint_info_creation(self):
        """EndpointInfo dataclass creates correctly."""
        endpoint = EndpointInfo(
            path="/users/{id}",
            method="GET",
            function_name="get_user",
            lineno=10,
            request_model="UserRequest",
            response_model="UserResponse",
            auth_required=True,
            decorators=["get"],
            docstring="Get user by ID"
        )

        assert endpoint.path == "/users/{id}"
        assert endpoint.method == "GET"
        assert endpoint.function_name == "get_user"
        assert endpoint.auth_required is True

    def test_service_info_creation(self):
        """ServiceInfo dataclass creates correctly."""
        service = ServiceInfo(
            name="UserService",
            lineno=5,
            methods=["create", "update", "delete"],
            dependencies=["db_client"],
            docstring="User service",
            is_async=False
        )

        assert service.name == "UserService"
        assert len(service.methods) == 3
        assert service.is_async is False

    def test_database_operation_info_creation(self):
        """DatabaseOperationInfo dataclass creates correctly."""
        operation = DatabaseOperationInfo(
            operation_type="SELECT",
            model="User",
            function_name="get_user",
            lineno=15,
            orm_type="sqlalchemy"
        )

        assert operation.operation_type == "SELECT"
        assert operation.model == "User"
        assert operation.orm_type == "sqlalchemy"

    def test_external_service_info_creation(self):
        """ExternalServiceInfo dataclass creates correctly."""
        service = ExternalServiceInfo(
            service_name="api_example_com",
            function_name="fetch_data",
            lineno=20,
            method="GET",
            is_async=True
        )

        assert service.service_name == "api_example_com"
        assert service.is_async is True

    def test_integration_analysis_result_creation(self):
        """IntegrationAnalysisResult dataclass creates correctly."""
        result = IntegrationAnalysisResult(
            file_path="test.py",
            endpoints=[],
            services=[],
            database_operations=[],
            external_services=[],
            framework="fastapi",
            has_auth=True,
            total_lines=100
        )

        assert result.file_path == "test.py"
        assert result.framework == "fastapi"
        assert result.total_lines == 100


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestIntegrationTestAnalysisPipeline:
    """Integration tests for complete analysis pipeline."""

    def test_analyze_complex_application(self, temp_dir: Path):
        """Analyzer handles a complex application with multiple patterns."""
        # Create a file with multiple patterns
        complex_file = temp_dir / "complex_app.py"
        complex_file.write_text('''
from fastapi import FastAPI, Depends
import requests

app = FastAPI()


class DataService:
    """Service for data operations."""

    def __init__(self, db):
        self.db = db

    def get_data(self, id):
        return self.db.query("SELECT * FROM data WHERE id = ?", id)


@app.get("/data/{data_id}")
def get_data(data_id: int):
    """Get data by ID."""
    service = DataService(db)
    return service.get_data(data_id)


@app.post("/data")
def create_data(data: dict):
    """Create new data."""
    response = requests.post("https://external.api/data", json=data)
    return response.json()
''')

        analyzer = IntegrationTestAnalyzer()
        result = analyzer.analyze_file(complex_file)

        # Should detect endpoints
        assert len(result["endpoints"]) >= 2

        # Should detect service
        assert len(result["services"]) >= 1

        # Should detect database operation
        assert len(result["database_operations"]) >= 1

        # Should detect external service call
        assert len(result["external_services"]) >= 1

        # Framework detected
        assert result["framework"] == "fastapi"
