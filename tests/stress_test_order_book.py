import pytest
import time
import random
import logging
import sys
from environments.order_book_env import OrderBookEnv

# Setup logger for this test
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OrderBookStress")

class TestOrderBookStress:
    @pytest.fixture
    def env(self):
        env = OrderBookEnv()
        env.reset()
        return env

    def test_order_flood(self, env):
        """
        Inject 10,000 orders as fast as possible to measure stability and perform basic perf check.
        """
        COUNT = 10000
        start_time = time.time()
        
        for i in range(COUNT):
            side = 'BUY' if i % 2 == 0 else 'SELL'
            # Oscillating price to force matches and resting
            base_price = 100.0
            price = base_price + (random.random() * 10 - 5)
            
            action = {
                'type': 'LIMIT',
                'side': side,
                'price': round(price, 2),
                'quantity': random.randint(1, 100),
                'id': f"flood_{i}"
            }
            env.step(action)
            
        duration = time.time() - start_time
        tps = COUNT / duration
        logger.info(f"Flood Test: Processed {COUNT} orders in {duration:.4f}s ({tps:.2f} TPS)")
        
        # Verify Integrity
        obs = env._get_obs()
        snapshot = obs['market_snapshot']
        
        # Check no negative quantities
        for bid in snapshot['bids']:
            assert bid['quantity'] > 0
        for ask in snapshot['asks']:
            assert ask['quantity'] > 0
            
        # Check crossed book invariant (should be uncrossed after processing)
        if snapshot['bids'] and snapshot['asks']:
            best_bid = snapshot['bids'][0]['price']
            best_ask = snapshot['asks'][0]['price']
            # Using exact comparison for float might be tricky, but logic dictates uncrossed.
            # However, if they are equal, they should have matched IF they arrived sequentially.
            # So Best Bid < Best Ask
            assert best_bid < best_ask, f"Book is crossed! Bid: {best_bid}, Ask: {best_ask}"

    def test_zero_liquidity_handling(self, env):
        """
        Ensure system handles operations on empty book gracefully.
        """
        # 1. Clear Book (handled by reset)
        obs = env._get_obs()
        assert len(obs['market_snapshot']['bids']) == 0
        assert len(obs['market_snapshot']['asks']) == 0
        
        # 2. Cancel non-existent order
        _, _, _, info = env.step({'type': 'CANCEL', 'id': 'ghost_order'})
        assert info['cancel_success'] is False
        
        # 3. Match against nothing (should rest)
        env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 10, 'id': 'lonely_buy'})
        obs = env._get_obs()
        assert len(obs['market_snapshot']['bids']) == 1
        
        # 4. Sell that doesn't match (price too high)
        env.step({'type': 'LIMIT', 'side': 'SELL', 'price': 200.0, 'quantity': 10, 'id': 'lonely_sell'})
        obs = env._get_obs()
        assert len(obs['market_snapshot']['bids']) == 1
        assert len(obs['market_snapshot']['asks']) == 1

    def test_random_chaos_consistency(self, env):
        """
        Randomly mix Adds and Cancels to check for state corruption.
        """
        ops = 5000 
        order_ids = []
        
        for i in range(ops):
            if order_ids and random.random() < 0.3:
                # Cancel something
                oid = random.choice(order_ids)
                env.step({'type': 'CANCEL', 'id': oid})
                # We don't remove from local list to simulate "double cancel" attempts or late cancels
            else:
                # Add Order
                oid = f"chaos_{i}"
                order_ids.append(oid)
                side = random.choice(['BUY', 'SELL'])
                price = round(100.0 + random.uniform(-10, 10), 2)
                qty = random.randint(1, 50)
                
                env.step({
                    'type': 'LIMIT', 
                    'side': side, 
                    'price': price, 
                    'quantity': qty, 
                    'id': oid
                })
        
        # Final Consistency Check
        obs = env._get_obs()
        snapshot = obs['market_snapshot']
        
        bids = snapshot['bids']
        asks = snapshot['asks']
        
        # 1. Order (Heaps should produce sorted output via get_snapshot)
        # Bids: Descending Price
        bid_prices = [b['price'] for b in bids]
        assert bid_prices == sorted(bid_prices, reverse=True), "Bids not sorted descending"
        
        # Asks: Ascending Price
        ask_prices = [a['price'] for a in asks]
        assert ask_prices == sorted(ask_prices), "Asks not sorted ascending"
        
        # 2. Uncrossed
        if bids and asks:
            assert bids[0]['price'] < asks[0]['price'], "Chaos left crossed book"

        logger.info(f"Chaos Test Passed. Final Book Depth - Bids: {len(bids)}, Asks: {len(asks)}")

    def test_latency_reordering_simulation(self, env):
        """
        Simulate delayed arrival by buffering actions and applying them in weird blocks, 
        checking if the final state is still valid (uncrossed).
        """
        # This is implicitly tested by "Random Chaos", but let's do a specific burst.
        # Generate 100 buy orders climbing up, 100 sell orders climbing down.
        # If processed in perfect order of price aggressiveness, they would all cross.
        # We verify that 'step' resolves them correctly regardless of the logical "confusion".
        
        for i in range(100):
            # Aggressive Buy
            env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100 + i, 'quantity': 1, 'id': f"b_{i}"})
            # Aggressive Sell (crossing the buy)
            env.step({'type': 'LIMIT', 'side': 'SELL', 'price': 100 + i, 'quantity': 1, 'id': f"s_{i}"})
            
        # Everything should have matched or be left in a clean state.
        obs = env._get_obs()
        snapshot = obs['market_snapshot']
        
        if snapshot['bids'] and snapshot['asks']:
             assert snapshot['bids'][0]['price'] < snapshot['asks'][0]['price']
