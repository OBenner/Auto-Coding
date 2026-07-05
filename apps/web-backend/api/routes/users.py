"""
User Management API routes

Provides endpoints for user registration, login, and profile management.
"""

import logging

from core.database import get_db
from core.security import create_access_token
from fastapi import APIRouter, Depends, HTTPException, status
from services.workspace_service import (
    accept_pending_invitations,
    get_or_create_personal_workspace,
)
from sqlalchemy.orm import Session

from api.models.user import (
    TokenResponse,
    User,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

logger = logging.getLogger(__name__)

# OAuth2 standard token type constant (not a credential)
_BEARER = "bearer"

# Create router for user endpoints
router = APIRouter(prefix="/api/users", tags=["users"])


def _build_token_response(user: "User") -> "TokenResponse":
    """Create an access token and wrap it with user info in a TokenResponse.

    Encapsulates the repeated pattern of: create token → build UserResponse →
    return TokenResponse that appears in both register and login handlers.

    Args:
        user: The authenticated or newly created User ORM object.

    Returns:
        TokenResponse containing the JWT access token and public user info.
    """
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    user_response = UserResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
    )
    return TokenResponse(
        access_token=access_token,
        token_type=_BEARER,
        user=user_response,
    )


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(
    request: UserRegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Register a new user account.

    Creates a new user with the provided email and password. Passwords are
    automatically hashed using bcrypt before storage. Returns a JWT token
    for immediate authentication.

    Args:
        request: User registration data (email, password)
        db: Database session dependency

    Returns:
        TokenResponse with access token and user information

    Raises:
        HTTPException: 400 if email already exists

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/users/register \
             -H "Content-Type: application/json" \
             -d '{"email": "user@example.com", "password": "secure123"}'
        # Returns: {"access_token": "...", "token_type": "bearer", "user": {...}}
        ```
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    user = User(email=request.email)
    user.set_password(request.password)

    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("New user registered: id=%s", user.id)

    # Bootstrap the user's Personal workspace (single-mode default).
    get_or_create_personal_workspace(db, user.id)

    # Convert any pending workspace invitations for this email into memberships
    # (C7). Best-effort: registration must not fail because of an invite issue.
    try:
        accept_pending_invitations(db, user)
    except Exception:
        logger.warning(
            "Failed to accept pending invitations for user_id=%s",
            user.id,
            exc_info=True,
        )

    return _build_token_response(user)


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login_user(
    request: UserLoginRequest,
    db: Session = Depends(get_db),
):
    """
    Login with email and password.

    Authenticates a user with their email and password. Returns a JWT token
    for subsequent API requests.

    Args:
        request: User login credentials (email, password)
        db: Database session dependency

    Returns:
        TokenResponse with access token and user information

    Raises:
        HTTPException: 401 if credentials are invalid

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/users/login \
             -H "Content-Type: application/json" \
             -d '{"email": "user@example.com", "password": "secure123"}'
        # Returns: {"access_token": "...", "token_type": "bearer", "user": {...}}
        ```
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()

    # Verify user exists and password is correct
    if not user or not user.verify_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    logger.info("User logged in: %s", user.email)

    # Ensure a Personal workspace exists (idempotent; backfills pre-C2 accounts).
    get_or_create_personal_workspace(db, user.id)

    return _build_token_response(user)
