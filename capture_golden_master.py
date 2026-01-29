import asyncio
import json
import logging
import os
import random
import shutil
import time
from datetime import datetime
import numpy as np # Implicit dependency for some envs usually, but strictly python based for now?

# Add source to path if needed (assuming running from root)
import sys
sys.path.append(os.getcwd())

from agent_forge.environments.grid_world import GridWorld
from agent_forge.environments.order_book_env import OrderBookEnv
from agent_forge.agents.learning_agent import LearningGridAgent
from agent_forge.models.decision_model import GridDecisionModel, ModelConfig
from agent_forge.utils.message_bus import MessageBus
from agent_forge.utils.interaction_logger import InteractionLogger
from agent_forge.agents.strategy_agents import MomentumTrader, MeanReversionTrader
from agent_forge.core.financial_risk import SystemicRiskMonitor

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GoldenMasterCapture")

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
GOLDEN_ROOT = os.path.join("golden", TIMESTAMP)

def setup_golden_dir(scenario_name):
    path = os.path.join(GOLDEN_ROOT, scenario_name)
    os.makedirs(path, exist_ok=True)
    return path

def save_metadata(path, config):
    with open(os.path.join(path, "metadata.json"), "w") as f:
        json.dump(config, f, indent=2)

def save_final_state(path, state_data):
    # Convert sets to lists if present, etc.
    with open(os.path.join(path, "final_state.json"), "w") as f:
        json.dump(state_data, f, default=str, indent=2)

# --- Scenario 1: Single Agent Grid (Async) ---
async def run_single_agent_scenario():
    scenario_name = "single_agent_grid"
    logger.info(f"Starting {scenario_name}...")
    path = setup_golden_dir(scenario_name)
    
    # Deterministic Seed
    SEED = 42
    random.seed(SEED)
    # If numpy is used internally: np.random.seed(SEED)
    
    config = {
        "scenario": scenario_name,
        "seed": SEED,
        "steps": 20,
        "grid_size": 5
    }
    save_metadata(path, config)
    
    # Custom Logger for this run
    db_path = os.path.join(path, "interactions.db")
    log_file = os.path.join(path, "events.jsonl")
    interaction_logger = InteractionLogger(db_path=db_path, log_file=log_file)
    
    # Setup
    bus = MessageBus()
    await bus.start()
    
    env = GridWorld(size=config["grid_size"])
    model = GridDecisionModel(ModelConfig(input_size=4, output_size=4))
    
    agent_id = "GoldenAgent-01"
    # We prefer to use the agent's internal loop if possible, 
    # but for full control and logging, we'll manually step like in simulation_runner.py
    
    agent = LearningGridAgent(agent_id, bus, env, model)
    await agent.start()
    
    # Reset
    obs = env.reset(agent_id=agent_id)
    agent.state["current_position"] = obs
    
    final_state = {}
    
    try:
        for step in range(config["steps"]):
            current_pos = agent.state["current_position"]
            state_vector = agent._get_state_vector(current_pos, env.goal)
            action_idx = agent.select_action(state_vector)
            actions = ["UP", "DOWN", "LEFT", "RIGHT"]
            action_str = actions[action_idx]
            
            # Step
            obs, reward, done, info = env.step(action_str, agent_id=agent_id)
            
            # Log
            interaction_logger.log_interaction(
                agent_id=agent_id,
                action=action_str,
                state=current_pos, # Log PREVIOUS state or resulting state? Usually state->action. 
                reward=reward,
                metadata={"step": step, "done": done, "info": info}
            )
            
            # Update Agent
            agent.state["current_position"] = obs
            
            if done:
                logger.info(f"Agent reached goal at step {step}")
                final_state["reached_goal_step"] = step
                break
                
        final_state["final_position"] = obs
        final_state["total_steps"] = step + 1
        
    finally:
        await bus.stop()
        
    save_final_state(path, final_state)
    logger.info(f"Finished {scenario_name}")

