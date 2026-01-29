import asyncio
import random
import sys
import os

# Put root on path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typing import Dict, Any, List

from src.agent_forge.core.engine import SimulationEngine
from environments.order_book_env import OrderBookEnv
from src.agent_forge.core.financial_risk import FinancialRiskMonitor

# --- Agents ---

class MartingaleTrader:
    def __init__(self, agent_id: str, start_price: float):
        self.agent_id = agent_id
        self.position = 0
        self.base_qty = 10
        self.last_price = start_price
        
    def act(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Martingale Strategy:
        - If Price < Last Price (Dip): BUY (Double Down!)
        - If Price > Last Price (Rise): SELL (Take Profit) & Reset
        """
        mid_price = obs.get('mid_price', 100.0)
        action = None
        
        if mid_price < self.last_price:
            # DIP detected! Double down!
            qty = self.base_qty * 2
            self.base_qty = qty # Increase bet size for next time
            
            action = {
                'type': 'LIMIT', 'side': 'BUY', 'price': mid_price + 2.0, 
                'quantity': qty, 'id': f'martingale_{random.randint(0, 1000000)}', 'agent_id': self.agent_id
            }
        elif mid_price > self.last_price:
            # Profit! Reset
            self.base_qty = 10 
            action = {
                'type': 'LIMIT', 'side': 'SELL', 'price': mid_price, 
                'quantity': 10, 'id': f'profit_{random.randint(0, 1000000)}', 'agent_id': self.agent_id
            }
            
        self.last_price = mid_price
        return action

class MarketMaker:
    def __init__(self, engine: SimulationEngine):
        self.engine = engine
        self.id = "mm_God"
        self.current_mid = 100.0
        self.spread = 1.0
        
    async def set_price(self, mid_price: float):
        """Forces the market to a specific price band."""
        old_mid = self.current_mid
        self.current_mid = mid_price
        
        # 1. Clear the path (Aggressive)
        if mid_price < old_mid:
            # Moving Down: Sell into Bids
            await self.engine.perform_action(self.id, {
                'type': 'LIMIT', 'side': 'SELL', 'price': mid_price - 1.0, 
                'quantity': 1000000, 'id': f'mm_dump_{random.randint(0,1000000)}', 'agent_id': self.id
            })
        elif mid_price > old_mid:
            # Moving Up: Buy into Asks
            await self.engine.perform_action(self.id, {
                'type': 'LIMIT', 'side': 'BUY', 'price': mid_price + 1.0, 
                'quantity': 1000000, 'id': f'mm_pump_{random.randint(0,1000000)}', 'agent_id': self.id
            })

        # 2. Set new band (Passive)
        # Ask
        await self.engine.perform_action(self.id, {
            'type': 'LIMIT', 'side': 'SELL', 'price': mid_price + (self.spread/2), 
            'quantity': 1000, 'id': f'mm_s_{random.randint(0,1000000)}', 'agent_id': self.id
        })
        # Bid
        await self.engine.perform_action(self.id, {
            'type': 'LIMIT', 'side': 'BUY', 'price': mid_price - (self.spread/2), 
            'quantity': 1000, 'id': f'mm_b_{random.randint(0,1000000)}', 'agent_id': self.id
        })

async def run_scenario(name: str, crash_market: bool):
    log_file = "kill_switch_results.txt"
    with open(log_file, "a") as f:
        f.write(f"\n=== SCENARIO: {name} ===\n")
    
    # 1. Setup
    env = OrderBookEnv(start_cash=100000.0)
    engine = SimulationEngine(env=env)
    
    mm = MarketMaker(engine)
    
    # SEED MM with Infinite Resources
    env.portfolios["mm_God"] = {'cash': 1e12, 'inventory': 1e12}
    
    trader = MartingaleTrader("risky_bot", start_price=100.0)
    
    # Risk Monitor: Strict
    risk_monitor = FinancialRiskMonitor(max_position=500, max_drawdown=0.10)
    risk_violation = None

    async def on_step(update):
        nonlocal risk_violation
        agent = update['agent_id']
        obs = update['observation']
        
        if agent == trader.agent_id:
            port = obs['portfolios'].get(agent, {'cash': 0, 'inventory': 0})
            mid = obs['mid_price']
            
            # Check Risk
            violations = risk_monitor.check_risk(agent, port, mid)
            if violations:
                risk_violation = violations[0]
                with open(log_file, "a") as f:
                    f.write(f"!!! KILL SWITCH TRIGGERED: {risk_violation['type']} !!!\n")
                    f.write(f"   Reason: {risk_violation['details']}\n")

    engine.on_step_callback = on_step
    
    # 2. Run Loop
    prices = [100.0] * 5
    if crash_market:
        # CRASH
        crash_curve = [100.0 - (i * 5.0) for i in range(15)] 
        prices += crash_curve
    else:
        # CALM
        calm_curve = [100.0 + (random.uniform(-1, 1)) for i in range(15)]
        prices += calm_curve
        
    for t, price in enumerate(prices):
        if risk_violation:
            break
            
        with open(log_file, "a") as f:
             f.write(f"Step {t}: Market Price {price}\n")
        
        # MM Moves (Async)
        await mm.set_price(price)
        
        # Trader Moves
        state = await engine.get_state(trader.agent_id)
        # Log Logic check
        port = env.portfolios.get(trader.agent_id, {'cash': 0, 'inventory': 0})
        with open(log_file, "a") as f:
             f.write(f"   Trader State: Price={state.get('mid_price')} Pos={port['inventory']} BaseQty={trader.base_qty}\n")

        action = trader.act(state)
        
        if action:
            await engine.perform_action(trader.agent_id, action)
            
    # 3. Report
    with open(log_file, "a") as f:
        if risk_violation:
            f.write(f"RESULT: BLOCKED. System correctly identified risk.\n")
            return False # Killed
        else:
            # Check profitability
            port = env.portfolios.get(trader.agent_id, {'cash': 100000, 'inventory': 0})
            mid = env._get_mid_price()
            equity = port['cash'] + (port['inventory'] * mid)
            profit = equity - 100000
            f.write(f"RESULT: SURVIVED. Final Profit/Loss: ${profit:.2f}\n")
            return True # Survived

async def main():
    try:
        print("--- TRUST KILL TEST START ---")
        
        # 1. Calm Run (Should Survive & Profit/Break-even)
        survived_calm = await run_scenario("CALM MARKET", crash_market=False)
        
        if not survived_calm:
            print("TEST FAILURE: Valid agent blocked in calm market.")
            sys.exit(1)
            
        # 2. Crash Run (Should Fail/Block)
        survived_crash = await run_scenario("CRITICAL CRASH", crash_market=True)
        
        if not survived_crash:
            print("\nTEST SUCCESS: Risky agent blocked during crash.")
            sys.exit(0)
        else:
            print("\nTEST FAILURE: Risky agent NOT blocked during crash.")
            sys.exit(1)
    except Exception as e:
        import traceback
        with open("kill_switch_results.txt", "a") as f:
            f.write(f"\nCRASHED UNEXPECTEDLY: {e}\n")
            f.write(traceback.format_exc())
        print(f"CRASHED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
