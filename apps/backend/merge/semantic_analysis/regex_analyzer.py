"""
Regex-based semantic analysis for code changes.
"""

from __future__ import annotations

import difflib
import re

from ..signature_parser import parse_function_signature
from ..types import ChangeType, FileAnalysis, SemanticChange


def analyze_with_regex(
    file_path: str,
    before: str,
    after: str,
    ext: str,
) -> FileAnalysis:
    """
    Analyze code changes using regex patterns.

    Args:
        file_path: Path to the file being analyzed
        before: Content before changes
        after: Content after changes
        ext: File extension

    Returns:
        FileAnalysis with changes detected via regex patterns
    """
    changes: list[SemanticChange] = []

    # Normalize line endings to LF for consistent cross-platform behavior
    # This handles Windows CRLF, old Mac CR, and Unix LF
    before_normalized = before.replace("\r\n", "\n").replace("\r", "\n")
    after_normalized = after.replace("\r\n", "\n").replace("\r", "\n")

    # Get a unified diff
    diff = list(
        difflib.unified_diff(
            before_normalized.splitlines(keepends=True),
            after_normalized.splitlines(keepends=True),
            lineterm="",
        )
    )

    # Analyze the diff for patterns
    added_lines: list[tuple[int, str]] = []
    removed_lines: list[tuple[int, str]] = []
    current_line = 0

    for line in diff:
        if line.startswith("@@"):
            # Parse the line numbers
            match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", line)
            if match:
                current_line = int(match.group(1))
        elif line.startswith("+") and not line.startswith("+++"):
            added_lines.append((current_line, line[1:]))
            current_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed_lines.append((current_line, line[1:]))
        elif not line.startswith("-"):
            current_line += 1

    # Detect imports
    import_pattern = get_import_pattern(ext)
    for line_num, line in added_lines:
        if import_pattern and import_pattern.match(line.strip()):
            changes.append(
                SemanticChange(
                    change_type=ChangeType.ADD_IMPORT,
                    target=line.strip(),
                    location="file_top",
                    line_start=line_num,
                    line_end=line_num,
                    content_after=line,
                )
            )

    for line_num, line in removed_lines:
        if import_pattern and import_pattern.match(line.strip()):
            changes.append(
                SemanticChange(
                    change_type=ChangeType.REMOVE_IMPORT,
                    target=line.strip(),
                    location="file_top",
                    line_start=line_num,
                    line_end=line_num,
                    content_before=line,
                )
            )

    # Detect function changes (simplified)
    func_pattern = get_function_pattern(ext)
    if func_pattern:
        # For JS/TS patterns with alternation, findall() returns tuples
        # Extract the non-empty match from each tuple
        def extract_func_names(matches):
            names = set()
            for match in matches:
                if isinstance(match, tuple):
                    # Get the first non-empty group from the tuple
                    name = next((m for m in match if m), None)
                    if name:
                        names.add(name)
                elif match:
                    names.add(match)
            return names

        funcs_before = extract_func_names(func_pattern.findall(before_normalized))
        funcs_after = extract_func_names(func_pattern.findall(after_normalized))

        for func in funcs_after - funcs_before:
            changes.append(
                SemanticChange(
                    change_type=ChangeType.ADD_FUNCTION,
                    target=func,
                    location=f"function:{func}",
                    line_start=1,
                    line_end=1,
                )
            )

        for func in funcs_before - funcs_after:
            changes.append(
                SemanticChange(
                    change_type=ChangeType.REMOVE_FUNCTION,
                    target=func,
                    location=f"function:{func}",
                    line_start=1,
                    line_end=1,
                )
            )

        # Detect signature modifications for Python functions
        if ext == ".py":
            sigs_before = extract_function_signatures(before_normalized, ext)
            sigs_after = extract_function_signatures(after_normalized, ext)

            # Find functions that exist in both but have different signatures
            common_funcs = set(sigs_before.keys()) & set(sigs_after.keys())
            for func_name in common_funcs:
                sig_before = sigs_before[func_name]
                sig_after = sigs_after[func_name]

                # Check if signatures actually differ (including return types)
                # Note: We don't use signatures_match() because it ignores return types
                try:
                    parsed_before = parse_function_signature(sig_before)
                    parsed_after = parse_function_signature(sig_after)

                    # Compare all aspects: name (already same), params, return type
                    sig_differs = (
                        parsed_before.params != parsed_after.params
                        or parsed_before.return_type != parsed_after.return_type
                    )

                    if sig_differs:
                        # Store signature details in metadata
                        metadata = {
                            "signature_before": sig_before,
                            "signature_after": sig_after,
                            "params_before": parsed_before.params,
                            "params_after": parsed_after.params,
                            "return_type_before": parsed_before.return_type,
                            "return_type_after": parsed_after.return_type,
                        }

                        changes.append(
                            SemanticChange(
                                change_type=ChangeType.MODIFY_FUNCTION,
                                target=func_name,
                                location=f"function:{func_name}",
                                line_start=1,  # Line info approximate for signature changes
                                line_end=1,
                                content_before=sig_before,
                                content_after=sig_after,
                                metadata=metadata,
                            )
                        )
                except ValueError:
                    # If signature parsing fails, skip detailed analysis
                    pass

    # Build analysis
    analysis = FileAnalysis(file_path=file_path, changes=changes)

    for change in changes:
        if change.change_type == ChangeType.ADD_IMPORT:
            analysis.imports_added.add(change.target)
        elif change.change_type == ChangeType.REMOVE_IMPORT:
            analysis.imports_removed.add(change.target)
        elif change.change_type == ChangeType.ADD_FUNCTION:
            analysis.functions_added.add(change.target)
        elif change.change_type == ChangeType.MODIFY_FUNCTION:
            analysis.functions_modified.add(change.target)

    analysis.total_lines_changed = len(added_lines) + len(removed_lines)

    return analysis


