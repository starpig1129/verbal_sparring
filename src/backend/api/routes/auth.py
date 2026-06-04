"""Auth API routes: register and login endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_session
from src.backend.models import Player
from src.backend.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from src.backend.services.auth import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    req: RegisterRequest, db: AsyncSession = Depends(get_session)
) -> TokenResponse:
    """Register a new player account and return a JWT token.

    Args:
        req: Registration payload containing username, password, and optional email.
        db: Injected async database session.

    Returns:
        A ``TokenResponse`` with the signed JWT and user details.

    Raises:
        HTTPException: 409 if the username is already taken.
    """
    existing = await db.execute(select(Player).where(Player.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already taken")
    player = Player(
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
    )
    db.add(player)
    await db.commit()
    token = create_access_token(str(player.id), player.username)
    return TokenResponse(
        access_token=token,
        username=player.username,
        user_id=str(player.id),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest, db: AsyncSession = Depends(get_session)
) -> TokenResponse:
    """Authenticate an existing player and return a JWT token.

    Args:
        req: Login payload containing username and password.
        db: Injected async database session.

    Returns:
        A ``TokenResponse`` with the signed JWT and user details.

    Raises:
        HTTPException: 401 if the username does not exist or the password is wrong.
    """
    result = await db.execute(select(Player).where(Player.username == req.username))
    player = result.scalar_one_or_none()
    if not player or not verify_password(req.password, player.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(str(player.id), player.username)
    return TokenResponse(
        access_token=token,
        username=player.username,
        user_id=str(player.id),
    )
