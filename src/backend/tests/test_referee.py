import pytest
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.asyncio(loop_scope="session")

from src.backend.services.referee.graph import run_referee

MOCK_OLLAMA_RESPONSE = '{"damage": 22, "referee_comment": "嘴砲有力", "display_text": "你這廢物！"}'


async def test_referee_returns_valid_result():
    with patch("src.backend.services.referee.graph._call_ollama", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = MOCK_OLLAMA_RESPONSE
        result = await run_referee("你好遜", None)
    assert result["damage"] == 22
    assert result["comment"] == "嘴砲有力"
    assert result["display_text"] == "你這廢物！"


async def test_referee_clamps_damage():
    with patch("src.backend.services.referee.graph._call_ollama", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = '{"damage": 99, "referee_comment": "爆表", "display_text": "X"}'
        result = await run_referee("超強攻擊", None)
    assert result["damage"] == 30  # clamped to max


async def test_referee_handles_parse_failure():
    with patch("src.backend.services.referee.graph._call_ollama", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = "我不知道啊"
        result = await run_referee("測試", None)
    assert result["damage"] == 10
    assert "裁判嘴瓢" in result["comment"]
    assert result["display_text"] == "測試"
