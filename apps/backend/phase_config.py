"""
Phase Configuration Module
===========================

Handles model and thinking level configuration for different execution phases.
Reads configuration from task_metadata.json and provides resolved model IDs.
"""

import json
import os
from pathlib import Path
from typing import Literal, TypedDict

# Model shorthand to full model ID mapping
MODEL_ID_MAP: dict[str, str] = {
    "opus": "claude-opus-4-5-20251101",
    "sonnet": "claude-sonnet-4-5-20250929",
    "haiku": "claude-haiku-4-5-20251001",
}

# Complexity thresholds for determining task complexity level
COMPLEXITY_THRESHOLDS: dict[str, int] = {
    "description_short": 100,  # Short task description (characters)
    "description_medium": 500,  # Medium task description
    "description_long": 1500,  # Long/complex task description
    "files_simple": 3,  # Few files affected
    "files_medium": 10,  # Moderate number of files
    "services_simple": 1,  # Single service
    "services_medium": 3,  # Multiple services
}

# Thinking level to budget tokens mapping (None = no extended thinking)
# Values must match auto-code-ui/src/shared/constants/models.ts THINKING_BUDGET_MAP
THINKING_BUDGET_MAP: dict[str, int | None] = {
    "none": None,
    "low": 1024,
    "medium": 4096,  # Moderate analysis
    "high": 16384,  # Deep thinking for QA review
    "ultrathink": 63999,  # Maximum reasoning depth (API requires max_tokens >= budget + 1, so 63999 + 1 = 64000 limit)
}

# Spec runner phase-specific thinking levels
# Heavy phases use ultrathink for deep analysis
# Light phases use medium after compaction
SPEC_PHASE_THINKING_LEVELS: dict[str, str] = {
    # Heavy phases - ultrathink (discovery, spec creation, self-critique)
    "discovery": "ultrathink",
    "spec_writing": "ultrathink",
    "self_critique": "ultrathink",
    # Light phases - medium (after first invocation with compaction)
    "requirements": "medium",
    "research": "medium",
    "context": "medium",
    "planning": "medium",
    "validation": "medium",
    "quick_spec": "medium",
    "historical_context": "medium",
    "complexity_assessment": "medium",
}

# Default phase configuration (fallback, matches 'Balanced' profile)
DEFAULT_PHASE_MODELS: dict[str, str] = {
    "spec": "sonnet",
    "planning": "sonnet",  # Changed from "opus" (fix #433)
    "coding": "sonnet",
    "qa": "sonnet",
    "test_generation": "sonnet",
}

DEFAULT_PHASE_THINKING: dict[str, str] = {
    "spec": "medium",
    "planning": "high",
    "coding": "medium",
    "qa": "high",
    "test_generation": "medium",
}

# Agent-level default model mapping
# Maps each agent type from AGENT_CONFIGS to a default model shorthand
# Used for multi-model orchestration where different agents can use different models
AGENT_DEFAULT_MODELS: dict[str, str] = {
    # ═══════════════════════════════════════════════════════════════════════
    # SPEC CREATION AGENTS (Use sonnet for spec phases)
    # ═══════════════════════════════════════════════════════════════════════
    "spec_gatherer": "sonnet",
    "spec_researcher": "sonnet",
    "spec_writer": "sonnet",
    "spec_critic": "sonnet",  # Uses ultrathink for self-critique
    "spec_discovery": "sonnet",
    "spec_context": "sonnet",
    "spec_validation": "sonnet",
    "spec_compaction": "sonnet",
    # ═══════════════════════════════════════════════════════════════════════
    # BUILD AGENTS (Use sonnet for planning and coding)
    # ═══════════════════════════════════════════════════════════════════════
    "planner": "sonnet",
    "coder": "sonnet",
    # ═══════════════════════════════════════════════════════════════════════
    # QA AGENTS (Use sonnet for quality assurance)
    # ═══════════════════════════════════════════════════════════════════════
    "qa_reviewer": "sonnet",
    "qa_fixer": "sonnet",
    # ═══════════════════════════════════════════════════════════════════════
    # UTILITY AGENTS (Use haiku for lightweight tasks)
    # ═══════════════════════════════════════════════════════════════════════
    "insights": "haiku",  # Lightweight memory extraction
    "merge_resolver": "haiku",  # Simple conflict resolution
    "commit_message": "haiku",  # Quick commit message generation
    # ═══════════════════════════════════════════════════════════════════════
    # PR AGENTS (Use sonnet for code review)
    # ═══════════════════════════════════════════════════════════════════════
    "pr_reviewer": "sonnet",
    "pr_orchestrator_parallel": "sonnet",
    "pr_followup_parallel": "sonnet",
    # ═══════════════════════════════════════════════════════════════════════
    # ANALYSIS AGENTS (Use sonnet for analysis, haiku for batch)
    # ═══════════════════════════════════════════════════════════════════════
    "analysis": "sonnet",
    "batch_analysis": "haiku",  # Batch processing
    "batch_validation": "haiku",  # Batch validation
    # ═══════════════════════════════════════════════════════════════════════
    # ROADMAP & IDEATION (Use sonnet for strategic thinking)
    # ═══════════════════════════════════════════════════════════════════════
    "roadmap_discovery": "sonnet",
    "competitor_analysis": "sonnet",
    "ideation": "sonnet",
}

