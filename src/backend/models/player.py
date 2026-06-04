import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base


class Player(Base):
    """ORM model representing a registered player.

    Attributes:
        id: UUID primary key, auto-generated.
        username: Unique display name, max 32 characters.
        email: Optional unique email address.
        password_hash: Bcrypt/argon2 hashed password string.
        wins: Total wins accumulated across all matches.
        losses: Total losses accumulated across all matches.
        total_damage: Cumulative damage dealt across all rounds.
        created_at: UTC timestamp of account creation.
    """

    __tablename__ = "players"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_damage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
