import heapq
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from .base_env import BaseEnvironment

logger = logging.getLogger(__name__)

@dataclass(order=True)
class Order:
    price: float
    timestamp: float
    quantity: int = field(compare=False)
    order_id: str = field(compare=False)
    side: str = field(compare=False) # 'BUY' or 'SELL'
    agent_id: str = field(compare=False, default="unknown")

class BidOrder(Order):
    def __lt__(self, other):
        if self.price != other.price:
            return self.price > other.price
        return self.timestamp < other.timestamp

class AskOrder(Order):
    def __lt__(self, other):
        if self.price != other.price:
            return self.price < other.price
        return self.timestamp < other.timestamp

class OrderBook:
    def __init__(self):
        self.bids: List[BidOrder] = []
        self.asks: List[AskOrder] = []
        self.orders: Dict[str, Order] = {}
        self.time_counter = 0.0

    def add_order(self, side: str, price: float, quantity: int, order_id: str, agent_id: str) -> List[Dict]:
        self.time_counter += 1.0
        trades = []
        remaining_qty = quantity
        
        if side == 'BUY':
            while remaining_qty > 0 and self.asks:
                best_ask = self.asks[0]
                if price >= best_ask.price:
                    trade_qty = min(remaining_qty, best_ask.quantity)
                    trade_price = best_ask.price
                    
                    trades.append({
                        'buy_order_id': order_id,
                        'buy_agent_id': agent_id,
                        'sell_order_id': best_ask.order_id,
                        'sell_agent_id': best_ask.agent_id,
                        'price': trade_price,
                        'quantity': trade_qty,
                        'side': 'BUY' # Aggressor side
                    })
                    
                    remaining_qty -= trade_qty
                    best_ask.quantity -= trade_qty
                    
                    if best_ask.quantity == 0:
                        heapq.heappop(self.asks)
                        if best_ask.order_id in self.orders:
                            del self.orders[best_ask.order_id]
                else:
                    break
            
            if remaining_qty > 0:
                order = BidOrder(price=price, timestamp=self.time_counter, quantity=remaining_qty, order_id=order_id, side='BUY', agent_id=agent_id)
                heapq.heappush(self.bids, order)
                self.orders[order_id] = order
                
        elif side == 'SELL':
            while remaining_qty > 0 and self.bids:
                best_bid = self.bids[0]
                if price <= best_bid.price:
                    trade_qty = min(remaining_qty, best_bid.quantity)
                    trade_price = best_bid.price
                    
                    trades.append({
                        'buy_order_id': best_bid.order_id,
                        'buy_agent_id': best_bid.agent_id,
                        'sell_order_id': order_id,
                        'sell_agent_id': agent_id,
                        'price': trade_price,
                        'quantity': trade_qty,
                        'side': 'SELL' # Aggressor side
                    })
                    
                    remaining_qty -= trade_qty
                    best_bid.quantity -= trade_qty
                    
                    if best_bid.quantity == 0:
                        heapq.heappop(self.bids)
                        if best_bid.order_id in self.orders:
                            del self.orders[best_bid.order_id]
                else:
                    break
            
            if remaining_qty > 0:
                order = AskOrder(price=price, timestamp=self.time_counter, quantity=remaining_qty, order_id=order_id, side='SELL', agent_id=agent_id)
                heapq.heappush(self.asks, order)
                self.orders[order_id] = order
                
        return trades

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders:
            order = self.orders[order_id]
            del self.orders[order_id]
            if order.side == 'BUY':
                try:
                    self.bids.remove(order)
                    heapq.heapify(self.bids)
                except ValueError:
                    pass
            else:
                try:
                    self.asks.remove(order)
                    heapq.heapify(self.asks)
                except ValueError:
                    pass
            return True
        return False

    def get_snapshot(self, depth: int = 5) -> Dict:
        top_bids = heapq.nsmallest(depth, self.bids)
        top_asks = heapq.nsmallest(depth, self.asks)
        return {
            'bids': [{'price': b.price, 'quantity': b.quantity, 'id': b.order_id, 'agent_id': b.agent_id} for b in top_bids],
            'asks': [{'price': a.price, 'quantity': a.quantity, 'id': a.order_id, 'agent_id': a.agent_id} for a in top_asks]
        }

