"""
Git repository model for user OAuth connections

SQLAlchemy ORM model for the repositories table. Handles linking users
to their Git repositories via OAuth.
"""

from datetime import datetime, UTC
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from core.database import Base


class GitRepository(Base):
    """
    Git repository model for cloud-hosted Auto Claude

    Stores user Git repository connections via OAuth. Links users to their
    repositories on GitHub, GitLab, or other Git providers.
    """

    __tablename__ = "repositories"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Git provider details
    provider = Column(String(50), nullable=False)  # "github", "gitlab", etc.
    repository_url = Column(String(500), nullable=False)
    repository_name = Column(String(255), nullable=False)
    repository_owner = Column(String(255), nullable=False)

    # OAuth credentials (encrypted at rest in production)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    # Relationship to User
    user = relationship("User", back_populates="repositories")

    def __repr__(self) -> str:
        """String representation of GitRepository model"""
        return f"<GitRepository(id={self.id}, user_id={self.user_id}, provider={self.provider}, repo={self.repository_name})>"


# Pydantic models for API requests and responses


class RepositoryCreateRequest(BaseModel):
    """Request model for linking a repository"""

    provider: str = Field(..., description="Git provider (github, gitlab, etc.)")
    repository_url: str = Field(..., description="Full repository URL")
    repository_name: str = Field(..., description="Repository name")
    repository_owner: str = Field(..., description="Repository owner/organization")
    access_token: str = Field(..., description="OAuth access token")
    refresh_token: Optional[str] = Field(None, description="OAuth refresh token")
    token_expires_at: Optional[datetime] = Field(None, description="Token expiration timestamp")


class RepositoryResponse(BaseModel):
    """Response model for repository data"""

    id: int = Field(..., description="Repository ID")
    user_id: int = Field(..., description="User ID")
    provider: str = Field(..., description="Git provider")
    repository_url: str = Field(..., description="Repository URL")
    repository_name: str = Field(..., description="Repository name")
    repository_owner: str = Field(..., description="Repository owner")
    created_at: datetime = Field(..., description="Link creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class RepositoryListResponse(BaseModel):
    """Response model for list of repositories"""

    repositories: list[RepositoryResponse] = Field(..., description="List of repositories")
