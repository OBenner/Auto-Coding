"""CLI command for text-only provider analysis."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from agents.runtime import (
    RuntimeRequirements,
    create_runtime_session,
    run_runtime_session,
)
from agents.runtime.artifacts import save_analysis_only_artifact
from core.providers.base import SessionConfig
from core.providers.config import ProviderConfig
from core.providers.factory import create_engine_provider
from task_logger import LogPhase
from ui import print_key_value, print_status

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 24_000


def _read_optional_text(path: Path, *, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """Read a context file with a small safety cap."""
    if not path.exists() or not path.is_file():
        return ""

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        logger.debug("Could not read analysis context file %s: %s", path, e)
        return ""

    if len(content) <= max_chars:
        return content
    return content[:max_chars] + "\n\n[Truncated for analysis prompt]\n"


def build_analysis_prompt(
    *,
    spec_dir: Path,
    project_dir: Path,
    user_prompt: str | None = None,
) -> str:
    """Build a non-mutating analysis prompt from spec artifacts."""
    spec_text = _read_optional_text(spec_dir / "spec.md")
    plan_text = _read_optional_text(spec_dir / "implementation_plan.json")
    qa_text = _read_optional_text(spec_dir / "qa_report.md", max_chars=8_000)

    request = (
        user_prompt.strip()
        if user_prompt and user_prompt.strip()
        else (
            "Analyze this spec and implementation state. Identify likely edit "
            "areas, risks, dependencies, and concrete next steps. Do not modify "
            "files or claim implementation is complete."
        )
    )

    sections = [
        "# Auto Code Analysis Request",
        "",
        (
            "You are running in analysis-only mode. Do not edit files, run tools, or "
            "claim the implementation is complete. Produce useful engineering "
            "guidance for the next coding step."
        ),
        "",
        f"Project name: {project_dir.name}",
        f"Spec name: {spec_dir.name}",
        "",
        "## User Request",
        request,
    ]

    if spec_text:
        sections.extend(["", "## spec.md", spec_text])
    if plan_text:
        sections.extend(["", "## implementation_plan.json", plan_text])
    if qa_text:
        sections.extend(["", "## qa_report.md", qa_text])

    return "\n".join(sections)


async def run_analysis_only_session(
    *,
    project_dir: Path,
    spec_dir: Path,
    model: str | None,
    user_prompt: str | None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Run one text-only analysis session and persist its output."""
    provider_name = "unknown"
    try:
        provider_config = ProviderConfig.from_env(agent_type="analysis")
        provider = create_engine_provider(provider_config)
        provider_name = provider.name
        session_config = SessionConfig(
            name="analysis-session",
            model=model,
            extra={"agent_type": "analysis"},
        )

        if provider.name == "claude":
            from agents.session import run_agent_session

            session = provider.create_session(
                session_config,
                project_dir=project_dir,
                spec_dir=spec_dir,
                agent_type="planner",
            )
            runtime_session = create_runtime_session(
                provider_name=provider.name,
                agent_session=session,
                claude_session_runner=run_agent_session,
                runtime_mode="analysis_only",
                project_dir=project_dir,
            )
        else:
            session = provider.create_session(session_config)
            runtime_session = create_runtime_session(
                provider_name=provider.name,
                agent_session=session,
                runtime_mode="analysis_only",
                project_dir=project_dir,
            )

        prompt = build_analysis_prompt(
            spec_dir=spec_dir,
            project_dir=project_dir,
            user_prompt=user_prompt,
        )
        result = await run_runtime_session(
            runtime_session,
            prompt,
            spec_dir,
            verbose=verbose,
            phase=LogPhase.PLANNING,
            requirements=RuntimeRequirements.text_only(),
        )
        artifact_path = save_analysis_only_artifact(
            spec_dir=spec_dir,
            response_text=result.response_text,
            provider_name=provider.name,
            phase="analysis",
            session_num=1,
        )
    except Exception as e:
        logger.error("Analysis-only runtime failed", exc_info=True)
        return {
            "status": "error",
            "provider": provider_name,
            "runtime_mode": "analysis_only",
            "artifact": "",
            "response": f"Analysis-only runtime failed: {e}",
        }

    return {
        "status": result.status,
        "provider": provider.name,
        "runtime_mode": "analysis_only",
        "artifact": str(artifact_path),
        "response": result.response_text,
    }


def handle_analysis_command(
    *,
    project_dir: Path,
    spec_dir: Path,
    model: str | None,
    user_prompt: str | None,
    verbose: bool = False,
    output_json: bool = False,
) -> dict[str, Any]:
    """Run a non-mutating provider analysis pass for a spec."""
    result = asyncio.run(
        run_analysis_only_session(
            project_dir=project_dir,
            spec_dir=spec_dir,
            model=model,
            user_prompt=user_prompt,
            verbose=verbose,
        )
    )

    if output_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        status_style = "success" if result["status"] != "error" else "error"
        status_text = (
            "Analysis-only pass complete"
            if result["status"] != "error"
            else "Analysis-only pass failed"
        )
        print_status(status_text, status_style)
        print_key_value("Provider", result["provider"])
        if result["artifact"]:
            print_key_value("Artifact", result["artifact"])
        print()
        response = str(result["response"]).strip()
        if response:
            print(response)

    return result
