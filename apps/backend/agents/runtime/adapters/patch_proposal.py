"""Patch proposal runtime adapter."""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..capabilities import RuntimeCapabilities
from ..result import AgentRunResult
from .completion import CompletionRuntimeSession

SENSITIVE_PATH_PARTS = {
    ".git",
    ".claude",
    ".mcp.json",
    "secrets",
}
SENSITIVE_FILENAME_PREFIXES = (".env",)

PATCH_PROMPT_TEMPLATE = """\
You are running in Auto Code patch proposal mode.

You do not have tools, shell access, filesystem access, or MCP access. Use only
the context already present in the task prompt. Return exactly one JSON object
and no markdown fences.

The JSON object must match this shape:
{
  "summary": "Short description of the proposed change",
  "files": [
    {
      "path": "relative/path/from/project/root",
      "operation": "modify",
      "patch": "unified diff for this file"
    }
  ],
  "tests": ["suggested verification command, not executed automatically"],
  "risks": ["known risk or missing context"]
}

Patch rules:
- Use unified diff format.
- Paths must be relative to the project root.
- Do not modify .git, .claude, .mcp.json, .env files, shell profiles, secrets, or
  files outside the workspace.
- If there is not enough context to safely edit, return an empty "files" list
  and explain the missing context in "risks".

Original task prompt:
__AUTO_CODE_TASK_PROMPT__
"""


class PatchProposalError(RuntimeError):
    """Raised when a patch proposal cannot be validated or applied."""


class PatchProposalRuntimeSession:
    """Runtime that turns completion-model output into validated local patches."""

    name = "patch_proposal"
    capabilities = RuntimeCapabilities.patch_proposal()

    def __init__(
        self,
        *,
        provider_name: str,
        agent_session: Any,
        project_dir: Path,
    ):
        self.provider_name = provider_name
        self.agent_session = agent_session
        self.project_dir = project_dir
        self._completion_runtime = CompletionRuntimeSession(
            provider_name=provider_name,
            agent_session=agent_session,
        )

    @property
    def context_client(self) -> Any:
        return None

    async def run(
        self,
        *,
        message: str,
        spec_dir: Path,
        verbose: bool,
        phase: Any,
        subtask_id: str | None = None,
    ) -> AgentRunResult:
        del verbose, phase

        prompt = PATCH_PROMPT_TEMPLATE.replace("__AUTO_CODE_TASK_PROMPT__", message)
        proposal_text = await self._complete(prompt)
        proposal: dict[str, Any] | None = None
        patch = ""
        artifacts: dict[str, str] = {}
        try:
            proposal = parse_patch_proposal(proposal_text)
            patch = collect_patch_text(proposal)
            artifacts.update(
                save_patch_artifacts(
                    spec_dir=spec_dir,
                    provider_name=self.provider_name,
                    subtask_id=subtask_id,
                    proposal=proposal,
                    patch=patch,
                    raw_response=proposal_text,
                    status="proposed",
                )
            )

            if not patch.strip():
                risks = proposal.get("risks") or []
                risk_text = (
                    "; ".join(str(risk) for risk in risks) or "no patch returned"
                )
                artifacts.update(
                    save_patch_result_artifact(
                        spec_dir=spec_dir,
                        provider_name=self.provider_name,
                        subtask_id=subtask_id,
                        status="error",
                        message=(
                            "Patch proposal did not include changes: " + risk_text
                        ),
                        artifacts=artifacts,
                    )
                )
                return AgentRunResult(
                    status="error",
                    response_text=(
                        f"Patch proposal did not include changes: {risk_text}"
                    ),
                )

            validate_patch_paths(patch, self.project_dir)
            apply_git_patch(patch, self.project_dir)
        except PatchProposalError as e:
            artifacts.update(
                save_patch_result_artifact(
                    spec_dir=spec_dir,
                    provider_name=self.provider_name,
                    subtask_id=subtask_id,
                    status="error",
                    message=str(e),
                    artifacts=artifacts,
                    raw_response=proposal_text,
                    patch=patch,
                )
            )
            return AgentRunResult(
                status="error",
                response_text=f"Patch proposal failed: {e}",
            )

        summary = str(proposal.get("summary") or "Patch proposal applied")
        tests = proposal.get("tests") or []
        risks = proposal.get("risks") or []
        response_lines = [
            summary,
            "",
            f"Applied patch proposal with {len(proposal.get('files') or [])} file entry/entries.",
        ]
        if artifacts:
            response_lines.extend(["", "Artifacts:"])
            response_lines.extend(
                f"- {name}: {path}" for name, path in artifacts.items()
            )
        if tests:
            response_lines.extend(["", "Suggested verification commands:"])
            response_lines.extend(f"- {test}" for test in tests)
        if risks:
            response_lines.extend(["", "Risks:"])
            response_lines.extend(f"- {risk}" for risk in risks)

        artifacts.update(
            save_patch_result_artifact(
                spec_dir=spec_dir,
                provider_name=self.provider_name,
                subtask_id=subtask_id,
                status="applied",
                message=summary,
                artifacts=artifacts,
                tests=tests,
                risks=risks,
                patch=patch,
            )
        )

        return AgentRunResult(
            status="continue",
            response_text="\n".join(response_lines),
        )

    async def _complete(self, message: str) -> str:
        chunks: list[str] = []
        async for chunk in self._completion_runtime._stream_text(message):
            chunks.append(chunk)
        return "".join(chunks)


