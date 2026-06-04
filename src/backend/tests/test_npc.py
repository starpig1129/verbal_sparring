import pytest
import uuid
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.asyncio(loop_scope="session")

from src.backend.services.npc.agent import run_npc_turn

MOCK_NPC_RESPONSE = "你的攻擊力跟你的智商一樣低！"


async def test_npc_generates_attack(db):
    opponent_id = str(uuid.uuid4())
    with patch("src.backend.services.npc.agent._call_ollama", new_callable=AsyncMock) as mock:
        mock.return_value = MOCK_NPC_RESPONSE
        result = await run_npc_turn(
            db=db,
            match_id=str(uuid.uuid4()),
            opponent_id=opponent_id,
            my_hp=100,
            opponent_hp=80,
            round_number=1,
            recent_opponent_attacks=["你好遜"],
        )
    assert isinstance(result, str)
    assert len(result) > 0


async def test_npc_uses_memory_in_prompt(db):
    opponent_id = str(uuid.uuid4())
    # 先建立記憶
    from src.backend.models import NpcMemory, Player
    player = Player(id=uuid.UUID(opponent_id), username=f"u_{opponent_id[:6]}", password_hash="x")
    db.add(player)
    memory = NpcMemory(
        opponent_id=uuid.UUID(opponent_id),
        attack_patterns=["愛用圖攻擊"],
        weaknesses=["怕文字嗆"],
        round_count=3,
    )
    db.add(memory)
    await db.commit()

    captured_prompt = []

    async def capture_call(messages):
        captured_prompt.extend(messages)
        return "記憶驅動攻擊！"

    with patch("src.backend.services.npc.agent._call_ollama", side_effect=capture_call):
        await run_npc_turn(
            db=db,
            match_id=str(uuid.uuid4()),
            opponent_id=opponent_id,
            my_hp=60,
            opponent_hp=100,
            round_number=5,
            recent_opponent_attacks=["圖攻擊1", "圖攻擊2"],
        )
    full_prompt = str(captured_prompt)
    assert "愛用圖攻擊" in full_prompt
