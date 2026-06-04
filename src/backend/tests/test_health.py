import pytest

# Use the session-scoped event loop so that asyncpg connections established by
# the session-scoped test_engine fixture are in the same loop as this test.
pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
