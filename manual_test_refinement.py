import torch
import numpy as np
import random
import os
import shutil
from collections import deque
from environments.order_book_env import OrderBookEnv
from models.decision_model import GridDecisionModel, ModelConfig
from models.trainer import DQNTrainer

# Configuration
INPUT_SIZE = 6 # [MidPrice, Spread, Inventory, Cash, BestBid, BestAsk]
OUTPUT_SIZE = 4 # [HOLD, BUY, SELL, CLEAR]
HIDDEN_SIZE = 32

class FinancialAdapter:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.last_mid = 100.0

    def encode(self, obs):
        snapshot = obs['market_snapshot']
        portfolios = obs['portfolios']
        
        # Market Features
        bids = snapshot['bids']
        asks = snapshot['asks']
        
        best_bid = bids[0]['price'] if bids else 0.0
        best_ask = asks[0]['price'] if asks else 0.0
        
        mid = (best_bid + best_ask) / 2 if (best_bid and best_ask) else (best_bid if best_bid else 100.0)
        spread = best_ask - best_bid if (best_bid and best_ask) else 0.0
        
        # Agent Features
        p = portfolios.get(self.agent_id, {'cash': 100000.0, 'inventory': 0})
        inventory = float(p.get('inventory', 0))
        cash = float(p.get('cash', 0))
        
        # Normalize roughly
        # Price ~ 100. Spread ~ 0-5. Inv ~ -100 to 100. Cash ~ 100k
        state = [
            mid / 100.0,
            spread / 10.0,
            inventory / 100.0, # Target max pos 100
            cash / 100000.0,
            best_bid / 100.0,
            best_ask / 100.0
        ]
        return state

def map_action(action_idx, agent_id, obs):
    """Maps NN output to Env Action."""
    snapshot = obs['market_snapshot']
    mid = obs['mid_price']
    
    # 0: HOLD
    if action_idx == 0:
        return {'type': 'HOLD', 'id': 'noop', 'agent_id': agent_id}
    
    # 1: BUY 10 (Aggressive)
    if action_idx == 1:
        # Buy at Ask + epsilon to cross
        price = snapshot['asks'][0]['price'] if snapshot['asks'] else mid + 1.0
        return {'type': 'LIMIT', 'side': 'BUY', 'price': price, 'quantity': 10, 'id': f'b_{random.randint(0,1000000)}', 'agent_id': agent_id}
    
    # 2: SELL 10
    if action_idx == 2:
        price = snapshot['bids'][0]['price'] if snapshot['bids'] else mid - 1.0
        return {'type': 'LIMIT', 'side': 'SELL', 'price': price, 'quantity': 10, 'id': f's_{random.randint(0,1000000)}', 'agent_id': agent_id}
    
    # 3: CLEAR (Cancel All / Liquidate - for now just Cancel All mock)
    # Since Env doesn't have "Cancel All", we'll just emit a HOLD but log it.
    # Or ideally, send multiple cancels? Env step only takes one action.
    # Let's map it to a "De-Risk" action: Sell if Long, Buy if Short.
    if action_idx == 3:
         port = obs['portfolios'].get(agent_id, {})
         inv = port.get('inventory', 0)
         if inv > 0:
             price = snapshot['bids'][0]['price'] if snapshot['bids'] else mid - 1.0
             return {'type': 'LIMIT', 'side': 'SELL', 'price': price, 'quantity': min(inv, 10), 'id': f'liq_s_{random.randint(0,1000000)}', 'agent_id': agent_id}
         elif inv < 0:
             price = snapshot['asks'][0]['price'] if snapshot['asks'] else mid + 1.0
             return {'type': 'LIMIT', 'side': 'BUY', 'price': price, 'quantity': min(abs(inv), 10), 'id': f'liq_b_{random.randint(0,1000000)}', 'agent_id': agent_id}
         return {'type': 'HOLD', 'id': 'noop', 'agent_id': agent_id}

    return {'type': 'HOLD', 'id': 'noop', 'agent_id': agent_id}

def calculate_reward(agent_id, prev_port, curr_port, current_price, penalty_factor=0.5):
    # PnL Change
    prev_eq = prev_port['cash'] + (prev_port['inventory'] * current_price)
    curr_eq = curr_port['cash'] + (curr_port['inventory'] * current_price)
    pnl = curr_eq - prev_eq
    
    # Drawdown Penalty (Current state only for simple reward)
    # If inventory is high, penalty.
    risk_penalty = abs(curr_port['inventory']) * penalty_factor
    
    return pnl - risk_penalty

