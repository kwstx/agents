"""
Test script for Engram GUI
Runs a simulation and starts the FastAPI server for the GUI
"""

import asyncio
import sys
import os
from threading import Thread
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agent_forge.core.engine import SimulationEngine
from agent_forge.envs.warehouse import WarehouseEnv
from agent_forge.ui.data_bridge import data_bridge
from agent_forge.api.gui_server import start_server


async def run_simulation():
    """Run a continuous simulation for the GUI"""
    print("Starting simulation...")
    
    # Create environment and engine
    env = WarehouseEnv(size=10, num_agents=3)
    engine = SimulationEngine(
        env=env,
        stress_config={
            "latency_rate": 0.3,
            "latency_range": (0.5, 2.0),
            "seed": 42
        }
    )
    
    # Set engine in data bridge
    data_bridge.set_engine(engine)
    
    # Initialize agents
    agent_ids = ["bot-01", "bot-02", "bot-03"]
    
    print(f"Initializing {len(agent_ids)} agents...")
    engine.reset()
    
    # Run simulation loop
    step = 0
    while True:
        step += 1
        print(f"\n=== Step {step} ===")
        
        for agent_id in agent_ids:
            try:
                state = await engine.get_state(agent_id)
                
                # Simple action logic
                if step % 3 == 0:
                    action = "MOVE_UP"
                elif step % 3 == 1:
                    action = "MOVE_RIGHT"
                else:
                    action = "STAY"
                
                success = await engine.perform_action(agent_id, action)
                
                if success:
                    print(f"  {agent_id}: {action} ✓")
                else:
                    print(f"  {agent_id}: {action} ✗ (halted by compliance)")
                    
            except Exception as e:
                print(f"  {agent_id}: Error - {e}")
        
        # Show current risk score
        risk_score = data_bridge.get_system_risk_score()
        print(f"  System Risk: {risk_score:.1f}")
        
        # Wait before next step
        await asyncio.sleep(2)


def start_backend_server():
    """Start the FastAPI server in a separate thread"""
    print("Starting FastAPI server on http://127.0.0.1:8765")
    start_server(host="127.0.0.1", port=8765)


if __name__ == "__main__":
    print("=" * 60)
    print("ENGRAM GUI TEST")
    print("=" * 60)
    print()
    print("This script will:")
    print("1. Start the FastAPI backend server on port 8765")
    print("2. Run a continuous simulation with 3 agents")
    print("3. Generate live data for the GUI")
    print()
    print("Open the GUI at: http://localhost:1420")
    print("Press Ctrl+C to stop")
    print()
    print("=" * 60)
    print()
    
    # Start backend server in a separate thread
    server_thread = Thread(target=start_backend_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    time.sleep(2)
    
    # Run simulation
    try:
        asyncio.run(run_simulation())
    except KeyboardInterrupt:
        print("\n\nSimulation stopped by user")
        print("=" * 60)