# --- Scenario 2: Multi-Agent Finance (Sync) ---
def run_multi_agent_scenario():
    scenario_name = "multi_agent_finance"
    logger.info(f"Starting {scenario_name}...")
    path = setup_golden_dir(scenario_name)
    
    SEED = 12345
    random.seed(SEED)
    
    config = {
        "scenario": scenario_name,
        "seed": SEED,
        "steps": 50,
        "shock_step": 20
    }
    save_metadata(path, config)
    
    db_path = os.path.join(path, "interactions.db")
    log_file = os.path.join(path, "events.jsonl")
    interaction_logger = InteractionLogger(db_path=db_path, log_file=log_file)

    # Mock MB for sync agents
    class MockMessageBus:
        def register(self, agent_id): return "auth_token"
        async def publish(self, *args, **kwargs): pass
        def subscribe(self, *args): pass

    mb = MockMessageBus()
    
    env = OrderBookEnv(start_cash=1000000.0)
    
    # Agents
    agents = []
    # 2 Momentum, 2 MeanReversion
    for i in range(2):
        agents.append(MomentumTrader(f"Mom_{i}", 100000.0, message_bus=mb))
    for i in range(2):
        agents.append(MeanReversionTrader(f"Rev_{i}", 100000.0, message_bus=mb))
        
    # Init Portfolios
    for a in agents:
        env.portfolios[a.agent_id] = {'cash': 100000.0, 'inventory': 0}
        
    # MM for liquidity
    mm_id = "MarketMaker"
    env.portfolios[mm_id] = {'cash': 1e9, 'inventory': 10000}
    
    def run_mm():
        # Simple random MM
        mid = env._get_mid_price()
        snap = env.book.get_snapshot(depth=5)
        if len(snap['bids']) < 3:
            env.step({'type': 'LIMIT', 'side': 'BUY', 'price': mid - 1.0, 'quantity': 10, 'id': f'mm_b_{random.randint(0,1000000)}', 'agent_id': mm_id})
        if len(snap['asks']) < 3:
            env.step({'type': 'LIMIT', 'side': 'SELL', 'price': mid + 1.0, 'quantity': 10, 'id': f'mm_s_{random.randint(0,1000000)}', 'agent_id': mm_id})

    # Initial orders
    env.book.add_order('BUY', 99.0, 100, 'init_b', mm_id)
    env.book.add_order('SELL', 101.0, 100, 'init_s', mm_id)
    
    for t in range(config["steps"]):
        # MM
        run_mm()
        
        # Shock
        if t == config["shock_step"]:
            env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 150.0, 'quantity': 200, 'id': 'shock_buy', 'agent_id': 'Whale'})
            logger.info("Shock injected")
            interaction_logger.log_interaction("Whale", "SHOCK_BUY", {}, 0, {"price": 150.0, "qty": 200})

        obs = env._get_obs()
        random.shuffle(agents)
        
        for agent in agents:
            # We assume agent.decide() returns an action dict
            # Standardizing agent interface is part of refactor, but here we use what exists
            action = agent.decide(obs)
            
            # Use deterministic IDs if possible, or log what we got
            if action['type'] == 'LIMIT':
                action['id'] = f"{agent.agent_id}_{t}_{random.randint(100,999)}"
            
            # Step
            if action['type'] != 'HOLD':
                obs_res, _, _, info = env.step(action)
                
                interaction_logger.log_interaction(
                    agent_id=agent.agent_id,
                    action=action['type'],
                    state=obs['mid_price'],
                    reward=0,
                    metadata={"full_action": action, "info": info}
                )

    save_final_state(path, {
        "mid_price": env._get_mid_price(),
        "portfolios": env.portfolios
    })
    logger.info(f"Finished {scenario_name}")

