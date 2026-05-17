"""
Plugin SDK Module
==================

SDK for developing Auto Code plugins.

This package provides base classes, utilities, and APIs for creating:
- Agent plugins: Custom agent behaviors and tools
- Integration plugins: External service connections via MCP
- UI plugins: Frontend extensions and custom UI components
"""

from .agent import AgentContext, AgentPlugin, ToolHookDecision
from .integration import IntegrationContext, IntegrationPlugin
from .ui import UIComponentDefinition, UIContext, UIExtensionPoint, UIPlugin

__all__ = [
    "AgentContext",
    "AgentPlugin",
    "ToolHookDecision",
    "IntegrationContext",
    "IntegrationPlugin",
    "UIContext",
    "UIPlugin",
    "UIExtensionPoint",
    "UIComponentDefinition",
]
