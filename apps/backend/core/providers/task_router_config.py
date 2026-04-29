"""
Configuration loader for task-aware model routing.

Loads the routing table from YAML when present, applies environment
overrides, and falls back to hardcoded defaults so runtime routing remains
available in packaged or minimal installations.
"""

from __future__ import annotations

import copy
import logging
import os
from pathlib import Path
from typing import Any

import yaml
from core.providers.config import AIEngineProvider
from core.providers.cost_calculator import MODEL_PRICING

logger = logging.getLogger(__name__)


DEFAULT_MODEL_ROUTING_CONFIG: dict[str, Any] = {
    "complexity_thresholds": {
        "high": 0.7,
        "medium": 0.4,
    },
    "scoring_weights": {
        "base_score": 0.3,
        "high_risk_issue": 0.1,
        "high_risk_max": 0.3,
        "medium_risk_issue": 0.05,
        "medium_risk_max": 0.15,
        "files_threshold_medium": 5,
        "files_score_medium": 0.15,
        "files_threshold_high": 10,
        "files_score_high": 0.25,
        "architecture_keywords": [
            "architect",
            "design",
            "refactor",
            "migrate",
            "rewrite",
            "restructure",
            "overhaul",
        ],
        "architecture_keyword_score": 0.2,
        "trivial_keywords": [
            "fix typo",
            "update comment",
            "format",
            "whitespace",
            "rename variable",
        ],
        "trivial_keyword_score": -0.2,
        "security_work_type_bonus": 0.1,
    },
    "routing": {
        "high": {
            "provider": "claude",
            "model": "claude-sonnet-4-5-20250929",
            "max_tokens": 16384,
        },
        "medium": {
            "provider": "openai",
            "model": "gpt-4o",
            "max_tokens": 8192,
        },
        "low": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "max_tokens": 4096,
        },
    },
    "estimated_tokens": {
        "input": 5000,
        "output": 2000,
    },
}


def get_default_config_path() -> Path:
    """
    Return the default model routing config path.

    Returns:
        Path to apps/backend/config/model_routing.yaml.
    """
    return Path(__file__).resolve().parents[2] / "config" / "model_routing.yaml"


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge dictionaries without mutating either input."""
    merged = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _apply_env_overrides(config: dict[str, Any]) -> dict[str, Any]:
    """Apply MODEL_ROUTER_{LEVEL}_PROVIDER/MODEL env overrides."""
    updated = copy.deepcopy(config)
    routing = updated.setdefault("routing", {})
    for level in ("high", "medium", "low"):
        route = routing.setdefault(level, {})
        env_prefix = f"MODEL_ROUTER_{level.upper()}"
        provider = os.getenv(f"{env_prefix}_PROVIDER")
        model = os.getenv(f"{env_prefix}_MODEL")
        if provider:
            route["provider"] = provider.lower()
        if model:
            route["model"] = model
    return updated


def _validate_config(config: dict[str, Any]) -> None:
    """
    Validate provider names, model names, and required routing sections.

    Args:
        config: Loaded routing configuration.

    Raises:
        ValueError: If the config references an unsupported provider or model.
    """
    valid_providers = {provider.value for provider in AIEngineProvider}
    routing = config.get("routing", {})

    for level in ("high", "medium", "low"):
        if level not in routing:
            raise ValueError(
                f"Missing model routing entry for complexity level: {level}"
            )

        provider = str(routing[level].get("provider", "")).lower()
        model = str(routing[level].get("model", ""))

        if provider not in valid_providers:
            raise ValueError(
                f"Invalid model router provider for {level}: {provider}. "
                f"Supported providers: {', '.join(sorted(valid_providers))}"
            )
        if model not in MODEL_PRICING:
            raise ValueError(
                f"Invalid model router model for {level}: {model}. "
                "Model must exist in MODEL_PRICING."
            )

    thresholds = config.get("complexity_thresholds", {})
    if float(thresholds.get("high", 0.7)) <= float(thresholds.get("medium", 0.4)):
        raise ValueError("High complexity threshold must be greater than medium.")


def load_model_routing_config(config_path: Path | None = None) -> dict[str, Any]:
    """
    Load model routing configuration from YAML with safe defaults.

    Args:
        config_path: Optional explicit YAML path. If omitted, uses
            apps/backend/config/model_routing.yaml.

    Returns:
        Validated routing configuration dictionary.

    Raises:
        ValueError: If YAML content is invalid or references unknown
            providers/models.
    """
    path = config_path or get_default_config_path()
    config = copy.deepcopy(DEFAULT_MODEL_ROUTING_CONFIG)

    if path.exists():
        try:
            with path.open(encoding="utf-8") as config_file:
                loaded = yaml.safe_load(config_file) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML in model routing config: {path}") from exc
        if not isinstance(loaded, dict):
            raise ValueError(f"Model routing config must be a mapping: {path}")
        config = _deep_merge(config, loaded)
        logger.debug("Loaded model routing config from %s", path)
    else:
        logger.info("Model routing config not found at %s; using defaults", path)

    config = _apply_env_overrides(config)
    _validate_config(config)
    return config
