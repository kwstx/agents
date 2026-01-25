import os
import time
import csv
import json
import threading
import pandas as pd
from datetime import datetime
from dashboards.data_loader import load_metrics, METRICS_FILE

# Configuration
TEST_DURATION = 5  # Run for 5 seconds
WRITE_INTERVAL = 0.1 # Write every 100ms
ACCEPTABLE_LATENCY_MS = 500

def writer_thread(stop_event):
    """Simulates the simulation_runner writing metrics."""
    step = 0
    while not stop_event.is_set():
        # Write timestamp is NOW
        write_time = datetime.now().isoformat()
        
        # Simulating simulation_runner.py atomic append
        with open(METRICS_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            # Log format: timestamp, step, agent_id, epsilon, reward
            # We embed the precise write timestamp in the 'agent_id' field for easy extraction? 
            # Or just use the timestamp column.
            # Let's use the timestamp column.
            writer.writerow([write_time, step, "TEST_AGENT", 1.0, 10.0])
            
        step += 1
        time.sleep(WRITE_INTERVAL)

def reader_thread(stop_event, latencies):
    """Simulates the dashboard polling metrics."""
    last_step = -1
    
    while not stop_event.is_set():
        start_read = time.time()
        
        # Use data_loader's actual function
        df = load_metrics()
        
        if not df.empty:
            # Check latest row
            latest = df.iloc[-1]
            step = int(latest["step"])
            
            if step > last_step:
                # New data found!
                read_time = time.time()
                write_time_str = latest["timestamp"]
                try:
                    write_time = datetime.fromisoformat(write_time_str).timestamp()
                    latency_ms = (read_time - write_time) * 1000
                    latencies.append(latency_ms)
                    # print(f"Step {step}: Latency {latency_ms:.2f}ms")
                except:
                    pass
                last_step = step
                
        # Simulate Streamlit auto-refresh rate? 
        # User wants to know "how long it takes ... to appear". 
        # If we poll as fast as possible, we measure the *system* latency.
        # If we poll at 1s, the latency will be dominated by polling interval.
        # We want to measure the pipeline overhead. So we poll fast.
        time.sleep(0.01) 

def main():
    print(f"Starting Latency Benchmark (Duration: {TEST_DURATION}s)...")
    
    # Clean setup
    if os.path.exists(METRICS_FILE):
        os.remove(METRICS_FILE)
    # Init headers
    with open(METRICS_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "step", "agent_id", "epsilon", "reward"])

    stop_event = threading.Event()
    latencies = []
    
    w = threading.Thread(target=writer_thread, args=(stop_event,))
    r = threading.Thread(target=reader_thread, args=(stop_event, latencies))
    
    w.start()
    r.start()
    
    try:
        time.sleep(TEST_DURATION)
    finally:
        stop_event.set()
        w.join()
        r.join()
        
    # Analyze
    if latencies:
        avg_lat = sum(latencies) / len(latencies)
        max_lat = max(latencies)
        min_lat = min(latencies)
        
        print(f"\nResults ({len(latencies)} samples):")
        print(f"Average Latency: {avg_lat:.2f}ms")
        print(f"Max Latency:     {max_lat:.2f}ms")
        print(f"Min Latency:     {min_lat:.2f}ms")
        
        if avg_lat < ACCEPTABLE_LATENCY_MS:
            print("PASS: Latency within acceptable limits.")
        else:
            print(f"FAIL: Latency too high (> {ACCEPTABLE_LATENCY_MS}ms).")
    else:
        print("FAIL: No data read during test.")

if __name__ == "__main__":
    main()
