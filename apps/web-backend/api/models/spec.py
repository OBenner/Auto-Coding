"""
Spec data models

Pydantic models for spec management API endpoints.
These models are aliases for task models since tasks and specs are synonymous.
"""

from typing import Optional
from pydantic import BaseModel, Field


class SpecStatus(BaseModel):
    """Spec status and progress information"""

    status: str = Field(..., description="Status: pending, initialized, in_progress, complete")
    progress: str = Field(..., description="Progress string (e.g., '3/10' for subtasks)")
    has_build: bool = Field(default=False, description="Whether an active build exists in worktree")


class SpecSummary(BaseModel):
    """Summary information for a spec"""

    number: str = Field(..., description="Spec number (e.g., '001')")
    name: str = Field(..., description="Human-readable spec name")
    folder: str = Field(..., description="Folder name (e.g., '001-feature-name')")
    status: str = Field(..., description="Current status")
    progress: str = Field(..., description="Progress string")
    has_build: bool = Field(default=False, description="Whether an active build exists")


class SpecProgressDetail(BaseModel):
    """Detailed progress information for a spec"""

    completed: int = Field(default=0, description="Number of completed subtasks")
    in_progress: int = Field(default=0, description="Number of in-progress subtasks")
    pending: int = Field(default=0, description="Number of pending subtasks")
    failed: int = Field(default=0, description="Number of failed subtasks")
    total: int = Field(default=0, description="Total number of subtasks")
    percentage: float = Field(default=0.0, description="Completion percentage (0-100)")


class SpecDetail(BaseModel):
    """Detailed information for a specific spec"""

    number: str = Field(..., description="Spec number")
    name: str = Field(..., description="Spec name")
    folder: str = Field(..., description="Folder name")
    status: str = Field(..., description="Current status")
    progress: SpecProgressDetail = Field(..., description="Detailed progress information")
    has_build: bool = Field(default=False, description="Whether an active build exists")
    spec_content: Optional[str] = Field(None, description="Content of spec.md file")


class SpecListResponse(BaseModel):
    """Response model for listing specs"""

    specs: list[SpecSummary] = Field(default_factory=list, description="List of specs")
    total: int = Field(..., description="Total number of specs")
