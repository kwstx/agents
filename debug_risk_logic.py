from environments.order_book_env import OrderBookEnv
from src.agent_forge.core.financial_risk import FinancialRiskMonitor, RiskViolation

def debug_risk():
    print("Setting up...")
    env = OrderBookEnv(start_cash=10000.0)
    risk_monitor = FinancialRiskMonitor(max_position=20, max_drawdown=0.10)
    agent_id = "trader_1"

    print("Step 1: Buy 15")
    # Seed MM
    env.portfolios['mm'] = {'cash': 10000.0, 'inventory': 1000}
    env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 15, 'id': 'ord1', 'agent_id': agent_id})
    env.step({'type': 'LIMIT', 'side': 'SELL', 'price': 100.0, 'quantity': 15, 'id': 'sell1', 'agent_id': 'mm'})
    
    portfolio = env._get_obs()['portfolios'][agent_id]
    print(f"Portfolio after step 1: {portfolio}")
    
    violations = risk_monitor.check_risk(agent_id, portfolio, 100.0)
    print(f"Violations 1: {violations}")
    
    print("Step 2: Buy 10 more")
    env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 10, 'id': 'ord2', 'agent_id': agent_id})
    env.step({'type': 'LIMIT', 'side': 'SELL', 'price': 100.0, 'quantity': 10, 'id': 'sell2', 'agent_id': 'mm'})
    
    portfolio = env._get_obs()['portfolios'][agent_id]
    print(f"Portfolio after step 2: {portfolio}")
    
    violations = risk_monitor.check_risk(agent_id, portfolio, 100.0)
    print(f"Violations 2: {violations}")
    
    if len(violations) > 0 and violations[0]['type'] == RiskViolation.POSITION_LIMIT.value:
        print("SUCCESS: Position Limit Caught")
    else:
        print("FAILURE: Position Limit NOT Caught")

    # Drawdown Test
    print("\n--- Drawdown Test ---")
    env.reset() # Wipes portfolios
    # Re-init manually for clarity? No, step does it. 
    # But start_cash is 10000.
    
    print("Step 3: Buy 100 @ 100 (Full allocation)")
    # OrderBookEnv default start_cash is 10000 passed in init? Yes.
    env.portfolios['mm'] = {'cash': 10000.0, 'inventory': 1000}
    env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 100, 'id': 'b_all', 'agent_id': agent_id})
    env.step({'type': 'LIMIT', 'side': 'SELL', 'price': 100.0, 'quantity': 100, 'id': 's_all', 'agent_id': 'mm'})
    
    portfolio = env._get_obs()['portfolios'][agent_id]
    print(f"Portfolio after full buy: {portfolio}")
    
    # Peak logic
    risk_monitor.peak_equity = {} # Reset
    risk_monitor.check_risk(agent_id, portfolio, 100.0)
    print(f"Peak Equity: {risk_monitor.peak_equity.get(agent_id)}")
    
    print("Step 4: Crash to 89")
    violations = risk_monitor.check_risk(agent_id, portfolio, 89.0)
    print(f"Violations at 89: {violations}")
    
    if len(violations) > 0 and violations[0]['type'] == RiskViolation.DRAWDOWN_LIMIT.value:
         print("SUCCESS: Drawdown Caught")
    else:
         print("FAILURE: Drawdown NOT Caught")

if __name__ == "__main__":
    try:
        debug_risk()
    except Exception as e:
        print(f"CRASHED: {e}")
        import traceback
        traceback.print_exc()
