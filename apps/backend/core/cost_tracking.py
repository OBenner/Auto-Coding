"""
Cost Tracking System for Multi-Model Agent Orchestration
=========================================================

Tracks AI API costs across different models and agent types.
Provides cost reporting and analysis for budget management.

Components:
- MODEL_PRICING: Pricing data for all Claude models (per 1M tokens)
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

    # Get cost summary
    summary = tracker.get_cost_summary()
    print(summary)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Claude model pricing (per 1M tokens)
# Based on Anthropic pricing as of January 2025
# https://www.anthropic.com/pricing
MODEL_PRICING: dict[str, dict[str, float]] = {
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
        """Create from dictionary loaded from JSON."""
        return cls(
            agent_type=data["agent_type"],
            model=data["model"],
            input_tokens=data["input_tokens"],
            output_tokens=data["output_tokens"],
            cost=data["cost"],
            timestamp=data["timestamp"],
            provider=data.get("provider", "anthropic"),  # Default for backward compatibility
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
        Calculate cost for a model operation.

        Args:
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in dollars
        """
        # Get pricing for model (fallback to default if not found)
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])

        # Calculate cost (pricing is per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

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

        for provider, cost in sorted(by_provider.items(), key=lambda x: x[1], reverse=True):
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