# Agent-level default provider mapping
# Maps each agent type to a default AI provider
# Used for multi-provider orchestration where different agents can use different providers
AGENT_DEFAULT_PROVIDERS: dict[str, str] = {
    # ═══════════════════════════════════════════════════════════════════════
    # SPEC CREATION AGENTS (Use claude as default provider)
    # ═══════════════════════════════════════════════════════════════════════
    "spec_gatherer": "claude",
    "spec_researcher": "claude",
    "spec_writer": "claude",
    "spec_critic": "claude",
    "spec_discovery": "claude",
    "spec_context": "claude",
    "spec_validation": "claude",
    "spec_compaction": "claude",
    # ═══════════════════════════════════════════════════════════════════════
    # BUILD AGENTS (Use claude as default provider)
    # ═══════════════════════════════════════════════════════════════════════
    "planner": "claude",
    "coder": "claude",
    # ═══════════════════════════════════════════════════════════════════════
    # QA AGENTS (Use claude as default provider)
    # ═══════════════════════════════════════════════════════════════════════
    "qa_reviewer": "claude",
    "qa_fixer": "claude",
    # ═══════════════════════════════════════════════════════════════════════
    # UTILITY AGENTS (Use claude as default provider)
    # ═══════════════════════════════════════════════════════════════════════
    "insights": "claude",
    "merge_resolver": "claude",
    "commit_message": "claude",
    # ═══════════════════════════════════════════════════════════════════════
    # PR AGENTS (Use claude as default provider)
    # ═══════════════════════════════════════════════════════════════════════
    "pr_reviewer": "claude",
    "pr_orchestrator_parallel": "claude",
    "pr_followup_parallel": "claude",
    # ═══════════════════════════════════════════════════════════════════════
    # ANALYSIS AGENTS (Use claude as default provider)
    # ═══════════════════════════════════════════════════════════════════════
    "analysis": "claude",
    "batch_analysis": "claude",
    "batch_validation": "claude",
    # ═══════════════════════════════════════════════════════════════════════
    # ROADMAP & IDEATION (Use claude as default provider)
    # ═══════════════════════════════════════════════════════════════════════
    "roadmap_discovery": "claude",
    "competitor_analysis": "claude",
    "ideation": "claude",
}


class PhaseModelConfig(TypedDict, total=False):
    spec: str
    planning: str
    coding: str
    qa: str
    test_generation: str


class PhaseThinkingConfig(TypedDict, total=False):
    spec: str
    planning: str
    coding: str
    qa: str
    test_generation: str


class AgentModelConfig(TypedDict, total=False):
    """Agent-level model configuration for multi-model orchestration"""

    # Spec creation agents
    spec_gatherer: str
    spec_researcher: str
    spec_writer: str
    spec_critic: str
    spec_discovery: str
    spec_context: str
    spec_validation: str
    spec_compaction: str
    # Build agents
    planner: str
    coder: str
    # QA agents
    qa_reviewer: str
    qa_fixer: str
    # Utility agents
    insights: str
    merge_resolver: str
    commit_message: str
    # PR agents
    pr_reviewer: str
    pr_orchestrator_parallel: str
    pr_followup_parallel: str
    # Analysis agents
    analysis: str
    batch_analysis: str
    batch_validation: str
    # Roadmap & Ideation agents
    roadmap_discovery: str
    competitor_analysis: str
    ideation: str


