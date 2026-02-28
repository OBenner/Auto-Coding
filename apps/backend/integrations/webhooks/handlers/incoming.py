"""
Incoming Webhook Handlers
=========================

Base classes and implementations for processing incoming webhooks from external services.
Handles parsing, validation, and triggering builds based on webhook events.

Design:
- Abstract base class `IncomingWebhookHandler` defines the handler interface
- Concrete implementations for GitHub, GitLab, and generic webhooks
- Each handler validates payload format, extracts relevant data, and triggers actions
- Handlers return structured results for logging and debugging

Usage:
    >>> from integrations.webhooks.handlers.incoming import GitHubWebhookHandler
    >>> handler = GitHubWebhookHandler(spec_dir=Path("/path/to/spec"))
    >>> result = handler.handle_webhook(webhook_config, payload)
    >>> print(result.action_taken)
"""

from __future__ import annotations

import ast
import logging
import operator
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ..models import WebhookConfig

# =============================================================================
# Logging
# =============================================================================


logger = logging.getLogger(__name__)


# =============================================================================
# Handler Result Types
# =============================================================================


class WebhookAction(str, Enum):
    """Actions that can be taken by webhook handlers."""

    TRIGGER_BUILD = "trigger_build"
    TRIGGER_SUBTASK = "trigger_subtask"
    UPDATE_STATUS = "update_status"
    NO_ACTION = "no_action"
    ERROR = "error"


class HandlerResult(BaseModel):
    """
    Result of processing a webhook.

    Encapsulates the outcome of webhook processing including
    what action was taken, any data extracted, and error information.
    """

    success: bool = Field(description="Whether processing was successful")
    action_taken: WebhookAction = Field(
        default=WebhookAction.NO_ACTION,
        description="What action was taken",
    )
    message: str = Field(
        default="",
        description="Human-readable result message",
    )
    extracted_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Data extracted from webhook payload",
    )
    error: str | None = Field(
        default=None,
        description="Error message if processing failed",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "action_taken": self.action_taken.value,
            "message": self.message,
            "extracted_data": self.extracted_data,
            "error": self.error,
        }


# =============================================================================
# Base Handler Interface
# =============================================================================


