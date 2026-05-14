"""
Tutorial Spec Generator
========================

Generates a simple, fixed spec for the login form component tutorial.
This provides a predictable, demonstrable example for new user onboarding.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def generate_tutorial_spec() -> dict[str, Any]:
    """
    Generate a fixed spec for the login form tutorial example.

    This creates a simple, non-trivial example that:
    - Is visual and demonstrable (login form UI)
    - Has clear acceptance criteria
    - Can be completed in under 15 minutes
    - Showcases all phases of autonomous development

    Returns:
        dict: Spec dictionary with title, description, and acceptance_criteria
    """
    spec = {
        "title": "Add Login Form Component",
        "description": (
            "Create a reusable login form component with email and password fields, "
            "validation, and submit handling. This component will be used across the "
            "application for user authentication.\n\n"
            "The component should follow existing UI patterns, include proper form "
            "validation, and provide clear error messages to users."
        ),
        "acceptance_criteria": [
            "Login form component created with email and password fields",
            "Form includes client-side validation (email format, password length)",
            "Component shows validation errors below each field",
            "Submit button disabled when form is invalid",
            "Loading state shown during submission",
            "Component follows existing design system patterns",
            "Component is responsive and accessible (ARIA labels, keyboard navigation)",
            "Unit tests cover validation logic",
        ],
        "user_stories": [
            "As a user, I want to enter my credentials in a clear form so I can log in to the application",
            "As a user, I want to see validation errors so I can correct my input before submitting",
        ],
        "technical_notes": (
            "This is a tutorial example designed to demonstrate Auto Code's autonomous "
            "development workflow. The task is intentionally scoped to be simple yet "
            "non-trivial, showcasing spec creation, planning, implementation, and QA phases."
        ),
    }

    logger.info(f"Generated tutorial spec: {spec['title']}")
    return spec