def get_import_pattern(ext: str) -> re.Pattern | None:
    """
    Get the import pattern for a file extension.

    Args:
        ext: File extension

    Returns:
        Compiled regex pattern for import statements, or None if not supported
    """
    patterns = {
        ".py": re.compile(r"^(?:from\s+\S+\s+)?import\s+"),
        ".js": re.compile(r"^import\s+"),
        ".jsx": re.compile(r"^import\s+"),
        ".ts": re.compile(r"^import\s+"),
        ".tsx": re.compile(r"^import\s+"),
    }
    return patterns.get(ext)


def get_function_pattern(ext: str) -> re.Pattern | None:
    """
    Get the function definition pattern for a file extension.

    Args:
        ext: File extension

    Returns:
        Compiled regex pattern for function definitions, or None if not supported
    """
    patterns = {
        ".py": re.compile(r"def\s+(\w+)\s*\("),
        ".js": re.compile(
            r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>))"
        ),
        ".jsx": re.compile(
            r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>))"
        ),
        ".ts": re.compile(
            r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*(?::\s*\w+)?\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>))"
        ),
        ".tsx": re.compile(
            r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*(?::\s*\w+)?\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>))"
        ),
    }
    return patterns.get(ext)


def extract_function_signatures(code: str, ext: str) -> dict[str, str]:
    """
    Extract function signatures from code.

    Args:
        code: Source code to parse
        ext: File extension

    Returns:
        Dictionary mapping function name to full signature line (including colon)
    """
    if ext != ".py":
        # Only Python signature parsing is currently supported
        return {}

    signatures = {}
    lines = code.split("\n")

    for line in lines:
        line_stripped = line.strip()
        # Match function definition lines
        if re.match(r"^(async\s+)?def\s+\w+", line_stripped):
            # Extract function name
            match = re.match(r"^(?:async\s+)?def\s+(\w+)\s*\(", line_stripped)
            if match:
                func_name = match.group(1)
                # Extract only the signature portion (up to and including colon)
                # This ensures we get "def foo(x):" not "def foo(x): pass"
                sig_match = re.match(r"^(async\s+)?def\s+\w+\s*\(.*?\)\s*(?:->\s*[^:]+)?\s*:", line_stripped)
                if sig_match:
                    signatures[func_name] = sig_match.group(0)

    return signatures