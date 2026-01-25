import asyncio
import json
import logging
import os
import random
import time
import csv
from datetime import datetime

from agents.learning_agent import LearningGridAgent
from models.decision_model import GridDecisionModel
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
    init_logs()
    
    # Initialize components
    bus = MessageBus()
    await bus.start()
    
    env = GridWorld(size=10)
    model = GridDecisionModel(input_size=4, output_size=4) # UP, DOWN, LEFT, RIGHT
    
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
    
    agent = LearningGridAgent("Agent-007", bus, env, model, hooks=[MetricsHook()])
    # Initial Reset
    obs = env.reset()
    agent.state["current_position"] = obs
    agent.steps = 0
    
    logger.info("Simulation initialized. Waiting for START command...")

    while True:
        try:
            config = load_control()
            status = config.get("status", "STOPPED")
            
            if status == "STOPPED":
                time.sleep(1)
                continue
                
            if status == "PAUSED":
                time.sleep(0.5)
                continue
            
            if status == "RUNNING":
                # Update Parameters
                stress_config = config.get("stress_config", {})
                params = config.get("agent_params", {})
                
                # Update engine stress
                engine.stress_config = stress_config
                
                # Update agent params
                if "epsilon" in params:
                    agent.epsilon = float(params["epsilon"]) # Override epsilon
                
                # EXECUTE STEP
                await engine._apply_stress() # Apply global stress (latency)
                
                # 1. Select Action
                # Accessing internal method or copying logic from LearningGridAgent
                current_x, current_y = agent.state["current_position"]
                state_vector = agent._get_state_vector((current_x, current_y), env.goal)
                
                action_idx = agent.select_action(state_vector) # Need to expose this or replicate logic
                actions = ["UP", "DOWN", "LEFT", "RIGHT"]
                action = actions[action_idx]
                
                # 2. Step Environment via Engine (handles logging)
                # But engine.perform_action expects agent_id
                # And engine wrappers env. But agent has its own env reference.
                # Let's use the engine to step the env that the agent *also* has reference to (it's the same object)
                
                # Update engine env reference just in case? No, passed in init.
                
                # Perform Action
                start_time = time.time()
                obs, reward, done, info = env.step(action)
                
                # Failures?
                if "failure_rate" in stress_config and random.random() < stress_config["failure_rate"]:
                    logging.error("Simulated Failure Injection!")
                    # Log event
                    with open(EVENT_LOG, "a") as f:
                        f.write(json.dumps({"timestamp": datetime.now().isoformat(), "type": "ERROR", "msg": "Simulated Failure"}) + "\n")
                    # Don't update state? Or just penalty?
                    reward = -10
                
                # Update Agent State
                agent.state["current_position"] = obs
                agent.steps += 1
                
                # Log Metric
                log_learning_metric(agent.steps, agent.agent_id, agent.epsilon, reward)
                
                # If done, reset
                if done:
                    obs = env.reset()
                    agent.state["current_position"] = obs
                    logger.info("Episode finished. Resetting.")
                
                time.sleep(0.1) # Throttle slightly
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Simulation Loop Error: {e}")
            time.sleep(1)

    await bus.stop()

if __name__ == "__main__":
    asyncio.run(run_simulation_loop())
