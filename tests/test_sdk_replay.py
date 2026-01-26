import asyncio
import os
import shutil
import pytest
import random
from agent_forge.core.runner import HeadlessRunner
from agent_forge.core.engine import SimulationEngine
from agent_forge.envs.warehouse import WarehouseEnv
from agent_forge.envs.warehouse_agent import WarehouseAgent
from agent_forge.utils.message_bus import MessageBus
from tests.helpers.replay_agent import ReplayStubAgent

@pytest.mark.asyncio
async def test_replay_determinism():
    """
    Verifies that re-playing the exact same action sequence results in the exact same state.
    """
    GRID_SIZE = 5
    NUM_AGENTS = 1
    STEPS = 20
    SEED = 123
    
    # --- PHASE 1: RECORD ---
    random.seed(SEED)
    
    bus1 = MessageBus(log_path=None) 
    await bus1.start()
    env1 = WarehouseEnv(size=GRID_SIZE, num_agents=NUM_AGENTS)
    engine1 = SimulationEngine(env1)
    
    agent1 = WarehouseAgent("Agent-Replay", bus1, engine1)
    agent1.enable_checkpoints = False
    env1.get_agent_state("Agent-Replay") # Init
    
    # Capture Trace: List of (Action, ResultStateHash)
    trace_actions = []
    trace_states = []
    
    for _ in range(STEPS):
        # We manually drive the agent decision logic
        await agent1.step()
        
        # We need to capture what action it JUST took. 
        # But step() logic is internal.
        # Ideally we'd intercept perform_action in engine?
        # Or we rely on the fact that if we seed it, it behaves same.
        # BUT this test specifically wants to test ACTION REPLAY (Environment Determinism).
        # So we need to know the action.
        
        # HACK for Test: access log/state
        # Better: Mock the engine to capture calls?
        # Or just trust that we can't easily capture action from outside without spying.
        
        # Alternative: We produce the actions externally!
        # Let's generate a RANDOM sequence of actions and force the Agent to take them?
        # No, WarehouseAgent step() calculates logic.
        
        # Let's use `engine1.perform_action` wrapper to capture? 
        # For this test, let's subclass Engine or just spy on it?
        pass

    # RE-STRATEGY: 
    # Instead of recording a smart agent, let's RECORD A RANDOM WALK.
    # Then Replay the Random Walk.
    # This proves Env Determinism nicely.
    
    recorded_actions = []
    recorded_states = []
    
    # Reset for cleaner Random Walk
    random.seed(SEED)
    env_rec = WarehouseEnv(size=GRID_SIZE, num_agents=NUM_AGENTS)
    engine_rec = SimulationEngine(env_rec)
    env_rec.get_agent_state("Agent-0")
    
    possible_actions = ["UP", "DOWN", "LEFT", "RIGHT", "PICKUP", "DROPOFF", "CHARGE"]
    
    for _ in range(STEPS):
        action = random.choice(possible_actions)
        recorded_actions.append(action)
        
        should_proceed = await engine_rec.perform_action("Agent-0", action)
        state = await engine_rec.get_state("Agent-0")
        recorded_states.append(str(state)) # Stringify as hash proxy
        
    # --- PHASE 2: REPLAY ---
    # New clean env
    env_play = WarehouseEnv(size=GRID_SIZE, num_agents=NUM_AGENTS)
    engine_play = SimulationEngine(env_play)
    
    # We need to ensure initial state is same!
    # The Env init uses random for positions.
    # So we must seed before Init!
    
    # WAIT! We seeded random.seed(SEED) before env_rec.
    # We must seed random.seed(SEED) before env_play too!
    random.seed(SEED)
    env_play = WarehouseEnv(size=GRID_SIZE, num_agents=NUM_AGENTS)
    engine_play = SimulationEngine(env_play)
    env_play.get_agent_state("Agent-0") # Init state (should be same random pos)
    
    replay_agent = ReplayStubAgent("Agent-0", None, engine_play, recorded_actions)
    
    for i in range(STEPS):
        await replay_agent.step() # Takes recorded_actions[i]
        
        state = await engine_play.get_state("Agent-0")
        
        # Verify
        if str(state) != recorded_states[i]:
            print(f"MISMATCH at step {i}")
            print(f"Action: {recorded_actions[i]}")
            print(f"Expect: {recorded_states[i]}")
            print(f"Actual: {state}")
            assert False, "Replay state mismatch!"

    print("SUCCESS: Replay matched exactly.")

if __name__ == "__main__":
    asyncio.run(test_replay_determinism())
