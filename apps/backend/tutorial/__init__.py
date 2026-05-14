"""
Tutorial Module
================

Handles tutorial orchestration for new user onboarding.
Generates simple example specs and runs guided autonomous builds.
"""

from .tutorial_spec_generator import generate_tutorial_spec

__all__ = ["generate_tutorial_spec"]
