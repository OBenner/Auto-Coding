"""Backward compatibility shim - import from core.agent instead."""

from core.agent import *  # noqa: F403, F401

# Ensure workspace functions are explicitly exported
from core.agent import (  # noqa: F401
    load_workspace_context,
    get_workspace_project_dirs,
)
