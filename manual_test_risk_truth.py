from environments.order_book_env import OrderBookEnv
from src.agent_forge.core.financial_risk import FinancialRiskMonitor, RiskViolation
import sys

def manual_test():
    print("Starting Manual Risk Truth Tests...")
    failures = []

    # Test 1: Cash Exhaustion
    try:
        print("T1: Cash Exhaustion")
        env = OrderBookEnv(start_cash=100000.0)
        env.portfolios['mm'] = {'cash': 1e9, 'inventory': 10000}
        agent_id = "spender"
        
        # Invest almost all cash (99,900)
        env.portfolios[agent_id] = {'cash': 100000.0, 'inventory': 0}
        env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 999, 'id': 'big_buy', 'agent_id': agent_id})
        env.step({'type': 'LIMIT', 'side': 'SELL', 'price': 100.0, 'quantity': 999, 'id': 'mm_s', 'agent_id': 'mm'})
        
        # Remaining should be 100.0
        cash = env.portfolios[agent_id]['cash']
        if abs(cash - 100.0) > 0.01:
            failures.append(f"T1 Failed: Cash wrong. Expected 100.0, Got {cash}")
            
        # Try to buy 2 @ 100 (Cost 200) -> Should Fail
        _, _, _, info = env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 2, 'id': 'fail', 'agent_id': agent_id})
        
        if 'rejected' not in info or not info['rejected']:
            failures.append("T1 Failed: Order not rejected due to insufficient cash.")
        else:
            print("T1 Passed.")
            
    except Exception as e:
        failures.append(f"T1 Crashed: {e}")

    # Test 2: Margin Call Threshold
    try:
        print("T2: Margin Call Threshold")
        env = OrderBookEnv(start_cash=100000.0)
        risk_monitor = FinancialRiskMonitor(max_position=1000, max_drawdown=0.10)
        agent_id = "risky"
        env.portfolios['mm'] = {'cash': 1e9, 'inventory': 10000}
        
        # Buy 1000 @ 100 (100k invested). Cash 0.
        env.portfolios[agent_id] = {'cash': 100000.0, 'inventory': 0}
        env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 1000, 'id': 'b1', 'agent_id': agent_id})
        env.step({'type': 'LIMIT', 'side': 'SELL', 'price': 100.0, 'quantity': 1000, 'id': 'mm1', 'agent_id': 'mm'})
        
        portfolio = env.portfolios[agent_id]
        risk_monitor.check_risk(agent_id, portfolio, 100.0) # Set peak 100k
        
        # 9.99% Drop -> 90.01
        violations = risk_monitor.check_risk(agent_id, portfolio, 90.01)
        if violations:
            failures.append(f"T2 Failed: Safe drop triggered violation: {violations}")

        # 10.01% Drop -> 89.99
        violations = risk_monitor.check_risk(agent_id, portfolio, 89.99)
        if not violations:
            failures.append("T2 Failed: Violation drop DID NOT trigger violation.")
        elif violations[0]['type'] != RiskViolation.DRAWDOWN_LIMIT.value:
            failures.append(f"T2 Failed: Wrong violation type: {violations[0]['type']}")
        else:
            print("T2 Passed.")
            
    except Exception as e:
        failures.append(f"T2 Crashed: {e}")

    # Test 3: Simulation Halt
    try:
        print("T3: Sim Halt Mock")
        env = OrderBookEnv(start_cash=100000.0)
        risk_monitor = FinancialRiskMonitor(max_position=1000, max_drawdown=0.10)
        agent_id = "crasher"
        env.portfolios[agent_id] = {'cash': 100000.0, 'inventory': 0}
        env.portfolios['mm'] = {'cash': 1e9, 'inventory': 10000}
        
        # Position
        env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 1000, 'id': 'b1', 'agent_id': agent_id})
        env.step({'type': 'LIMIT', 'side': 'SELL', 'price': 100.0, 'quantity': 1000, 'id': 'mm1', 'agent_id': 'mm'})
        risk_monitor.check_risk(agent_id, env.portfolios[agent_id], 100.0)
        
        running = True
        step_count = 0
        price_feed = [100.0, 95.0, 90.01, 89.99, 85.0]
        
        for p in price_feed:
            if not running: break
            step_count += 1
            if risk_monitor.check_risk(agent_id, env.portfolios[agent_id], p):
                running = False
        
        if step_count != 4:
             failures.append(f"T3 Failed: Processed {step_count} steps, expected 4.")
        else:
             print("T3 Passed.")
             
    except Exception as e:
        failures.append(f"T3 Crashed: {e}")

    if failures:
        print("\nFAILURES:")
        for f in failures: print(f)
        sys.exit(1)
    else:
        print("\nALL TRUTH TESTS PASSED")

if __name__ == "__main__":
    manual_test()
