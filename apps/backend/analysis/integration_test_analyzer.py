#!/usr/bin/env python3
"""
Integration Test Analyzer Module
=================================

Analyzes code to detect API endpoints and service boundaries for integration test generation.
This module identifies testable integration points including HTTP endpoints, service classes,
database operations, and external service calls.

The integration test analyzer results are used by:
- Test Generator: To create integration tests for detected API endpoints
- QA Agent: To validate service interactions and API contracts
- Planner: To understand system boundaries for integration testing

Usage:
    from integration_test_analyzer import IntegrationTestAnalyzer

    analyzer = IntegrationTestAnalyzer()
    result = analyzer.analyze_file('path/to/api.py')

    print(f"Endpoints: {result['endpoints']}")
    print(f"Services: {result['services']}")
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class EndpointInfo:
    """
    Represents an API endpoint.

    Attributes:
        path: URL path pattern (e.g., '/users/{id}')
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        function_name: Name of the handler function
        lineno: Line number in source file
        request_model: Request body model class name if available
        response_model: Response model class name if available
        auth_required: Whether endpoint requires authentication
        decorators: List of decorator names
        docstring: Function docstring if available
    """

    path: str
    method: str
    function_name: str
    lineno: int
    request_model: str | None = None
    response_model: str | None = None
    auth_required: bool = False
    decorators: list[str] = field(default_factory=list)
    docstring: str | None = None


@dataclass
class ServiceInfo:
    """
    Represents a service class or module.

    Attributes:
        name: Service class/module name
        lineno: Line number in source file
        methods: List of public methods
        dependencies: List of injected dependencies
        docstring: Service docstring if available
        is_async: Whether service uses async methods
    """

    name: str
    lineno: int
    methods: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    docstring: str | None = None
    is_async: bool = False


@dataclass
class DatabaseOperationInfo:
    """
    Represents a database operation.

    Attributes:
        operation_type: Type of operation (SELECT, INSERT, UPDATE, DELETE)
        model: Database model/table name if detected
        function_name: Name of function performing operation
        lineno: Line number in source file
        orm_type: ORM framework (sqlalchemy, django, peewee, etc.)
    """

    operation_type: str
    model: str | None
    function_name: str
    lineno: int
    orm_type: str | None = None


@dataclass
class ExternalServiceInfo:
    """
    Represents an external service call.

    Attributes:
        service_name: Name of external service
        function_name: Function making the call
        lineno: Line number in source file
        method: HTTP method or RPC method
        is_async: Whether call is asynchronous
    """

    service_name: str
    function_name: str
    lineno: int
    method: str | None = None
    is_async: bool = False


@dataclass
class IntegrationAnalysisResult:
    """
    Result of integration test analysis.

    Attributes:
        file_path: Path to analyzed file
        endpoints: List of detected API endpoints
        services: List of service classes
        database_operations: List of database operations
        external_services: List of external service calls
        framework: Detected web framework (fastapi, flask, django, etc.)
        has_auth: Whether file has authentication logic
        total_lines: Total lines in file
    """

    file_path: str
    endpoints: list[EndpointInfo] = field(default_factory=list)
    services: list[ServiceInfo] = field(default_factory=list)
    database_operations: list[DatabaseOperationInfo] = field(default_factory=list)
    external_services: list[ExternalServiceInfo] = field(default_factory=list)
    framework: str | None = None
    has_auth: bool = False
    total_lines: int = 0


# =============================================================================
# INTEGRATION TEST ANALYZER
# =============================================================================


class IntegrationTestAnalyzer:
    """
    Analyzes Python source code to detect integration points.

    Detects:
    - API endpoints (FastAPI, Flask, Django)
    - Service classes and methods
    - Database operations (SQLAlchemy, Django ORM)
    - External service calls (HTTP, gRPC)
    """

    # Framework-specific patterns
    FASTAPI_DECORATORS = {"get", "post", "put", "delete", "patch", "options", "head"}
    FLASK_DECORATORS = {"route"}
    DJANGO_VIEW_BASES = {"View", "APIView", "ViewSet", "GenericViewSet"}

    # Database operation patterns
    DB_QUERY_METHODS = {
        "select",
        "insert",
        "update",
        "delete",
        "query",
        "filter",
        "all",
        "first",
        "get",
        "create",
        "save",
        "commit",
    }

    # External service patterns
    HTTP_CLIENT_METHODS = {"get", "post", "put", "delete", "patch", "request"}
    HTTP_LIBRARIES = {"requests", "httpx", "aiohttp", "urllib"}

    def __init__(self):
        """Initialize the integration test analyzer."""
        pass

    def analyze_file(self, file_path: str | Path) -> dict[str, Any]:
        """
        Analyze a Python source file for integration points.

        Args:
            file_path: Path to Python file to analyze

        Returns:
            Dictionary containing analysis results with keys:
            - endpoints: List of EndpointInfo objects
            - services: List of ServiceInfo objects
            - database_operations: List of DatabaseOperationInfo objects
            - external_services: List of ExternalServiceInfo objects
            - framework: Detected web framework
            - has_auth: Whether authentication is used
            - total_lines: Total lines in file
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise ValueError(f"Unable to read file as UTF-8: {file_path}")

        result = self._analyze_source(source, str(path))
        return self._result_to_dict(result)

    def analyze_source(self, source: str) -> dict[str, Any]:
        """
        Analyze Python source code string for integration points.

        Args:
            source: Python source code as string

        Returns:
            Dictionary containing analysis results
        """
        result = self._analyze_source(source, "<string>")
        return self._result_to_dict(result)

    def _analyze_source(self, source: str, file_path: str) -> IntegrationAnalysisResult:
        """
        Internal method to analyze source code.

        Args:
            source: Python source code
            file_path: Path for error reporting

        Returns:
            IntegrationAnalysisResult object
        """
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Syntax error in {file_path}: {e}")

        result = IntegrationAnalysisResult(
            file_path=file_path, total_lines=len(source.splitlines())
        )

        # Detect framework from imports
        result.framework = self._detect_framework(tree)

        # Extract imports for context
        imports = self._extract_imports(tree)

        # Check for authentication patterns
        result.has_auth = self._detect_auth(tree, imports)

        # Analyze top-level definitions
        for node in ast.walk(tree):
            # Extract API endpoints
            if isinstance(node, ast.FunctionDef):
                endpoint = self._extract_endpoint(node, result.framework)
                if endpoint:
                    result.endpoints.append(endpoint)

                # Extract database operations
                db_ops = self._extract_database_operations(node)
                result.database_operations.extend(db_ops)

                # Extract external service calls
                ext_services = self._extract_external_services(node, imports)
                result.external_services.extend(ext_services)

            # Extract service classes
            if isinstance(node, ast.ClassDef):
                service = self._extract_service(node)
                if service:
                    result.services.append(service)

        return result

    def _detect_framework(self, tree: ast.AST) -> str | None:
        """
        Detect web framework from imports.

        Args:
            tree: AST tree

        Returns:
            Framework name or None
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "fastapi":
                        return "fastapi"
                    elif alias.name == "flask":
                        return "flask"
                    elif alias.name == "django":
                        return "django"

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    if node.module.startswith("fastapi"):
                        return "fastapi"
                    elif node.module.startswith("flask"):
                        return "flask"
                    elif node.module.startswith("django"):
                        return "django"

        return None

    def _extract_imports(self, tree: ast.AST) -> list[str]:
        """
        Extract import statements.

        Args:
            tree: AST tree

        Returns:
            List of imported module names
        """
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        return imports

    def _detect_auth(self, tree: ast.AST, imports: list[str]) -> bool:
        """
        Detect authentication patterns.

        Args:
            tree: AST tree
            imports: List of imports

        Returns:
            True if authentication is detected
        """
        # Check for auth-related imports
        auth_keywords = {"auth", "jwt", "oauth", "token", "session", "login"}

        for imp in imports:
            if any(keyword in imp.lower() for keyword in auth_keywords):
                return True

        # Check for auth decorators
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    decorator_name = self._get_decorator_name(decorator)
                    if any(
                        keyword in decorator_name.lower() for keyword in auth_keywords
                    ):
                        return True

        return False

    def _extract_endpoint(
        self, node: ast.FunctionDef, framework: str | None
    ) -> EndpointInfo | None:
        """
        Extract API endpoint information from function.

        Args:
            node: Function definition node
            framework: Detected framework

        Returns:
            EndpointInfo or None if not an endpoint
        """
        # Look for route decorators
        for decorator in node.decorator_list:
            decorator_name = self._get_decorator_name(decorator)

            # FastAPI pattern: @app.get("/path")
            if framework == "fastapi" and decorator_name in self.FASTAPI_DECORATORS:
                path = self._extract_path_from_decorator(decorator)
                if path:
                    return EndpointInfo(
                        path=path,
                        method=decorator_name.upper(),
                        function_name=node.name,
                        lineno=node.lineno,
                        request_model=self._extract_request_model(node),
                        response_model=self._extract_response_model(node, decorator),
                        auth_required=self._has_auth_decorator(node),
                        decorators=[
                            self._get_decorator_name(d) for d in node.decorator_list
                        ],
                        docstring=ast.get_docstring(node),
                    )

            # Flask pattern: @app.route("/path", methods=["GET"])
            elif framework == "flask" and decorator_name in self.FLASK_DECORATORS:
                path = self._extract_path_from_decorator(decorator)
                method = self._extract_method_from_decorator(decorator)
                if path:
                    return EndpointInfo(
                        path=path,
                        method=method or "GET",
                        function_name=node.name,
                        lineno=node.lineno,
                        auth_required=self._has_auth_decorator(node),
                        decorators=[
                            self._get_decorator_name(d) for d in node.decorator_list
                        ],
                        docstring=ast.get_docstring(node),
                    )

        return None

    def _extract_service(self, node: ast.ClassDef) -> ServiceInfo | None:
        """
        Extract service class information.

        Args:
            node: Class definition node

        Returns:
            ServiceInfo or None if not a service
        """
        # Heuristic: Classes ending in "Service", "Client", "Repository", "Manager"
        service_suffixes = {"Service", "Client", "Repository", "Manager", "Handler"}

        if any(node.name.endswith(suffix) for suffix in service_suffixes):
            methods = []
            is_async = False

            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    if not item.name.startswith("_"):  # Public methods
                        methods.append(item.name)
                elif isinstance(item, ast.AsyncFunctionDef):
                    if not item.name.startswith("_"):
                        methods.append(item.name)
                    is_async = True

            # Extract dependencies from __init__
            dependencies = self._extract_dependencies(node)

            return ServiceInfo(
                name=node.name,
                lineno=node.lineno,
                methods=methods,
                dependencies=dependencies,
                docstring=ast.get_docstring(node),
                is_async=is_async,
            )

        return None

    def _extract_database_operations(
        self, node: ast.FunctionDef
    ) -> list[DatabaseOperationInfo]:
        """
        Extract database operations from function.

        Args:
            node: Function definition node

        Returns:
            List of DatabaseOperationInfo
        """
        operations = []

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                # Handle both attribute calls (table.select()) and function calls (select())
                if isinstance(child.func, ast.Attribute):
                    method_name = child.func.attr.lower()
                elif isinstance(child.func, ast.Name):
                    method_name = child.func.id.lower()
                else:
                    continue

                if method_name in self.DB_QUERY_METHODS:
                    # Determine operation type
                    op_type = self._classify_db_operation(method_name)

                    # Try to extract model name
                    if isinstance(child.func, ast.Attribute):
                        model = self._extract_model_name(child.func)
                    elif isinstance(child.func, ast.Name) and child.args:
                        # For select(User), extract model from first argument
                        model = self._extract_model_from_arg(child.args[0])
                    else:
                        model = None

                    operations.append(
                        DatabaseOperationInfo(
                            operation_type=op_type,
                            model=model,
                            function_name=node.name,
                            lineno=child.lineno,
                            orm_type="sqlalchemy",  # Default, could be enhanced
                        )
                    )

        return operations

    def _extract_external_services(
        self, node: ast.FunctionDef, imports: list[str]
    ) -> list[ExternalServiceInfo]:
        """
        Extract external service calls from function.

        Args:
            node: Function definition node
            imports: List of imports

        Returns:
            List of ExternalServiceInfo
        """
        external_calls = []

        # Check if HTTP client is imported
        has_http_client = any(
            lib in imp.lower() for imp in imports for lib in self.HTTP_LIBRARIES
        )

        if not has_http_client:
            return external_calls

        is_async = isinstance(node, ast.AsyncFunctionDef)

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    method_name = child.func.attr.lower()

                    if method_name in self.HTTP_CLIENT_METHODS:
                        # Try to extract service name from URL or variable
                        service_name = self._extract_service_name(child)

                        external_calls.append(
                            ExternalServiceInfo(
                                service_name=service_name or "external_api",
                                function_name=node.name,
                                lineno=child.lineno,
                                method=method_name.upper(),
                                is_async=is_async,
                            )
                        )

        return external_calls

    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """
        Extract decorator name from decorator node.

        Args:
            decorator: Decorator expression node

        Returns:
            Decorator name as string
        """
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return decorator.attr
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id
            elif isinstance(decorator.func, ast.Attribute):
                return decorator.func.attr
        return ""

    def _extract_path_from_decorator(self, decorator: ast.expr) -> str | None:
        """
        Extract URL path from route decorator.

        Args:
            decorator: Decorator node

        Returns:
            URL path or None
        """
        if isinstance(decorator, ast.Call):
            # First argument is usually the path
            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                return decorator.args[0].value

        return None

    def _extract_method_from_decorator(self, decorator: ast.expr) -> str | None:
        """
        Extract HTTP method from Flask route decorator.

        Args:
            decorator: Decorator node

        Returns:
            HTTP method or None
        """
        if isinstance(decorator, ast.Call):
            for keyword in decorator.keywords:
                if keyword.arg == "methods":
                    if isinstance(keyword.value, ast.List):
                        if keyword.value.elts and isinstance(
                            keyword.value.elts[0], ast.Constant
                        ):
                            return keyword.value.elts[0].value

        return None

    def _extract_request_model(self, node: ast.FunctionDef) -> str | None:
        """
        Extract request model from function signature.

        Args:
            node: Function definition node

        Returns:
            Request model class name or None
        """
        # Look for type annotations on arguments
        for arg in node.args.args:
            if arg.annotation:
                if isinstance(arg.annotation, ast.Name):
                    # Heuristic: Model names often end with "Request" or "Input"
                    if arg.annotation.id.endswith(("Request", "Input", "Model")):
                        return arg.annotation.id

        return None

    def _extract_response_model(
        self, node: ast.FunctionDef, decorator: ast.expr
    ) -> str | None:
        """
        Extract response model from decorator or return annotation.

        Args:
            node: Function definition node
            decorator: Route decorator

        Returns:
            Response model class name or None
        """
        # Check decorator for response_model keyword (FastAPI)
        if isinstance(decorator, ast.Call):
            for keyword in decorator.keywords:
                if keyword.arg == "response_model":
                    if isinstance(keyword.value, ast.Name):
                        return keyword.value.id

        # Check return type annotation
        if node.returns:
            if isinstance(node.returns, ast.Name):
                return node.returns.id

        return None

    def _has_auth_decorator(self, node: ast.FunctionDef) -> bool:
        """
        Check if function has authentication decorator.

        Args:
            node: Function definition node

        Returns:
            True if auth decorator present
        """
        auth_keywords = {"auth", "login", "token", "jwt", "oauth", "depends"}

        for decorator in node.decorator_list:
            decorator_name = self._get_decorator_name(decorator)
            if any(keyword in decorator_name.lower() for keyword in auth_keywords):
                return True

        return False

    def _extract_dependencies(self, node: ast.ClassDef) -> list[str]:
        """
        Extract dependencies from class __init__.

        Args:
            node: Class definition node

        Returns:
            List of dependency names
        """
        dependencies = []

        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                # Extract parameter names (excluding self)
                for arg in item.args.args[1:]:
                    dependencies.append(arg.arg)

        return dependencies

    def _classify_db_operation(self, method_name: str) -> str:
        """
        Classify database operation type.

        Args:
            method_name: ORM method name

        Returns:
            Operation type (SELECT, INSERT, UPDATE, DELETE)
        """
        if method_name in {"select", "query", "filter", "all", "first", "get"}:
            return "SELECT"
        elif method_name in {"insert", "create"}:
            return "INSERT"
        elif method_name in {"update", "save"}:
            return "UPDATE"
        elif method_name in {"delete"}:
            return "DELETE"
        else:
            return "UNKNOWN"

    def _extract_model_name(self, func: ast.Attribute) -> str | None:
        """
        Extract database model name from attribute chain.

        Args:
            func: Attribute node

        Returns:
            Model name or None
        """
        # Try to get the base object name
        if isinstance(func.value, ast.Name):
            return func.value.id
        elif isinstance(func.value, ast.Attribute):
            return func.value.attr

        return None

    def _extract_model_from_arg(self, arg: ast.AST) -> str | None:
        """
        Extract database model name from function argument.

        For SQLAlchemy 2.0 style calls like select(User), the model is passed
        as an argument.

        Args:
            arg: AST node from function arguments

        Returns:
            Model name or None
        """
        if isinstance(arg, ast.Name):
            return arg.id
        elif isinstance(arg, ast.Attribute):
            # Handle cases like models.User
            return arg.attr
        elif isinstance(arg, ast.Call):
            # Handle cases like User() (unlikely but possible)
            if isinstance(arg.func, ast.Name):
                return arg.func.id
        return None

    def _extract_service_name(self, call: ast.Call) -> str | None:
        """
        Extract service name from HTTP call.

        Args:
            call: Call node

        Returns:
            Service name or None
        """
        # Try to extract from URL string
        for arg in call.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                # Simple heuristic: extract domain from URL
                url = arg.value
                if "://" in url:
                    return url.split("://")[1].split("/")[0].replace(".", "_")

        return None

    def _result_to_dict(self, result: IntegrationAnalysisResult) -> dict[str, Any]:
        """
        Convert IntegrationAnalysisResult to dictionary.

        Args:
            result: IntegrationAnalysisResult object

        Returns:
            Dictionary representation
        """
        return {
            "file_path": result.file_path,
            "endpoints": [
                {
                    "path": ep.path,
                    "method": ep.method,
                    "function_name": ep.function_name,
                    "lineno": ep.lineno,
                    "request_model": ep.request_model,
                    "response_model": ep.response_model,
                    "auth_required": ep.auth_required,
                    "decorators": ep.decorators,
                    "docstring": ep.docstring,
                }
                for ep in result.endpoints
            ],
            "services": [
                {
                    "name": svc.name,
                    "lineno": svc.lineno,
                    "methods": svc.methods,
                    "dependencies": svc.dependencies,
                    "docstring": svc.docstring,
                    "is_async": svc.is_async,
                }
                for svc in result.services
            ],
            "database_operations": [
                {
                    "operation_type": db.operation_type,
                    "model": db.model,
                    "function_name": db.function_name,
                    "lineno": db.lineno,
                    "orm_type": db.orm_type,
                }
                for db in result.database_operations
            ],
            "external_services": [
                {
                    "service_name": ext.service_name,
                    "function_name": ext.function_name,
                    "lineno": ext.lineno,
                    "method": ext.method,
                    "is_async": ext.is_async,
                }
                for ext in result.external_services
            ],
            "framework": result.framework,
            "has_auth": result.has_auth,
            "total_lines": result.total_lines,
        }
