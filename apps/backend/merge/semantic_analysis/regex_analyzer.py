"""
Regex-based semantic analysis for code changes.
"""

from __future__ import annotations

import difflib
import logging
import re

from ..rename_detector import is_function_rename
from ..scope_analyzer import infer_scope
from ..signature_parser import parse_function_signature
from ..types import ChangeType, FileAnalysis, SemanticChange

logger = logging.getLogger(__name__)


def extract_function_definitions(code: str, ext: str) -> dict[str, str]:
    """
    Extract full function definitions from code.

    Args:
        code: Source code
        ext: File extension

    Returns:
        Dictionary mapping function name to full definition (including body)

    Known limitations (TODO: switch to AST-based extraction):
        - Uses indentation heuristics that miss decorated functions (the decorator
          line is not included in the collected definition).
        - Multi-line signatures are not collected; only single-line ``def`` starters
          are detected, so the first line of the definition may be incomplete.
        - Class-level docstrings that appear at the same indent as the ``def`` can
          prematurely terminate body collection.
    """
    if ext != ".py":
        return {}

    definitions = {}
    lines = code.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]
        line_stripped = line.strip()

        # Match function definition
        if re.match(r"^(async\s+)?def\s+\w+", line_stripped):
            match = re.match(r"^(?:async\s+)?def\s+(\w+)\s*\(", line_stripped)
            if match:
                func_name = match.group(1)
                # Collect function body (simplified - just collect until we hit dedent)
                definition_lines = [line]
                i += 1
                # Get base indentation
                base_indent = len(line) - len(line.lstrip())

                # Collect all lines that are part of this function
                while i < len(lines):
                    next_line = lines[i]
                    if next_line.strip() == "":
                        definition_lines.append(next_line)
                        i += 1
                        continue

                    next_indent = len(next_line) - len(next_line.lstrip())

                    # If we see something at same or less indent, function ended
                    if next_indent <= base_indent:
                        break

                    definition_lines.append(next_line)
                    i += 1

                definitions[func_name] = "\n".join(definition_lines)
                continue

        i += 1

    return definitions


def _get_func_line_range(code: str, func_def: str) -> tuple[int, int]:
    """
    Return the 1-based (line_start, line_end) of func_def within code.

    Args:
        code: The source text to search within
        func_def: The function definition string to locate

    Returns:
        (line_start, line_end) tuple, or (1, 1) when not found
    """
    idx = code.find(func_def)
    if idx < 0:
        return 1, 1
    line_start = code[:idx].count("\n") + 1
    line_end = line_start + func_def.count("\n")
    return line_start, line_end


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

        # Check for renames before marking as add/remove
        # A rename looks like: remove old_name + add new_name with same structure
        removed_funcs = funcs_before - funcs_after
        added_funcs = funcs_after - funcs_before

        # For Python functions, check for renames using AST analysis
        if ext == ".py" and removed_funcs and added_funcs:
            # Extract full function definitions for rename detection
            func_defs_before = extract_function_definitions(before_normalized, ext)
            func_defs_after = extract_function_definitions(after_normalized, ext)

            # Check each removed+added pair for rename
            matched_adds = set()
            matched_removes = set()
            for removed_func in removed_funcs:
                for added_func in added_funcs:
                    if added_func in matched_adds:
                        continue

                    removed_def = func_defs_before.get(removed_func, "")
                    added_def = func_defs_after.get(added_func, "")

                    # Check if this is a rename (same structure, different name)
                    if (
                        removed_def
                        and added_def
                        and is_function_rename(removed_def, added_def)
                    ):
                        # This is a rename, not remove+add
                        location = f"function:{added_func}"
                        scope = infer_scope(added_func, location)
                        # Look up accurate line numbers from the stored definitions
                        added_start, added_end = _get_func_line_range(
                            after_normalized, added_def
                        )
                        changes.append(
                            SemanticChange(
                                change_type=ChangeType.RENAME_FUNCTION,
                                target=f"{removed_func}->{added_func}",
                                location=location,
                                line_start=added_start,
                                line_end=added_end,
                                content_before=removed_func,
                                content_after=added_func,
                                metadata={
                                    "old_name": removed_func,
                                    "new_name": added_func,
                                    "scope": scope,
                                },
                            )
                        )
                        matched_adds.add(added_func)
                        matched_removes.add(removed_func)
                        break

            # Filter out matched adds and removes
            added_funcs -= matched_adds
            removed_funcs -= matched_removes

        # Remaining adds are new functions
        for func in added_funcs:
            location = f"function:{func}"
            scope = infer_scope(func, location)
            changes.append(
                SemanticChange(
                    change_type=ChangeType.ADD_FUNCTION,
                    target=func,
                    location=location,
                    line_start=1,
                    line_end=1,
                    metadata={"scope": scope},
                )
            )

        # Remaining removes are deleted functions
        for func in removed_funcs:
            location = f"function:{func}"
            scope = infer_scope(func, location)
            changes.append(
                SemanticChange(
                    change_type=ChangeType.REMOVE_FUNCTION,
                    target=func,
                    location=location,
                    line_start=1,
                    line_end=1,
                    metadata={"scope": scope},
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
                        location = f"function:{func_name}"
                        scope = infer_scope(func_name, location)
                        metadata = {
                            "signature_before": sig_before,
                            "signature_after": sig_after,
                            "params_before": parsed_before.params,
                            "params_after": parsed_after.params,
                            "return_type_before": parsed_before.return_type,
                            "return_type_after": parsed_after.return_type,
                            "scope": scope,
                        }

                        changes.append(
                            SemanticChange(
                                change_type=ChangeType.MODIFY_FUNCTION,
                                target=func_name,
                                location=location,
                                line_start=1,  # Line info approximate for signature changes
                                line_end=1,
                                content_before=sig_before,
                                content_after=sig_after,
                                metadata=metadata,
                            )
                        )
                except ValueError:
                    # If signature parsing fails, skip detailed analysis
                    logger.debug(
                        "Signature parsing failed for function '%s': before=%r after=%r",
                        func_name,
                        sig_before,
                        sig_after,
                    )

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

    Handles both single-line and multi-line function signatures by accumulating
    continuation lines until the opening parenthesis is balanced.

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
    i = 0

    while i < len(lines):
        line_stripped = lines[i].strip()
        # Match start of a function definition
        if re.match(r"^(async\s+)?def\s+\w+", line_stripped):
            match = re.match(r"^(?:async\s+)?def\s+(\w+)\s*\(", line_stripped)
            if match:
                func_name = match.group(1)
                # Accumulate lines until parentheses balance (handles multiline sigs)
                sig_parts = [line_stripped]
                depth = line_stripped.count("(") - line_stripped.count(")")
                j = i + 1
                while depth > 0 and j < len(lines):
                    next_stripped = lines[j].strip()
                    depth += next_stripped.count("(") - next_stripped.count(")")
                    sig_parts.append(next_stripped)
                    j += 1
                # Normalise to a single line; with whitespace pre-normalised,
                # use simple fixed-space patterns to avoid adjacent optional
                # quantifiers that can cause polynomial regex backtracking.
                full_sig = re.sub(r"\s+", " ", " ".join(sig_parts))
                sig_match = re.match(
                    r"^(async )?def \w+ ?\([^)]*\)(?: -> [^:]+)?:",
                    full_sig,
                )
                if sig_match:
                    signatures[func_name] = sig_match.group(0)
                i = j
                continue
        i += 1

    return signatures
