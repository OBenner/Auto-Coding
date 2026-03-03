"""
Context Package
===============

Task context building for autonomous coding.
"""

from .builder import ContextBuilder
from .categorizer import FileCategorizer
from .graphiti_integration import fetch_graph_hints, is_graphiti_enabled
from .keyword_extractor import KeywordExtractor
from .models import FileMatch, TaskContext
from .pattern_discovery import PatternDiscoverer, discover_with_memory
from .priority_manager import PriorityManager
from .search import CodeSearcher
from .serialization import load_context, save_context, serialize_context
from .service_matcher import ServiceMatcher
from .token_estimator import TokenEstimator

__all__ = [
    # Main builder
    "ContextBuilder",
    # Models
    "FileMatch",
    "TaskContext",
    # Components
    "CodeSearcher",
    "ServiceMatcher",
    "KeywordExtractor",
    "FileCategorizer",
    "PatternDiscoverer",
    "discover_with_memory",
    "TokenEstimator",
    "PriorityManager",
    # Graphiti integration
    "fetch_graph_hints",
    "is_graphiti_enabled",
    # Serialization
    "serialize_context",
    "save_context",
    "load_context",
]
