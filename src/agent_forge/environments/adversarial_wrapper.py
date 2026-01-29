import random
import logging
from typing import Dict, Any, Tuple
from .order_book_env import OrderBookEnv

logger = logging.getLogger("AdversarialMarket")

class AdversarialOrderBookWrapper:
    def __init__(self, env: OrderBookEnv, config: Dict[str, Any] = None):
        self.env = env
        self.config = config or {}
        
        # Probabilities
        self.p_reject = self.config.get('p_reject', 0.0)
        self.p_flash_crash = self.config.get('p_flash_crash', 0.0)
        self.p_liquidity_crisis = self.config.get('p_liquidity_crisis', 0.0)
        
        # State
        self.step_count = 0

    def reset(self) -> Dict[str, Any]:
        self.step_count = 0
        return self.env.reset()

    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        self.step_count += 1
        info_extras = {}
        
        # 1. Random Order Rejection
        if action.get('type') == 'LIMIT':
            if random.random() < self.p_reject:
                logger.warning(f"[ADVERSARY] Rejecting order {action.get('id')}")
                return self.env._get_obs(), 0.0, False, {'rejected': True, 'reason': 'ADVERSARIAL_REJECTION'}

        # 2. Flash Crash Injection (Before processing action)
        if random.random() < self.p_flash_crash:
            logger.warning("[ADVERSARY] FLASH CRASH INITIATED")
            # Dump massive sell order to clear bids
            crash_id = f"crash_{self.step_count}"
            self.env.portfolios['adversary'] = {'cash': 1e9, 'inventory': 100000}
            
            # Get current best bid to know where to smash
            obs = self.env._get_obs()
            bids = obs['market_snapshot']['bids']
            if bids:
                deepest_bid = bids[-1]['price']
                crash_price = deepest_bid * 0.5 # Smash through it
                
                # Execute Crash
                self.env.step({
                    'type': 'LIMIT',
                    'side': 'SELL',
                    'price': crash_price,
                    'quantity': 10000,
                    'id': crash_id,
                    'agent_id': 'adversary'
                })
                info_extras['adversary_event'] = 'FLASH_CRASH'

        # 3. Liquidity Crisis (Spread Widening)
        if random.random() < self.p_liquidity_crisis:
            logger.warning("[ADVERSARY] LIQUIDITY CRISIS - PULLING QUOTES")
            # Cancel all MM orders (Simulated by clearing book on one side? Or just removing top 5?)
            # Since we don't track who is MM easily without agent_id filtering, 
            # let's just use the `cancel_order` if we knew IDs.
            # Brute force: Re-init book? No that kills agent orders too.
            # Let's implementation: Remove top 3 levels of Bids and Asks to widen spread.
            # Access internal book directly (Whitebox adversary)
            
            # Remove top bids
            for _ in range(3):
                if self.env.book.bids:
                    import heapq
                    heapq.heappop(self.env.book.bids)
            # Remove top asks
            for _ in range(3):
                if self.env.book.asks:
                    import heapq
                    heapq.heappop(self.env.book.asks)
            
            info_extras['adversary_event'] = 'LIQUIDITY_CRISIS'

        # Process actual action
        obs, reward, done, info = self.env.step(action)
        info.update(info_extras)
        return obs, reward, done, info

    @property
    def portfolios(self):
        return self.env.portfolios
