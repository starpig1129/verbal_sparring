from pydantic import BaseModel


class RoundSnapshot(BaseModel):
    round_number: int
    attacker: str | None
    original_text: str | None
    display_text: str
    damage: int
    referee_comment: str
    hp_snapshot: dict


class ReplayResponse(BaseModel):
    match_id: str
    rounds: list[RoundSnapshot]
