import sys
import os

sys.path.append(os.getcwd())

try:
    print("Attempting to import environments.robotics_sim...")
    import environments.robotics_sim
    print("Success: environments.robotics_sim")
except Exception as e:
    print(f"FAIL: environments.robotics_sim: {e}")

try:
    print("Attempting to import agents.finance_agent...")
    import agents.finance_agent
    print("Success: agents.finance_agent")
except Exception as e:
    print(f"FAIL: agents.finance_agent: {e}")
