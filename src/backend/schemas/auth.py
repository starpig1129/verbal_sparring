"""Pydantic schemas for auth request/response payloads."""

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    """Payload for the ``POST /api/auth/register`` endpoint.

    Attributes:
        username: Desired display name (max 32 chars enforced at DB level).
        password: Plain-text password; will be hashed before storage.
        email: Optional email address.
    """

    username: str
    password: str
    email: str | None = None


class LoginRequest(BaseModel):
    """Payload for the ``POST /api/auth/login`` endpoint.

    Attributes:
        username: Registered display name.
        password: Plain-text password to verify.
    """

    username: str
    password: str


class TokenResponse(BaseModel):
    """Response returned after successful register or login.

    Attributes:
        access_token: Signed JWT string.
        token_type: Always ``"bearer"``.
        username: The authenticated user's display name.
        user_id: The authenticated user's UUID as a string.
    """

    access_token: str
    token_type: str = "bearer"
    username: str
    user_id: str
