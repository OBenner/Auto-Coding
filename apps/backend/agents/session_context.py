"""
Session Context Storage Schema for Graphiti
============================================

Manages persistent storage of conversation history, code references, and
session context in Graphiti memory system. Enables:
- Full session context persistence across restarts
- Context window optimization (recent + relevant)
- Long-running session stability (4+ hours)
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.sentry import capture_exception
from debug import debug, debug_error, debug_success, debug_warning

logger = logging.getLogger(__name__)

# ============================================================================
# Episode Type Constants (extend schema.py)
# ============================================================================

EPISODE_TYPE_CONVERSATION_ROUND = "conversation_round"
EPISODE_TYPE_CODE_REFERENCE = "code_reference"
EPISODE_TYPE_SESSION_CONTEXT = "session_context"

# Context window optimization settings
DEFAULT_MAX_RECENT_ROUNDS = 20  # Always include last N rounds
DEFAULT_MAX_RELEVANT_ROUNDS = 10  # Add top N relevant rounds from history
DEFAULT_MIN_RELEVANCE_SCORE = 0.6  # Minimum score for relevance


# ============================================================================
# Session Context Manager
# ============================================================================


class SessionContext:
    """
    Manages session context storage and retrieval in Graphiti.

    This class bridges the ConversationHistory from session.py with Graphiti
    persistent storage, enabling:
    - Session persistence across restarts
    - Context window optimization
    - Long-running session support
    """

    def __init__(
        self,
        spec_dir: Path,
        project_dir: Path,
        graphiti_memory=None,
    ):
        """
        Initialize session context manager.

        Args:
            spec_dir: Spec directory
            project_dir: Project root directory
            graphiti_memory: Optional GraphitiMemory instance (lazy init if None)
        """
        self.spec_dir = spec_dir
        self.project_dir = project_dir
        self._graphiti_memory = graphiti_memory
        self._initialized = False

    async def initialize(self) -> bool:
        """
        Initialize Graphiti connection.

        Returns:
            True if initialization succeeded
        """
        if self._initialized:
            return True

        if self._graphiti_memory is None:
            # Lazy load GraphitiMemory
            try:
                from memory.graphiti_helpers import get_graphiti_memory

                self._graphiti_memory = await get_graphiti_memory(
                    self.spec_dir, self.project_dir
                )
            except Exception as e:
                debug_error(
                    "session_context",
                    f"Failed to initialize Graphiti memory: {e}",
                )
                logger.warning(f"Failed to initialize Graphiti memory: {e}")
                return False

        if self._graphiti_memory is None:
            debug_warning(
                "session_context",
                "Graphiti memory not available - session persistence disabled",
            )
            return False

        # Ensure Graphiti is initialized
        if not self._graphiti_memory.is_initialized:
            try:
                await self._graphiti_memory.initialize()
            except Exception as e:
                debug_error(
                    "session_context",
                    f"Failed to initialize Graphiti: {e}",
                )
                logger.warning(f"Failed to initialize Graphiti: {e}")
                return False

        self._initialized = self._graphiti_memory.is_initialized
        return self._initialized

    async def save_conversation_round(
        self,
        session_id: str,
        round_data: dict[str, Any],
        subtask_id: str | None = None,
    ) -> bool:
        """
        Save a single conversation round to Graphiti.

        Args:
            session_id: Unique session identifier
            round_data: Conversation round dictionary (from ConversationRound.to_dict())
            subtask_id: Optional subtask identifier

        Returns:
            True if saved successfully
        """
        if not await self.initialize():
            debug_warning(
                "session_context",
                "Graphiti not initialized - skipping conversation round save",
            )
            return False

        try:
            from graphiti_core.nodes import EpisodeType

            episode_content = {
                "type": EPISODE_TYPE_CONVERSATION_ROUND,
                "session_id": session_id,
                "subtask_id": subtask_id,
                "spec_id": self._graphiti_memory.spec_context_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "round_data": round_data,
            }

            round_num = round_data.get("round_number", 0)
            episode_name = f"conversation_{session_id}_round_{round_num:03d}"

            await self._graphiti_memory.client.graphiti.add_episode(
                name=episode_name,
                episode_body=json.dumps(episode_content),
                source=EpisodeType.text,
                source_description=f"Conversation round {round_num} for session {session_id}",
                reference_time=datetime.now(UTC),
                group_id=self._graphiti_memory.group_id,
            )

            debug(
                "session_context",
                f"Saved conversation round {round_num} to Graphiti",
                session_id=session_id,
            )
            return True

        except Exception as e:
            debug_error(
                "session_context",
                f"Failed to save conversation round: {e}",
            )
            logger.warning(f"Failed to save conversation round: {e}")
            capture_exception(
                e,
                operation="save_conversation_round",
                session_id=session_id,
            )
            return False

    async def save_conversation_history(
        self,
        conversation_history,
    ) -> bool:
        """
        Save complete conversation history to Graphiti.

        Args:
            conversation_history: ConversationHistory instance from session.py

        Returns:
            True if all rounds saved successfully
        """
        if not await self.initialize():
            debug_warning(
                "session_context",
                "Graphiti not initialized - skipping conversation history save",
            )
            return False

        try:
            # Save each round as a separate episode for granular retrieval
            success_count = 0
            for round_obj in conversation_history.rounds:
                if await self.save_conversation_round(
                    session_id=conversation_history.session_id,
                    round_data=round_obj.to_dict(),
                    subtask_id=conversation_history.subtask_id,
                ):
                    success_count += 1

            # Save overall session context summary
            await self._save_session_context_summary(conversation_history)

            debug_success(
                "session_context",
                f"Saved conversation history: {success_count}/{len(conversation_history.rounds)} rounds",
                session_id=conversation_history.session_id,
            )
            return success_count == len(conversation_history.rounds)

        except Exception as e:
            debug_error(
                "session_context",
                f"Failed to save conversation history: {e}",
            )
            logger.warning(f"Failed to save conversation history: {e}")
            capture_exception(
                e,
                operation="save_conversation_history",
                session_id=conversation_history.session_id,
            )
            return False

    async def _save_session_context_summary(
        self,
        conversation_history,
    ) -> bool:
        """
        Save session context summary to Graphiti.

        This creates a high-level episode with session metadata for quick lookups.

        Args:
            conversation_history: ConversationHistory instance

        Returns:
            True if saved successfully
        """
        try:
            from graphiti_core.nodes import EpisodeType

            input_tokens, output_tokens = conversation_history.get_total_tokens()
            all_code_refs = list(conversation_history.get_all_code_references())

            episode_content = {
                "type": EPISODE_TYPE_SESSION_CONTEXT,
                "session_id": conversation_history.session_id,
                "subtask_id": conversation_history.subtask_id,
                "spec_id": self._graphiti_memory.spec_context_id,
                "session_start": conversation_history.session_start.isoformat(),
                "total_rounds": len(conversation_history.rounds),
                "total_input_tokens": input_tokens,
                "total_output_tokens": output_tokens,
                "code_references": all_code_refs,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            episode_name = f"session_context_{conversation_history.session_id}"

            await self._graphiti_memory.client.graphiti.add_episode(
                name=episode_name,
                episode_body=json.dumps(episode_content),
                source=EpisodeType.text,
                source_description=f"Session context summary for {conversation_history.session_id}",
                reference_time=datetime.now(UTC),
                group_id=self._graphiti_memory.group_id,
            )

            debug(
                "session_context",
                "Saved session context summary",
                session_id=conversation_history.session_id,
                rounds=len(conversation_history.rounds),
                code_refs=len(all_code_refs),
            )
            return True

        except Exception as e:
            debug_error(
                "session_context",
                f"Failed to save session context summary: {e}",
            )
            logger.warning(f"Failed to save session context summary: {e}")
            return False

    async def save_code_references(
        self,
        session_id: str,
        code_references: set[str],
        context: str = "",
    ) -> bool:
        """
        Save code references to Graphiti.

        Args:
            session_id: Unique session identifier
            code_references: Set of file paths referenced
            context: Optional context description

        Returns:
            True if saved successfully
        """
        if not await self.initialize():
            return False

        if not code_references:
            return True  # Nothing to save

        try:
            from graphiti_core.nodes import EpisodeType

            episode_content = {
                "type": EPISODE_TYPE_CODE_REFERENCE,
                "session_id": session_id,
                "spec_id": self._graphiti_memory.spec_context_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "references": list(code_references),
                "context": context,
            }

            episode_name = (
                f"code_refs_{session_id}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
            )

            await self._graphiti_memory.client.graphiti.add_episode(
                name=episode_name,
                episode_body=json.dumps(episode_content),
                source=EpisodeType.text,
                source_description=f"Code references for session {session_id}",
                reference_time=datetime.now(UTC),
                group_id=self._graphiti_memory.group_id,
            )

            debug(
                "session_context",
                f"Saved {len(code_references)} code references to Graphiti",
                session_id=session_id,
            )
            return True

        except Exception as e:
            debug_error(
                "session_context",
                f"Failed to save code references: {e}",
            )
            logger.warning(f"Failed to save code references: {e}")
            capture_exception(
                e,
                operation="save_code_references",
                session_id=session_id,
            )
            return False

    async def get_optimized_context(
        self,
        query: str,
        max_recent_rounds: int = DEFAULT_MAX_RECENT_ROUNDS,
        max_relevant_rounds: int = DEFAULT_MAX_RELEVANT_ROUNDS,
        min_relevance_score: float = DEFAULT_MIN_RELEVANCE_SCORE,
    ) -> dict[str, Any] | None:
        """
        Get optimized session context for current task.

        This implements context window optimization by combining:
        - Most recent N conversation rounds (for continuity)
        - Top M relevant rounds from history (for context)

        Args:
            query: Current task/query for relevance matching
            max_recent_rounds: Max recent rounds to include
            max_relevant_rounds: Max relevant rounds to include
            min_relevance_score: Minimum relevance score (0.0-1.0)

        Returns:
            Dict with optimized context or None if unavailable
        """
        if not await self.initialize():
            return None

        try:
            # Use Graphiti search to find relevant conversation rounds
            from integrations.graphiti.queries_pkg.search import GraphitiSearch

            search = GraphitiSearch(
                self._graphiti_memory.client,
                self._graphiti_memory.group_id,
                self._graphiti_memory.spec_context_id,
                self._graphiti_memory.group_id_mode,
                self.project_dir,
            )

            # Search for relevant rounds
            results = await search.search_episodes(
                query=query,
                episode_type=EPISODE_TYPE_CONVERSATION_ROUND,
                num_results=max_recent_rounds + max_relevant_rounds,
            )

            if not results:
                debug_warning(
                    "session_context",
                    "No conversation rounds found in Graphiti",
                )
                return None

            # TODO: Implement context window optimization logic
            # For now, return raw results
            debug_success(
                "session_context",
                f"Retrieved {len(results)} conversation rounds from Graphiti",
            )

            return {
                "rounds": results,
                "total_rounds": len(results),
                "query": query,
            }

        except Exception as e:
            debug_error(
                "session_context",
                f"Failed to get optimized context: {e}",
            )
            logger.warning(f"Failed to get optimized context: {e}")
            capture_exception(
                e,
                operation="get_optimized_context",
                query=query[:100],
            )
            return None

    async def close(self) -> None:
        """Close Graphiti connection."""
        if self._graphiti_memory:
            await self._graphiti_memory.close()
            self._graphiti_memory = None
            self._initialized = False
