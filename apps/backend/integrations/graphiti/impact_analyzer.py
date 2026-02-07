"""
Impact analysis operations for code relationships.

Analyzes the impact of code changes by traversing dependency graphs
and calculating relationship strength scores.
"""

import logging
from pathlib import Path

from core.sentry import capture_exception

logger = logging.getLogger(__name__)


class ImpactAnalyzer:
    """
    Manages impact analysis and dependency traversal operations.

    Provides methods for analyzing the impact of code changes,
    computing relationship strength, and identifying tight coupling.
    """

    def __init__(
        self,
        client,
        group_id: str,
        spec_context_id: str,
        project_dir: Path,
    ):
        """
        Initialize impact analyzer.

        Args:
            client: GraphitiClient instance
            group_id: Group ID for memory namespace
            spec_context_id: Spec-specific context ID
            project_dir: Project root directory
        """
        self.client = client
        self.group_id = group_id
        self.spec_context_id = spec_context_id
        self.project_dir = project_dir
        self.logger = logger
