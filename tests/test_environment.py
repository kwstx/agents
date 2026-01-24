import pytest
from environments.grid_world import GridWorld

def test_initial_state():
    env = GridWorld()
    state = env.reset()
    assert state == (0, 0)

def test_movement_determinism():
    env = GridWorld()
    env.reset()
    
    # Move Right
    state, reward, done, info = env.step("RIGHT")
    assert state == (1, 0)
    assert reward == -0.1
    assert not done
    
    # Move Up
    state, reward, done, info = env.step("UP")
    assert state == (1, 1)

def test_boundary_conditions():
    env = GridWorld()
    env.reset()
    
    # Try moving DOWN from (0,0) - should hit wall
    state, reward, done, info = env.step("DOWN")
    assert state == (0, 0)  # No change
    assert reward == -1.0   # Penalty
    assert info["valid_action"] == False
    
    # Move LEFT - should hit wall
    state, reward, done, info = env.step("LEFT")
    assert state == (0, 0)

def test_goal_state():
    env = GridWorld(size=2) # Small grid for quick test: Goal at (1,1)
    env.reset()
    
    # (0,0) -> RIGHT -> (1,0)
    env.step("RIGHT")
    
    # (1,0) -> UP -> (1,1) [GOAL]
    state, reward, done, info = env.step("UP")
    
    assert state == (1, 1)
    assert reward == 10.0
    assert done == True

def test_invalid_action():
    env = GridWorld()
    env.reset()
    
    state, reward, done, info = env.step("FLY")
    assert state == (0, 0)
    assert reward == -1.0
    assert info["valid_action"] == False
