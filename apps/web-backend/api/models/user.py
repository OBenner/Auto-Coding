"""
User model for authentication and authorization

SQLAlchemy ORM model for the users table. Handles user registration,
authentication, and profile management.
"""

from datetime import UTC, datetime

from core.database import Base
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    """
    User model for cloud-hosted Auto Code

    Stores user authentication credentials and profile information.
    Passwords are hashed using bcrypt before storage.
    """

    __tablename__ = "users"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Authentication fields
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    repositories = relationship(
        "GitRepository", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        """
        Hash and set the user's password

        Args:
            password: Plain text password to hash
        """
        self.hashed_password = pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        """
        Verify a password against the stored hash

        Args:
            password: Plain text password to verify

        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(password, self.hashed_password)

    def __repr__(self) -> str:
        """String representation of User model"""
        return f"<User(id={self.id}, email={self.email}, active={self.is_active})>"


# Pydantic models for API requests and responses


class UserRegisterRequest(BaseModel):
    """Request model for user registration"""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ..., min_length=8, description="User password (min 8 characters)"
    )


class UserLoginRequest(BaseModel):
    """Request model for user login"""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    """Response model for user data"""

    id: int = Field(..., description="User ID")
    email: str = Field(..., description="User email address")
    is_active: bool = Field(..., description="Whether the account is active")
    is_verified: bool = Field(..., description="Whether the email is verified")
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Response model for authentication token"""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: UserResponse = Field(..., description="User information")
