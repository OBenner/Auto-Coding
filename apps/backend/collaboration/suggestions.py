"""
Suggestion System for Collaborative Spec Editing
==============================================

Manager for suggested changes to spec content.
Provides CRUD operations, review workflow, and status management.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from collaboration.models import Suggestion, SuggestionStatus, load_suggestions, save_suggestions

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass


class SuggestionManager:
    """Manager for spec suggestions with review workflow.

    Provides a high-level interface for managing suggested changes
    to specifications. Suggestions can be proposed, reviewed, accepted,
    or rejected with comments from reviewers.
    """

    def __init__(self, spec_dir: Path):
        """Initialize the suggestion manager.

        Args:
            spec_dir: Path to the spec directory
        """
        self.spec_dir = spec_dir
        self._suggestions_cache: list[Suggestion] | None = None

    def load_suggestions(self) -> list[Suggestion]:
        """Load suggestions from disk.

        Returns:
            List of all suggestions for this spec
        """
        if self._suggestions_cache is None:
            self._suggestions_cache = load_suggestions(self.spec_dir)
            logger.debug(
                "Loaded %d suggestions from %s",
                len(self._suggestions_cache),
                self.spec_dir,
            )
        return self._suggestions_cache

    def save_suggestions(self, suggestions: list[Suggestion] | None = None) -> bool:
        """Save suggestions to disk.

        Args:
            suggestions: Optional list of suggestions (uses cache if None)

        Returns:
            True if save was successful
        """
        suggestions_to_save = suggestions if suggestions is not None else self._suggestions_cache
        if suggestions_to_save is None:
            logger.warning("No suggestions to save")
            return False

        try:
            save_suggestions(self.spec_dir, suggestions_to_save)
            self._suggestions_cache = suggestions_to_save
            logger.debug(
                "Saved %d suggestions to %s",
                len(suggestions_to_save),
                self.spec_dir,
            )
            return True
        except Exception as e:
            logger.error("Failed to save suggestions: %s", e)
            return False

    def add_suggestion(
        self,
        author: str,
        author_name: str,
        original_text: str,
        suggested_text: str,
        section_id: str | None = None,
        reason: str | None = None,
    ) -> Suggestion | None:
        """Add a new suggestion.

        Args:
            author: Author identifier
            author_name: Display name of author
            original_text: Original text to be replaced
            suggested_text: Proposed replacement text
            section_id: Optional section this suggestion references
            reason: Optional explanation for the change

        Returns:
            Created suggestion or None if creation failed
        """
        if not suggested_text or not suggested_text.strip():
            logger.warning("Cannot add suggestion with empty suggested_text")
            return None

        if not original_text or not original_text.strip():
            logger.warning("Cannot add suggestion with empty original_text")
            return None

        suggestions = self.load_suggestions()

        # Create new suggestion
        suggestion = Suggestion(
            id=str(uuid.uuid4()),
            spec_id=self.spec_dir.name,
            section_id=section_id,
            author=author,
            author_name=author_name,
            original_text=original_text.strip(),
            suggested_text=suggested_text.strip(),
            reason=reason.strip() if reason else None,
            status=SuggestionStatus.PENDING,
            created_at=datetime.utcnow(),
        )

        suggestions.append(suggestion)

        if self.save_suggestions(suggestions):
            logger.info(
                "Added suggestion %s by %s to spec %s",
                suggestion.id,
                author,
                self.spec_dir.name,
            )
            return suggestion

        return None

    def get_suggestion(self, suggestion_id: str) -> Suggestion | None:
        """Get a specific suggestion by ID.

        Args:
            suggestion_id: Suggestion identifier

        Returns:
            Suggestion or None if not found
        """
        suggestions = self.load_suggestions()
        for suggestion in suggestions:
            if suggestion.id == suggestion_id:
                return suggestion
        return None

    def get_suggestions_for_spec(
        self,
        status: SuggestionStatus | None = None,
    ) -> list[Suggestion]:
        """Get all suggestions for this spec.

        Args:
            status: Optional status filter

        Returns:
            List of suggestions matching criteria
        """
        suggestions = self.load_suggestions()

        if status:
            return [s for s in suggestions if s.status == status]

        return suggestions

    def get_suggestions_for_section(
        self,
        section_id: str | None,
    ) -> list[Suggestion]:
        """Get suggestions for a specific section.

        Args:
            section_id: Section identifier (None for spec-level suggestions)

        Returns:
            List of suggestions for the section
        """
        suggestions = self.load_suggestions()

        filtered = [s for s in suggestions if s.section_id == section_id]

        return filtered

    def get_suggestions_by_author(
        self,
        author: str,
    ) -> list[Suggestion]:
        """Get all suggestions by a specific author.

        Args:
            author: Author identifier

        Returns:
            List of suggestions by the author
        """
        suggestions = self.load_suggestions()

        filtered = [s for s in suggestions if s.author == author]

        return filtered

    def accept_suggestion(
        self,
        suggestion_id: str,
        reviewed_by: str,
        review_comment: str | None = None,
    ) -> bool:
        """Accept a suggestion.

        Args:
            suggestion_id: Suggestion to accept
            reviewed_by: User accepting the suggestion
            review_comment: Optional comment from reviewer

        Returns:
            True if acceptance was successful
        """
        suggestions = self.load_suggestions()

        for suggestion in suggestions:
            if suggestion.id == suggestion_id:
                suggestion.status = SuggestionStatus.ACCEPTED
                suggestion.reviewed_by = reviewed_by
                suggestion.reviewed_at = datetime.utcnow()
                suggestion.review_comment = review_comment.strip() if review_comment else None

                if self.save_suggestions(suggestions):
                    logger.info(
                        "Accepted suggestion %s by %s",
                        suggestion_id,
                        reviewed_by,
                    )
                    return True
                return False

        logger.warning("Suggestion not found for acceptance: %s", suggestion_id)
        return False

    def reject_suggestion(
        self,
        suggestion_id: str,
        reviewed_by: str,
        review_comment: str | None = None,
    ) -> bool:
        """Reject a suggestion.

        Args:
            suggestion_id: Suggestion to reject
            reviewed_by: User rejecting the suggestion
            review_comment: Optional comment from reviewer

        Returns:
            True if rejection was successful
        """
        suggestions = self.load_suggestions()

        for suggestion in suggestions:
            if suggestion.id == suggestion_id:
                suggestion.status = SuggestionStatus.REJECTED
                suggestion.reviewed_by = reviewed_by
                suggestion.reviewed_at = datetime.utcnow()
                suggestion.review_comment = review_comment.strip() if review_comment else None

                if self.save_suggestions(suggestions):
                    logger.info(
                        "Rejected suggestion %s by %s",
                        suggestion_id,
                        reviewed_by,
                    )
                    return True
                return False

        logger.warning("Suggestion not found for rejection: %s", suggestion_id)
        return False

    def reset_suggestion(self, suggestion_id: str) -> bool:
        """Reset a reviewed suggestion back to pending.

        Args:
            suggestion_id: Suggestion to reset

        Returns:
            True if reset was successful
        """
        suggestions = self.load_suggestions()

        for suggestion in suggestions:
            if suggestion.id == suggestion_id:
                suggestion.status = SuggestionStatus.PENDING
                suggestion.reviewed_by = None
                suggestion.reviewed_at = None
                suggestion.review_comment = None

                if self.save_suggestions(suggestions):
                    logger.info("Reset suggestion %s to pending", suggestion_id)
                    return True
                return False

        logger.warning("Suggestion not found for reset: %s", suggestion_id)
        return False

    def update_suggestion(
        self,
        suggestion_id: str,
        suggested_text: str | None = None,
        reason: str | None = None,
    ) -> bool:
        """Update suggestion content.

        Args:
            suggestion_id: Suggestion to update
            suggested_text: New suggested text
            reason: New reason

        Returns:
            True if update was successful
        """
        suggestions = self.load_suggestions()

        for suggestion in suggestions:
            if suggestion.id == suggestion_id:
                if suggested_text is not None:
                    if not suggested_text or not suggested_text.strip():
                        logger.warning("Cannot update suggestion with empty suggested_text")
                        return False
                    suggestion.suggested_text = suggested_text.strip()

                if reason is not None:
                    suggestion.reason = reason.strip() if reason else None

                if self.save_suggestions(suggestions):
                    logger.info("Updated suggestion %s", suggestion_id)
                    return True
                return False

        logger.warning("Suggestion not found for update: %s", suggestion_id)
        return False

    def delete_suggestion(self, suggestion_id: str) -> bool:
        """Delete a suggestion permanently.

        Args:
            suggestion_id: Suggestion to delete

        Returns:
            True if deletion was successful
        """
        suggestions = self.load_suggestions()

        # Find and remove suggestion
        original_length = len(suggestions)
        suggestions = [s for s in suggestions if s.id != suggestion_id]

        if len(suggestions) < original_length:
            if self.save_suggestions(suggestions):
                logger.info("Deleted suggestion %s", suggestion_id)
                return True
            return False

        logger.warning("Suggestion not found for deletion: %s", suggestion_id)
        return False

    def get_suggestion_count(
        self,
        section_id: str | None = None,
    ) -> int:
        """Get count of suggestions.

        Args:
            section_id: Optional section to count for

        Returns:
            Number of suggestions matching criteria
        """
        if section_id:
            return len(self.get_suggestions_for_section(section_id))
        return len(self.get_suggestions_for_spec())

    def get_pending_suggestion_count(self, section_id: str | None = None) -> int:
        """Get count of pending suggestions.

        Args:
            section_id: Optional section to count for

        Returns:
            Number of pending suggestions
        """
        if section_id:
            suggestions = self.get_suggestions_for_section(section_id)
        else:
            suggestions = self.get_suggestions_for_spec()

        return len([s for s in suggestions if s.status == SuggestionStatus.PENDING])

    def get_suggestions_by_status(
        self,
        status: SuggestionStatus,
        section_id: str | None = None,
    ) -> list[Suggestion]:
        """Get suggestions by status.

        Args:
            status: Status to filter by
            section_id: Optional section to filter by

        Returns:
            List of suggestions with the specified status
        """
        if section_id:
            suggestions = self.get_suggestions_for_section(section_id)
        else:
            suggestions = self.get_suggestions_for_spec()

        return [s for s in suggestions if s.status == status]
