import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from agent_forge.server.api import app, session_manager
from unittest.mock import MagicMock, patch

@pytest.mark.asyncio
async def test_server_lifecycle():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Start Default Session
        resp = await ac.post("/api/sim/start", json={
            "num_agents": 2, 
            "grid_size": 10, 
            "vertical": "warehouse"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "started"
        assert data["session_id"] == "default"
        
        # Verify internal state
        assert "default" in session_manager.sessions
        runner = session_manager.sessions["default"]
        assert runner.is_running
        assert len(runner.agents) == 2
        
        # 2. Stop Session
        resp = await ac.post("/api/sim/stop")
        assert resp.status_code == 200
        assert not runner.is_running

@pytest.mark.asyncio
async def test_server_resilience():
    """Verify server survives SDK crash during start."""
    # Clear global state to ensure we get a fresh Runner (Mock)
    session_manager.sessions.clear()
    
    # Mock HeadlessRunner to raise Exception on start
    with patch("agent_forge.server.api.HeadlessRunner") as MockRunner:
        mock_instance = MockRunner.return_value
        mock_instance.start.side_effect = RuntimeError("SDK CRASH SIMULATION")
        mock_instance.is_running = False
        
        mock_instance.is_running = False
        
        # raise_app_exceptions=False allows us to see the 500 response instead of crashing the test client
        async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as ac:
            # Try to start
            print("DEBUG: Sending Start Request")
            # Should return 500 or Error, but NOT crash the server process
            # FastAPI handles exceptions by default (500)
            resp = await ac.post("/api/sim/start", json={
                "num_agents": 1, 
                "grid_size": 5,
                "vertical": "warehouse"
            })
            print(f"DEBUG: Status Code: {resp.status_code}")
            print(f"DEBUG: Response Body: {resp.text}")
            # It should probably be 500 because we re-raised the exception in api.py
            assert resp.status_code == 500
            
            # Verify server is still alive
            health = await ac.get("/docs")
            assert health.status_code == 200

if __name__ == "__main__":
    asyncio.run(test_server_lifecycle())
