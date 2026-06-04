import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.core.database import Base

if TYPE_CHECKING:
    from src.backend.models.player import Player


class NpcMemory(Base):
    """ORM model for persisting NPC memory about a specific opponent.

    One row per opponent player; updated after each match round involving that
    opponent so the NPC can adapt its strategy over time.

    Attributes:
        id: UUID primary key, auto-generated.
        opponent_id: FK to players.id; unique — one memory record per opponent.
        attack_patterns: JSONB list of observed attack pattern descriptors.
        weaknesses: JSONB list of identified weakness strings.
        avg_damage_recv: Running average damage received per round from opponent.
        round_count: Total rounds observed against this opponent.
        updated_at: UTC timestamp of the last memory update.
        opponent: Relationship to the Player this memory is about.
    """

    __tablename__ = "npc_memory"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    opponent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), unique=True, nullable=False
    )
    opponent: Mapped["Player"] = relationship("Player", foreign_keys=[opponent_id])
    attack_patterns: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    weaknesses: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    avg_damage_recv: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    round_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
