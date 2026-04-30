"""
OpenAI-Compatible Base Classes
===============================

Provides base session and provider classes for any provider that uses
the OpenAI-compatible API (OpenAI, Ollama, etc.).

This avoids code duplication across adapters that share the same
streaming/completion logic.
"""

import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from core.providers.base import (
    AgentSession,
    AIEngineProvider,
    ProviderToolCall,
    ProviderToolCallResponse,
    SessionConfig,
)
from core.providers.exceptions import (
    ProviderConfigError,
    ProviderError,
    ProviderNotInstalled,
)

if TYPE_CHECKING:
    from core.providers.config import ProviderConfig

logger = logging.getLogger(__name__)


class OpenAICompatibleSession(AgentSession):
    """Base session for providers using the OpenAI-compatible API.

    Handles conversation history, lazy client creation, streaming,
    and non-streaming completions. Subclasses only need to override
    ``_build_client_kwargs`` to customise the ``AsyncOpenAI`` constructor.
    """

    def __init__(
        self,
        session_id: str,
        provider_name: str,
        model: str,
        system_prompt: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        super().__init__(session_id, provider_name=provider_name)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._messages: list[dict[str, Any]] = []
        self._client: Any = None

        if system_prompt:
            self._messages.append({"role": "system", "content": system_prompt})

    @property
    def model(self) -> str:
        return self._model

    @property
    def messages(self) -> list[dict[str, Any]]:
        return self._messages.copy()

    def _build_client_kwargs(self) -> dict[str, Any]:
        """Return kwargs for ``AsyncOpenAI(**kwargs)``.

        Subclasses must override to supply at least ``api_key``.
        """
        raise NotImplementedError

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as e:
                raise ProviderNotInstalled(
                    f"{self.provider_name.capitalize()} provider requires the openai package. "
                    "Install with: pip install openai\n"
                    f"Error: {e}"
                )
            self._client = AsyncOpenAI(**self._build_client_kwargs())
        return self._client

    def add_user_message(self, content: str) -> None:
        self._messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        self._messages.append({"role": "assistant", "content": content})

    def add_tool_result(self, tool_call_id: str, name: str, result: Any) -> None:
        """Append a provider-native tool result to the session history."""
        content = result if isinstance(result, str) else json.dumps(result)
        self._messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": name,
                "content": content,
            }
        )

    def _completion_kwargs(self, *, stream: bool) -> dict[str, Any]:
        """Build common chat completion arguments."""
        completion_kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": self._messages,
            "stream": stream,
        }

        if self._temperature is not None:
            completion_kwargs["temperature"] = self._temperature
        if self._max_tokens is not None:
            completion_kwargs["max_tokens"] = self._max_tokens

        return completion_kwargs

    async def complete(self, message: str, stream: bool = True) -> AsyncIterator[str]:
        if not self._is_active:
            raise ProviderError("Session is closed")

        client = self._get_client()
        self.add_user_message(message)

        completion_kwargs = self._completion_kwargs(stream=stream)

        try:
            if stream:
                response = await client.chat.completions.create(**completion_kwargs)
                full_response = ""

                async for chunk in response:
                    if hasattr(chunk, "choices") and chunk.choices:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, "content") and delta.content:
                            full_response += delta.content
                            yield delta.content

                if full_response:
                    self.add_assistant_message(full_response)
            else:
                response = await client.chat.completions.create(**completion_kwargs)
                if hasattr(response, "choices") and response.choices:
                    content = response.choices[0].message.content
                    if content:
                        self.add_assistant_message(content)
                        yield content

        except Exception as e:
            logger.error(f"{self.provider_name.capitalize()} completion error: {e}")
            raise ProviderError(
                f"{self.provider_name.capitalize()} completion failed: {e}"
            ) from e

    async def complete_with_tool_calls(
        self,
        message: str | None,
        tools: list[dict[str, Any]],
    ) -> ProviderToolCallResponse:
        """Send a non-streaming request with provider-native function tools."""
        if not self._is_active:
            raise ProviderError("Session is closed")

        client = self._get_client()
        if message:
            self.add_user_message(message)

        completion_kwargs = self._completion_kwargs(stream=False)
        completion_kwargs["tools"] = [
            _format_openai_tool_schema(tool) for tool in tools
        ]
        completion_kwargs["tool_choice"] = "auto"

        try:
            response = await client.chat.completions.create(**completion_kwargs)
            if not hasattr(response, "choices") or not response.choices:
                return ProviderToolCallResponse(content="")

            message_obj = response.choices[0].message
            content = str(getattr(message_obj, "content", "") or "")
            tool_calls = _parse_openai_tool_calls(message_obj)
            if content or tool_calls:
                self._messages.append(
                    _assistant_message_from_response(
                        content=content,
                        tool_calls=tool_calls,
                    )
                )
            return ProviderToolCallResponse(
                content=content,
                tool_calls=tuple(tool_calls),
            )
        except Exception as e:
            logger.error(
                f"{self.provider_name.capitalize()} tool-call completion error: {e}"
            )
            raise ProviderError(
                f"{self.provider_name.capitalize()} tool-call completion failed: {e}"
            ) from e

    def clear_history(self, keep_system: bool = True) -> None:
        if keep_system:
            system_msgs = [m for m in self._messages if m["role"] == "system"]
            self._messages = system_msgs
        else:
            self._messages = []

    def close(self) -> None:
        super().close()
        self._messages = []
        self._client = None
        logger.debug(
            f"{self.provider_name.capitalize()} session {self.session_id} closed"
        )


