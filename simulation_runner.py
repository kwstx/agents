import asyncio
import json
import logging
import os
import random
import time
import csv
from datetime import datetime

from agents.learning_agent import LearningGridAgent
from models.decision_model import GridDecisionModel, ModelConfig
from environments.grid_world import GridWorld
from environments.simulation_engine import SimulationEngine
from utils.message_bus import MessageBus

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SimulationRunner")

CONTROL_FILE = "control.json"
METRICS_FILE = "logs/learning_metrics.csv"
EVENT_LOG = "logs/simulation_events.jsonl"

def load_control():
    try:
        with open(CONTROL_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read control file: {e}")
        return {"status": "STOPPED", "stress_config": {}, "agent_params": {}}

def init_logs():
    os.makedirs("logs", exist_ok=True)
    # Initialize learning metrics CSV
    if not os.path.exists(METRICS_FILE):
        with open(METRICS_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "step", "agent_id", "epsilon", "reward"])

    # Initialize event log
    if not os.path.exists(EVENT_LOG):
        # Just create the file or append to it
        pass

def log_learning_metric(step, agent_id, epsilon, reward):
    with open(METRICS_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().isoformat(), step, agent_id, epsilon, reward])

class MetricsHook:
    def on_step_end(self, agent, state, action, reward, next_state, done):
        # Log to CSV
        log_learning_metric(agent.steps, agent.agent_id, agent.epsilon, reward)
        return None