def parse_patch_proposal(text: str) -> dict[str, Any]:
    """Parse a model patch proposal JSON object."""
    candidate = _extract_json_object(text)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as e:
        raise PatchProposalError(f"Patch proposal is not valid JSON: {e}") from e

    if not isinstance(parsed, dict):
        raise PatchProposalError("Patch proposal must be a JSON object")

    files = parsed.get("files")
    if files is None:
        raise PatchProposalError("Patch proposal missing 'files'")
    if not isinstance(files, list):
        raise PatchProposalError("Patch proposal 'files' must be a list")

    for index, file_entry in enumerate(files):
        if not isinstance(file_entry, dict):
            raise PatchProposalError(f"Patch proposal file #{index + 1} is invalid")
        path = file_entry.get("path")
        if path is not None:
            validate_workspace_relative_path(str(path))
        patch = file_entry.get("patch")
        if patch is not None and not isinstance(patch, str):
            raise PatchProposalError(
                f"Patch proposal file #{index + 1} field 'patch' must be a string"
            )

    return parsed


def collect_patch_text(proposal: dict[str, Any]) -> str:
    """Collect unified diff text from a proposal."""
    top_level_patch = proposal.get("patch")
    patches: list[str] = []
    if isinstance(top_level_patch, str):
        patches.append(top_level_patch)

    for file_entry in proposal.get("files") or []:
        if isinstance(file_entry, dict) and isinstance(file_entry.get("patch"), str):
            patches.append(file_entry["patch"])

    return "\n".join(patch.strip("\n") for patch in patches if patch.strip())


def validate_patch_paths(patch: str, project_dir: Path) -> None:
    """Validate all paths referenced by a unified diff."""
    del project_dir
    paths = extract_patch_paths(patch)
    if not paths:
        raise PatchProposalError("Patch does not contain any file paths")

    for path in paths:
        validate_workspace_relative_path(path)


def extract_patch_paths(patch: str) -> set[str]:
    """Extract workspace paths from unified diff headers."""
    paths: set[str] = set()
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                paths.add(_clean_diff_path(parts[2]))
                paths.add(_clean_diff_path(parts[3]))
            continue

        if line.startswith("--- ") or line.startswith("+++ "):
            raw_path = line[4:].split("\t", 1)[0].strip()
            if raw_path != "/dev/null":
                paths.add(_clean_diff_path(raw_path))

    return {path for path in paths if path}


def validate_workspace_relative_path(path: str) -> None:
    """Reject paths that could escape or target sensitive workspace files."""
    cleaned = _clean_diff_path(path)
    candidate = Path(cleaned)

    if candidate.is_absolute():
        raise PatchProposalError(f"Patch path must be relative: {path}")
    if any(part in ("", ".", "..") for part in candidate.parts):
        raise PatchProposalError(f"Patch path contains unsafe segments: {path}")
    if any(part in SENSITIVE_PATH_PARTS for part in candidate.parts):
        raise PatchProposalError(f"Patch path targets sensitive file: {path}")
    if candidate.name.startswith(SENSITIVE_FILENAME_PREFIXES):
        raise PatchProposalError(f"Patch path targets sensitive file: {path}")


