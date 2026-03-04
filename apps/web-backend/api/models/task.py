"""
Task/Spec data models

Pydantic models for task (spec) management API endpoints.
Tasks and specs are synonymous - a spec is a task to be implemented.
"""

from pydantic import BaseModel, Field


class TaskStatus(BaseModel):
    """Task status and progress information"""

    status: str = Field(
        ..., description="Status: pending, initialized, in_progress, complete"
    )
    progress: str = Field(
        ..., description="Progress string (e.g., '3/10' for subtasks)"
    )
    has_build: bool = Field(
        default=False, description="Whether an active build exists in worktree"
    )


class TaskSummary(BaseModel):
    """Summary information for a task/spec"""

    number: str = Field(..., description="Spec number (e.g., '001')")
    name: str = Field(..., description="Human-readable spec name")
    folder: str = Field(..., description="Folder name (e.g., '001-feature-name')")
    status: str = Field(..., description="Current status")
    progress: str = Field(..., description="Progress string")
    has_build: bool = Field(default=False, description="Whether an active build exists")


class TaskProgressDetail(BaseModel):
    """Detailed progress information for a task"""

    completed: int = Field(default=0, description="Number of completed subtasks")
    in_progress: int = Field(default=0, description="Number of in-progress subtasks")
    pending: int = Field(default=0, description="Number of pending subtasks")
    failed: int = Field(default=0, description="Number of failed subtasks")
    total: int = Field(default=0, description="Total number of subtasks")
    percentage: float = Field(default=0.0, description="Completion percentage (0-100)")


class TaskDetail(BaseModel):
    """Detailed information for a specific task/spec"""

    number: str = Field(..., description="Spec number")
    name: str = Field(..., description="Spec name")
    folder: str = Field(..., description="Folder name")
    status: str = Field(..., description="Current status")
    progress: TaskProgressDetail = Field(
        ..., description="Detailed progress information"
    )
    has_build: bool = Field(default=False, description="Whether an active build exists")
    spec_content: str | None = Field(None, description="Content of spec.md file")


class TaskListResponse(BaseModel):
    """Response model for listing tasks"""

    tasks: list[TaskSummary] = Field(default_factory=list, description="List of tasks")
    total: int = Field(..., description="Total number of tasks")
