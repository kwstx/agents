import pytest
import asyncio
import tracemalloc
from utils.message_bus import MessageBus

# Mock Handler that always fails
def crashing_handler(message):
    raise ValueError("Crash")

@pytest.mark.asyncio
async def test_dlq_cap():
    """Verify DLQ does not grow indefinitely."""
    # Limit DLQ to 10
    bus = MessageBus(log_path="logs/endurance.jsonl", dlq_limit=10)
    await bus.start()
    
    bus.subscribe("crash", crashing_handler)
    
    # Send 50 crashing messages
    token = bus.register("system")
    for i in range(50):
        await bus.publish("crash", "system", f"fail_{i}", auth_token=token)
        
    await asyncio.sleep(0.5) # Allow processing
    
    # Assert size capped at 10
    assert len(bus.dlq) == 10
    # Assert circular: The last message should be in there (fail_49)
    # Payload of last in DLQ should be one of the later ones
    print(f"DLQ Tip: {bus.dlq[-1].payload}")
    assert bus.dlq[-1].payload == "fail_49"
    
    await bus.stop()

@pytest.mark.asyncio
async def test_memory_stability():
    """Verify memory doesn't leak over iterations."""
    tracemalloc.start()
    
    bus = MessageBus(log_path="logs/endurance.jsonl")
    await bus.start()
    token = bus.register("system")
    
    bus.subscribe("ping", lambda m: None) # No-op handler
    
    snapshot1 = tracemalloc.take_snapshot()
    
    # Run 1000 messages
    for i in range(1000):
        await bus.publish("ping", "system", "payload" * 10, auth_token=token)
        
    await asyncio.sleep(0.1)
    
    snapshot2 = tracemalloc.take_snapshot()
    
    stats = snapshot2.compare_to(snapshot1, 'lineno')
    print("\n[Top 3 Memory Changes]")
    for stat in stats[:3]:
        print(stat)
        
    # We expect some growth due to logs/buffers, but not massive.
    # Total growth shouldn't exceed modest MBs.
    
    total_diff = sum(stat.size_diff for stat in stats)
    print(f"Total Memory Diff: {total_diff / 1024:.2f} KB")
    
    # Arbitrary threshold: 500KB leak for 1000 messages is acceptable/noise (logging buffers etc)
    # If it's multi-megabytes, likely a leak.
    assert total_diff < 1024 * 1024, "Memory grew more than 1MB!"
    
    await bus.stop()
    tracemalloc.stop()
