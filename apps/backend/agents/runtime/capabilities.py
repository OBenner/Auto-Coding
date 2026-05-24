"""
Runtime capability contracts.

The provider layer answers "which model can we call?" The runtime layer answers
"which workspace actions can this session perform safely?"

``RuntimeCapabilities`` describes what the runtime physically supports.
Promotion of a runtime to satisfy a stricter requirement (for example
treating a Generic Edit session as ``full_autonomous`` after a provider
clears the AutonomyPolicy gate) is a separate decision expressed via
``RuntimePolicy``. Capabilities must never claim a flag that the runtime
cannot back; promotion lives in policy so operators can see the two
forces independently.
"""

import warnings
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
    def promoted_edit(cls) -> "RuntimeCapabilities":
        """Capabilities for a Generic Edit session that may be policy-promoted.

        Physically identical to :meth:`generic_edit`. Promotion to satisfy
        ``full_coder``/``planner`` requirements is represented separately
        via :class:`RuntimePolicy` so the capability flags stay honest.
        """
        return cls.generic_edit()

    @classmethod
    def direct_api_autonomous(cls) -> "RuntimeCapabilities":
        """Deprecated alias for :meth:`promoted_edit`.

        The previous implementation set ``native_tool_loop=True`` to make
        :class:`DirectApiAutonomousRuntimeSession` satisfy ``full_coder``
        requirements through the capability check. That conflated
        capability (what the runtime physically does) with policy (whether
        the AutonomyPolicy gate promoted the runtime). Use
        :meth:`promoted_edit` for the honest capability and combine it
        with a :class:`RuntimePolicy` carrying
        ``promoted_to_full_autonomous=True`` for the promotion decision.
        """
        warnings.warn(
            "RuntimeCapabilities.direct_api_autonomous() is deprecated; "
            "use RuntimeCapabilities.promoted_edit() combined with a "
            "RuntimePolicy that carries promoted_to_full_autonomous=True.",
            DeprecationWarning,
            stacklevel=2,
        )
        return cls.promoted_edit()

    def available(self) -> list[str]:
        """Return capability names set to true."""
        return [
            name
            for name, value in self.__dict__.items()
            if isinstance(value, bool) and value
        ]

    def missing(
        self,
        requirements: "RuntimeRequirements",
        *,
        policy: "RuntimePolicy | None" = None,
    ) -> list[str]:
        """Return required capabilities this runtime does not provide.

        ``policy`` may grant the runtime additional satisfied capabilities
        through evidence-based promotion (see :class:`RuntimePolicy`).
        """
        granted = policy.granted_capabilities() if policy is not None else frozenset()
        return [
            capability
            for capability in requirements.required
            if not bool(getattr(self, capability, False))
            and capability not in granted
        ]

    def supports(
        self,
        requirements: "RuntimeRequirements",
        *,
        policy: "RuntimePolicy | None" = None,
    ) -> bool:
        """Return true when all required capabilities are available.

        Pass ``policy`` to honor evidence-based promotion (for example a
        Generic Edit runtime that the AutonomyPolicy gate promoted to
        ``full_autonomous`` for a specific provider).
        """
        return not self.missing(requirements, policy=policy)


# Capabilities the promoted-edit policy grants the runtime when the
# AutonomyPolicy gate signs off. ``native_tool_loop`` is granted because
# the underlying Generic Edit engine attempts the provider's native tool
# API and falls back to its JSON action loop when the provider does not
# support tools; the gate evidence proves the provider/model combination
# can drive that loop end-to-end. Promotion alone does NOT grant
# ``subagents`` or ``sandbox``: those still require Phase 1.2 and Phase
# 1.3 capability work in docs/roadmap/non-claude-provider-autonomy.md.
_PROMOTED_FULL_AUTONOMOUS_GRANTS: frozenset[str] = frozenset(
    {"native_tool_loop"}
)
# Additional capability the policy grants once the external MCP client
# bridge is enabled. Phase 1.1: direct API providers can reach Graphiti,
# Linear, Electron, Puppeteer, and custom MCP servers through the
# provider-neutral bridge so they match the Claude SDK MCP surface for
# tool discovery and invocation.
_MCP_EXECUTION_GRANTS: frozenset[str] = frozenset({"mcp"})


@dataclass(frozen=True)
class RuntimePolicy:
    """Policy-driven attributes applied on top of :class:`RuntimeCapabilities`.

    Capability and policy are intentionally separate concerns: capability
    describes what the runtime can physically do, policy describes what the
    operator (or an evidence gate) has decided to allow on top of that.
    """

    promoted_to_full_autonomous: bool = False
    mcp_execution_enabled: bool = False

    def granted_capabilities(self) -> frozenset[str]:
        """Return capability names the policy treats as satisfied."""
        granted: set[str] = set()
        if self.promoted_to_full_autonomous:
            granted |= _PROMOTED_FULL_AUTONOMOUS_GRANTS
        if self.mcp_execution_enabled:
            granted |= _MCP_EXECUTION_GRANTS
        return frozenset(granted)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe policy snapshot."""
        return {
            "promoted_to_full_autonomous": self.promoted_to_full_autonomous,
            "mcp_execution_enabled": self.mcp_execution_enabled,
            "granted_capabilities": sorted(self.granted_capabilities()),
        }


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
        policy: RuntimePolicy | None = None,
    ):
        self.provider_name = provider_name
        self.runtime_name = runtime_name
        self.requirements = requirements
        self.capabilities = capabilities
        self.policy = policy
        self.missing = capabilities.missing(requirements, policy=policy)
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
        policy_block = ""
        if self.policy is not None:
            granted = sorted(self.policy.granted_capabilities())
            granted_text = "\n".join(f"- {name}" for name in granted) or "- none"
            policy_block = (
                f"\nPolicy-granted capabilities:\n{granted_text}\n"
                f"Promoted to full autonomous: "
                f"{self.policy.promoted_to_full_autonomous}\n"
            )
        return (
            f"Cannot run {self.requirements.mode} with provider={self.provider_name} "
            f"runtime={self.runtime_name}.\n\n"
            f"Missing capabilities:\n{missing}\n\n"
            f"Required capabilities:\n{required}\n\n"
            f"Available capabilities:\n{available}\n"
            f"{policy_block}\n"
            "Use Claude Agent SDK for full autonomous coding today, or run a "
            "limited generic_edit, patch_proposal, or analysis_only phase with "
            "a compatible runtime."
        )
