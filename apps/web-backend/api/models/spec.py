"""
Spec data models

Pydantic models for spec management API endpoints.
These models extend the task models since tasks and specs are synonymous.
"""

from api.models.task import TaskDetail, TaskProgressDetail, TaskStatus, TaskSummary
from pydantic import BaseModel, Field


class SpecStatus(TaskStatus):
    """Spec status - extends TaskStatus (tasks and specs are synonymous)."""


class SpecSummary(TaskSummary):
    """Spec summary - extends TaskSummary (tasks and specs are synonymous)."""


class SpecProgressDetail(TaskProgressDetail):
    """Spec progress detail - extends TaskProgressDetail."""


class SpecDetail(TaskDetail):
    """Spec detail - extends TaskDetail (tasks and specs are synonymous)."""


class SpecListResponse(BaseModel):
    """Response model for listing specs"""

    specs: list[SpecSummary] = Field(default_factory=list, description="List of specs")
    total: int = Field(..., description="Total number of specs")
