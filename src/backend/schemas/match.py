"""Pydantic schemas for the matches API."""

from pydantic import BaseModel, field_validator


class CreateMatchRequest(BaseModel):
    """Request body for creating a new match.

    Attributes:
        opponent: Either ``"npc"`` (case-insensitive) for an AI match, or
            the username of a registered human opponent (1–32 characters).
    """

    opponent: str

    @field_validator("opponent")
    @classmethod
    def opponent_must_be_valid(cls, v: str) -> str:
        """Validate and normalise the opponent field.

        Args:
            v: Raw opponent string from the request body.

        Returns:
            The stripped opponent string.

        Raises:
            ValueError: If the value is empty or exceeds 32 characters.
        """
        v = v.strip()
        if not v:
            raise ValueError("opponent must not be empty")
        if len(v) > 32:
            raise ValueError("opponent must be 32 characters or fewer")
        return v


class MatchResponse(BaseModel):
    """Response payload returned after a match is created.

    Attributes:
        match_id: UUID of the newly created match as a string.
        opponent: The opponent value echoed from the request.
        is_npc: True when the opponent is an NPC (AI), False otherwise.
    """

    match_id: str
    opponent: str
    is_npc: bool