class OrderBookEnv(BaseEnvironment):
    def __init__(self, start_cash: float = 100000.0):
        self.start_cash = start_cash
        self.book = OrderBook()
        self.last_trades = []
        # Portfolios: agent_id -> {cash, inventory}
        self.portfolios: Dict[str, Dict[str, float]] = {}

    def reset(self) -> Dict[str, Any]:
        self.book = OrderBook()
        self.last_trades = []
        self.portfolios = {}
        return self._get_obs()

    def _ensure_portfolio(self, agent_id: str):
        if agent_id not in self.portfolios:
            self.portfolios[agent_id] = {'cash': self.start_cash, 'inventory': 0}

    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """
        Extended Action Schema:
        { ..., 'agent_id': str } (Required for portfolio logic)
        """
        action_type = action.get('type')
        order_id = action.get('id')
        agent_id = action.get('agent_id', 'unknown')
        
        self._ensure_portfolio(agent_id)
        
        info = {'trades': [], 'errors': []}
        
        if action_type == 'LIMIT':
            side = action.get('side')
            price = float(action.get('price'))
            qty = int(action.get('quantity'))
            
            # Basic Pre-Trade Check (optional: can be strict or loose, risk monitor handles strict)
            # For now, let's allow negative cash/inventory in the matching engine (margin), 
            # and rely on RiskMonitor to yell about it. Or we can enforce here.
            # Plan said: "Hard Constraints: Reject orders if insufficient cash/inventory."
            rejected = False
            portfolio = self.portfolios[agent_id]
            cost = price * qty
            
            if side == 'BUY':
                 if portfolio['cash'] < cost:
                     info['errors'].append("Insufficient Cash")
                     rejected = True
            elif side == 'SELL':
                 # If we enforce no short selling:
                 if portfolio['inventory'] < qty:
                     info['errors'].append("Insufficient Inventory")
                     # For test purposes, we might want to ALLOW short selling or partial implementation.
                     # Let's enforced strict NO SHORT for "sanity" unless specified.
                     rejected = True
            
            if not rejected:
                trades = self.book.add_order(side, price, qty, order_id, agent_id)
                info['trades'] = trades
                self.last_trades = trades
                self._process_trades(trades)
            else:
                info['rejected'] = True

        elif action_type == 'CANCEL':
            success = self.book.cancel_order(order_id)
            info['cancel_success'] = success
            
        return self._get_obs(), 0.0, False, info

    def _process_trades(self, trades: List[Dict]):
        for trade in trades:
            price = trade['price']
            qty = trade['quantity']
            cost = price * qty
            
            # Buyer
            buyer = trade['buy_agent_id']
            self._ensure_portfolio(buyer)
            self.portfolios[buyer]['cash'] -= cost
            self.portfolios[buyer]['inventory'] += qty
            
            # Seller
            seller = trade['sell_agent_id']
            self._ensure_portfolio(seller)
            self.portfolios[seller]['cash'] += cost
            self.portfolios[seller]['inventory'] -= qty

    def _get_obs(self) -> Dict[str, Any]:
        return {
            'market_snapshot': self.book.get_snapshot(),
            'last_trades': self.last_trades,
            'portfolios': self.portfolios, # Public for debugging/risk monitoring
            'mid_price': self._get_mid_price()
        }

    def _get_mid_price(self) -> float:
        snapshot = self.book.get_snapshot(depth=1)
        best_bid = snapshot['bids'][0]['price'] if snapshot['bids'] else None
        best_ask = snapshot['asks'][0]['price'] if snapshot['asks'] else None
        
        if best_bid and best_ask:
            return (best_bid + best_ask) / 2
        return best_bid if best_bid else (best_ask if best_ask else 100.0)