class IncomingWebhookHandler(ABC):
    """
    Abstract base class for incoming webhook handlers.

    Defines the interface for processing webhooks from external services.
    Concrete implementations handle specific webhook formats (GitHub, GitLab, etc.)

    Subclasses must implement:
    - validate_payload(): Check if payload is valid for this handler
    - extract_event_data(): Extract relevant data from payload
    - determine_action(): Decide what action to take based on payload

    The handler can optionally trigger builds or subtasks based on webhook events.
    """

    def __init__(
        self,
        spec_dir: Path,
        project_dir: Path | None = None,
    ):
        """
        Initialize the webhook handler.

        Args:
            spec_dir: Spec directory (contains implementation_plan.json)
            project_dir: Project root directory (for build triggering)
        """
        self.spec_dir = spec_dir
        self.project_dir = project_dir or spec_dir.parent.parent

    @abstractmethod
    def validate_payload(self, payload: dict[str, Any]) -> bool:
        """
        Validate that the payload is correctly formatted for this handler.

        Args:
            payload: Webhook payload data

        Returns:
            True if payload is valid, False otherwise
        """
        pass

    @abstractmethod
    def extract_event_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Extract relevant data from the webhook payload.

        Args:
            payload: Webhook payload data

        Returns:
            Dictionary of extracted data (event type, repo, branch, etc.)
        """
        pass

    @abstractmethod
    def determine_action(self, payload: dict[str, Any]) -> WebhookAction:
        """
        Determine what action to take based on the webhook payload.

        Args:
            payload: Webhook payload data

        Returns:
            WebhookAction indicating what action to take
        """
        pass

    def handle_webhook(
        self,
        webhook_config: WebhookConfig,
        payload: dict[str, Any],
    ) -> HandlerResult:
        """
        Process an incoming webhook.

        This is the main entry point for webhook processing. It validates
        the payload, extracts data, determines what action to take, and
        optionally executes that action (like triggering a build).

        Args:
            webhook_config: Configuration for this webhook
            payload: Webhook payload data

        Returns:
            HandlerResult with processing outcome
        """
        try:
            # Validate payload
            if not self.validate_payload(payload):
                return HandlerResult(
                    success=False,
                    action_taken=WebhookAction.ERROR,
                    message="Payload validation failed",
                    error="Invalid payload format for this handler",
                )

            # Extract event data
            event_data = self.extract_event_data(payload)
            logger.info(
                f"Extracted event: integration={event_data.get('integration')}, "
                f"event_type={event_data.get('event_type')}, "
                f"webhook_id={webhook_config.id}"
            )

            # Determine action
            action = self.determine_action(payload)
            logger.info(f"Determined action: {action.value}")

            # Execute action if needed
            if action == WebhookAction.TRIGGER_BUILD:
                return self._handle_trigger_build(
                    webhook_config=webhook_config,
                    payload=payload,
                    event_data=event_data,
                )
            elif action == WebhookAction.TRIGGER_SUBTASK:
                return self._handle_trigger_subtask(
                    webhook_config=webhook_config,
                    payload=payload,
                    event_data=event_data,
                )
            else:
                return HandlerResult(
                    success=True,
                    action_taken=action,
                    message="Webhook processed successfully (no action taken)",
                    extracted_data=event_data,
                )

        except Exception as e:
            logger.error(f"Error handling webhook: {e}", exc_info=True)
            return HandlerResult(
                success=False,
                action_taken=WebhookAction.ERROR,
                message="Webhook processing failed",
                error=str(e),
            )

    def _handle_trigger_build(
        self,
        webhook_config: WebhookConfig,
        payload: dict[str, Any],
        event_data: dict[str, Any],
    ) -> HandlerResult:
        """
        Handle triggering a build from a webhook.

        Args:
            webhook_config: Webhook configuration
            payload: Webhook payload
            event_data: Extracted event data

        Returns:
            HandlerResult with build trigger outcome
        """
        try:
            # For now, just log the intent to trigger
            # In a future subtask, this will integrate with the build system
            logger.info(
                f"Would trigger build for spec {event_data.get('spec_id')} "
                f"from webhook {webhook_config.id}"
            )

            return HandlerResult(
                success=True,
                action_taken=WebhookAction.TRIGGER_BUILD,
                message=f"Build trigger prepared for {event_data.get('spec_id', 'unknown')}",
                extracted_data=event_data,
            )

        except Exception as e:
            logger.error(f"Error triggering build: {e}", exc_info=True)
            return HandlerResult(
                success=False,
                action_taken=WebhookAction.ERROR,
                message="Failed to trigger build",
                error=str(e),
                extracted_data=event_data,
            )

    def _handle_trigger_subtask(
        self,
        webhook_config: WebhookConfig,
        payload: dict[str, Any],
        event_data: dict[str, Any],
    ) -> HandlerResult:
        """
        Handle triggering a specific subtask from a webhook.

        Args:
            webhook_config: Webhook configuration
            payload: Webhook payload
            event_data: Extracted event data

        Returns:
            HandlerResult with subtask trigger outcome
        """
        try:
            # For now, just log the intent to trigger
            # In a future subtask, this will integrate with the build system
            subtask_id = event_data.get("subtask_id", "unknown")
            logger.info(
                f"Would trigger subtask {subtask_id} from webhook {webhook_config.id}"
            )

            return HandlerResult(
                success=True,
                action_taken=WebhookAction.TRIGGER_SUBTASK,
                message=f"Subtask trigger prepared for {subtask_id}",
                extracted_data=event_data,
            )

        except Exception as e:
            logger.error(f"Error triggering subtask: {e}", exc_info=True)
            return HandlerResult(
                success=False,
                action_taken=WebhookAction.ERROR,
                message="Failed to trigger subtask",
                error=str(e),
                extracted_data=event_data,
            )


# =============================================================================
# GitHub Webhook Handler
# =============================================================================


class GitHubWebhookHandler(IncomingWebhookHandler):
    """
    Handler for GitHub webhooks.

    Processes incoming webhooks from GitHub for events like:
    - Push events (commits pushed to a branch)
    - Pull request events (PR opened, merged, closed)

    Extracts repository, branch, and commit information to trigger builds.
    """

    def validate_payload(self, payload: dict[str, Any]) -> bool:
        """
        Validate that the payload is a correctly formatted GitHub webhook.

        Args:
            payload: Webhook payload data

        Returns:
            True if payload is valid GitHub webhook, False otherwise
        """
        # GitHub webhooks should have a 'repository' key
        if "repository" not in payload:
            return False

        # Repository should be a dict with 'name' and 'full_name'
        repository = payload.get("repository", {})
        if not isinstance(repository, dict):
            return False

        if "name" not in repository or "full_name" not in repository:
            return False

        # Should have some kind of event indicator
        # Either 'ref' (for push) or 'pull_request' (for PR events)
        # or 'action' (for most other events)
        if not any(key in payload for key in ["ref", "pull_request", "action"]):
            return False

        return True

    def extract_event_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Extract relevant data from the GitHub webhook payload.

        Args:
            payload: Webhook payload data

        Returns:
            Dictionary with extracted data (event type, repo, branch, etc.)
        """
        repository = payload.get("repository", {})

        # Extract repository information
        repo_name = repository.get("name", "")
        repo_full_name = repository.get("full_name", "")
        repo_url = repository.get("html_url", "")
        clone_url = repository.get("clone_url", "")

        # Determine event type
        event_type = "unknown"
        if "ref" in payload:
            event_type = "push"
        elif "pull_request" in payload:
            event_type = "pull_request"

        # Extract branch/ref information
        ref = payload.get("ref", "")
        branch = ""

        if ref.startswith("refs/heads/"):
            branch = ref.replace("refs/heads/", "")
        elif ref.startswith("refs/tags/"):
            branch = ref.replace("refs/tags/", "")

        # Extract PR information if present
        pr_info = {}
        if "pull_request" in payload:
            pr = payload.get("pull_request", {})
            pr_info = {
                "pr_number": pr.get("number"),
                "pr_title": pr.get("title"),
                "pr_action": payload.get("action", ""),
                "pr_state": pr.get("state", ""),
                "pr_merged": pr.get("merged", False),
                "pr_merge_commit_sha": pr.get("merge_commit_sha"),
            }

        # Extract sender/actor information
        sender = payload.get("sender", {})
        actor = sender.get("login", "")

        # Extract commit information
        commit_info = {}
        if event_type == "push":
            commit_info = {
                "before": payload.get("before", ""),
                "after": payload.get("after", ""),
                "commits": [
                    {
                        "id": c.get("id"),
                        "message": c.get("message"),
                        "author": c.get("author", {}).get("name"),
                        "url": c.get("url"),
                    }
                    for c in payload.get("commits", [])
                ],
                "pusher": payload.get("pusher", {}).get("email", ""),
            }
        elif event_type == "pull_request":
            pr = payload.get("pull_request", {})
            commit_info = {
                "pr_head_sha": pr.get("head", {}).get("sha"),
                "pr_base_sha": pr.get("base", {}).get("sha"),
                "pr_merge_commit_sha": pr.get("merge_commit_sha"),
            }

        # Build extracted data
        extracted = {
            "integration": "github",
            "event_type": event_type,
            "repo_name": repo_name,
            "repo_full_name": repo_full_name,
            "repo_url": repo_url,
            "clone_url": clone_url,
            "ref": ref,
            "branch": branch,
            "actor": actor,
            **pr_info,
            "commits": commit_info,
        }

        # Add spec_id if available from webhook config mapping
        # This would be set when the webhook is configured
        # For now, we'll derive it from the branch name or PR title
        if branch:
            # Try to extract spec ID from branch name
            # Handles patterns like "feature/084-xxx", "084-xxx", "auto-code/084-xxx"
            import re

            # Strip prefix (e.g., "feature/" or "auto-code/")
            branch_name = branch.rsplit("/", 1)[-1] if "/" in branch else branch
            # Look for leading numeric ID like "084-..."
            match = re.match(r"^(\d+)-", branch_name)
            if match:
                extracted["spec_id"] = match.group(1)

        return extracted

    def determine_action(self, payload: dict[str, Any]) -> WebhookAction:
        """
        Determine what action to take based on the GitHub webhook payload.

        Args:
            payload: Webhook payload data

        Returns:
            WebhookAction indicating what action to take
        """
        # Handle push events
        if "ref" in payload:
            ref = payload.get("ref", "")

            # Only trigger on branch pushes, not tags
            if ref.startswith("refs/heads/"):
                branch = ref.replace("refs/heads/", "")

                # Skip specific branches if needed
                # For example, skip build branches or dependency update bots
                if branch in ["main", "master", "develop"]:
                    # Could still trigger if configured
                    logger.debug(f"Push to {branch} - no action by default")
                    return WebhookAction.NO_ACTION

                # Trigger build for feature branches
                logger.info(f"Push to feature branch {branch} - triggering build")
                return WebhookAction.TRIGGER_BUILD

        # Handle pull request events
        if "pull_request" in payload:
            action = payload.get("action", "")
            pr = payload.get("pull_request", {})
            merged = pr.get("merged", False)

            # Only trigger on merged PRs
            if action == "closed" and merged:
                logger.info("PR merged - triggering build")
                return WebhookAction.TRIGGER_BUILD

            # Could also trigger when PR is opened for testing
            if action == "opened":
                logger.info("PR opened - could trigger test build")
                return WebhookAction.NO_ACTION

        return WebhookAction.NO_ACTION


