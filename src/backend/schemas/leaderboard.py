from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    total_damage: int
    wins: int
    losses: int


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]
