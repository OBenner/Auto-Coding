"""
Cost Tracking System for Multi-Model Agent Orchestration
=========================================================

Tracks AI API costs across different models and agent types.
Provides cost reporting and analysis for budget management.

Supports multiple providers:
- Claude (Anthropic): Claude 4.5 (Opus, Sonnet, Haiku), Claude 3.5 Sonnet, Claude 3 (Opus, Sonnet, Haiku)
- OpenAI: GPT-4 Turbo, GPT-4, GPT-4o, GPT-3.5 Turbo
- Google Gemini: Gemini 1.5 Pro, Gemini 1.5 Flash, Gemini 2.0 Flash
- Zhipu AI GLM: GLM-4.7, GLM-4.5, GLM-4 series (Plus, Air, Flash)
- Ollama (local models, zero cost)

Components:
- MODEL_PRICING: Pricing data for all supported models (per 1M tokens)
- CostTracker: Tracks usage and calculates costs per agent session

Usage:
    # Create tracker for a spec
    tracker = CostTracker(spec_dir=Path(".auto-claude/specs/001"))

    # Log usage after agent session
    tracker.log_usage(
        agent_type="coder",
        model="claude-sonnet-4-5-20250929",
        input_tokens=5000,
        output_tokens=2000
    )

    # Log usage for OpenAI model
    tracker.log_usage(
        agent_type="planner",
        model="gpt-4o",
        input_tokens=3000,
        output_tokens=1500
    )

    # Get cost summary
    summary = tracker.get_cost_summary()
    print(summary)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Model pricing for all supported providers (per 1M tokens)
# Claude pricing: https://www.anthropic.com/pricing (January 2025)
# OpenAI pricing: https://openai.com/api/pricing/ (January 2025)
# Google Gemini pricing: https://ai.google.dev/pricing (January 2025)
MODEL_PRICING: dict[str, dict[str, float]] = {
    # ========================================
    # Claude Models (Anthropic)
    # ========================================
    # Claude 4 Opus
    "claude-opus-4-20250514": {
        "input": 15.00,
        "output": 75.00,
    },
    # Claude 4.5 Opus - Most capable model
    "claude-opus-4-5-20251101": {
        "input": 15.00,
        "output": 75.00,
    },
    # Claude 4.5 Sonnet - Balanced performance and cost
    "claude-sonnet-4-5-20250929": {
        "input": 3.00,
        "output": 15.00,
    },
    # Claude 4.5 Haiku - Fast and cost-effective
    "claude-haiku-4-5-20251001": {
        "input": 0.80,
        "output": 4.00,
    },
    # Extended thinking variants (same pricing as base models)
    "claude-sonnet-4-5-20250929-thinking": {
        "input": 3.00,
        "output": 15.00,
    },
    "claude-opus-4-5-20251101-thinking": {
        "input": 15.00,
        "output": 75.00,
    },
    # Claude 3.5 Sonnet - Previous generation balanced model
    "claude-3-5-sonnet-20241022": {
        "input": 3.00,
        "output": 15.00,
    },
    "claude-3-5-sonnet-20240620": {
        "input": 3.00,
        "output": 15.00,
    },
    # Claude 3 Opus - Previous generation high capability
    "claude-3-opus-20240229": {
        "input": 15.00,
        "output": 75.00,
    },
    # Claude 3 Sonnet - Previous generation balanced
    "claude-3-sonnet-20240229": {
        "input": 3.00,
        "output": 15.00,
    },
    # Claude 3 Haiku - Previous generation fast and economical
    "claude-3-haiku-20240307": {
        "input": 0.25,
        "output": 1.25,
    },
    # ========================================
    # OpenAI Models
    # ========================================
    # GPT-4 Turbo - High capability, balanced cost
    "gpt-4-turbo": {
        "input": 10.00,
        "output": 30.00,
    },
    "gpt-4-turbo-2024-04-09": {
        "input": 10.00,
        "output": 30.00,
    },
    # GPT-4 - Original high capability model
    "gpt-4": {
        "input": 30.00,
        "output": 60.00,
    },
    "gpt-4-0613": {
        "input": 30.00,
        "output": 60.00,
    },
    # GPT-4o - Multimodal, cost-effective flagship
    "gpt-4o": {
        "input": 2.50,
        "output": 10.00,
    },
    "gpt-4o-2024-11-20": {
        "input": 2.50,
        "output": 10.00,
    },
    # GPT-4o-mini - Most cost-effective GPT-4 class
    "gpt-4o-mini": {
        "input": 0.15,
        "output": 0.60,
    },
    "gpt-4o-mini-2024-07-18": {
        "input": 0.15,
        "output": 0.60,
    },
    # GPT-3.5 Turbo - Legacy but still useful
    "gpt-3.5-turbo": {
        "input": 0.50,
        "output": 1.50,
    },
    "gpt-3.5-turbo-0125": {
        "input": 0.50,
        "output": 1.50,
    },
    # ========================================
    # Google Gemini Models
    # ========================================
    # Gemini 1.5 Pro - High capability, balanced cost
    "gemini-1.5-pro": {
        "input": 1.25,
        "output": 5.00,
    },
    "gemini-1.5-pro-latest": {
        "input": 1.25,
        "output": 5.00,
    },
    "gemini-pro": {
        "input": 1.25,
        "output": 5.00,
    },
    # Gemini 1.5 Flash - Fast and cost-effective
    "gemini-1.5-flash": {
        "input": 0.075,
        "output": 0.30,
    },
    "gemini-1.5-flash-latest": {
        "input": 0.075,
        "output": 0.30,
    },
    "gemini-flash": {
        "input": 0.075,
        "output": 0.30,
    },
    # Gemini 2.0 Flash - Next generation, experimental
    "gemini-2.0-flash": {
        "input": 0.10,
        "output": 0.40,
    },
    "gemini-2.0-flash-exp": {
        "input": 0.10,
        "output": 0.40,
    },
    # ========================================
    # Ollama Models (Local, Zero Cost)
    # ========================================
    # Llama 3 - Meta's open source model
    "ollama/llama3": {
        "input": 0.00,
        "output": 0.00,
    },
    "ollama/llama3.1": {
        "input": 0.00,
        "output": 0.00,
    },
    "ollama/llama3.2": {
        "input": 0.00,
        "output": 0.00,
    },
    # Mistral - Efficient open source models
    "ollama/mistral": {
        "input": 0.00,
        "output": 0.00,
    },
    "ollama/mixtral": {
        "input": 0.00,
        "output": 0.00,
    },
    # CodeLlama - Specialized for code
    "ollama/codellama": {
        "input": 0.00,
        "output": 0.00,
    },
    # Gemma - Google's open source model
    "ollama/gemma": {
        "input": 0.00,
        "output": 0.00,
    },
    "ollama/gemma2": {
        "input": 0.00,
        "output": 0.00,
    },
    # Qwen - Alibaba's open source model
    "ollama/qwen": {
        "input": 0.00,
        "output": 0.00,
    },
    "ollama/qwen2": {
        "input": 0.00,
        "output": 0.00,
    },
    # Phi - Microsoft's efficient model
    "ollama/phi": {
        "input": 0.00,
        "output": 0.00,
    },
    "ollama/phi3": {
        "input": 0.00,
        "output": 0.00,
    },
    # ========================================
    # Zhipu AI GLM Models (ChatGLM)
    # ========================================
    # GLM-4.7 - Latest model (December 2025)
    "glm-4.7": {
        "input": 0.40,
        "output": 1.50,
    },
    # GLM-4.5 - Previous generation
    "glm-4.5": {
        "input": 0.35,
        "output": 1.55,
    },
    # GLM-4-Plus - High capability variant
    "glm-4-plus": {
        "input": 0.50,
        "output": 2.00,
    },
    # GLM-4 - Standard model
    "glm-4": {
        "input": 0.10,
        "output": 0.10,
    },
    # GLM-4-Air - Lightweight, cost-effective
    "glm-4-air": {
        "input": 0.001,
        "output": 0.001,
    },
    # GLM-4-AirX - Extended air model
    "glm-4-airx": {
        "input": 0.001,
        "output": 0.001,
    },
    # GLM-4-Flash - Fast inference
    "glm-4-flash": {
        "input": 0.001,
        "output": 0.001,
    },
    # GLM-4-FlashX - Extended flash model
    "glm-4-flashx": {
        "input": 0.001,
        "output": 0.001,
    },
    # GLM-3-Turbo - Legacy model
    "glm-3-turbo": {
        "input": 0.001,
        "output": 0.001,
    },
    # ========================================
    # Fallback
    # ========================================
    # Fallback pricing (use sonnet pricing)
    "default": {
        "input": 3.00,
        "output": 15.00,
    },
}


@dataclass
class UsageRecord:
    """Single usage record for an agent session."""

    agent_type: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    timestamp: str
    provider: str = "anthropic"  # Provider name (e.g., "anthropic", "openai")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_type": self.agent_type,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost": self.cost,
            "timestamp": self.timestamp,
            "provider": self.provider,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UsageRecord:
        """Create from dictionary loaded from JSON.

        Defensive against missing or malformed fields to avoid
        crashing when loading historical cost_report.json files.
        """
        try:
            return cls(
                agent_type=str(data.get("agent_type", "unknown")),
                model=str(data.get("model", "unknown")),
                input_tokens=int(data.get("input_tokens", 0)),
                output_tokens=int(data.get("output_tokens", 0)),
                cost=float(data.get("cost", 0.0)),
                timestamp=str(
                    data.get(
                        "timestamp",
                        datetime.now(UTC).isoformat(),
                    )
                ),
                provider=str(data.get("provider", "anthropic")),
            )
        except (TypeError, ValueError) as exc:
            logger.warning("Failed to deserialize UsageRecord from %r: %s", data, exc)
            return cls(
                agent_type="unknown",
                model="unknown",
                input_tokens=0,
                output_tokens=0,
                cost=0.0,
                timestamp=datetime.now(UTC).isoformat(),
            )


@dataclass
class CostTracker:
    """
    Tracks AI API costs for a spec.

    Records usage per agent type and generates cost reports.
    Data is persisted to cost_report.json in the spec directory.

    Args:
        spec_dir: Path to spec directory (e.g., .auto-claude/specs/001)
    """

    spec_dir: Path
    records: list[UsageRecord] = field(default_factory=list)
    _report_file: Path = field(init=False)

    def __post_init__(self):
        """Initialize tracker and load existing records."""
        self.spec_dir = Path(self.spec_dir)
        self._report_file = self.spec_dir / "cost_report.json"
        self._load_records()

    def _load_records(self) -> None:
        """Load existing records from cost_report.json."""
        if not self._report_file.exists():
            return

        try:
            with open(self._report_file, encoding="utf-8") as f:
                data = json.load(f)
                self.records = [
                    UsageRecord.from_dict(record) for record in data.get("records", [])
                ]
        except (json.JSONDecodeError, KeyError, TypeError):
            # If file is corrupted, start fresh
            self.records = []

    def _save_records(self) -> None:
        """Save records to cost_report.json."""
        # Ensure spec directory exists
        self.spec_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "spec_dir": str(self.spec_dir),
            "total_cost": self.get_total_cost(),
            "records": [record.to_dict() for record in self.records],
            "last_updated": datetime.now(UTC).isoformat() + "Z",
        }

        with open(self._report_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """
        Calculate cost for a model operation across multiple providers.

        Supports models from:
        - Claude (Anthropic): claude-opus-4-5-*, claude-sonnet-4-5-*, claude-haiku-4-5-*,
          claude-3-5-sonnet-*, claude-3-opus-*, claude-3-sonnet-*, claude-3-haiku-*
        - OpenAI: gpt-4, gpt-4o, gpt-4-turbo, gpt-3.5-turbo
        - Google Gemini: gemini-1.5-pro, gemini-1.5-flash, gemini-2.0-flash
        - Zhipu AI GLM: glm-4.7, glm-4.5, glm-4-plus, glm-4, glm-4-air, glm-4-flash, glm-3-turbo
        - Ollama (local): ollama/llama3, ollama/mistral, etc. (zero cost)

        If a model is not found in the pricing database, falls back to default
        pricing (Claude Sonnet rates) and logs a warning.

        Args:
            model: Model identifier (e.g., "gpt-4", "gemini-1.5-pro", "glm-4.7", "ollama/llama3")
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in dollars (0.00 for local models, calculated for API models)
        """
        # Get pricing for model (fallback to default if not found)
        if model not in MODEL_PRICING:
            logger.warning(
                "Model '%s' not found in pricing database. "
                "Using default pricing (Claude Sonnet rates). "
                "Consider adding this model to MODEL_PRICING in cost_tracking.py",
                model,
            )
            pricing = MODEL_PRICING["default"]
        else:
            pricing = MODEL_PRICING[model]

        # Calculate cost (pricing is per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        total_cost = input_cost + output_cost

        logger.debug(
            "Cost calculation: model=%s, input_tokens=%d, output_tokens=%d, cost=$%.6f",
            model,
            input_tokens,
            output_tokens,
            total_cost,
        )

        return total_cost

    def log_usage(
        self,
        agent_type: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        provider: str = "anthropic",
    ) -> float:
        """
        Log usage for an agent session.

        Args:
            agent_type: Type of agent (e.g., "coder", "planner")
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            provider: Model provider (e.g., "anthropic", "openai")

        Returns:
            Cost of this operation in dollars
        """
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        record = UsageRecord(
            agent_type=agent_type,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            timestamp=datetime.now(UTC).isoformat() + "Z",
            provider=provider,
        )

        self.records.append(record)
        self._save_records()

        return cost

    def get_total_cost(self) -> float:
        """Get total cost across all records."""
        return sum(record.cost for record in self.records)

    def get_cost_by_agent(self) -> dict[str, float]:
        """Get cost breakdown by agent type."""
        costs: dict[str, float] = {}
        for record in self.records:
            costs[record.agent_type] = costs.get(record.agent_type, 0.0) + record.cost
        return costs

    def get_cost_by_model(self) -> dict[str, float]:
        """Get cost breakdown by model."""
        costs: dict[str, float] = {}
        for record in self.records:
            costs[record.model] = costs.get(record.model, 0.0) + record.cost
        return costs

    def get_cost_by_provider(self) -> dict[str, float]:
        """Get cost breakdown by provider."""
        costs: dict[str, float] = {}
        for record in self.records:
            costs[record.provider] = costs.get(record.provider, 0.0) + record.cost
        return costs

    def get_token_usage(self) -> dict[str, int]:
        """Get total token usage (input + output)."""
        return {
            "input_tokens": sum(record.input_tokens for record in self.records),
            "output_tokens": sum(record.output_tokens for record in self.records),
            "total_tokens": sum(
                record.input_tokens + record.output_tokens for record in self.records
            ),
        }

    def get_cost_summary(self) -> str:
        """
        Generate human-readable cost summary.

        Returns:
            Formatted string with cost breakdown
        """
        if not self.records:
            return "No usage recorded yet."

        total = self.get_total_cost()
        by_agent = self.get_cost_by_agent()
        by_model = self.get_cost_by_model()
        by_provider = self.get_cost_by_provider()
        tokens = self.get_token_usage()

        lines = [
            "=" * 60,
            "COST SUMMARY",
            "=" * 60,
            f"Total Cost: ${total:.4f}",
            "",
            "Cost by Agent Type:",
            "-" * 60,
        ]

        for agent, cost in sorted(by_agent.items(), key=lambda x: x[1], reverse=True):
            percentage = (cost / total * 100) if total > 0 else 0
            lines.append(f"  {agent:20s} ${cost:7.4f} ({percentage:5.1f}%)")

        lines.extend(
            [
                "",
                "Cost by Model:",
                "-" * 60,
            ]
        )

        for model, cost in sorted(by_model.items(), key=lambda x: x[1], reverse=True):
            percentage = (cost / total * 100) if total > 0 else 0
            # Shorten model name for display
            model_short = (
                model.replace("claude-", "")
                .replace("-20250929", "")
                .replace("-20251001", "")
                .replace("-20251101", "")
            )
            lines.append(f"  {model_short:20s} ${cost:7.4f} ({percentage:5.1f}%)")

        lines.extend(
            [
                "",
                "Cost by Provider:",
                "-" * 60,
            ]
        )

        for provider, cost in sorted(
            by_provider.items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (cost / total * 100) if total > 0 else 0
            lines.append(f"  {provider:20s} ${cost:7.4f} ({percentage:5.1f}%)")

        lines.extend(
            [
                "",
                "Token Usage:",
                "-" * 60,
                f"  Input Tokens:  {tokens['input_tokens']:,}",
                f"  Output Tokens: {tokens['output_tokens']:,}",
                f"  Total Tokens:  {tokens['total_tokens']:,}",
                "=" * 60,
            ]
        )

        return "\n".join(lines)
