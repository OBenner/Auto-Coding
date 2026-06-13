"""
OpenAI-Compatible Base Classes
===============================

Provides base session and provider classes for any provider that uses
the OpenAI-compatible API (OpenAI, Ollama, etc.).

This avoids code duplication across adapters that share the same
streaming/completion logic.
"""

import inspect
import json
import logging
import uuid
from collections.abc import AsyncIterator, Mapping
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
        completion_kwargs["tools"] = [format_openai_tool_schema(tool) for tool in tools]
        completion_kwargs["tool_choice"] = "auto"

        try:
            response = await client.chat.completions.create(**completion_kwargs)
            if not hasattr(response, "choices") or not response.choices:
                return ProviderToolCallResponse(content="")

            message_obj = response.choices[0].message
            content = provider_message_content(message_obj)
            tool_calls = parse_openai_tool_calls(message_obj)
            if content or tool_calls:
                self._messages.append(
                    assistant_message_from_tool_calls(
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

    async def aclose(self) -> None:
        """Async-close the session and its underlying ``AsyncOpenAI`` client.

        The sync :meth:`close` only drops references; the ``AsyncOpenAI``
        client owns an httpx connection pool that must be awaited closed in
        the running event loop, or the sockets leak (and asyncio emits
        "Unclosed client session" warnings on GC). Callers that build a
        session inside an event loop — e.g. the direct-API QA fixer/reviewer
        recovery loops, which rebuild a session per attempt — should prefer
        this over :meth:`close`. Best-effort and idempotent.
        """
        client = self._client
        if client is not None:
            aclose = getattr(client, "close", None)
            if callable(aclose):
                try:
                    result = aclose()
                    if inspect.isawaitable(result):
                        await result
                except Exception as e:  # noqa: BLE001 - cleanup is best-effort
                    logger.debug(
                        f"{self.provider_name.capitalize()} async client close "
                        f"failed: {e}"
                    )
        self.close()


def format_openai_tool_schema(tool: dict[str, Any]) -> dict[str, Any]:
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


def parse_openai_tool_calls(message_obj: Any) -> list[ProviderToolCall]:
    """Normalize gateway-specific tool-call objects into runtime-friendly records."""
    normalized: list[ProviderToolCall] = []
    tool_calls = coalesce_provider_tool_call_fragments(
        iter_provider_tool_calls(message_obj)
    )
    for index, tool_call in enumerate(tool_calls, start=1):
        name, raw_arguments = tool_call_name_and_arguments(tool_call)
        if not name:
            raise ProviderError("Tool call is missing a function name")
        parsed_arguments = parse_tool_call_arguments(name, raw_arguments)

        normalized.append(
            ProviderToolCall(
                id=tool_call_id(tool_call, index),
                name=name,
                arguments=parsed_arguments,
            )
        )
    return normalized


def assistant_message_from_tool_calls(
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


def _get_attr_or_key(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def provider_message_content(message_obj: Any) -> str:
    """Extract text content from common provider message object shapes."""
    content = _get_attr_or_key(message_obj, "content", "")
    if isinstance(content, str):
        return content
    if content is None:
        return ""
    if isinstance(content, list):
        return "".join(content_part_text(part) for part in content)
    return str(content)


def content_part_text(part: Any) -> str:
    """Extract text from one provider content part."""
    text = _get_attr_or_key(part, "text", None)
    if isinstance(text, str):
        return text
    if isinstance(part, str):
        return part
    return ""


def iter_provider_tool_calls(message_obj: Any) -> list[Any]:
    """Return tool calls from OpenAI, LiteLLM, OpenRouter, and Gemini-like shapes."""
    call_groups = (
        nested_provider_tool_calls(message_obj),
        choice_provider_tool_calls(message_obj),
        direct_provider_tool_calls(message_obj),
        part_provider_tool_calls(message_obj),
    )
    for calls in call_groups:
        if calls:
            return calls
    return []


def nested_provider_tool_calls(message_obj: Any) -> list[Any]:
    """Return tool calls from nested message/delta envelopes."""
    for nested_name in ("message", "delta"):
        nested_message = _get_attr_or_key(message_obj, nested_name, None)
        if nested_message and nested_message is not message_obj:
            nested_calls = iter_provider_tool_calls(nested_message)
            if nested_calls:
                return nested_calls
    return []


def choice_provider_tool_calls(message_obj: Any) -> list[Any]:
    """Return tool calls from chat-completion choice envelopes."""
    calls_from_choices: list[Any] = []
    for choice in as_sequence(_get_attr_or_key(message_obj, "choices", None)):
        choice_message = _get_attr_or_key(choice, "message", None) or _get_attr_or_key(
            choice, "delta", None
        )
        if not choice_message:
            continue
        calls_from_choices.extend(iter_provider_tool_calls(choice_message))
    if calls_from_choices:
        return calls_from_choices
    return []


def direct_provider_tool_calls(message_obj: Any) -> list[Any]:
    """Return direct tool_calls/function_call fields from a message object."""
    tool_calls = as_sequence(_get_attr_or_key(message_obj, "tool_calls", None))
    if tool_calls:
        return tool_calls

    direct_call = first_present_value(
        message_obj,
        ("function_call", "functionCall", "tool_use", "toolUse"),
    )
    if direct_call:
        return [direct_call]
    return []


def part_provider_tool_calls(message_obj: Any) -> list[Any]:
    """Return tool calls embedded in output/content/parts arrays."""
    calls_from_parts: list[Any] = []
    for container_name in ("output", "content", "parts"):
        for part in as_sequence(_get_attr_or_key(message_obj, container_name, None)):
            calls_from_parts.extend(tool_calls_from_part(part))
    return calls_from_parts


def tool_call_name_and_arguments(tool_call: Any) -> tuple[str, Any]:
    """Extract function name and arguments from common tool-call envelopes."""
    function = (
        first_present_value(
            tool_call,
            ("function", "function_call", "functionCall", "tool_use", "toolUse"),
        )
        or tool_call
    )
    name = str(
        _get_attr_or_key(function, "name", None)
        or _get_attr_or_key(tool_call, "name", "")
        or ""
    )
    raw_arguments = first_present_value(
        function,
        TOOL_ARGUMENT_KEYS,
    )
    if raw_arguments is None and function is not tool_call:
        raw_arguments = first_present_value(
            tool_call,
            TOOL_ARGUMENT_KEYS,
        )
    return name, raw_arguments


def parse_tool_call_arguments(name: str, raw_arguments: Any) -> dict[str, Any]:
    """Parse tool arguments from JSON strings, dicts, and mapping-like objects."""
    if raw_arguments in (None, ""):
        return {}
    if isinstance(raw_arguments, Mapping):
        return dict(raw_arguments)
    if isinstance(raw_arguments, str):
        try:
            parsed_arguments = json.loads(raw_arguments)
        except json.JSONDecodeError as e:
            raise ProviderError(f"Invalid tool-call arguments for {name}: {e}") from e
    else:
        parsed_arguments = dump_mapping_like_arguments(name, raw_arguments)
    if not isinstance(parsed_arguments, dict):
        raise ProviderError(f"Tool-call arguments for {name} must be an object")
    return parsed_arguments


def tool_call_id(tool_call: Any, index: int) -> str:
    value = explicit_tool_call_id(tool_call) or f"call_{index}"
    return str(value)


TOOL_ARGUMENT_KEYS = (
    "arguments",
    "arguments_json",
    "argumentsJson",
    "args",
    "parameters",
    "parameters_json",
    "parametersJson",
    "input",
    "input_json",
    "inputJson",
    "tool_input",
    "toolInput",
)


def explicit_tool_call_id(tool_call: Any) -> Any:
    """Return a provider-supplied tool-call id without synthesizing a fallback."""
    return first_present_value(
        tool_call,
        (
            "id",
            "tool_call_id",
            "toolCallId",
            "call_id",
            "callId",
            "tool_use_id",
            "toolUseId",
        ),
    )


def tool_call_index(tool_call: Any) -> Any:
    """Return a provider-supplied streaming tool-call index when present."""
    return first_present_value(tool_call, ("index", "tool_call_index", "toolCallIndex"))


def coalesce_provider_tool_call_fragments(tool_calls: list[Any]) -> list[Any]:
    """Merge streaming tool-call deltas that split arguments across chunks."""
    grouped: list[dict[str, Any]] = []
    groups_by_key: dict[str, dict[str, Any]] = {}

    for position, tool_call in enumerate(tool_calls, start=1):
        key = tool_call_fragment_key(tool_call, position)
        fragment = provider_tool_call_fragment(tool_call)
        existing = groups_by_key.get(key)
        if existing is None:
            groups_by_key[key] = fragment
            grouped.append(fragment)
            continue
        merge_tool_call_fragment(existing, fragment)

    return [
        provider_tool_call_from_fragment(fragment, index)
        for index, fragment in enumerate(grouped, start=1)
    ]


def tool_call_fragment_key(tool_call: Any, position: int) -> str:
    """Return a stable grouping key for streaming tool-call fragments."""
    index = tool_call_index(tool_call)
    if index is not None:
        return f"index:{index}"
    call_id = explicit_tool_call_id(tool_call)
    if call_id is not None:
        return f"id:{call_id}"
    return f"position:{position}"


def provider_tool_call_fragment(tool_call: Any) -> dict[str, Any]:
    """Extract mergeable id/name/argument fields from one raw tool-call block."""
    name, raw_arguments = tool_call_name_and_arguments(tool_call)
    return {
        "id": explicit_tool_call_id(tool_call),
        "name": name,
        "arguments": raw_arguments,
    }


def merge_tool_call_fragment(
    target: dict[str, Any],
    fragment: dict[str, Any],
) -> None:
    """Merge one streaming tool-call fragment into an accumulated fragment."""
    if not target.get("id") and fragment.get("id"):
        target["id"] = fragment["id"]
    if not target.get("name") and fragment.get("name"):
        target["name"] = fragment["name"]
    target["arguments"] = merge_tool_call_arguments(
        target.get("arguments"),
        fragment.get("arguments"),
    )


def merge_tool_call_arguments(existing: Any, incoming: Any) -> Any:
    """Merge argument fragments while preserving full-object argument payloads."""
    if incoming in (None, ""):
        return existing
    if existing in (None, ""):
        return incoming
    if isinstance(existing, str) and isinstance(incoming, str):
        return existing + incoming
    if isinstance(existing, Mapping) and isinstance(incoming, Mapping):
        return {**dict(existing), **dict(incoming)}
    return incoming


def provider_tool_call_from_fragment(
    fragment: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    """Build a regular OpenAI-shaped tool call from a merged fragment."""
    call_id = fragment.get("id") or f"call_{index}"
    return {
        "id": call_id,
        "function": {
            "name": fragment.get("name", ""),
            "arguments": fragment.get("arguments"),
        },
    }


def as_sequence(value: Any) -> list[Any]:
    """Return a provider field as a list without treating dicts as iterables."""
    if value is None:
        return []
    if isinstance(value, Mapping):
        return [value]
    if isinstance(value, str | bytes):
        return []
    try:
        return list(value)
    except TypeError:
        return [value]


def tool_call_from_part(part: Any) -> Any | None:
    """Extract a callable tool block from common response part formats."""
    function_call = first_present_value(
        part,
        ("function_call", "functionCall", "tool_use", "toolUse"),
    )
    if function_call:
        return function_call

    part_type = str(_get_attr_or_key(part, "type", "") or "").lower()
    if part_type in {"function_call", "tool_call", "tool_use", "tooluse"}:
        return part

    if (
        _get_attr_or_key(part, "name", None)
        and first_present_value(part, TOOL_ARGUMENT_KEYS) is not None
    ):
        return part

    return None


def tool_calls_from_part(part: Any) -> list[Any]:
    """Extract direct or nested tool calls from one provider content part."""
    function_call = tool_call_from_part(part)
    if function_call:
        return [function_call]

    calls: list[Any] = []
    for container_name in ("tool_calls", "toolCalls", "content", "parts", "output"):
        for nested_part in as_sequence(_get_attr_or_key(part, container_name, None)):
            calls.extend(tool_calls_from_part(nested_part))
    return calls


def dump_mapping_like_arguments(name: str, raw_arguments: Any) -> dict[str, Any]:
    """Convert SDK-specific argument containers to plain dictionaries."""
    for method_name in ("model_dump", "to_dict", "dict"):
        method = getattr(raw_arguments, method_name, None)
        if not callable(method):
            continue
        try:
            dumped = method()
        except TypeError:
            continue
        if isinstance(dumped, Mapping):
            return dict(dumped)

    try:
        return dict(raw_arguments)
    except (TypeError, ValueError) as e:
        raise ProviderError(
            f"Tool-call arguments for {name} must be a JSON object"
        ) from e


def first_present_value(value: Any, keys: tuple[str, ...]) -> Any:
    for key in keys:
        candidate = _get_attr_or_key(value, key, None)
        if candidate is not None:
            return candidate
    return None


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
