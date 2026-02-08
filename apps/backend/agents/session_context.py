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

        Also extracts and saves code references as a separate episode for
        efficient querying.

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

            # Extract and save code references as separate episode for efficient querying
            code_refs = round_data.get("code_references", [])
            if code_refs:
                await self.save_code_reference_episode(
                    session_id=session_id,
                    round_number=round_num,
                    code_references=set(code_refs),
                )

            debug(
                "session_context",
                f"Saved conversation round {round_num} to Graphiti",
                session_id=session_id,
                code_refs=len(code_refs),
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

            # Search for relevant rounds (cast wider net for sorting/filtering)
            results = await search.search_episodes(
                query=query,
                episode_type=EPISODE_TYPE_CONVERSATION_ROUND,
                num_results=(max_recent_rounds + max_relevant_rounds) * 2,
            )

            if not results:
                debug_warning(
                    "session_context",
                    "No conversation rounds found in Graphiti",
                )
                return None

            # Context window optimization: recent + relevant strategy
            optimized_rounds = self._optimize_context_window(
                results=results,
                max_recent_rounds=max_recent_rounds,
                max_relevant_rounds=max_relevant_rounds,
                min_relevance_score=min_relevance_score,
            )

            # Extract code references from optimized rounds
            code_references = self._extract_code_references_from_rounds(
                optimized_rounds["recent_rounds"] + optimized_rounds["relevant_rounds"]
            )

            debug_success(
                "session_context",
                f"Optimized context window: {optimized_rounds['total_recent']} recent + "
                f"{optimized_rounds['total_relevant']} relevant rounds",
                code_refs=len(code_references),
            )

            return {
                "recent_rounds": optimized_rounds["recent_rounds"],
                "relevant_rounds": optimized_rounds["relevant_rounds"],
                "code_references": code_references,
                "total_recent": optimized_rounds["total_recent"],
                "total_relevant": optimized_rounds["total_relevant"],
                "total_rounds": optimized_rounds["total_recent"]
                + optimized_rounds["total_relevant"],
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

    async def get_code_references(
        self,
        session_id: str | None = None,
        file_path: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get code references from Graphiti.

        Args:
            session_id: Optional session ID to filter by
            file_path: Optional file path to filter by

        Returns:
            List of code reference dictionaries
        """
        if not await self.initialize():
            return []

        try:
            from integrations.graphiti.queries_pkg.search import GraphitiSearch

            search = GraphitiSearch(
                self._graphiti_memory.client,
                self._graphiti_memory.group_id,
                self._graphiti_memory.spec_context_id,
                self._graphiti_memory.group_id_mode,
                self.project_dir,
            )

            # Build query based on filters
            query_parts = ["code references"]
            if session_id:
                query_parts.append(f"session {session_id}")
            if file_path:
                query_parts.append(f"file {file_path}")

            query = " ".join(query_parts)

            # Search for code reference episodes
            results = await search.search_episodes(
                query=query,
                episode_type=EPISODE_TYPE_CODE_REFERENCE,
                num_results=100,
            )

            debug(
                "session_context",
                f"Retrieved {len(results)} code references from Graphiti",
                session_id=session_id,
                file_path=file_path,
            )

            return results

        except Exception as e:
            debug_error(
                "session_context",
                f"Failed to get code references: {e}",
            )
            logger.warning(f"Failed to get code references: {e}")
            return []

    async def get_sessions_for_file(
        self,
        file_path: str,
    ) -> list[dict[str, Any]]:
        """
        Get all sessions that referenced a specific file.

        Args:
            file_path: File path to search for

        Returns:
            List of session context summaries that reference this file
        """
        if not await self.initialize():
            return []

        try:
            from integrations.graphiti.queries_pkg.search import GraphitiSearch

            search = GraphitiSearch(
                self._graphiti_memory.client,
                self._graphiti_memory.group_id,
                self._graphiti_memory.spec_context_id,
                self._graphiti_memory.group_id_mode,
                self.project_dir,
            )

            # Search for session contexts that mention this file
            query = f"sessions that modified or referenced {file_path}"

            results = await search.search_episodes(
                query=query,
                episode_type=EPISODE_TYPE_SESSION_CONTEXT,
                num_results=50,
            )

            # Filter results to only those that actually reference this file
            filtered_results = []
            for result in results:
                try:
                    episode_data = json.loads(result.get("episode_body", "{}"))
                    code_refs = episode_data.get("code_references", [])
                    if file_path in code_refs:
                        filtered_results.append(result)
                except (json.JSONDecodeError, KeyError):
                    continue

            debug(
                "session_context",
                f"Found {len(filtered_results)} sessions referencing {file_path}",
            )

            return filtered_results

        except Exception as e:
            debug_error(
                "session_context",
                f"Failed to get sessions for file: {e}",
            )
            logger.warning(f"Failed to get sessions for file: {e}")
            return []

    async def get_all_code_references_for_session(
        self,
        session_id: str,
    ) -> set[str]:
        """
        Get all unique code references for a session from conversation rounds.

        Args:
            session_id: Session identifier

        Returns:
            Set of unique file paths referenced in this session
        """
        if not await self.initialize():
            return set()

        try:
            from integrations.graphiti.queries_pkg.search import GraphitiSearch

            search = GraphitiSearch(
                self._graphiti_memory.client,
                self._graphiti_memory.group_id,
                self._graphiti_memory.spec_context_id,
                self._graphiti_memory.group_id_mode,
                self.project_dir,
            )

            # Search for all conversation rounds in this session
            query = f"conversation rounds for session {session_id}"

            results = await search.search_episodes(
                query=query,
                episode_type=EPISODE_TYPE_CONVERSATION_ROUND,
                num_results=1000,  # Get all rounds
            )

            # Extract code references from all rounds
            all_code_refs = set()
            for result in results:
                try:
                    episode_data = json.loads(result.get("episode_body", "{}"))
                    round_data = episode_data.get("round_data", {})
                    code_refs = round_data.get("code_references", [])
                    all_code_refs.update(code_refs)
                except (json.JSONDecodeError, KeyError):
                    continue

            debug(
                "session_context",
                f"Retrieved {len(all_code_refs)} unique code references for session {session_id}",
            )

            return all_code_refs

        except Exception as e:
            debug_error(
                "session_context",
                f"Failed to get code references for session: {e}",
            )
            logger.warning(f"Failed to get code references for session: {e}")
            return set()

    async def save_code_reference_episode(
        self,
        session_id: str,
        round_number: int,
        code_references: set[str],
    ) -> bool:
        """
        Save code references from a specific round as a dedicated episode.

        This enables efficient querying of code references without loading full rounds.

        Args:
            session_id: Session identifier
            round_number: Round number
            code_references: Set of file paths referenced

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
                "round_number": round_number,
                "spec_id": self._graphiti_memory.spec_context_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "references": list(code_references),
            }

            episode_name = f"code_refs_{session_id}_round_{round_number:03d}"

            await self._graphiti_memory.client.graphiti.add_episode(
                name=episode_name,
                episode_body=json.dumps(episode_content),
                source=EpisodeType.text,
                source_description=f"Code references from round {round_number} of session {session_id}",
                reference_time=datetime.now(UTC),
                group_id=self._graphiti_memory.group_id,
            )

            debug(
                "session_context",
                f"Saved {len(code_references)} code references from round {round_number}",
                session_id=session_id,
            )
            return True

        except Exception as e:
            debug_error(
                "session_context",
                f"Failed to save code reference episode: {e}",
            )
            logger.warning(f"Failed to save code reference episode: {e}")
            return False

    def _optimize_context_window(
        self,
        results: list[dict[str, Any]],
        max_recent_rounds: int,
        max_relevant_rounds: int,
        min_relevance_score: float,
    ) -> dict[str, Any]:
        """
        Optimize context window using recent + relevant strategy.

        Strategy:
        1. Sort all rounds by timestamp to get most recent
        2. Take top N recent rounds (for continuity)
        3. Filter remaining rounds by relevance score
        4. Take top M relevant rounds (for context depth)
        5. Remove duplicates between recent and relevant sets

        Args:
            results: Raw search results from Graphiti
            max_recent_rounds: Max recent rounds to include
            max_relevant_rounds: Max relevant rounds to include
            min_relevance_score: Minimum relevance score threshold

        Returns:
            Dict with recent_rounds, relevant_rounds, and counts
        """
        if not results:
            return {
                "recent_rounds": [],
                "relevant_rounds": [],
                "total_recent": 0,
                "total_relevant": 0,
            }

        # Parse episode data and extract timestamps
        parsed_results = []
        for result in results:
            try:
                episode_data = json.loads(result.get("episode_body", "{}"))
                timestamp_str = episode_data.get("timestamp")
                relevance_score = result.get("score", 0.0)

                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    parsed_results.append(
                        {
                            "result": result,
                            "episode_data": episode_data,
                            "timestamp": timestamp,
                            "relevance_score": relevance_score,
                        }
                    )
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                debug_warning(
                    "session_context",
                    f"Failed to parse episode data: {e}",
                )
                continue

        if not parsed_results:
            return {
                "recent_rounds": [],
                "relevant_rounds": [],
                "total_recent": 0,
                "total_relevant": 0,
            }

        # Sort by timestamp (most recent first)
        parsed_results.sort(key=lambda x: x["timestamp"], reverse=True)

        # Get recent rounds (most recent N)
        recent_rounds_data = parsed_results[:max_recent_rounds]
        recent_rounds = [r["result"] for r in recent_rounds_data]
        recent_round_ids = {r["result"].get("episode_id") for r in recent_rounds_data}

        # Get relevant rounds from remaining results
        # Filter by relevance score and exclude those already in recent
        relevant_candidates = [
            r
            for r in parsed_results
            if r["result"].get("episode_id") not in recent_round_ids
            and r["relevance_score"] >= min_relevance_score
        ]

        # Sort by relevance score (highest first)
        relevant_candidates.sort(key=lambda x: x["relevance_score"], reverse=True)

        # Take top M relevant rounds
        relevant_rounds = [r["result"] for r in relevant_candidates[:max_relevant_rounds]]

        debug(
            "session_context",
            "Context window optimization complete",
            total_results=len(results),
            recent_rounds=len(recent_rounds),
            relevant_rounds=len(relevant_rounds),
            min_score=min_relevance_score,
        )

        return {
            "recent_rounds": recent_rounds,
            "relevant_rounds": relevant_rounds,
            "total_recent": len(recent_rounds),
            "total_relevant": len(relevant_rounds),
        }

    def _extract_code_references_from_rounds(
        self,
        rounds: list[dict[str, Any]],
    ) -> list[str]:
        """
        Extract unique code references from conversation rounds.

        Args:
            rounds: List of conversation round results

        Returns:
            Sorted list of unique file paths
        """
        code_refs = set()

        for round_data in rounds:
            try:
                episode_data = json.loads(round_data.get("episode_body", "{}"))
                round_info = episode_data.get("round_data", {})
                refs = round_info.get("code_references", [])
                code_refs.update(refs)
            except (json.JSONDecodeError, KeyError) as e:
                debug_warning(
                    "session_context",
                    f"Failed to extract code references: {e}",
                )
                continue

        # Return sorted list for consistency
        return sorted(code_refs)

    async def close(self) -> None:
        """Close Graphiti connection."""
        if self._graphiti_memory:
            await self._graphiti_memory.close()
            self._graphiti_memory = None
            self._initialized = False
