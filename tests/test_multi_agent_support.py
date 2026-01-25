
import pytest
import asyncio
from environments.grid_world import GridWorld
from agents.learning_agent import LearningGridAgent
from utils.message_bus import MessageBus
from models.decision_model import GridDecisionModel, ModelConfig

@pytest.mark.asyncio
async def test_multi_agent_state_independence():
    """Verify multiple agents have independent positions in the world."""
    env = GridWorld(size=5)
    bus = MessageBus()
    await bus.start()
    
    # Init agents
    model = GridDecisionModel(ModelConfig(input_size=4, output_size=4))
    agent_a = LearningGridAgent("Agent-A", bus, env, model)
    agent_b = LearningGridAgent("Agent-B", bus, env, model)
    
    # Reset
    pos_a = env.reset(agent_id=agent_a.agent_id)
    pos_b = env.reset(agent_id=agent_b.agent_id)
    
    assert pos_a == (0, 0)
    assert pos_b == (0, 0)
    assert env.agents["Agent-A"] == (0, 0)
    assert env.agents["Agent-B"] == (0, 0)
    
    # Move Agent A UP (x, y+1) -> (0, 1)
    # Mock model or force action? 
    # LearningGridAgent.select_action uses epsilon greedy.
    # Let's interact with env directly using agent_id to verify env logic first
    env.step("UP", agent_id="Agent-A")
    assert env.agents["Agent-A"] == (0, 1)
    assert env.agents["Agent-B"] == (0, 0) # B should not move
    
    # Move Agent B RIGHT (x+1, y) -> (1, 0)
    env.step("RIGHT", agent_id="Agent-B")
    assert env.agents["Agent-A"] == (0, 1)
    assert env.agents["Agent-B"] == (1, 0)
    
    await bus.stop()

@pytest.mark.asyncio
async def test_collaboration_communication():
    """Verify agents can signal events via bus."""
    bus = MessageBus()
    await bus.start()
    
    received_msgs = []
    async def handler(msg):
        received_msgs.append(msg)
        
    bus.subscribe("goal_reached", handler)
    
    # Simulate runner logic
    agent_id = "Agent-Winner"
    goal_pos = (4, 4)
    
    await bus.publish("goal_reached", agent_id, {"pos": goal_pos})
    await asyncio.sleep(0.1)
    
    assert len(received_msgs) == 1
    assert received_msgs[0].sender == agent_id
    assert received_msgs[0].payload["pos"] == goal_pos
    
    await bus.stop()
