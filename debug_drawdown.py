from environments.order_book_env import OrderBookEnv
from src.agent_forge.core.financial_risk import FinancialRiskMonitor, RiskViolation

def test_drawdown():
    env = OrderBookEnv(start_cash=10000.0)
    risk_monitor = FinancialRiskMonitor(max_position=20, max_drawdown=0.10)
    agent = "a"
    mm = "mm"
    
    env.portfolios[agent] = {'cash': 10000.0, 'inventory': 0}
    env.portfolios[mm] = {'cash': 10000.0, 'inventory': 1000}
    
    # Trade
    env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 100, 'id': 'b', 'agent_id': agent})
    env.step({'type': 'LIMIT', 'side': 'SELL', 'price': 100.0, 'quantity': 100, 'id': 's', 'agent_id': mm})
    
    p = env.portfolios[agent]
    print(f"Port: {p}")
    
    # Establish Peak
    risk_monitor.check_risk(agent, p, 100.0)
    print(f"Peak: {risk_monitor.peak_equity[agent]}")
    
    # Check 89
    violations = risk_monitor.check_risk(agent, p, 89.0)
    print(f"Violations: {violations}")
    
    if violations:
        print("PASS")
    else:
        print("FAIL - No Violations")

test_drawdown()
