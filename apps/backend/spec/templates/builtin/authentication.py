"""
Authentication Template
=======================

Template for implementing user authentication flows.
"""

from typing import Any

from ..registry import Template


class AuthenticationTemplate(Template):
    """Template for authentication implementation."""

    def __init__(self):
        """Initialize the authentication template."""
        super().__init__(
            name="authentication",
            description="User authentication with login, signup, and session management",
            category="security",
            parameters={
                "auth_method": {
                    "type": str,
                    "required": True,
                    "description": "Authentication method (jwt, session, oauth)",
                },
                "providers": {
                    "type": list,
                    "required": False,
                    "default": ["email"],
                    "description": "Authentication providers (email, google, github, etc.)",
                },
                "password_reset": {
                    "type": bool,
                    "required": False,
                    "default": True,
                    "description": "Include password reset functionality",
                },
                "email_verification": {
                    "type": bool,
                    "required": False,
                    "default": True,
                    "description": "Require email verification",
                },
                "mfa_support": {
                    "type": bool,
                    "required": False,
                    "default": False,
                    "description": "Support multi-factor authentication",
                },
            },
        )

    def generate(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate authentication spec from parameters."""
        auth_method = params["auth_method"]
        providers = params.get("providers", ["email"])
        password_reset = params.get("password_reset", True)
        email_verification = params.get("email_verification", True)
        mfa_support = params.get("mfa_support", False)

        providers_str = ", ".join(providers)

        return {
            "title": "User Authentication",
            "description": f"Secure user authentication system using {auth_method.upper()} with support for {providers_str}.",
            "rationale": "Provide secure, user-friendly authentication that protects user accounts while enabling easy access to the application.",
            "user_stories": [
                "As a user, I want to sign up for an account",
                "As a user, I want to log in securely",
                "As a user, I want to log out",
            ]
            + (
                ["As a user, I want to reset my forgotten password"]
                if password_reset
                else []
            )
            + (
                ["As a user, I want to verify my email address"]
                if email_verification
                else []
            )
            + (
                [
                    "As a user, I want to enable two-factor authentication for extra security"
                ]
                if mfa_support
                else []
            ),
            "acceptance_criteria": [
                "Sign up endpoint creates new user account",
                f"Login endpoint validates credentials and returns {auth_method.upper()} token/session",
                "Logout endpoint invalidates session/token",
                "Password must meet security requirements (min length, complexity)",
                "Failed login attempts are rate-limited to prevent brute force",
            ]
            + (
                ["Password reset flow sends email with secure reset link"]
                if password_reset
                else []
            )
            + (
                ["Email verification required before account activation"]
                if email_verification
                else []
            )
            + (["MFA enrollment and verification endpoints"] if mfa_support else [])
            + (
                [f"OAuth integration for: {providers_str}"]
                if any(p != "email" for p in providers)
                else []
            ),
            "technical_details": f"""
### Authentication Method

{auth_method.upper()}-based authentication

### Endpoints

**Sign Up**
- Method: POST
- Path: /auth/signup
- Body: {{ "email": "...", "password": "...", "name": "..." }}
- Response: 201 Created

**Log In**
- Method: POST
- Path: /auth/login
- Body: {{ "email": "...", "password": "..." }}
- Response: 200 OK with {auth_method} token

**Log Out**
- Method: POST
- Path: /auth/logout
- Response: 200 OK

{"**Password Reset**" if password_reset else ""}
{"- Method: POST" if password_reset else ""}
{"- Path: /auth/password-reset" if password_reset else ""}
{'- Body: { "email": "..." }' if password_reset else ""}
{"- Response: 200 OK (email sent)" if password_reset else ""}

{"**Email Verification**" if email_verification else ""}
{"- Method: GET" if email_verification else ""}
{"- Path: /auth/verify-email?token=..." if email_verification else ""}
{"- Response: 200 OK" if email_verification else ""}

### Security Requirements

- Passwords hashed with bcrypt/argon2
- Rate limiting on login attempts (5 attempts per 15 minutes)
- HTTPS required for all authentication endpoints
- Secure token generation and storage
{"- CSRF protection for session-based auth" if auth_method == "session" else ""}
{"- Token expiration and refresh mechanism" if auth_method == "jwt" else ""}

### Authentication Providers

{chr(10).join([f"- {provider.capitalize()}" for provider in providers])}
""",
            "test_coverage": [
                "Unit tests for password hashing and validation",
                "Integration tests for signup flow",
                "Integration tests for login flow",
                "Integration tests for logout",
                "Tests for rate limiting",
                "Tests for invalid credentials",
            ]
            + (["Tests for password reset flow"] if password_reset else [])
            + (["Tests for email verification"] if email_verification else [])
            + (["Tests for MFA enrollment and verification"] if mfa_support else []),
        }
