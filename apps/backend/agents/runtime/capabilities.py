"""
Runtime capability contracts.

The provider layer answers "which model can we call?" The runtime layer answers
"which workspace actions can this session perform safely?"
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeCapabilities:
    """Capabilities exposed by an agent runtime."""

    text_completion: bool = False
    streaming_text: bool = False
    structured_output: bool = False
    native_tool_loop: bool = False
    function_tools: bool = False
    mcp: bool = False
    filesystem_read: bool = False
    filesystem_edit: bool = False
    shell: bool = False
    apply_patch: bool = False
    subagents: bool = False
    sandbox: bool = False

    @classmethod
    def claude_agent_sdk(cls) -> "RuntimeCapabilities":
        """Capabilities expected from the existing Claude Agent SDK path."""
        return cls(
            text_completion=True,
            streaming_text=True,
            structured_output=True,
            native_tool_loop=True,
            function_tools=True,
            mcp=True,
            filesystem_read=True,
            filesystem_edit=True,
            shell=True,
            apply_patch=True,
            subagents=True,
            sandbox=True,
        )

    @classmethod
    def codex_cli(cls) -> "RuntimeCapabilities":
        """Capabilities expected from Codex CLI exec sessions."""
        return cls(
            text_completion=True,
            streaming_text=True,
            structured_output=True,
            native_tool_loop=True,
            filesystem_read=True,
            filesystem_edit=True,
            shell=True,
            apply_patch=True,
            sandbox=True,
        )

    @classmethod
    def completion_only(cls) -> "RuntimeCapabilities":
        """Capabilities for direct model SDKs and model gateways."""
        return cls(
            text_completion=True,
            streaming_text=True,
            structured_output=True,
        )

    @classmethod
    def patch_proposal(cls) -> "RuntimeCapabilities":
        """Capabilities for validated patch proposal mode."""
        return cls(
            text_completion=True,
            streaming_text=True,
            structured_output=True,
            filesystem_edit=True,
            apply_patch=True,
        )

    @classmethod
    def generic_edit(cls) -> "RuntimeCapabilities":
        """Capabilities for Auto Code's provider-neutral local tool loop."""
        return cls(
            text_completion=True,
            streaming_text=True,
            structured_output=True,
            function_tools=True,
            filesystem_read=True,
            filesystem_edit=True,
            shell=True,
            apply_patch=True,
        )

    @classmethod
    def direct_api_autonomous(cls) -> "RuntimeCapabilities":
        """Capabilities for promoted direct API providers using local tools."""
        return cls(
            text_completion=True,
            streaming_text=True,
            structured_output=True,
            native_tool_loop=True,
            function_tools=True,
            filesystem_read=True,
            filesystem_edit=True,
            shell=True,
            apply_patch=True,
        )

    def available(self) -> list[str]:
        """Return capability names set to true."""
        return [
            name
            for name, value in self.__dict__.items()
            if isinstance(value, bool) and value
        ]

    def missing(self, requirements: "RuntimeRequirements") -> list[str]:
        """Return required capabilities this runtime does not provide."""
        return [
            capability
            for capability in requirements.required
            if not bool(getattr(self, capability, False))
        ]

    def supports(self, requirements: "RuntimeRequirements") -> bool:
        """Return true when all required capabilities are available."""
        return not self.missing(requirements)


@dataclass(frozen=True)
class RuntimeRequirements:
    """Capabilities required by an agent phase or execution mode."""

    mode: str
    required: tuple[str, ...]

    @classmethod
    def planner(cls) -> "RuntimeRequirements":
        # The current planner prompt investigates and writes files, so it still
        # needs the full workspace runtime. A future text planner can relax this.
        return cls(
            mode="planner",
            required=(
                "text_completion",
                "structured_output",
                "native_tool_loop",
                "filesystem_read",
                "filesystem_edit",
                "shell",
            ),
        )

    @classmethod
    def full_coder(cls) -> "RuntimeRequirements":
        return cls(
            mode="full_autonomous",
            required=(
                "text_completion",
                "native_tool_loop",
                "filesystem_edit",
                "shell",
            ),
        )

    @classmethod
    def text_only(cls, mode: str = "analysis_only") -> "RuntimeRequirements":
        return cls(mode=mode, required=("text_completion",))

    @classmethod
    def patch_proposal(cls) -> "RuntimeRequirements":
        return cls(
            mode="patch_proposal",
            required=(
                "text_completion",
                "structured_output",
                "filesystem_edit",
                "apply_patch",
            ),
        )

    @classmethod
    def generic_edit(cls) -> "RuntimeRequirements":
        return cls(
            mode="generic_edit",
            required=(
                "text_completion",
                "structured_output",
                "function_tools",
                "filesystem_read",
                "filesystem_edit",
                "shell",
                "apply_patch",
            ),
        )


class RuntimeCapabilityError(RuntimeError):
    """Raised when a runtime cannot satisfy phase requirements."""

    def __init__(
        self,
        *,
        provider_name: str,
        runtime_name: str,
        requirements: RuntimeRequirements,
        capabilities: RuntimeCapabilities,
    ):
        self.provider_name = provider_name
        self.runtime_name = runtime_name
        self.requirements = requirements
        self.capabilities = capabilities
        self.missing = capabilities.missing(requirements)
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        required = "\n".join(f"- {name}" for name in self.requirements.required)
        available_names = self.capabilities.available()
        available = (
            "\n".join(f"- {name}" for name in available_names)
            if available_names
            else "- none"
        )
        missing = "\n".join(f"- {name}" for name in self.missing)
        return (
            f"Cannot run {self.requirements.mode} with provider={self.provider_name} "
            f"runtime={self.runtime_name}.\n\n"
            f"Missing capabilities:\n{missing}\n\n"
            f"Required capabilities:\n{required}\n\n"
            f"Available capabilities:\n{available}\n\n"
            "Use Claude Agent SDK for full autonomous coding today, or run a "
            "limited generic_edit, patch_proposal, or analysis_only phase with "
            "a compatible runtime."
        )
