import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base


class GameRound(Base):
    """ORM model for a single round within a match.

    Captures the attacker's input, the AI-modified display text, the damage
    dealt, the referee's comment, and a snapshot of HP values after the round.

    Attributes:
        id: UUID primary key, auto-generated.
        match_id: FK to matches.id; the owning match.
        round_number: 1-based round index within the match.
        attacker_id: FK to players.id; None for NPC attacker.
        original_text: Raw text submitted by the attacker; None for image input.
        image_b64: Base64-encoded image input; None for text input.
        display_text: AI-rewritten attack text shown to both players.
        damage: Integer damage dealt this round (typically 10–30).
        referee_comment: Short snarky comment from the AI referee.
        hp_snapshot: JSONB map of player keys to remaining HP after this round.
        created_at: UTC timestamp when the round record was written.
    """

    __tablename__ = "rounds"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    attacker_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), nullable=True
    )
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_b64: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_text: Mapped[str] = mapped_column(Text, nullable=False)
    damage: Mapped[int] = mapped_column(Integer, nullable=False)
    referee_comment: Mapped[str] = mapped_column(Text, nullable=False)
    hp_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