# --- Scenario 3: Stress Scenario (Higher Volume) ---
def run_stress_scenario():
    scenario_name = "stress_test"
    logger.info(f"Starting {scenario_name}...")
    path = setup_golden_dir(scenario_name)
    
    SEED = 999
    random.seed(SEED)
    
    config = {
        "scenario": scenario_name,
        "seed": SEED,
        "steps": 100,
        "agents": 20
    }
    save_metadata(path, config)
    
    db_path = os.path.join(path, "interactions.db")
    log_file = os.path.join(path, "events.jsonl")
    interaction_logger = InteractionLogger(db_path=db_path, log_file=log_file)
    
    class MockMessageBus:
        def register(self, agent_id): return "auth_token"
        async def publish(self, *args, **kwargs): pass
        def subscribe(self, *args): pass
    
    mb = MockMessageBus()
    env = OrderBookEnv(start_cash=10000000.0)
    
    agents = []
    for i in range(config["agents"]):
        agents.append(MomentumTrader(f"StressBot_{i}", 100000.0, message_bus=mb))
        
    for a in agents:
        env.portfolios[a.agent_id] = {'cash': 100000.0, 'inventory': 0}
        
    env.book.add_order('BUY', 99.0, 5000, 'init_b', 'MM')
    env.book.add_order('SELL', 101.0, 5000, 'init_s', 'MM')
    
    # Run
    for t in range(config["steps"]):
        obs = env._get_obs()
        # No shock, just chaotic trading
        for agent in agents:
            # Force high activity? 
            # Normal logic for now, verifying determinism of "many agents"
            action = agent.decide(obs)
            if action['type'] == 'LIMIT':
                action['id'] = f"{agent.agent_id}_{t}_{random.randint(1000,9999)}"
                obs_res, _, _, info = env.step(action)
                if info.get('trades'):
                     interaction_logger.log_interaction(agent.agent_id, "TRADE", obs['mid_price'], 0, info)
                     
    save_final_state(path, env.portfolios)
    logger.info(f"Finished {scenario_name}")

# --- Scenario 4: Failure Scenario (Invalid Actions) ---
def run_failure_scenario():
    scenario_name = "failure_case"
    logger.info(f"Starting {scenario_name}...")
    path = setup_golden_dir(scenario_name)
    
    SEED = 666
    random.seed(SEED)
    
    config = {
        "scenario": scenario_name,
        "seed": SEED
    }
    save_metadata(path, config)
    
    db_path = os.path.join(path, "interactions.db")
    log_file = os.path.join(path, "events.jsonl")
    interaction_logger = InteractionLogger(db_path=db_path, log_file=log_file)
    
    env = OrderBookEnv()
    
    # 1. insufficient funds
    env.portfolios["BrokeBot"] = {'cash': 10.0, 'inventory': 0}
    
    # Action: Buy expensive
    action = {'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 5, 'id': 'fail_1', 'agent_id': 'BrokeBot'}
    obs, _, _, info = env.step(action)
    
    interaction_logger.log_interaction("BrokeBot", "FAIL_BUY", 0, 0, {"expected_error": True, "info": info})
    
    # 2. invalid schema (missing fields)
    try:
        env.step({'type': 'LIMIT', 'side': 'BUY'}) # Missing price/qty
    except Exception as e:
        interaction_logger.log_interaction("System", "CRASH_CATCH", 0, 0, {"error": str(e)})

    # 3. Short sell check (if enforced)
    env.portfolios["BearBot"] = {'cash': 1000.0, 'inventory': 0}
    action_short = {'type': 'LIMIT', 'side': 'SELL', 'price': 90.0, 'quantity': 10, 'id': 'fail_2', 'agent_id': 'BearBot'}
    obs, _, _, info = env.step(action_short)
    interaction_logger.log_interaction("BearBot", "FAIL_SHORT", 0, 0, {"info": info})
    
    save_final_state(path, {"final_logs": "Check events.jsonl for error objects"})
    logger.info(f"Finished {scenario_name}")

async def main():
    logger.info(f"Starting Golden Master Capture. Root: {GOLDEN_ROOT}")
    
    # Run Scenarios
    await run_single_agent_scenario()
    
    # Sync Scenarios
    run_multi_agent_scenario()
    run_stress_scenario()
    run_failure_scenario()
    
    logger.info("All scenarios completed.")
    print(f"Golden Master artifacts saved to: {GOLDEN_ROOT}")

if __name__ == "__main__":
    asyncio.run(main())
