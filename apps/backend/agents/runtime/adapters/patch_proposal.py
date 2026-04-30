"""Patch proposal runtime adapter."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.platform import run_process

from ..capabilities import RuntimeCapabilities
from ..result import AgentRunResult
from .completion import CompletionRuntimeSession
from .json_helpers import extract_first_json_object

SENSITIVE_PATH_PARTS = {
    ".git",
    ".claude",
    ".mcp.json",
    ".ssh",
    "secrets",
}
SENSITIVE_FILENAME_PREFIXES = (
    ".env",
    ".bashrc",
    ".bash_profile",
    ".profile",
    ".zshrc",
    ".zprofile",
    ".netrc",
    ".npmrc",
    ".pypirc",
)

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
                        files=describe_proposal_files(proposal),
                        tests=normalize_string_list(proposal.get("tests")),
                        risks=normalize_string_list(proposal.get("risks")),
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
                    files=describe_proposal_files(proposal),
                    tests=normalize_string_list(proposal.get("tests"))
                    if proposal
                    else None,
                    risks=normalize_string_list(proposal.get("risks"))
                    if proposal
                    else None,
                    raw_response=proposal_text,
                    patch=patch,
                )
            )
            return AgentRunResult(
                status="error",
                response_text=f"Patch proposal failed: {e}",
            )

        summary = str(proposal.get("summary") or "Patch proposal applied")
        files = describe_proposal_files(proposal)
        tests = normalize_string_list(proposal.get("tests"))
        risks = normalize_string_list(proposal.get("risks"))

        artifacts.update(
            save_patch_result_artifact(
                spec_dir=spec_dir,
                provider_name=self.provider_name,
                subtask_id=subtask_id,
                status="applied",
                message=summary,
                artifacts=artifacts,
                files=files,
                tests=tests,
                risks=risks,
                patch=patch,
            )
        )
        artifacts.update(
            save_patch_summary_artifact(
                spec_dir=spec_dir,
                provider_name=self.provider_name,
                subtask_id=subtask_id,
                status="applied",
                summary=summary,
                files=files,
                tests=tests,
                risks=risks,
                artifacts=artifacts,
            )
        )

        response_lines = build_patch_response(
            summary=summary,
            files=files,
            tests=tests,
            risks=risks,
            artifacts=artifacts,
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


def normalize_string_list(value: Any) -> list[str]:
    """Normalize model-provided scalar/list values into display strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def describe_proposal_files(proposal: dict[str, Any] | None) -> list[dict[str, str]]:
    """Return stable file metadata for artifacts and user output."""
    if not proposal:
        return []

    files: list[dict[str, str]] = []
    for file_entry in proposal.get("files") or []:
        if not isinstance(file_entry, dict):
            continue
        path = file_entry.get("path")
        if path is None:
            continue
        files.append(
            {
                "path": str(path),
                "operation": str(file_entry.get("operation") or "modify"),
            }
        )
    return files


def build_patch_response(
    *,
    summary: str,
    files: list[dict[str, str]],
    tests: list[str],
    risks: list[str],
    artifacts: dict[str, str],
) -> list[str]:
    """Build concise user-facing patch proposal output."""
    response_lines = [
        summary,
        "",
        f"Applied patch proposal with {len(files)} file entry/entries.",
    ]
    if files:
        response_lines.extend(["", "Files:"])
        response_lines.extend(
            f"- {file['operation']}: {file['path']}" for file in files
        )
    if artifacts:
        response_lines.extend(["", "Artifacts:"])
        response_lines.extend(f"- {name}: {path}" for name, path in artifacts.items())
    if tests:
        response_lines.extend(["", "Suggested verification commands:"])
        response_lines.extend(f"- {test}" for test in tests)
    if risks:
        response_lines.extend(["", "Risks:"])
        response_lines.extend(f"- {risk}" for risk in risks)
    return response_lines


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

    check = run_process(
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

    applied = run_process(
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
    files: list[dict[str, str]] | None = None,
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
    if files is not None:
        payload["files"] = files
        payload["file_count"] = len(files)
    if tests is not None:
        payload["tests"] = tests
        payload["test_count"] = len(tests)
    if risks is not None:
        payload["risks"] = risks
        payload["risk_count"] = len(risks)
    if raw_response is not None:
        payload["raw_response"] = raw_response
    if patch is not None:
        payload["patch"] = patch

    result_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {"patch_result": str(result_path)}


def save_patch_summary_artifact(
    *,
    spec_dir: Path,
    provider_name: str,
    subtask_id: str | None,
    status: str,
    summary: str,
    files: list[dict[str, str]],
    tests: list[str],
    risks: list[str],
    artifacts: dict[str, str],
) -> dict[str, str]:
    """Persist a human-readable patch proposal summary."""
    artifact_dir = spec_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    summary_path = artifact_dir / "patch_summary.md"

    lines = [
        "# Patch Proposal Summary",
        "",
        f"Status: {status}",
        f"Provider: {provider_name}",
    ]
    if subtask_id:
        lines.append(f"Subtask: {subtask_id}")
    lines.extend(["", "## Summary", "", summary])

    if files:
        lines.extend(["", "## Files", ""])
        lines.extend(f"- `{file['operation']}` `{file['path']}`" for file in files)

    if tests:
        lines.extend(["", "## Suggested Verification Commands", ""])
        lines.extend(f"- `{test}`" for test in tests)

    if risks:
        lines.extend(["", "## Risks", ""])
        lines.extend(f"- {risk}" for risk in risks)

    if artifacts:
        lines.extend(["", "## Artifacts", ""])
        lines.extend(f"- `{name}`: `{path}`" for name, path in artifacts.items())

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"patch_summary": str(summary_path)}


def _extract_json_object(text: str) -> str:
    return extract_first_json_object(
        text,
        strip_fence=_strip_markdown_fence,
        error_factory=PatchProposalError,
        missing_message="Patch proposal did not contain a JSON object",
        incomplete_message="Patch proposal did not contain a complete JSON object",
    )


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