def apply_git_patch(patch: str, project_dir: Path) -> None:
    """Apply a validated unified diff using git apply."""
    if not patch.endswith("\n"):
        patch += "\n"

    check = subprocess.run(
        ["git", "apply", "--check", "--whitespace=nowarn", "-"],
        cwd=project_dir,
        input=patch,
        text=True,
        capture_output=True,
        timeout=30,
    )
    if check.returncode != 0:
        detail = check.stderr.strip() or check.stdout.strip()
        raise PatchProposalError(f"Patch failed validation: {detail}")

    applied = subprocess.run(
        ["git", "apply", "--whitespace=nowarn", "-"],
        cwd=project_dir,
        input=patch,
        text=True,
        capture_output=True,
        timeout=30,
    )
    if applied.returncode != 0:
        detail = applied.stderr.strip() or applied.stdout.strip()
        raise PatchProposalError(f"Patch failed to apply: {detail}")


def save_patch_artifacts(
    *,
    spec_dir: Path,
    provider_name: str,
    subtask_id: str | None,
    proposal: dict[str, Any],
    patch: str,
    raw_response: str,
    status: str,
) -> dict[str, str]:
    """Persist the latest patch proposal artifacts."""
    artifact_dir = spec_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).isoformat()
    proposal_path = artifact_dir / "patch_proposal.json"
    diff_path = artifact_dir / "patch.diff"

    proposal_payload = {
        "timestamp": timestamp,
        "provider": provider_name,
        "subtask_id": subtask_id,
        "status": status,
        "proposal": proposal,
        "raw_response": raw_response,
    }
    proposal_json = json.dumps(proposal_payload, indent=2, ensure_ascii=False)
    diff_text = patch if patch.endswith("\n") else f"{patch}\n"

    proposal_path.write_text(proposal_json, encoding="utf-8")
    diff_path.write_text(diff_text, encoding="utf-8")

    return {
        "patch_proposal": str(proposal_path),
        "patch_diff": str(diff_path),
    }


def save_patch_result_artifact(
    *,
    spec_dir: Path,
    provider_name: str,
    subtask_id: str | None,
    status: str,
    message: str,
    artifacts: dict[str, str] | None = None,
    tests: list[Any] | None = None,
    risks: list[Any] | None = None,
    raw_response: str | None = None,
    patch: str | None = None,
) -> dict[str, str]:
    """Persist the latest patch proposal result artifact."""
    artifact_dir = spec_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    result_path = artifact_dir / "patch_result.json"

    payload: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "provider": provider_name,
        "subtask_id": subtask_id,
        "status": status,
        "message": message,
        "artifacts": artifacts or {},
    }
    if tests is not None:
        payload["tests"] = tests
    if risks is not None:
        payload["risks"] = risks
    if raw_response is not None:
        payload["raw_response"] = raw_response
    if patch is not None:
        payload["patch"] = patch

    result_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {"patch_result": str(result_path)}


def _extract_json_object(text: str) -> str:
    stripped = _strip_markdown_fence(text)

    start = stripped.find("{")
    if start < 0:
        raise PatchProposalError("Patch proposal did not contain a JSON object")

    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(stripped[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return stripped[start : index + 1]

    raise PatchProposalError("Patch proposal did not contain a complete JSON object")


def _strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    lines = stripped.splitlines()
    if len(lines) < 2:
        return stripped

    opening = lines[0].strip().lower()
    closing = lines[-1].strip()
    if opening in {"```", "```json"} and closing == "```":
        return "\n".join(lines[1:-1]).strip()

    return stripped


def _clean_diff_path(path: str) -> str:
    cleaned = path.strip().strip('"')
    if cleaned.startswith("a/") or cleaned.startswith("b/"):
        cleaned = cleaned[2:]
    return cleaned
