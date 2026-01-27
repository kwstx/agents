import pytest
from environments.order_book_env import OrderBookEnv
from src.agent_forge.core.financial_risk import FinancialRiskMonitor, RiskViolation

class TestRiskEnforcement:
    @pytest.fixture
    def setup(self):
        env = OrderBookEnv(start_cash=10000.0)
        risk_monitor = FinancialRiskMonitor(max_position=20, max_drawdown=0.10)
        return env, risk_monitor

    def test_max_position_violation(self, setup):
        env, risk_monitor = setup
        agent_id = "trader_1"
        mm_id = "market_maker"
        
        # Seed MM
        env.portfolios[mm_id] = {'cash': 10000.0, 'inventory': 1000}

        # 1. Buy 15 (Under limit 20)
        env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 15, 'id': 'ord1', 'agent_id': agent_id})
        _, _, _, info = env.step({'type': 'LIMIT', 'side': 'SELL', 'price': 100.0, 'quantity': 15, 'id': 'sell1', 'agent_id': mm_id})
        
        assert len(info['trades']) > 0, f"Trade 1 failed: {info}"
        
        portfolio = env.portfolios[agent_id]
        violations = risk_monitor.check_risk(agent_id, portfolio, 100.0)
        assert len(violations) == 0, "Should be safe"
        
        # 2. Buy 10 more (Total 25 > 20)
        env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 10, 'id': 'ord2', 'agent_id': agent_id})
        _, _, _, info = env.step({'type': 'LIMIT', 'side': 'SELL', 'price': 100.0, 'quantity': 10, 'id': 'sell2', 'agent_id': mm_id})
        
        assert len(info['trades']) > 0, f"Trade 2 failed: {info}"
        
        portfolio = env.portfolios[agent_id]
        violations = risk_monitor.check_risk(agent_id, portfolio, 100.0)
        
        assert len(violations) > 0, "Expected Position Limit Violation"
        assert violations[0]['type'] == RiskViolation.POSITION_LIMIT.value

    def test_drawdown_violation(self, setup):
        env, risk_monitor = setup
        agent_id = "trader_bad"
        mm_id = "mm"
        
        # Reset and Seed
        env.reset()
        # Explicitly seed agent logic (though start_cash default handles it, let's be explicit)
        env.portfolios[agent_id] = {'cash': 10000.0, 'inventory': 0}
        env.portfolios[mm_id] = {'cash': 10000.0, 'inventory': 1000}
        
        # Buy 100 @ 100 (Full Allocation)
        env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 100, 'id': 'b_all', 'agent_id': agent_id})
        _, _, _, info = env.step({'type': 'LIMIT', 'side': 'SELL', 'price': 100.0, 'quantity': 100, 'id': 's_all', 'agent_id': mm_id})
        
        assert len(info['trades']) > 0, f"Full Buy failed: {info}"
        assert env.portfolios[agent_id]['inventory'] == 100, "Inventory not updated"
        
        # Establish Peak
        portfolio = env.portfolios[agent_id]
        risk_monitor.peak_equity = {} # Ensure clean
        risk_monitor.check_risk(agent_id, portfolio, 100.0) 
        # Peak should be 10000
        
        # Crash to 50.0
        # Equity = 0 + (100 * 50) = 5000. Drawdown 5000/10000 = 50%
        violations = risk_monitor.check_risk(agent_id, portfolio, 50.0)
        
        assert len(violations) > 0, f"Expected Drawdown Violation. Equity: {portfolio.get('cash',0) + portfolio['inventory']*50.0}"
        assert violations[0]['type'] == RiskViolation.DRAWDOWN_LIMIT.value
