import pytest
import asyncio
import time
import statistics
from utils.message_bus import MessageBus, Message
from agents.base_agent import BaseAgent

# Configure test parameters
NUM_SENDERS = 20
MSGS_PER_SENDER = 500
TOTAL_MSGS = NUM_SENDERS * MSGS_PER_SENDER
TIMEOUT_SECONDS = 30 

class LoadSender(BaseAgent):
    async def process_task(self, task):
        pass
        
    async def blast_messages(self, count):
        """Sends messages as fast as possible."""
        for i in range(count):
            await self.send_message(
                topic="stress_test", 
                payload={"seq": i, "ts": time.time()},
                receiver="sink" # Target sink
            )

class LoadSink(BaseAgent):
    def __init__(self, agent_id, bus):
        super().__init__(agent_id, bus)
        self.received_count = 0
        self.latencies = []
        self.start_time = None
        self.end_time = None
        self.done_event = asyncio.Event()

    async def process_task(self, task):
        pass

    async def receive_message(self, message: Message):
        # Only process if valid stress test message
        if message.topic != "stress_test":
            return
            
        current_time = time.time()
        
        # Calculate latency
        send_time = message.payload["ts"]
        latency = current_time - send_time
        self.latencies.append(latency)
        
        if self.received_count == 0:
            self.start_time = current_time
            
        self.received_count += 1
        
        if self.received_count >= TOTAL_MSGS:
            self.end_time = current_time
            self.done_event.set()
        
        await super().receive_message(message)


@pytest.mark.asyncio
async def test_high_load_stress():
    """
    Stress test the messaging bus:
    - 20 senders, 500 msgs each (10,000 total)
    - 1 sink
    - Expect no drops, no crashes.
    """
    print(f"\n--- Starting Stress Test: {TOTAL_MSGS} messages ---")
    
    bus = MessageBus(log_path="logs/stress_test.jsonl")
    await bus.start()

    sink = LoadSink("sink", bus)
    await sink.start()
    bus.subscribe("stress_test", sink.receive_message)

    senders = [LoadSender(f"sender_{i}", bus) for i in range(NUM_SENDERS)]
    for s in senders:
        await s.start()

    # Start Probing for Queue Size
    async def monitor_queue():
        while not sink.done_event.is_set():
            q_size = bus.qsize
            if q_size > 100:
                # Just print if backlog grows
                # print(f"Queue Backlog: {q_size}") 
                pass
            await asyncio.sleep(0.1)
    
    monitor_task = asyncio.create_task(monitor_queue())
    
    # Unleash the horde
    start_time = time.time()
    tasks = [s.blast_messages(MSGS_PER_SENDER) for s in senders]
    await asyncio.gather(*tasks)
    
    print("All messages sent. Waiting for sink...")
    
    # Wait for completion
    try:
        await asyncio.wait_for(sink.done_event.wait(), timeout=TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        print(f"FAILED: Timed out. Received {sink.received_count}/{TOTAL_MSGS}")
        monitor_task.cancel()
        assert False, f"Timeout! Only received {sink.received_count} messages."
    
    monitor_task.cancel()
    
    end_time = time.time()
    total_time = end_time - start_time
    throughput = TOTAL_MSGS / total_time
    
    avg_latency = statistics.mean(sink.latencies) * 1000 # ms
    max_latency = max(sink.latencies) * 1000 # ms
    p99_latency = sorted(sink.latencies)[int(len(sink.latencies)*0.99)] * 1000
    
    print(f"\n--- Stress Test Results ---")
    print(f"Total Messages: {TOTAL_MSGS}")
    print(f"Total Time:     {total_time:.2f}s")
    print(f"Throughput:     {throughput:.2f} msgs/sec")
    print(f"Avg Latency:    {avg_latency:.2f} ms")
    print(f"Max Latency:    {max_latency:.2f} ms")
    print(f"P99 Latency:    {p99_latency:.2f} ms")
    
    assert sink.received_count == TOTAL_MSGS
    
    # Teardown
    await sink.stop()
    for s in senders:
        await s.stop()
    await bus.stop()