# =============================================================================
# Generic Webhook Handler
# =============================================================================


class GenericWebhookHandler(IncomingWebhookHandler):
    """
    Handler for generic/custom webhooks with payload templates.

    Provides flexible webhook handling for custom integrations where
    the payload structure doesn't match pre-built handlers like GitHub.

    Features:
    - Payload template support for extracting data from custom payloads
    - Simple variable substitution (e.g., {{variable_name}})
    - Conditional triggering based on extracted values
    - Minimal validation - accepts most payload structures

    The payload_template in webhook_config can be:
    - A dict mapping variable names to JSON paths (e.g., {"branch": "ref"})
    - A list of paths to extract (e.g., ["branch", "commit", "repo"])
    - None to pass through the entire payload

    Examples:
        >>> config = WebhookConfig(
        ...     id="custom-1",
        ...     name="Custom CI webhook",
        ...     type=WebhookType.INCOMING,
        ...     integration=WebhookIntegration.GENERIC,
        ...     path="/webhooks/custom-ci",
        ...     payload_template={"branch": "ref", "commit": "after"}
        ... )
        >>> handler = GenericWebhookHandler(spec_dir=Path("/path/to/spec"))
        >>> result = handler.handle_webhook(config, {"ref": "main", "after": "abc123"})
        >>> print(result.extracted_data)
        {'branch': 'main', 'commit': 'abc123'}
    """

    def validate_payload(self, payload: dict[str, Any]) -> bool:
        """
        Validate that the payload is a dictionary.

        Generic handler accepts most payloads as long as they're structured data.
        Minimal validation to allow maximum flexibility.

        Args:
            payload: Webhook payload data

        Returns:
            True if payload is a dict, False otherwise
        """
        # Generic handler accepts any dict payload
        # No strict validation to allow custom integrations
        return isinstance(payload, dict)

    def extract_event_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Extract relevant data from the webhook payload using templates.

        Uses the payload_template from webhook_config to extract data.
        Supports multiple template formats:

        1. Dict template: {"target_var": "source_path", ...}
           - Extracts specific fields from payload
           - Maps payload paths to output variable names

        2. List template: ["field1", "field2", ...]
           - Extracts listed fields if they exist in payload
           - Preserves original field names

        3. None template:
           - Passes through entire payload

        Args:
            payload: Webhook payload data

        Returns:
            Dictionary with extracted data
        """
        # Get the template from config (will be passed via handle_webhook)
        # For now, return the entire payload
        # The handle_webhook method will apply the template
        return {
            "integration": "generic",
            "raw_payload": payload,
        }

    def determine_action(self, payload: dict[str, Any]) -> WebhookAction:
        """
        Determine what action to take based on the webhook payload.

        Generic handler defaults to TRIGGER_BUILD unless the webhook
        config specifies otherwise (e.g., event filters).

        Args:
            payload: Webhook payload data

        Returns:
            WebhookAction indicating what action to take
        """
        # Default to triggering build for generic webhooks
        # The webhook_config can have custom_event_filter to modify this
        return WebhookAction.TRIGGER_BUILD

    def handle_webhook(
        self,
        webhook_config: WebhookConfig,
        payload: dict[str, Any],
    ) -> HandlerResult:
        """
        Process an incoming webhook with payload template support.

        Overrides the base implementation to apply payload templates
        for data extraction and transformation.

        Args:
            webhook_config: Configuration for this webhook
            payload: Webhook payload data

        Returns:
            HandlerResult with processing outcome
        """
        try:
            # Validate payload
            if not self.validate_payload(payload):
                return HandlerResult(
                    success=False,
                    action_taken=WebhookAction.ERROR,
                    message="Payload validation failed",
                    error="Invalid payload format for generic handler",
                )

            # Apply payload template if configured
            template = webhook_config.payload_template
            if template is not None:
                event_data = self._apply_payload_template(payload, template)
                logger.info(
                    f"Applied payload template, extracted: {list(event_data.keys())}"
                )
            else:
                # No template - use raw payload
                event_data = {
                    "integration": "generic",
                    "raw_payload": payload,
                }
                logger.info("No payload template, using raw payload")

            # Add integration info
            event_data["integration"] = "generic"

            # Determine action
            action = self.determine_action(payload)

            # Apply custom event filter if configured
            if webhook_config.custom_event_filter:
                if not self._evaluate_event_filter(
                    event_data,
                    webhook_config.custom_event_filter,
                ):
                    logger.info("Event filter did not match, no action taken")
                    return HandlerResult(
                        success=True,
                        action_taken=WebhookAction.NO_ACTION,
                        message="Event filter did not match",
                        extracted_data=event_data,
                    )

            # Execute action
            if action == WebhookAction.TRIGGER_BUILD:
                return self._handle_trigger_build(
                    webhook_config=webhook_config,
                    payload=payload,
                    event_data=event_data,
                )
            elif action == WebhookAction.TRIGGER_SUBTASK:
                return self._handle_trigger_subtask(
                    webhook_config=webhook_config,
                    payload=payload,
                    event_data=event_data,
                )
            else:
                return HandlerResult(
                    success=True,
                    action_taken=action,
                    message="Webhook processed successfully (no action taken)",
                    extracted_data=event_data,
                )

        except Exception as e:
            logger.error(f"Error handling generic webhook: {e}", exc_info=True)
            return HandlerResult(
                success=False,
                action_taken=WebhookAction.ERROR,
                message="Webhook processing failed",
                error=str(e),
            )

    def _evaluate_event_filter(
        self,
        event_data: dict[str, Any],
        filter_expr: str,
    ) -> bool:
        """
        Evaluate a custom event filter expression safely.

        Supports simple comparison expressions like:
        - "field == 'value'"
        - "field != 'value'"
        - "field == 'value1' and other_field == 'value2'"
        - "field == 'value1' or other_field == 'value2'"

        Uses AST parsing instead of eval() to prevent code injection.

        Args:
            event_data: Extracted event data
            filter_expr: Filter expression to evaluate

        Returns:
            True if filter matches, False otherwise
        """
        try:
            tree = ast.parse(filter_expr, mode="eval")
            return bool(self._safe_eval_node(tree.body, event_data))
        except Exception as e:
            logger.warning(f"Failed to evaluate event filter '{filter_expr}': {e}")
            return False

    def _safe_eval_node(self, node: ast.AST, context: dict[str, Any]) -> Any:
        """Safely evaluate an AST node against context data."""
        _SAFE_OPS = {
            ast.Eq: operator.eq,
            ast.NotEq: operator.ne,
            ast.Lt: operator.lt,
            ast.LtE: operator.le,
            ast.Gt: operator.gt,
            ast.GtE: operator.ge,
            ast.In: lambda a, b: a in b,
            ast.NotIn: lambda a, b: a not in b,
        }

        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return context.get(node.id)
        elif isinstance(node, ast.Compare):
            left = self._safe_eval_node(node.left, context)
            for op_node, comparator in zip(node.ops, node.comparators):
                op_func = _SAFE_OPS.get(type(op_node))
                if op_func is None:
                    raise ValueError(
                        f"Unsupported comparison operator: {type(op_node).__name__}"
                    )
                right = self._safe_eval_node(comparator, context)
                if not op_func(left, right):
                    return False
                left = right
            return True
        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(self._safe_eval_node(v, context) for v in node.values)
            elif isinstance(node.op, ast.Or):
                return any(self._safe_eval_node(v, context) for v in node.values)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not self._safe_eval_node(node.operand, context)
        elif isinstance(node, ast.Attribute):
            value = self._safe_eval_node(node.value, context)
            if isinstance(value, dict):
                return value.get(node.attr)
            return getattr(value, node.attr, None)
        elif isinstance(node, ast.Call):
            # Only allow safe string methods
            if isinstance(node.func, ast.Attribute) and node.func.attr in (
                "startswith",
                "endswith",
                "lower",
                "upper",
                "strip",
            ):
                obj = self._safe_eval_node(node.func.value, context)
                args = [self._safe_eval_node(a, context) for a in node.args]
                if isinstance(obj, str):
                    return getattr(obj, node.func.attr)(*args)
            raise ValueError(f"Unsupported function call: {ast.dump(node.func)}")

        raise ValueError(f"Unsupported AST node: {type(node).__name__}")

    def _apply_payload_template(
        self,
        payload: dict[str, Any],
        template: dict[str, Any] | list[str] | None,
    ) -> dict[str, Any]:
        """
        Apply payload template to extract data from payload.

        Args:
            payload: Original webhook payload
            template: Payload template from webhook_config

        Returns:
            Extracted and transformed data
        """
        extracted = {}

        if template is None:
            # No template - return entire payload
            return payload

        if isinstance(template, list):
            # List of field names to extract
            for field in template:
                if isinstance(field, str) and field in payload:
                    extracted[field] = payload[field]

        elif isinstance(template, dict):
            # Dict mapping output names to source paths
            for target_key, source_path in template.items():
                if not isinstance(source_path, str):
                    continue

                # Support nested path notation (e.g., "repo.name" or "repo['name']")
                value = self._get_nested_value(payload, source_path)
                if value is not None:
                    extracted[target_key] = value

        else:
            # Unknown template format - return payload as-is
            logger.warning(f"Unknown template format: {type(template)}")
            return payload

        return extracted

    def _get_nested_value(
        self,
        data: dict[str, Any],
        path: str,
    ) -> Any:
        """
        Get a value from nested dict using path notation.

        Supports:
        - Dot notation: "repo.name"
        - Bracket notation: "repo['name']" or "repo[0]"
        - Mixed notation: "repo['owner'].login"

        Args:
            data: Source dictionary
            path: Path to value (e.g., "repo.name" or "repository.full_name")

        Returns:
            Value at path, or None if not found
        """
        if not path:
            return None

        # Handle bracket notation
        if "[" in path:
            # Parse path with brackets
            # e.g., "repo['owner']['login']" or "items[0].name"
            try:
                # Use regex to find all bracket-enclosed keys
                import re

                # Pattern to match: ['key'] or ["key"] or [0] or .key
                # Split into tokens: base name + list of [brackets] + dotted keys
                tokens = re.findall(
                    r"""([^\.\[\]]+)  # Unquoted (like 'repo' or 'name')
                        |\['([^']*)'\]  # ['key'] style
                        |\["([^"]*)"\]  # ["key"] style
                        |\[(\d+)\]      # [0] style""",
                    path,
                    re.VERBOSE,
                )

                value = data
                i = 0

                while i < len(tokens):
                    token = tokens[i]

                    # token is a tuple: (unquoted, single_quoted, double_quoted, index)
                    # One of these will be non-empty (regex returns empty strings, not None)
                    unquoted, single_q, double_q, index_str = token

                    if i == 0 and unquoted:
                        # First token is the base name
                        if isinstance(value, dict):
                            value = value.get(unquoted)
                        else:
                            return None
                    elif single_q:
                        # ['key'] style
                        if isinstance(value, dict):
                            value = value.get(single_q)
                        elif isinstance(value, list) and single_q.isdigit():
                            idx = int(single_q)
                            if 0 <= idx < len(value):
                                value = value[idx]
                            else:
                                return None
                        else:
                            return None
                    elif double_q:
                        # ["key"] style
                        if isinstance(value, dict):
                            value = value.get(double_q)
                        elif isinstance(value, list) and double_q.isdigit():
                            idx = int(double_q)
                            if 0 <= idx < len(value):
                                value = value[idx]
                            else:
                                return None
                        else:
                            return None
                    elif index_str:
                        # [0] style - numeric index
                        idx = int(index_str)
                        if isinstance(value, list) and 0 <= idx < len(value):
                            value = value[idx]
                        elif isinstance(value, dict) and str(idx) in value:
                            value = value.get(str(idx))
                        else:
                            return None
                    elif unquoted:
                        # .key style (dotted notation)
                        if isinstance(value, dict):
                            value = value.get(unquoted)
                        else:
                            return None

                    if value is None:
                        return None

                    i += 1

                return value
            except (ValueError, AttributeError, KeyError, ImportError):
                # If regex fails, fall back to simpler parsing
                pass

        # Handle simple dot notation
        keys = path.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return None
            else:
                return None

        return value


