"""
Agent Templates Module
=======================

Custom agent configuration templates for specialized tasks.

This module provides:
- AgentTemplate: Core template model for custom agents
- AgentTemplateRegistry: Template management and discovery
- Template storage, validation, and versioning

Allows users to create, share, and use custom agent configurations
with specialized prompts, tools, and behaviors.
"""

from .models import AgentTemplate

__all__ = [
    "AgentTemplate",
]