class TaskMetadataConfig(TypedDict, total=False):
    """Structure of model-related fields in task_metadata.json"""

    isAutoProfile: bool
    phaseModels: PhaseModelConfig
    phaseThinking: PhaseThinkingConfig
    agentModels: AgentModelConfig
    model: str
    thinkingLevel: str


Phase = Literal["spec", "planning", "coding", "qa", "test_generation"]


def resolve_model_id(model: str) -> str:
    """
    Resolve a model shorthand (haiku, sonnet, opus) to a full model ID.
    If the model is already a full ID, return it unchanged.

    Priority:
    1. Environment variable override (from API Profile)
    2. Hardcoded MODEL_ID_MAP
    3. Pass through unchanged (assume full model ID)

    Args:
        model: Model shorthand or full ID

    Returns:
        Full Claude model ID
    """
    # Check for environment variable override (from API Profile custom model mappings)
    if model in MODEL_ID_MAP:
        env_var_map = {
            "haiku": "ANTHROPIC_DEFAULT_HAIKU_MODEL",
            "sonnet": "ANTHROPIC_DEFAULT_SONNET_MODEL",
            "opus": "ANTHROPIC_DEFAULT_OPUS_MODEL",
        }
        env_var = env_var_map.get(model)
        if env_var:
            env_value = os.environ.get(env_var)
            if env_value:
                return env_value

        # Fall back to hardcoded mapping
        return MODEL_ID_MAP[model]

    # Already a full model ID or unknown shorthand
    return model


def get_thinking_budget(thinking_level: str) -> int | None:
    """
    Get the thinking budget for a thinking level.

    Args:
        thinking_level: Thinking level (none, low, medium, high, ultrathink)

    Returns:
        Token budget or None for no extended thinking
    """
    import logging

    if thinking_level not in THINKING_BUDGET_MAP:
        valid_levels = ", ".join(THINKING_BUDGET_MAP.keys())
        logging.warning(
            f"Invalid thinking_level '{thinking_level}'. Valid values: {valid_levels}. "
            f"Defaulting to 'medium'."
        )
        return THINKING_BUDGET_MAP["medium"]

    return THINKING_BUDGET_MAP[thinking_level]


