import sys
import asyncio
import random
from typing import Callable, Any, Dict

# Import the Real Engine
from src.agent_forge.core.engine import SimulationEngine
from environments.warehouse_env import WarehouseEnv
from environments.order_book_env import OrderBookEnv

# Import Risk Monitors
from src.agent_forge.core.logistics_risk import LogisticsRiskMonitor
from src.agent_forge.core.financial_risk import FinancialRiskMonitor

async def run_vertical_test(
    vertical_name: str,
    env: Any,
    agent_id: str,
    action_fn: Callable[[Any], Any],
    dataset: Dict[str, Any],
    setup_fn: Callable[[Any], None] = None
) -> bool:
    """
    Runs a simulation using the core engine and checks if risk is detected.
    """
    print(f"\n--- Running Vertical: {vertical_name} ---")
    
    # 1. Setup Risk Monitor & Callback
    risk_monitor = dataset['monitor']
    risk_adapter = dataset['adapter']
    risk_detected = False
    
    async def on_step(update: Dict[str, Any]):
        nonlocal risk_detected
        obs = update['observation']
        agent = update['agent_id']
        
        # Adapt observation for the specific risk monitor
        risk_input = risk_adapter(obs, agent)
        
        # Check Risk
        try:
             violations = risk_monitor.check_risk(agent, risk_input)
        except TypeError:
            if isinstance(risk_input, tuple):
                violations = risk_monitor.check_risk(agent, *risk_input)
            else:
                violations = risk_monitor.check_risk(agent, risk_input)

        if violations:
            print(f"[RISK DETECTED] {vertical_name}: {violations[0]}")
            risk_detected = True
        
        # DEBUG
        if 'trades' in update.get('info', {}):
             trades = update['info']['trades']
             if trades:
                 print(f"DEBUG: {vertical_name} Trades: {len(trades)}")
    
    # 2. Init Engine (This calls env.reset())
    engine = SimulationEngine(env=env)
    engine.on_step_callback = on_step
    
    # 3. Post-Init Setup (Inject Liquidity etc.)
    if setup_fn:
        setup_fn(engine.env)
    
    # 4. Run Loop
    steps = 50
    for i in range(steps):
        state = await engine.get_state(agent_id)
        action = action_fn(state)
        await engine.perform_action(agent_id, action)
        
        if risk_detected:
            break
            
    if risk_detected:
        print(f"SUCCESS: {vertical_name} simulation correctly flagged risk.")
        return True
    else:
        print(f"FAILURE: {vertical_name} simulation finished without detecting risk.")
        return False

# --- Scenario 1: Logistics ---
def setup_logistics():
    env = WarehouseEnv(config={"battery_drain": 5.0}) 
    agent_id = "worker_1"
    risk_monitor = LogisticsRiskMonitor(min_battery=20.0)
    
    def action_fn(obs):
        return "UP" 
        
    def risk_adapter(obs, agent_id):
        return obs
        
    return {
        "name": "LOGISTICS (Warehouse)",
        "env": env,
        "agent_id": agent_id,
        "action_fn": action_fn,
        "dataset": {
            "monitor": risk_monitor,
            "adapter": risk_adapter
        },
        "setup_fn": None
    }

# --- Scenario 2: Finance ---
def setup_finance():
    env = OrderBookEnv(start_cash=100000.0)
    agent_id = "trader_1"
    
    def setup_liquidity(env_instance):
        trades1 = env_instance.book.add_order('BUY', 90.0, 1000, 'mm_b', 'mm')
        trades2 = env_instance.book.add_order('SELL', 100.0, 1000, 'mm_s', 'mm')
        print(f"DEBUG: Liquidity Injected. Asks: {len(env_instance.book.asks)}")

    risk_monitor = FinancialRiskMonitor(max_position=20, max_drawdown=0.05)
    
    def action_fn(obs):
        return {
            'type': 'LIMIT', 
            'side': 'BUY', 
            'price': 100.0, 
            'quantity': 25, 
            'id': f'b_{random.randint(0,1000000)}', 
            'agent_id': agent_id
        }
        
    def risk_adapter(obs, agent_id):
        portfolios = obs.get('portfolios', {})
        port = portfolios.get(agent_id, {'cash': 0, 'inventory': 0})
        mid_price = obs.get('mid_price', 100.0)
        return (port, mid_price)
        
    return {
        "name": "FINANCE (OrderBook)",
        "env": env,
        "agent_id": agent_id,
        "action_fn": action_fn,
        "dataset": {
            "monitor": risk_monitor,
            "adapter": risk_adapter
        },
        "setup_fn": setup_liquidity
    }

async def main():
    # Clear logs
    with open("finance_debug.txt", "w") as f: f.write("")
    
    # 1. Logistics
    log_setup = setup_logistics()
    r1 = await run_vertical_test(
        log_setup['name'], 
        log_setup['env'], 
        log_setup['agent_id'], 
        log_setup['action_fn'], 
        log_setup['dataset'],
        log_setup['setup_fn']
    )
    
    # 2. Finance
    fin_setup = setup_finance()
    r2 = await run_vertical_test(
        fin_setup['name'], 
        fin_setup['env'], 
        fin_setup['agent_id'], 
        fin_setup['action_fn'], 
        fin_setup['dataset'],
        fin_setup['setup_fn']
    )
    
    if r1 and r2:
        print("\nALL VERTICALS CONSISTENT.")
        sys.exit(0)
    else:
        print("\nCROSS-VERTICAL TEST FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"CRASH: {e}")
        sys.exit(1)