def _format_openai_tool_schema(tool: dict[str, Any]) -> dict[str, Any]:
    """Convert a provider-neutral tool schema to OpenAI chat-completions shape."""
    if tool.get("type") == "function" and isinstance(tool.get("function"), dict):
        return tool

    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool.get(
                "parameters",
                {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
        },
    }


def _parse_openai_tool_calls(message_obj: Any) -> list[ProviderToolCall]:
    """Normalize OpenAI SDK tool-call objects into runtime-friendly records."""
    normalized: list[ProviderToolCall] = []
    for tool_call in getattr(message_obj, "tool_calls", None) or []:
        function = getattr(tool_call, "function", None)
        name = str(getattr(function, "name", "") or "")
        raw_arguments = str(getattr(function, "arguments", "") or "{}")
        try:
            parsed_arguments = json.loads(raw_arguments)
        except json.JSONDecodeError as e:
            raise ProviderError(f"Invalid tool-call arguments for {name}: {e}") from e
        if not isinstance(parsed_arguments, dict):
            raise ProviderError(f"Tool-call arguments for {name} must be an object")

        normalized.append(
            ProviderToolCall(
                id=str(getattr(tool_call, "id", "") or ""),
                name=name,
                arguments=parsed_arguments,
            )
        )
    return normalized


def _assistant_message_from_response(
    *,
    content: str,
    tool_calls: list[ProviderToolCall],
) -> dict[str, Any]:
    """Build a chat-completions assistant message with optional tool calls."""
    message: dict[str, Any] = {
        "role": "assistant",
        "content": content or None,
    }
    if tool_calls:
        message["tool_calls"] = [
            {
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.name,
                    "arguments": json.dumps(tool_call.arguments),
                },
            }
            for tool_call in tool_calls
        ]
    return message


class OpenAICompatibleProvider(AIEngineProvider):
    """Base provider for OpenAI-compatible backends.

    Subclasses must set class-level attributes and implement a few hooks:
    - ``_provider_name``: e.g. ``"openai"``
    - ``_supported_models``: list of model IDs
    - ``_get_api_key``: return API key from config
    - ``_get_model``: return model from config + session config
    - ``_create_session_instance``: build the concrete session
    - ``_config_error_message``: human-readable error for missing config
    - ``_config_env_var``: env var name shown in error messages
    """

    _provider_name: str = ""
    _supported_models: list[str] = []

    def __init__(self, config: "ProviderConfig"):
        self._config = config
        self._active_session: OpenAICompatibleSession | None = None
        self._validation_errors: list[str] = []

    @property
    def name(self) -> str:
        return self._provider_name

    @property
    def config(self) -> "ProviderConfig":
        return self._config

    # -- hooks for subclasses ---------------------------------------------------

    def _get_api_key(self) -> str | None:
        """Return the API key from config (or None if not set)."""
        raise NotImplementedError

    def _get_model(self, session_config: SessionConfig) -> str:
        """Resolve the model for a new session."""
        raise NotImplementedError

    def _create_session_instance(
        self, session_id: str, model: str, config: SessionConfig
    ) -> OpenAICompatibleSession:
        """Build the concrete session object."""
        raise NotImplementedError

    def _config_env_var(self) -> str:
        """Return the env-var name for the primary config check."""
        raise NotImplementedError

    def _is_config_set(self) -> bool:
        """Return True if the primary config value is present."""
        raise NotImplementedError

    # -- shared implementation --------------------------------------------------

    def create_session(self, config: SessionConfig) -> OpenAICompatibleSession:
        try:
            from openai import AsyncOpenAI  # noqa: F401
        except ImportError as e:
            raise ProviderNotInstalled(
                f"{self._provider_name.capitalize()} provider requires the openai package. "
                "Install with: pip install openai\n"
                f"Error: {e}"
            )

        model = self._get_model(config)
        if not model:
            raise ProviderConfigError(
                f"{self._provider_name.capitalize()} provider requires a model. "
                f"Set {self._config_env_var()} environment variable."
            )

        session_id = f"{self._provider_name}-{uuid.uuid4().hex[:12]}"
        session = self._create_session_instance(session_id, model, config)
        self._active_session = session
        logger.info(
            f"Created {self._provider_name} session {session_id} (model={model})"
        )
        return session

    async def send_message(self, message: str) -> AsyncIterator[str]:
        if not self._active_session:
            raise ProviderError("No active session. Call create_session() first.")
        if not self._active_session.is_active:
            raise ProviderError("Session is closed. Create a new session.")
        async for chunk in self._active_session.complete(message, stream=True):
            yield chunk

    def get_supported_models(self) -> list[str]:
        return self._supported_models.copy()

    def validate_config(self) -> bool:
        self._validation_errors = []
        if not self._is_config_set():
            self._validation_errors.append(
                f"{self._provider_name.capitalize()} provider requires "
                f"{self._config_env_var()} environment variable"
            )
            return False
        return True

    def get_validation_errors(self) -> list[str]:
        return self._validation_errors.copy()

    def health_check(self) -> bool:
        if not self.validate_config():
            return False
        try:
            from openai import AsyncOpenAI  # noqa: F401

            return True
        except ImportError:
            self._validation_errors.append("openai package is not installed")
            return False

    def get_active_session(self) -> OpenAICompatibleSession | None:
        if self._active_session and self._active_session.is_active:
            return self._active_session
        return None

    def close(self) -> None:
        if self._active_session:
            self._active_session.close()
            self._active_session = None
        logger.debug(f"{self._provider_name.capitalize()} provider closed")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
