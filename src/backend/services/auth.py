"""Authentication service: password hashing, JWT creation/decoding, and auth dependency."""

from datetime import datetime, timedelta, timezone

from fastapi import Header, HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.backend.core.config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plain-text password using bcrypt.

    Args:
        plain: The plain-text password string.

    Returns:
        A bcrypt-hashed password string.
    """
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a stored hash.

    Args:
        plain: The plain-text password to verify.
        hashed: The previously hashed password to compare against.

    Returns:
        True if the password matches, False otherwise.
    """
    return _pwd.verify(plain, hashed)


def create_access_token(user_id: str, username: str) -> str:
    """Create a signed JWT access token for the given user.

    Args:
        user_id: The user's UUID as a string, stored in the ``sub`` claim.
        username: The user's display name, stored as an additional claim.

    Returns:
        A signed JWT string.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": user_id, "username": username, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token.

    Args:
        token: The JWT string to decode.

    Returns:
        The decoded payload dict on success, or an empty dict if the token is
        invalid or expired.
    """
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError:
        return {}


async def get_current_player(authorization: str = Header(...)) -> dict:
    """FastAPI dependency that extracts and validates the Bearer token.

    Args:
        authorization: The HTTP ``Authorization`` header value.

    Returns:
        The decoded JWT payload dict containing ``sub`` (user_id) and
        ``username``.

    Raises:
        HTTPException: 401 if the header is missing the Bearer prefix or the
            token is invalid/expired.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.removeprefix("Bearer ")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload  # {"sub": user_id, "username": username}
