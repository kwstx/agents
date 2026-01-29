import pytest
from fastapi.testclient import TestClient
from agent_forge.server.api import app, session_manager

client = TestClient(app)

def test_engine_lifecycle_singleton():
    """
    Verifies that the SimulationEngine is initialized exactly once per server lifecycle
    and reused across simulation sessions, rather than being discarded.
    """
    # 1. Start Session A
    start_payload = {
        "num_agents": 2,
        "grid_size": 10,
        "vertical": "warehouse"
    }
    response = client.post("/api/v1/sim/control", json={"action": "start", "config": start_payload})
    assert response.status_code == 200
    
    # Get the runner and engine ID
    runner_a = session_manager.sessions["default"]
    engine_a = runner_a.engine
    engine_id_a = id(engine_a)
    
    assert engine_a is not None
    assert runner_a.is_running is True
    
    # 2. Stop Session A
    response = client.post("/api/v1/sim/control", json={"action": "stop"})
    assert response.status_code == 200
    assert runner_a.is_running is False
    
    # 3. Start Session B (Restart)
    response = client.post("/api/v1/sim/control", json={"action": "start", "config": start_payload})
    assert response.status_code == 200
    
    # Get the runner and engine ID again
    runner_b = session_manager.sessions["default"]
    engine_b = runner_b.engine
    engine_id_b = id(engine_b)
    
    # Assertions
    assert runner_a is runner_b, "Runner instance should persist (singleton session)"
    assert engine_a is engine_b, f"Engine instance should persist. IDs: {engine_id_a} vs {engine_id_b}"
    assert engine_id_a == engine_id_b
    
def test_clean_shutdown_without_start():
    """
    Verifies that stopping a session that hasn't started doesn't crash.
    """
    # reset session manager for this test if needed, or just use a new session id
    # mimic clean slate
    if "default" in session_manager.sessions:
        del session_manager.sessions["default"]
        
    # Attempt to stop non-existent
    response = client.post("/api/v1/sim/control", json={"action": "stop"})
    # Depending on API design, this might be 200 (idempotent) or 400/404 if "default" logic is strict.
    # Looking at api.py: control_session gets or creates runner. 
    # If action is 'stop', it calls stop(). 
    # Runner init state is STOPPED/IDLE. stop() should be safe.
    assert response.status_code == 200
    
    runner = session_manager.sessions.get("default")
    assert runner is not None
    assert runner.is_running is False

def test_repetitive_cycles():
    """
    Verifies stability under rapid start/stop cycles.
    """
    payload = {"num_agents": 1, "grid_size": 5, "vertical": "warehouse"}
    
    original_runner = None
    if "default" in session_manager.sessions:
        original_runner = session_manager.sessions["default"]

    original_engine_id = None
    if original_runner and original_runner.engine:
        original_engine_id = id(original_runner.engine)

    for i in range(5):
        # Start
        resp = client.post("/api/v1/sim/control", json={"action": "start", "config": payload})
        assert resp.status_code == 200
        
        # Capture ID on first run
        current_runner = session_manager.sessions["default"]
        if i == 0:
            original_engine_id = id(current_runner.engine)
        else:
            # Verify ID persistence
            assert id(current_runner.engine) == original_engine_id
            
        # Stop
        resp = client.post("/api/v1/sim/control", json={"action": "stop"})
        assert resp.status_code == 200

