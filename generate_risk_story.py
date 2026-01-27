from environments.order_book_env import OrderBookEnv
from src.agent_forge.core.financial_risk import FinancialRiskMonitor, RiskViolation
import json
import logging

# Configure Logging to capture "Dashboard Events"
dashboard_log = []

def log_event(type, details, timestamp=None):
    event = {
        "timestamp": timestamp or len(dashboard_log),
        "type": type,
        "details": details
    }
    dashboard_log.append(event)
    print(f"[{type}] {details}")

def generate_story():
    print("Generating Risk Story...")
    
    # Setup
    env = OrderBookEnv(start_cash=100000.0)
    risk_monitor = FinancialRiskMonitor(max_position=1000, max_drawdown=0.10)
    agent_id = "risk_chaser"
    mm_id = "mm"
    
    env.portfolios[mm_id] = {'cash': 1e9, 'inventory': 10000}
    env.portfolios[agent_id] = {'cash': 100000.0, 'inventory': 0}
    
    # 1. Initial State
    log_event("STATE", f"Initial Cash: ${env.portfolios[agent_id]['cash']:.2f}")
    
    # 2. The Decision (Buy Aggressively)
    # Buy 1000 @ 100 (100k invested)
    log_event("DECISION", f"Agent {agent_id} decided to BUY 1000 shares at $100.00 (Full Allocation)")
    
    env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 1000, 'id': 'b1', 'agent_id': agent_id})
    env.step({'type': 'LIMIT', 'side': 'SELL', 'price': 100.0, 'quantity': 1000, 'id': 'mm1', 'agent_id': 'mm'})
    
    port = env.portfolios[agent_id]
    log_event("EXECUTION", f"Filled 1000 @ 100.00. Inventory: {port['inventory']}")
    
    # Establish Peak
    risk_monitor.check_risk(agent_id, port, 100.0)
    log_event("RISK_CHECK", f"Peak Equity established at $100,000. Drawdown Limit: 10%")
    
    # 3. Market Drift (The Setup)
    prices = [98.0, 95.0, 92.0]
    for p in prices:
        # Update Market Context
        log_event("MARKET", f"Price drifted to ${p:.2f}")
        
        # Check Risk (Safe)
        violations = risk_monitor.check_risk(agent_id, port, p)
        if not violations:
             # Calculate current DD for display
             peak = risk_monitor.peak_equity[agent_id]
             eq = port['cash'] + (port['inventory'] * p)
             dd = (peak - eq) / peak
             log_event("RISK_CHECK", f"Drawdown {dd:.2%} (Safe)")
    
    # 4. The Crash (The Failure)
    crash_price = 89.0
    log_event("MARKET", f"Price CRASHED to ${crash_price:.2f}")
    
    violations = risk_monitor.check_risk(agent_id, port, crash_price)
    
    if violations:
        v = violations[0]
        log_event("CRITICAL_FAILURE", f"RISK VIOLATION: {v['type']}. {v['details']}")
        log_event("SYSTEM", "Agent halted to prevent insolvency.")
    else:
        log_event("ERROR", "Expected failure but none occurred!")

    # Save Dashboard Data
    with open("dashboard_data.json", "w") as f:
        json.dump(dashboard_log, f, indent=2)
    
    print("Story generated and saved to dashboard_data.json")

if __name__ == "__main__":
    generate_story()
