import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base


class MatchStatus(str, enum.Enum):
    """Lifecycle states for a match.

    Attributes:
        pending: Match created but not yet started.
        ongoing: Match is currently in progress.
        finished: Match has concluded with a winner.
    """

    pending = "pending"
    ongoing = "ongoing"
    finished = "finished"


class Match(Base):
    """ORM model representing a single match between two participants.

    Either participant may be None for NPC (AI) matches.

    Attributes:
        id: UUID primary key, auto-generated.
        player1_id: FK to players.id; None if participant is an NPC.
        player2_id: FK to players.id; None if participant is an NPC.
        winner_id: FK to players.id of the winning player; None until finished.
        status: Current lifecycle state of the match.
        started_at: UTC timestamp when the match transitioned to ongoing.
        ended_at: UTC timestamp when the match was finished.
    """

    __tablename__ = "matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    player1_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), nullable=True, index=True
    )
    player2_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), nullable=True, index=True
    )
    winner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), nullable=True
    )
    status: Mapped[MatchStatus] = mapped_column(
        SAEnum(MatchStatus), default=MatchStatus.pending, nullable=False, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
