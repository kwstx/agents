from environments.order_book_env import OrderBookEnv
from src.agent_forge.core.financial_risk import FinancialRiskMonitor, RiskViolation
import sys

def run_tests():
    print("Running Manual Risk Tests...")
    failures = []

    # Test 1: Max Position
    try:
        print("Test 1: Max Position Violation...")
        env = OrderBookEnv(start_cash=10000.0)
        risk_monitor = FinancialRiskMonitor(max_position=20, max_drawdown=0.10)
        agent_id = "trader_1"
        mm_id = "market_maker"
        env.portfolios[mm_id] = {'cash': 10000.0, 'inventory': 1000}

        # 1. Buy 15 (Safe)
        env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 15, 'id': 'ord1', 'agent_id': agent_id})
        env.step({'type': 'LIMIT', 'side': 'SELL', 'price': 100.0, 'quantity': 15, 'id': 'sell1', 'agent_id': mm_id})
        
        # 2. Buy 10 More (Total 25 > 20)
        env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 10, 'id': 'ord2', 'agent_id': agent_id})
        env.step({'type': 'LIMIT', 'side': 'SELL', 'price': 100.0, 'quantity': 10, 'id': 'sell2', 'agent_id': mm_id})

        portfolio = env.portfolios[agent_id]
        violations = risk_monitor.check_risk(agent_id, portfolio, 100.0)
        
        if not violations:
            failures.append("Test 1 Failed: No violations detected for position 25 > 20")
        elif violations[0]['type'] != RiskViolation.POSITION_LIMIT.value:
            failures.append(f"Test 1 Failed: Wrong violation type {violations[0]['type']}")
        else:
            print("Test 1 Passed.")
            
    except Exception as e:
        failures.append(f"Test 1 Crashed: {e}")

    # Test 2: Drawdown
    try:
        print("Test 2: Drawdown Violation...")
        env = OrderBookEnv(start_cash=10000.0)
        risk_monitor = FinancialRiskMonitor(max_position=100, max_drawdown=0.10)
        agent_id = "trader_bad"
        mm_id = "mm"
        env.portfolios[mm_id] = {'cash': 10000.0, 'inventory': 1000}
        
        # Buy 100 @ 100
        env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 100, 'id': 'b_all', 'agent_id': agent_id})
        env.step({'type': 'LIMIT', 'side': 'SELL', 'price': 100.0, 'quantity': 100, 'id': 's_all', 'agent_id': mm_id})
        
        portfolio = env.portfolios[agent_id]
        # Peak
        risk_monitor.check_risk(agent_id, portfolio, 100.0)
        
        # Crash to 50
        violations = risk_monitor.check_risk(agent_id, portfolio, 50.0)
        
        if not violations:
            failures.append(f"Test 2 Failed: No violations for 50% drawdown. Port: {portfolio}")
        elif violations[0]['type'] != RiskViolation.DRAWDOWN_LIMIT.value:
             failures.append(f"Test 2 Failed: Wrong violation type {violations[0]['type']}")
        else:
             print("Test 2 Passed.")
             
    except Exception as e:
        failures.append(f"Test 2 Crashed: {e}")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f)
        sys.exit(1)
    else:
        print("\nALL MANUAL TESTS PASSED")
        sys.exit(0)

if __name__ == "__main__":
    run_tests()
