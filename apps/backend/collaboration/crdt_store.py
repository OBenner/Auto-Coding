"""
CRDT Store for Spec Content
===========================

Conflict-free Replicated Data Type (CRDT) implementation for real-time
collaborative spec editing. Supports offline editing with automatic merge.

Uses an operation-based CRDT with character-wise tracking for markdown text.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass


class OpType(str, Enum):
    """Type of CRDT operation."""

    INSERT = "insert"
    DELETE = "delete"


class CrdtOperation:
    """A single CRDT operation for tracking text changes.

    Operations form a directed acyclic graph (DAG) based on dependencies.
    Each operation has a unique ID and references previous operations.
    """

    def __init__(
        self,
        op_type: OpType,
        content: str,
        position: int,
        author: str,
        author_name: str,
        timestamp: datetime | None = None,
        op_id: str | None = None,
        parent_id: str | None = None,
    ):
        """Initialize a CRDT operation.

        Args:
            op_type: Type of operation (insert or delete)
            content: Text content being inserted (empty for delete)
            position: Position in the document for this operation
            author: Author identifier
            author_name: Display name of author
            timestamp: Operation timestamp (defaults to now)
            op_id: Unique operation ID (auto-generated if None)
            parent_id: ID of the parent operation this depends on
        """
        self.op_type = op_type
        self.content = content
        self.position = position
        self.author = author
        self.author_name = author_name
        self.timestamp = timestamp or datetime.utcnow()
        self.op_id = op_id or str(uuid.uuid4())
        self.parent_id = parent_id

    def to_dict(self) -> dict:
        """Convert operation to dictionary.

        Returns:
            Dictionary representation of the operation
        """
        return {
            "op_type": self.op_type.value,
            "content": self.content,
            "position": self.position,
            "author": self.author,
            "author_name": self.author_name,
            "timestamp": self.timestamp.isoformat(),
            "op_id": self.op_id,
            "parent_id": self.parent_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CrdtOperation:
        """Create operation from dictionary.

        Args:
            data: Dictionary representation of an operation

        Returns:
            CrdtOperation instance
        """
        if isinstance(data.get("op_type"), str):
            data["op_type"] = OpType(data["op_type"])

        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        # Extract fields that match __init__ signature
        return cls(
            op_type=data["op_type"],
            content=data["content"],
            position=data["position"],
            author=data["author"],
            author_name=data["author_name"],
            timestamp=data.get("timestamp"),
            op_id=data.get("op_id"),
            parent_id=data.get("parent_id"),
        )

    def __repr__(self) -> str:
        return (
            f"CrdtOperation({self.op_type.value}, "
            f"pos={self.position}, len={len(self.content)}, "
            f"author={self.author})"
        )


class CRDTStore:
    """CRDT store for collaborative spec editing.

    Tracks all operations and provides methods for applying new operations
    while maintaining consistency across multiple concurrent editors.

    Operations are persisted to disk and can be loaded to restore state.
    """

    def __init__(self, spec_id: str | None = None, spec_dir: Path | None = None):
        """Initialize the CRDT store.

        Args:
            spec_id: Optional spec identifier
            spec_dir: Optional directory for persistence
        """
        self.spec_id = spec_id or ""
        self.spec_dir = spec_dir
        self.operations: list[CrdtOperation] = []
        self.current_state = ""
        self._known_heads: set[str] = set()  # Tracks operation DAG leaf nodes

    def load_from_file(self, spec_dir: Path) -> bool:
        """Load CRDT state from disk.

        Args:
            spec_dir: Path to the spec directory

        Returns:
            True if load was successful, False otherwise
        """
        self.spec_dir = spec_dir
        crdt_file = spec_dir / "collaboration" / "crdt.json"

        if not crdt_file.exists():
            logger.debug("No CRDT state file found at %s", crdt_file)
            # Try to load from spec.md as initial state
            spec_file = spec_dir / "spec.md"
            if spec_file.exists():
                try:
                    with open(spec_file, encoding="utf-8") as f:
                        self.current_state = f.read()
                    logger.debug(
                        "Loaded initial state from spec.md: %d chars",
                        len(self.current_state),
                    )
                    return True
                except OSError as e:
                    logger.warning("Failed to load spec.md: %s", e)
            return False

        try:
            with open(crdt_file, encoding="utf-8") as f:
                data = json.load(f)

            # Load metadata
            self.spec_id = data.get("spec_id", "")
            self.current_state = data.get("current_state", "")

            # Load operations
            ops_data = data.get("operations", [])
            self.operations = [CrdtOperation.from_dict(op) for op in ops_data]

            # Rebuild head tracking
            self._rebuild_heads()

            logger.info(
                "Loaded CRDT state: %d operations, %d chars",
                len(self.operations),
                len(self.current_state),
            )
            return True

        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.error("Failed to load CRDT state from %s: %s", crdt_file, e)
            return False

    def save_to_file(self, spec_dir: Path | None = None) -> bool:
        """Save CRDT state to disk.

        Args:
            spec_dir: Path to the spec directory (uses self.spec_dir if None)

        Returns:
            True if save was successful, False otherwise
        """
        target_dir = spec_dir or self.spec_dir
        if not target_dir:
            logger.warning("No spec directory specified for saving CRDT state")
            return False

        collaboration_dir = target_dir / "collaboration"
        collaboration_dir.mkdir(parents=True, exist_ok=True)

        crdt_file = collaboration_dir / "crdt.json"

        try:
            data = {
                "spec_id": self.spec_id,
                "current_state": self.current_state,
                "operations": [op.to_dict() for op in self.operations],
                "updated_at": datetime.utcnow().isoformat(),
            }

            with open(crdt_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug("Saved CRDT state: %d operations", len(self.operations))
            return True

        except OSError as e:
            logger.error("Failed to save CRDT state to %s: %s", crdt_file, e)
            return False

    def get_content(self) -> str:
        """Get the current document content.

        Returns:
            Current document state as text
        """
        return self.current_state

    def set_initial_content(self, content: str) -> None:
        """Set initial content (used when creating new spec).

        Args:
            content: Initial document content
        """
        self.current_state = content
        self.operations = []
        self._known_heads = set()

    def insert(
        self,
        content: str,
        position: int,
        author: str,
        author_name: str,
        parent_id: str | None = None,
    ) -> CrdtOperation:
        """Create and apply an insert operation.

        Args:
            content: Text to insert
            position: Position to insert at
            author: Author identifier
            author_name: Display name of author
            parent_id: Optional parent operation ID for ordering

        Returns:
            The created CrdtOperation
        """
        # Validate position
        if position < 0 or position > len(self.current_state):
            position = len(self.current_state)

        # Create operation
        op = CrdtOperation(
            op_type=OpType.INSERT,
            content=content,
            position=position,
            author=author,
            author_name=author_name,
            timestamp=datetime.utcnow(),
            parent_id=parent_id or self._get_latest_head(),
        )

        # Apply operation
        self._apply_operation(op)
        self.operations.append(op)
        self._update_heads(op.op_id, op.parent_id)

        return op

    def delete(
        self,
        position: int,
        length: int,
        author: str,
        author_name: str,
        parent_id: str | None = None,
    ) -> CrdtOperation:
        """Create and apply a delete operation.

        Args:
            position: Position to start deleting
            length: Number of characters to delete
            author: Author identifier
            author_name: Display name of author
            parent_id: Optional parent operation ID for ordering

        Returns:
            The created CrdtOperation
        """
        # Validate position and length
        if position < 0:
            position = 0
        if position > len(self.current_state):
            position = len(self.current_state)
        if position + length > len(self.current_state):
            length = len(self.current_state) - position

        # Extract deleted content for tracking
        deleted_content = self.current_state[position : position + length]

        # Create operation
        op = CrdtOperation(
            op_type=OpType.DELETE,
            content=deleted_content,
            position=position,
            author=author,
            author_name=author_name,
            timestamp=datetime.utcnow(),
            parent_id=parent_id or self._get_latest_head(),
        )

        # Apply operation
        self._apply_operation(op)
        self.operations.append(op)
        self._update_heads(op.op_id, op.parent_id)

        return op

    def apply_remote_operation(self, op_data: dict) -> bool:
        """Apply an operation received from a remote client.

        Args:
            op_data: Dictionary representation of the operation

        Returns:
            True if operation was applied successfully
        """
        # Check if we already have this operation
        op_id = op_data.get("op_id")
        if any(op.op_id == op_id for op in self.operations):
            logger.debug("Operation %s already applied, skipping", op_id)
            return False

        try:
            # Create operation from data
            op = CrdtOperation.from_dict(op_data)

            # Apply operation
            self._apply_operation(op)
            self.operations.append(op)
            self._update_heads(op.op_id, op.parent_id)

            logger.debug("Applied remote operation %s from %s", op.op_id, op.author)
            return True

        except (KeyError, ValueError) as e:
            logger.error("Failed to apply remote operation: %s", e)
            return False

    def get_operations_since(self, timestamp: datetime) -> list[dict]:
        """Get all operations since a given timestamp.

        Used for syncing changes to clients that were offline.

        Args:
            timestamp: Timestamp to filter operations

        Returns:
            List of operation dictionaries
        """
        return [
            op.to_dict()
            for op in self.operations
            if op.timestamp > timestamp
        ]

    def get_missing_operations(self, known_op_ids: set[str]) -> list[dict]:
        """Get operations that the client doesn't have yet.

        Args:
            known_op_ids: Set of operation IDs the client already knows

        Returns:
            List of missing operation dictionaries
        """
        return [
            op.to_dict()
            for op in self.operations
            if op.op_id not in known_op_ids
        ]

    def _apply_operation(self, op: CrdtOperation) -> None:
        """Apply a single operation to the current state.

        Args:
            op: Operation to apply
        """
        if op.op_type == OpType.INSERT:
            # Insert content at position
            if op.position < 0:
                pos = 0
            elif op.position > len(self.current_state):
                pos = len(self.current_state)
            else:
                pos = op.position

            self.current_state = (
                self.current_state[:pos] + op.content + self.current_state[pos:]
            )

        elif op.op_type == OpType.DELETE:
            # Delete content at position
            if op.position < 0:
                pos = 0
            elif op.position > len(self.current_state):
                pos = len(self.current_state)
            else:
                pos = op.position

            end_pos = min(pos + len(op.content), len(self.current_state))
            self.current_state = self.current_state[:pos] + self.current_state[end_pos:]

    def _get_latest_head(self) -> str | None:
        """Get the latest head operation ID.

        Returns:
            Most recent head operation ID, or None if no operations
        """
        if not self._known_heads:
            return None

        # Return the head with the latest timestamp
        head_ops = [
            op for op in self.operations if op.op_id in self._known_heads
        ]
        if not head_ops:
            return None

        latest = max(head_ops, key=lambda op: op.timestamp)
        return latest.op_id

    def _update_heads(self, new_op_id: str, parent_id: str | None) -> None:
        """Update the set of head operations after adding a new operation.

        Args:
            new_op_id: ID of the newly added operation
            parent_id: ID of the parent operation
        """
        # Add new operation as a head
        self._known_heads.add(new_op_id)

        # Remove parent from heads (it's no longer a leaf)
        if parent_id and parent_id in self._known_heads:
            self._known_heads.remove(parent_id)

    def _rebuild_heads(self) -> None:
        """Rebuild the set of head operations from loaded operations."""
        if not self.operations:
            self._known_heads = set()
            return

        # All operation IDs
        all_ids = {op.op_id for op in self.operations}

        # All parent IDs (that are also operations)
        parent_ids = {
            op.parent_id for op in self.operations if op.parent_id and op.parent_id in all_ids
        }

        # Heads are operations that are not parents of any other operation
        self._known_heads = all_ids - parent_ids

    def get_operation_history(self) -> list[dict]:
        """Get the complete operation history.

        Returns:
            List of all operation dictionaries in order
        """
        return [op.to_dict() for op in self.operations]

    def get_stats(self) -> dict:
        """Get statistics about the CRDT store.

        Returns:
            Dictionary with stats
        """
        return {
            "spec_id": self.spec_id,
            "operation_count": len(self.operations),
            "content_length": len(self.current_state),
            "head_count": len(self._known_heads),
            "last_operation_time": (
                self.operations[-1].timestamp.isoformat()
                if self.operations
                else None
            ),
        }
