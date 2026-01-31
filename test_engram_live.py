"""
Test script to demonstrate Engram TUI with live data
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agent_forge.core.engine import SimulationEngine
from agent_forge.envs.warehouse import WarehouseEnv
from agent_forge.ui.data_bridge import data_bridge
from agent_forge.core.justice_log import get_justice_logger


async def run_test_simulation():
    """Run a quick simulation to generate data for the TUI"""
    print("Starting test simulation...")
    
    # Create environment and engine
    env = WarehouseEnv(grid_size=10)
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
    
    # Get Justice Logger
    justice_log = get_justice_logger("engram_test.jsonl")
    
    # Initialize agent
    agent_id = "test-bot-01"
    await engine.reset()
    
    print(f"Running simulation with agent: {agent_id}")
    
    # Run a few steps
    for step in range(10):
        state = await engine.get_state(agent_id)
        
        # Simple action
        action = "MOVE_UP" if step % 2 == 0 else "STAY"
        success = await engine.perform_action(agent_id, action)
        
        # Log to Justice Log
        justice_log.log("SIMULATION_STEP", agent_id, {
            "step": step,
            "action": action,
            "success": success,
            "state": str(state)
        })
        
        if not success:
            print(f"Step {step}: Agent halted by compliance")
            break
        
        print(f"Step {step}: {action} - Success")
    
    # Print summary
    print("\n" + "=" * 60)
    print("SIMULATION COMPLETE")
    print("=" * 60)
    
    # Show data bridge stats
    status = data_bridge.get_simulation_status()
    print(f"Status: {status['status']}")
    print(f"Events Logged: {status['events_logged']}")
    
    risk_score = data_bridge.get_system_risk_score()
    print(f"System Risk Score: {risk_score:.1f}")
    
    agents = data_bridge.get_active_agents()
    print(f"Active Agents: {len(agents)}")
    for agent in agents:
        print(f"  - {agent['agent_id']}: Risk={agent['risk_score']} ({agent['risk_level']})")
    
    incidents = data_bridge.get_incidents()
    print(f"Incidents Detected: {len(incidents)}")
    for inc in incidents[:3]:  # Show first 3
        print(f"  - {inc['incident_id']}: {inc['fault_type']} (Preventability: {inc['preventability']}%)")
    
    # Verify Justice Log
    print("\n" + "=" * 60)
    print("JUSTICE LOG VERIFICATION")
    print("=" * 60)
    result = justice_log.verify_integrity()
    print(f"Valid: {result['valid']}")
    print(f"Total Entries: {result['total_entries']}")
    print(f"Message: {result['message']}")
    
    # Seal log
    manifest = justice_log.seal()
    print(f"\nLog sealed. Chain hash: {manifest['chain_hash'][:32]}...")
    
    print("\n" + "=" * 60)
    print("You can now launch the TUI to see this data:")
    print("  python engram.py tui")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_test_simulation())
