from environments.order_book_env import OrderBookEnv

def test():
    env = OrderBookEnv(start_cash=10000.0)
    agent = "a"
    mm = "mm"
    
    # Setup
    env.portfolios[agent] = {'cash': 10000.0, 'inventory': 0}
    env.portfolios[mm] = {'cash': 10000.0, 'inventory': 1000}
    
    # Buy 100 @ 100
    env.step({'type': 'LIMIT', 'side': 'BUY', 'price': 100.0, 'quantity': 100, 'id': 'b', 'agent_id': agent})
    env.step({'type': 'LIMIT', 'side': 'SELL', 'price': 100.0, 'quantity': 100, 'id': 's', 'agent_id': mm})
    
    p = env.portfolios[agent]
    print(f"Agent Port: {p}")
    
    if p['inventory'] == 100:
        print("TRADE SUCCESS")
    else:
        print(f"TRADE FAILED. Cash: {p['cash']}, Inv: {p['inventory']}")
    
    p_mm = env.portfolios[mm]
    print(f"MM Port: {p_mm}")

test()
