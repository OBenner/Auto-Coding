"""
Template System
===============

Pre-built specification templates for common development tasks.
"""

from .generator import SpecGenerator
from .library import TemplateLibrary, suggest_templates
from .registry import Template, TemplateRegistry

__all__ = [
    "TemplateRegistry",
    "Template",
    "SpecGenerator",
    "TemplateLibrary",
    "suggest_templates",
]
