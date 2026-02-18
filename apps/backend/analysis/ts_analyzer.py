#!/usr/bin/env python3
"""
TypeScript/React Analyzer Module
=================================

Analyzes TypeScript and React/TSX source code to extract testable components and functions.
This module provides analysis of React component structure for automated test generation.

The TypeScript analyzer results are used by:
- Test Generator: To identify components/functions that need Vitest tests
- QA Agent: To determine what React code needs test coverage
- Planner: To understand component complexity for test planning

Usage:
    from ts_analyzer import TypeScriptAnalyzer

    analyzer = TypeScriptAnalyzer()
    result = analyzer.analyze_file('path/to/Component.tsx')

    print(f"Components: {result['components']}")
    print(f"Hooks: {result['hooks']}")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class PropInfo:
    """
    Represents a component prop or function parameter.

    Attributes:
        name: Prop/parameter name
        type: TypeScript type if available
        optional: Whether prop is optional
        default_value: Default value if specified
    """

    name: str
    type: str | None = None
    optional: bool = False
    default_value: str | None = None


@dataclass
class HookUsage:
    """
    Represents a React hook usage.

    Attributes:
        name: Hook name (e.g., 'useState', 'useEffect')
        variables: Variables returned/affected by the hook
        dependencies: Dependency array for useEffect/useCallback/useMemo
    """

    name: str
    variables: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)


@dataclass
class ComponentInfo:
    """
    Represents a React component.

    Attributes:
        name: Component name
        lineno: Line number in source file
        is_function_component: True for function components, False for class components
        props: List of component props
        state_variables: List of state variable names (from useState, class state)
        hooks: List of hooks used
        exported: Whether component is exported
        default_export: Whether component is default export
        has_children: Whether component accepts children prop
        event_handlers: List of event handler names
    """

    name: str
    lineno: int
    is_function_component: bool = True
    props: list[PropInfo] = field(default_factory=list)
    state_variables: list[str] = field(default_factory=list)
    hooks: list[HookUsage] = field(default_factory=list)
    exported: bool = False
    default_export: bool = False
    has_children: bool = False
    event_handlers: list[str] = field(default_factory=list)


@dataclass
class FunctionInfo:
    """
    Represents a utility function or custom hook.

    Attributes:
        name: Function name
        lineno: Line number in source file
        params: List of function parameters
        return_type: Return type if specified
        is_async: Whether function is async
        is_hook: Whether function is a custom React hook (starts with 'use')
        exported: Whether function is exported
    """

    name: str
    lineno: int
    params: list[PropInfo] = field(default_factory=list)
    return_type: str | None = None
    is_async: bool = False
    is_hook: bool = False
    exported: bool = False


@dataclass
class TypeInfo:
    """
    Represents a TypeScript type or interface.

    Attributes:
        name: Type/interface name
        lineno: Line number in source file
        kind: 'interface', 'type', or 'enum'
        exported: Whether type is exported
    """

    name: str
    lineno: int
    kind: str
    exported: bool = False


@dataclass
class AnalysisResult:
    """
    Result of TypeScript/React code analysis.

    Attributes:
        file_path: Path to analyzed file
        components: List of React components
        functions: List of utility functions and custom hooks
        types: List of TypeScript types/interfaces
        imports: List of import statements
        has_tests: Whether test file exists
        total_lines: Total lines in file
        edge_cases: List of detected edge case patterns
    """

    file_path: str
    components: list[ComponentInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    types: list[TypeInfo] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    has_tests: bool = False
    total_lines: int = 0
    edge_cases: list[dict[str, Any]] = field(default_factory=list)


# =============================================================================
# TYPESCRIPT ANALYZER
# =============================================================================


class TypeScriptAnalyzer:
    """
    Analyzes TypeScript and React source code using regex patterns.

    Extracts:
    - React components (function and class)
    - Custom hooks and utility functions
    - Component props and state
    - Hook usage patterns
    - TypeScript types and interfaces
    """

    def __init__(self):
        """Initialize the TypeScript analyzer."""
        # Regex patterns for extraction
        self._function_component_pattern = re.compile(
            r"(?:export\s+(?:default\s+)?)?(?:const|function)\s+(\w+)\s*[=:]?\s*(?:\(([^)]*)\)|<[^>]*>\s*\(([^)]*)\))\s*(?::\s*[\w.<>]+\s*)?(?:=>|{)",
            re.MULTILINE,
        )
        self._class_component_pattern = re.compile(
            r"(?:export\s+(?:default\s+)?)?class\s+(\w+)\s+extends\s+(?:React\.)?(?:Component|PureComponent)",
            re.MULTILINE,
        )
        self._hook_usage_pattern = re.compile(
            r"(?:const|let)\s*(?:\[([^\]]+)\]|\{([^}]+)\}|(\w+))\s*=\s*(use\w+)\s*\(",
            re.MULTILINE,
        )
        self._import_pattern = re.compile(
            r'import\s+(?:{[^}]+}|[\w*]+)\s+from\s+["\']([^"\']+)["\']', re.MULTILINE
        )
        self._type_pattern = re.compile(
            r"(?:export\s+)?(?:interface|type|enum)\s+(\w+)", re.MULTILINE
        )
        self._export_pattern = re.compile(
            r"export\s+(?:default\s+)?(?:const|function|class|interface|type|enum)?\s*(\w+)",
            re.MULTILINE,
        )

    def analyze_file(self, file_path: str | Path) -> dict[str, Any]:
        """
        Analyze a TypeScript/TSX source file.

        Args:
            file_path: Path to TypeScript/TSX file to analyze

        Returns:
            Dictionary containing analysis results with keys:
            - components: List of ComponentInfo objects
            - functions: List of FunctionInfo objects
            - types: List of TypeInfo objects
            - imports: List of import module names
            - has_tests: Whether corresponding test file exists
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

        # Check for corresponding test file
        result.has_tests = self._has_test_file(path)

        return self._result_to_dict(result)

    def analyze_source(self, source: str) -> dict[str, Any]:
        """
        Analyze TypeScript/TSX source code string.

        Args:
            source: TypeScript/TSX source code as string

        Returns:
            Dictionary containing analysis results
        """
        result = self._analyze_source(source, "<string>")
        return self._result_to_dict(result)

    def _analyze_source(self, source: str, file_path: str) -> AnalysisResult:
        """
        Internal method to analyze source code.

        Args:
            source: TypeScript/TSX source code
            file_path: Path for error reporting

        Returns:
            AnalysisResult object
        """
        result = AnalysisResult(
            file_path=file_path, total_lines=len(source.splitlines())
        )

        # Extract imports
        result.imports = self._extract_imports(source)

        # Extract types/interfaces
        result.types = self._extract_types(source)

        # Extract components
        result.components = self._extract_components(source)

        # Extract functions
        result.functions = self._extract_functions(source)

        # Detect edge cases for test generation
        result.edge_cases = self._detect_edge_cases(source)

        return result

    def _extract_imports(self, source: str) -> list[str]:
        """Extract import module names."""
        imports = []
        for match in self._import_pattern.finditer(source):
            module = match.group(1)
            imports.append(module)
        return imports

    def _extract_types(self, source: str) -> list[TypeInfo]:
        """Extract TypeScript types and interfaces."""
        types = []
        lines = source.splitlines()

        for lineno, line in enumerate(lines, 1):
            # Match interface, type, or enum declarations
            match = re.search(r"(?:export\s+)?(interface|type|enum)\s+(\w+)", line)
            if match:
                kind, name = match.groups()
                exported = "export" in line
                types.append(
                    TypeInfo(name=name, lineno=lineno, kind=kind, exported=exported)
                )

        return types

    def _extract_components(self, source: str) -> list[ComponentInfo]:
        """Extract React components (function and class)."""
        components = []

        # Extract function components
        for match in self._function_component_pattern.finditer(source):
            name = match.group(1)

            # Skip if not a component (doesn't start with uppercase)
            if not name[0].isupper():
                continue

            # Find line number
            lineno = source[: match.start()].count("\n") + 1

            # Extract props
            props_str = match.group(2) or match.group(3) or ""
            props = self._extract_props(props_str)

            # Check if exported
            exported = "export" in source[max(0, match.start() - 50) : match.start()]
            default_export = (
                "export default" in source[max(0, match.start() - 50) : match.start()]
            )

            # Extract component body to analyze hooks and state
            component_body = self._extract_component_body(source, match.start())
            hooks, state_vars = self._extract_hooks_and_state(component_body)
            event_handlers = self._extract_event_handlers(component_body)

            # Check for children prop
            has_children = "children" in props_str or "children:" in component_body

            components.append(
                ComponentInfo(
                    name=name,
                    lineno=lineno,
                    is_function_component=True,
                    props=props,
                    state_variables=state_vars,
                    hooks=hooks,
                    exported=exported,
                    default_export=default_export,
                    has_children=has_children,
                    event_handlers=event_handlers,
                )
            )

        # Extract class components
        for match in self._class_component_pattern.finditer(source):
            name = match.group(1)
            lineno = source[: match.start()].count("\n") + 1

            exported = "export" in source[max(0, match.start() - 50) : match.start()]
            default_export = (
                "export default" in source[max(0, match.start() - 50) : match.start()]
            )

            # Extract class body
            component_body = self._extract_component_body(source, match.start())
            state_vars = self._extract_class_state(component_body)
            event_handlers = self._extract_event_handlers(component_body)

            components.append(
                ComponentInfo(
                    name=name,
                    lineno=lineno,
                    is_function_component=False,
                    state_variables=state_vars,
                    exported=exported,
                    default_export=default_export,
                    event_handlers=event_handlers,
                )
            )

        return components

    def _extract_functions(self, source: str) -> list[FunctionInfo]:
        """Extract utility functions and custom hooks."""
        functions = []

        # Pattern for function declarations
        func_pattern = re.compile(
            r"(?:export\s+)?(?:async\s+)?(?:function|const|let)\s+(\w+)\s*[=:]?\s*(?:async\s+)?\(([^)]*)\)\s*(?::\s*([\w<>[\]|&\s]+))?\s*(?:=>|{)",
            re.MULTILINE,
        )

        for match in func_pattern.finditer(source):
            name = match.group(1)

            # Skip components (start with uppercase) - they're handled separately
            if name[0].isupper():
                continue

            lineno = source[: match.start()].count("\n") + 1
            params_str = match.group(2) or ""
            return_type = match.group(3)

            # Parse parameters
            params = self._extract_props(params_str)

            # Check if async
            is_async = (
                "async" in source[max(0, match.start() - 20) : match.start() + 20]
            )

            # Check if it's a custom hook (starts with 'use')
            is_hook = name.startswith("use")

            # Check if exported
            exported = "export" in source[max(0, match.start() - 50) : match.start()]

            functions.append(
                FunctionInfo(
                    name=name,
                    lineno=lineno,
                    params=params,
                    return_type=return_type,
                    is_async=is_async,
                    is_hook=is_hook,
                    exported=exported,
                )
            )

        return functions

    def _extract_props(self, props_str: str) -> list[PropInfo]:
        """Extract prop information from props string."""
        if not props_str or props_str.strip() == "":
            return []

        props = []

        # Handle destructured props: { prop1, prop2: type, prop3? }
        if "{" in props_str:
            # Extract content between braces
            match = re.search(r"\{([^}]+)\}", props_str)
            if match:
                props_content = match.group(1)
                # Split by comma
                for prop in props_content.split(","):
                    prop = prop.strip()
                    if not prop:
                        continue

                    # Parse prop name, type, and optional flag
                    prop_match = re.match(r"(\w+)(\?)?(?:\s*:\s*(.+))?", prop)
                    if prop_match:
                        name = prop_match.group(1)
                        optional = bool(prop_match.group(2))
                        prop_type = prop_match.group(3)

                        props.append(
                            PropInfo(
                                name=name,
                                type=prop_type.strip() if prop_type else None,
                                optional=optional,
                            )
                        )
        else:
            # Simple prop: (props: PropsType) or (prop1: string, prop2: number)
            for param in props_str.split(","):
                param = param.strip()
                if not param:
                    continue

                param_match = re.match(r"(\w+)(\?)?(?:\s*:\s*(.+))?", param)
                if param_match:
                    name = param_match.group(1)
                    optional = bool(param_match.group(2))
                    param_type = param_match.group(3)

                    props.append(
                        PropInfo(
                            name=name,
                            type=param_type.strip() if param_type else None,
                            optional=optional,
                        )
                    )

        return props

    def _extract_component_body(self, source: str, start_pos: int) -> str:
        """Extract the body of a component/function."""
        # Find the opening brace
        brace_pos = source.find("{", start_pos)
        if brace_pos == -1:
            return ""

        # Count braces to find matching closing brace
        depth = 0
        pos = brace_pos
        while pos < len(source):
            if source[pos] == "{":
                depth += 1
            elif source[pos] == "}":
                depth -= 1
                if depth == 0:
                    return source[brace_pos : pos + 1]
            pos += 1

        return source[brace_pos:]

    def _extract_hooks_and_state(
        self, component_body: str
    ) -> tuple[list[HookUsage], list[str]]:
        """Extract React hooks and state variables from component body."""
        hooks = []
        state_vars = []

        for match in self._hook_usage_pattern.finditer(component_body):
            # Extract variable names
            array_vars = match.group(1)  # [state, setState]
            object_vars = match.group(2)  # { value, setValue }
            simple_var = match.group(3)  # value
            hook_name = match.group(4)  # useState, useEffect, etc.

            variables = []
            if array_vars:
                # Parse [var1, var2]
                variables = [v.strip() for v in array_vars.split(",")]
            elif object_vars:
                # Parse { var1, var2 }
                variables = [v.strip() for v in object_vars.split(",")]
            elif simple_var:
                variables = [simple_var]

            # For useState, first variable is state
            if hook_name == "useState" and variables:
                state_vars.append(variables[0])

            hooks.append(HookUsage(name=hook_name, variables=variables))

        return hooks, state_vars

    def _extract_class_state(self, class_body: str) -> list[str]:
        """Extract state variables from class component."""
        state_vars = []

        # Look for state = { ... } or this.state = { ... }
        state_match = re.search(r"(?:this\.)?state\s*=\s*\{([^}]+)\}", class_body)
        if state_match:
            state_content = state_match.group(1)
            # Extract property names
            for prop in state_content.split(","):
                prop_match = re.match(r"(\w+)\s*:", prop.strip())
                if prop_match:
                    state_vars.append(prop_match.group(1))

        return state_vars

    def _extract_event_handlers(self, component_body: str) -> list[str]:
        """Extract event handler function names."""
        handlers = []

        # Pattern for handler functions: onClick={handleClick} or onClick={...}
        handler_pattern = re.compile(r"on\w+\s*=\s*\{(\w+)\}")

        for match in handler_pattern.finditer(component_body):
            handler_name = match.group(1)
            if handler_name not in handlers:
                handlers.append(handler_name)

        return handlers

    def _detect_edge_cases(self, source: str) -> list[dict[str, Any]]:
        """
        Detect edge case patterns for test scenario generation.

        Identifies:
        - Error boundaries (componentDidCatch, error states)
        - Conditional rendering (ternary, &&, ||)
        - Null/undefined checks
        - Loading states
        - Error handling (try/catch, .catch())
        - Form validation patterns
        """
        edge_cases = []
        lines = source.splitlines()

        for lineno, line in enumerate(lines, 1):
            # Detect null/undefined checks
            if re.search(r"(?:!==|===|==|!=)\s*(?:null|undefined)", line):
                edge_cases.append(
                    {
                        "type": "boundary_condition",
                        "pattern": "null_undefined_check",
                        "lineno": lineno,
                        "description": f"Null/undefined check: {line.strip()}",
                    }
                )

            # Detect loading states
            if re.search(r"(?:isLoading|loading|pending)", line, re.IGNORECASE):
                edge_cases.append(
                    {
                        "type": "state_condition",
                        "pattern": "loading_state",
                        "lineno": lineno,
                        "description": "Loading state handling",
                    }
                )

            # Detect error states
            if re.search(r"(?:isError|error|hasError)", line, re.IGNORECASE):
                edge_cases.append(
                    {
                        "type": "state_condition",
                        "pattern": "error_state",
                        "lineno": lineno,
                        "description": "Error state handling",
                    }
                )

            # Detect try/catch blocks
            if "try {" in line or "catch" in line:
                edge_cases.append(
                    {
                        "type": "error_handling",
                        "pattern": "try_catch",
                        "lineno": lineno,
                        "description": "Try/catch error handling",
                    }
                )

            # Detect conditional rendering
            if re.search(r"\?\s*<|\&\&\s*<", line):
                edge_cases.append(
                    {
                        "type": "conditional_rendering",
                        "pattern": "ternary_or_logical",
                        "lineno": lineno,
                        "description": f"Conditional rendering: {line.strip()}",
                    }
                )

            # Detect form validation
            if re.search(r"(?:validate|isValid|hasError|error)", line):
                edge_cases.append(
                    {
                        "type": "validation",
                        "pattern": "form_validation",
                        "lineno": lineno,
                        "description": "Form validation logic",
                    }
                )

        return edge_cases

    def _has_test_file(self, source_path: Path) -> bool:
        """Check if corresponding test file exists."""
        # Common test file patterns
        test_patterns = [
            source_path.with_suffix(".test.tsx"),
            source_path.with_suffix(".test.ts"),
            source_path.with_name(f"{source_path.stem}.test{source_path.suffix}"),
            source_path.parent
            / "__tests__"
            / f"{source_path.stem}.test{source_path.suffix}",
        ]

        return any(p.exists() for p in test_patterns)

    def _result_to_dict(self, result: AnalysisResult) -> dict[str, Any]:
        """Convert AnalysisResult to dictionary."""
        return {
            "file_path": result.file_path,
            "components": [
                {
                    "name": c.name,
                    "lineno": c.lineno,
                    "is_function_component": c.is_function_component,
                    "props": [
                        {
                            "name": p.name,
                            "type": p.type,
                            "optional": p.optional,
                            "default_value": p.default_value,
                        }
                        for p in c.props
                    ],
                    "state_variables": c.state_variables,
                    "hooks": [
                        {
                            "name": h.name,
                            "variables": h.variables,
                            "dependencies": h.dependencies,
                        }
                        for h in c.hooks
                    ],
                    "exported": c.exported,
                    "default_export": c.default_export,
                    "has_children": c.has_children,
                    "event_handlers": c.event_handlers,
                }
                for c in result.components
            ],
            "functions": [
                {
                    "name": f.name,
                    "lineno": f.lineno,
                    "params": [
                        {"name": p.name, "type": p.type, "optional": p.optional}
                        for p in f.params
                    ],
                    "return_type": f.return_type,
                    "is_async": f.is_async,
                    "is_hook": f.is_hook,
                    "exported": f.exported,
                }
                for f in result.functions
            ],
            "types": [
                {
                    "name": t.name,
                    "lineno": t.lineno,
                    "kind": t.kind,
                    "exported": t.exported,
                }
                for t in result.types
            ],
            "imports": result.imports,
            "has_tests": result.has_tests,
            "total_lines": result.total_lines,
            "edge_cases": result.edge_cases,
        }
