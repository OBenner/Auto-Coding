"""
Plugin SDK Module
==================

SDK for developing Auto Claude plugins.

This package provides base classes, utilities, and APIs for creating:
- Agent plugins: Custom agent behaviors and tools
- Integration plugins: External service connections via MCP
- UI plugins: Frontend extensions and custom UI components
"""

from .agent import AgentContext, AgentPlugin
from .integration import IntegrationContext, IntegrationPlugin
from .ui import UIContext, UIPlugin, UIExtensionPoint, UIComponentDefinition

__all__ = [
    "AgentContext",
    "AgentPlugin",
    "IntegrationContext",
    "IntegrationPlugin",
    "UIContext",
    "UIPlugin",
    "UIExtensionPoint",
    "UIComponentDefinition",
]
