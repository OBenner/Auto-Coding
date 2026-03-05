"""
Plugin SDK Module
==================

SDK for developing Auto Code plugins.

This package provides base classes, utilities, and APIs for creating:
- Agent plugins: Custom agent behaviors and tools
- Integration plugins: External service connections via MCP
- UI plugins: Frontend extensions and custom UI components
"""

from .agent import AgentContext, AgentPlugin
from .docs_generator import PluginDocsGenerator
from .integration import IntegrationContext, IntegrationPlugin
from .scaffold import PluginScaffold
from .testing import MockAgentContext
from .ui import UIComponentDefinition, UIContext, UIExtensionPoint, UIPlugin
from .utils import PluginFileManager
from .validator import PluginValidator

__all__ = [
    "AgentContext",
    "AgentPlugin",
    "IntegrationContext",
    "IntegrationPlugin",
    "MockAgentContext",
    "PluginDocsGenerator",
    "PluginFileManager",
    "PluginScaffold",
    "PluginValidator",
    "UIContext",
    "UIPlugin",
    "UIExtensionPoint",
    "UIComponentDefinition",
]
