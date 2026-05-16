"""Language-specific extraction helpers for codebase intelligence."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from .models import CodeDependency, CodeReference, CodeSymbol

PYTHON_EXTENSIONS = {".py"}
TYPESCRIPT_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx"}
SUPPORTED_EXTENSIONS = PYTHON_EXTENSIONS | TYPESCRIPT_EXTENSIONS


def detect_language(path: Path) -> str | None:
    """Return the supported language name for a file path."""
    suffix = path.suffix.lower()
    if suffix in PYTHON_EXTENSIONS:
        return "python"
    if suffix in TYPESCRIPT_EXTENSIONS:
        return "typescript"
    return None


def extract_python_file(
    path: Path,
    rel_path: str,
) -> tuple[list[CodeSymbol], list[CodeDependency], list[CodeReference]]:
    """Extract Python symbols and import dependencies using stdlib AST."""
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError, UnicodeDecodeError):
        return [], [], []

    symbols: list[CodeSymbol] = []
    dependencies: list[CodeDependency] = []
    references = _extract_python_references(tree, rel_path)

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            symbols.append(_python_class_symbol(node, rel_path))
            for child in node.body:
                if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                    symbols.append(_python_function_symbol(child, rel_path, node.name))
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            symbols.append(_python_function_symbol(node, rel_path, None))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                dependencies.append(
                    CodeDependency(
                        source_path=rel_path,
                        target=alias.name,
                        kind="python_import",
                        line=node.lineno,
                        imported_names=[],
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            names = [alias.name for alias in node.names]
            dependencies.append(
                CodeDependency(
                    source_path=rel_path,
                    target=node.module or "",
                    kind="python_import",
                    line=node.lineno,
                    imported_names=names,
                    metadata={
                        "is_relative": node.level > 0,
                        "level": node.level,
                    },
                )
            )

    return symbols, dependencies, references


def extract_typescript_file(
    path: Path, rel_path: str
) -> tuple[list[CodeSymbol], list[CodeDependency], list[CodeReference]]:
    """Extract TypeScript/JavaScript symbols and module dependencies."""
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return [], [], []

    symbols = _extract_typescript_symbols(source, rel_path)
    dependencies = _extract_typescript_dependencies(source, rel_path)
    references = _extract_typescript_references(source, rel_path)
    return symbols, dependencies, references


def _python_class_symbol(node: ast.ClassDef, rel_path: str) -> CodeSymbol:
    return CodeSymbol(
        name=node.name,
        kind="class",
        file_path=rel_path,
        line=node.lineno,
        end_line=getattr(node, "end_lineno", None),
        language="python",
        signature=f"class {node.name}",
        docstring=ast.get_docstring(node),
    )


def _python_function_symbol(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    rel_path: str,
    container: str | None,
) -> CodeSymbol:
    args = [arg.arg for arg in node.args.args]
    prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    name = f"{container}.{node.name}" if container else node.name
    return CodeSymbol(
        name=name,
        kind="method" if container else "function",
        file_path=rel_path,
        line=node.lineno,
        end_line=getattr(node, "end_lineno", None),
        container=container,
        language="python",
        signature=f"{prefix}def {node.name}({', '.join(args)})",
        docstring=ast.get_docstring(node),
    )


def _extract_python_references(tree: ast.AST, rel_path: str) -> list[CodeReference]:
    visitor = _PythonReferenceVisitor(rel_path)
    visitor.visit(tree)
    return visitor.references


class _PythonReferenceVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.container_stack: list[str] = []
        self.references: list[CodeReference] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.container_stack.append(node.name)
        self.generic_visit(node)
        self.container_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = _python_call_name(node.func)
        if name:
            self.references.append(
                CodeReference(
                    name=name,
                    kind="call",
                    file_path=self.rel_path,
                    line=node.lineno,
                    container=self._container_name(),
                )
            )
        self.generic_visit(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.container_stack.append(node.name)
        self.generic_visit(node)
        self.container_stack.pop()

    def _container_name(self) -> str | None:
        if not self.container_stack:
            return None
        if len(self.container_stack) >= 2:
            return ".".join(self.container_stack[-2:])
        return self.container_stack[-1]


def _python_call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _python_call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


_TS_DEPENDENCY_RE = re.compile(
    r"\b(?:import|export)\s+(?:type\s+)?(?:[\w*{}\s,]+?\s+from\s+)?[\"']([^\"']+)[\"']"
)
_TS_REQUIRE_RE = re.compile(r"\brequire\(\s*[\"']([^\"']+)[\"']\s*\)")
_TS_NAMED_DECL_RE = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:(async)\s+)?"
    r"(function|class|interface|type)\s+([A-Za-z_$][\w$]*)"
)
_TS_CONST_RE = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*="
    r"\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>"
)
_TS_CALL_RE = re.compile(r"\b([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)?)\s*\(")
_TS_CALL_KEYWORDS = {
    "catch",
    "for",
    "function",
    "if",
    "require",
    "return",
    "switch",
    "while",
}


def _extract_typescript_dependencies(source: str, rel_path: str) -> list[CodeDependency]:
    dependencies: list[CodeDependency] = []
    for line_no, line in enumerate(source.splitlines(), 1):
        for match in _TS_DEPENDENCY_RE.finditer(line):
            dependencies.append(
                CodeDependency(
                    source_path=rel_path,
                    target=match.group(1),
                    kind="typescript_import",
                    line=line_no,
                )
            )
        for match in _TS_REQUIRE_RE.finditer(line):
            dependencies.append(
                CodeDependency(
                    source_path=rel_path,
                    target=match.group(1),
                    kind="typescript_import",
                    line=line_no,
                )
            )
    return dependencies


def _extract_typescript_symbols(source: str, rel_path: str) -> list[CodeSymbol]:
    symbols: list[CodeSymbol] = []
    for line_no, line in enumerate(source.splitlines(), 1):
        named_match = _TS_NAMED_DECL_RE.match(line)
        if named_match:
            declaration_kind = named_match.group(2)
            symbol_name = named_match.group(3)
            symbols.append(
                CodeSymbol(
                    name=symbol_name,
                    kind="function" if declaration_kind == "function" else declaration_kind,
                    file_path=rel_path,
                    line=line_no,
                    language="typescript",
                    signature=line.strip().rstrip("{").strip(),
                )
            )
            continue

        const_match = _TS_CONST_RE.match(line)
        if const_match:
            symbols.append(
                CodeSymbol(
                    name=const_match.group(1),
                    kind="function",
                    file_path=rel_path,
                    line=line_no,
                    language="typescript",
                    signature=line.strip().rstrip("{").strip(),
                )
            )

    return symbols


def _extract_typescript_references(source: str, rel_path: str) -> list[CodeReference]:
    references: list[CodeReference] = []
    container: str | None = None
    for line_no, line in enumerate(source.splitlines(), 1):
        named_match = _TS_NAMED_DECL_RE.match(line)
        const_match = _TS_CONST_RE.match(line)
        if named_match:
            container = named_match.group(3)
        elif const_match:
            container = const_match.group(1)

        for match in _TS_CALL_RE.finditer(line):
            name = match.group(1)
            if name in _TS_CALL_KEYWORDS:
                continue
            references.append(
                CodeReference(
                    name=name,
                    kind="call",
                    file_path=rel_path,
                    line=line_no,
                    container=container,
                )
            )
    return references
