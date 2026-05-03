"""
Codex CLI provider adapter.

This provider is intentionally separate from the direct OpenAI API provider:
Codex account login is stored in CODEX_HOME and executed through `codex exec`,
while OpenAI direct API calls require OPENAI_API_KEY.
"""

from __future__ import annotations

import os
import shutil
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

from core.providers.base import AgentSession, AIEngineProvider, SessionConfig
from core.providers.config import DEFAULT_CODEX_MODEL, ProviderConfig
from core.providers.exceptions import ProviderConfigError

CODEX_MODELS = [
    DEFAULT_CODEX_MODEL,
    "gpt-5.3-codex",
    "gpt-5.5",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
]


def _resolve_codex_command(explicit_path: str = "") -> str | None:
    if explicit_path:
        expanded = Path(explicit_path).expanduser()
        if expanded.exists():
            return str(expanded)
    return shutil.which("codex")


def _resolve_codex_home(config: ProviderConfig) -> str:
    codex_home = config.codex_home or os.environ.get("CODEX_HOME", "~/.codex")
    return str(Path(codex_home).expanduser())


def _has_codex_auth_material(codex_home: str) -> bool:
    home = Path(codex_home).expanduser()
    return any(
        (home / filename).exists() for filename in ("auth.json", "credentials.json")
    )


class CodexCliSession(AgentSession):
    """Session wrapper for Codex CLI execution."""

    def __init__(
        self,
        *,
        session_id: str,
        codex_command: str,
        codex_home: str,
        model: str,
        resume_session_id: str | None = None,
        resume_last: bool = False,
    ):
        super().__init__(session_id, provider_name="codex")
        self.codex_command = codex_command
        self.codex_home = codex_home
        self.model = model
        self.codex_resume_session_id = resume_session_id
        self.codex_resume_last = resume_last

    @property
    def context_client(self) -> None:
        return None


class CodexCliProvider(AIEngineProvider):
    """Provider adapter for authenticated Codex CLI accounts."""

    def __init__(self, config: ProviderConfig):
        self._config = config
        self._validation_errors: list[str] = []

    @property
    def name(self) -> str:
        return "codex"

    def create_session(self, config: SessionConfig) -> CodexCliSession:
        if not self.validate_config():
            raise ProviderConfigError(
                "Invalid Codex CLI provider configuration: "
                + "; ".join(self._validation_errors)
            )

        command = _resolve_codex_command(self._config.codex_cli_path)
        if command is None:
            raise ProviderConfigError("Codex CLI executable was not found")

        model = config.model or self._config.codex_model or DEFAULT_CODEX_MODEL
        extra = config.extra or {}
        return CodexCliSession(
            session_id=f"codex-{uuid.uuid4().hex[:12]}",
            codex_command=command,
            codex_home=_resolve_codex_home(self._config),
            model=model,
            resume_session_id=(
                extra.get("codex_resume_session_id") or extra.get("resume_session_id")
            ),
            resume_last=bool(
                extra.get("codex_resume_last") or extra.get("resume_last")
            ),
        )

    async def send_message(self, message: str) -> AsyncIterator[str]:
        raise NotImplementedError(
            "Codex CLI provider is executed through the codex runtime adapter"
        )

    def get_supported_models(self) -> list[str]:
        return CODEX_MODELS

    def validate_config(self) -> bool:
        self._validation_errors = []
        if not _resolve_codex_command(self._config.codex_cli_path):
            self._validation_errors.append("codex CLI executable was not found")
        codex_home = _resolve_codex_home(self._config)
        if not _has_codex_auth_material(codex_home):
            self._validation_errors.append(
                f"Codex login credentials were not found in CODEX_HOME={codex_home}"
            )
        return not self._validation_errors

    def get_validation_errors(self) -> list[str]:
        if not self._validation_errors:
            self.validate_config()
        return self._validation_errors