def load_task_metadata(spec_dir: Path) -> TaskMetadataConfig | None:
    """
    Load task_metadata.json from the spec directory.

    Args:
        spec_dir: Path to the spec directory

    Returns:
        Parsed task metadata or None if not found
    """
    metadata_path = spec_dir / "task_metadata.json"
    if not metadata_path.exists():
        return None

    try:
        with open(metadata_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def get_phase_model(
    spec_dir: Path,
    phase: Phase,
    cli_model: str | None = None,
) -> str:
    """
    Get the resolved model ID for a specific execution phase.

    Priority:
    1. CLI argument (if provided)
    2. Phase-specific config from task_metadata.json (if auto profile)
    3. Single model from task_metadata.json (if not auto profile)
    4. Default phase configuration

    Args:
        spec_dir: Path to the spec directory
        phase: Execution phase (spec, planning, coding, qa)
        cli_model: Model from CLI argument (optional)

    Returns:
        Resolved full model ID
    """
    # CLI argument takes precedence
    if cli_model:
        return resolve_model_id(cli_model)

    # Load task metadata
    metadata = load_task_metadata(spec_dir)

    if metadata:
        # Check for auto profile with phase-specific config
        if metadata.get("isAutoProfile") and metadata.get("phaseModels"):
            phase_models = metadata["phaseModels"]
            model = phase_models.get(phase, DEFAULT_PHASE_MODELS[phase])
            return resolve_model_id(model)

        # Non-auto profile: use single model
        if metadata.get("model"):
            return resolve_model_id(metadata["model"])

    # Fall back to default phase configuration
    return resolve_model_id(DEFAULT_PHASE_MODELS[phase])


def get_agent_model(
    spec_dir: Path,
    agent_type: str,
    cli_model: str | None = None,
) -> str:
    """
    Get the resolved model ID for a specific agent type.

    Priority:
    1. CLI argument (if provided)
    2. Environment variable AGENT_MODEL_<agent_type> (if set)
    3. Agent-specific config from task_metadata.json agentModels (if present)
    4. AGENT_DEFAULT_MODELS (if agent_type exists)
    5. Fallback to "sonnet"

    Args:
        spec_dir: Path to the spec directory
        agent_type: Agent type (e.g., 'coder', 'planner', 'qa_reviewer')
        cli_model: Model from CLI argument (optional)

    Returns:
        Resolved full model ID
    """
    # CLI argument takes precedence
    if cli_model:
        return resolve_model_id(cli_model)

    # Check for environment variable override
    env_var_name = f"AGENT_MODEL_{agent_type.upper()}"
    env_model = os.environ.get(env_var_name)
    if env_model:
        return resolve_model_id(env_model)

    # Load task metadata
    metadata = load_task_metadata(spec_dir)

    if metadata:
        # Check for agent-specific config
        if metadata.get("agentModels"):
            agent_models = metadata["agentModels"]
            if agent_type in agent_models:
                return resolve_model_id(agent_models[agent_type])

    # Fall back to default agent configuration
    if agent_type in AGENT_DEFAULT_MODELS:
        return resolve_model_id(AGENT_DEFAULT_MODELS[agent_type])

    # Final fallback to sonnet
    return resolve_model_id("sonnet")


def get_phase_thinking(
    spec_dir: Path,
    phase: Phase,
    cli_thinking: str | None = None,
) -> str:
    """
    Get the thinking level for a specific execution phase.

    Priority:
    1. CLI argument (if provided)
    2. Phase-specific config from task_metadata.json (if auto profile)
    3. Single thinking level from task_metadata.json (if not auto profile)
    4. Default phase configuration

    Args:
        spec_dir: Path to the spec directory
        phase: Execution phase (spec, planning, coding, qa)
        cli_thinking: Thinking level from CLI argument (optional)

    Returns:
        Thinking level string
    """
    # CLI argument takes precedence
    if cli_thinking:
        return cli_thinking

    # Load task metadata
    metadata = load_task_metadata(spec_dir)

    if metadata:
        # Check for auto profile with phase-specific config
        if metadata.get("isAutoProfile") and metadata.get("phaseThinking"):
            phase_thinking = metadata["phaseThinking"]
            return phase_thinking.get(phase, DEFAULT_PHASE_THINKING[phase])

        # Non-auto profile: use single thinking level
        if metadata.get("thinkingLevel"):
            return metadata["thinkingLevel"]

    # Fall back to default phase configuration
    return DEFAULT_PHASE_THINKING[phase]


def get_phase_thinking_budget(
    spec_dir: Path,
    phase: Phase,
    cli_thinking: str | None = None,
) -> int | None:
    """
    Get the thinking budget tokens for a specific execution phase.

    Args:
        spec_dir: Path to the spec directory
        phase: Execution phase (spec, planning, coding, qa)
        cli_thinking: Thinking level from CLI argument (optional)

    Returns:
        Token budget or None for no extended thinking
    """
    thinking_level = get_phase_thinking(spec_dir, phase, cli_thinking)
    return get_thinking_budget(thinking_level)


def get_phase_config(
    spec_dir: Path,
    phase: Phase,
    cli_model: str | None = None,
    cli_thinking: str | None = None,
) -> tuple[str, str, int | None]:
    """
    Get the full configuration for a specific execution phase.

    Args:
        spec_dir: Path to the spec directory
        phase: Execution phase (spec, planning, coding, qa)
        cli_model: Model from CLI argument (optional)
        cli_thinking: Thinking level from CLI argument (optional)

    Returns:
        Tuple of (model_id, thinking_level, thinking_budget)
    """
    model_id = get_phase_model(spec_dir, phase, cli_model)
    thinking_level = get_phase_thinking(spec_dir, phase, cli_thinking)
    thinking_budget = get_thinking_budget(thinking_level)

    return model_id, thinking_level, thinking_budget


# Output constraint templates for controlling response length
OUTPUT_CONSTRAINT_TEMPLATES: dict[str, str] = {
    "summary": "Respond in {limit} words or less",
    "brief": "Keep your response under {limit} words",
    "concise": "Provide a concise response in {limit} words or fewer",
    "strict": "Your response MUST NOT exceed {limit} words",
}


def get_output_constraint(format_type: str, word_limit: int) -> str:
    """
    Get a formatted output constraint string.

    Args:
        format_type: Type of constraint format (summary, brief, concise, strict)
        word_limit: Maximum word count

    Returns:
        Formatted constraint string
    """
    template = OUTPUT_CONSTRAINT_TEMPLATES.get(
        format_type, OUTPUT_CONSTRAINT_TEMPLATES["summary"]
    )
    return template.format(limit=word_limit)


def suggest_thinking_budget(
    description: str, file_count: int, service_count: int
) -> str:
    """
    Suggest thinking level based on task complexity.

    Uses COMPLEXITY_THRESHOLDS to score description length, file count,
    and service count, then maps the total score to a thinking level.

    Args:
        description: Task description text
        file_count: Number of files affected
        service_count: Number of services involved

    Returns:
        Thinking level string: "low", "medium", "high", or "ultrathink"
    """
    score = 0

    # Score based on description length
    desc_len = len(description)
    if desc_len >= COMPLEXITY_THRESHOLDS["description_long"]:
        score += 3
    elif desc_len >= COMPLEXITY_THRESHOLDS["description_medium"]:
        score += 2
    elif desc_len >= COMPLEXITY_THRESHOLDS["description_short"]:
        score += 1

    # Score based on file count
    if file_count >= COMPLEXITY_THRESHOLDS["files_medium"]:
        score += 2
    elif file_count >= COMPLEXITY_THRESHOLDS["files_simple"]:
        score += 1

    # Score based on service count
    if service_count >= COMPLEXITY_THRESHOLDS["services_medium"]:
        score += 2
    elif service_count > COMPLEXITY_THRESHOLDS["services_simple"]:
        score += 1

    # Map score to thinking level
    if score >= 6:
        return "ultrathink"
    elif score >= 4:
        return "high"
    elif score >= 2:
        return "medium"
    else:
        return "low"


def get_spec_phase_thinking_budget(phase_name: str) -> int | None:
    """
    Get the thinking budget for a specific spec runner phase.

    This maps granular spec phases (discovery, spec_writing, etc.) to their
    appropriate thinking budgets based on SPEC_PHASE_THINKING_LEVELS.

    Args:
        phase_name: Name of the spec phase (e.g., 'discovery', 'spec_writing')

    Returns:
        Token budget for extended thinking, or None for no extended thinking
    """
    thinking_level = SPEC_PHASE_THINKING_LEVELS.get(phase_name, "medium")
    return get_thinking_budget(thinking_level)


def get_provider_for_agent(agent_type: str) -> str:
    """
    Get the AI provider to use for a specific agent.

    Priority:
    1. Environment variable AGENT_PROVIDER_<agent_type> (if set)
    2. Global AI_ENGINE_PROVIDER environment variable (if set)
    3. AGENT_DEFAULT_PROVIDERS mapping (if agent_type has a default)
    4. Default to 'claude'

    Args:
        agent_type: The agent type (e.g., 'coder', 'planner', 'qa_reviewer')

    Returns:
        Provider name ('claude', 'litellm', or 'openrouter')
    """
    # 1. Check for agent-specific environment variable override
    env_var_name = f"AGENT_PROVIDER_{agent_type.upper()}"
    env_provider = os.environ.get(env_var_name)
    if env_provider:
        return env_provider

    # 2. Global AI_ENGINE_PROVIDER env var overrides the hardcoded defaults
    global_provider = os.environ.get("AI_ENGINE_PROVIDER")
    if global_provider:
        return global_provider

    # 3. Check agent default providers mapping
    default_provider = AGENT_DEFAULT_PROVIDERS.get(agent_type)
    if default_provider:
        return default_provider

    return "claude"