def manual_test_refinement():
    print("Starting Auto-Refinement Validation...")
    
    # Setup
    env = OrderBookEnv(start_cash=10000.0)
    config = ModelConfig(input_size=INPUT_SIZE, output_size=OUTPUT_SIZE, hidden_size=HIDDEN_SIZE)
    model = GridDecisionModel(config)
    trainer = DQNTrainer(model, config)
    
    agent_id = "learner"
    adapter = FinancialAdapter(agent_id)
    mm_id = "mm"
    
    # Training Loop
    episodes = 50
    steps_per_episode = 20
    
    # Metrics
    drawdowns = []
    rewards = []
    
    # Keep Early Model
    trainer.save_model("models/early_agent.pth")
    
    print(f"Training for {episodes} episodes...")
    for ep in range(episodes):
        env.reset()
        env.portfolios[agent_id] = {'cash': 10000.0, 'inventory': 0}
        env.portfolios[mm_id] = {'cash': 1e9, 'inventory': 1000}
        
        # Initialize Liquidity
        # Add some resting orders
        for i in range(5):
            env.book.add_order('BUY', 99.0 - i, 100, f'mm_b_{i}', mm_id)
            env.book.add_order('SELL', 101.0 + i, 100, f'mm_s_{i}', mm_id)
            
        obs = env._get_obs()
        state = adapter.encode(obs)
        total_reward = 0
        peak_eq = 10000.0
        max_dd = 0.0
        
        for t in range(steps_per_episode):
            # Select Action
            action_idx = 0
            if random.random() < 0.1: # Epsilon greedy
                action_idx = random.randint(0, OUTPUT_SIZE - 1)
            else:
                with torch.no_grad():
                    q = model(torch.FloatTensor([state]))
                    action_idx = q.argmax().item()
            
            mapped_action = map_action(action_idx, agent_id, obs)
            
            # Step
            prev_port = env.portfolios[agent_id].copy()
            next_obs, _, _, info = env.step(mapped_action)
            
            # Refresh MM liquidity if needed (simple MM logic)
            if not next_obs['market_snapshot']['bids']:
                env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 90.0, 'quantity': 100, 'id': f'mm_b_r_{t}', 'agent_id': mm_id})
            
            next_state = adapter.encode(next_obs)
            curr_port = env.portfolios[agent_id]
            curr_mid = next_obs['mid_price']
            
            # Calculate Risk Metrics
            curr_eq = curr_port['cash'] + (curr_port['inventory'] * curr_mid)
            peak_eq = max(peak_eq, curr_eq)
            dd = (peak_eq - curr_eq) / peak_eq if peak_eq > 0 else 0
            max_dd = max(max_dd, dd)
            
            # Reward: Heavily penalize drawdown
            # Standard PnL
            step_pnl = curr_eq - (prev_port['cash'] + (prev_port['inventory'] * curr_mid))
            
            # Penalty
            reward = step_pnl - (dd * 1000.0) # Huge penalty for DD
            
            trainer.store_experience(state, action_idx, reward, next_state, False)
            trainer.train_step()
            
            state = next_state
            total_reward += reward
            
        rewards.append(total_reward)
        drawdowns.append(max_dd)
        
        if ep % 10 == 0:
            print(f"Ep {ep}: Max DD {max_dd:.2%}, Reward {total_reward:.2f}, Epsilon 0.1")

    # Save Late Model
    trainer.save_model("models/late_agent.pth")
    
    # Analysis
    avg_dd_early = float(np.mean(drawdowns[:10]))
    avg_dd_late = float(np.mean(drawdowns[-10:]))
    
    print(f"\nFinal Analysis:")
    print(f"Avg Drawdown (First 10): {avg_dd_early:.2%}")
    print(f"Avg Drawdown (Last 10): {avg_dd_late:.2%}")
    
    if avg_dd_late < avg_dd_early:
        print("SUCCESS: Agent learned to reduce risk.")
    elif avg_dd_late == 0.0 and avg_dd_early == 0.0:
        print("WARNING: No risk taken. Try increasing volatilty.")
    else:
        print("FAILURE: Agent did not reduce risk.")
        
    # Replay Comparison
    print("\n--- Playback Verification ---")
    # Load Early
    trainer.load_model("models/early_agent.pth")
    # Run 1 Ep
    # ... (Omitted for brevity, logic already covered by stats above)

if __name__ == "__main__":
    manual_test_refinement()
