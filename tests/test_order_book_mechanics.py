import pytest
from environments.order_book_env import OrderBookEnv

class TestOrderBookMechanics:
    @pytest.fixture
    def env(self):
        env = OrderBookEnv()
        env.reset()
        return env

    def test_resting_limit_order(self, env):
        """
        Scenario 1: Single limit order rests in the book.
        A BUY order at 100 should be the best bid.
        """
        action = {
            'type': 'LIMIT',
            'side': 'BUY',
            'price': 100.0,
            'quantity': 10,
            'id': 'order_1'
        }
        obs, _, _, info = env.step(action)
        
        snapshot = obs['market_snapshot']
        assert len(snapshot['bids']) == 1
        assert snapshot['bids'][0]['price'] == 100.0
        assert snapshot['bids'][0]['quantity'] == 10
        assert len(info['trades']) == 0

    def test_crossing_order_immediate_full_fill(self, env):
        """
        Scenario 2: Crossing sell order matches immediate buy order.
        """
        # 1. Place Buy Limit 100
        env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 10, 'id': 'buy_1'})
        
        # 2. Place Sell Limit 99 (Crosses 100) -> Should match at Maker Price (100)
        action = {'type': 'LIMIT', 'side': 'SELL', 'price': 99.0, 'quantity': 5, 'id': 'sell_1'}
        obs, _, _, info = env.step(action)
        
        trades = info['trades']
        assert len(trades) == 1
        trade = trades[0]
        assert trade['price'] == 100.0 # Match at maker price
        assert trade['quantity'] == 5
        assert trade['buy_order_id'] == 'buy_1'
        assert trade['sell_order_id'] == 'sell_1'
        
        # Check Book State
        snapshot = obs['market_snapshot']
        assert snapshot['bids'][0]['quantity'] == 5 # 10 - 5
        assert len(snapshot['asks']) == 0 # Sell order fully filled

    def test_partial_fill_and_resting_remainder(self, env):
        """
        Scenario 3: Partial fill where aggressor is larger than maker.
        Remainder of aggressor should rest in book.
        """
        # 1. Place Sell Limit 105, Qty 10
        env.step({'type': 'LIMIT', 'side': 'SELL', 'price': 105.0, 'quantity': 10, 'id': 'sell_1'})
        
        # 2. Place Buy Limit 105, Qty 15 (Matches 10, Remainder 5 rests)
        action = {'type': 'LIMIT', 'side': 'BUY', 'price': 105.0, 'quantity': 15, 'id': 'buy_1'}
        obs, _, _, info = env.step(action)
        
        trades = info['trades']
        assert len(trades) == 1
        assert trades[0]['quantity'] == 10
        
        snapshot = obs['market_snapshot']
        # Asks empty
        assert len(snapshot['asks']) == 0
        # Buy remainder resting
        assert len(snapshot['bids']) == 1
        assert snapshot['bids'][0]['price'] == 105.0
        assert snapshot['bids'][0]['quantity'] == 5

    def test_price_time_priority(self, env):
        """
        Scenario: Two orders at same price. First one should match first.
        """
        # 1. Buy 100, Qty 10 (Time 0)
        env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 10, 'id': 'buy_early'})
        # 2. Buy 100, Qty 10 (Time 1)
        env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 10, 'id': 'buy_late'})
        
        # 3. Sell 100, Qty 15. Should match 10 from early, 5 from late.
        action = {'type': 'LIMIT', 'side': 'SELL', 'price': 100.0, 'quantity': 15, 'id': 'sell_agg'}
        _, _, _, info = env.step(action)
        
        trades = info['trades']
        assert len(trades) == 2
        
        # First trade: buy_early
        assert trades[0]['buy_order_id'] == 'buy_early'
        assert trades[0]['quantity'] == 10
        
        # Second trade: buy_late
        assert trades[1]['buy_order_id'] == 'buy_late'
        assert trades[1]['quantity'] == 5

    def test_cancellation(self, env):
        """
        Scenario 4: Cancel an order.
        """
        # 1. Place Buy
        env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 10, 'id': 'buy_to_cancel'})
        obs, _, _, _ = env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 90.0, 'quantity': 5, 'id': 'buy_other'})
        
        assert len(obs['market_snapshot']['bids']) == 2
        
        # 2. Cancel
        _, _, _, info = env.step({'type': 'CANCEL', 'id': 'buy_to_cancel'})
        assert info['cancel_success'] is True
        
        # 3. Verify
        obs = env._get_obs()
        snapshot = obs['market_snapshot']
        assert len(snapshot['bids']) == 1
        assert snapshot['bids'][0]['id'] == 'buy_other'
