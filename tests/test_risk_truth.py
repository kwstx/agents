import pytest
from environments.order_book_env import OrderBookEnv
from src.agent_forge.core.financial_risk import FinancialRiskMonitor, RiskViolation

class TestRiskTruth:
    @pytest.fixture
    def setup(self):
        env = OrderBookEnv(start_cash=100_000.0)
        risk_monitor = FinancialRiskMonitor(max_position=1000, max_drawdown=0.10) # 10% DD Limit
        return env, risk_monitor

    def test_cash_exhaustion(self, setup):
        """
        Agent attempts to buy more than they have cash for.
        Expect rejection.
        """
        env, _ = setup
        agent_id = "spender"
        
        # 1. Invest almost all cash
        # Cash 100k. Price 100. Buy 999 @ 100 = 99,900. Remaining 100.
        env.portfolios[agent_id] = {'cash': 100000.0, 'inventory': 0}
        
        # Need a matching side or just check pre-validation (Env checks pre-match now!)
        # Our OrderBookEnv checks 'portfolio['cash'] < cost' BEFORE matching.
        
        action = {'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 999, 'id': 'big_buy', 'agent_id': agent_id}
        obs, _, _, info = env.step(action)
        
        # Should be accepted (we assume no fill needed for cash deduction? 
        # WAIT. Standard logic: Cash deducted on FILL or HOLD?
        # In simple Env, usually deducted on Fill? Or Reserved on Order?
        # My implementation: `_process_trades` deducts cash. 
        # But `step` checks `if portfolio['cash'] < cost`.
        # IF cash is only deducted on fill, then I can place infinite orders if they don't fill?
        # Ah, the simple implementation only checks CURRENT cash vs COST.
        # It doesn't track "locked" cash. 
        # So to fail "Cash Exhaustion", I must actually SPEND the cash (Turn it into inventory).
        
        # So verify trades happen.
        # Seed MM
        env.portfolios['mm'] = {'cash': 1e9, 'inventory': 10000}
        env.step({'type': 'LIMIT', 'side': 'SELL', 'price': 100.0, 'quantity': 10000, 'id': 'mm_s', 'agent_id': 'mm'})
        
        # Check Fill
        assert len(info['trades']) > 0
        assert env.portfolios[agent_id]['cash'] == 100.0, f"Cash not drained correctly: {env.portfolios[agent_id]['cash']}"
        
        # 2. Try to buy 2 shares @ 100 (Cost 200 > 100)
        action_fail = {'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 2, 'id': 'fail_buy', 'agent_id': agent_id}
        _, _, _, info_fail = env.step(action_fail)
        
        # Expect Error / Rejection
        assert 'errors' in info_fail and "Insufficient Cash" in info_fail['errors']
        assert 'rejected' in info_fail and info_fail['rejected'] is True

    def test_margin_call_exact_threshold(self, setup):
        """
        Verify 10% Drawdown triggers at 10.01% but not 9.99%.
        """
        env, risk_monitor = setup
        agent_id = "risky"
        env.portfolios['mm'] = {'cash': 1e9, 'inventory': 10000}
        
        # 1. Enter Position
        # Cash 100k. Buy 1000 @ 100 = 100k.
        # Portfolio: Cash 0, Inv 1000. Peak Equity 100,000.
        env.portfolios[agent_id] = {'cash': 100000.0, 'inventory': 0}
        env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 1000, 'id': 'b1', 'agent_id': agent_id})
        env.step({'type': 'LIMIT', 'side': 'SELL', 'price': 100.0, 'quantity': 1000, 'id': 'mm1', 'agent_id': 'mm'})
        
        portfolio = env.portfolios[agent_id]
        risk_monitor.peak_equity = {} # Reset
        risk_monitor.check_risk(agent_id, portfolio, 100.0)
        assert risk_monitor.peak_equity[agent_id] == 100000.0
        
        # 2. Test Safe Drop (9.99%)
        # Drawdown = (Peak - Eq) / Peak. 0.0999 = (100k - Eq)/100k -> Eq = 100k * (1 - 0.0999) = 90010.
        # Price = 90010 / 1000 = 90.01.
        
        violations = risk_monitor.check_risk(agent_id, portfolio, 90.01)
        assert len(violations) == 0, f"Should be safe at 9.99% DD. Violations: {violations}"
        
        # 3. Test Violation Drop (10.01%)
        # Eq = 100k * (1 - 0.1001) = 89990.
        # Price = 89.99.
        
        violations = risk_monitor.check_risk(agent_id, portfolio, 89.99)
        assert len(violations) > 0, "Should have triggered Margin Call"
        assert violations[0]['type'] == RiskViolation.DRAWDOWN_LIMIT.value

    def test_simulation_halt_on_critical_failure(self, setup):
        """
        Simulate a loop that should break on failure.
        """
        env, risk_monitor = setup
        agent_id = "crasher"
        env.portfolios['mm'] = {'cash': 1e9, 'inventory': 10000}
        
        # Setup Risk State (Full allocation)
        env.portfolios[agent_id] = {'cash': 100000.0, 'inventory': 0}
        env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 1000, 'id': 'b1', 'agent_id': agent_id})
        env.step({'type': 'LIMIT', 'side': 'SELL', 'price': 100.0, 'quantity': 1000, 'id': 'mm1', 'agent_id': 'mm'})
        risk_monitor.check_risk(agent_id, env.portfolios[agent_id], 100.0)
        
        # Simulation Loop Mock
        running = True
        price_feed = [100.0, 95.0, 90.01, 89.99, 85.0] # 89.99 triggers
        step_count = 0
        failure_detected = False
        
        for price in price_feed:
            if not running:
                break
            
            step_count += 1
            # Check Risk
            violations = risk_monitor.check_risk(agent_id, env.portfolios[agent_id], price)
            if violations:
                # Stop Logic
                running = False
                failure_detected = True
        
        # Verify
        assert failure_detected is True
        assert step_count == 4 # Should process 100, 95, 90.01, 89.99 then STOP. 85.0 never reached.