async def run_simulation_loop():
    args = parse_args()
    
    init_logs()
    
    logger.info(f"Starting Simulation with {args.agent_count} agents in {args.env_size}x{args.env_size} world.")
    
    # Initialize components
    bus = MessageBus()
    await bus.start()
    system_token = bus.register("System")
    
    env = GridWorld(size=args.env_size)
    model = GridDecisionModel(ModelConfig(input_size=4, output_size=4)) # UP, DOWN, LEFT, RIGHT
    
    # We use a custom runner loop instead of agent._navigate_to_goal to allow external control
    # So we create the agent but might control it step-by-step
    # However, existing agent logic is loop-based. 
    # Let's start the agent and let it run, but we need to inject the control checks inside the loop?
    # Or cleaner: The Runner *is* the main loop, and drives the agent.
    
    # Agent wrapper for step execution
    engine = SimulationEngine(env, stress_config={})
    
    # Re-using LearningGridAgent logic but step-wise
    # To do this cleanly without rewriting the agent entirely, let's just make the agent check control params
    # But `LearningGridAgent._navigate_to_goal` is a `while` loop.
    # Let's subclass or monkeykey-patch `LearningGridAgent` or just modify `LearningGridAgent` to be controllable.
    # For MVP, I'll modify LearningGridAgent to accept a 'controller' callback or just read the config.
    
    # Actually, the plan was to "execute step" in the runner. 
    # So let's instantiate the agent but NOT call `start()`. Instead, we manually step it.
    
    # Create Multiple Agents
    agents = []
    
    # Simple Factory
    for i in range(args.agent_count):
        agent_id = f"Agent-{i+1}"
        if args.agent_type == "collaborative":
            from agents.collaborative_agent import CollaborativeExplorerAgent
            agent = CollaborativeExplorerAgent(agent_id, bus, env)
            agents.append(agent)
        else:
            # Default Learning Agent
            agent = LearningGridAgent(agent_id, bus, env, model, hooks=[MetricsHook()])
            agents.append(agent)
            
    # Start agents (register subscriptions etc)
    for agent in agents:
        await agent.start()
    
    # Initial Reset for all
    for agent in agents:
        obs = env.reset(agent_id=agent.agent_id)
        agent.state["current_position"] = obs
        agent.steps = 0
    
    logger.info(f"Simulation initialized with {args.agent_type} agents. Waiting for START command...")

    while True:
        try:
            config = load_control()
            status = config.get("status", "STOPPED")
            
            if status == "STOPPED":
                await asyncio.sleep(1)
                continue
                
            if status == "PAUSED":
                await asyncio.sleep(0.5)
                continue
            
            if status == "RUNNING":
                # Update Parameters
                stress_config = config.get("stress_config", {})
                params = config.get("agent_params", {})
                
                # Update engine stress
                engine.stress_config = stress_config
                
                # Update MessageBus Chaos
                latency_ms = stress_config.get("latency_ms", 0)
                drop_rate = stress_config.get("drop_rate", 0.0)
                if latency_ms > 0 or drop_rate > 0:
                    bus.set_chaos(latency_min=0, latency_max=latency_ms/1000.0, drop_rate=drop_rate)
                
                # EXECUTE STEP for EACH AGENT
                await engine._apply_stress() # Apply global stress (latency)
                
                for agent in agents:
                    # Update agent params
                    if hasattr(agent, "epsilon") and "epsilon" in params:
                        agent.epsilon = float(params["epsilon"]) 
                    
                    # 1. Select Action
                    if not agent.state.get("done", False):
                        current_x, current_y = agent.state["current_position"]
                        
                        # Polymorphic Action Selection
                        if isinstance(agent, LearningGridAgent):
                            state_vector = agent._get_state_vector((current_x, current_y), env.goal)
                            action_idx = agent.select_action(state_vector) 
                            actions = ["UP", "DOWN", "LEFT", "RIGHT"]
                            action = actions[action_idx]
                        elif hasattr(agent, "select_action"):
                            # Collaborative Agent takes pos
                             action = agent.select_action((current_x, current_y))
                        else:
                             action = "STAY"
                        
                        # 2. Step Environment
                        start_time = time.time()
                        obs, reward, done, info = env.step(action, agent_id=agent.agent_id)
                        
                        # Failures?
                        if "failure_rate" in stress_config and random.random() < stress_config["failure_rate"]:
                            logging.error(f"Simulated Failure for {agent.agent_id}!")
                            with open(EVENT_LOG, "a") as f:
                                f.write(json.dumps({"timestamp": datetime.now().isoformat(), "type": "ERROR", "msg": f"Simulated Failure {agent.agent_id}"}) + "\n")
                            reward = -10
                        
                        # Update Agent State
                        agent.state["current_position"] = obs
                        agent.steps += 1
                        
                        # Collaborative Callback
                        if hasattr(agent, "on_step_complete"):
                            await agent.on_step_complete(obs)
                            
                        # LEARNING STEP
                        if isinstance(agent, LearningGridAgent):
                             next_state_vector = agent._get_state_vector(obs, env.goal)
                             agent.learn_from_step(state_vector, action_idx, reward, next_state_vector, done)
                        
                        # Log Metric
                        epsilon_val = getattr(agent, "epsilon", 0.0)
                        log_learning_metric(agent.steps, agent.agent_id, epsilon_val, reward)
                        
                        # If done, reset just this agent? or mark done?
                        # For continuous sim, let's reset this agent
                        if done:
                            if hasattr(agent, "on_episode_end"):
                                agent.on_episode_end()
                                
                            obs = env.reset(agent_id=agent.agent_id)
                            agent.state["current_position"] = obs
                            logger.info(f"Agent {agent.agent_id} reached goal! Resetting.")
                            # Optional: Send finding to other agents?
                            await bus.publish("goal_reached", "System", {"agent_id": agent.agent_id, "pos": env.goal}, auth_token=system_token)
                
                # Render periodically or just log?
                # env.render() # Spammy if too fast
                
                await asyncio.sleep(0.1) # Throttle slightly
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Simulation Loop Error: {e}")
            time.sleep(1)

    await bus.stop()

def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="Run simulation runner")
    parser.add_argument("--agent_count", type=int, default=2, help="Number of agents")
    parser.add_argument("--env_size", type=int, default=10, help="Size of grid world")
    parser.add_argument("--agent_type", type=str, default="learning", help="Type of agent: learning, collaborative")
    return parser.parse_args()

if __name__ == "__main__":
    asyncio.run(run_simulation_loop())
