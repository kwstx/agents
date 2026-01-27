import sys
from typing import Callable, Any
from environments.warehouse_env import WarehouseEnv
from environments.order_book_env import OrderBookEnv
from src.agent_forge.core.logistics_risk import LogisticsRiskMonitor
from src.agent_forge.core.financial_risk import FinancialRiskMonitor
import random

# --- The Universal Simulation Engine ---
def run_simulation(
    name: str, 
    env: Any, 
    agent_id: str, 
    action_fn: Callable[[Any], Any], 
    risk_monitor: Any, 
    risk_adapter: Callable[[Any], Any],
    steps: int = 50
):
    print(f"\n--- Running Vertical: {name} ---")
    observation = env.reset()
    
    risk_detected = False
    
    for t in range(steps):
        # 1. Agent Decision
        action = action_fn(observation)
        
        # 2. Environment Step
        # Handle API variance (OrderBook uses dict action, Warehouse uses str/dict)
        # Assuming env.step signature is roughly compatible or handled by action
        
        # Helper for different env signatures if needed
        if hasattr(env, 'portfolios'): # OrderBook
             observation, _, _, info = env.step(action)
        else: # Warehouse
             observation, _, _, info = env.step(action, agent_id=agent_id)
        
        # 3. Risk Check
        # Standardize input to risk monitor via adapter
        risk_input = risk_adapter(observation)
        violations = risk_monitor.check_risk(agent_id, risk_input)
        
        if violations:
            print(f"[STEP {t}] RISK VIOLATION: {violations[0]['type']} - {violations[0]['details']}")
            risk_detected = True
            break
            
    if risk_detected:
        print(f"SUCCESS: {name} simulation correctly flagged risk.")
        return True
    else:
        print(f"FAILURE: {name} simulation finished without detecting risk.")
        return False

# --- Scenario 1: Logistics ---
def test_logistics():
    env = WarehouseEnv(battery_drain=5.0) # Fast drain
    agent_id = "worker_1"
    risk_monitor = LogisticsRiskMonitor(min_battery=20.0)
    
    def action_fn(obs):
        return "UP" # Just move
        
    def risk_adapter(obs):
        # Obs in Warehouse is the state dict? Or we dig it out?
        # Env.step returns state for that agent in WarehouseEnv
        return obs # It IS the state dict
        
    return run_simulation("LOGISTICS (Warehouse)", env, agent_id, action_fn, risk_monitor, risk_adapter)

# --- Scenario 2: Finance ---
def test_finance():
    env = OrderBookEnv(start_cash=100000.0)
    agent_id = "trader_1"
    env.portfolios['mm'] = {'cash': 1e9, 'inventory': 10000}
    
    risk_monitor = FinancialRiskMonitor(max_position=100, max_drawdown=0.05)
    
    # Setup Liquidity for valid pricing
    env.book.add_order('BUY', 100.0, 1000, 'mm_b', 'mm')
    env.book.add_order('SELL', 100.0, 1000, 'mm_s', 'mm')
    
    def action_fn(obs):
        # Buy aggressively to hit position limit
        # Price 100. Limit 100. 
        # Buy 20 per step -> 5 steps to limit
        return {'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 25, 'id': f'b_{random.randint(0,1e6)}', 'agent_id': agent_id}
        
    def risk_adapter(obs):
        # Need to return (portfolio, price) for FinancialRiskMonitor?
        # Wait, check_risk takes (agent_id, portfolio, price).
        # But we standarized on (agent_id, risk_input).
        # We can't change the signature of FinancialRiskMonitor easily without breaking previous tests
        # So we wrap it? Or use a Lambda that calls it correctly?
        # The generic loop calls: `risk_monitor.check_risk(agent_id, risk_input)`
        # So specific monitor adapter must expect `risk_input`.
        # BUT FinancialRiskMonitor.check_risk expects 3 args.
        pass
    
    # Wrapper for Finance Monitor to match generic Loop Signature
    class FinanceMonitorWrapper:
        def __init__(self, monitor): self.monitor = monitor
        def check_risk(self, agent_id, input_data):
            port, price = input_data
            return self.monitor.check_risk(agent_id, port, price)
            
    wrapper = FinanceMonitorWrapper(risk_monitor)
    
    def risk_adapter(obs):
        port = obs['portfolios'][agent_id]
        mid = obs['mid_price']
        return (port, mid)
        
    return run_simulation("FINANCE (OrderBook)", env, agent_id, action_fn, wrapper, risk_adapter)

if __name__ == "__main__":
    p1 = test_logistics()
    p2 = test_finance()
    
    if p1 and p2:
        print("\nALL VERTICALS CONSISTENT.")
    else:
        print("\nCROSS-VERTICAL TEST FAILED.")
        sys.exit(1)