# =============================================================================
# Handler Registry
# =============================================================================


class HandlerRegistry:
    """
    Registry for webhook handlers.

    Maps webhook integrations to their handler implementations.
    """

    _handlers: dict[str, type[IncomingWebhookHandler]] = {}

    @classmethod
    def register(
        cls,
        integration: str,
        handler_class: type[IncomingWebhookHandler],
    ) -> None:
        """
        Register a handler class for an integration type.

        Args:
            integration: Integration identifier (e.g., "github", "gitlab")
            handler_class: Handler class to register
        """
        cls._handlers[integration] = handler_class
        logger.debug(f"Registered webhook handler for integration: {integration}")

    @classmethod
    def get_handler(
        cls,
        integration: str,
        spec_dir: Path,
        project_dir: Path | None = None,
    ) -> IncomingWebhookHandler | None:
        """
        Get a handler instance for an integration.

        Args:
            integration: Integration identifier
            spec_dir: Spec directory
            project_dir: Project directory (optional)

        Returns:
            Handler instance or None if not registered
        """
        handler_class = cls._handlers.get(integration)
        if not handler_class:
            logger.warning(f"No handler registered for integration: {integration}")
            return None

        return handler_class(spec_dir=spec_dir, project_dir=project_dir)

    @classmethod
    def list_supported_integrations(cls) -> list[str]:
        """
        List all supported integrations.

        Returns:
            List of integration identifiers
        """
        return list(cls._handlers.keys())

    @classmethod
    def reset(cls) -> None:
        """
        Reset the handler registry.

        Clears all registered handlers. Useful for testing to ensure
        clean state between test cases.
        """
        cls._handlers = {}


# =============================================================================
# Utility Functions
# =============================================================================


def create_handler_for_webhook(
    webhook_config: WebhookConfig,
    spec_dir: Path,
    project_dir: Path | None = None,
) -> IncomingWebhookHandler | None:
    """
    Create a handler instance for a webhook configuration.

    Factory function that creates the appropriate handler based on
    the webhook's integration type.

    Args:
        webhook_config: Webhook configuration
        spec_dir: Spec directory
        project_dir: Project directory (optional)

    Returns:
        Handler instance or None if integration not supported

    Examples:
        >>> handler = create_handler_for_webhook(
        ...     webhook_config,
        ...     spec_dir=Path("/path/to/spec"),
        ... )
        >>> result = handler.handle_webhook(webhook_config, payload)
    """
    integration = webhook_config.integration.value
    return HandlerRegistry.get_handler(integration, spec_dir, project_dir)


# =============================================================================
# Handler Registration
# =============================================================================


# Register built-in handlers
HandlerRegistry.register("github", GitHubWebhookHandler)
HandlerRegistry.register("generic", GenericWebhookHandler)
