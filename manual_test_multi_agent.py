from environments.order_book_env import OrderBookEnv
from agents.strategy_agents import MomentumTrader, MeanReversionTrader
from src.agent_forge.core.financial_risk import SystemicRiskMonitor
import random
import sys

def test_multi_agent_risk():
    print("Starting Multi-Agent Systemic Risk Test...")
    
    # Setup
    env = OrderBookEnv(start_cash=1000000.0)
    risk_monitor = SystemicRiskMonitor(vol_window=5, stress_threshold=0.1) # Extremely Sensitive threshold
    
    # Mock Message Bus
    class MockMessageBus:
        def register(self, agent_id): return "auth_token"
        def subscribe(self, topic, handler): pass
        def unsubscribe(self, topic, handler): pass
        async def publish(self, *args, **kwargs): pass

    mb = MockMessageBus()

    # Agents
    mm_id = "mm"
    mom_agents = [MomentumTrader(f"mom_{i}", 100000.0, message_bus=mb) for i in range(3)]
    mr_agents = [MeanReversionTrader(f"mr_{i}", 100000.0, message_bus=mb) for i in range(2)]
    
    all_agents = mom_agents + mr_agents
    
    # Seed MM logic (Passive Provider)
    def run_mm():
        # MM keeps order around mid
        mid = env._get_mid_price()
        # Cancel old and replace
        # Simplified: Just layer in new orders if book thin
        snap = env.book.get_snapshot(depth=5)
        if len(snap['bids']) < 5:
            env.step({'type': 'LIMIT', 'side': 'BUY', 'price': mid - 1.0, 'quantity': 50, 'id': f'mm_b_{random.randint(0,1000000)}', 'agent_id': mm_id})
        if len(snap['asks']) < 5:
            env.step({'type': 'LIMIT', 'side': 'SELL', 'price': mid + 1.0, 'quantity': 50, 'id': f'mm_s_{random.randint(0,1000000)}', 'agent_id': mm_id})

    # Init Portfolios
    env.portfolios[mm_id] = {'cash': 1e9, 'inventory': 10000}
    for a in all_agents:
        env.portfolios[a.agent_id] = {'cash': 100000.0, 'inventory': 0}
        
    # Simulation Loop
    steps = 50
    stress_detected = False
    culprits = []
    
    print(f"Simulating {steps} steps with {len(all_agents)} agents...")
    
    # Inject Initial Liquidity
    env.book.add_order('BUY', 99.0, 100, 'init_b', mm_id)
    env.book.add_order('SELL', 101.0, 100, 'init_s', mm_id)
    
    for t in range(steps):
        # 1. MM provides liquidity
        run_mm()
        
        # 2. Shock Event at t=10
        if t == 10:
            print("--- INJECTING SHOCK (Market Buy) ---")
            env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 200.0, 'quantity': 500, 'id': 'shock', 'agent_id': 'whale'})
            
        # 3. Agents Decide & Act
        obs = env._get_obs()
        
        # Shuffle order
        random.shuffle(all_agents)
        for agent in all_agents:
            action = agent.decide(obs)
            if action['type'] != 'HOLD':
                # Add random jitter to simple strategy to ensure matching
                if action['type'] == 'LIMIT':
                    # Fix ID
                    action['id'] = f"{action['id']}_{t}"
                env.step(action)
                
        # 4. Monitor Risk
        risk_monitor.update(obs, env.last_trades)
        report = risk_monitor.detect_stress()
        
        mid =  obs['mid_price']
        if report.get('status') == 'HIGH_VOLATILITY':
            print(f"Step {t}: HIGH VOLATILITY DETECTED! Vol: {report['volatility']:.2f}")
            print(f"Top Contributors: {report['top_contributors']}")
            stress_detected = True
            culprits = report['top_contributors']
            
        if t % 10 == 0:
            print(f"Step {t}: Price {mid:.2f}")

    # Analysis
    if not stress_detected:
        print("FAILURE: No systemic stress detected after shock.")
        sys.exit(1)
        
    print("\nSystemic Risk Detected.")
    # Verify Attribution
    # Momentum traders should be top contributors because they chase the shock
    # Whale is also there but we care about agents.
    
    mom_volume = 0
    mr_volume = 0
    
    for agent_id, vol in culprits:
        if "mom" in agent_id:
            mom_volume += vol
        if "mr" in agent_id:
            mr_volume += vol
            
    print(f"Attribution - Momentum Vol: {mom_volume}, MeanRev Vol: {mr_volume}")
    
    if mom_volume > mr_volume:
        print("SUCCESS: Momentum agents identified as primary drivers of volatility.")
    else:
        print("WARNING: unexpected attribution.")
        
    sys.exit(0)

if __name__ == "__main__":
    test_multi_agent_risk()
